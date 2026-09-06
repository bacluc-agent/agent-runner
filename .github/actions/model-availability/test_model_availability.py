import json
import types
from datetime import datetime, timezone

import model_availability


CONFIG = {
    "provider": {
        "opencode-go-openai": {"options": {"baseURL": "https://opencode.ai/zen/go/v1"}},
        "opencode-go-anthropic": {"options": {"baseURL": "https://opencode.ai/zen/go/v1/messages"}},
    }
}


def fake_run(args, *a, **kw):
    if args == ["opencode", "models"]:
        return types.SimpleNamespace(stdout="opencode/a-free\n")
    if args == ["opencode", "debug", "config"]:
        return types.SimpleNamespace(stdout=json.dumps(CONFIG))
    raise AssertionError(f"unexpected args: {args}")


class TestDiscoverModels:
    def test_discovers_models_per_provider(self, monkeypatch):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"data": [{"id": "glm-5.2"}]}'

        def fake_urlopen(request, timeout=30):
            captured["headers"] = request.headers
            captured["full_url"] = request.full_url
            return FakeResponse()

        monkeypatch.setattr(model_availability.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(model_availability.subprocess, "run", fake_run)
        free_models, provider_models = model_availability.discover_models()
        assert free_models == ["opencode/a-free"]
        assert provider_models == {
            "opencode-go-openai": ["glm-5.2"],
            "opencode-go-anthropic": ["glm-5.2"],
        }
        assert captured["headers"]["User-agent"] == "curl/8.5.0"
        assert not any("Python-urllib" in v for v in captured["headers"].values())
        assert any(k.lower() == "x-opencode-session" for k in captured["headers"])
        assert captured["full_url"].endswith("/models")

    def test_endpoint_failure_per_provider(self, monkeypatch):
        def fail(request, timeout=30):
            raise RuntimeError("403 Forbidden")

        monkeypatch.setattr(model_availability.urllib.request, "urlopen", fail)
        monkeypatch.setattr(model_availability.subprocess, "run", fake_run)
        free_models, provider_models = model_availability.discover_models()
        assert free_models == ["opencode/a-free"]
        assert provider_models == {
            "opencode-go-openai": [],
            "opencode-go-anthropic": [],
        }

    def test_missing_baseurl_per_provider(self, monkeypatch):
        config = {
            "provider": {
                "opencode-go-openai": {"options": {"baseURL": "https://opencode.ai/zen/go/v1"}},
            }
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"data": [{"id": "glm-5.2"}]}'

        def fake_run_missing(args, *a, **kw):
            if args == ["opencode", "models"]:
                return types.SimpleNamespace(stdout="opencode/a-free\n")
            if args == ["opencode", "debug", "config"]:
                return types.SimpleNamespace(stdout=json.dumps(config))
            raise AssertionError(f"unexpected args: {args}")

        monkeypatch.setattr(
            model_availability.urllib.request, "urlopen", lambda *a, **kw: FakeResponse()
        )
        monkeypatch.setattr(model_availability.subprocess, "run", fake_run_missing)
        free_models, provider_models = model_availability.discover_models()
        assert free_models == ["opencode/a-free"]
        assert provider_models == {"opencode-go-openai": ["glm-5.2"]}

    def test_config_read_failure(self, monkeypatch):
        def fail_config(args, *a, **kw):
            if args == ["opencode", "models"]:
                return types.SimpleNamespace(stdout="opencode/a-free\n")
            raise RuntimeError("opencode failed")

        monkeypatch.setattr(model_availability.subprocess, "run", fail_config)
        free_models, provider_models = model_availability.discover_models()
        assert free_models == ["opencode/a-free"]
        assert provider_models == {}


class TestParseFreeModels:
    def test_extracts_free_models(self):
        output = (
            "opencode/big-pickle\n"
            "opencode/ling-3.0-flash-fin-free\n"
            "opencode/mimo-v2.5-free\n"
            "custom-provider/other-free\n"
            "custom-provider/big-pickle\n"
            "standalone-free\n"
            "big-pickle\n"
            "opencode/paid-model\n"
            "other/paid-model\n"
        )
        assert model_availability.parse_free_models(output) == [
            "big-pickle",
            "custom-provider/big-pickle",
            "custom-provider/other-free",
            "opencode/big-pickle",
            "opencode/ling-3.0-flash-fin-free",
            "opencode/mimo-v2.5-free",
            "standalone-free",
        ]

    def test_deduplicates(self):
        assert model_availability.parse_free_models("opencode/a-free\nopencode/a-free\n") == [
            "opencode/a-free"
        ]


class TestParseGoModelIds:
    def test_extracts_and_deduplicates_ids(self):
        data = json.dumps(
            {"data": [{"id": "glm-5.2"}, {"id": "qwen3.8-flash"}, {"id": "glm-5.2"}]}
        )
        assert model_availability.parse_go_model_ids(data) == ["glm-5.2", "qwen3.8-flash"]

    def test_invalid_json_returns_empty(self):
        assert model_availability.parse_go_model_ids("not json") == []


class TestBuildCandidates:
    def test_skips_providers_without_api_key(self):
        env = {"OPENCODE_GO_API_KEY": "key1"}
        assert model_availability.build_candidates(
            ["opencode/a-free"],
            {"opencode-go-openai": ["glm-5.2"], "opencode-go-anthropic": ["glm-5.2"]},
            env,
        ) == [
            "opencode-go-openai/glm-5.2",
            "opencode-go-anthropic/glm-5.2",
            "opencode/a-free",
        ]

    def test_free_models_last(self):
        env = {"OPENCODE_GO_API_KEY": "key1", "OPENCODE_GO_2_API_KEY": "key2"}
        candidates = model_availability.build_candidates(
            ["opencode/a-free"],
            {
                "opencode-go-openai": ["glm-5.2"],
                "opencode-go-openai-2": ["glm-5.2"],
                "opencode-go-anthropic": ["glm-5.2"],
                "opencode-go-anthropic-2": ["glm-5.2"],
            },
            env,
        )
        assert candidates[-1] == "opencode/a-free"
        assert len(candidates) == 5

    def test_provider_models_are_not_crossed(self):
        env = {"OPENCODE_GO_API_KEY": "key1", "OPENCODE_GO_2_API_KEY": "key2"}
        provider_models = {
            "opencode-go-openai": ["x"],
            "opencode-go-openai-2": ["y"],
        }
        assert model_availability.build_candidates([], provider_models, env) == [
            "opencode-go-openai/x",
            "opencode-go-openai-2/y",
        ]


class TestIsCacheFresh:
    def test_fresh_available(self):
        now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        entry = {"ok": True, "checked": "2026-09-06T10:00:00Z"}
        assert model_availability.is_cache_fresh(entry, now)

    def test_expired_available(self):
        now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        entry = {"ok": True, "checked": "2026-09-06T10:00:00Z"}
        assert not model_availability.is_cache_fresh(entry, now)

    def test_fresh_failed(self):
        now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        entry = {"ok": False, "checked": "2026-09-06T11:00:00Z"}
        assert model_availability.is_cache_fresh(entry, now)

    def test_expired_failed(self):
        now = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
        entry = {"ok": False, "checked": "2026-09-06T11:00:00Z"}
        assert not model_availability.is_cache_fresh(entry, now)

    def test_missing_or_malformed_entry(self):
        now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        assert not model_availability.is_cache_fresh(None, now)
        assert not model_availability.is_cache_fresh({"ok": "yes"}, now)
        assert not model_availability.is_cache_fresh({"ok": True}, now)


class TestMergeResults:
    def test_merges_and_overwrites(self):
        cache = {"opencode/a-free": {"ok": True, "checked": "old"}}
        results = {"opencode/a-free": False, "opencode-go-openai/glm-5.2": True}
        assert model_availability.merge_results(cache, results, "2026-09-06T12:00:00Z") == {
            "opencode/a-free": {"ok": False, "checked": "2026-09-06T12:00:00Z"},
            "opencode-go-openai/glm-5.2": {"ok": True, "checked": "2026-09-06T12:00:00Z"},
        }


class TestAvailableModels:
    def test_paid_before_free(self):
        cache = {
            "opencode-go-openai/glm-5.2": {"ok": True, "checked": "x"},
            "opencode/a-free": {"ok": True, "checked": "x"},
            "opencode/b-free": {"ok": False, "checked": "x"},
            "opencode-go-openai-2/glm-5.2": {"ok": True, "checked": "x"},
        }
        assert model_availability.available_models(
            cache,
            ["opencode/a-free", "opencode/b-free"],
            {"opencode-go-openai": ["glm-5.2"], "opencode-go-openai-2": ["glm-5.2"]},
        ) == [
            "opencode-go-openai/glm-5.2",
            "opencode-go-openai-2/glm-5.2",
            "opencode/a-free",
        ]

    def test_priority_models_first_across_providers(self):
        cache = {
            "opencode-go-openai/glm-5.3": {"ok": True, "checked": "x"},
            "opencode-go-openai-2/glm-5.3": {"ok": True, "checked": "x"},
            "opencode-go-openai/qwen3.8-max": {"ok": True, "checked": "x"},
            "opencode-go-openai-2/kimi-k3": {"ok": True, "checked": "x"},
            "opencode-go-openai/glm-5.2": {"ok": True, "checked": "x"},
            "opencode/a-free": {"ok": True, "checked": "x"},
        }
        assert model_availability.available_models(
            cache,
            ["opencode/a-free"],
            ["glm-5.2", "glm-5.3", "qwen3.8-max", "kimi-k3"],
        ) == [
            "opencode-go-openai/glm-5.3",
            "opencode-go-openai-2/glm-5.3",
            "opencode-go-openai/qwen3.8-max",
            "opencode-go-openai-2/kimi-k3",
            "opencode-go-openai/glm-5.2",
            "opencode/a-free",
        ]

    def test_falls_back_to_free_when_no_paid_available(self):
        cache = {"opencode/a-free": {"ok": True, "checked": "x"}}
        assert model_availability.available_models(
            cache, ["opencode/a-free"], []
        ) == ["opencode/a-free"]

    def test_priority_model_missing_from_go_model_ids_is_skipped(self):
        cache = {
            "opencode-go-openai/glm-5.3": {"ok": True, "checked": "x"},
            "opencode-go-openai/glm-5.2": {"ok": True, "checked": "x"},
        }
        assert model_availability.available_models(
            cache, [], ["glm-5.2"]
        ) == ["opencode-go-openai/glm-5.2"]


class TestReadCache:
    def test_reads_issue_body(self, monkeypatch):
        monkeypatch.setattr(
            model_availability,
            "run_gh",
            lambda *args: '{"opencode/a-free": {"ok": true, "checked": "x"}}',
        )
        assert model_availability.read_cache() == {
            "opencode/a-free": {"ok": True, "checked": "x"}
        }

    def test_returns_empty_on_failure(self, monkeypatch):
        def fail(*args):
            raise RuntimeError("gh failed")

        monkeypatch.setattr(model_availability, "run_gh", fail)
        assert model_availability.read_cache() == {}


class TestWriteCache:
    def test_writes_issue_body(self, monkeypatch):
        calls = []

        def fake_run_gh(*args):
            calls.append(args)

        monkeypatch.setattr(model_availability, "run_gh", fake_run_gh)
        model_availability.write_cache({"a": 1})
        assert calls == [("issue", "edit", "49", "--body", '{"a": 1}')]

    def test_swallows_failure(self, monkeypatch):
        def fail(*args):
            raise RuntimeError("gh failed")

        monkeypatch.setattr(model_availability, "run_gh", fail)
        model_availability.write_cache({"a": 1})


class TestModelsEndpointFor:
    def test_openai_style(self):
        assert (
            model_availability.models_endpoint_for("https://opencode.ai/zen/go/v1")
            == "https://opencode.ai/zen/go/v1/models"
        )

    def test_anthropic_style(self):
        assert (
            model_availability.models_endpoint_for("https://opencode.ai/zen/go/v1/messages")
            == "https://opencode.ai/zen/go/v1/models"
        )

    def test_trailing_slash(self):
        assert (
            model_availability.models_endpoint_for("https://opencode.ai/zen/go/v1/")
            == "https://opencode.ai/zen/go/v1/models"
        )
        assert (
            model_availability.models_endpoint_for("https://opencode.ai/zen/go/v1/messages/")
            == "https://opencode.ai/zen/go/v1/models"
        )


class TestLoadProviderBaseUrls:
    def test_returns_base_urls(self, monkeypatch):
        config = {
            "provider": {
                "opencode-go-openai": {"options": {"baseURL": "https://opencode.ai/zen/go/v1"}},
                "opencode-go-anthropic": {"options": {"baseURL": "https://opencode.ai/zen/go/v1/messages"}},
                "no-base-url": {"options": {}},
            }
        }
        monkeypatch.setattr(
            model_availability.subprocess,
            "run",
            lambda *args, **kwargs: types.SimpleNamespace(stdout=json.dumps(config)),
        )
        assert model_availability.load_provider_base_urls() == {
            "opencode-go-openai": "https://opencode.ai/zen/go/v1",
            "opencode-go-anthropic": "https://opencode.ai/zen/go/v1/messages",
        }

    def test_returns_empty_on_failure(self, monkeypatch):
        def fail(*args, **kwargs):
            raise RuntimeError("opencode failed")

        monkeypatch.setattr(model_availability.subprocess, "run", fail)
        assert model_availability.load_provider_base_urls() == {}


class TestProbeModelLogging:
    def test_writes_probe_log_with_stdout_and_stderr(self, tmp_path, monkeypatch):
        class FakeResult:
            returncode = 0
            stdout = "OK\n"
            stderr = "debug: loaded model\n"

        monkeypatch.setattr(
            model_availability.subprocess, "run", lambda *args, **kwargs: FakeResult()
        )
        assert (
            model_availability.probe_model("opencode-go-openai/glm-5.2", str(tmp_path))
            is True
        )
        log = tmp_path / "model-probes" / "probe-opencode-go-openai-glm-5.2.log"
        assert log.read_text() == "OK\ndebug: loaded model\n"

    def test_writes_probe_log_even_when_probe_fails(self, tmp_path, monkeypatch):
        class FakeResult:
            returncode = 1
            stdout = "model unavailable\n"
            stderr = ""

        monkeypatch.setattr(
            model_availability.subprocess, "run", lambda *args, **kwargs: FakeResult()
        )
        assert model_availability.probe_model("opencode/a-free", str(tmp_path)) is False
        log = tmp_path / "model-probes" / "probe-opencode-a-free.log"
        assert log.read_text() == "model unavailable\n"


class TestDiscoverModelsLogging:
    def test_writes_opencode_models_log(self, tmp_path, monkeypatch):
        class FakeResult:
            stdout = "opencode/a-free\nopencode/big-pickle\n"
            stderr = ""

        class FakeResponse:
            def read(self):
                return b'{"data": []}'

        def fake_run_logging(args, *a, **kw):
            if args == ["opencode", "models"]:
                return types.SimpleNamespace(stdout=FakeResult.stdout, stderr=FakeResult.stderr)
            if args == ["opencode", "debug", "config"]:
                return types.SimpleNamespace(stdout=json.dumps(CONFIG))
            raise AssertionError(f"unexpected args: {args}")

        monkeypatch.setattr(model_availability.subprocess, "run", fake_run_logging)
        monkeypatch.setattr(
            model_availability.urllib.request,
            "urlopen",
            lambda *args, **kwargs: FakeResponse(),
        )
        monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
        free_models, provider_models = model_availability.discover_models()
        assert free_models == ["opencode/a-free", "opencode/big-pickle"]
        assert provider_models == {
            "opencode-go-openai": [],
            "opencode-go-anthropic": [],
        }
        log = tmp_path / "model-probes" / "opencode-models.log"
        assert log.read_text() == "opencode/a-free\nopencode/big-pickle\n"
