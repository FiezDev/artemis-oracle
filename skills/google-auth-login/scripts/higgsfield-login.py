#!/usr/bin/env python3
"""
Higgsfield.ai Automated Login via Google Auth + TOTP 2FA
Uses Playwright for browser automation and PyOTP for TOTP code generation.

Usage:
    export HIGGSFIELD_EMAIL="ittipolbiz@gmail.com"
    export HIGGSFIELD_PASSWORD="your-password"
    export HIGGSFIELD_TOTP_SECRET="your-totp-secret"
    python3 scripts/higgsfield-login.py [--headless]
"""

import os
import sys
import time
import argparse
from urllib.parse import urlparse

# Add venv to path if needed
venv_site = os.path.join(os.path.dirname(__file__), '..', '.venv', 'lib')
if os.path.exists(venv_site):
    for d in os.listdir(venv_site):
        site_pkg = os.path.join(venv_site, d, 'site-packages')
        if os.path.isdir(site_pkg):
            sys.path.insert(0, site_pkg)

from pyotp import TOTP
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def get_credentials():
    """Load credentials from environment variables."""
    email = os.environ.get("HIGGSFIELD_EMAIL")
    password = os.environ.get("HIGGSFIELD_PASSWORD")
    totp_secret = os.environ.get("HIGGSFIELD_TOTP_SECRET")
    if not all([email, password, totp_secret]):
        print("ERROR: Set environment variables:")
        print("  export HIGGSFIELD_EMAIL='your-email'")
        print("  export HIGGSFIELD_PASSWORD='your-password'")
        print("  export HIGGSFIELD_TOTP_SECRET='your-totp-secret'")
        sys.exit(1)
    return email, password, totp_secret


def generate_totp(secret: str) -> str:
    """Generate current TOTP code from secret."""
    return TOTP(secret).now()


