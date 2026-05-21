"""CloakBrowser+Playwright orchestrator for fresh screenshot capture.

Usage (standalone):
    python3 capture.py --config-file /path/to/iso-doc.json

What it does:
    1. Read per-project config (urls, auth, routes)
    2. Pull creds from ~/.claude/dev-vault/<vault_key>.json
    3. For each lang in config.LANGUAGES:
         - Launch CloakBrowser (Playwright-compatible stealth Chromium),
           navigate to the live URL
         - Log in as the configured role (admin by default)
         - Switch UI language to <lang>
         - Walk discovered routes; screenshot each
         - For dynamic routes, click first row to hit detail page
    4. Save PNGs to {output_dir}/assets/screenshots/{lang}/{id}.png

Auth modes:
    form_password  — email+password form login (e.g. DAD)
    otp_phone      — OTP digit-per-field (asks you to relay OTP in chat)
    cookie_inject  — reads pre-captured cookies from config

Requires:
    pip install cloakbrowser playwright
    cloakbrowser install   # downloads stealth Chromium binary

The browser is launched once per `main()` invocation and reused across all
routes and languages. Page navigation uses Playwright's `page.goto()` and
JavaScript execution uses `page.evaluate()` — replacing the old subprocess
calls to agent-browser. All JS evaluation blocks are preserved verbatim from
the agent-browser version.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Optional, Tuple

from cloakbrowser import launch as cloak_launch
from playwright.sync_api import Page, BrowserContext, Browser, TimeoutError as PWTimeout

VAULT_DIR = os.path.expanduser("~/.claude/dev-vault")


def evaluate(page: Page, js: str, default: Any = "") -> Any:
    """Run a JS expression via Playwright. Wraps errors so they don't kill the run."""
    try:
        return page.evaluate(js)
    except Exception as e:
        # Mirror agent-browser's "check=False" semantics — log and return default.
        print(f"  [evaluate] failed: {e!s:.200}")
        return default


