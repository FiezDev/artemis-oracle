#!/usr/bin/env python3
"""
Facebook automated post via agent-browser CLI, replacing the n8n webhook path.

Credentials are read from the encrypted vault (scripts/auth-vault.py).
A master passphrase is required on every run (env MASTER_PASSWORD or interactive prompt).

Usage:
    # Verify login only (no post).
    MASTER_PASSWORD=xxx python3 scripts/facebook-post.py --login-only

    # Post plain text.
    MASTER_PASSWORD=xxx python3 scripts/facebook-post.py --text "Hello world"

    # Post with one or more images.
    MASTER_PASSWORD=xxx python3 scripts/facebook-post.py --text "Caption" --image /path/to/img.jpg

    # Alternate service name (default: 'facebook').
    MASTER_PASSWORD=xxx python3 scripts/facebook-post.py --service fb-brand --text "..."

Flow:
  1. Navigate to m.facebook.com (simpler mobile UI — stabler selectors).
  2. If not logged in, fill login form + submit.
  3. Detect checkpoints / 2FA and stop with a readable error.
  4. Open composer (aria-label "What's on your mind?" equivalent).
  5. Type text, attach image if provided.
  6. Click Post.
  7. Screenshot the resulting state into gen-output/ for audit.

This bypasses the n8n → TikTok/FB webhook. Pulse processes can spawn this
script directly on the qone_corp host.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
VAULT_SCRIPT = SCRIPT_DIR / 'auth-vault.py'
AGENT_BROWSER = os.environ.get('AGENT_BROWSER_BIN', '/home/bjgdr/.linuxbrew/bin/agent-browser')
OUT_DIR = REPO_ROOT / 'gen-output' / 'facebook-post'

# Persistent browser profile for Facebook — cookies + IndexedDB survive between runs.
# Set the env var to override. Headed mode is the default because Facebook's
# reCAPTCHA Enterprise fires on headless sessions; a logged-in headed session
# gets trusted and can be used unattended afterwards.
FB_PROFILE = os.environ.get('FB_BROWSER_PROFILE', '/home/bjgdr/.agent-browser/fb-profile')
FB_HEADED = os.environ.get('FB_BROWSER_HEADED', '1') not in ('0', 'false', 'False', '')


class CheckpointError(RuntimeError):
    """Raised when Facebook presents a captcha/2FA/checkpoint that needs a human.

    When this is raised, the browser window is left open so the human can solve
    the challenge and the session cookies persist for the next automated run.
    """


def vault_get(service: str, field: str) -> str:
    result = subprocess.run(
        [sys.executable, str(VAULT_SCRIPT), 'get', service, field],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Vault error ({service}.{field}): {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def ab(*args, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    """Call agent-browser with persistent profile (+ headed flag on `open`)."""
    base = [AGENT_BROWSER, '--profile', FB_PROFILE]
    if args and args[0] == 'open' and FB_HEADED:
        base.append('--headed')
    cmd = [*base, *args]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and res.returncode != 0:
        raise RuntimeError(f"agent-browser {' '.join(shlex.quote(a) for a in args)} failed "
                           f"(exit {res.returncode}):\n{res.stderr or res.stdout}")
    return res


def eval_js(script: str) -> str:
    res = ab('eval', script)
    return (res.stdout or '').strip()


def page_snapshot() -> str:
    return ab('snapshot').stdout or ''


def wait_for(selector_or_ms: str, timeout: int = 20) -> None:
    ab('wait', selector_or_ms, check=False, timeout=timeout)


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def screenshot(tag: str) -> Path:
    ensure_out_dir()
    p = OUT_DIR / f'{int(time.time())}-{tag}.png'
    ab('screenshot', str(p), check=False)
    return p


def is_logged_in() -> bool:
    """Heuristic: once logged in, mobile FB document has a 'Create a post' or similar element."""
    res = eval_js(
        "(() => {"
        "  const text = document.body?.innerText || '';"
        "  const loggedInMarkers = ["
        "    /What's on your mind/i,"
        "    /Create post/i,"
        "    /News Feed/i,"
        "    /Your Profile/i"
        "  ];"
        "  const loggedOutMarkers = ["
        "    /Log in to Facebook/i,"
        "    /Create new account/i,"
        "    /Forgotten password/i"
        "  ];"
        "  if (loggedOutMarkers.some(r => r.test(text))) return 'out';"
        "  if (loggedInMarkers.some(r => r.test(text))) return 'in';"
        "  return 'unknown';"
        "})()"
    )
    return res.strip().strip('"') == 'in'


CHECKPOINT_JS = (
    "(() => {"
    " const text = document.body ? document.body.innerText : '';"
    " const iframes = Array.from(document.querySelectorAll('iframe'))"
    "   .map(f => f.src || '').join(' ');"
    " const checks = ["
    "  [text, /I.?m not a robot/i, 'reCAPTCHA checkbox'],"
    "  [text, /Please complete the security check/i, 'reCAPTCHA challenge'],"
    "  [text, /Enter login code/i, '2FA: enter login code'],"
    "  [text, /Two-factor authentication/i, '2FA challenge'],"
    "  [text, /Check your (phone|email) for a text message/i, '2FA SMS/email'],"
    "  [text, /We need to confirm it.?s you/i, 'identity checkpoint'],"
    "  [text, /Suspicious login attempt/i, 'suspicious-login checkpoint'],"
    "  [text, /This helps us to combat harmful conduct/i, 'Meta security check'],"
    "  [iframes, /recaptcha[.]net\\/recaptcha|google[.]com\\/recaptcha\\/api2/i, 'reCAPTCHA iframe visible']"
    " ];"
    " for (const [hay, re, label] of checks) { if (re.test(hay)) return label; }"
    " return null;"
    "})()"
)

COMPOSER_ROOT_JS = (
    "function composerRoot() {"
    " const roots = Array.from(document.querySelectorAll('[role=dialog], [role=presentation], div'));"
    " const candidates = roots.filter(d => {"
    "   const r = d.getBoundingClientRect();"
    "   if (r.width < 320 || r.height < 180 || r.width > 900 || r.height > 900) return false;"
    "   const text = d.innerText || '';"
    "   if (!/Create post|Post settings|Scheduling options/i.test(text)) return false;"
    "   return !!d.querySelector('[contenteditable=true], [role=\"textbox\"], textarea, input[role=combobox]');"
    " });"
    " candidates.sort((a, b) => (a.getBoundingClientRect().width * a.getBoundingClientRect().height)"
    "   - (b.getBoundingClientRect().width * b.getBoundingClientRect().height));"
    " return candidates[0] || null;"
    "}"
)


def detect_checkpoint() -> str | None:
    """Return a short reason string if a checkpoint/2FA page is detected."""
    res = eval_js(CHECKPOINT_JS).strip().strip('"')
    if not res or res == 'null':
        return None
    return res


def do_login(email: str, password: str) -> None:
    print('[login] navigating to m.facebook.com/login')
    ab('open', 'https://m.facebook.com/login/')
    # Wait for email input
    wait_for('input[name="email"]', timeout=20)

    print('[login] filling credentials (password not logged)')
    ab('fill', 'input[name="email"]', email)
    ab('fill', 'input[name="pass"]', password)

    print('[login] submitting')
    # Mobile login form uses button[type=submit] or named "login"
    try:
        ab('click', 'button[name="login"]')
    except RuntimeError:
        try:
            ab('click', 'button[type="submit"]')
        except RuntimeError:
            ab('press', 'Enter')

    # Give Facebook time to navigate.
    time.sleep(6)

    cp = detect_checkpoint()
    if cp:
        shot = screenshot('checkpoint')
        # Leave the browser open so the human can solve the challenge in-place;
        # the session cookies will persist for the next run.
        raise CheckpointError(f"Login blocked by: {cp}. Screenshot: {shot}")

    if not is_logged_in():
        shot = screenshot('login-unknown-state')
        print(f"[login] state unclear. Screenshot: {shot}")
        # Re-evaluate after a short wait (FB occasionally shows interstitials).
        time.sleep(4)
        cp2 = detect_checkpoint()
        if cp2:
            raise CheckpointError(f"Login blocked by: {cp2}. Screenshot: {shot}")
        if not is_logged_in():
            raise RuntimeError(f"Login did not complete (see screenshot: {shot})")

    print('[login] logged in')


def ensure_logged_in(email: str, password: str) -> None:
    """Check that a session is live on web.facebook.com. Avoid m.facebook.com —
    it triggers reCAPTCHA Enterprise far more aggressively than the desktop path,
    and our post flow operates on web.facebook.com anyway."""
    try:
        ab('open', 'https://web.facebook.com/')
        time.sleep(4)
    except RuntimeError:
        pass

    cp = detect_checkpoint()
    if cp:
        raise CheckpointError(f"Facebook is presenting: {cp}. Resolve manually in the open window and rerun.")

    if is_logged_in():
        print('[login] existing session detected, skipping login')
        return

    do_login(email, password)


def do_post(text: str, image_paths: list[str]) -> str:
    """Compose + publish a post. Returns the detected post URL or '' if unknown."""
    print('[post] opening composer')
    # Stable entry point: go to the composer directly.
    ab('open', 'https://m.facebook.com/composer/')
    time.sleep(4)

    cp = detect_checkpoint()
    if cp:
        shot = screenshot('compose-checkpoint')
        raise RuntimeError(f"Composer blocked: {cp} (screenshot: {shot})")

    # Fill the textarea — mobile composer uses <textarea name="xc_message">.
    try:
        ab('fill', 'textarea[name="xc_message"]', text)
    except RuntimeError:
        # Fallback to any visible contenteditable or textarea the composer exposes.
        try:
            ab('fill', 'textarea', text)
        except RuntimeError:
            ab('fill', '[contenteditable="true"]', text)

    if image_paths:
        paths = [Path(image_path).expanduser().resolve() for image_path in image_paths]
        missing = [str(p) for p in paths if not p.is_file()]
        if missing:
            raise RuntimeError(f"Image not found: {', '.join(missing)}")
        print(f'[post] attaching images: {len(paths)}')
        try:
            ab('upload', 'input[type="file"]', *[str(p) for p in paths])
            time.sleep(3)  # upload progress
        except RuntimeError as e:
            shot = screenshot('upload-failed')
            raise RuntimeError(f"Image upload failed ({e}). Screenshot: {shot}")

    print('[post] clicking Post')
    # Mobile submit button varies — try a few selectors.
    for sel in (
        'button[type="submit"]',
        'button[name="view_post"]',
        'button[value="Post"]',
        'button:has-text("Post")',
    ):
        try:
            ab('click', sel)
            break
        except RuntimeError:
            continue
    else:
        shot = screenshot('submit-no-button')
        raise RuntimeError(f"Could not find Post button. Screenshot: {shot}")

    time.sleep(6)

    cp = detect_checkpoint()
    if cp:
        shot = screenshot('post-checkpoint')
        raise RuntimeError(f"Post blocked by: {cp} (screenshot: {shot})")

    shot = screenshot('post-done')
    print(f'[post] posted. Screenshot: {shot}')

    # Best-effort: scrape current URL; FB often redirects to the new post.
    url = (ab('get', 'url').stdout or '').strip()
    return url


def switch_to_page(page_id: str) -> None:
    """Switch the session identity into a managed Facebook Page before posting.

    Flow: navigate to the page's profile URL; if a 'Switch Now' button appears,
    click it. After this call, opening the home feed reveals a composer
    that posts as the page.
    """
    print(f'[page] switching identity to page {page_id}')
    ab('open', f'https://web.facebook.com/profile.php?id={page_id}')
    time.sleep(5)

    # Look for "Switch Now" / "Switch" button exposed only to the page admin.
    marker = eval_js(
        "(() => {"
        " const btns = Array.from(document.querySelectorAll('[role=button], button'));"
        " const target = btns.find(b => /^(Switch|Switch\\s*Now)$/i.test((b.getAttribute('aria-label') || b.innerText || '').trim()));"
        " if (!target) return 'no-switch-btn';"
        " target.setAttribute('data-ab-switch', '1');"
        " return 'marked';"
        "})()"
    ).strip().strip('"')

    if marker == 'marked':
        try:
            ab('click', '[data-ab-switch="1"]')
            time.sleep(5)
        except RuntimeError as e:
            print(f'[page] could not click Switch Now: {e}')

    # Some accounts show a confirmation modal before the profile switch.
    modal_marker = eval_js(
        "(() => {"
        " const d = document.querySelector('[role=dialog]');"
        " if (!d || !/Switch profiles/i.test(d.innerText || '')) return 'no-modal';"
        " const target = Array.from(d.querySelectorAll('[role=button], button'))"
        "   .find(b => /^Switch$/i.test((b.innerText || b.getAttribute('aria-label') || '').trim()));"
        " if (!target) return 'no-modal-switch';"
        " target.setAttribute('data-ab-switch-modal', '1');"
        " return 'marked';"
        "})()"
    ).strip().strip('"')
    if modal_marker == 'marked':
        ab('click', '[data-ab-switch-modal="1"]')
        time.sleep(8)
    # else: already in page mode or no admin switch required


def parse_schedule_at(value: str) -> datetime:
    """Parse a schedule timestamp and normalize it to Asia/Bangkok."""
    raw = value.strip()
    if not raw:
        raise ValueError("--schedule-at cannot be empty")
    if "T" not in raw and " " in raw:
        raw = raw.replace(" ", "T", 1)
    dt = datetime.fromisoformat(raw)
    bkk = ZoneInfo("Asia/Bangkok")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=bkk)
    return dt.astimezone(bkk)


def fb_schedule_values(schedule_at: datetime) -> tuple[str, str]:
    """Return Facebook's English date/time input values."""
    date_value = schedule_at.strftime("%d %b %Y").lstrip("0")
    time_value = schedule_at.strftime("%H:%M")
    return date_value, time_value


