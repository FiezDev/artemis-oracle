---
name: google-auth-login
description: Automate Google OAuth login with TOTP 2FA on any website using Playwright + real Chrome. Use this skill whenever the user wants to automate signing into a website via Google OAuth, automate login flows, handle Google 2FA programmatically, generate TOTP codes, or needs to bypass Google's "This browser or app may not be secure" block. Also use when the user mentions automated login, OAuth automation, Google sign-in scripting, or TOTP/2FA automation.
---

# Google OAuth + TOTP Login Automation

Automates the full Google OAuth login flow on any website, including TOTP-based 2FA (Authenticator app codes). Uses Playwright with **real Chrome** (`channel="chrome"`) to avoid Google's automation detection.

## When to Use

- User wants to automate login to a site that uses "Continue with Google"
- User needs to programmatically generate TOTP codes from an Authenticator secret
- User is getting "This browser or app may not be secure" from Google when using headless/automated browsers
- User wants to save session cookies for reuse

## Prerequisites

```bash
# Create venv if not exists
python3 -m venv .venv
.venv/bin/pip install pyotp playwright
.venv/bin/playwright install chromium
```

The system must have **Google Chrome** installed (not Chromium — Google detects Chromium-based automation). The script uses `channel="chrome"` to launch the real Chrome browser.

## The Login Script

The main script is at `scripts/google-auth-totp.py`. Read it and adapt it to the target site. The script handles:

1. Navigate to target site
2. Find and click "Login" / "Sign in"
3. Click "Continue with Google"
4. Enter email (character-by-character for Google's detection)
5. Enter password
6. Handle 2FA — goes directly to TOTP input if Google presents `/challenge/totp`, or navigates the selection page to find the Authenticator option
7. Wait for redirect back to target site
8. Save cookies for session reuse

## Parameters

| Parameter | Env Variable | Required | Description |
|-----------|-------------|----------|-------------|
| Target URL | `TARGET_URL` | Yes | The website to log into |
| Email | `AUTH_EMAIL` | Yes | Google account email |
| Password | `AUTH_PASSWORD` | Yes | Google account password |
| TOTP Secret | `AUTH_TOTP_SECRET` | Yes | From Google Authenticator setup ("Can't scan it?" link) |
| Headless | `--headless` flag | No | Run without visible browser window |
| Browser profile | `BROWSER_PROFILE` | No | Path for persistent Chrome profile (default: `~/.config/auth-browser-profile`) |

## TOTP Secret Setup

The TOTP secret comes from setting up Google Authenticator in the Google account:

1. Go to https://myaccount.google.com/signinoptions/two-step-verification
2. Add **Authenticator app** as a 2FA method
3. When shown the QR code, click **"Can't scan it?"** or **"Enter a setup key"**
4. Copy the 16+ character secret key (e.g., `fvds bwm5 eeix o5qr ffb6 q5bw mkwo s7yp`)
5. This is the `AUTH_TOTP_SECRET` value

The secret is base32-encoded. `pyotp.TOTP(secret).now()` generates valid 6-digit codes.

## Google's 2FA Page States

Google's sign-in v3 can land on different challenge URLs after the password step:

| URL Path | Meaning | Script Action |
|----------|---------|---------------|
| `/challenge/totp` | TOTP input page directly | Enter code immediately |
| `/challenge/dp` | Device prompt (phone push) | Click "Try another way" to get to selection |
| `/challenge/selection` | Method selection page | Find and click Authenticator option (`data-challengetype="6"`) |

The script handles all three cases. The most common flow with a configured Authenticator is landing directly on `/challenge/totp`.

## Site-Specific Adaptation

Each target site has its own login button placement and flow. The key selectors that may need adaptation:

```python
# Step 1: Login link/button on the target site
login_link = page.locator('a[href*="sign-in"], a:has-text("Login"), a:has-text("Log in")').first

# Step 2: "Continue with Google" button on the auth dialog
google_btn = page.locator('button:has-text("Continue with Google")').first

# Step 3: Google's "Next" buttons use container-specific selectors
# Email step: div#identifierNext button
# Password step: div#passwordNext button
```

For a new target site, inspect the page to find the correct selectors for the Login button and Google OAuth button. The Google-side selectors (email input, password input, TOTP input, Next buttons) are universal.

## Avoiding Google's Automation Detection

Google blocks browsers it detects as automated. The script uses three techniques to avoid this:

1. **Real Chrome** via `channel="chrome"` — not Playwright's bundled Chromium
2. **Persistent context** — uses a real user data directory, not a fresh temp profile
3. **Webdriver override** — `navigator.webdriver` returns `undefined` instead of `true`

```python
context = p.chromium.launch_persistent_context(
    user_data_dir,
    channel="chrome",  # Real Chrome, not Chromium
    headless=headless,
    args=["--disable-blink-features=AutomationControlled", ...]
)
context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
""")
```

If Google still blocks the sign-in, the persistent profile may need to be cleared or Chrome may need to be updated.

## Cookie Reuse

After successful login, cookies are saved to `.auth-cookies.json`. These can be loaded in future sessions to skip the login flow while the session is still valid.

## Security Notes

- Credentials are passed via environment variables, never hardcoded in scripts
- The TOTP secret is equivalent to the Authenticator app — protect it like a password
- Cookie files contain session tokens — add to `.gitignore`
- The browser profile directory may contain cached credentials — protect it
