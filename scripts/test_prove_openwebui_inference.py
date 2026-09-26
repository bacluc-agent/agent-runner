import io
import urllib.error
from email.message import Message
from typing import Any, cast

import prove_openwebui_inference as prove


class TestExtractText:
    def test_happy_path(self) -> None:
        payload: dict[str, Any] = {"choices": [{"message": {"role": "assistant", "content": "Blue."}}]}
        assert prove.extract_text(payload) == "Blue."

    def test_empty_completion(self) -> None:
        assert prove.extract_text({"choices": [{"message": {"content": ""}}]}) == ""

    def test_response_without_choices(self) -> None:
        assert prove.extract_text({"error": {"message": "nope"}}) == ""

    def test_choices_without_message_uses_text(self) -> None:
        assert prove.extract_text({"choices": [{"text": " Blue. "}]}) == "Blue."

    def test_strips_surrounding_whitespace(self) -> None:
        payload = {"choices": [{"message": {"content": "  Blue.\n"}}]}
        assert prove.extract_text(payload) == "Blue."


class TestRequest:
    def test_http_error_status_is_reported_with_body(self, monkeypatch: Any) -> None:
        def fake_urlopen(req: Any, timeout: Any = None) -> Any:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", cast(Message, {}), io.BytesIO(b'{"error": "slow down"}'))

        monkeypatch.setattr(prove.urllib.request, "urlopen", fake_urlopen)
        status, payload = prove.request("POST", "http://example.invalid", {"a": 1})
        assert status == 429
        assert payload == {"error": "slow down"}

    def test_non_json_body_is_kept_raw(self, monkeypatch: Any) -> None:
        class FakeResponse(io.BytesIO):
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *exc: Any) -> None:
                return None

        monkeypatch.setattr(prove.urllib.request, "urlopen", lambda req, timeout=None: FakeResponse(b"not json"))
        status, payload = prove.request("GET", "http://example.invalid")
        assert status == 200
        assert payload == {"_raw": "not json"}

    def test_connection_refused_is_a_status_not_an_exception(self, monkeypatch: Any) -> None:
        def fake_urlopen(req: Any, timeout: Any = None) -> Any:
            raise urllib.error.URLError(ConnectionRefusedError("Connection refused"))

        monkeypatch.setattr(prove.urllib.request, "urlopen", fake_urlopen)
        status, payload = prove.request("GET", "http://example.invalid", timeout=1)
        assert status == 0
        assert "Connection refused" in payload["_error"]


class TestWaitReady:
    def test_retries_until_ready(self, monkeypatch: Any) -> None:
        statuses = [0, 0, 200]
        monkeypatch.setattr(prove, "request", lambda *a, **k: (statuses.pop(0), {}))
        monkeypatch.setattr(prove.time, "sleep", lambda seconds: None)
        assert prove.wait_ready("http://example.invalid/readyz") is True
        assert statuses == []

    def test_gives_up_after_the_attempt_budget(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(prove, "request", lambda *a, **k: (0, {}))
        monkeypatch.setattr(prove.time, "sleep", lambda seconds: None)
        assert prove.wait_ready("http://example.invalid/readyz", attempts=3) is False
