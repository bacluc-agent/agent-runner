import json
import os
import sys
import time
from pathlib import Path

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


def _submit_password_with_retry(page, password) -> str | None:
    """Submit the password, retrying on the OpenAI error page. Returns a blocking label or None."""

    def submit() -> str | None:
        page.locator('input[type="password"]:visible').first.wait_for(timeout=15000)
        page.locator('input[type="password"]:visible').first.fill(password)
        _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Log in")'])
        return _wait_for_blocking_clear(page)

    blocking = submit()
    if blocking:
        return blocking
    for attempt in range(2):
        if not _is_error_page(page):
            return None
        print(f"[chatgpt-login] OpenAI error page after password submit, retry {attempt + 1}/2", file=sys.stderr)
        time.sleep(2)
        _click_first_visible(page, ['a:has-text("Try again")', 'button:has-text("Try again")'])
        try:
            page.locator('input[type="password"]:visible').first.wait_for(timeout=15000)
        except Exception:
            return None
        blocking = submit()
        if blocking:
            return blocking
    return None


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
    try:
        for inp in page.locator("input").all():
            try:
                print(
                    "[chatgpt-login] input "
                    f"type={inp.get_attribute('type')} name={inp.get_attribute('name')} "
                    f"id={inp.get_attribute('id')} autocomplete={inp.get_attribute('autocomplete')} "
                    f"visible={inp.is_visible()}",
                    file=sys.stderr,
                )
            except Exception:
                continue
    except Exception:
        print("[chatgpt-login] inputs=<unavailable>", file=sys.stderr)


def main() -> int:
    email = _env("CHATGPT_EMAIL", ["OPENAI_USERNAME"])
    password = _env("CHATGPT_PASSWORD", ["OPENAI_PASSWORD"])
    totp_key = _env("CHATGPT_2FA_KEY", ["OPENAI_2FA_KEY", "CHATGPT_TOTP_KEY"])

    if not email or not password:
        print("CHATGPT_EMAIL/OPENAI_USERNAME and CHATGPT_PASSWORD/OPENAI_PASSWORD must be set", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; run pip install playwright", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        try:
            browser = _launch_browser(p, _is_headless())
        except Exception as e:
            print(f"Failed to launch browser: {e}. If chromium is not installed, run: playwright install chromium", file=sys.stderr)
            return 1
        context = browser.new_context(user_agent=_DESKTOP_UA, viewport=_DESKTOP_VIEWPORT)
        page = context.new_page()
        try:
            page.goto("https://chatgpt.com/auth/login", wait_until="domcontentloaded")
        except Exception as e:
            print(f"Failed to reach chatgpt.com: {e}", file=sys.stderr)
            browser.close()
            return 1

        _log_step(page, "goto")

        blocking = _has_blocking_screen(page)
        if blocking:
            print(f"Login blocked: {blocking} — cannot automate with credentials alone", file=sys.stderr)
            browser.close()
            return 2

        try:
            page.locator('input[type="email"]').first.wait_for(timeout=30000)
            page.locator('input[type="email"]').first.fill(email)
            # Continue button: prefer the real submit button; the social login
            # buttons ("Continue with Google/Apple/phone") are type=button.
            _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")'])
            blocking = _wait_for_blocking_clear(page)
            if blocking:
                print(f"Login blocked after email: {blocking}", file=sys.stderr)
                browser.close()
                return 2
            _log_step(page, "email")
        except Exception as e:
            print(f"Failed at email step: {e}", file=sys.stderr)
            browser.close()
            return 1

        try:
            blocking = _submit_password_with_retry(page, password)
            if blocking:
                print(f"Login blocked after password: {blocking}", file=sys.stderr)
                browser.close()
                return 2
            _log_step(page, "password")
        except Exception as e:
            print(f"Failed at password step: {e}", file=sys.stderr)
            browser.close()
            return 1

        # 2FA handling
        otp_loc = None
        for sel in OTP_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=3000):
                    otp_loc = loc
                    break
            except Exception:
                continue
        # also text detection
        needs_2fa = otp_loc is not None
        if not needs_2fa:
            for txt in TWO_FA_TEXTS:
                try:
                    if page.locator(f'text="{txt}"').first.is_visible(timeout=2000):
                        needs_2fa = True
                        break
                except Exception:
                    continue

        if needs_2fa:
            if not totp_key:
                print("2FA required but no TOTP key (CHATGPT_2FA_KEY/OPENAI_2FA_KEY/CHATGPT_TOTP_KEY) set", file=sys.stderr)
                browser.close()
                return 1
            try:
                import pyotp

                code = pyotp.TOTP(totp_key).now()
            except ImportError:
                print("pyotp not installed; run pip install pyotp", file=sys.stderr)
                browser.close()
                return 1
            except Exception as e:
                print(f"Failed to generate TOTP: {e}", file=sys.stderr)
                browser.close()
                return 1
            if otp_loc is None:
                for sel in OTP_SELECTORS:
                    try:
                        loc = page.locator(sel).first
                        if loc.is_visible(timeout=2000):
                            otp_loc = loc
                            break
                    except Exception:
                        continue
            if otp_loc is None:
                print("2FA input not found", file=sys.stderr)
                browser.close()
                return 1
            otp_loc.fill(code)
            _click_first_visible(page, ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Verify")'])
            blocking = _wait_for_blocking_clear(page)
            if blocking:
                print(f"Login blocked after 2FA: {blocking}", file=sys.stderr)
                browser.close()
                return 2
            _log_step(page, "2fa")

        try:
            page.wait_for_url("https://chatgpt.com/**", timeout=30000)
        except Exception:
            pass

        blocking = _has_blocking_screen(page)
        if blocking:
            print(f"Login blocked before token read: {blocking}", file=sys.stderr)
            browser.close()
            return 2

        _log_step(page, "token-read")

        js = """
        () => {
            const keys = ["accessToken","refreshToken","accessTokenExpiresAt","oai-accessToken","oai-refreshToken","oai-accessTokenExpiresAt"];
            const out = {};
            for (const k of keys) {
                try { out[k] = localStorage.getItem(k); } catch(e) { out[k] = null; }
            }
            // also try to find tokens in localStorage by scanning
            try {
                for (let i=0; i<localStorage.length; i++) {
                    const k = localStorage.key(i);
                    if (k && k.toLowerCase().includes("token") && !(k in out)) {
                        out[k] = localStorage.getItem(k);
                    }
                }
            } catch(e) {}
            return out;
        }
        """
        try:
            data = page.evaluate(js)
        except Exception as e:
            print(f"Failed to read localStorage: {e}", file=sys.stderr)
            browser.close()
            return 1

        access = data.get("accessToken") or data.get("oai-accessToken")
        refresh = data.get("refreshToken") or data.get("oai-refreshToken")
        expires_raw = data.get("accessTokenExpiresAt") or data.get("oai-accessTokenExpiresAt")

        if not access or not refresh or not expires_raw:
            _dump_page_state(page)
            print(f"Tokens not found in localStorage, found keys: {[k for k, v in data.items() if v]}", file=sys.stderr)
            browser.close()
            return 1

        try:
            expires = int(str(expires_raw).strip())
        except ValueError:
            print(f"Invalid expires value: {expires_raw!r}", file=sys.stderr)
            browser.close()
            return 1

        try:
            auth = build_auth_json(access, refresh, expires)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            browser.close()
            return 1

        write_auth_file(auth)
        json.dump(auth, sys.stdout)
        sys.stdout.write("\n")
        browser.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