def open_url(page: Page, url: str, wait_ms: int = 30000) -> None:
    """Navigate to URL. Waits for DOMContentLoaded; the rest is handled by wait_for_page_ready."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=wait_ms)
    except PWTimeout:
        # Slow page — keep going; wait_for_page_ready will decide if it's usable.
        print(f"  [open_url] goto timed out on {url} — continuing")


def load_vault(vault_key, role="admin"):
    path = os.path.join(VAULT_DIR, f"{vault_key}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No vault entry: {path}")
    with open(path) as f:
        data = json.load(f)
    creds = data.get("credentials", {}).get("roles", {}).get(role, {})
    if not creds:
        raise ValueError(f"No {role} creds in {path}")
    return creds


def login_form_password(page: Page, base_url, creds, lang):
    """Form-password login. Handles email/username + password forms broadly.

    Label-based field detection + React-compatible event dispatch + form.requestSubmit().
    Waits up to 6s for redirect away from /auth/login.
    """
    open_url(page, f"{base_url}/{lang}/auth/login")
    time.sleep(1.5)
    _try_fill_form(page, creds)
    for _ in range(20):
        time.sleep(0.5)
        url = str(evaluate(page, "location.href", default=""))
        if "/auth/" not in url and "/login" not in url:
            print(f"  [capture] login success -> {url}")
            time.sleep(1.5)
            return
    raise RuntimeError(
        f"login failed for {lang}: still at {url} after 10s. "
        f"Check that the vault credentials are valid for this environment."
    )


def login_otp_phone(page: Page, base_url, creds, lang, login_path="/login"):
    """OTP login for phone-based flows.

    Flow:
      1. Open the login URL.
      2. Auto-fill phone from vault + submit (triggers SMS).
      3. Read the 6-digit code from env var `ISO_OTP_CODE` if set, else prompt
         stdin — so Claude can relay the code the user typed in chat.
      4. Auto-fill OTP (handles 6-box layouts and single-input layouts) + submit.
      5. Wait for redirect away from /login (up to 15 s).
    """
    phone = creds.get("phone", "")
    if not phone:
        raise ValueError("OTP login requires 'phone' in vault creds")

    full_login = base_url.rstrip("/") + login_path
    print(f"  [otp] opening {full_login}")
    open_url(page, full_login)
    time.sleep(3.0)

    js_phone = (
        "(function(){"
        "  const phone = " + json.dumps(phone) + ";"
        "  const setVal = (el, v) => {"
        "    const s = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value');"
        "    if (s && s.set) s.set.call(el, v); else el.value = v;"
        "    el.dispatchEvent(new Event('input',{bubbles:true}));"
        "    el.dispatchEvent(new Event('change',{bubbles:true}));"
        "  };"
        "  let inp = document.querySelector('input[type=tel], input[autocomplete=tel], "
        "input[name*=phone i], input[name*=mobile i], input[placeholder*=phone i], "
        "input[placeholder*=mobile i], input[placeholder*=โทร], input[placeholder*=เบอร]');"
        "  if (!inp) inp = document.querySelector('input[type=text], input:not([type])');"
        "  if (inp) setVal(inp, phone);"
        "  const form = (inp && inp.form) || document.querySelector('form');"
        "  if (form && form.requestSubmit) { form.requestSubmit(); return 'form.requestSubmit:' + (inp?'ok':'noinp'); }"
        "  const btn = document.querySelector('button[type=submit], form button, button');"
        "  if (btn) { btn.click(); return 'btn.click:' + (inp?'ok':'noinp'); }"
        "  return 'no-submit-found';"
        "})()"
    )
    res = evaluate(page, js_phone)
    print(f"  [otp] phone submit: {res}")
    time.sleep(4.0)

    otp = os.environ.get("ISO_OTP_CODE", "").strip()
    if not otp:
        sys.stdout.write(f"  [otp] Enter 6-digit code sent to {phone}: ")
        sys.stdout.flush()
        otp = sys.stdin.readline().strip()
    if not (otp and otp.isdigit() and len(otp) == 6):
        raise RuntimeError(f"invalid OTP: {otp!r}")

    js_otp = (
        "(function(){"
        "  const code = " + json.dumps(otp) + ";"
        "  const setVal = (el, v) => {"
        "    const s = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value');"
        "    if (s && s.set) s.set.call(el, v); else el.value = v;"
        "    el.dispatchEvent(new Event('input',{bubbles:true}));"
        "    el.dispatchEvent(new Event('change',{bubbles:true}));"
        "  };"
        "  const boxes = document.querySelectorAll('input[maxlength=\"1\"]');"
        "  if (boxes && boxes.length >= 6) {"
        "    for (let i = 0; i < 6; i++) setVal(boxes[i], code[i]);"
        "    for (let i = 0; i < 6; i++) {"
        "      boxes[i].dispatchEvent(new KeyboardEvent('keyup',{key:code[i],bubbles:true}));"
        "    }"
        "    const form = boxes[5].form || document.querySelector('form');"
        "    if (form && form.requestSubmit) { form.requestSubmit(); return 'filled:6boxes:submit'; }"
        "    const btn = document.querySelector('button[type=submit], form button, button');"
        "    if (btn) { btn.click(); return 'filled:6boxes:btn'; }"
        "    return 'filled:6boxes:no-submit';"
        "  }"
        "  let inp = document.querySelector('input[autocomplete=one-time-code], "
        "input[inputmode=numeric], input[maxlength=\"6\"], input[name*=otp i], "
        "input[name*=code i], input[placeholder*=otp i], input[placeholder*=รหัส]');"
        "  if (!inp) {"
        "    const all = document.querySelectorAll('input[type=text], input[type=number], input:not([type])');"
        "    for (const a of all) { if (!/phone|mobile|โทร|เบอร/i.test((a.name||'') + (a.placeholder||''))) { inp = a; break; } }"
        "  }"
        "  if (inp) {"
        "    setVal(inp, code);"
        "    const form = inp.form || document.querySelector('form');"
        "    if (form && form.requestSubmit) { form.requestSubmit(); return 'filled:single:submit'; }"
        "    const btn = document.querySelector('button[type=submit], form button, button');"
        "    if (btn) { btn.click(); return 'filled:single:btn'; }"
        "    return 'filled:single:no-submit';"
        "  }"
        "  return 'no-otp-field';"
        "})()"
    )
    res = evaluate(page, js_otp)
    print(f"  [otp] code submit: {res}")

    last = ""
    for _ in range(30):
        time.sleep(0.5)
        url = str(evaluate(page, "location.href", default=""))
        last = url
        if "/login" not in url and "/auth/" not in url and "/verify" not in url:
            print(f"  [otp] login success -> {url}")
            time.sleep(2.0)
            return
    raise RuntimeError(f"OTP login failed: still at {last} after 15s")


def _try_fill_form(page: Page, creds):
    """Fill login form via label-matching + React-native setter + form.requestSubmit()."""
    user_value = creds.get("email") or creds.get("username") or ""
    pw_value = creds.get("password", "")
    js_fill = (
        "(function() {"
        "  const setNativeValue = (el, value) => {"
        "    const proto = Object.getPrototypeOf(el);"
        "    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;"
        "    if (setter) setter.call(el, value); else el.value = value;"
        "    el.dispatchEvent(new Event('input',  {bubbles: true}));"
        "    el.dispatchEvent(new Event('change', {bubbles: true}));"
        "  };"
        "  const findByLabel = (substrs) => {"
        "    const inputs = Array.from(document.querySelectorAll('input, textarea'));"
        "    for (const input of inputs) {"
        "      const id = input.id;"
        "      const label = id ? document.querySelector(`label[for=\"${id}\"]`) : null;"
        "      const text = ((label?.textContent || '') + ' ' +"
        "                    (input.placeholder || '') + ' ' +"
        "                    (input.name || '') + ' ' +"
        "                    (input.getAttribute('aria-label') || '')).toLowerCase();"
        "      if (substrs.some(s => text.includes(s))) return input;"
        "    } return null;"
        "  };"
        "  const pw = document.querySelector('input[type=password]');"
        "  let user = document.querySelector('input[type=email]')"
        "          || findByLabel(['email','username','user','login','ชื่อผู้ใช้']);"
        "  if (!user) {"
        "    const texts = Array.from(document.querySelectorAll('input[type=text], input:not([type])'));"
        "    user = texts[0] || null;"
        "  }"
        f"  if (user) setNativeValue(user, {json.dumps(user_value)});"
        f"  if (pw)   setNativeValue(pw,   {json.dumps(pw_value)});"
        "  const form = (pw && pw.form) || (user && user.form) || document.querySelector('form');"
        "  if (form && form.requestSubmit) { form.requestSubmit(); return 'form.requestSubmit'; }"
        "  const btn = document.querySelector("
        "    'button[type=submit], button.ant-btn-primary, form button, button');"
        "  if (btn) { btn.click(); return 'button.click'; }"
        "  return 'no-submit-found';"
        "})()"
    )
    result = evaluate(page, js_fill)
    print(f"  [capture] login form submit: {result}")


def switch_language(page: Page, lang, mode="click"):
    """Switch UI language.

    mode="click"                    — click a menu item whose text matches EN/ไทย
    mode="vue_i18n_localstorage"    — write lang to localStorage keys used by
                                      vue-i18n setups, then reload
    mode="none"                     — no-op (app is single-language)
    """
    if mode == "none":
        return
    if mode == "vue_i18n_localstorage":
        js = (
            "(function() {"
            f"  const l = {json.dumps(lang)};"
            "  try { localStorage.setItem('lang', l); } catch(e) {}"
            "  try { localStorage.setItem('locale', l); } catch(e) {}"
            "  try { localStorage.setItem('i18n', l); } catch(e) {}"
            "  try { localStorage.setItem('language', l); } catch(e) {}"
            "  location.reload(); return l;"
            "})()"
        )
        evaluate(page, js)
        time.sleep(1.5)
        return
    label_map = {"en": "English", "th": "ไทย"}
    label = label_map.get(lang, lang)
    js = (
        "(function() {"
        "  const candidates = document.querySelectorAll('"
        ".ant-dropdown-menu-item, .van-popover__action, [role=menuitem], li, a, button');"
        "  for (const el of candidates) {"
        f"    if (el.textContent.trim() === {json.dumps(label)}) {{ el.click(); return true; }}"
        "  } return false;"
        "})()"
    )
    evaluate(page, js)


def click_first_row(page: Page):
    """Click the first clickable row of a list table."""
    js = (
        "(function() {"
        "  const row = document.querySelector('.ant-table-row, tr[data-row-key], tbody tr');"
        "  if (row) { row.click(); return true; } return false;"
        "})()"
    )
    evaluate(page, js)


def resolve_dynamic_url(page: Page, base_url, route, lang):
    """Turn a template route like /buildings/[id]/edit into a live URL by:

      1. Building the list URL (everything BEFORE the first dynamic segment).
      2. Opening that list.
      3. Reading the first row's data-row-key (or extracting an ID from the
         first table cell's <a href>) to get a real record id.
      4. Substituting that id in, preserving any suffix segments AFTER [id]
         (e.g. /edit, /units, /detail).

    Returns the resolved URL or None if the list has no rows we can use.

    This replaces the old "strip [id], click first row, hope the router does
    the right thing" flow which broke for routes like /buildings/[id]/edit —
    Next.js catch-all matching would interpret "edit" as the [id] value and
    leave the detail page stuck in skeleton forever.
    """
    parts = route.strip("/").split("/")
    before_dyn, after_dyn, dyn_idx = [], [], -1
    for i, p in enumerate(parts):
        if p in ("[locale]", "[lang]", "[language]"):
            before_dyn.append(lang)
            continue
        if p.startswith("[") and p.endswith("]"):
            dyn_idx = i
            break
        before_dyn.append(p)
    if dyn_idx < 0:
        return None  # shouldn't happen for is_dynamic routes
    for p in parts[dyn_idx + 1:]:
        if p in ("[locale]", "[lang]", "[language]"):
            after_dyn.append(lang)
        elif p.startswith("[") and p.endswith("]"):
            after_dyn.append("")  # second dynamic segment; best-effort blank
        else:
            after_dyn.append(p)

    list_path = "/".join(p for p in before_dyn if p)
    list_url = f"{base_url.rstrip('/')}/{list_path}" if list_path else base_url.rstrip("/")
    open_url(page, list_url)
    wait_for_page_ready(page, timeout=15.0, settle=1.5, stable_checks=2)

    row_id_js = (
        "(function() {"
        "  const row = document.querySelector('"
        ".ant-table-tbody tr[data-row-key], tbody tr[data-row-key]');"
        "  if (row) {"
        "    const k = row.getAttribute('data-row-key');"
        "    if (k) return k;"
        "  }"
        "  const a = document.querySelector('"
        ".ant-table-tbody a[href], tbody a[href]');"
        "  if (a) {"
        "    try {"
        "      const u = new URL(a.href, location.origin);"
        "      const segs = u.pathname.split('/').filter(Boolean);"
        "      if (segs.length) return segs[segs.length - 1];"
        "    } catch (e) {}"
        "  }"
        "  const clickable = document.querySelector('"
        ".ant-table-row.ant-table-row-level-0, "
        "tr.clickable, tr[onclick], tbody tr');"
        "  if (clickable) {"
        "    const k = clickable.getAttribute('data-row-key')"
        "           || clickable.getAttribute('data-id')"
        "           || clickable.getAttribute('id');"
        "    if (k) return k;"
        "  }"
        "  return '';"
        "})()"
    )
    real_id = str(evaluate(page, row_id_js, default="")).strip()
    if not real_id or real_id in ("null", "undefined"):
        return None

    final_parts = [list_path, real_id] + [p for p in after_dyn if p]
    final_path = "/".join(p for p in final_parts if p)
    return f"{base_url.rstrip('/')}/{final_path}"


def dismiss_toasts(page: Page):
    """Remove transient ant-message / ant-notification toasts so they don't leak into shots."""
    js = (
        "(function() {"
        "  const sels = ['.ant-message', '.ant-notification',"
        "                '.ant-message-notice', '.ant-notification-notice'];"
        "  let n = 0;"
        "  for (const s of sels) {"
        "    document.querySelectorAll(s).forEach(el => { el.remove(); n++; });"
        "  }"
        "  return n;"
        "})()"
    )
    evaluate(page, js)


