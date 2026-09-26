from datetime import datetime, timezone

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


def test_chunk_report_is_byte_limited_and_reconstructable():
    rows = [run_history.render_row(run(index, "2026-09-20T00:00:00Z")) for index in range(1000)]
    chunks = run_history.chunk_report("header\n", rows, limit=200)

    assert len(chunks) > 1
    assert all(len(chunk.encode()) <= 200 for chunk in chunks)
    assert "\n".join(chunks).count("https://github.com/bacluc-agent/agent-runner/actions/runs/") == 1000
