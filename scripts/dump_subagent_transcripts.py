#!/usr/bin/env python3

import json
import os
import re
import secrets
import subprocess
import sys
import tempfile


def run_opencode(*args) -> str:
    env = dict(os.environ)
    return subprocess.run(
        ["opencode", *args], check=True, capture_output=True, text=True, env=env
    ).stdout


def export_to_json(session_id: str):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    size = 0
    try:
        with open(path, "w") as out:
            subprocess.run(
                ["opencode", "export", session_id],
                stdout=out,
                check=True,
                env=dict(os.environ),
            )
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            size = 0
        with open(path) as f:
            data = json.load(f)
        return data, size
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def compact_json(value) -> str:
    return json.dumps(value, separators=(",", ":"))


def as_text(value) -> str:
    return value if isinstance(value, str) else compact_json(value)


def trunc(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def render_transcript(session: dict, session_id: str, label: str = "Subagent transcript") -> list[str]:
    agent = (session.get("info") or {}).get("agent") or "subagent"
    lines = [f"--- {label}: {agent} ({session_id}) ---"]
    for message in session.get("messages") or []:
        for part in message.get("parts") or []:
            if part.get("type") == "text" and len(part.get("text") or "") > 0:
                lines.append(f"[{agent}] {part['text']}")
            elif part.get("type") == "tool" and (part.get("tool") or "") != "task":
                state = part.get("state") or {}
                line = f"[{agent}:tool] {part.get('tool') or 'unknown'} {trunc(compact_json(state.get('input') or {}), 200)}"
                output = state.get("output")
                if (
                    state.get("status") == "completed"
                    and output is not None
                    and len(as_text(output)) > 0
                ):
                    line += "\n  output: " + trunc(as_text(output), 500)
                lines.append(line)
    return lines


_MARKER_RE = re.compile(r"\[(Build|Refiner|Planner|Tester|Review) Agent\]")


def _inline_groups(root_export: dict) -> dict:
    groups: dict[str, list[dict]] = {}
    for message in root_export.get("messages") or []:
        msg_agent = (message.get("info") or {}).get("agent")
        for part in message.get("parts") or []:
            text = part.get("text") or ""
            part_agent = (part.get("info") or {}).get("agent")
            m = _MARKER_RE.search(text) if text else None
            agent = None
            if m:
                agent = m.group(1)
            elif part_agent and part_agent != "coordinator":
                agent = part_agent
            elif msg_agent and msg_agent != "coordinator":
                agent = msg_agent
            else:
                gm = re.search(r"\[([A-Za-z]+) Agent\]", text) if text else None
                if gm:
                    agent = gm.group(1)
                else:
                    continue
            groups.setdefault(agent, []).append({"parts": [part]})
    return groups


def child_session_ids(root_export: dict) -> list[str]:
    ids: set[str] = set()
    for message in root_export.get("messages") or []:
        for part in message.get("parts") or []:
            if part.get("type") == "tool" and part.get("tool") == "task":
                session_id = ((part.get("state") or {}).get("metadata") or {}).get("sessionId")
                if session_id:
                    ids.add(session_id)
    return sorted(ids)


def coordinator_session_id(sessions, title: str) -> str | None:
    for session in sessions:
        if session.get("title") == title:
            return session.get("id")
    return None


def main() -> int:
    title = os.environ.get("COORDINATOR_SESSION_TITLE", "coordinator-run")
    try:
        sessions = json.loads(run_opencode("session", "list", "--format", "json"))
        root_id = coordinator_session_id(sessions, title)
    except Exception as e:
        print(f"Failed to list sessions: {e}")
        sessions = []
        root_id = None
    if not root_id:
        print("No coordinator session found; skipping subagent transcripts.")
        return 0

    root_export = None
    root_size = 0
    child_ids: list[str] = []
    root_error: Exception | None = None
    try:
        root_export, root_size = export_to_json(root_id)
        child_ids = child_session_ids(root_export)
        session_ids = {s.get("id") for s in sessions if isinstance(s, dict)}
        child_ids = [cid for cid in child_ids if cid in session_ids]
    except json.JSONDecodeError as e:
        root_error = e
        root_export = None
        child_ids = []
    except subprocess.CalledProcessError as e:
        root_error = e
        root_export = None
        child_ids = []
    except Exception as e:
        root_error = e
        root_export = None
        child_ids = []

    token = secrets.token_hex(32)
    print(f"::stop-commands::{token}")

    if root_export is not None:
        for line in render_transcript(root_export, root_id, label="Coordinator transcript"):
            print(line)
    else:
        print("--- Coordinator transcript: export failed ---")
        if isinstance(root_error, json.JSONDecodeError):
            print(
                f"Diagnostics: searched title={title} root_id_found={bool(root_id)} sessions={len(sessions)} size={root_size} bytes error={root_error.msg} at {root_error.pos}"
            )
        elif root_error is not None:
            print(f"Export failed for {root_id}: {root_error}")
            print(
                f"Diagnostics: searched title={title} root_id_found={bool(root_id)} sessions={len(sessions)} size={root_size} bytes"
            )
        else:
            print(
                f"Diagnostics: searched title={title} root_id_found={bool(root_id)} sessions={len(sessions)} size={root_size} bytes"
            )

    if not child_ids:
        inline_groups = _inline_groups(root_export) if root_export is not None else {}
        if inline_groups:
            for agent, msgs in sorted(inline_groups.items()):
                pseudo = {"info": {"agent": agent}, "messages": msgs}
                for line in render_transcript(pseudo, "inline", label="Inline subagent transcript"):
                    print(line)
        else:
            print("(No subagents were spawned.)")
            if root_export is not None:
                msg_count = len(root_export.get("messages") or [])
                print(
                    f"Diagnostics: title={title} root_id={root_id} sessions={len(sessions)} messages={msg_count} size={root_size} bytes"
                )
            else:
                print(f"Diagnostics: title={title} root_id={root_id} sessions={len(sessions)} size={root_size} bytes")
    else:
        for child_id in child_ids:
            try:
                child_export, _child_size = export_to_json(child_id)
                for line in render_transcript(child_export, child_id):
                    print(line)
            except json.JSONDecodeError as e:
                print(
                    f"Child export JSON decode failed for {child_id}: {e.msg} at {e.pos}",
                )
                continue
            except subprocess.CalledProcessError:
                continue
            except Exception:
                continue

    print(f"::{token}::")
    return 0


if __name__ == "__main__":
    sys.exit(main())