def page_error_reason(page: Page):
    """Return a non-empty string naming the error if the page is showing an error/alert state.

    Checks Ant Design error surfaces, Next.js runtime-error overlays (including
    the dev/prod error dialog and toast), and plain-text 404/500 markers in both
    EN and TH. Empty string = page is functional.
    """
    js = (
        "(function() {"
        "  const visible = (el) => {"
        "    if (!el) return false;"
        "    const r = el.getBoundingClientRect();"
        "    return r.width > 0 && r.height > 0;"
        "  };"
        "  const errSelectors = ["
        "    '.ant-result-error', '.ant-result-500', '.ant-result-404',"
        "    '.ant-result-warning',"
        "    '.ant-alert-error', '.ant-alert-warning',"
        "    '.ant-message-error', '.ant-notification-notice-error',"
        "    '[data-test=error-boundary]', '[role=alert]',"
        "    'nextjs-portal', '[data-nextjs-dialog]',"
        "    '[data-nextjs-dialog-overlay]', '[data-nextjs-toast]',"
        "    '[data-nextjs-toast-errors-parent]', '[data-nextjs-errors-dialog]',"
        "    '.nextjs-container-errors-header', '.nextjs-toast-errors'"
        "  ];"
        "  for (const s of errSelectors) {"
        "    const el = document.querySelector(s);"
        "    if (visible(el)) return 'selector:' + s;"
        "  }"
        "  const portal = document.querySelector('nextjs-portal');"
        "  if (portal && portal.shadowRoot) {"
        "    const inner = portal.shadowRoot.querySelector("
        "      '[data-nextjs-dialog], [data-nextjs-toast], .nextjs-toast-errors,"
        "       .nextjs-container-errors-header'"
        "    );"
        "    if (inner) return 'selector:nextjs-portal/shadow';"
        "  }"
        "  const body = (document.body && document.body.innerText) || '';"
        "  const patterns = ["
        "    /Application error/i,"
        "    /Something went wrong/i,"
        "    /This page could not be found/i,"
        "    /Page not found/i,"
        "    /Not [Ff]ound\\b/,"
        "    /Internal Server Error/i,"
        "    /Failed to (load|fetch)/i,"
        "    /Unable to (load|fetch|connect)/i,"
        "    /Unhandled Runtime Error/i,"
        "    /Unidentified Runtime Error/i,"
        "    /Unhandled Promise Rejection/i,"
        "    /Runtime Error/i,"
        "    /Network [Ee]rror/,"
        "    /ReferenceError:/,"
        "    /TypeError:/,"
        "    /SyntaxError:/,"
        "    /Module not found/i,"
        "    /Hydration failed/i,"
        "    /Text content does not match/i,"
        "    /Access [Dd]enied/,"
        "    /Forbidden/,"
        "    /Unauthorized/,"
        "    /เกิดข้อผิดพลาด/,"
        "    /ไม่พบหน้า/,"
        "    /ไม่พบทรัพยากร/,"
        "    /ไม่พบข้อมูล/,"
        "    /ขออภัย.{0,60}ไม่พบ/,"
        "    /ไม่สามารถ(เชื่อมต่อ|โหลด|ดึง)/,"
        "    /ลองใหม่อีกครั้ง/,"
        "    /ไม่มีสิทธิ์/,"
        "    /หมดอายุ/"
        "  ];"
        "  for (const p of patterns) {"
        "    const m = body.match(p);"
        "    if (m) return 'text:' + m[0];"
        "  }"
        "  const bodyTextLen = body.replace(/\\s+/g, '').length;"
        "  const visibleEls = document.body ? document.body.querySelectorAll('*') : [];"
        "  if (bodyTextLen < 10 && visibleEls.length < 20) {"
        "    return 'blank-body:textLen=' + bodyTextLen + ' els=' + visibleEls.length;"
        "  }"
        "  return '';"
        "})()"
    )
    out = str(evaluate(page, js, default="")).strip()
    return out if out and out not in ("null", "undefined") else ""


