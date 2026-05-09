# Site-Specific Adaptation Guide

When adapting the script for a new target site, these are the selectors and behaviors that typically need customization.

## Custom Selectors

### Login Button
Each site names and places its login button differently:

| Site | Selector | Notes |
|------|----------|-------|
| Higgsfield.ai | `a:has-text("Login")` | In top nav, opens Clerk modal |
| Generic | `a[href*="sign-in"], a[href*="login"]` | Common patterns |

### Google OAuth Button
The button that triggers Google OAuth:

| Site | Selector | Auth Provider |
|------|----------|---------------|
| Higgsfield.ai | `button:has-text("Continue with Google")` | Clerk |
| Generic | `button:has-text("Continue with Google")` | Various |

### Overlay/Modal Handling
Some sites show a promotional overlay on first load:

```python
# Dismiss by pressing Escape
page.keyboard.press("Escape")
page.wait_for_timeout(1000)
```

## Clerk-Specific Notes (Higgsfield and similar)

Sites using Clerk for auth:
- OAuth buttons are in a modal dialog
- Rate limiting: Clerk limits OAuth attempts. If you get "Too many requests", wait 2-3 minutes
- Sign-in URL pattern: Modal-based, not a separate route (e.g., `/sign-in` returns 404)
- Clerk client_id for Google: `565486769470-fhjhtkgh7hbrcsd4mt0632cmj0io1phm.apps.googleusercontent.com`

## Google 2FA Challenge Types

| ct value | Method | Description |
|----------|--------|-------------|
| 6 | Authenticator TOTP | The one we want — standard 6-digit code |
| 5 | Phone security code | Google sends code to phone |
| 9 | SMS | Text message code |
| 39 | Phone tap / device prompt | Push notification to phone |
| 53 | Passkey | Hardware/security key |

## Timing Considerations

TOTP codes are valid for 30 seconds. The script generates the code at the last moment (right before typing). If the code is rejected:

1. Check system clock sync: `timedatectl | grep synchronized`
2. The code may have expired during typing — increase `delay` parameter
3. Try regenerating if > 15 seconds have passed since generation
