#!/usr/bin/env python3
"""Refresh the opencode OpenAI (ChatGPT) OAuth credential.

Drives the browser through opencode's own OAuth flow:
  1. Generate PKCE verifier/challenge + state
  2. Start a localhost callback server on port 1455
  3. Open https://auth.openai.com/oauth/authorize (the same URL opencode uses)
  4. Automate login: email -> password -> 2FA -> consent
  5. Exchange the authorization code for tokens
  6. Write ~/.local/share/opencode/auth.json and print the auth JSON

Exit codes: 0 success, 1 setup/step failure, 2 blocked (captcha/device check).
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
ISSUER = "https://auth.openai.com"
CALLBACK_PORT = 1455
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/auth/callback"
AUTHORIZE_PATH = "/oauth/authorize"
TOKEN_PATH = "/oauth/token"
CALLBACK_PATH = "/auth/callback"

OTP_SELECTORS = [
    'input[name="otp"]',
    'input[inputmode="numeric"]',
    'input[autocomplete="one-time-code"]',
    'input[type="tel"]',
    'input[name="code"]',
    'input[data-testid*="otp"]',
    'input[data-testid*="code"]',
]

TWO_FA_TEXTS = ["Two-factor", "Two-factor authentication", "authenticator"]


def build_auth_json(access: str, refresh: str, expires: int) -> dict:
    if not isinstance(access, str) or not access:
        raise ValueError("access must be a non-empty string")
    if not isinstance(refresh, str) or not refresh:
        raise ValueError("refresh must be a non-empty string")
    if not isinstance(expires, int):
        raise ValueError("expires must be an int (millisecond epoch)")
    return {"openai": {"type": "oauth", "access": access, "refresh": refresh, "expires": expires}}


def write_auth_file(auth: dict, path: Path | None = None) -> Path:
    dest = path or Path.home() / ".local" / "share" / "opencode" / "auth.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(auth), encoding="utf-8")
    return dest


def _env(name: str, fallbacks: list[str]) -> str | None:
    val = os.environ.get(name)
    if val:
        return val
    for fb in fallbacks:
        v = os.environ.get(fb)
        if v:
            return v
    return None


def _is_headless() -> bool:
    return os.environ.get("CHATGPT_HEADLESS", "").lower() in ("1", "true")


_DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.92 Safari/537.36"
_DESKTOP_VIEWPORT = {"width": 1440, "height": 900}


def _launch_browser(p, headless: bool):
    args = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    try:
        return p.chromium.launch(headless=headless, channel="chrome", args=args)
    except Exception:
        return p.chromium.launch(headless=headless, args=args)


def _log_step(page, name: str) -> None:
    try:
        print(f"[chatgpt-login] step={name} url={page.url} title={page.title()}", file=sys.stderr)
    except Exception:
        print(f"[chatgpt-login] step={name} url=<unknown> title=<unknown>", file=sys.stderr)


def _dump_page_state(page) -> None:
    try:
        print(f"[chatgpt-login] failure url={page.url} title={page.title()}", file=sys.stderr)
    except Exception:
        print("[chatgpt-login] failure url=<unknown> title=<unknown>", file=sys.stderr)
    try:
        text = " ".join(page.inner_text("body").split())
        print(f"[chatgpt-login] body_text={text[:600]!r}", file=sys.stderr)
    except Exception:
        print("[chatgpt-login] body_text=<unavailable>", file=sys.stderr)


def _has_blocking_screen(page) -> str | None:
    checks = [
        ("Verify you are human", 'text="Verify you are human"'),
        ("captcha iframe", 'iframe[src*="captcha"]'),
        ("Checking your browser", 'text="Checking your browser"'),
        ("Verify your email", 'text="Verify your email"'),
        ("Check your email", 'text="Check your email"'),
        ("human verification", 'text="human verification"'),
        ("device verification", 'text="device verification"'),
    ]
    content = page.content().lower()
    if "captcha" in content or "human verification" in content or "device verification" in content:
        return "captcha/device verification detected"
    for label, sel in checks:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                return label
        except Exception:
            continue
    return None


def _wait_for_blocking_clear(page, timeout_s=60) -> str | None:
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            blocking = _has_blocking_screen(page)
        except Exception:
            blocking = "challenge in progress"
        if blocking is None:
            return None
        if time.monotonic() >= deadline:
            return blocking
        time.sleep(5)


def _click_first_visible(page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                loc.click()
                return True
        except Exception:
            continue
    return False


def _fill_first_visible(page, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                loc.fill(value)
                return True
        except Exception:
            continue
    return False


def _is_error_page(page) -> bool:
    try:
        title = page.title()
    except Exception:
        title = ""
    try:
        body = page.inner_text("body")
    except Exception:
        body = ""
    return "Oops, an error occurred" in title or "Oops, an error occurred" in body or "Route Error" in body


def _page_path(page) -> str:
    try:
        return urllib.parse.urlparse(page.url).path
    except Exception:
        return ""


def _generate_pkce() -> tuple[str, str]:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    verifier = "".join(secrets.choice(chars) for _ in range(43))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _authorize_url(verifier: str, state: str) -> str:
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email offline_access",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "state": state,
        "originator": "opencode",
    }
    return f"{ISSUER}{AUTHORIZE_PATH}?{urllib.parse.urlencode(params)}"


class _CallbackServer:
    """Localhost server that captures the OAuth authorization code."""

    def __init__(self, state: str):
        self.state = state
        self.code: str | None = None
        self.error: str | None = None
        self._server = http.server.HTTPServer(("localhost", CALLBACK_PORT), self._handler_factory())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def _handler_factory(self):
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                url = urllib.parse.urlparse(self.path)
                if url.path != CALLBACK_PATH:
                    self.send_response(404)
                    self.end_headers()
                    return
                qs = urllib.parse.parse_qs(url.query)
                if qs.get("state", [None])[0] != server.state:
                    server.error = "state mismatch"
                elif qs.get("error_description") or qs.get("error"):
                    server.error = (qs.get("error_description") or qs.get("error"))[0]
                else:
                    server.code = qs.get("code", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Success! You can close this window.</h1></body></html>")

            def log_message(self, *args):
                pass

        return Handler

    def start(self):
        self._thread.start()

    def wait(self, timeout_s=120) -> str | None:
        """Wait for the callback. Returns the code, or None on timeout/error."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.error:
                return None
            if self.code:
                return self.code
            time.sleep(0.5)
        return None

    def close(self):
        self._server.shutdown()
        self._server.server_close()


