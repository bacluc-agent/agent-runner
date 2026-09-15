"""Extract the /completion-check-command declaration from AGENTS.md.

Mirrors the parsing of the removed bacluc-opencode-completion-check-command
plugin (readDefaultCommandFromAgentsMd + parseCodeBlock): the first
occurrence of the marker, then the first fenced code block after it.
"""

import re
import sys

MARKER = "/completion-check-command"
CODE_BLOCK_RE = re.compile(r"(?:```|~~~)[a-zA-Z0-9_-]*\n([\s\S]*?)(?:```|~~~)")


def extract_completion_check_command(agents_md_path: str) -> str | None:
    try:
        with open(agents_md_path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None
    idx = content.find(MARKER)
    if idx == -1:
        return None
    match = CODE_BLOCK_RE.search(content[idx:])
    if match is None:
        return None
    return match.group(1).strip()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"usage: {argv[0]} OUTPUT_FILE", file=sys.stderr)
        return 2
    command = extract_completion_check_command("AGENTS.md")
    if command is None:
        return 0
    with open(argv[1], "w", encoding="utf-8") as f:
        f.write(command + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))