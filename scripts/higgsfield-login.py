#!/usr/bin/env python3
"""
Higgsfield.ai Automated Login via Google Auth + TOTP 2FA
Credentials decrypted from encrypted vault at runtime.

Usage:
    MASTER_PASSWORD=xxx .venv/bin/python3 scripts/higgsfield-login.py [--headless]

    # Or interactive (prompts for master password):
    .venv/bin/python3 scripts/higgsfield-login.py
"""

import os
import sys
import json
import argparse
import subprocess
from urllib.parse import urlparse

from pyotp import TOTP
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_SCRIPT = os.path.join(SCRIPT_DIR, 'auth-vault.py')


def vault_get(service: str, field: str) -> str:
    """Decrypt a credential from the vault."""
    result = subprocess.run(
        [sys.executable, VAULT_SCRIPT, 'get', service, field],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Vault error: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def generate_totp(secret: str) -> str:
    return TOTP(secret).now()


def clean_lock_files(profile_dir: str):
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        path = os.path.join(profile_dir, f)
        if os.path.exists(path):
            os.remove(path)


def login_higgsfield(headless: bool = False):
    # Decrypt credentials from vault
    print("Decrypting credentials from vault...")
    email = vault_get("higgsfield", "email")
    password = vault_get("higgsfield", "password")
    totp_secret = vault_get("higgsfield", "totp_secret")
    print(f"  Account: {email}")

    profile_dir = os.path.expanduser("~/.config/higgsfield-browser-profile")
    os.makedirs(profile_dir, exist_ok=True)
    clean_lock_files(profile_dir)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            profile_dir,
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.pages[0] if context.pages else context.new_page()

        print("[1/7] Navigating to higgsfield.ai...")
        page.goto("https://higgsfield.ai/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Dismiss promo modal/overlay
        page.wait_for_timeout(3000)
        try:
            # The close button is the first button inside the dialog element
            close_btn = page.locator('dialog button').first
            if close_btn.is_visible():
                close_btn.click()
                print("  Dismissed promo modal")
            else:
                page.keyboard.press("Escape")
                print("  Pressed Escape")
        except Exception:
            page.keyboard.press("Escape")
            print("  Pressed Escape (fallback)")
        page.wait_for_timeout(2000)

        # Check if already logged in (no Login link = authenticated)
        print("[2/7] Checking login state...")
        login_link = page.locator('a[href*="sign-in"], a:has-text("Login"), a:has-text("Log in")').first
        if login_link.is_visible():
            print("  Found Login link — clicking it...")
            login_link.click(force=True)
        else:
            # Maybe already logged in
            avatar = page.locator('button[aria-label*="User"], button[aria-label*="Profile"], img[alt*="avatar"]').first
            if avatar.is_visible():
                print("  Already logged in! Skipping to cookie save.")
                cookies = context.cookies()
                cookie_file = os.path.join(SCRIPT_DIR, '..', '.higgsfield-cookies.json')
                with open(cookie_file, 'w') as f:
                    json.dump(cookies, f, indent=2)
                print(f"  Cookies saved to {cookie_file}")
                if not headless:
                    print("  Browser open for 30s...")
                    try:
                        page.wait_for_timeout(30000)
                    except Exception:
                        pass
                context.close()
                print("Done. Already authenticated.")
                return
            else:
                print("  Login link not found and not logged in. Taking debug screenshot...")
                page.screenshot(path='/tmp/higgsfield-debug.png')
                print("  Saved to /tmp/higgsfield-debug.png")
                # Try refreshing
                page.reload(wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                page.keyboard.press("Escape")
                page.wait_for_timeout(2000)
                login_link = page.locator('a[href*="sign-in"], a:has-text("Login"), a:has-text("Log in")').first
                login_link.click(force=True)
        page.wait_for_timeout(3000)

        print("[3/7] Clicking 'Continue with Google'...")
        google_btn = page.locator('button:has-text("Continue with Google")').first
        google_btn.click(force=True)
        page.wait_for_timeout(5000)

        if len(context.pages) > 1:
            page = context.pages[-1]
            print(f"  Switched to Google tab. URL: {page.url[:80]}")
        else:
            print(f"  URL after Google click: {page.url[:80]}")

        print(f"[4/7] Entering email: {email}")
        page.wait_for_selector('input[type="email"], input[name="identifier"]', timeout=20000)
        email_input = page.locator('input[type="email"], input[name="identifier"]').first
        email_input.click()
        page.wait_for_timeout(300)
        email_input.type(email, delay=50)
        page.wait_for_timeout(800)

        print("  Clicking Next after email...")
        next_btn = page.locator('div#identifierNext button').first
        if not next_btn.is_visible():
            next_btn = page.get_by_role("button", name="Next").first
        next_btn.click()
        page.wait_for_timeout(5000)

        print(f"  URL after email Next: {page.url[:100]}")
        page.screenshot(path='/tmp/google-after-email.png')

        try:
            page_text = page.locator('body').inner_text(timeout=5000)
            if "couldn't sign you in" in page_text.lower() or "not be secure" in page_text.lower():
                print("  ERROR: Google blocked the automated sign-in!")
                context.close()
                sys.exit(1)
        except Exception:
            pass

        print("[5/7] Entering password...")
        page.wait_for_selector('input[type="password"], input[name="password"], input[name="Passwd"]', timeout=20000)
        pwd_input = page.locator('input[type="password"], input[name="password"], input[name="Passwd"]').first
        pwd_input.click()
        page.wait_for_timeout(300)
        pwd_input.type(password, delay=50)
        page.wait_for_timeout(800)

        print("  Clicking Next after password...")
        pwd_next = page.locator('div#passwordNext button').first
        if not pwd_next.is_visible():
            pwd_next = page.get_by_role("button", name="Next").first
        pwd_next.click()
        page.wait_for_timeout(5000)

        print("[6/7] Handling 2FA...")
        page.wait_for_timeout(3000)

        parsed = urlparse(page.url)
        on_google = "accounts.google.com" in (parsed.hostname or "")

        if not on_google:
            print("  No 2FA needed!")
        else:
            print(f"  On Google 2FA page: {parsed.path}")
            page.screenshot(path='/tmp/google-2fa-page.png')

            totp_found = False

            try:
                totp_input = page.locator('input[name="totpPin"], input[autocomplete="one-time-code"], input[type="tel"]').first
                totp_input.wait_for(state="visible", timeout=3000)
                totp_found = True
                print("  Found TOTP input directly")
            except PWTimeout:
                pass

            if not totp_found and "/challenge/dp" in parsed.path:
                print("  On device prompt — clicking 'Try another way'...")
                try:
                    page.locator('button:has-text("Try another way"), a:has-text("Try another way")').first.click()
                    page.wait_for_timeout(3000)
                    parsed = urlparse(page.url)
                except Exception as e:
                    print(f"  Could not click 'Try another way': {e}")

            if not totp_found and "/challenge/selection" in parsed.path:
                print("  On 2FA selection page — looking for Authenticator...")
                options = page.locator('[data-challengetype]').all()
                print(f"  Found {len(options)} options:")
                for opt in options:
                    ct = opt.get_attribute('data-challengetype')
                    text = opt.inner_text(timeout=3000).replace('\n', ' ')[:80]
                    print(f"    ct={ct}: {text}")

                try:
                    page.locator('[data-challengetype="6"]').first.click()
                    page.wait_for_timeout(3000)
                except Exception:
                    try:
                        page.locator('div:has-text("Authenticator"), li:has-text("Authenticator")').first.click()
                        page.wait_for_timeout(3000)
                    except Exception as e:
                        print(f"  Could not find Authenticator: {e}")

                try:
                    totp_input = page.locator('input[type="tel"], input[name="totpPin"], input[autocomplete="one-time-code"]').first
                    totp_input.wait_for(state="visible", timeout=10000)
                    totp_found = True
                except PWTimeout:
                    pass

            if totp_found:
                code = generate_totp(totp_secret)
                print(f"  Generated TOTP code: {code}")
                totp_input.click()
                totp_input.type(code, delay=80)
                page.wait_for_timeout(500)

                page.locator('div#totpNext button, button:has-text("Next"), button:has-text("Verify")').first.click()
                print("  TOTP code submitted!")
                page.wait_for_timeout(5000)
            else:
                print("  WARNING: Could not find TOTP input.")
                page.screenshot(path='/tmp/google-2fa-debug.png')

        page.wait_for_timeout(5000)

        print("[7/7] Waiting for redirect to Higgsfield...")
        try:
            page.wait_for_url("**/higgsfield.ai/**", timeout=30000)
            print(f"  SUCCESS! Redirected to: {page.url}")
        except PWTimeout:
            parsed = urlparse(page.url)
            print(f"  Still on: {parsed.hostname}{parsed.path}")
            page.screenshot(path='/tmp/higgsfield-post-login.png')

        cookies = context.cookies()
        cookie_file = os.path.join(SCRIPT_DIR, '..', '.higgsfield-cookies.json')
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"  Cookies saved to {cookie_file}")

        if not headless:
            print("\nBrowser stays open for 30 seconds...")
            try:
                page.wait_for_timeout(30000)
            except Exception:
                pass

        context.close()
        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Higgsfield.ai login")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    login_higgsfield(headless=args.headless)
