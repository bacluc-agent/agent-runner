from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from select_refinement_model import select_model


def test_selection_preserves_preference_filtering_fallback_and_duplicates():
    available = [
        "openrouter/first-free",
        "opencode/nemotron-free",
        "openrouter/first-free",
        "opencode/big-pickle",
        "provider/fallback",
    ]
    with TemporaryDirectory() as directory:
        deny_list = Path(directory) / "deny-list.txt"
        deny_list.write_text("/nemotron-\n")
        assert select_model(available, "", "", "", deny_list) == (
            "opencode/big-pickle",
            "preferred list",
        )
        assert select_model(
            ["openrouter/first-free", "opencode/nemotron-free"],
            "",
            "",
            "openrouter-key",
            deny_list,
        ) == (
            "openrouter/first-free",
            "preferred list",
        )
        assert select_model(["provider/fallback", "provider/fallback"], "", "", "", deny_list) == (
            "provider/fallback",
            "last resort (deny-list filtered)",
        )


def test_provider_credentials_are_required_and_empty_selection_fails():
    go = "opencode-go-openai/qwen3.8-flash"
    go_two = "opencode-go-openai-2/qwen3.8-flash"
    with TemporaryDirectory() as directory:
        deny_list = Path(directory) / "deny-list.txt"
        deny_list.write_text("/never-matches/\n")
        assert select_model([go, go_two], "", "go-two-key", "", deny_list)[0] == go_two
        assert select_model([go], "go-key", "", "", deny_list)[0] == go
        with pytest.raises(ValueError, match="No refinement model is available"):
            select_model(["opencode/nemotron-free"], "", "", "", Path("scripts/model-deny-list.txt"))
