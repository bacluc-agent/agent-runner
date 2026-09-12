import json
import subprocess
import types
from datetime import datetime, timezone

import model_availability


CONFIG = {
    "provider": {
        "opencode-go-openai": {"options": {"baseURL": "https://opencode.ai/zen/go/v1"}},
        "opencode-go-anthropic": {"options": {"baseURL": "https://opencode.ai/zen/go/v1/messages"}},
        "openrouter": {"options": {"baseURL": "https://openrouter.ai/api/v1"}},
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
            "openrouter": ["glm-5.2"],
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
            "openrouter": [],
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

    def test_filters_openrouter_models_by_whitelist(self, monkeypatch):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                if captured["full_url"].startswith("https://openrouter.ai"):
                    return b'{"data": [{"id": "deepseek/deepseek-chat-v3.1"}, {"id": "zai/GLM-4.5"}, {"id": "qwen/qwen3-8b"}, {"id": "anthropic/claude-sonnet-4.5"}, {"id": "cohere/north-mini-code:free"}]}'
                return b'{"data": [{"id": "deepseek/deepseek-chat-v3.1"}]}'

        def fake_urlopen(request, timeout=30):
            captured["full_url"] = request.full_url
            return FakeResponse()

        monkeypatch.setattr(model_availability.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(model_availability.subprocess, "run", fake_run)
        free_models, provider_models = model_availability.discover_models()
        assert provider_models["openrouter"] == [
            "cohere/north-mini-code:free",
            "qwen/qwen3-8b",
            "zai/GLM-4.5",
        ]
        assert provider_models["opencode-go-openai"] == ["deepseek/deepseek-chat-v3.1"]
        assert ("openrouter", "OPENROUTER_API_KEY") in model_availability.PROVIDERS


EXAMPLE_OPENCODE_WHITELIST = [r"(?:-|:)free$", r"big-pickle", r"glm", r"gpt-5\.6-luna", r"qwen", r"kimi"]

class TestParseWhitelistedModels:
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
            "opencode-go-openai/glm-5.3\n"
            "opencode-go-openai/qwen3.8-flash\n"
            "opencode-go-openai/kimi-k3\n"
            "opencode-go-openai/gpt-5.6-luna\n"
            "openrouter/zai/GLM-4.5\n"
            "openrouter/deepseek/deepseek-chat-v3.1\n"
            "openrouter/anthropic/claude-sonnet-4.5\n"
            "openrouter/cohere/north-mini-code:free\n"
            "openrouter/google/gemma-4-31b-it:free\n"
        )
        assert model_availability.parse_whitelisted_models(
            output, EXAMPLE_OPENCODE_WHITELIST
        ) == [
            "big-pickle",
            "custom-provider/big-pickle",
            "custom-provider/other-free",
            "opencode/big-pickle",
            "opencode/ling-3.0-flash-fin-free",
            "opencode/mimo-v2.5-free",
            "openrouter/cohere/north-mini-code:free",
            "openrouter/google/gemma-4-31b-it:free",
            "standalone-free",
            "opencode-go-openai/glm-5.3",
            "opencode-go-openai/gpt-5.6-luna",
            "opencode-go-openai/kimi-k3",
            "opencode-go-openai/qwen3.8-flash",
            "openrouter/zai/GLM-4.5",
        ]

    def test_deduplicates(self):
        assert model_availability.parse_whitelisted_models(
            "opencode/a-free\nopencode/a-free\n",
            EXAMPLE_OPENCODE_WHITELIST,
        ) == ["opencode/a-free"]

    def test_free_first_then_whitelisted(self):
        assert model_availability.parse_whitelisted_models(
            "opencode/glm-5.3\nopencode/z-free\n",
            EXAMPLE_OPENCODE_WHITELIST,
        ) == ["opencode/z-free", "opencode/glm-5.3"]

    def test_case_insensitive_matching(self):
        assert model_availability.parse_whitelisted_models(
            "openrouter/zai/GLM-4.5\n",
            EXAMPLE_OPENCODE_WHITELIST,
        ) == ["openrouter/zai/GLM-4.5"]


class TestIsWhitelisted:
    def test_matches_case_insensitively(self):
        assert model_availability.is_whitelisted("zai/GLM-4.5", ["glm"])
        assert model_availability.is_whitelisted("qwen/qwen3-8b", ["qwen"])

    def test_no_match(self):
        patterns = EXAMPLE_OPENCODE_WHITELIST
        assert not model_availability.is_whitelisted("deepseek/deepseek-chat-v3.1", patterns)
        assert not model_availability.is_whitelisted("anthropic/claude-sonnet-4.5", patterns)

    def test_free_pattern_is_anchored(self):
        assert model_availability.is_whitelisted("a-free", ["(?:-|:)free$"])
        assert model_availability.is_whitelisted("a:free", ["(?:-|:)free$"])
        assert not model_availability.is_whitelisted("free", ["(?:-|:)free$"])

    def test_empty_patterns_match_nothing(self):
        assert not model_availability.is_whitelisted("anything", [])

    def test_workflow_referenced_models_match(self):
        patterns = EXAMPLE_OPENCODE_WHITELIST
        for model in [
            "opencode/big-pickle",
            "opencode-go-openai/qwen3.8-flash",
            "opencode-go-openai/glm-5.3",
            "opencode-go-openai/kimi-k3",
            "opencode-go-openai/gpt-5.6-luna",
        ]:
            assert model_availability.is_whitelisted(model, patterns)
        assert not model_availability.is_whitelisted("deepseek/deepseek-chat-v3.1", patterns)
        assert not model_availability.is_whitelisted("anthropic/claude-sonnet-4.5", patterns)

    def test_openrouter_free_models_match(self):
        patterns = model_availability.PROVIDER_WHITELISTS["openrouter"]
        for model in [
            "cohere/north-mini-code:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-3.5-lightning:free",
            "thinkingmachines/inkling:free",
        ]:
            assert model_availability.is_whitelisted(model, patterns)
        assert not model_availability.is_whitelisted("deepseek/deepseek-chat-v3.1", patterns)
        assert not model_availability.is_whitelisted("anthropic/claude-sonnet-4.5", patterns)


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

    def test_deduplicates_overlapping_models(self):
        env = {"OPENCODE_GO_API_KEY": "key1"}
        assert model_availability.build_candidates(
            ["opencode-go-openai/glm-5.2", "opencode/a-free"],
            {"opencode-go-openai": ["glm-5.2"]},
            env,
        ) == ["opencode-go-openai/glm-5.2", "opencode/a-free"]


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
        entry = {"ok": False, "checked": "2026-09-05T11:00:00Z"}  # 28h gap > 24h TTL
        assert not model_availability.is_cache_fresh(entry, now)

    def test_missing_or_malformed_entry(self):
        now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        assert not model_availability.is_cache_fresh(None, now)
        assert not model_availability.is_cache_fresh({"ok": "yes"}, now)
        assert not model_availability.is_cache_fresh({"ok": True}, now)


class TestCandidatePriority:
    def test_big_pickle_first(self):
        assert model_availability.candidate_priority("opencode/big-pickle") == 0
        assert model_availability.candidate_priority("big-pickle") == 0

    def test_qwen_flash_second(self):
        assert model_availability.candidate_priority("opencode-go-openai/qwen3.8-flash") == 1
        assert model_availability.candidate_priority("opencode-go-openai-2/qwen3.8-flash") == 1

    def test_opencode_free_before_openrouter_free(self):
        assert model_availability.candidate_priority("opencode/a-free") == 2
        assert model_availability.candidate_priority("openrouter/zai/GLM-4.5:free") == 3

    def test_opencode_paid(self):
        assert model_availability.candidate_priority("opencode/paid-model") == 4

    def test_go_openai_providers(self):
        assert model_availability.candidate_priority("opencode-go-openai/glm-5.3") == 5
        assert model_availability.candidate_priority("opencode-go-openai-2/glm-5.3") == 5

    def test_go_anthropic_providers(self):
        assert model_availability.candidate_priority("opencode-go-anthropic/glm-5.3") == 6
        assert model_availability.candidate_priority("opencode-go-anthropic-2/glm-5.3") == 6

    def test_openrouter_paid_and_custom_provider_last(self):
        assert model_availability.candidate_priority("openrouter/anthropic/claude-sonnet-4.5") == 7
        assert model_availability.candidate_priority("custom-provider/other-free") == 7


class TestPrioritizeCandidates:
    def test_sorts_by_priority(self):
        candidates = [
            "openrouter/anthropic/claude-sonnet-4.5",
            "opencode-go-openai/qwen3.8-flash",
            "opencode/a-free",
            "opencode/big-pickle",
        ]
        assert model_availability.prioritize_candidates(candidates) == [
            "opencode/big-pickle",
            "opencode-go-openai/qwen3.8-flash",
            "opencode/a-free",
            "openrouter/anthropic/claude-sonnet-4.5",
        ]

    def test_stable_within_same_priority(self):
        candidates = ["opencode-go-openai/glm-5.3", "opencode-go-openai-2/kimi-k3"]
        assert model_availability.prioritize_candidates(candidates) == candidates


class TestSelectPending:
    def test_stale_highest_priority_first(self):
        now = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
        cache = {
            "opencode/big-pickle": {"ok": False, "checked": "2026-09-05T11:00:00Z"},
            "opencode/a-free": {"ok": False, "checked": "2026-09-05T11:00:00Z"},
            "openrouter/anthropic/claude-sonnet-4.5": {"ok": False, "checked": "2026-09-05T11:00:00Z"},
        }
        pending, skipped = model_availability.select_pending(
            list(cache), cache, now
        )
        assert pending == [
            "opencode/big-pickle",
            "opencode/a-free",
            "openrouter/anthropic/claude-sonnet-4.5",
        ]
        assert skipped == 0

    def test_skips_fresh_entries(self):
        now = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
        cache = {
            "opencode/big-pickle": {"ok": True, "checked": "2026-09-06T10:00:00Z"},
            "opencode/a-free": {"ok": False, "checked": "2026-09-05T11:00:00Z"},
        }
        pending, skipped = model_availability.select_pending(list(cache), cache, now)
        assert pending == ["opencode/a-free"]
        assert skipped == 0

    def test_caps_at_probe_budget(self):
        now = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
        stale = {
            f"opencode-go-openai/model-{i}": {"ok": False, "checked": "2026-09-05T11:00:00Z"}
            for i in range(model_availability.PROBE_BUDGET + 10)
        }
        pending, skipped = model_availability.select_pending(list(stale), stale, now)
        assert len(pending) == model_availability.PROBE_BUDGET
        assert skipped == 10


class TestProbeBudgetCoversCritical:
    def test_budget_covers_workflow_critical_models(self):
        assert model_availability.PROBE_BUDGET >= 28


class TestMergeResults:
    def test_merges_and_overwrites(self):
        cache = {"opencode/a-free": {"ok": True, "checked": "old"}}
        results = {"opencode/a-free": False, "opencode-go-openai/glm-5.2": True}
        assert model_availability.merge_results(cache, results, "2026-09-06T12:00:00Z") == {
            "opencode/a-free": {"ok": False, "checked": "2026-09-06T12:00:00Z"},
            "opencode-go-openai/glm-5.2": {"ok": True, "checked": "2026-09-06T12:00:00Z"},
        }


class TestAvailableModels:
    def test_free_first_then_paid(self):
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
            "opencode/a-free",
            "opencode-go-openai/glm-5.2",
            "opencode-go-openai-2/glm-5.2",
        ]


class TestResolveCacheIssue:
    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("MODEL_AVAILABILITY_CACHE_ISSUE", "7")
        monkeypatch.setenv("ISSUE_REPOSITORY", "bacluc-agent/agent-todo")
        calls = []

        def fake_run_gh(*args):
            calls.append(args)

        monkeypatch.setattr(model_availability, "run_gh", fake_run_gh)
        assert model_availability.resolve_cache_issue() == "7"
        assert calls == []

    def test_auto_detect_by_title(self, monkeypatch):
        monkeypatch.delenv("MODEL_AVAILABILITY_CACHE_ISSUE", raising=False)
        monkeypatch.setenv("ISSUE_REPOSITORY", "bacluc-agent/agent-todo")
        calls = []

        def fake_run_gh(*args):
            calls.append(args)
            return "3\n"

        monkeypatch.setattr(model_availability, "run_gh", fake_run_gh)
        assert model_availability.resolve_cache_issue() == "3"
        assert calls == [
            (
                "api",
                "search/issues?q=repo:bacluc-agent/agent-todo+is:issue+in:title+%22model-discovery+cache%22",
                "--jq",
                ".items[0].number // empty",
            )
        ]

    def test_no_repo_returns_none(self, monkeypatch, capsys):
        monkeypatch.delenv("MODEL_AVAILABILITY_CACHE_ISSUE", raising=False)
        monkeypatch.delenv("ISSUE_REPOSITORY", raising=False)
        assert model_availability.resolve_cache_issue() is None
        assert "warning: ISSUE_REPOSITORY not set" in capsys.readouterr().err

    def test_search_failure_returns_none(self, monkeypatch, capsys):
        monkeypatch.delenv("MODEL_AVAILABILITY_CACHE_ISSUE", raising=False)
        monkeypatch.setenv("ISSUE_REPOSITORY", "bacluc-agent/agent-todo")

        def fail(*args):
            raise RuntimeError("gh failed")

        monkeypatch.setattr(model_availability, "run_gh", fail)
        assert model_availability.resolve_cache_issue() is None
        assert "warning: failed to auto-detect the cache issue" in capsys.readouterr().err


class TestReadCache:
    def test_reads_issue_body(self, monkeypatch):
        monkeypatch.setattr(
            model_availability,
            "run_gh",
            lambda *args: '{"opencode/a-free": {"ok": true, "checked": "x"}}',
        )
        assert model_availability.read_cache("49") == {
            "opencode/a-free": {"ok": True, "checked": "x"}
        }

    def test_returns_empty_on_failure(self, monkeypatch):
        def fail(*args):
            raise RuntimeError("gh failed")

        monkeypatch.setattr(model_availability, "run_gh", fail)
        assert model_availability.read_cache("49") == {}


class TestWriteCache:
    def test_writes_issue_body(self, monkeypatch):
        calls = []

        def fake_run_gh(*args):
            calls.append(args)

        monkeypatch.setattr(model_availability, "run_gh", fake_run_gh)
        model_availability.write_cache("49", {"a": 1})
        assert calls == [("issue", "edit", "49", "--body", '{"a": 1}')]

    def test_warns_on_failure(self, monkeypatch, capsys):
        def fail(*args):
            raise RuntimeError("gh failed")

        monkeypatch.setattr(model_availability, "run_gh", fail)
        model_availability.write_cache("49", {"a": 1})
        assert "warning: failed to write cache issue 49" in capsys.readouterr().err

    def test_warns_when_body_exceeds_limit(self, monkeypatch, capsys):
        calls = []

        def fake_run_gh(*args):
            calls.append(args)

        monkeypatch.setattr(model_availability, "run_gh", fake_run_gh)
        model_availability.write_cache("49", {"x": "a" * 70000})
        assert calls == []
        err = capsys.readouterr().err
        assert "warning: cache body is" in err
        assert str(model_availability.GITHUB_ISSUE_BODY_LIMIT) in err


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

    def test_writes_timeout_marker(self, tmp_path, monkeypatch):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=30)

        monkeypatch.setattr(model_availability.subprocess, "run", timeout)
        assert model_availability.probe_model("opencode/a-free", str(tmp_path)) is False
        log = tmp_path / "model-probes" / "probe-opencode-a-free.log"
        assert log.read_text() == "TIMEOUT after 30s\n"


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
            "openrouter": [],
        }
        log = tmp_path / "model-probes" / "opencode-models.log"
        assert log.read_text() == "opencode/a-free\nopencode/big-pickle\n"


