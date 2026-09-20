import json

import loop_metrics


class TestComputeMetrics:
    def test_convergence_rate_with_positive_delta(self):
        m = loop_metrics.compute_metrics(10, 2, "success", 0.05)
        assert m["step_count"] == 10
        assert m["token_cost_per_step"] == 0.05
        assert m["convergence_rate"] == 5  # 10 / 2
        assert m["failure_mode"] == "success"
        assert m["terminated_at"]

    def test_convergence_rate_with_zero_delta(self):
        m = loop_metrics.compute_metrics(10, 0)
        assert m["convergence_rate"] == 10  # falls back to steps

    def test_token_estimate_fallback(self):
        m = loop_metrics.compute_metrics(100, 1)
        assert m["token_cost_per_step"] == 0.05  # 100 * 0.0005

    def test_failure_modes(self):
        for mode in ("success", "max-steps", "error", "timeout", "unknown"):
            assert loop_metrics.compute_metrics(1, 1, mode)["failure_mode"] == mode


class TestEmitMetrics:
    def test_writes_summary_table_and_artifact(self, tmp_path):
        summary_path = str(tmp_path / "summary.md")
        artifact_path = str(tmp_path / "metrics.json")
        m = loop_metrics.compute_metrics(3, 1, "timeout")
        res = loop_metrics.emit_metrics(m, summary_path, artifact_path)
        assert "timeout" in res["summary"]
        assert res["artifact"] == artifact_path
        assert "timeout" in open(summary_path).read()
        with open(artifact_path) as f:
            assert json.load(f)["step_count"] == 3


class TestMain:
    def test_reads_existing_artifact_and_writes_only_output(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        artifact = {"step_count": 5, "failure_mode": "max-steps"}
        with open("loop-metrics.json", "w") as f:
            json.dump(artifact, f)
        output_path = tmp_path / "output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
        monkeypatch.setenv("LOOP_STEPS", "0")
        monkeypatch.setenv("LOOP_FAILURE_MODE", "unknown")

        assert loop_metrics.main() == 0

        with open(output_path) as f:
            assert f.read() == f"metrics={json.dumps(artifact)}\n"
        # The summary table was already appended by the tool; do not duplicate it.
        assert not (tmp_path / "summary.md").exists()
        # The artifact is not rewritten.
        with open("loop-metrics.json") as f:
            assert json.load(f) == artifact

    def test_emits_from_env_when_no_artifact(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "summary.md"
        output_path = tmp_path / "output.txt"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
        monkeypatch.setenv("LOOP_STEPS", "7")
        monkeypatch.setenv("LOOP_PROGRESS_DELTA", "2")
        monkeypatch.setenv("LOOP_FAILURE_MODE", "success")
        monkeypatch.setenv("LOOP_TOKEN_ESTIMATE", "0.02")

        assert loop_metrics.main() == 0

        assert "| Steps | 7 |" in summary_path.read_text()
        with open("loop-metrics.json") as f:
            artifact = json.load(f)
        assert artifact["step_count"] == 7
        assert artifact["failure_mode"] == "success"
        with open(output_path) as f:
            assert f"metrics={json.dumps(artifact)}\n" in f.read()