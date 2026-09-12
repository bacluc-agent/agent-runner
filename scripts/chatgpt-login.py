import json
import os
import sys
from pathlib import Path


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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://chatgpt.com/auth/login", wait_until="domcontentloaded")

        def _has_blocking_screen() -> str | None:
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

        blocking = _has_blocking_screen()
        if blocking:
            print(f"Login blocked: {blocking} — cannot automate with credentials alone", file=sys.stderr)
            browser.close()
            return 2

        try:
            page.locator('input[type="email"]').first.wait_for(timeout=15000)
            page.locator('input[type="email"]').first.fill(email)
            # Continue button
            for sel in ['button:has-text("Continue")', 'button[type="submit"]']:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=2000):
                        loc.click()
                        break
                except Exception:
                    continue
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Failed at email step: {e}", file=sys.stderr)
            browser.close()
            return 1

        blocking = _has_blocking_screen()
        if blocking:
            print(f"Login blocked after email: {blocking}", file=sys.stderr)
            browser.close()
            return 2

        try:
            page.locator('input[type="password"]').first.wait_for(timeout=15000)
            page.locator('input[type="password"]').first.fill(password)
            for sel in ['button:has-text("Continue")', 'button:has-text("Log in")', 'button[type="submit"]']:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=2000):
                        loc.click()
                        break
                except Exception:
                    continue
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Failed at password step: {e}", file=sys.stderr)
            browser.close()
            return 1

        blocking = _has_blocking_screen()
        if blocking:
            print(f"Login blocked after password: {blocking}", file=sys.stderr)
            browser.close()
            return 2

        # 2FA handling
        otp_loc = None
        for sel in ['input[name="otp"]', 'input[inputmode="numeric"]', 'input[autocomplete="one-time-code"]']:
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
            try:
                if page.locator('text="Two-factor"').first.is_visible(timeout=2000):
                    needs_2fa = True
            except Exception:
                pass

        if needs_2fa:
            if not totp_key:
                print("2FA required but no TOTP key (CHATGPT_2FA_KEY/OPENAI_2FA_KEY) set", file=sys.stderr)
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
                for sel in ['input[name="otp"]', 'input[inputmode="numeric"]', 'input[autocomplete="one-time-code"]']:
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
            for sel in ['button:has-text("Continue")', 'button:has-text("Verify")', 'button[type="submit"]']:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=2000):
                        loc.click()
                        break
                except Exception:
                    continue
            page.wait_for_timeout(3000)
            blocking = _has_blocking_screen()
            if blocking:
                print(f"Login blocked after 2FA: {blocking}", file=sys.stderr)
                browser.close()
                return 2

        try:
            page.wait_for_url("https://chatgpt.com/**", timeout=30000)
        except Exception:
            pass

        blocking = _has_blocking_screen()
        if blocking:
            print(f"Login blocked before token read: {blocking}", file=sys.stderr)
            browser.close()
            return 2

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
            print(f"Tokens not found in localStorage: {data}", file=sys.stderr)
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
