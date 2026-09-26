#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_COMMENT_BYTES = 65_000
WORKFLOWS = ("Hourly issue runner", "OpenCode agent", "Refine issues", "Review fixes runner", "CI")
MARKER = "<!-- run-history-report window={start}..{end} -->"


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso_time(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def api_json(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"gh api failed: {path}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"gh api returned invalid JSON: {error}") from error


def collect_runs(repo, since, until, pages=1000):
    runs = {}
    for page in range(1, pages + 1):
        path = f"repos/{repo}/actions/runs?per_page=100&page={page}"
        payload = api_json(path)
        page_runs = payload.get("workflow_runs")
        if not isinstance(page_runs, list):
            raise RuntimeError("GitHub API response lacks workflow_runs")
        for item in page_runs:
            created = parse_time(item["created_at"])
            if since <= created <= until and item.get("name") in WORKFLOWS:
                runs[str(item["id"])] = item
        if not page_runs or (page_runs and parse_time(page_runs[-1]["created_at"]) < since):
            break
    else:
        raise RuntimeError(f"reached pagination limit ({pages} pages)")
    return sorted(runs.values(), key=sort_key)


def sort_key(item):
    status = item.get("status")
    conclusion = item.get("conclusion")
    if status in {"queued", "in_progress", "waiting", "requested", "pending"}:
        group = 1
    elif conclusion == "success":
        group = 2
    else:
        group = 0
    return group, -parse_time(item["created_at"]).timestamp(), int(item["id"])


def escape(value):
    return str(value or "—").replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def duration(item):
    if not item.get("updated_at") or item.get("status") != "completed":
        return "—"
    seconds = max(0, int((parse_time(item["updated_at"]) - parse_time(item["created_at"])).total_seconds()))
    return f"{seconds // 3600:02}:{seconds % 3600 // 60:02}:{seconds % 60:02}"


def render_row(item):
    run_id = item["id"]
    actor = item.get("actor") or {}
    state = f"{item.get('status') or '—'}/{item.get('conclusion') or '—'}"
    return "| " + " | ".join(
        (
            f"[{run_id}](https://github.com/bacluc-agent/agent-runner/actions/runs/{run_id})",
            escape(item.get("name")),
            escape(item.get("event")),
            escape(item.get("head_branch")),
            escape(state),
            escape(iso_time(parse_time(item["created_at"]))),
            duration(item),
            escape(actor.get("login")),
        )
    ) + " |"


def render_report(runs, since, until, previous=None):
    start, end = iso_time(since), iso_time(until)
    failures = sum(1 for item in runs if item.get("conclusion") not in (None, "success"))
    previous_line = f"\nPrevious report: {previous}" if previous else ""
    header = (
        MARKER.format(start=start, end=end)
        + f"\n## Actions run history ({start} through {end}, inclusive)\n"
        + f"Rows: {len(runs)} · Failures: {failures} · Workflows: {', '.join(WORKFLOWS)}"
        + previous_line
        + "\n\n"
        + "| Run ID | Workflow | Event | Branch | Status/Conclusion | Created | Duration | Actor |\n"
        + "|---|---|---|---|---|---|---|---|\n"
    )
    return header + "\n".join(render_row(item) for item in runs) + "\n"


def chunk_report(header, rows, limit=MAX_COMMENT_BYTES):
    chunks, current = [], header
    if len(current.encode()) > limit:
        raise ValueError("report header exceeds GitHub comment limit")
    for row in rows:
        candidate = current + ("" if current.endswith("\n") else "\n") + row + "\n"
        if len(candidate.encode()) > limit and current != header:
            chunks.append(current)
            current = header + row + "\n"
        elif len(candidate.encode()) > limit:
            raise ValueError("report row exceeds GitHub comment limit")
        else:
            current = candidate
    if current != header or not chunks:
        chunks.append(current)
    return chunks


def comments(repo, issue):
    result = []
    for page in range(1, 1001):
        payload = api_json(f"repos/{repo}/issues/{issue}/comments?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise RuntimeError("GitHub API response for comments is not a list")
        result.extend(payload)
        if not payload:
            return result
    raise RuntimeError("reached comment pagination limit")


REPORT_RE = re.compile(r"<!-- run-history-report window=([0-9TZ:.-]+)\.\.([0-9TZ:.-]+) -->")
COMMENT_URL_RE = re.compile(r"issuecomment-(\d+)")


def previous_report(comment_list):
    reports = [item for item in comment_list if REPORT_RE.search(item.get("body", ""))]
    return max(reports, key=lambda item: item.get("created_at", ""), default=None)


def has_report_window(comment_list, since, until):
    marker = MARKER.format(start=iso_time(since), end=iso_time(until))
    return any(marker in item.get("body", "") for item in comment_list)


def post_chunks(repo, issue, chunks):
    posted = []
    path = Path(".run-history-comment.md")
    try:
        for chunk in chunks:
            path.write_text(chunk)
            result = subprocess.run(
                ["gh", "issue", "comment", str(issue), "-R", repo, "--body-file", str(path)],
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError("failed to post report comment")
            match = COMMENT_URL_RE.search(result.stdout)
            if not match:
                raise RuntimeError("posted report comment URL was not returned")
            posted.append(match.group(1))
    except RuntimeError:
        for comment_id in reversed(posted):
            subprocess.run(
                ["gh", "api", "--method", "DELETE", f"repos/{repo}/issues/{issue}/comments/{comment_id}"],
                capture_output=True,
                text=True,
            )
        raise
    finally:
        path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="bacluc-agent/agent-runner")
    parser.add_argument("--issue-repository", default="bacluc-agent/agent-todo")
    parser.add_argument("--issue", type=int, default=219)
    parser.add_argument("--now", help="UTC ISO timestamp for deterministic generation")
    parser.add_argument("--since", help="UTC ISO timestamp; defaults to previous end or seven days")
    parser.add_argument("--pages", type=int, default=1000)
    parser.add_argument("--post", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    until = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    comment_list = comments(args.issue_repository, args.issue)
    prior = previous_report(comment_list)
    previous_end = None
    if prior:
        match = REPORT_RE.search(prior["body"])
        if match:
            previous_end = parse_time(match.group(2))
    since = parse_time(args.since) if args.since else (previous_end or until - timedelta(days=7))
    if since > until:
        raise ValueError("since must not be after now")
    if args.post and has_report_window(comment_list=comment_list, since=since, until=until):
        return 0
    runs = collect_runs(args.repo, since, until, args.pages)
    full = render_report(runs, since, until, prior.get("html_url") if prior else None)
    separator = full.index("|---|")
    header_end = full.index("\n", separator) + 1
    header = full[:header_end]
    rows = [line for line in full[header_end:].splitlines() if line.startswith("|")]
    chunks = chunk_report(header, rows)
    if args.dry_run or not args.post:
        sys.stdout.write("\n\n".join(chunks))
        return 0
    post_chunks(args.issue_repository, args.issue, chunks)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError) as error:
        print(f"run-history: {error}", file=sys.stderr)
        raise SystemExit(1)
