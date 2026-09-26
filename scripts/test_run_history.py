from datetime import datetime, timezone

import json
import subprocess

import run_history


def run(run_id, created, *, name="CI", status="completed", conclusion="success", updated=None):
    return {
        "id": run_id,
        "name": name,
        "event": "push",
        "head_branch": "main",
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "updated_at": updated or created,
        "actor": {"login": "octocat"},
    }


def test_collect_runs_paginates_deduplicates_and_keeps_inclusive_window(monkeypatch):
    pages = [
        {"workflow_runs": [run(3, "2026-09-21T00:00:00Z"), run(1, "2026-09-20T00:00:00Z")]},
        {"workflow_runs": [run(1, "2026-09-20T00:00:00Z"), run(2, "2026-09-19T23:59:59Z")]},
    ]

    def fake_api(path):
        return pages.pop(0)

    monkeypatch.setattr(run_history, "api_json", fake_api)
    result = run_history.collect_runs(
        "bacluc-agent/agent-runner",
        datetime(2026, 9, 20, tzinfo=timezone.utc),
        datetime(2026, 9, 21, tzinfo=timezone.utc),
        pages=2,
    )

    assert [item["id"] for item in result] == [3, 1]


def test_render_has_required_columns_order_and_escaped_values():
    item = run(
        42,
        "2026-09-20T00:00:00Z",
        name="CI | nightly",
        conclusion="failure",
        updated="2026-09-20T00:01:02Z",
    )
    body = run_history.render_report(
        [item],
        datetime(2026, 9, 20, tzinfo=timezone.utc),
        datetime(2026, 9, 21, tzinfo=timezone.utc),
        previous=None,
    )

    assert "<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->" in body
    assert "| Run ID | Workflow | Event | Branch | Status/Conclusion | Created | Duration | Actor |" in body
    assert "[42](https://github.com/bacluc-agent/agent-runner/actions/runs/42)" in body
    assert "CI \\| nightly" in body
    assert "00:01:02" in body
    assert body.index("| Run ID") < body.index("| [42]")


def test_post_report_rejects_oversized_body_before_mutation(monkeypatch):
    def fail_run(*args, **kwargs):
        raise AssertionError("GitHub API must not be called")

    monkeypatch.setattr(run_history.subprocess, "run", fail_run)

    try:
        run_history.post_report("bacluc-agent/agent-todo", 219, "x" * (run_history.MAX_COMMENT_BYTES + 1), [])
    except ValueError as error:
        assert str(error) == "report exceeds GitHub comment limit"
    else:
        raise AssertionError("post_report should reject oversized reports")


def test_post_report_updates_the_lowest_id_matching_window(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "{}", "")

    monkeypatch.setattr(run_history.subprocess, "run", fake_run)
    comments = [
        {"id": 20, "body": "<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->"},
        {"id": 10, "body": "<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->"},
    ]

    body = "<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->\nreport"
    run_history.post_report("bacluc-agent/agent-todo", 219, body, comments)

    assert calls == [["gh", "api", "--method", "PATCH", "repos/bacluc-agent/agent-todo/issues/comments/10", "--input", "-"]]


def test_post_report_creates_one_comment_from_stdin(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "{}", "")

    monkeypatch.setattr(run_history.subprocess, "run", fake_run)

    run_history.post_report("bacluc-agent/agent-todo", 219, "report", [])

    assert calls[0][0] == ["gh", "api", "--method", "POST", "repos/bacluc-agent/agent-todo/issues/219/comments", "--input", "-"]
    assert json.loads(calls[0][1]["input"]) == {"body": "report"}


def test_post_report_surfaces_api_failure_without_follow_up_mutation(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", "controlled failure")

    monkeypatch.setattr(run_history.subprocess, "run", fake_run)

    try:
        run_history.post_report("bacluc-agent/agent-todo", 219, "report", [])
    except RuntimeError as error:
        assert str(error) == "failed to create report comment: controlled failure"
    else:
        raise AssertionError("post_report should surface API failures")

    assert len(calls) == 1


def test_matching_report_uses_the_lowest_comment_id():
    since = datetime(2026, 9, 20, tzinfo=timezone.utc)
    until = datetime(2026, 9, 21, tzinfo=timezone.utc)
    comments = [
        {"id": 20, "body": "<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->"},
        {"id": 10, "body": "<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->"},
    ]

    assert run_history.matching_report(comments, since, until)["id"] == 10


def test_report_window_reads_the_marker():
    assert run_history.report_window("<!-- run-history-report window=2026-09-20T00:00:00Z..2026-09-21T00:00:00Z -->") == (
        datetime(2026, 9, 20, tzinfo=timezone.utc),
        datetime(2026, 9, 21, tzinfo=timezone.utc),
    )
