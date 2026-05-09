#!/usr/bin/env python3
"""
Google OAuth + TOTP 2FA Automated Login
Works with any site that uses Google OAuth for authentication.

Uses Playwright with real Chrome to avoid Google's automation detection.

Usage:
    export TARGET_URL="https://example.com"
    export AUTH_EMAIL="user@gmail.com"
    export AUTH_PASSWORD="your-password"
    export AUTH_TOTP_SECRET="your-totp-secret"
    python3 google-auth-totp.py [--headless] [--timeout 60]

Requires:
    pip install pyotp playwright
    playwright install chromium
    Google Chrome installed on system
"""

import os
import sys
import json
import time
import argparse
from urllib.parse import urlparse

from pyotp import TOTP
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def get_credentials():
    """Load credentials from environment variables."""
    target_url = os.environ.get("TARGET_URL")
    email = os.environ.get("AUTH_EMAIL")
    password = os.environ.get("AUTH_PASSWORD")
    totp_secret = os.environ.get("AUTH_TOTP_SECRET")

    missing = []
    if not target_url: missing.append("TARGET_URL")
    if not email: missing.append("AUTH_EMAIL")
    if not password: missing.append("AUTH_PASSWORD")
    if not totp_secret: missing.append("AUTH_TOTP_SECRET")

    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Set them before running:")
        print("  export TARGET_URL='https://example.com'")
        print("  export AUTH_EMAIL='user@gmail.com'")
        print("  export AUTH_PASSWORD='your-password'")
        print("  export AUTH_TOTP_SECRET='your-totp-secret'")
        sys.exit(1)

    return target_url, email, password, totp_secret


def generate_totp(secret: str) -> str:
    """Generate current TOTP code from secret."""
    return TOTP(secret).now()


def clean_lock_files(profile_dir: str):
    """Remove Chrome's stale lock files."""
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        path = os.path.join(profile_dir, f)
        if os.path.exists(path):
            os.remove(path)


