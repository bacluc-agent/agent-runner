#!/usr/bin/env python3
"""Probe model availability and merge results into the cache issue."""

import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

AVAILABLE_TTL_HOURS = 24
FAILED_TTL_HOURS = 24
FREE_PATTERNS = [r"(?:-|:)free$", r"big-pickle"]
PROVIDER_WHITELISTS: dict[str, list[str]] = {
    "openrouter": [r"(?:-|:)free$", r"big-pickle"],
    "opencode": [r"(?:-|:)free$", r"big-pickle", r"glm", r"gpt-5\.6-luna", r"qwen", r"kimi"],
}
PROVIDERS = (
    ("opencode-go-openai", "OPENCODE_GO_API_KEY"),
    ("opencode-go-openai-2", "OPENCODE_GO_2_API_KEY"),
    ("opencode-go-anthropic", "OPENCODE_GO_API_KEY"),
    ("opencode-go-anthropic-2", "OPENCODE_GO_2_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
)
MAX_CONCURRENT = 5
PROBE_TIMEOUT_SECONDS = 30
PROBE_BUDGET = 30
PROBE_PROMPT = "Respond with exactly OK."
CACHE_ISSUE_TITLE = "model-discovery cache"
DISCOVERY_TIMEOUT_SECONDS = 120
GITHUB_ISSUE_BODY_LIMIT = 65536


def run_gh(*args: str) -> str:
    repo = os.environ.get("ISSUE_REPOSITORY", "").strip()
    gh_args = ["gh", *(["-R", repo] if repo else []), *args]
    return subprocess.run(gh_args, check=True, capture_output=True, text=True).stdout


def issue_repo() -> str:
    return os.environ.get("ISSUE_REPOSITORY", "")


def resolve_cache_issue() -> str | None:
    """Cache issue number: MODEL_AVAILABILITY_CACHE_ISSUE env, else auto-detect by title."""
    env_issue = os.environ.get("MODEL_AVAILABILITY_CACHE_ISSUE", "").strip()
    if env_issue:
        return env_issue
    repo = issue_repo()
    if not repo:
        print("warning: ISSUE_REPOSITORY not set; cannot auto-detect the cache issue", file=sys.stderr)
        return None
    try:
        query = f"search/issues?q=repo:{repo}+is:issue+in:title+%22{CACHE_ISSUE_TITLE.replace(' ', '+')}%22"
        number = run_gh("api", query, "--jq", ".items[0].number // empty").strip()
        return number or None
    except Exception as e:
        print(f"warning: failed to auto-detect the cache issue: {e}", file=sys.stderr)
        return None


def read_cache(cache_issue: str) -> dict:
    try:
        body = run_gh(
            "issue", "view", str(cache_issue), "--json", "body", "--jq", ".body"
        )
        cache = json.loads(body)
        return cache if isinstance(cache, dict) else {}
    except Exception:
        return {}


def write_cache(cache_issue: str, cache: dict) -> None:
    body = json.dumps(cache)
    if len(body.encode("utf-8")) > GITHUB_ISSUE_BODY_LIMIT:
        print(
            f"warning: cache body is {len(body.encode('utf-8'))} bytes, exceeding the "
            f"{GITHUB_ISSUE_BODY_LIMIT}-byte GitHub issue limit; cache not updated",
            file=sys.stderr,
        )
        return
    try:
        run_gh("issue", "edit", str(cache_issue), "--body", body)
    except Exception as e:
        print(f"warning: failed to write cache issue {cache_issue}: {e}", file=sys.stderr)


def is_whitelisted(model_id: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, model_id, re.IGNORECASE) for pattern in patterns)


def parse_whitelisted_models(opencode_models_output: str, patterns: list[str]) -> list[str]:
    free = []
    rest = []
    for line in opencode_models_output.splitlines():
        line = line.strip()
        if not line:
            continue
        model_id = line.split("/", 1)[-1]
        if not is_whitelisted(model_id, patterns):
            continue
        (free if is_whitelisted(model_id, FREE_PATTERNS) else rest).append(line)
    return sorted(set(free)) + sorted(set(rest))


def parse_go_model_ids(models_json: str) -> list[str]:
    try:
        data = json.loads(models_json)
        return sorted(set(m["id"] for m in data.get("data", []) if m.get("id")))
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def load_provider_config() -> dict[str, dict[str, str | None]]:
    """{provider: {"baseURL": str, "apiKeyEnv": str | None}} from `opencode debug config`."""
    try:
        output = subprocess.run(
            ["opencode", "debug", "config"], check=True, capture_output=True, text=True, timeout=60
        ).stdout
        config = json.loads(output)
    except Exception as e:
        print(f"warning: failed to read opencode config: {e}", file=sys.stderr)
        return {}
    result = {}
    for name, provider in config.get("provider", {}).items():
        options = provider.get("options", {})
        api_key_env = None
        api_key = options.get("apiKey")
        if isinstance(api_key, str):
            match = re.fullmatch(r"\{env:([^}]+)\}", api_key)
            if match:
                api_key_env = match.group(1)
        result[name] = {"baseURL": options.get("baseURL"), "apiKeyEnv": api_key_env}
    return result


