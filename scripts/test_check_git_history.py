import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from check_git_history import main


def git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(path: Path, subject: str, content: str | None = None) -> str:
    if content is not None:
        (path / "file.txt").write_text(content)
        git(path, "add", "file.txt")
    git(path, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-m", subject)
    return git(path, "rev-parse", "HEAD")


def repo() -> tuple[TemporaryDirectory, Path, str]:
    temporary = TemporaryDirectory()
    path = Path(temporary.name)
    git(path, "init", "-q", "-b", "main")
    commit(path, "chore: base", "base\n")
    base = git(path, "rev-parse", "HEAD")
    return temporary, path, base


def run(path: Path, base: str, *args: str) -> tuple[int, str]:
    import contextlib
    import io

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = main(["--repo", str(path), "--base", base, *args])
    return status, output.getvalue()


def test_clean_branch_and_explicit_range():
    temporary, path, base = repo()
    try:
        commit(path, "feat: first", "one\n")
        head = commit(path, "fix: second", "two\n")
        assert run(path, base, "--head", head) == (0, "")
    finally:
        temporary.cleanup()


def test_clean_branch_with_no_commits_is_fast_forward():
    temporary, path, base = repo()
    try:
        assert run(path, base) == (0, "")
    finally:
        temporary.cleanup()


@pytest.mark.parametrize("rule", ["linear", "fast-forward", "duplicate-patch", "already-upstream", "empty", "subject-style", "no-followup"])
def test_rejects_each_history_rule(rule):
    cases = {
        "linear": lambda path: (git(path, "checkout", "-q", "-b", "side"), commit(path, "feat: side", "side\n"), git(path, "checkout", "-q", "main"), subprocess.run(["git", "-C", str(path), "-c", "user.name=Test", "-c", "user.email=test@example.com", "merge", "--no-ff", "side", "-m", "merge"], check=True, capture_output=True)),
        "fast-forward": lambda path: (git(path, "branch", "base-ref"), git(path, "checkout", "-q", "-b", "diverged"), commit(path, "feat: side", "side\n"), git(path, "checkout", "-q", "base-ref"), commit(path, "feat: other", "other\n"), git(path, "checkout", "-q", "diverged")),
        "duplicate-patch": lambda path: (commit(path, "feat: first", "change\n"), commit(path, "feat: second", "base\n"), commit(path, "fix: repeated", "change\n")),
        "already-upstream": lambda path: (commit(path, "feat: upstream", "upstream\n"), git(path, "branch", "base-ref"), git(path, "reset", "--hard", "HEAD~1"), commit(path, "feat: repeated", "upstream\n")),
        "empty": lambda path: commit(path, "feat: empty"),
        "subject-style": lambda path: commit(path, "bad subject", "change\n"),
        "no-followup": lambda path: commit(path, "fix: address review", "change\n"),
    }
    temporary, path, base = repo()
    try:
        cases[rule](path)
        if rule in {"already-upstream", "fast-forward"}:
            base = "base-ref"
        status, output = run(path, base)
        assert status == 1, rule
        assert rule in output and ": " in output, (rule, output)
        assert output.strip().splitlines()[0].split(": ", 1)[1], output
    finally:
        temporary.cleanup()


def test_rejects_fallback_automated_commit_subject():
    temporary, path, base = repo()
    try:
        commit(path, "agent-run: automated commit", "change\n")
        status, output = run(path, base)
        assert status == 1 and "no-followup" in output
    finally:
        temporary.cleanup()


def test_help_lists_all_rule_ids():
    import contextlib
    import io

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            main(["--help"])
        except SystemExit as error:
            assert error.code == 0
    assert all(rule in output.getvalue() for rule in ("linear", "fast-forward", "duplicate-patch", "already-upstream", "empty", "subject-style", "no-followup"))
