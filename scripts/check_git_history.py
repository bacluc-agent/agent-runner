#!/usr/bin/env python3
"""Reject agent branches with history that cannot be merged as-is."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


SUBJECT = re.compile(r"^(feat|fix|refactor|docs|test|chore|perf|build|ci|style|revert)(\([a-z0-9./-]+\))?: .+")
FOLLOWUP = re.compile(r"wip|fixup!|squash!|amend|address review|address feedback|address comments|follow[- ]up|oops|as requested|revert \"|cherry-pick|pushed fix|cleanup", re.I)


def git(repo: str, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def commits(repo: str, base: str, head: str) -> list[str]:
    return git(repo, "rev-list", "--reverse", f"{base}..{head}").splitlines()


def check_linear(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    return git(repo, "rev-list", "--merges", f"{base}..{head}").splitlines()


def check_fast_forward(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    result = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", base, head], capture_output=True)
    return [] if result.returncode == 0 else [head]


def patch_id(repo: str, sha: str) -> str:
    patch = subprocess.run(["git", "-C", repo, "show", sha, "--pretty=format:", "--binary"], capture_output=True, check=True).stdout
    return subprocess.run(["git", "patch-id", "--stable"], input=patch, capture_output=True, check=True).stdout.decode().split()[0] if patch.strip() else ""


def check_duplicate_patch(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    violations = []
    for sha in shas:
        value = patch_id(repo, sha)
        if value and value in seen:
            violations.append(sha)
        seen[value] = sha
    return violations


def check_already_upstream(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    upstream = git(repo, "rev-list", base).splitlines()
    values = {patch_id(repo, sha) for sha in upstream}
    return [sha for sha in shas if patch_id(repo, sha) and patch_id(repo, sha) in values]


def check_empty(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    return [sha for sha in shas if not git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)]


def check_subject_style(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    return [sha for sha in shas if (subject := git(repo, "show", "-s", "--format=%s", sha)) and (len(subject) > 72 or not SUBJECT.fullmatch(subject) or subject.endswith("…"))]


def check_no_followup(repo: str, base: str, head: str, shas: list[str]) -> list[str]:
    return [sha for sha in shas if (subject := git(repo, "show", "-s", "--format=%s", sha)) and (FOLLOWUP.search(subject) or subject.lower().startswith("agent-run: automated commit"))]


RULES = (("linear", check_linear), ("fast-forward", check_fast_forward), ("duplicate-patch", check_duplicate_patch), ("already-upstream", check_already_upstream), ("empty", check_empty), ("subject-style", check_subject_style), ("no-followup", check_no_followup))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check agent branch history against its base.", epilog="Rules: " + ", ".join(rule for rule, _ in RULES) + ".")
    parser.add_argument("--base", help="base ref (default: origin/HEAD, origin/main, or origin/devel)")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    try:
        base = args.base
        if not base:
            symbolic = git(args.repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False)
            base = symbolic or next((ref for ref in ("origin/main", "origin/devel") if git(args.repo, "rev-parse", "--verify", ref, check=False)), None)
            if not base:
                raise RuntimeError("could not determine base; pass --base")
        shas = commits(args.repo, base, args.head)
        violations = [(rule, sha) for rule, fn in RULES for sha in fn(args.repo, base, args.head, shas)]
        for rule, sha in violations:
            subject = git(args.repo, "show", "-s", "--format=%s", sha)
            print(f"{rule} {sha[:7]} {subject}")
        return int(bool(violations))
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"check-git-history: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
