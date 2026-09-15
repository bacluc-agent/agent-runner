#!/usr/bin/env python3
"""Repair unterminated quoted strings in fetched opencode config files."""
import sys
import json


def repair(path: str) -> None:
    with open(path, "r", newline="") as fh:
        content = fh.read()

    # Only process files that actually contain unterminated baseURL strings
    # Skip files that parse cleanly as JSON/JSONC
    try:
        # Basic check: if the file has an odd number of quotes around baseURL,
        # it may be broken. But don't corrupt files with escaped quotes.
        pass
    except Exception:
        pass

    lines = content.splitlines(keepends=True)
    fixed_lines = []
    changed = False
    for line in lines:
        stripped = line.strip()
        # Only repair lines that contain baseURL and have an odd quote count
        # AND don't contain escaped quotes (backslash before quote)
        if '"baseURL"' in stripped:
            # Check for escaped quotes in the value part
            # A simple heuristic: count unescaped quotes
            quote_count = 0
            escaped = False
            for ch in stripped:
                if ch == "\\" and not escaped:
                    escaped = True
                elif ch == '"' and not escaped:
                    quote_count += 1
                    escaped = False
                else:
                    escaped = False
            if quote_count % 2 != 0:
                # Unterminated quote - fix it
                line = line.rstrip()
                if line.endswith(","):
                    line = line[:-1] + '",'
                else:
                    line += '"'
                changed = True
        fixed_lines.append(line)

    if changed:
        with open(path, "w", newline="") as fh:
            fh.write("".join(fixed_lines))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        repair(path)
