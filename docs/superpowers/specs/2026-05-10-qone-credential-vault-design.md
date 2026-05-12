# qone_corp Credential Vault + Social Login Adapters — Design

**Date:** 2026-05-10
**Status:** Draft, pending spec review
**Owner:** Fiez
**Implementation target:** `qone_corp/dashboard/` (vault) + `qone_corp/social-login/` (adapters)

---

## 1. Problem statement

The `qone_corp/social-login/` package today supports two platforms (TikTok, Facebook) and accepts credentials only via CLI flags or environment variables. Workflows in the qone_corp dashboard cannot pick a credential at run-time, secrets live in plaintext on disk, and there is no support for additional platforms (Google services, ChatGPT) that the user needs to automate.

The goal of this design is to add:

1. **An encrypted credential store** in the qone_corp dashboard, with a UI for adding/removing credentials and an API surface for the workflow runner to consume them.
2. **Login adapters** for Google (covering Gemini and `labs.google/flow`) and ChatGPT (web), in addition to TikTok and Facebook.
3. **A workflow runner integration** that lets a workflow step say "log in as credential ID X" and pause to a human-review gate when an unsolvable challenge appears.

The use case is hands-off automation. A workflow fires unattended, the runner asks the vault for a credential, the adapter logs in and continues. A first-time **warm-up** per account is the only step that requires a human, and only because Google and OpenAI both throw "is this you?" challenges on never-before-seen device fingerprints.

---

## 2. Decisions log

These were settled during brainstorming. They constrain everything below.

| # | Question | Choice | Rationale |
|---|---|---|---|
| 1 | What is "Google Flow"? | `labs.google/flow` (Veo / AI filmmaking) | Same `accounts.google.com` login as Gemini; only post-login URL differs. One Google credential covers both. |
| 2 | How hands-on should logins be? | **Fully hands-off everywhere** (with one-time warm-up) | User accepts the realistic shape: one assisted warm-up per account, then headless cookie reuse forever, with a password+TOTP fallback when cookies expire. |
| 3 | 2FA status of accounts? | **All 2FA-enabled and TOTP seeds available** | Vault stores password + TOTP seed → adapter generates 6-digit code on-the-fly → no manual code typing during fallback re-login. |
| 4 | OpenAI CLI scope? | Both `codex` browser-flow and `openai` API-key | Vault data model supports `web_password` AND `api_key` credential kinds. Codex flow consumes the warm chatgpt.com session; `openai` CLI just reads the key. |
| 5 | Vault encryption design? | **Envelope encryption: KEK in env + per-row DEK** | Standard pattern. Allows KEK rotation without re-encrypting every payload, and per-row revocation by deleting the row's DEK. |
| 6 | UI scope for v1? | **List + Create + Delete** (no edit) | Fastest path to working vault. Edit-in-place deferred to Phase 2; for now you delete + recreate. |

---

## 3. Architecture overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  qone_corp/dashboard/  (existing Next.js + Bun/Hono + PG)                │
│                                                                          │
│  frontend/app/credentials/page.tsx  ◄── new UI (list, create, delete)    │
│             │                                                            │
│             │ TanStack Query                                             │
│             ▼                                                            │
│  api/src/routes/credentials.ts      ◄── new routes                       │
│             │                                                            │
│             │ Drizzle                                                    │
│             ▼                                                            │
│  Postgres `credentials` table       ◄── new table, envelope-encrypted    │
│             ▲                                                            │
│             │ /use, /status (X-Internal-Token)                           │
│             │                                                            │
│  api/runner/adapters/social-login.ts  ◄── new runner adapter             │
│             │                                                            │
│             │ shells out to                                              │
│             ▼                                                            │
└─────────────│────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  qone_corp/social-login/  (existing standalone TS package)               │
│                                                                          │
│  src/cli.ts          ◄── adds `from-vault --id <uuid>` command           │
│  src/vault.ts        ◄── NEW: fetches credential, reports status         │
│  src/totp.ts         ◄── NEW: TOTP code generator (otpauth lib)          │
│  src/google.ts       ◄── NEW: Google login (TOTP-aware, fingerprint-     │
│                              stable, falls back to needs_human)          │
│  src/openai_web.ts   ◄── NEW: chatgpt.com login                          │
│  src/tiktok.ts       ◄── refactored: loginTikTokFromVault entry          │
│  src/facebook.ts     ◄── refactored: loginFacebookFromVault entry        │
│  src/browser.ts      ◄── extended: accepts fingerprint_seed              │
└──────────────────────────────────────────────────────────────────────────┘
```

The vault and the adapters are split across **two packages on purpose**: the dashboard owns storage + UI; the social-login package owns Playwright + CloakBrowser. The CLI is the integration boundary, mirroring the existing `dashboard/api/runner/adapters/hermes-cli.ts` and `openclaw-cli.ts` patterns.

---

## 4. Data model

### 4.1 New table: `credentials`

```sql
CREATE TYPE credential_platform AS ENUM (
  'tiktok', 'facebook', 'google', 'openai_web', 'openai_api'
);
CREATE TYPE credential_kind AS ENUM (
  'web_password', 'api_key', 'oauth_token'
);