def login_higgsfield(headless: bool = False):
    email, password, totp_secret = get_credentials()

    # Use persistent Chrome profile to avoid Google's automation detection
    user_data_dir = os.path.expanduser("~/.config/higgsfield-browser-profile")
    os.makedirs(user_data_dir, exist_ok=True)

    with sync_playwright() as p:
        # Use real Chrome with persistent context — Google won't flag it as automated
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
        # Remove webdriver flag to avoid detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.pages[0] if context.pages else context.new_page()

        # Step 1: Navigate to Higgsfield
        print("[1/7] Navigating to higgsfield.ai...")
        page.goto("https://higgsfield.ai/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Dismiss any overlay/modal that appears on load
        overlay = page.locator('div[data-state="open"].fixed.inset-0')
        if overlay.count() > 0 and overlay.first.is_visible():
            print("  Dismissing overlay/modal...")
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)

        # Step 2: Click Login
        print("[2/7] Clicking Login...")
        login_link = page.locator('a[href*="sign-in"], a:has-text("Login"), a:has-text("Log in")').first
        login_link.click(force=True)
        page.wait_for_timeout(3000)

        # Step 3: Click "Continue with Google"
        print("[3/7] Clicking 'Continue with Google'...")
        google_btn = page.locator('button:has-text("Continue with Google")').first
        google_btn.click(force=True)
        page.wait_for_timeout(5000)

        # Handle possible popup/tab for Google sign-in
        # Wait for Google sign-in page
        page.wait_for_timeout(2000)
        if len(context.pages) > 1:
            page = context.pages[-1]  # Switch to new tab
            print(f"  Switched to Google sign-in tab. URL: {page.url}")
        else:
            print(f"  Current URL after Google click: {page.url}")

        # Step 4: Enter email
        print(f"[4/7] Entering email: {email}")
        page.wait_for_selector('input[type="email"], input[name="identifier"]', timeout=20000)
        email_input = page.locator('input[type="email"], input[name="identifier"]').first
        email_input.click()
        page.wait_for_timeout(300)
        # Type email character by character for Google's detection
        email_input.type(email, delay=50)
        page.wait_for_timeout(800)

        # Click Next - Google uses specific button in #identifierNext container
        print("  Clicking Next after email...")
        next_btn = page.locator('div#identifierNext button, button#identifierNext').first
        if not next_btn.is_visible():
            next_btn = page.get_by_role("button", name="Next").first
        next_btn.click()
        page.wait_for_timeout(5000)

        # Debug: check what page we're on
        print(f"  URL after email Next: {page.url[:100]}")
        page.screenshot(path='/tmp/google-after-email.png')

        # Check for Google security warning
        page_text = page.locator('body').inner_text(timeout=5000)
        if "couldn't sign you in" in page_text.lower() or "not be secure" in page_text.lower():
            print("  ERROR: Google blocked the automated sign-in!")
            print("  Google detected this as an automated browser.")
            print("  Page text snippet:", page_text[:500])
            browser.close()
            sys.exit(1)

        # Step 5: Enter password
        print("[5/7] Entering password...")
        page.wait_for_selector('input[type="password"], input[name="password"], input[name="Passwd"]', timeout=20000)
        pwd_input = page.locator('input[type="password"], input[name="password"], input[name="Passwd"]').first
        pwd_input.click()
        page.wait_for_timeout(300)
        pwd_input.type(password, delay=50)
        page.wait_for_timeout(800)

        # Click Next
        print("  Clicking Next after password...")
        pwd_next = page.locator('div#passwordNext button, button#passwordNext').first
        if not pwd_next.is_visible():
            pwd_next = page.get_by_role("button", name="Next").first
        pwd_next.click()
        page.wait_for_timeout(5000)

        # Step 6: Handle 2FA with TOTP
        print(f"[6/7] Handling 2FA...")
        page.wait_for_timeout(3000)

        current_url = page.url
        parsed = urlparse(current_url)
        on_google = "accounts.google.com" in parsed.hostname or "google.com" in parsed.hostname

        if not on_google:
            print("  No 2FA needed — already redirected back!")
        else:
            print(f"  On Google 2FA page: {parsed.path}")
            page.screenshot(path='/tmp/google-2fa-page.png')

            totp_found = False

            # Case 1: Already on TOTP input page
            try:
                totp_input = page.locator('input[name="totpPin"], input[autocomplete="one-time-code"], input[type="tel"]').first
                totp_input.wait_for(state="visible", timeout=3000)
                totp_found = True
                print("  Found TOTP input directly")
            except PWTimeout:
                pass

            # Case 2: On device prompt (/challenge/dp) — need "Try another way"
            if not totp_found and "/challenge/dp" in parsed.path:
                print("  On device prompt — clicking 'Try another way'...")
                try:
                    another_way = page.locator('button:has-text("Try another way"), a:has-text("Try another way")').first
                    another_way.click()
                    page.wait_for_timeout(3000)
                    # After clicking, we should land on /challenge/selection
                    parsed = urlparse(page.url)
                    page.screenshot(path='/tmp/google-2fa-selection.png')
                except Exception as e:
                    print(f"  Could not click 'Try another way': {e}")

            # Case 3: On selection page (/challenge/selection) — pick Authenticator
            if not totp_found and "/challenge/selection" in parsed.path:
                print("  On 2FA selection page — looking for Authenticator option...")
                # Debug: list all challenge options on the page
                options = page.locator('[data-challengetype]').all()
                print(f"  Found {len(options)} challenge options:")
                for opt in options:
                    ct = opt.get_attribute('data-challengetype')
                    text = opt.inner_text(timeout=3000).replace('\n', ' ')[:80]
                    print(f"    ct={ct}: {text}")

                # Try to click Authenticator (ct=6)
                try:
                    auth_option = page.locator('[data-challengetype="6"]').first
                    auth_option.click()
                    page.wait_for_timeout(3000)
                    print("  Clicked Authenticator option (ct=6)")
                except Exception as e:
                    print(f"  ct=6 not found, trying text search: {e}")
                    try:
                        auth_option = page.locator('div:has-text("Authenticator"), li:has-text("Authenticator")').first
                        auth_option.click()
                        page.wait_for_timeout(3000)
                        print("  Clicked Authenticator by text")
                    except Exception as e2:
                        print(f"  Could not find Authenticator option: {e2}")
                        page.screenshot(path='/tmp/google-2fa-no-auth.png')

                # Now look for TOTP input
                try:
                    totp_input = page.locator('input[type="tel"], input[name="totpPin"], input[autocomplete="one-time-code"]').first
                    totp_input.wait_for(state="visible", timeout=10000)
                    totp_found = True
                    print("  Found TOTP input after selection")
                except PWTimeout:
                    print("  TOTP input not found after selection")
                    page.screenshot(path='/tmp/google-2fa-no-input.png')

            if totp_found:
                code = generate_totp(totp_secret)
                print(f"  Generated TOTP code: {code}")
                totp_input.click()
                totp_input.type(code, delay=80)
                page.wait_for_timeout(500)

                verify_btn = page.locator('div#totpNext button, button:has-text("Next"), button:has-text("Verify")').first
                verify_btn.click()
                print("  TOTP code submitted!")
                page.wait_for_timeout(5000)
            else:
                print("  WARNING: Could not find TOTP entry field.")
                print("  URL:", page.url)
                page.screenshot(path='/tmp/google-2fa-debug.png')
                print("  Check /tmp/google-2fa-debug.png for the page state")

        page.wait_for_timeout(5000)

        # Step 7: Wait for redirect back to Higgsfield and verify login
        print("[7/7] Waiting for redirect to Higgsfield...")
        try:
            page.wait_for_url("**/higgsfield.ai/**", timeout=30000)
            print(f"  SUCCESS! Redirected to: {page.url}")
        except PWTimeout:
            parsed = urlparse(page.url)
            print(f"  Still on: {parsed.hostname}{parsed.path}")
            page.screenshot(path='/tmp/higgsfield-post-login.png')
            page_text = page.locator('body').inner_text(timeout=5000)
            if "wrong" in page_text.lower() or "invalid" in page_text.lower() or "try again" in page_text.lower():
                print("  TOTP code may have been rejected.")
            else:
                print("  Check browser window for status.")

        # Keep browser open briefly for inspection (unless headless)
        if not headless:
            print("\nBrowser stays open for 30 seconds for inspection...")
            try:
                page.wait_for_timeout(30000)
            except Exception:
                pass

        # Save cookies for reuse
        cookies = context.cookies()
        cookie_file = os.path.join(os.path.dirname(__file__), '..', '.higgsfield-cookies.json')
        with open(cookie_file, 'w') as f:
            import json
            json.dump(cookies, f, indent=2)
        print(f"Cookies saved to {cookie_file}")

        context.close()
        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Higgsfield.ai login")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()
    login_higgsfield(headless=args.headless)