def load_provider_base_urls() -> dict[str, str]:
    """Run `opencode debug config`, return {provider_id: baseURL} for providers with a baseURL."""
    return {
        name: info["baseURL"]
        for name, info in load_provider_config().items()
        if info["baseURL"]
    }


def provider_probeable(model_id: str, provider_config: dict, env: dict) -> bool:
    """True if the model's provider can be probed. Built-in/unknown providers pass;
    configured providers need an absolute baseURL and a set apiKey env var."""
    provider = model_id.split("/", 1)[0] if "/" in model_id else ""
    if not provider or provider not in provider_config:
        return True
    info = provider_config[provider]
    base_url = info.get("baseURL")
    if not base_url or not base_url.startswith(("http://", "https://")):
        return False
    api_key_env = info.get("apiKeyEnv")
    return bool(api_key_env) and bool(env.get(api_key_env))


def models_endpoint_for(base_url: str) -> str:
    """Anthropic-style baseURLs end in /messages; the models endpoint is always <api-root>/models."""
    return base_url.rstrip("/").removesuffix("/messages") + "/models"


def fetch_model_ids(endpoint: str, api_key: str | None = None) -> list[str]:
    """GET the v1/models endpoint with curl User-Agent + x-opencode-session; [] + warning on failure."""
    try:
        session_id = os.urandom(16).hex()
        headers = {"x-opencode-session": session_id, "User-Agent": "curl/8.5.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(endpoint, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return parse_go_model_ids(response.read().decode())
    except Exception as e:
        print(f"warning: failed to discover models from {endpoint}: {e}", file=sys.stderr)
        return []


def discover_models() -> tuple[list[str], dict[str, list[str]]]:
    """whitelisted_models from `opencode models`; provider_models: {provider: model_ids} per provider."""
    result = subprocess.run(
        ["opencode", "models"], check=True, capture_output=True, text=True, timeout=DISCOVERY_TIMEOUT_SECONDS
    )
    log_dir = os.path.join(
        os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "model-probes"
    )
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "opencode-models.log"), "w") as handle:
            handle.write(result.stdout)
            handle.write(getattr(result, "stderr", ""))
    except OSError:
        pass
    whitelisted_models = parse_whitelisted_models(
        result.stdout, PROVIDER_WHITELISTS.get("opencode", [ r".*"])
    )
    provider_config = load_provider_config()
    base_urls = {name: info["baseURL"] for name, info in provider_config.items() if info["baseURL"]}
    kept, dropped = [], []
    for model in whitelisted_models:
        (kept if provider_probeable(model, provider_config, os.environ) else dropped).append(model)
    if dropped:
        providers = sorted({m.split("/", 1)[0] for m in dropped})
        print(
            f"warning: skipping {len(dropped)} models from unprobeable providers: {', '.join(providers)}",
            file=sys.stderr,
        )
    whitelisted_models = kept
    provider_models = {}
    for provider, key_env in PROVIDERS:
        base_url = base_urls.get(provider)
        if not base_url or not base_url.startswith(("http://", "https://")):
            print(f"warning: no valid baseURL configured for {provider}", file=sys.stderr)
            continue
        api_key = os.environ.get(key_env)
        if not api_key:
            print(f"warning: no API key configured for {provider}", file=sys.stderr)
            continue
        model_ids = fetch_model_ids(models_endpoint_for(base_url), api_key=api_key)
        patterns = PROVIDER_WHITELISTS.get(provider, [ r".*"])
        if patterns:
            model_ids = [m for m in model_ids if is_whitelisted(m, patterns)]
        provider_models[provider] = model_ids
    return whitelisted_models, provider_models


def build_candidates(
    whitelisted_models: list[str], provider_models: dict[str, list[str]], env: dict
) -> list[str]:
    candidates = []
    for provider, key_env in PROVIDERS:
        if not env.get(key_env):
            continue
        for model in provider_models.get(provider, []):
            candidates.append(f"{provider}/{model}")
    candidates.extend(whitelisted_models)
    return list(dict.fromkeys(candidates))