def login(target_url: str, email: str, password: str, totp_secret: str,
          headless: bool = False, timeout: int = 60):
    """Execute the full Google OAuth + TOTP login flow."""

    # Persistent Chrome profile to avoid automation detection
    profile_dir = os.environ.get(
        "BROWSER_PROFILE",
        os.path.expanduser("~/.config/auth-browser-profile")
    )
    os.makedirs(profile_dir, exist_ok=True)
    clean_lock_files(profile_dir)

    timeout_ms = timeout * 1000

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
        # Override webdriver detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.pages[0] if context.pages else context.new_page()

        # --- Step 1: Navigate to target site ---
        print(f"[1/7] Navigating to {target_url}...")
        page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(3000)

        # --- Step 2: Dismiss overlays and click Login ---
        print("[2/7] Looking for Login button...")
        # Try dismissing modal overlays
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)

        login_selectors = [
            'a[href*="sign-in"]',
            'a[href*="login"]',
            'a:has-text("Login")',
            'a:has-text("Log in")',
            'a:has-text("Sign in")',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
        ]
        login_clicked = False
        for sel in login_selectors:
            loc = page.locator(sel).first
            if loc.is_visible():
                loc.click(force=True)
                login_clicked = True
                print(f"  Clicked login via: {sel}")
                break
        if not login_clicked:
            print("  WARNING: Could not find Login button. Page may already be on auth.")
        page.wait_for_timeout(3000)

        # --- Step 3: Click "Continue with Google" ---
        print("[3/7] Clicking 'Continue with Google'...")
        google_selectors = [
            'button:has-text("Continue with Google")',
            'a:has-text("Continue with Google")',
            'button:has-text("Sign in with Google")',
            'a:has-text("Sign in with Google")',
        ]
        google_clicked = False
        for sel in google_selectors:
            loc = page.locator(sel).first
            if loc.is_visible():
                loc.click(force=True)
                google_clicked = True
                print(f"  Clicked Google auth via: {sel}")
                break
        if not google_clicked:
            print("  ERROR: Could not find Google OAuth button.")
            page.screenshot(path='/tmp/auth-no-google-btn.png')
            context.close()
            sys.exit(1)
        page.wait_for_timeout(5000)

        # Handle popup/tab
        if len(context.pages) > 1:
            page = context.pages[-1]
            print(f"  Switched to Google tab. URL: {page.url[:80]}")
        else:
            print(f"  URL after Google click: {page.url[:80]}")

        # --- Step 4: Enter email ---
        print(f"[4/7] Entering email: {email}")
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

        # Click Next
        print("  Clicking Next after email...")
        next_btn = page.locator('div#identifierNext button').first
        if not next_btn.is_visible():
            next_btn = page.get_by_role("button", name="Next").first
        next_btn.click()
        page.wait_for_timeout(5000)

        # Check for Google security block
        print(f"  URL after email Next: {page.url[:100]}")
        try:
            page_text = page.locator('body').inner_text(timeout=5000)
            if "couldn't sign you in" in page_text.lower() or "not be secure" in page_text.lower():
                print("  ERROR: Google blocked the sign-in!")
                print("  Google detected this as an automated browser.")
                page.screenshot(path='/tmp/auth-google-blocked.png')
                context.close()
                sys.exit(1)
        except Exception:
            pass

        # --- Step 5: Enter password ---
        print("[5/7] Entering password...")
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

        # Click Next
        print("  Clicking Next after password...")
        pwd_next = page.locator('div#passwordNext button').first
        if not pwd_next.is_visible():
            pwd_next = page.get_by_role("button", name="Next").first
        pwd_next.click()
        page.wait_for_timeout(5000)

        # --- Step 6: Handle 2FA with TOTP ---
        print("[6/7] Handling 2FA...")
        page.wait_for_timeout(3000)

        current_url = page.url
        parsed = urlparse(current_url)
        on_google = "accounts.google.com" in (parsed.hostname or "")

        if not on_google:
            print("  No 2FA needed — already redirected back!")
        else:
            print(f"  On Google 2FA page: {parsed.path}")

            totp_found = False

            # Case 1: Already on TOTP input page
            try:
                totp_input = page.locator(
                    'input[name="totpPin"], input[autocomplete="one-time-code"], input[type="tel"]'
                ).first
                totp_input.wait_for(state="visible", timeout=3000)
                totp_found = True
                print("  Found TOTP input directly")
            except PWTimeout:
                pass

            # Case 2: On device prompt — click "Try another way"
            if not totp_found and "/challenge/dp" in parsed.path:
                print("  On device prompt — clicking 'Try another way'...")
                try:
                    another_way = page.locator(
                        'button:has-text("Try another way"), a:has-text("Try another way")'
                    ).first
                    another_way.click()
                    page.wait_for_timeout(3000)
                    parsed = urlparse(page.url)
                except Exception as e:
                    print(f"  Could not click 'Try another way': {e}")

            # Case 3: On selection page — pick Authenticator
            if not totp_found and "/challenge/selection" in parsed.path:
                print("  On 2FA selection page — looking for Authenticator option...")
                options = page.locator('[data-challengetype]').all()
                print(f"  Found {len(options)} challenge options:")
                for opt in options:
                    ct = opt.get_attribute('data-challengetype')
                    text = opt.inner_text(timeout=3000).replace('\n', ' ')[:80]
                    print(f"    ct={ct}: {text}")

                # Try ct=6 (Authenticator TOTP) first, then text search
                try:
                    auth_option = page.locator('[data-challengetype="6"]').first
                    auth_option.click()
                    page.wait_for_timeout(3000)
                    print("  Clicked Authenticator option (ct=6)")
                except Exception:
                    try:
                        auth_option = page.locator(
                            'div:has-text("Authenticator"), li:has-text("Authenticator")'
                        ).first
                        auth_option.click()
                        page.wait_for_timeout(3000)
                        print("  Clicked Authenticator by text")
                    except Exception as e:
                        print(f"  Could not find Authenticator: {e}")
                        page.screenshot(path='/tmp/auth-2fa-no-auth.png')

                # Find TOTP input
                try:
                    totp_input = page.locator(
                        'input[type="tel"], input[name="totpPin"], input[autocomplete="one-time-code"]'
                    ).first
                    totp_input.wait_for(state="visible", timeout=10000)
                    totp_found = True
                    print("  Found TOTP input after selection")
                except PWTimeout:
                    print("  TOTP input not found after selection")

            if totp_found:
                code = generate_totp(totp_secret)
                print(f"  Generated TOTP code: {code}")
                totp_input.click()
                totp_input.type(code, delay=80)
                page.wait_for_timeout(500)

                verify_btn = page.locator(
                    'div#totpNext button, button:has-text("Next"), button:has-text("Verify")'
                ).first
                verify_btn.click()
                print("  TOTP code submitted!")
                page.wait_for_timeout(5000)
            else:
                print("  WARNING: Could not find TOTP entry field.")
                print("  URL:", page.url)
                page.screenshot(path='/tmp/auth-2fa-debug.png')

        page.wait_for_timeout(5000)

        # --- Step 7: Verify redirect ---
        print("[7/7] Waiting for redirect back to target site...")
        target_host = urlparse(target_url).hostname
        try:
            page.wait_for_url(f"**/{target_host}/**", timeout=30000)
            print(f"  SUCCESS! Redirected to: {page.url}")
        except PWTimeout:
            parsed = urlparse(page.url)
            print(f"  Current URL: {parsed.hostname}{parsed.path}")
            page.screenshot(path='/tmp/auth-post-login.png')

        # Save cookies
        cookies = context.cookies()
        cookie_file = os.path.join(
            os.path.dirname(__file__), '..', '.auth-cookies.json'
        )
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"  Cookies saved to {cookie_file}")

        # Keep browser open briefly
        if not headless:
            print("\nBrowser stays open for 30 seconds for inspection...")
            try:
                page.wait_for_timeout(30000)
            except Exception:
                pass

        context.close()
        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated Google OAuth + TOTP login"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="Page load timeout in seconds (default: 60)"
    )
    args = parser.parse_args()

    target_url, email, password, totp_secret = get_credentials()
    login(target_url, email, password, totp_secret,
          headless=args.headless, timeout=args.timeout)