class TestRunGhRepoInjection:
    def test_injects_repo_when_set(self, monkeypatch):
        monkeypatch.setenv("ISSUE_REPOSITORY", "bacluc-agent/agent-todo")
        captured = {}

        def fake_run(args, *a, **kw):
            captured["args"] = args
            return types.SimpleNamespace(stdout="")

        monkeypatch.setattr(model_availability.subprocess, "run", fake_run)
        model_availability.run_gh("issue", "view", "49")
        assert captured["args"][:3] == ["gh", "-R", "bacluc-agent/agent-todo"]
        assert captured["args"][3:] == ["issue", "view", "49"]

    def test_no_repo_when_unset(self, monkeypatch):
        monkeypatch.delenv("ISSUE_REPOSITORY", raising=False)
        captured = {}

        def fake_run(args, *a, **kw):
            captured["args"] = args
            return types.SimpleNamespace(stdout="")

        monkeypatch.setattr(model_availability.subprocess, "run", fake_run)
        model_availability.run_gh("issue", "view", "49")
        assert captured["args"] == ["gh", "issue", "view", "49"]


class TestOpencodeWhitelist:
    def test_matches_openrouter_patterns(self):
        assert (
            model_availability.PROVIDER_WHITELISTS["opencode"]
            == model_availability.PROVIDER_WHITELISTS["openrouter"]
        )

    def test_free_and_whitelisted_models_pass(self):
        patterns = model_availability.PROVIDER_WHITELISTS["opencode"]
        for model in ["opencode/a-free", "opencode/big-pickle", "opencode/qwen3.8-flash"]:
            assert model_availability.is_whitelisted(model, patterns)
        assert not model_availability.is_whitelisted("opencode/some-paid-model", patterns)


class TestMainProbeSummary:
    def test_prints_probe_outcome_summary(self, monkeypatch, capsys):
        monkeypatch.setattr(model_availability, "resolve_cache_issue", lambda: None)
        monkeypatch.setattr(
            model_availability, "discover_models", lambda: (["opencode/a-free"], {})
        )
        monkeypatch.setattr(
            model_availability, "build_candidates", lambda *args: ["opencode/a-free"]
        )
        monkeypatch.setattr(
            model_availability, "select_pending", lambda *args: (["opencode/a-free"], 0)
        )
        monkeypatch.setattr(
            model_availability, "probe_candidates", lambda *args: {"opencode/a-free": True}
        )
        monkeypatch.setattr(model_availability, "write_outputs", lambda *args: None)
        assert model_availability.main() == 0
        assert "probe results: 1 ok, 0 failed" in capsys.readouterr().out


class TestDiscoveryTimeout:
    def test_discovery_timeout_is_bounded(self):
        assert model_availability.DISCOVERY_TIMEOUT_SECONDS <= 120
