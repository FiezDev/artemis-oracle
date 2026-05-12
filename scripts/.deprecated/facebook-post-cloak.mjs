#!/usr/bin/env node
// Facebook poster via cloakbrowser (Playwright-flavoured stealth Chromium).
//
// Replaces the legacy scripts/facebook-post.py (which uses agent-browser).
// Profile is persistent at ~/.config/facebook-browser-profile so login
// survives across runs; first run should use --login-only --headed to sign
// in interactively, after which subsequent posts run headless.
//
// USAGE
//   # Vault flow (preferred): credentials are managed in the qone dashboard
//   # at /credentials and pulled by --credential <label> at post time.
//   node scripts/facebook-post-cloak.mjs \
//     --credential qonecompany-fb \
//     --page-id 1136813799507714 \
//     --text "Caption body…" \
//     --image /abs/path/to/image.jpg
//
//   # Test that credentials work (no post)
//   node scripts/facebook-post-cloak.mjs --credential qonecompany-fb --test-login
//
//   # Manual sign-in fallback (visible browser, user types creds + 2FA)
//   node scripts/facebook-post-cloak.mjs --login-only --headed
//
//   # text-only (only allowed when --allow-text-only)
//   node scripts/facebook-post-cloak.mjs --credential qonecompany-fb --text "Hello" --allow-text-only
//
// EXIT CODES
//   0  posted successfully (writes JSON manifest to gen-output/facebook-post/)
//   2  not logged in — run with --login-only first
//   3  required flag missing or image missing
//   4  composer/post button never appeared
//   5  Facebook returned a checkpoint / 2FA wall after composer submit
//
// OUTPUT
//   On success prints a single JSON line on stdout:
//   { "ok": true, "url": "<post permalink or m.facebook composer>",
//     "screenshot": "<path>", "manifest": "<path>", "pageId": "..." }

import { launchPersistentContext, ensureBinary } from 'cloakbrowser';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { homedir } from 'node:os';