def inject_webfont(page: Page, lang):
    """When the page's default font lacks glyphs for `lang`, inject a Google
    Fonts stylesheet + @font-face fallback and rewrite the base font-family so
    every subsequent text render picks up the new font.

    Explicitly awaits `document.fonts.load("16px <family>")` for the target
    family — the catch-all `document.fonts.ready` resolves the moment no NEW
    fonts are pending, which on a slow cold cache can fire BEFORE our just-
    injected @import has started downloading. Forcing a named load() on the
    family we just asked for is the only way to block until the glyphs are
    actually rasterisable.
    """
    family_map = {
        "th": ("Noto Sans Thai", "Noto+Sans+Thai:wght@400;500;700"),
        "ja": ("Noto Sans JP",   "Noto+Sans+JP:wght@400;500;700"),
        "ko": ("Noto Sans KR",   "Noto+Sans+KR:wght@400;500;700"),
        "zh": ("Noto Sans SC",   "Noto+Sans+SC:wght@400;500;700"),
    }
    if lang not in family_map:
        return
    family, gurl = family_map[lang]
    js = (
        "(async function() {"
        "  const fam = " + json.dumps(family) + ";"
        "  const href = 'https://fonts.googleapis.com/css2?family=" + gurl + "&display=swap';"
        "  if (!document.querySelector(`link[data-iso-font=\"${fam}\"]`)) {"
        "    const link = document.createElement('link');"
        "    link.rel = 'stylesheet'; link.href = href;"
        "    link.setAttribute('data-iso-font', fam);"
        "    document.head.appendChild(link);"
        "  }"
        "  if (!document.querySelector(`style[data-iso-font=\"${fam}\"]`)) {"
        "    const style = document.createElement('style');"
        "    style.setAttribute('data-iso-font', fam);"
        "    style.textContent = `html, body, * { font-family: \"${fam}\", \"Noto Sans\", system-ui, sans-serif !important; }`;"
        "    document.head.appendChild(style);"
        "  }"
        "  try {"
        "    await Promise.race(["
        "      document.fonts.load(`700 16px \"${fam}\"`),"
        "      new Promise(r => setTimeout(r, 8000))"
        "    ]);"
        "    await Promise.race(["
        "      document.fonts.load(`400 16px \"${fam}\"`),"
        "      new Promise(r => setTimeout(r, 4000))"
        "    ]);"
        "    await document.fonts.ready;"
        "  } catch(e) {}"
        "  return fam + ':' + (document.fonts.check(`16px \"${fam}\"`) ? 'ready' : 'pending');"
        "})()"
    )
    res = evaluate(page, js)
    print(f"  [font] inject {lang} -> {res}")
    time.sleep(1.0)


