#!/usr/bin/env python3
"""Probe model availability and merge results into the cache on issue #49."""

import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

CACHE_ISSUE = 49
AVAILABLE_TTL_HOURS = 24
FAILED_TTL_HOURS = 2
PROVIDERS = (
    ("opencode-go-openai", "OPENCODE_GO_API_KEY"),
    ("opencode-go-openai-2", "OPENCODE_GO_2_API_KEY"),
    ("opencode-go-anthropic", "OPENCODE_GO_API_KEY"),
    ("opencode-go-anthropic-2", "OPENCODE_GO_2_API_KEY"),
)
PRIORITY_MODELS = ("glm-5.3", "qwen3.8-max", "kimi-k3")
MAX_CONCURRENT = 5
PROBE_TIMEOUT_SECONDS = 60
PROBE_PROMPT = "Respond with exactly OK."


def run_gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    ).stdout


def read_cache() -> dict:
    try:
        body = run_gh(
            "issue", "view", str(CACHE_ISSUE), "--json", "body", "--jq", ".body"
        )
        cache = json.loads(body)
        return cache if isinstance(cache, dict) else {}
    except Exception:
        return {}


def write_cache(cache: dict) -> None:
    try:
        run_gh("issue", "edit", str(CACHE_ISSUE), "--body", json.dumps(cache))
    except Exception:
        pass


def parse_free_models(opencode_models_output: str) -> list[str]:
    return sorted(
        set(
            re.findall(
                r"^(?:[^\s]+-free|[^\s]*big-pickle)$",
                opencode_models_output,
                re.MULTILINE,
            )
        )
    )


def parse_go_model_ids(models_json: str) -> list[str]:
    try:
        data = json.loads(models_json)
        return sorted(set(m["id"] for m in data.get("data", []) if m.get("id")))
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def load_provider_base_urls() -> dict[str, str]:
    """Run `opencode debug config`, return {provider_id: baseURL} for providers with a baseURL."""
    try:
        output = subprocess.run(
            ["opencode", "debug", "config"], check=True, capture_output=True, text=True, timeout=60
        ).stdout
        config = json.loads(output)
    except Exception as e:
        print(f"warning: failed to read opencode config: {e}", file=sys.stderr)
        return {}
    return {
        name: provider.get("options", {}).get("baseURL")
        for name, provider in config.get("provider", {}).items()
        if provider.get("options", {}).get("baseURL")
    }


def models_endpoint_for(base_url: str) -> str:
    """Anthropic-style baseURLs end in /messages; the models endpoint is always <api-root>/models."""
    return base_url.rstrip("/").removesuffix("/messages") + "/models"


def fetch_model_ids(endpoint: str) -> list[str]:
    """GET the v1/models endpoint with curl User-Agent + x-opencode-session; [] + warning on failure."""
    try:
        session_id = os.urandom(16).hex()
        request = urllib.request.Request(
            endpoint,
            headers={"x-opencode-session": session_id, "User-Agent": "curl/8.5.0"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return parse_go_model_ids(response.read().decode())
    except Exception as e:
        print(f"warning: failed to discover models from {endpoint}: {e}", file=sys.stderr)
        return []


def discover_models() -> tuple[list[str], dict[str, list[str]]]:
    """free_models from `opencode models`; provider_models: {provider: model_ids} per provider."""
    result = subprocess.run(
        ["opencode", "models"], check=True, capture_output=True, text=True, timeout=600
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
    free_models = parse_free_models(result.stdout)
    base_urls = load_provider_base_urls()
    provider_models = {}
    for provider, _ in PROVIDERS:
        base_url = base_urls.get(provider)
        if not base_url:
            print(f"warning: no baseURL configured for {provider}", file=sys.stderr)
            continue
        provider_models[provider] = fetch_model_ids(models_endpoint_for(base_url))
    return free_models, provider_models


def build_candidates(
    free_models: list[str], provider_models: dict[str, list[str]], env: dict
) -> list[str]:
    candidates = []
    for provider, key_env in PROVIDERS:
        if not env.get(key_env):
            continue
        for model in provider_models.get(provider, []):
            candidates.append(f"{provider}/{model}")
    candidates.extend(free_models)
    return candidates


def is_cache_fresh(entry, now: datetime) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("ok"), bool):
        return False
    ttl_hours = AVAILABLE_TTL_HOURS if entry["ok"] else FAILED_TTL_HOURS
    try:
        checked = datetime.fromisoformat(entry["checked"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        return False
    return (now - checked).total_seconds() < ttl_hours * 3600


def probe_model(
    candidate: str, work_dir: str, timeout: int = PROBE_TIMEOUT_SECONDS
) -> bool:
    probe_dir = os.path.join(work_dir, "probe-" + candidate.replace("/", "-"))
    os.makedirs(probe_dir, exist_ok=True)
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
        return False
    log_dir = os.path.join(work_dir, "model-probes")
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(
            os.path.join(log_dir, "probe-" + candidate.replace("/", "-") + ".log"), "w"
        ) as handle:
            handle.write(result.stdout)
            handle.write(result.stderr)
    except OSError:
        pass
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
    cache: dict, free_models: list[str], provider_models: dict[str, list[str]]
) -> list[str]:
    available = []
    go_model_ids_set = set(go_model_ids)
    for model in PRIORITY_MODELS:
        if model not in go_model_ids_set:
            continue
        for provider, _ in PROVIDERS:
            candidate = f"{provider}/{model}"
            if cache.get(candidate, {}).get("ok"):
                available.append(candidate)
    for provider, _ in PROVIDERS:
        for model in provider_models.get(provider, []):
            candidate = f"{provider}/{model}"
            if cache.get(candidate, {}).get("ok"):
                available.append(candidate)
    for model in free_models:
        if cache.get(model, {}).get("ok"):
            available.append(model)
    return list(dict.fromkeys(available))


def write_outputs(cache: dict, available: list[str]) -> None:
    lines = [
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
    cache = read_cache()
    free_models, provider_models = discover_models()
    candidates = build_candidates(free_models, provider_models, os.environ)
    now = datetime.now(timezone.utc)
    pending = [c for c in candidates if not is_cache_fresh(cache.get(c), now)]
    work_dir = os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()
    results = probe_candidates(pending, work_dir)
    checked = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cache = merge_results(cache, results, checked)
    write_cache(cache)
    available = available_models(cache, free_models, provider_models)
    write_outputs(cache, available)
    print("Available models:")
    print("\n".join(available) if available else "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())