def do_post_as_page(text: str, image_paths: list[str], schedule_at: datetime | None = None) -> str:
    """Compose + publish via the home-feed composer (which posts as the currently active page)."""
    print('[post] opening home feed to access page composer')
    try:
        ab('open', 'https://web.facebook.com/', timeout=90)
    except RuntimeError as e:
        ready = eval_js(
            "(() => {"
            " const text = document.body?.innerText || '';"
            " return text.includes(\"What's on your mind, AI Inspire?\") ? 'ready' : 'not-ready';"
            "})()"
        ).strip().strip('"')
        if ready != 'ready':
            raise e
        print('[post] home open timed out, but current page already has the AI Inspire composer')
    time.sleep(5)
    ab('press', 'Escape', check=False)
    time.sleep(1)

    # Find the "What's on your mind, <PageName>?" button and mark it so agent-browser
    # can dispatch a trusted CDP click (synthesised clicks don't fire React handlers).
    marker = eval_js(
        "(() => {"
        " const el = Array.from(document.querySelectorAll('div, [role=button]')).find(e => {"
        "   const t = (e.innerText||'').trim();"
        "   return t.startsWith('What') && t.includes('on your mind')"
        "          && e.children.length <= 2"
        "          && e.getBoundingClientRect().width > 100"
        "          && e.getBoundingClientRect().width < 800;"
        " });"
        " if (!el) return 'no-placeholder';"
        " el.setAttribute('data-ab-composer', '1');"
        " el.scrollIntoView({block: 'center'});"
        " const r = el.getBoundingClientRect();"
        " return ['marked', Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)].join('|');"
        "})()"
    ).strip().strip('"')
    if not marker.startswith('marked|'):
        shot = screenshot('no-composer-placeholder')
        raise RuntimeError(f"Could not locate the 'What’s on your mind' composer placeholder (screenshot: {shot})")

    _, x, y = marker.split('|')
    time.sleep(1)
    try:
        ab('click', '[data-ab-composer="1"]')
    except RuntimeError:
        ab('mouse', 'move', x, y)
        ab('mouse', 'down')
        ab('mouse', 'up')
    time.sleep(4)

    # Verify the composer modal opened, and extract the posting identity. Facebook
    # can show a skeleton dialog for several seconds before mounting the editor.
    actor = 'NO-COMPOSER-DIALOG'
    for _ in range(30):
        actor = eval_js(
            "(() => {"
            f" {COMPOSER_ROOT_JS}"
            " const d = composerRoot();"
            " if (!d || !d.querySelector('[contenteditable=true], [role=\"textbox\"], textarea')) return 'NO-COMPOSER-DIALOG';"
            " const txt = d.innerText || '';"
            " const m = txt.match(/Create post\\n([^\\n]+)\\n/);"
            " return m ? m[1] : 'unknown';"
            "})()"
        ).strip().strip('"')
        if actor != 'NO-COMPOSER-DIALOG':
            break
        time.sleep(1)
    if actor == 'NO-COMPOSER-DIALOG':
        shot = screenshot('composer-did-not-open')
        raise RuntimeError(f"Composer dialog did not open (screenshot: {shot})")
    print(f'[post] composer open, posting as: {actor}')

    # Mark + type into the contenteditable (selector-targeted, so focus is on the right element).
    ab('eval',
       "(() => {"
       f" {COMPOSER_ROOT_JS}"
       " const d = composerRoot();"
       " const ce = d && d.querySelector('[contenteditable=true], [role=\"textbox\"], textarea');"
       " if (!ce) return 'no-ce'; ce.setAttribute('data-ab-compose', '1'); ce.focus(); return 'marked'; })()")
    time.sleep(1)
    ab('type', '[data-ab-compose="1"]', text)
    time.sleep(2)

    if image_paths:
        paths = [Path(image_path).expanduser().resolve() for image_path in image_paths]
        missing = [str(p) for p in paths if not p.is_file()]
        if missing:
            raise RuntimeError(f"Image not found: {', '.join(missing)}")
        print(f'[post] attaching images: {len(paths)}')
        try:
            marker = eval_js(
                "(() => {"
                f" {COMPOSER_ROOT_JS}"
                " const d = composerRoot();"
                " const input = d && d.querySelector('input[type=\"file\"]');"
                " if (!input) return 'no-file-input';"
                " input.setAttribute('data-ab-compose-file', '1');"
                " return 'marked';"
                "})()"
            ).strip().strip('"')
            if marker != 'marked':
                raise RuntimeError(marker)
            ab('upload', '[data-ab-compose-file="1"]', *[str(p) for p in paths])
            time.sleep(5)
        except RuntimeError as e:
            shot = screenshot('upload-failed')
            raise RuntimeError(f"Image upload failed ({e}). Screenshot: {shot}")

    # Click "Next" to reveal the final Post button.
    ab('eval',
       "(() => {"
       f" {COMPOSER_ROOT_JS}"
       " const d = composerRoot();"
       " const nxt = Array.from(d.querySelectorAll('[role=button]')).find(b => (b.innerText||'').trim() === 'Next');"
       " if (nxt) nxt.setAttribute('data-ab-next', '1');"
       " return nxt ? 'marked' : 'no-next'; })()")
    try:
        ab('click', '[data-ab-next="1"]')
        time.sleep(4)
    except RuntimeError:
        # Some composers skip the Next step; carry on and try Post directly.
        pass

    final_button_text = 'Post'
    if schedule_at is not None:
        date_value, time_value = fb_schedule_values(schedule_at)
        print(f'[post] scheduling for {date_value} {time_value} Asia/Bangkok')

        marker = eval_js(
            "(() => {"
            f" {COMPOSER_ROOT_JS}"
            " const d = composerRoot();"
            " if (!d) return 'no-dialog';"
            " const btn = Array.from(d.querySelectorAll('[role=button], button'))"
            "   .find(b => (b.innerText || '').includes('Scheduling options'));"
            " if (!btn) return 'no-scheduling-options';"
            " btn.setAttribute('data-ab-scheduling-options', '1');"
            " btn.scrollIntoView({block: 'center'});"
            " return 'marked'; })()"
        ).strip().strip('"')
        if marker != 'marked':
            shot = screenshot('no-scheduling-options')
            raise RuntimeError(f"Could not locate Scheduling options (screenshot: {shot})")

        ab('click', '[data-ab-scheduling-options="1"]')
        time.sleep(3)

        inputs = eval_js(
            "(() => {"
            f" {COMPOSER_ROOT_JS}"
            " const d = composerRoot();"
            " const inputs = Array.from(d ? d.querySelectorAll('input[role=combobox]') : []);"
            " if (inputs.length < 2) return 'not-enough-inputs:' + inputs.length;"
            " inputs[0].setAttribute('data-ab-schedule-date', '1');"
            " inputs[1].setAttribute('data-ab-schedule-time', '1');"
            " return inputs.map(i => i.value).join('|'); })()"
        ).strip().strip('"')
        if inputs.startswith('not-enough-inputs'):
            shot = screenshot('schedule-inputs-missing')
            raise RuntimeError(f"Could not locate schedule date/time inputs ({inputs}, screenshot: {shot})")

        ab('fill', '[data-ab-schedule-date="1"]', date_value)
        ab('fill', '[data-ab-schedule-time="1"]', time_value)
        time.sleep(1)

        marker = eval_js(
            "(() => {"
            f" {COMPOSER_ROOT_JS}"
            " const d = composerRoot();"
            " const btn = Array.from(d ? d.querySelectorAll('[role=button], button') : [])"
            "   .find(b => (b.innerText || '').trim() === 'Schedule for later');"
            " if (!btn) return 'no-schedule-for-later';"
            " btn.setAttribute('data-ab-schedule-later', '1');"
            " return 'marked'; })()"
        ).strip().strip('"')
        if marker != 'marked':
            shot = screenshot('no-schedule-for-later')
            raise RuntimeError(f"Could not locate Schedule for later button (screenshot: {shot})")

        ab('click', '[data-ab-schedule-later="1"]')
        time.sleep(3)
        final_button_text = 'Schedule'

    # Click the final Post/Schedule button.
    ab('eval',
       "(() => {"
       f" {COMPOSER_ROOT_JS}"
       " const d = composerRoot();"
       " if (!d) return 'already-posted';"
       f" const post = Array.from(d.querySelectorAll('[role=button], button')).find(b => (b.innerText||'').trim() === '{final_button_text}');"
       " if (!post) return 'no-post-btn';"
       " post.setAttribute('data-ab-postfinal', '1');"
       " post.scrollIntoView({block: 'center'}); return 'marked'; })()")
    try:
        ab('click', '[data-ab-postfinal="1"]')
    except RuntimeError:
        # Dialog may already be closing.
        pass

    caption_probe = ' '.join(text.split())[:48]
    caption_probe_js = json.dumps(caption_probe)
    expected_action_js = json.dumps('Scheduled' if schedule_at is not None else 'Posted')

    # Wait for dialogs to clear. FB frequently shows a post-publish upsell dialog
    # (WhatsApp button, Boost post, etc.) stacked on top of the composer — find any
    # dismiss button across all open dialogs and click it.
    for _ in range(20):
        time.sleep(2)
        state = eval_js(
            "(() => {"
            f" const probe = {caption_probe_js};"
            f" const expectedAction = {expected_action_js};"
            f" {COMPOSER_ROOT_JS}"
            " const body = document.body?.innerText || '';"
            " if (probe && body.includes(probe) && /Scheduled by|Scheduled|Posted by|Posted/i.test(body)) return expectedAction.toLowerCase() + '-visible';"
            " const root = composerRoot();"
            " const dialogs = Array.from(document.querySelectorAll('[role=dialog]'))"
            "   .filter(d => { const r = d.getBoundingClientRect(); return r.width > 0 && r.height > 0; });"
            " if (dialogs.length === 0 && !root) return 'closed';"
            " if (root) dialogs.push(root);"
            " const upsellRe = /WhatsApp button|Boost (?:your )?post|Help people find your Page|Make it easier to contact you/i;"
            " const dismissRe = /^(Not now|Not Now|Maybe later|Skip|Close|No thanks)$/i;"
            " for (const d of dialogs) {"
            "   const text = d.innerText || '';"
            "   if (upsellRe.test(text)) {"
            "     const btn = Array.from(d.querySelectorAll('[role=button], button'))"
            "       .find(b => dismissRe.test((b.innerText||b.getAttribute('aria-label')||'').trim()));"
            "     if (btn) { btn.setAttribute('data-ab-dismiss', '1'); return 'upsell'; }"
            "   }"
            " }"
            " return 'dialog-still-open:' + dialogs.length;"
            "})()"
        ).strip().strip('"')
        if state in {'closed', 'scheduled-visible', 'posted-visible'}:
            break
        if state == 'upsell':
            try:
                ab('click', '[data-ab-dismiss="1"]')
                time.sleep(2)
            except RuntimeError:
                pass
    else:
        shot = screenshot('dialog-stuck')
        raise RuntimeError(f"Post dialog did not close after submit (screenshot: {shot})")

    shot = screenshot('post-done')
    action = 'scheduled' if schedule_at is not None else 'posted'
    print(f'[post] {action} as {actor}. Screenshot: {shot}')
    return (ab('get', 'url').stdout or '').strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--service', default='facebook', help='Vault service key (default: facebook)')
    ap.add_argument('--text', help='Post text')
    ap.add_argument('--image', action='append', default=[], help='Local path to an image to attach. Repeat for multiple images.')
    ap.add_argument('--page-id', help='Page ID to post as (e.g. 61563629127518 for AI Inspired). If omitted, posts to your personal feed via the mobile composer.')
    ap.add_argument('--schedule-at', help='Schedule Page post at local Asia/Bangkok time, e.g. 2026-04-28T16:00:00+07:00 or "2026-04-28 16:00".')
    ap.add_argument('--login-only', action='store_true', help='Verify login succeeds, do not post')
    ap.add_argument('--skip-login', action='store_true', help='Reuse the existing browser session without reading vault credentials.')
    ap.add_argument('--keep-open', action='store_true', help='Leave the browser session open after run')
    args = ap.parse_args()

    if not args.login_only and not args.text:
        ap.error('--text is required unless --login-only is set')

    email = password = ''
    if args.skip_login:
        print('[auth] skipping vault login; using existing browser session')
    else:
        email = vault_get(args.service, 'email')
        password = vault_get(args.service, 'password')
        print(f"[auth] using vault service '{args.service}' (account: {email})")

    keep_open_override = False
    try:
        if not args.skip_login:
            ensure_logged_in(email, password)

        if args.login_only:
            print('[ok] login verified')
            return 0

        schedule_at = parse_schedule_at(args.schedule_at) if args.schedule_at else None

        if args.page_id:
            switch_to_page(args.page_id)
            url = do_post_as_page(args.text, args.image, schedule_at=schedule_at)
        else:
            if schedule_at is not None:
                raise RuntimeError('--schedule-at is only supported with --page-id')
            url = do_post(args.text, args.image)
        print(json.dumps({'ok': True, 'url': url}))
        return 0
    except CheckpointError as e:
        # Don't close — the human needs to solve the challenge in the live browser.
        keep_open_override = True
        print(json.dumps({
            'ok': False,
            'checkpoint': True,
            'error': str(e),
            'action': 'Solve the challenge in the open browser window, then re-run the script.',
        }), file=sys.stderr)
        return 2
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}), file=sys.stderr)
        return 1
    finally:
        if not args.keep_open and not keep_open_override:
            subprocess.run([AGENT_BROWSER, 'close', '--all'], capture_output=True)


if __name__ == '__main__':
    sys.exit(main())