def font_missing_reason(page: Page, lang):
    """Detect "tofu" box rendering — i.e. the page's fonts lack glyphs for the
    script of `lang`.  Returns a non-empty string describing the problem, or
    empty string if glyphs render correctly.

    Technique: measure a representative glyph vs a known-missing codepoint
    (U+E000 private use area) in the page's computed font.  If they render at
    the same advance width, the glyph is falling back to the same "missing
    glyph" box and the shot will contain squares.
    """
    probe = {"th": "กขคงจฉชซญณฐฑฒณถผฝพฟ", "ja": "あ亜", "ko": "가", "zh": "中文"}.get(lang, "")
    if not probe:
        return ""
    js = (
        "(function() {"
        "  const probe = " + json.dumps(probe) + ";"
        "  const c = document.createElement('canvas');"
        "  const ctx = c.getContext('2d');"
        "  const ff = getComputedStyle(document.body).fontFamily || 'sans-serif';"
        "  ctx.font = '24px ' + ff;"
        "  const miss = ctx.measureText('\\uE000').width;"
        "  const latn = ctx.measureText('M').width;"
        "  let matches_miss = 0;"
        "  for (const ch of probe) {"
        "    const w = ctx.measureText(ch).width;"
        "    if (Math.abs(w - miss) < 0.5 && Math.abs(w - latn) > 0.5) matches_miss++;"
        "  }"
        "  if (matches_miss >= Math.max(2, Math.floor(probe.length / 3))) {"
        "    return 'tofu:' + matches_miss + '/' + probe.length + ' ff=' + ff.slice(0, 60);"
        "  }"
        "  return '';"
        "})()"
    )
    out = str(evaluate(page, js, default="")).strip()
    return out if out and out not in ("null", "undefined") else ""


