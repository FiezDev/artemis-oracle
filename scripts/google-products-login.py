#!/usr/bin/env python3
"""
Google Products Auto-Login (Gemini, NotebookLM, Flow)
Signs into Google once, then opens all products.
Credentials are decrypted from the encrypted vault at runtime.

Usage:
    # Interactive (prompts for master password):
    .venv/bin/python3 scripts/google-products-login.py

    # With master password via env (for automation):
    MASTER_PASSWORD=xxx .venv/bin/python3 scripts/google-products-login.py

    # Options:
    --headless       Run without visible browser
    --product X      Open specific product: gemini, notebooklm, flow, all

Requires:
    pip install pyotp playwright cryptography
    playwright install chromium
    Google Chrome installed
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

PRODUCTS = {
    "gemini": "https://gemini.google.com/",
    "notebooklm": "https://notebooklm.google.com/",
    "flow": "https://labs.google/flow",
}


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


def google_signin(page, email: str, password: str, totp_secret: str):
    """Handle Google sign-in flow (email -> password -> optional 2FA)."""
    # Enter email
    print("  Entering email...")
    page.wait_for_selector(
        'input[type="email"], input[name="identifier"]',
        timeout=20000
    )
    email_input = page.locator(
        'input[type="email"], input[name="identifier"]'
    ).first
    email_input.click()
    page.wait_for_timeout(300)
    email_input.type(email, delay=50)
    page.wait_for_timeout(800)

    next_btn = page.locator('div#identifierNext button').first
    if not next_btn.is_visible():
        next_btn = page.get_by_role("button", name="Next").first
    next_btn.click()
    page.wait_for_timeout(5000)

    # Check for security block
    try:
        page_text = page.locator('body').inner_text(timeout=5000)
        if "couldn't sign you in" in page_text.lower() or "not be secure" in page_text.lower():
            print("  ERROR: Google blocked sign-in (automation detected)")
            page.screenshot(path='/tmp/google-blocked.png')
            return False
    except Exception:
        pass

    # Enter password
    print("  Entering password...")
    page.wait_for_selector(
        'input[type="password"], input[name="password"], input[name="Passwd"]',
        timeout=20000
    )
    pwd_input = page.locator(
        'input[type="password"], input[name="password"], input[name="Passwd"]'
    ).first
    pwd_input.click()
    page.wait_for_timeout(300)
    pwd_input.type(password, delay=50)
    page.wait_for_timeout(800)

    pwd_next = page.locator('div#passwordNext button').first
    if not pwd_next.is_visible():
        pwd_next = page.get_by_role("button", name="Next").first
    pwd_next.click()
    page.wait_for_timeout(5000)

    # Handle 2FA
    parsed = urlparse(page.url)
    on_google = "accounts.google.com" in (parsed.hostname or "")

    if not on_google:
        print("  Signed in! No 2FA required.")
        return True

    print(f"  On 2FA page: {parsed.path}")

    if not totp_secret:
        print("  2FA required but no TOTP secret in vault.")
        print("  Complete 2FA manually in browser...")
        page.wait_for_timeout(30000)
        return True

    totp_found = False
    try:
        totp_input = page.locator(
            'input[name="totpPin"], input[autocomplete="one-time-code"], input[type="tel"]'
        ).first
        totp_input.wait_for(state="visible", timeout=3000)
        totp_found = True
    except PWTimeout:
        pass

    if not totp_found and "/challenge/dp" in parsed.path:
        print("  On device prompt — switching to Authenticator...")
        try:
            page.locator('button:has-text("Try another way")').first.click()
            page.wait_for_timeout(3000)
            parsed = urlparse(page.url)
        except Exception:
            pass

    if not totp_found and "/challenge/selection" in parsed.path:
        options = page.locator('[data-challengetype]').all()
        for opt in options:
            ct = opt.get_attribute('data-challengetype')
            text = opt.inner_text(timeout=3000).replace('\n', ' ')[:80]
            print(f"    ct={ct}: {text}")
        try:
            page.locator('[data-challengetype="6"]').first.click()
            page.wait_for_timeout(3000)
        except Exception:
            try:
                page.locator('div:has-text("Authenticator")').first.click()
                page.wait_for_timeout(3000)
            except Exception:
                pass

        try:
            totp_input = page.locator(
                'input[type="tel"], input[name="totpPin"], input[autocomplete="one-time-code"]'
            ).first
            totp_input.wait_for(state="visible", timeout=10000)
            totp_found = True
        except PWTimeout:
            pass

    if totp_found:
        code = generate_totp(totp_secret)
        print(f"  TOTP code: {code}")
        totp_input.click()
        totp_input.type(code, delay=80)
        page.wait_for_timeout(500)
        page.locator(
            'div#totpNext button, button:has-text("Next"), button:has-text("Verify")'
        ).first.click()
        print("  TOTP submitted!")
        page.wait_for_timeout(5000)
    else:
        print("  WARNING: Could not auto-complete 2FA. Do it manually...")
        page.wait_for_timeout(30000)

    return True


def main():
    parser = argparse.ArgumentParser(description="Google Products Auto-Login")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--product", choices=list(PRODUCTS.keys()) + ["all"],
        default="all", help="Which product to open (default: all)"
    )
    args = parser.parse_args()

    # Decrypt credentials from vault
    print("Decrypting credentials from vault...")
    email = vault_get("google", "email")
    password = vault_get("google", "password")
    totp_secret = vault_get("google", "totp_secret")
    print(f"  Account: {email}")

    profile_dir = os.path.expanduser("~/.config/google-products-profile")
    os.makedirs(profile_dir, exist_ok=True)
    clean_lock_files(profile_dir)

    targets = PRODUCTS if args.product == "all" else {args.product: PRODUCTS[args.product]}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            profile_dir,
            channel="chrome",
            headless=args.headless,
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

        print("[1/3] Signing into Google...")
        page.goto("https://accounts.google.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        if "myaccount.google.com" in page.url or "myaccount" in page.url:
            print("  Already signed in!")
        else:
            if not google_signin(page, email, password, totp_secret):
                context.close()
                sys.exit(1)

        print(f"[2/3] Opening: {', '.join(targets.keys())}")
        for name, url in targets.items():
            print(f"  Opening {name}: {url}")
            new_page = context.new_page()
            new_page.goto(url, wait_until="domcontentloaded", timeout=60000)
            new_page.wait_for_timeout(2000)
            print(f"  {name} loaded: {new_page.url[:80]}")

        cookies = context.cookies()
        cookie_file = os.path.join(SCRIPT_DIR, '..', '.google-products-cookies.json')
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"[3/3] Session saved.")

        if not args.headless:
            print("\nBrowser open for 60s. Ctrl+C to close earlier.")
            try:
                page.wait_for_timeout(60000)
            except Exception:
                pass

        context.close()
        print("Done.")


if __name__ == "__main__":
    main()