def _exchange_code(code: str, verifier: str) -> dict:
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(
        f"{ISSUER}{TOKEN_PATH}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "opencode/refresh"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _do_email_step(page, email: str) -> bool:
    if not _fill_first_visible(page, ['input[type="email"]', 'input[name="email"]', 'input[id="email"]'], email):
        return False
    return _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")'])


def _do_password_step(page, password: str) -> bool:
    if not _fill_first_visible(page, ['input[type="password"]'], password):
        return False
    return _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")'])


def _do_2fa_step(page, totp_key: str) -> bool:
    try:
        import pyotp

        code = pyotp.TOTP(totp_key).now()
    except ImportError:
        print("pyotp not installed; run pip install pyotp", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to generate TOTP: {e}", file=sys.stderr)
        return False
    if not _fill_first_visible(page, OTP_SELECTORS, code):
        return False
    return _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Verify")'])


def _do_consent_step(page) -> bool:
    return _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Allow")'])


def _do_choose_account_step(page) -> bool:
    return _click_first_visible(page, ['button[data-testid*="account"]', 'button:has-text("Select account")'])


def main() -> int:
    email = _env("CHATGPT_EMAIL", ["OPENAI_USERNAME"])
    password = _env("CHATGPT_PASSWORD", ["OPENAI_PASSWORD"])
    totp_key = _env("CHATGPT_2FA_KEY", ["OPENAI_2FA_KEY", "CHATGPT_TOTP_KEY"])

    if not email or not password:
        print("CHATGPT_EMAIL/OPENAI_USERNAME and CHATGPT_PASSWORD/OPENAI_PASSWORD must be set", file=sys.stderr)
        return 1

    verifier, _ = _generate_pkce()
    state = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

    callback = _CallbackServer(state)
    try:
        callback.start()
    except OSError as e:
        print(f"Failed to start callback server on port {CALLBACK_PORT}: {e}", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; run pip install playwright", file=sys.stderr)
        callback.close()
        return 1

    with sync_playwright() as p:
        try:
            browser = _launch_browser(p, _is_headless())
        except Exception as e:
            print(f"Failed to launch browser: {e}. If chrome is not installed, run: playwright install chrome", file=sys.stderr)
            callback.close()
            return 1
        context = browser.new_context(user_agent=_DESKTOP_UA, viewport=_DESKTOP_VIEWPORT)
        page = context.new_page()
        try:
            page.goto(_authorize_url(verifier, state), wait_until="domcontentloaded")
        except Exception as e:
            print(f"Failed to reach auth.openai.com: {e}", file=sys.stderr)
            browser.close()
            callback.close()
            return 1

        _log_step(page, "authorize")

        blocking = _has_blocking_screen(page)
        if blocking:
            print(f"Login blocked: {blocking} — cannot automate with credentials alone", file=sys.stderr)
            browser.close()
            callback.close()
            return 2

        # Drive the login state machine until the callback fires. Step
        # functions may "fail" even when the click worked (playwright raises
        # when the element detaches during navigation), so the loop just
        # re-checks the page state each iteration and only gives up when a
        # step makes no progress.
        deadline = time.monotonic() + 180
        last_step = ""
        attempts: dict[str, int] = {}
        while time.monotonic() < deadline:
            if callback.code or callback.error:
                break
            path = _page_path(page)
            step = {
                "/log-in-or-create-account": "email",
                "/log-in": "email",
                "/log-in/password": "password",
                "/mfa-challenge": "2fa",
                "/choose-an-account": "choose-account",
                "/sign-in-with-chatgpt": "consent",
            }.get(path, "")
            if step and step != last_step:
                _log_step(page, step)
                last_step = step
                attempts[step] = 0
            if step:
                attempts[step] = attempts.get(step, 0) + 1
                if attempts[step] > 5:
                    print(f"Stuck at step {step}", file=sys.stderr)
                    _dump_page_state(page)
                    browser.close()
                    callback.close()
                    return 1

            try:
                if path.startswith("/log-in") and "password" not in path:
                    _do_email_step(page, email)
                elif path == "/log-in/password":
                    _do_password_step(page, password)
                    # The SPA may show an error page; retry a couple of times.
                    for attempt in range(2):
                        blocking = _wait_for_blocking_clear(page, timeout_s=30)
                        if blocking:
                            print(f"Login blocked after password: {blocking}", file=sys.stderr)
                            browser.close()
                            callback.close()
                            return 2
                        if not _is_error_page(page):
                            break
                        print(f"[chatgpt-login] OpenAI error page after password submit, retry {attempt + 1}/2", file=sys.stderr)
                        time.sleep(2)
                        _click_first_visible(page, ['a:has-text("Try again")', 'button:has-text("Try again")'])
                        time.sleep(1)
                        _do_password_step(page, password)
                elif path.startswith("/mfa-challenge"):
                    if not totp_key:
                        print("2FA required but no TOTP key (CHATGPT_2FA_KEY/OPENAI_2FA_KEY/CHATGPT_TOTP_KEY) set", file=sys.stderr)
                        browser.close()
                        callback.close()
                        return 1
                    _do_2fa_step(page, totp_key)
                elif path == "/choose-an-account":
                    _do_choose_account_step(page)
                elif path.startswith("/sign-in-with-chatgpt"):
                    _do_consent_step(page)
                elif path == CALLBACK_PATH:
                    break
            except Exception as e:
                print(f"Failed at step {step or path}: {e}", file=sys.stderr)
                _dump_page_state(page)
                browser.close()
                callback.close()
                return 1

            time.sleep(1)

        code = callback.wait(timeout_s=10)
        if callback.error:
            print(f"OAuth callback error: {callback.error}", file=sys.stderr)
            browser.close()
            callback.close()
            return 1
        if not code:
            print("Timed out waiting for OAuth callback", file=sys.stderr)
            _dump_page_state(page)
            browser.close()
            callback.close()
            return 1

        _log_step(page, "callback")

        try:
            tokens = _exchange_code(code, verifier)
        except Exception as e:
            print(f"Token exchange failed: {e}", file=sys.stderr)
            browser.close()
            callback.close()
            return 1

        access = tokens.get("access_token", "")
        refresh = tokens.get("refresh_token", "")
        expires_in = tokens.get("expires_in", 3600)
        if not access or not refresh:
            print("Token exchange returned no access/refresh token", file=sys.stderr)
            browser.close()
            callback.close()
            return 1

        try:
            auth = build_auth_json(access, refresh, int(time.time() * 1000) + int(expires_in) * 1000)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            browser.close()
            callback.close()
            return 1

        write_auth_file(auth)
        json.dump(auth, sys.stdout)
        sys.stdout.write("\n")
        browser.close()
        callback.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())