def font_missing_reason_auto(page: Page) -> Tuple[Optional[str], str]:
    """Detect tofu on whatever script is actually present in the rendered body."""
    js = (
        "(function(){"
        "  const t = (document.body && document.body.innerText) || '';"
        "  return {"
        "    th: /[\\u0E00-\\u0E7F]/.test(t),"
        "    ja: /[\\u3040-\\u30FF]/.test(t),"
        "    ko: /[\\uAC00-\\uD7AF]/.test(t),"
        "    zh: /[\\u4E00-\\u9FFF]/.test(t)"
        "  };"
        "})()"
    )
    present = evaluate(page, js, default={})
    if not isinstance(present, dict):
        return None, ""
    for script in ("th", "ja", "ko", "zh"):
        if present.get(script):
            reason = font_missing_reason(page, script)
            if reason:
                return script, reason
    return None, ""


# JS pre-injected into every page to track fetch/XHR activity for wait_for_page_ready.
NET_TRACKER_JS = (
    "(function(){"
    "  if (window.__iso_net_installed) return;"
    "  window.__iso_net_last = performance.now();"
    "  window.__iso_net_pending = 0;"
    "  const origFetch = window.fetch;"
    "  if (origFetch) {"
    "    window.fetch = function() {"
    "      window.__iso_net_pending++;"
    "      window.__iso_net_last = performance.now();"
    "      return origFetch.apply(this, arguments).finally(() => {"
    "        window.__iso_net_pending = Math.max(0, window.__iso_net_pending - 1);"
    "        window.__iso_net_last = performance.now();"
    "      });"
    "    };"
    "  }"
    "  const OX = window.XMLHttpRequest;"
    "  if (OX) {"
    "    const origOpen = OX.prototype.open;"
    "    const origSend = OX.prototype.send;"
    "    OX.prototype.open = function() { this.__iso_tracked = true; return origOpen.apply(this, arguments); };"
    "    OX.prototype.send = function() {"
    "      if (this.__iso_tracked) {"
    "        window.__iso_net_pending++;"
    "        window.__iso_net_last = performance.now();"
    "        this.addEventListener('loadend', () => {"
    "          window.__iso_net_pending = Math.max(0, window.__iso_net_pending - 1);"
    "          window.__iso_net_last = performance.now();"
    "        });"
    "      }"
    "      return origSend.apply(this, arguments);"
    "    };"
    "  }"
    "  window.__iso_net_installed = true;"
    "})()"
)


def wait_for_page_ready(page: Page, timeout=25.0, settle=2.5, stable_checks=3):
    """Wait for the page to be visually ready before screenshot.

    See agent-browser version for the full gate list — Playwright port behaves
    identically except that the network-activity tracker is pre-injected via
    `context.add_init_script()` on the BrowserContext rather than re-installed
    on every check. The poll JS reads the same `window.__iso_net_*` globals.
    """
    js = (
        "(function() {"
        "  if (document.readyState !== 'complete') return 'loading';"
        "  const visible = (el) => {"
        "    if (!el) return false;"
        "    const r = el.getBoundingClientRect();"
        "    if (r.width <= 1 || r.height <= 1) return false;"
        "    const st = getComputedStyle(el);"
        "    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) return false;"
        "    return true;"
        "  };"
        "  const anyVisible = (sel) => {"
        "    const els = document.querySelectorAll(sel);"
        "    for (const el of els) if (visible(el)) return true;"
        "    return false;"
        "  };"
        "  const skeletonSel = ["
        "    '.ant-skeleton-active', '.ant-skeleton',"
        "    '[class*=\"skeleton\"]:not(script):not(style)',"
        "    '[class*=\"Skeleton\"]:not(script):not(style)',"
        "    '.animate-pulse', '[class*=\"shimmer\"]:not(script):not(style)',"
        "    '[aria-busy=\"true\"]'"
        "  ];"
        "  for (const s of skeletonSel) {"
        "    if (anyVisible(s)) return 'busy:skeleton:' + s;"
        "  }"
        "  const spinnerSel = ["
        "    '.ant-spin-spinning', '.ant-spin-nested-loading .ant-spin',"
        "    '.ant-progress-status-active',"
        "    '[role=\"progressbar\"]',"
        "    '[class*=\"spinner\"]:not(script):not(style)',"
        "    '[class*=\"loader\"]:not(script):not(style)'"
        "  ];"
        "  for (const s of spinnerSel) {"
        "    if (anyVisible(s)) return 'busy:spinner:' + s;"
        "  }"
        "  const i18nKeyRe = /^[A-Z][A-Za-z0-9]+\\.[a-z][A-Za-z0-9]+$/;"
        "  const i18nSurfaces = ["
        "    '.ant-breadcrumb', '.ant-breadcrumb-link',"
        "    '.ant-page-header-heading-title', '.ant-page-header-heading-sub-title',"
        "    '.ant-typography', 'h1', 'h2', 'h3',"
        "    '.ant-menu-item', '.ant-menu-title-content',"
        "    '.ant-tabs-tab-btn', '.ant-card-head-title',"
        "    '.ant-descriptions-item-label', '.ant-form-item-label > label',"
        "    'label', 'title'"
        "  ];"
        "  for (const s of i18nSurfaces) {"
        "    const els = document.querySelectorAll(s);"
        "    for (const el of els) {"
        "      if (!visible(el)) continue;"
        "      const txt = (el.textContent || '').trim();"
        "      if (!txt || txt.length > 60 || txt.includes(' ')) continue;"
        "      if (i18nKeyRe.test(txt)) return 'busy:i18n-key:' + txt;"
        "    }"
        "  }"
        "  const imgs = Array.from(document.images).filter(visible);"
        "  for (const img of imgs) {"
        "    if (!img.complete || img.naturalWidth === 0) return 'busy:img:' + (img.src || '?').slice(-40);"
        "  }"
        "  if (window.__iso_net_installed) {"
        "    if ((window.__iso_net_pending || 0) > 0) return 'busy:xhr:' + window.__iso_net_pending;"
        "    const idle = performance.now() - (window.__iso_net_last || 0);"
        "    if (idle < 800) return 'busy:net-idle:' + Math.round(idle);"
        "  }"
        "  const contentSel = ["
        "    '.ant-table-tbody tr', '.ant-table-placeholder',"
        "    '.ant-card-body', '.ant-layout-content',"
        "    'main', 'article', '[data-ready=1]', 'form',"
        "    'table tbody tr', '[class*=\"content\"]'"
        "  ];"
        "  for (const s of contentSel) {"
        "    if (anyVisible(s)) return 'ready';"
        "  }"
        "  return 'no-content';"
        "})()"
    )
    deadline = time.time() + timeout
    consecutive_ready = 0
    last = "unknown"
    while time.time() < deadline:
        out = str(evaluate(page, js, default="")).strip()
        last = out
        if out == "ready":
            consecutive_ready += 1
            if consecutive_ready >= stable_checks:
                time.sleep(settle)
                return True, "ready"
        else:
            consecutive_ready = 0
        time.sleep(0.4)
    print(f"  [capture] page not fully ready after {timeout}s (state={last})")
    return False, last


