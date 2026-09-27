import run_status


def test_success_outcome():
    assert run_status.classify("success", "0", "0", "") == "✅ completed"


def test_fatal_reason_beats_exit_code():
    assert run_status.classify("failure", "124", "0", "retry_limit") == "❌ fatal error: retry_limit"


def test_success_beats_fatal_reason():
    assert run_status.classify("success", "0", "0", "auth") == "✅ completed"


def test_completed_coordinator_with_failing_tee_is_completed():
    assert run_status.classify("failure", "0", "2", "") == "✅ completed (log capture failed, tee exit 2)"


def test_timeout():
    assert run_status.classify("failure", "124", "0", "") == "⏱️ timed out (coordinator exit 124)"


def test_other_nonzero_exit():
    assert run_status.classify("failure", "1", "0", "") == "⚠️ failed (coordinator exit 1)"


def test_cancelled():
    assert run_status.classify("cancelled", "", "", "") == "⚠️ cancelled before the coordinator finished"


def test_missing_exit_codes_keep_origin_main_wording():
    assert run_status.classify("failure", "", "", "") == "⚠️ failed (coordinator exit failure)"


def test_main_reads_env(monkeypatch, capsys):
    monkeypatch.setenv("COORDINATOR_OUTCOME", "failure")
    monkeypatch.setenv("COORDINATOR_STATUS", "124")
    monkeypatch.setenv("COORDINATOR_TEE_STATUS", "0")
    monkeypatch.setenv("FATAL_REASON", "")
    assert run_status.main() == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "⏱️ timed out (coordinator exit 124)"
    assert (
        captured.err.strip()
        == "run_status: outcome='failure' status='124' tee='0' fatal='' -> ⏱️ timed out (coordinator exit 124)"
    )
