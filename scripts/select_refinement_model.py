import argparse
import os
import re
import sys
from pathlib import Path


def _allowed(model: str, deny_patterns: list[re.Pattern[str]]) -> bool:
    return not any(pattern.search(model) for pattern in deny_patterns)


def select_model(
    available: list[str],
    opencode_go_api_key: str,
    opencode_go_2_api_key: str,
    openrouter_api_key: str,
    deny_list: Path = Path("scripts/model-deny-list.txt"),
) -> tuple[str, str]:
    patterns = [
        re.compile(line)
        for line in deny_list.read_text(encoding="utf-8").splitlines()
    ]
    unique_free_models = list(
        dict.fromkeys(
            model
            for model in available
            if re.fullmatch(r"(?:opencode|openrouter)/[^\s]+(?:-free|:free)", model)
            and _allowed(model, patterns)
        )
    )
    preferred = [
        "opencode-go-openai/qwen3.8-flash",
        "opencode-go-openai-2/qwen3.8-flash",
        "opencode/big-pickle",
        *unique_free_models,
    ]
    available_set = set(available)
    for candidate in preferred:
        if candidate not in available_set:
            continue
        if candidate == "opencode-go-openai/qwen3.8-flash" and not opencode_go_api_key:
            continue
        if candidate == "opencode-go-openai-2/qwen3.8-flash" and not opencode_go_2_api_key:
            continue
        if candidate.startswith("opencode/") and candidate != "opencode/big-pickle" and not candidate.endswith("-free"):
            continue
        if candidate.startswith("openrouter/") and (
            not openrouter_api_key or not candidate.endswith(("-free", ":free"))
        ):
            continue
        return candidate, "preferred list"

    fallback = next((model for model in available if _allowed(model, patterns)), "")
    if not fallback:
        raise ValueError("No refinement model is available; not dispatching.")
    return fallback, "last resort (deny-list filtered)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--available-models-file", required=True, type=Path)
    args = parser.parse_args()
    available = args.available_models_file.read_text(encoding="utf-8").splitlines()
    try:
        model, source = select_model(
            available,
            opencode_go_api_key=os.environ.get("OPENCODE_GO_API_KEY", ""),
            opencode_go_2_api_key=os.environ.get("OPENCODE_GO_2_API_KEY", ""),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if source != "preferred list":
        print(f"Using fallback model: {model}", file=sys.stderr)
    print(f"{model}\t{source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