// ── CLI ─────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const flag = (n) => argv.includes(`--${n}`);
const arg = (n, fb) => {
  const i = argv.indexOf(`--${n}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fb;
};

const HEADED = flag('headed');
const HEADLESS = !HEADED;
const LOGIN_ONLY = flag('login-only');
const TEST_LOGIN = flag('test-login');
const ALLOW_TEXT_ONLY = flag('allow-text-only');
const TEXT = arg('text', '');
const IMAGE = arg('image', '');
const PAGE_ID = arg('page-id', '');
const CREDENTIAL = arg('credential', '');           // label, e.g. "qonecompany-fb"
const CREDENTIAL_ID = arg('credential-id', '');     // alternative — direct uuid
const PROFILE_DIR = arg('profile', resolve(homedir(), '.config/facebook-browser-profile'));
const TIMEOUT_MS = parseInt(arg('timeout', '60000'), 10);
const REPO_ROOT = resolve(homedir(), 'Dev/artemis-oracle');
const OUT_DIR = join(REPO_ROOT, 'gen-output/facebook-post');
const QONE_API = process.env.QONE_API_URL || 'http://localhost:5501/api/v1';
const SERVICE_SECRET = process.env.SERVICE_SECRET || '';

mkdirSync(PROFILE_DIR, { recursive: true });
mkdirSync(OUT_DIR, { recursive: true });

// Ensure context is always closed cleanly — otherwise headless Chromium leaks
// and holds the profile's SingletonLock, breaking the next run.
let _context = null;
const __cleanup = async () => {
  if (_context) {
    try { await _context.close(); } catch {}
    _context = null;
  }
};
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP', 'beforeExit']) {
  process.on(sig, async () => { await __cleanup(); if (sig !== 'beforeExit') process.exit(130); });
}
process.on('uncaughtException', async (e) => { console.error('[fb-post] uncaught:', e.message); await __cleanup(); process.exit(1); });

const TS = new Date().toISOString().replace(/[:.]/g, '-');

function die(code, msg) {
  process.stderr.write(`[fb-post] ${msg}\n`);
  process.exit(code);
}

function log(...parts) {
  process.stderr.write(`[fb-post ${new Date().toISOString().slice(11, 19)}] ${parts.join(' ')}\n`);
}

if (!LOGIN_ONLY && !TEST_LOGIN) {
  if (!TEXT) die(3, '--text is required (or use --login-only / --test-login)');
  if (!IMAGE && !ALLOW_TEXT_ONLY) {
    die(3, '--image is required unless --allow-text-only is passed (AI Inspire posts need a square image)');
  }
  if (IMAGE && !existsSync(IMAGE)) die(3, `--image path does not exist: ${IMAGE}`);
}

// ── credential fetch (vault flow) ───────────────────────────────────────
async function fetchCredentialFromVault() {
  if (!CREDENTIAL && !CREDENTIAL_ID) return null;
  if (!SERVICE_SECRET) {
    die(3, 'SERVICE_SECRET env var is required to use --credential (set it from dashboard/api/.env)');
  }
  let id = CREDENTIAL_ID;
  if (!id) {
    const listRes = await fetch(`${QONE_API}/credentials`, {
      headers: { 'X-Service-Token': SERVICE_SECRET, 'X-Agent-ID': 'artemis' },
    });
    if (!listRes.ok) die(3, `credentials list failed: ${listRes.status} ${await listRes.text()}`);
    const all = await listRes.json();
    const hit = all.find((c) => c.label === CREDENTIAL);
    if (!hit) die(3, `credential not found by label: ${CREDENTIAL}`);
    id = hit.id;
  }
  const useRes = await fetch(`${QONE_API}/credentials/${id}/use`, {
    method: 'POST',
    headers: { 'X-Service-Token': SERVICE_SECRET, 'X-Agent-ID': 'artemis', 'content-type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!useRes.ok) die(3, `credential reveal failed: ${useRes.status} ${await useRes.text()}`);
  const body = await useRes.json();
  return body; // { id, label, platform, account, kind, payload: { password, totp_seed? } }
}

// ── browser setup ───────────────────────────────────────────────────────
log('Ensuring cloakbrowser binary…');
await ensureBinary();

log(`Launching cloakbrowser (headless=${HEADLESS}) profile=${PROFILE_DIR}`);
const context = await launchPersistentContext({
  userDataDir: PROFILE_DIR,
  headless: HEADLESS,
  viewport: { width: 414, height: 896 },
  // Mobile UA → m.facebook.com layout, stable selectors
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  locale: 'en-US',
});
_context = context;

const page = context.pages()[0] || (await context.newPage());
page.setDefaultTimeout(TIMEOUT_MS);

// ── helpers ─────────────────────────────────────────────────────────────
async function isLoggedIn() {
  await page.goto('https://m.facebook.com/', { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });
  // Logged-in UI shows the composer prompt; logged-out shows the email/pass form.
  const composer = await page.$('div[aria-label*="What\'s on your mind"], input[name="email"]');
  if (!composer) return false;
  const tag = await composer.evaluate((el) => el.tagName.toLowerCase()).catch(() => '');
  return tag === 'div'; // composer = logged in, input = login form
}

async function shot(name) {
  const p = join(OUT_DIR, `${TS}_${name}.png`);
  await page.screenshot({ path: p, fullPage: false }).catch(() => {});
  return p;
}

// ── login-only mode ─────────────────────────────────────────────────────
if (LOGIN_ONLY) {
  log('Login-only mode. Opening m.facebook.com — sign in manually, then close the window or press Ctrl+C.');
  await page.goto('https://m.facebook.com/login', { waitUntil: 'domcontentloaded' });
  // Wait until either composer appears (logged in) or the window is closed.
  await page.waitForSelector('div[aria-label*="What\'s on your mind"]', { timeout: 10 * 60 * 1000 })
    .then(() => log('Login detected ✓'))
    .catch(() => log('Timed out / browser closed before login completed.'));
  await shot('login-final');
  await context.close();
  process.exit(0);
}

// ── auto-login via vault credential ─────────────────────────────────────
async function autoLogin(cred) {
  log(`Auto-login with credential "${cred.label}" account=${cred.account}`);
  await page.goto('https://m.facebook.com/login', { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });
  // Slight settle so JS-rendered tokens are present before we fill the form
  await page.waitForTimeout(800);
  await shot('autologin-pre');

  // Fill email — type with small delay instead of .fill (more human-like; FB
  // anti-bot is sensitive to atomic field population on suspicious devices).
  const emailSel = 'input[name="email"], input[type="email"]';
  await page.waitForSelector(emailSel, { timeout: 15000 });
  await page.click(emailSel);
  await page.type(emailSel, cred.account, { delay: 35 });

  // Fill password — same human-typing pattern.
  const passSel = 'input[name="pass"], input[type="password"]';
  await page.click(passSel);
  await page.type(passSel, cred.payload.password, { delay: 40 });
  await page.waitForTimeout(400);
  await shot('autologin-filled');

  // Submit. Prefer real click on the button; fall back to Enter.
  const submitBtn = await page.$('button[name="login"], button[type="submit"], button:has-text("Log in"), div[role="button"]:has-text("Log in")');
  if (submitBtn) {
    await submitBtn.click({ timeout: 10000 }).catch(async () => {
      await page.press(passSel, 'Enter').catch(() => {});
    });
  } else {
    await page.press(passSel, 'Enter').catch(() => {});
  }
  // Wait for either a navigation OR a long delay (FB may do JS-only state changes).
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
  await shot('autologin-post');

  const url = page.url();
  log(`Post-submit URL: ${url}`);

  // 2FA / checkpoint detection
  if (/checkpoint|two_factor|two_step|approvals|confirm_your_identity/i.test(url)) {
    await shot('2fa-wall');
    die(5, `Facebook 2FA/checkpoint at ${url}. Either pass --headed for manual handling, or add a TOTP seed to the credential in /credentials.`);
  }

  // "Save login info" prompt sometimes appears — click "Not now"
  const notNow = await page.$('div[role="button"]:has-text("Not now"), button:has-text("Not now"), a:has-text("Not Now")');
  if (notNow) {
    log('Dismissing "Save login info" prompt');
    await notNow.click().catch(() => {});
    await page.waitForLoadState('domcontentloaded', { timeout: 10000 }).catch(() => {});
  }

  // Error detection: still on login means creds rejected
  if (/\/login/.test(page.url())) {
    const errText = await page.locator('text=/incorrect|wrong|try again/i').first().textContent({ timeout: 2000 }).catch(() => '');
    die(2, `Login appears to have failed — still on /login (${errText || 'no specific error message'}). Check credentials in /credentials.`);
  }
}

// ── post flow ───────────────────────────────────────────────────────────
const targetUrl = PAGE_ID
  ? `https://m.facebook.com/${PAGE_ID}`
  : 'https://m.facebook.com/';

log(`Navigating to ${targetUrl}`);
await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });

