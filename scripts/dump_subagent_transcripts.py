#!/usr/bin/env python3

import json
import os
import secrets
import subprocess
import sys
import tempfile


def run_opencode(*args) -> str:
    env = dict(os.environ)
    return subprocess.run(
        ["opencode", *args], check=True, capture_output=True, text=True, env=env
    ).stdout


def run_opencode_to_file(*args, path: str) -> None:
    result = run_opencode(*args)
    with open(path, "w") as f:
        f.write(result)


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


AGENT_LABELS = {
    "[Build Agent]",
    "[Refiner Agent]",
    "[Planner Agent]",
    "[Tester Agent]",
    "[Review Agent]",
}


def child_session_ids(root_export: dict) -> list[str]:
    ids = set()

    def walk(node):
        if isinstance(node, dict):
            if node.get("tool") == "task":
                session_id = ((node.get("state") or {}).get("metadata") or {}).get(
                    "sessionId"
                )
                if session_id:
                    ids.add(session_id)
            # Inspect info/agent fields for session references
            info = node.get("info") or {}
            agent = info.get("agent")
            if agent and isinstance(agent, str) and agent.startswith("ses_"):
                ids.add(agent)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    # Walk full export for task metadata session IDs
    walk(root_export)

    # Also inspect messages/parts for agent info and inline markers
    for message in root_export.get("messages") or []:
        msg_info = message.get("info") or {}
        msg_agent = msg_info.get("agent")
        if msg_agent and isinstance(msg_agent, str) and msg_agent.startswith("ses_"):
            ids.add(msg_agent)
        for part in message.get("parts") or []:
            part_info = part.get("info") or {}
            part_agent = part_info.get("agent")
            if part_agent and isinstance(part_agent, str) and part_agent.startswith("ses_"):
                ids.add(part_agent)
            # Fallback: text markers that reference agent names (not session IDs)
            text = part.get("text") or ""
            for label in AGENT_LABELS:
                if label in text:
                    # Inline agent segment detected; no separate session ID
                    pass

    return sorted(ids)


def inline_agent_segments(root_export: dict) -> list[tuple[str, dict]]:
    """Extract inline subagent segments from coordinator transcript.
    Returns list of (agent_name, pseudo_session_dict) for rendering.
    # ponytail: inline segment extraction; upgrade to structured session refs if needed
    """
    segments = []
    for message in root_export.get("messages") or []:
        msg_info = message.get("info") or {}
        msg_agent = msg_info.get("agent")
        agent_name = msg_agent if msg_agent else None
        # Fallback: detect agent from text markers in parts
        for part in message.get("parts") or []:
            text = part.get("text") or ""
            for label in AGENT_LABELS:
                if label in text:
                    agent_name = label.strip("[]")
                    break
            if agent_name and not msg_agent:
                # Build pseudo-session from this message's parts
                pseudo = {
                    "info": {"agent": agent_name},
                    "messages": [{"parts": message.get("parts", [])}],
                }
                segments.append((agent_name, pseudo))
        if agent_name and msg_agent and not any(s[0] == agent_name for s in segments):
            pseudo = {
                "info": {"agent": agent_name},
                "messages": [{"parts": message.get("parts", [])}],
            }
            segments.append((agent_name, pseudo))
    # Deduplicate by agent name, keep first
    seen = set()
    deduped = []
    for agent_name, pseudo in segments:
        if agent_name not in seen:
            seen.add(agent_name)
            deduped.append((agent_name, pseudo))
    return deduped


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
    except Exception:
        root_id = None
    if not root_id:
        print("No coordinator session found; skipping subagent transcripts.")
        return 0

    # Fix A + B: temp-file export with graceful truncation diagnostics
    root_export = None
    root_export_size = 0
    root_tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            root_tmp_path = tmp.name
        run_opencode_to_file("export", root_id, path=root_tmp_path)
        root_export_size = os.path.getsize(root_tmp_path)
        with open(root_tmp_path) as f:
            root_export = json.load(f)
    except json.JSONDecodeError as e:
        print(f"COORDINATOR_SESSION_TITLE={title} found={root_id is not None} total_sessions={len(sessions) if isinstance(sessions, list) else 'N/A'} root_export_bytes={root_export_size} last_valid_index=N/A error={e}", file=sys.stderr)
        root_export = None
    except Exception as e:
        print(f"COORDINATOR_SESSION_TITLE={title} found={root_id is not None} total_sessions={len(sessions) if isinstance(sessions, list) else 'N/A'} root_export_bytes={root_export_size if root_tmp_path else 0} error={e}", file=sys.stderr)
        root_export = None
    finally:
        if root_tmp_path and os.path.exists(root_tmp_path):
            try:
                os.unlink(root_tmp_path)
            except OSError:
                pass

    child_ids = []
    if root_export is not None:
        try:
            child_ids = child_session_ids(root_export)
        except Exception as e:
            print(f"Child session ID extraction failed: {e}", file=sys.stderr)
            child_ids = []

    # child_ids are taken as-is; render attempt will gracefully skip missing exports

    token = secrets.token_hex(32)
    print(f"::stop-commands::{token}")

    if root_export is not None:
        for line in render_transcript(root_export, root_id, label="Coordinator transcript"):
            print(line)
    else:
        print("--- Coordinator transcript: export failed ---")

    # Fix C: render inline agent segments when no separate child IDs exist
    inline_segments = []
    if root_export is not None:
        inline_segments = inline_agent_segments(root_export)

    if not child_ids and not inline_segments:
        print("(No subagents were spawned.)")
    else:
        for child_id in child_ids:
            child_tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                    child_tmp_path = tmp.name
                run_opencode_to_file("export", child_id, path=child_tmp_path)
                with open(child_tmp_path) as f:
                    child_export = json.load(f)
                for line in render_transcript(child_export, child_id):
                    print(line)
            except Exception:
                continue
            finally:
                if child_tmp_path and os.path.exists(child_tmp_path):
                    try:
                        os.unlink(child_tmp_path)
                    except OSError:
                        pass

        # Render inline segments from coordinator transcript
        for agent_name, pseudo in inline_segments:
            pseudo_id = f"inline-{agent_name.lower().replace(' ', '-')}-segment"
            for line in render_transcript(pseudo, pseudo_id, label=f"Inline agent segment: {agent_name}"):
                print(line)

    # Fix D: diagnostics when root_export is None or no child_ids
    if root_export is None:
        print(f"COORDINATOR_SESSION_TITLE={title} found={root_id is not None} total_sessions={len(sessions) if isinstance(sessions, list) else 'N/A'} root_export_bytes={root_export_size if root_tmp_path else 0} messages=N/A")
    elif not child_ids:
        msg_count = len(root_export.get("messages", [])) if isinstance(root_export, dict) else 0
        print(f"COORDINATOR_SESSION_TITLE={title} found={root_id is not None} total_sessions={len(sessions) if isinstance(sessions, list) else 'N/A'} root_export_bytes={root_export_size if root_tmp_path else 0} messages={msg_count}")

    print(f"::{token}::")
    return 0


if __name__ == "__main__":
    sys.exit(main())
