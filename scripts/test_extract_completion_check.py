import subprocess
import sys
from pathlib import Path

import extract_completion_check_command as extract

AGENTS_MD = "AGENTS.md"


def write_agents_md(tmp_path: Path, content: str) -> Path:
    path = tmp_path / AGENTS_MD
    path.write_text(content, encoding="utf-8")
    return path


def test_no_marker_writes_no_file(tmp_path: Path) -> None:
    agents_md = write_agents_md(tmp_path, "# Repo\nNo declaration here.\n")
    assert extract.extract_completion_check_command(str(agents_md)) is None


def test_marker_with_bash_block_extracts_command(tmp_path: Path) -> None:
    agents_md = write_agents_md(
        tmp_path,
        "# Repo\n\n/completion-check-command\n\n```bash\n./scripts/completion-check\n```\n",
    )
    assert (
        extract.extract_completion_check_command(str(agents_md))
        == "./scripts/completion-check"
    )


def test_first_marker_occurrence_wins(tmp_path: Path) -> None:
    agents_md = write_agents_md(
        tmp_path,
        "See /completion-check-command in the docs.\n\n"
        "/completion-check-command\n\n```bash\n./scripts/real-check\n```\n",
    )
    assert (
        extract.extract_completion_check_command(str(agents_md))
        == "./scripts/real-check"
    )


def test_missing_agents_md_returns_none(tmp_path: Path) -> None:
    assert extract.extract_completion_check_command(str(tmp_path / AGENTS_MD)) is None


def test_cli_writes_output_file(tmp_path: Path) -> None:
    write_agents_md(
        tmp_path,
        "/completion-check-command\n\n```bash\n./scripts/completion-check\n```\n",
    )
    output = tmp_path / "command.txt"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent / "extract_completion_check_command.py"),
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert output.read_text(encoding="utf-8") == "./scripts/completion-check\n"