// Check login state — try auto-login if not, before bailing
let loggedIn = await isLoggedIn();
if (!loggedIn) {
  const cred = await fetchCredentialFromVault();
  if (cred && cred.kind === 'web_password') {
    await autoLogin(cred);
    loggedIn = await isLoggedIn();
  }
}
if (!loggedIn) {
  await shot('not-logged-in');
  die(2, 'Not logged in. Either pass --credential <label> (managed in dashboard /credentials) or run --login-only --headed.');
}

if (TEST_LOGIN) {
  log('TEST-LOGIN ✓ — session valid.');
  const sp = await shot('test-login-ok');
  await context.close();
  process.stdout.write(JSON.stringify({ ok: true, loggedIn: true, account: (await fetchCredentialFromVault())?.account ?? null, screenshot: sp }) + '\n');
  process.exit(0);
}

// Navigate to the page's composer (managed pages have a "Create post" CTA at the top)
if (PAGE_ID) {
  await page.goto(`https://m.facebook.com/${PAGE_ID}`, { waitUntil: 'domcontentloaded' });
}

// Click the "What's on your mind?" composer
log('Opening composer…');
const composerSel = 'div[aria-label*="What\'s on your mind"], a[aria-label*="Create post"], div[role="button"]:has-text("What\'s on your mind")';
try {
  await page.click(composerSel, { timeout: 15000 });
} catch (e) {
  await shot('composer-missing');
  die(4, `Could not click composer (${e.message?.slice(0, 80)})`);
}

// Wait for composer textarea
await page.waitForSelector('div[contenteditable="true"], textarea[name="xc_message"]', { timeout: TIMEOUT_MS })
  .catch(async () => {
    await shot('composer-no-textarea');
    die(4, 'Composer textarea never appeared');
  });

// Type text
log(`Typing text (${TEXT.length} chars)`);
const textarea = await page.$('div[contenteditable="true"], textarea[name="xc_message"]');
await textarea.click();
await textarea.type(TEXT, { delay: 8 });

// Attach image
if (IMAGE) {
  log(`Attaching image: ${IMAGE}`);
  // m.facebook.com composer has a hidden <input type="file">; setting files directly works in stealth Chromium
  const fileInput = await page.$('input[type="file"]');
  if (!fileInput) {
    await shot('no-file-input');
    die(4, 'No file input element found in composer');
  }
  await fileInput.setInputFiles(IMAGE);
  // Wait for thumbnail preview
  await page.waitForSelector('img[src*="scontent"], img[alt*="Photo"]', { timeout: 30000 }).catch(() => {
    log('warning: image preview not detected, posting anyway');
  });
}

await shot('pre-post');

// Click Post
log('Clicking Post…');
const postBtnSel = 'button[type="submit"]:has-text("Post"), div[role="button"]:has-text("Post"), button:has-text("Post")';
try {
  await page.click(postBtnSel, { timeout: 15000 });
} catch (e) {
  await shot('post-button-missing');
  die(4, `Could not click Post button: ${e.message?.slice(0, 80)}`);
}

// Wait for navigation / confirmation
await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {});
const finalUrl = page.url();
await shot('post-final');

// Detect checkpoint
if (/checkpoint|confirm_your_identity|two_factor/i.test(finalUrl)) {
  die(5, `Facebook returned a checkpoint/2FA wall: ${finalUrl}`);
}

const manifest = {
  ok: true,
  url: finalUrl,
  pageId: PAGE_ID || null,
  textChars: TEXT.length,
  image: IMAGE || null,
  postedAt: new Date().toISOString(),
  profile: PROFILE_DIR,
};
const manifestPath = join(OUT_DIR, `${TS}_manifest.json`);
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

await context.close();

// Single JSON line on stdout for callers to parse
process.stdout.write(JSON.stringify({
  ok: true,
  url: finalUrl,
  screenshot: join(OUT_DIR, `${TS}_post-final.png`),
  manifest: manifestPath,
  pageId: PAGE_ID || null,
}) + '\n');