CREATE TABLE credentials (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- identity (clear, used for the picker and the UI)
  label                    text NOT NULL,
  platform                 credential_platform NOT NULL,
  account                  text NOT NULL,          -- email / username; "—" for api_key
  kind                     credential_kind NOT NULL,

  -- envelope encryption: DEK wrapped by KEK, payload wrapped by DEK
  dek_ct                   bytea NOT NULL,         -- KEK-encrypted DEK
  dek_iv                   bytea NOT NULL,
  payload_ct               bytea NOT NULL,         -- DEK-encrypted JSON payload
  payload_iv               bytea NOT NULL,

  -- operational metadata (clear; useful in UI/runner without decrypt)
  fingerprint_seed         text NOT NULL,          -- stable CloakBrowser seed
  proxy_ref                text,                   -- optional, Phase 2

  -- warm session for headless reuse (encrypted with the same row DEK)
  warm_session_state_ct    bytea,
  warm_session_state_iv    bytea,
  warm_session_state_at    timestamptz,

  -- telemetry
  last_used_at             timestamptz,
  last_status              text,
  last_error               text,

  created_at               timestamptz NOT NULL DEFAULT now(),
  updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ON credentials (platform, account, label);
```

### 4.2 Decrypted payload shape (the JSON sealed inside `payload_ct`)

```ts
type Payload =
  | {
      kind: "web_password";
      password: string;
      totp_seed?: string;       // Base32, used by totp() helper
      backup_codes?: string[];  // optional, one-time, future fallback
    }
  | {
      kind: "api_key";
      api_key: string;
    }
  | {
      kind: "oauth_token";
      access_token: string;
      refresh_token?: string;
      expires_at?: string;      // ISO 8601
    };
```

### 4.3 Crypto envelope

* **Algorithm:** AES-256-GCM throughout (authenticated encryption, integrity guaranteed).
* **KEK:** 32 random bytes in `QONE_VAULT_KEY` env var. Loaded at API process start; never persisted; never sent over the wire.
* **DEK:** 32 random bytes generated per credential at create time. Used to encrypt both `payload_ct` and `warm_session_state_ct`.
* **DEK wrapping:** the DEK is itself encrypted by the KEK, and the ciphertext lives in `dek_ct`. Decrypting any field requires unwrapping the DEK first.
* **KEK rotation:** unwrap each row's DEK with the old KEK, rewrap with the new KEK, update `dek_ct` + `dek_iv`. Payload ciphertexts are not touched.
* **Per-row revocation:** `DELETE FROM credentials WHERE id = $1` permanently destroys the DEK; the payload ciphertext becomes unrecoverable.

The crypto helper lives at `dashboard/api/src/lib/crypto-envelope.ts`. Estimated size: ~80 lines (Node `crypto` module, `randomBytes` + `createCipheriv("aes-256-gcm")` + auth tag handling). No new npm dependency.

---

## 5. API surface

All routes live at `/api/v1/credentials`, implemented in `dashboard/api/src/routes/credentials.ts`.

### 5.1 Public-to-the-dashboard endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET`    | `/credentials`        | local-only | List rows. Returns `{id, label, platform, account, kind, fingerprint_seed, last_used_at, last_status}` per row. **Never** returns ciphertext or plaintext. |
| `POST`   | `/credentials`        | local-only | Create. Body has decrypted `payload`; server generates DEK, wraps with KEK, inserts. Returns `{id}`. |
| `DELETE` | `/credentials/:id`    | local-only | Delete row. Returns 204. |

"local-only" means the route is unauthenticated within the loopback API, identical to every existing dashboard route — this matches the dashboard's single-user / localhost-binding security model. The plaintext password traverses loopback (browser → port 5500 → port 5501) when you submit the create form; this is the unavoidable cost of using a UI for credential entry, and never leaves the host.

### 5.2 Internal endpoints (runner-only)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/credentials/:id/use`    | `X-Internal-Token: $EVENT_BRIDGE_SECRET` | Returns the **decrypted** payload, fingerprint seed, and last warm session state. Optional body `update_session_state` writes a refreshed session back. |
| `POST` | `/credentials/:id/status` | `X-Internal-Token: $EVENT_BRIDGE_SECRET` | Runner reports `{status, error?}`. Updates `last_status`, `last_error`, `last_used_at`. |

### 5.3 Wire format for `/use`

**Request body (optional):**
```jsonc
{ "update_session_state": "<base64 storage_state JSON>" }
```

**Response body:**
```jsonc
{
  "id": "uuid",
  "label": "qoneidol-tiktok",
  "platform": "tiktok",
  "account": "qoneidol@gmail.com",
  "kind": "web_password",
  "fingerprint_seed": "1234567890",
  "payload": {
    "kind": "web_password",
    "password": "...",
    "totp_seed": "JBSW..."
  },
  "warm_session_state": "<base64 storage_state JSON>"   // null if no warm session yet
}
```

The split between `/use` and `/status` keeps the decrypt surface small: `/status` can update telemetry without re-running decrypt, and a runner that already has the payload can report status without leaking it back.

### 5.4 Out of scope for v1

* No JWT or per-user auth. Dashboard is single-user, localhost-bound.
* No request signing beyond the existing internal-token pattern.
* No request-rate limiting on `/use` (the runner takes a per-credential advisory lock; see §8).

---

## 6. UI

### 6.1 Page layout

`frontend/app/credentials/page.tsx` — a single screen, no detail view. Matches the existing dashboard's table-based pages (e.g. `/agents`, `/tasks`).

```
┌─────────────────────────────────────────────────────────────────┐
│ Credentials                              [ + New Credential ]   │
├─────────────────────────────────────────────────────────────────┤
│ Label          Platform   Account              Kind    Used     │
│ qoneidol-tt    TikTok     qoneidol@gmail.com   pwd     2m ago  🟢
│ qonecorp-fb    Facebook   QoneCompany@gmail    pwd     1h ago  🟢
│ bjgdrx-google  Google     Bjgdrx@gmail.com     pwd     —       ⚪
│ ittitask-cgpt  ChatGPT    Itti.task@gmail.com  pwd     3d ago  🟡
│ ittibiz-cgpt   ChatGPT    ittipolbiz@gmail     pwd     5m ago  🟢
└─────────────────────────────────────────────────────────────────┘
```

Status dot = `last_status`. 🟢 logged_in · 🟡 needs_human · 🔴 bad_credentials/error · ⚪ never used. Hover = `last_error`.

A `[⋯]` per-row dropdown contains a single action: **Delete** (with confirmation modal). No edit, no reveal.

### 6.2 New Credential modal

A single form with conditional fields driven by **Platform** selection.

* Always: `Label`, `Platform`, `Account`.
* Platform = TikTok / Facebook / Google / ChatGPT → `kind = web_password`, show `Password`, `TOTP seed`, optional collapsed `Backup codes` paste area.
* Platform = OpenAI API → `kind = api_key`, show `API key`, hide other fields.

On submit: `POST /api/v1/credentials`, modal closes, table re-fetches. New row's status is ⚪ until first warm-up.

### 6.3 Sidebar nav

`components/sidebar.tsx` gets a new entry between "Processes" and "Automation":

```
Credentials   (key icon)   /credentials
```

### 6.4 Deliberately not in v1

* Reveal / view-password.
* Edit-in-place — delete + recreate is the model.
* Tag / search / filter (table is short, ≤20 rows realistically).
* `<CredentialPicker>` component for the workflow builder.
* Per-credential audit log of decrypts.

---

## 7. Login adapters

All live in `qone_corp/social-login/src/`.

### 7.1 New file: `totp.ts`

Wraps the `otpauth` npm package. ~30 lines.

```ts
import { TOTP, Secret } from "otpauth";
export function totp(seedBase32: string): string {
  return new TOTP({
    secret: Secret.fromBase32(seedBase32),
    digits: 6,
    period: 30,
  }).generate();
}
```

### 7.2 New file: `vault.ts`

The only file in the package that knows the dashboard API exists.

```ts
export async function fetchCredential(id: string): Promise<VaultEntry>;
export async function reportStatus(id: string, status: LoginStatus, error?: string): Promise<void>;
export async function pushSessionState(id: string, storageStateJson: string): Promise<void>;
```

Reads `QONE_VAULT_API_URL` and `QONE_VAULT_INTERNAL_TOKEN` from env. Adapters call this; they never see the URL or the token.

### 7.3 New file: `google.ts`

The most complex adapter. Strategy in order:

1. **Try warm session first.** Load `storage_state` from the vault into a CloakBrowser context. Navigate to the target URL (Gemini or Flow). If a logged-in signal is visible (avatar, `myaccount.google.com` reachable), return `logged_in` immediately. **No login form interaction.**
2. **If no warm session, run the password chain.** Goto `accounts.google.com/signin`. Fill email → Next. Fill password → Next.
3. **Branch on what Google asks next:**
   * Lands on `myaccount.google.com` (or target URL) → `logged_in`. Capture state, push to vault.
   * `/challenge/totp` → `totp(seed)` → fill → Next → expect logged-in.
   * `/challenge/dp` (device prompt) → `needs_human`. We have no device to confirm from.
   * `/signin/v2/challenge/selection` (Google offering verification methods) → `needs_human`.
   * `/speedbump` ("verify it's you") → `needs_human`.
   * Credential error visible → `bad_credentials`.
4. **Stable fingerprint seed** is essential — `--fingerprint=<credentials.fingerprint_seed>` passed to CloakBrowser on every launch. Without this, Google sees a new device every run.
5. **`humanize: false`** for this adapter (lesson from Facebook in the existing flows): Google's login pages reflow heavily during render and humanize's scroll-into-view racing causes intermittent failures. C++ stealth patches still apply.

Honest failure mode: even with a warm fingerprint, Google occasionally throws `/dp` or `/speedbump`. That manifests as a `needs_human` outcome, the runner pauses to a gate, the human runs `--warm-up` once, and hands-off resumes.

### 7.4 New file: `openai_web.ts`

Targets `chatgpt.com` (which redirects to `auth.openai.com/log-in`). Fewer surprises than Google but two notable wrinkles:

* **Cloudflare Turnstile** gates the login page. CloakBrowser's README claims auto-resolve on the non-interactive variant. If the interactive variant fires → `needs_human`.
* **"Continue with Google" path.** If a ChatGPT account was originally created via Google-sign-in (unknown until first warm-up), the email step redirects to `accounts.google.com` instead of asking for a password. The adapter detects the redirect and chains into `google.ts` to complete. v1 implements detection and the chain.

Otherwise: email → Continue → password → Continue → optional TOTP → chatgpt.com. Capture and push session state.

> **Phase 2 follow-up (out of scope for v1):** translate the captured chatgpt.com session into the on-disk format the `codex` CLI expects (`~/.codex/auth.json` or equivalent), so `codex` itself runs unattended after warm-up. v1 stops at "session is in the vault and `social-login` can re-use it."

### 7.5 Refactored: `tiktok.ts`, `facebook.ts`

Existing logic stays. New entry points wrap the existing functions:

```ts
// preserved (used by tests and one-off CLI)
export async function loginTikTok(opts: TikTokLoginOpts): Promise<LoginResult>;

// new (used by the runner)
export async function loginTikTokFromVault(opts: { credentialId: string; ...}): Promise<LoginResult>;
```

The `*FromVault` variant calls `vault.fetchCredential()`, maps the payload + fingerprint seed + warm session state into the existing `LoginOpts` shape, runs the existing flow, then on success calls `vault.pushSessionState()` with the captured storage state. On any non-success status it calls `vault.reportStatus()`.

### 7.6 Extended: `browser.ts`

Adds two optional fields to `OpenOptions`:

```ts
fingerprintSeed?: string;          // → CloakBrowser --fingerprint=<seed>
storageStateJson?: string;         // → preload Playwright storage_state
```

The fingerprint seed is the critical addition: without it, every login has a fresh fingerprint and Google will challenge constantly.

### 7.7 CLI changes

Existing commands (`tiktok`, `facebook` with `--identifier`/`--password`) keep working — useful for the bootstrap phase before the vault is populated.

New top-level command:

```
bun run src/cli.ts from-vault --id <uuid>
                              [--headed]
                              [--warm-up]
                              [--json]
                              [--timeout <ms>]
```

`--warm-up` implies `--headed` and bumps the timeout to 5 minutes — the human-in-the-loop case. Without it, headless reuse is the default.

---

## 8. Workflow runner integration

### 8.1 New runner adapter: `dashboard/api/runner/adapters/social-login.ts`

```ts
export async function loginViaSocialAdapter(
  credentialId: string,
  opts: { warmUp?: boolean; timeoutMs?: number },
): Promise<LoginResult>;
```

Shells out to `bun run /path/to/social-login/src/cli.ts from-vault --id <uuid> --json [--headed --warm-up]`. Sets `QONE_VAULT_API_URL` (= `API_INTERNAL_URL`) and `QONE_VAULT_INTERNAL_TOKEN` (= `EVENT_BRIDGE_SECRET`) on the spawned process. Parses stdout JSON and returns it.

The adapter never decrypts anything. The CLI talks to `/use`. The adapter only sees the runtime result.

### 8.2 Workflow step config

A workflow step's config (already a JSON column on `workflows`) gains an optional `credential_id` field:

```jsonc
{
  "id": "post-to-tiktok",
  "kind": "social_login_then_post",
  "credential_id": "8a4f...uuid",
  "post": { ... }
}
```

By ID rather than `(platform, account)` so renaming or rotating accounts doesn't silently break workflows.

### 8.3 Outcome → step state mapping

| CLI status | Runner action | Visible in dashboard |
|---|---|---|
| `logged_in` | Step succeeds, workflow continues | 🟢 step turns green |
| `needs_human` | Step **pauses**; create a row in `gates` with `kind='credential_warmup'`, `credential_id`, `message` | 🟡 step pauses; gate card on `/gates` with **Resolve** button |
| `bad_credentials` | Step fails. Suggest "delete and re-create credential" | 🔴 step turns red, error visible |
| `error` | Step fails (transient). Eligible for the workflow's retry policy | 🔴 step turns red |

### 8.4 Gate `kind = 'credential_warmup'`

Extends the existing `gates` table — a `kind` column probably exists already; if not, add one with a default of `'review'` and the new value. Gate row carries enough state to resume:

```ts
{
  kind: 'credential_warmup',
  credential_id: uuid,
  workflow_run_id: uuid,
  message: string,    // from CLI: "Google /speedbump challenge", etc.
}
```

The Resolve button on the `/gates` page invokes the adapter again with `warmUp: true`. CloakBrowser opens headed on the host, the human completes the challenge, the CLI captures the new session, the gate clears, and the workflow run auto-resumes from the failed step.

This intentionally re-uses the existing `gates` infrastructure; no new "human escalation" subsystem.

### 8.5 Optional notification

If `NOTIFY_ON_CREDENTIAL_GATE=true` is set in `dashboard/.env`, the gate-creation path also fires through `dashboard/api/src/integrations/notifications/`. v1 keeps this trivial — whatever notification channel is already wired. Off by default.

### 8.6 Concurrency

Per-credential serialization: before launching the CLI, the runner takes a Postgres advisory lock keyed on `credentialId`. This prevents two workflows from racing two simultaneous logins to the same Google account, which would almost certainly trigger a challenge.

```ts
await db.execute(sql`SELECT pg_advisory_lock(hashtext(${credentialId}))`);
try { return await loginViaSocialAdapter(...); }
finally { await db.execute(sql`SELECT pg_advisory_unlock(hashtext(${credentialId}))`); }
```

A `min_seconds_between_uses` knob (Phase 2) could be layered on top if rate-limiting Google sees of repeated logins becomes desirable.

---

## 9. Rollout plan

Five phases, each independently mergeable.

### Phase 1 — Vault foundation

* Drizzle migration: `dashboard/api/migrations/20260510_credentials.sql`.
* Schema entry: `dashboard/api/src/db/schema.ts`.
* Crypto helper: `dashboard/api/src/lib/crypto-envelope.ts`.
* Routes: `dashboard/api/src/routes/credentials.ts`.

End-of-phase capability: add/remove credentials by `curl`. No UI.

### Phase 2 — Vault UI

* Page: `frontend/app/credentials/page.tsx`.
* Sidebar entry: `frontend/components/sidebar.tsx`.
* Hooks: `frontend/lib/queries.ts` (3 hooks: `useCredentials`, `useCreateCredential`, `useDeleteCredential`).
* Types: `frontend/lib/types.ts`.

End-of-phase capability: full vault usable from the dashboard UI.

### Phase 3 — Adapters + TOTP

* `social-login/src/totp.ts`, `vault.ts`, `google.ts`, `openai_web.ts`.
* Refactor `tiktok.ts` / `facebook.ts` to expose `*FromVault` variants.
* Extend `browser.ts` with `fingerprintSeed` + `storageStateJson`.
* CLI: `from-vault` subcommand.

End-of-phase capability: log into any credential by ID from the CLI.

### Phase 4 — Runner adapter + gates

* `dashboard/api/runner/adapters/social-login.ts`.
* Extend `gates` table / route with `kind='credential_warmup'`.
* `frontend/app/gates/page.tsx`: render the new gate kind + Resolve button.

End-of-phase capability: workflows can reference a credential, pause to a gate on `needs_human`, and resume after warm-up.

### Phase 5 — Warm-up walkthrough

Operational, not code. Eight credential rows × ~30-90 seconds each, walked through together, ending with all status dots green.

---

## 10. Initial vault contents (Phase 5)

Five accounts, eight credential rows.

| Row | Label | Platform | Account | Status before warm-up |
|---|---|---|---|---|
| 1 | `qoneidol-tiktok`   | `tiktok`     | qoneidol@gmail.com    | Already warmed in `social-login/profiles/tiktok/main` — import cookies, no fresh warm-up needed |
| 2 | `ittibiz-tiktok`    | `tiktok`     | ittipolbiz@gmail.com  | Fresh warm-up |
| 3 | `qonecompany-fb`    | `facebook`   | QoneCompany@gmail.com | Already warmed — import cookies |
| 4 | `bjgdrx-fb`         | `facebook`   | Bjgdrx@gmail.com      | Fresh warm-up |
| 5 | `bjgdrx-google`     | `google`     | Bjgdrx@gmail.com      | Fresh warm-up. Used for both Gemini and labs.google/flow. |
| 6 | `bjgdrx-cgpt`       | `openai_web` | Bjgdrx@gmail.com      | Fresh warm-up. May redirect to Google — see §7.4 |
| 7 | `ittitask-cgpt`     | `openai_web` | Itti.task@gmail.com   | Fresh warm-up |
| 8 | `ittibiz-cgpt`      | `openai_web` | ittipolbiz@gmail.com  | Fresh warm-up |

Same Google password and TOTP seed for `Bjgdrx@gmail.com` are stored in **two separate rows** (Google + ChatGPT) because the cookies, sessions, and warm-up state are platform-specific. This is intentional — the rows are session containers, not password records.

---

## 11. Pre-flight (one-time, before any code lands)

Three operational items the user does once:

```bash
# 1. Generate the KEK and put it in dashboard/.env
openssl rand -base64 32
# → QONE_VAULT_KEY=<output>

# 2. Confirm EVENT_BRIDGE_SECRET is set (already required by the existing dashboard)
grep EVENT_BRIDGE_SECRET dashboard/.env || openssl rand -hex 32

# 3. Capture the TOTP seed (Base32 string) for each of the 6 distinct accounts.
#    Use the authenticator app's "show secret" or "export" feature.
#    Have all 6 ready before starting Phase 5.
```

---

## 12. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Google throws non-TOTP challenge despite warm fingerprint | Medium (a few times per account per month) | Medium (workflow pauses to gate) | Stable fingerprint seed, stable IP via optional proxy (Phase 2). Gate + Resolve button makes the recovery 30 seconds. |
| KEK leaks via `.env` exfiltration | Low (same as existing `EVENT_BRIDGE_SECRET`) | High (entire vault decryptable) | `chmod 600`, never commit, never in shared backups. Recovery: rotate KEK (~30s, re-wrap DEKs) + rotate the 8 account passwords (~10 min). |
| Cookie expiry mid-month → password+TOTP fallback fires | Low (cookies refresh on every successful login) | Low (transparent to user) | Adapter automatically falls through password+TOTP path. |
| Google account flagged for "suspicious activity" | Low | High (account locked, hours to recover) | Per-credential advisory lock prevents same-account races. Stable fingerprint avoids "new device" signal. |
| chatgpt.com login was created via "Continue with Google" | Unknown (per-account discovery) | Low | Adapter detects redirect and chains into `google.ts`; first warm-up reveals which accounts need this path. |
| Selectors drift on TikTok/FB/Google/OpenAI | High over months | Low (per-platform fix) | URL-based detection where possible (already learned this lesson); selector lists tolerant; clear failure mode (`error` status with last URL). |

---

## 13. Out of scope (deferred to Phase 2 or later)

* `<CredentialPicker>` UI component embedded in the workflow builder.
* "View password" / reveal in UI.
* Audit log of every decrypt event.
* Edit-in-place credential editing.
* `proxy_ref` actually wired up (column exists, unused in v1).
* Cookie auto-rotation on a schedule.
* Telegram / Slack / email notification on `needs_human` (only the env-flag stub is wired; concrete channel deferred).
* Writing captured ChatGPT session into `~/.codex/auth.json` for the `codex` CLI itself.
* Multi-user auth on the dashboard.
* `min_seconds_between_uses` rate-limit knob.

---

## 14. Acceptance criteria (what "done" looks like for v1)

1. From the dashboard `/credentials` page: I can add a credential, see it appear in the table, and delete it.
2. From the CLI: `bun run src/cli.ts from-vault --id <uuid> --headed --warm-up` opens a stealth Chromium, logs into TikTok / Facebook / Google / ChatGPT (whichever the credential is for), and ends with `status: logged_in` and the warm session pushed back to the vault.
3. From the CLI: re-running the same command **without** `--headed --warm-up` completes in seconds with `status: logged_in` and refreshed cookies.
4. A workflow step with `credential_id` set runs the runner adapter, which results in either: (a) a green step on success, (b) a yellow gate row on `needs_human`, or (c) a red step with a clear error message on `bad_credentials`/`error`.
5. The `/gates` page shows credential-warmup gates with a Resolve button that opens a headed CloakBrowser, lets the human complete the challenge, and clears the gate.
6. All eight credential rows from §10 are present in the vault and each has a green status dot after Phase 5.

---

## 15. Notes for the spec reviewer

* The split between the `dashboard/` package (vault, UI, runner integration) and the `social-login/` package (adapters, CLI, CloakBrowser) is intentional. The integration boundary is the CLI, mirroring `hermes-cli.ts` / `openclaw-cli.ts`.
* The dashboard is single-user and binds to localhost. There is no per-user auth in the broader system; that is unchanged here. The `local-only` security tier on the public credentials endpoints is identical to every existing dashboard route.
* Envelope encryption (KEK + per-row DEK) is the standard pattern (e.g. AWS KMS, GCP KMS, age, libsodium sealed boxes); this design implements it directly with the Node `crypto` module rather than pulling a new dependency. The crypto helper is small and testable.
* CloakBrowser fingerprint stability per credential is the single technical decision that most affects long-term success against Google. Without a stable fingerprint, every login looks like a new device and Google challenges constantly.
* The "fully hands-off" framing the user chose is honest: hands-off in steady state, with one human warm-up per account on first run and an occasional re-warm-up when Google or OpenAI throw a non-TOTP challenge. The gate/Resolve loop makes the human-step duration about 30 seconds.