def is_cache_fresh(entry, now: datetime) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("ok"), bool):
        return False
    ttl_hours = AVAILABLE_TTL_HOURS if entry["ok"] else FAILED_TTL_HOURS
    try:
        checked = datetime.fromisoformat(entry["checked"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        return False
    return (now - checked).total_seconds() < ttl_hours * 3600


def candidate_priority(candidate: str) -> int:
    """Lower = probed first. Workflow-critical models beat everything else."""
    provider, _, model = candidate.partition("/")
    if model == "big-pickle" or candidate == "big-pickle":
        return 0
    if candidate in ("opencode-go-openai/qwen3.8-flash", "opencode-go-openai-2/qwen3.8-flash"):
        return 1
    free = is_whitelisted(model, FREE_PATTERNS)
    if provider == "opencode":
        return 2 if free else 4
    if provider == "openrouter":
        return 3 if free else 7
    if provider in ("opencode-go-openai", "opencode-go-openai-2"):
        return 5
    if provider in ("opencode-go-anthropic", "opencode-go-anthropic-2"):
        return 6
    return 7


def prioritize_candidates(candidates: list[str]) -> list[str]:
    """Stable sort by candidate_priority; input order preserved within a priority."""
    return sorted(candidates, key=candidate_priority)


def select_pending(candidates: list[str], cache: dict, now: datetime) -> tuple[list[str], int]:
    """Stale candidates, highest priority first, capped at PROBE_BUDGET.

    Returns (pending, skipped_count) so main() can report truncation.
    """
    all_pending = [c for c in candidates if not is_cache_fresh(cache.get(c), now)]
    pending = prioritize_candidates(all_pending)[:PROBE_BUDGET]
    return pending, len(all_pending) - len(pending)


def _write_probe_log(log_path: str, content: str) -> None:
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w") as handle:
            handle.write(content)
    except OSError:
        pass


def probe_model(
    candidate: str, work_dir: str, timeout: int = PROBE_TIMEOUT_SECONDS
) -> bool:
    probe_dir = os.path.join(work_dir, "probe-" + candidate.replace("/", "-"))
    os.makedirs(probe_dir, exist_ok=True)
    log_path = os.path.join(work_dir, "model-probes", "probe-" + candidate.replace("/", "-") + ".log")
    try:
        result = subprocess.run(
            [
                "opencode",
                "--pure",
                "run",
                "--dir",
                probe_dir,
                "--model",
                candidate,
                PROBE_PROMPT,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _write_probe_log(log_path, f"TIMEOUT after {timeout}s\n")
        return False
    _write_probe_log(log_path, result.stdout + result.stderr)
    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", result.stdout)
    return result.returncode == 0 and re.fullmatch(r"\s*OK\.?\s*", text) is not None


def probe_candidates(candidates: list[str], work_dir: str) -> dict[str, bool]:
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = {
            executor.submit(probe_model, candidate, work_dir): candidate
            for candidate in candidates
        }
        for future in concurrent.futures.as_completed(futures):
            candidate = futures[future]
            try:
                results[candidate] = future.result()
            except Exception:
                results[candidate] = False
    return results


def merge_results(cache: dict, results: dict[str, bool], checked: str) -> dict:
    merged = dict(cache)
    for candidate, ok in results.items():
        merged[candidate] = {"ok": ok, "checked": checked}
    return merged


def available_models(
    cache: dict, whitelisted_models: list[str], provider_models: dict[str, list[str]]
) -> list[str]:
    available = []
    for model in whitelisted_models:
        if cache.get(model, {}).get("ok"):
            available.append(model)
    for provider, _ in PROVIDERS:
        for model in provider_models.get(provider, []):
            candidate = f"{provider}/{model}"
            if cache.get(candidate, {}).get("ok"):
                available.append(candidate)
    return list(dict.fromkeys(available))


def write_outputs(cache_issue: str | None, cache: dict, available: list[str]) -> None:
    lines = [
        f"cache-issue={cache_issue or ''}",
        "cache-json<<CACHE_EOF",
        json.dumps(cache),
        "CACHE_EOF",
        "available-models<<MODELS_EOF",
        *available,
        "MODELS_EOF",
        "",
    ]
    output = "\n".join(lines)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as handle:
            handle.write(output)
    else:
        print(output, end="")


def main() -> int:
    cache_issue = resolve_cache_issue()
    cache = {}
    if cache_issue is not None:
        cache = read_cache(cache_issue)
    whitelisted_models, provider_models = discover_models()
    candidates = build_candidates(whitelisted_models, provider_models, os.environ)
    now = datetime.now(timezone.utc)
    pending, skipped = select_pending(candidates, cache, now)
    if skipped:
        print(
            f"warning: {skipped} stale candidates skipped (probe budget {PROBE_BUDGET})",
            file=sys.stderr,
        )
    work_dir = os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()
    results = probe_candidates(pending, work_dir)
    ok = sum(1 for v in results.values() if v)
    print(f"probe results: {ok} ok, {len(results) - ok} failed")
    checked = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Re-read the cache right before updating to avoid clobbering concurrent runs' updates
    if cache_issue is not None:
        cache = read_cache(cache_issue) or cache
    cache = merge_results(cache, results, checked)
    if cache_issue is not None:
        write_cache(cache_issue, cache)
    available = available_models(cache, whitelisted_models, provider_models)
    write_outputs(cache_issue, cache, available)
    print("Available models:")
    print("\n".join(available) if available else "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())