def build_url(base_url, route, lang):
    """Substitute [locale]/:locale with lang. Blanks out other dynamic segments."""
    parts = []
    for seg in route.strip("/").split("/"):
        if seg in ("[locale]", "[lang]", "[language]"):
            parts.append(lang)
        elif seg in (":locale", ":lang", ":language"):
            parts.append(lang)
        elif seg.startswith("[") and seg.endswith("]"):
            parts.append("")  # dynamic — will be filled by click_first_row
        elif seg.startswith(":"):
            parts.append("")
        else:
            parts.append(seg)
    path = "/".join(p for p in parts if p)
    return f"{base_url.rstrip('/')}/{path}" if path else base_url.rstrip("/")


def capture_routes(page: Page, config, routes, lang, skip_login=False):
    """Screenshot every route for a language.

    skip_login=True assumes the browser context is already authenticated
    (useful for OTP flows where the human drove login by hand, and for multi-
    frontend configs sharing a single session).
    """
    out_dir = (config.lang_screenshots_dir(lang)
               if hasattr(config, 'lang_screenshots_dir')
               else os.path.join(config.SCREENSHOTS_DIR, lang))
    os.makedirs(out_dir, exist_ok=True)
    default_base = config.SYSTEM_URL.rstrip("/")

    vault_key = (config.AUTH.get("vault_key") if hasattr(config, "AUTH")
                 else getattr(config, "VAULT_KEY", ""))
    mode = (config.AUTH.get("mode") if hasattr(config, "AUTH")
            else getattr(config, "AUTH_MODE", "form_password"))
    role = (config.AUTH.get("role") if hasattr(config, "AUTH")
            else getattr(config, "AUTH_ROLE", "admin"))

    creds = None
    if not skip_login and vault_key:
        creds = load_vault(vault_key, role)
        if mode == "form_password":
            login_form_password(page, default_base, creds, lang)
        elif mode == "otp_phone":
            login_otp_phone(page, default_base, creds, lang)
    elif skip_login:
        print(f"  [{lang}] --skip-login set; assuming session is already authenticated")

    switch_language(page, lang)
    time.sleep(1)

    def _re_login():
        if not skip_login and creds and mode == "form_password":
            print(f"  [{lang}] session lost — re-logging in")
            login_form_password(page, default_base, creds, lang)

    is_logout = lambda r: "/auth/logout" in r.get("route", "") or r.get("id", "").endswith("logout")
    routes_ordered = [r for r in routes if not is_logout(r)] + [r for r in routes if is_logout(r)]

    switched_fronts = set()

    skipped = []
    for r in routes_ordered:
        base = r.get("base_url", default_base).rstrip("/")
        url = build_url(base, r.get("route", "/"), lang)
        out_path = os.path.join(out_dir, f"{r['id']}.png")
        route_is_auth = "/auth/" in r.get("route", "") or "/login" in r.get("route", "")
        fe_id = r.get("frontend_id", "default")
        try:
            if fe_id not in switched_fronts:
                i18n_mode = r.get("i18n_mode", "click")
                if i18n_mode and i18n_mode != "click":
                    open_url(page, base)
                    time.sleep(1.0)
                    switch_language(page, lang, mode=i18n_mode)
                switched_fronts.add(fe_id)

            if r.get("is_dynamic"):
                resolved = resolve_dynamic_url(page, base, r.get("route", "/"), lang)
                if not resolved:
                    skipped.append((r["id"], "no-row-in-list"))
                    print(f"  [{lang}] SKIP {r['id']:<36} no-row-in-list")
                    continue
                open_url(page, resolved)
                ready, state = wait_for_page_ready(page, timeout=20.0, settle=3.5, stable_checks=4)
            else:
                open_url(page, url)
                ready, state = wait_for_page_ready(page)

            if not skip_login:
                cur = str(evaluate(page, "location.href", default=""))
                if not route_is_auth and ("/auth/login" in cur or "/auth/register" in cur):
                    _re_login()
                    if r.get("is_dynamic"):
                        resolved = resolve_dynamic_url(page, base, r.get("route", "/"), lang)
                        if not resolved:
                            skipped.append((r["id"], "no-row-in-list"))
                            print(f"  [{lang}] SKIP {r['id']:<36} no-row-in-list")
                            continue
                        open_url(page, resolved)
                        ready, state = wait_for_page_ready(page, timeout=20.0, settle=3.5, stable_checks=4)
                    else:
                        open_url(page, url)
                        ready, state = wait_for_page_ready(page)

            if not ready and state.startswith("busy:"):
                if os.path.exists(out_path):
                    os.remove(out_path)
                skipped.append((r["id"], state))
                print(f"  [{lang}] SKIP {r['id']:<36} {state}")
                continue

            dismiss_toasts(page)

            if not route_is_auth:
                reason = page_error_reason(page)
                if reason:
                    time.sleep(3.0)
                    dismiss_toasts(page)
                    reason = page_error_reason(page)
                if reason:
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    skipped.append((r["id"], reason))
                    print(f"  [{lang}] SKIP {r['id']:<36} {reason}")
                    continue

            tofu_script, glyph_reason = font_missing_reason_auto(page)
            if tofu_script:
                print(f"  [{lang}] tofu on {r['id']} ({glyph_reason}) — injecting webfont for {tofu_script}")
                inject_webfont(page, tofu_script)
                time.sleep(0.8)
                tofu_script, glyph_reason = font_missing_reason_auto(page)
                if tofu_script:
                    print(f"  [{lang}] still tofu ({glyph_reason}) — reload + re-inject")
                    evaluate(page, "location.reload()")
                    time.sleep(2.0)
                    inject_webfont(page, tofu_script)
                    wait_for_page_ready(page, timeout=15.0, settle=1.5, stable_checks=2)
                    time.sleep(0.6)
                    tofu_script, glyph_reason = font_missing_reason_auto(page)
                    if tofu_script:
                        print(f"  [{lang}] SKIP {r['id']:<36} tofu-unresolvable:{glyph_reason}")
                        if os.path.exists(out_path):
                            os.remove(out_path)
                        skipped.append((r["id"], f"tofu-unresolvable:{glyph_reason}"))
                        continue

            if not route_is_auth:
                late_err = page_error_reason(page)
                if late_err:
                    print(f"  [{lang}] SKIP {r['id']:<36} late-error:{late_err}")
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    skipped.append((r["id"], f"late-error:{late_err}"))
                    continue

            page.screenshot(path=out_path, full_page=True)
            print(f"  [{lang}] {r['id']:<40} {url}")
        except Exception as e:
            print(f"  [{lang}] FAIL {r['id']}: {e}")

    if skipped:
        print(f"  [{lang}] skipped {len(skipped)} routes with error/alert state")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file", required=True)
    parser.add_argument("--analysis-file", default="")
    parser.add_argument("--langs", default="")
    parser.add_argument("--headed", action="store_true", help="show the browser window (for debugging)")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import ProjectConfig
    import discover

    cfg = ProjectConfig.from_json(args.config_file)
    langs = args.langs.split(",") if args.langs else cfg.LANGUAGES

    frontend_path = (cfg.ROUTES.get("frontend_path") if hasattr(cfg, "ROUTES")
                     else "frontend/app")
    ignore = cfg.ROUTES.get("ignore") if hasattr(cfg, "ROUTES") else None
    routes = discover.walk(cfg.LOCAL_REPO, frontend_path, ignore)
    print(f"Discovered {len(routes)} routes")

    # Launch CloakBrowser (returns a Playwright Browser). Single instance per run.
    # `humanize=True` adds human-like mouse/keyboard timing — useful even when our
    # targets are our own apps, since it makes the automation behave more naturally
    # for forms with debounced validators.
    browser: Browser = cloak_launch(headless=not args.headed, humanize=True)
    context: BrowserContext = browser.new_context(viewport={"width": 1440, "height": 900})
    # Pre-inject the network tracker into every page in this context.
    context.add_init_script(NET_TRACKER_JS)
    page: Page = context.new_page()

    try:
        for lang in langs:
            print(f"\n=== Capturing {lang.upper()} ===")
            capture_routes(page, cfg, routes, lang)
    finally:
        try:
            context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
