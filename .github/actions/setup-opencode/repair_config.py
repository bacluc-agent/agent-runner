#!/usr/bin/env python3
"""Repair unterminated quoted strings in fetched opencode config files."""
import sys


def repair(path: str) -> None:
    with open(path, "r") as fh:
        lines = fh.read().splitlines()
    fixed = []
    for line in lines:
        stripped = line.strip()
        if '"baseURL"' in stripped and stripped.count('"') % 2 != 0:
            line = line.rstrip()
            if line.endswith(","):
                line = line[:-1] + '",'
            else:
                line += '"'
        fixed.append(line)
    with open(path, "w") as fh:
        fh.write("\n".join(fixed) + ("\n" if fixed else ""))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        try:
            repair(path)
        except Exception:
            pass
