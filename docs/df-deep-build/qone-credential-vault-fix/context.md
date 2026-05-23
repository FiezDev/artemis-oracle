# context.md — qone-credential-vault-fix

Living reference for what was discovered during recon, plus patterns and open questions later phases need. Subsequent phases (plan, execute, review) **append** here — do not overwrite.

---

## Files read during recon

| Path | Why it mattered |
|---|---|
| `docs/superpowers/specs/2026-05-10-qone-credential-vault-design.md` (655 lines, revision 2) | Authoritative spec — data model, API shape, auth model, rollout phases, acceptance criteria. §5.1 explicitly says UI mutations use X-Agent-ID only; the hardening commit violated this. |
| `docs/superpowers/plans/2026-05-10-qone-credential-vault.md` (2617 lines, full) | TDD plan with 22+ tasks. Most landed. Phase 4 (warm-up walkthrough) is operational and still mostly undone. |
| `/Users/fiez/Dev/qone_corp/dashboard/` (full audit via parallel Explore agent) | Real Phase 1 backend impl lives here. Migration `0032_credentials.sql` (not 0033 as planned — migrations drifted, latest is 0049). |
| `/Users/fiez/Dev/qone_corp/social-login/` (full audit via parallel Explore agent) | Phase 3 adapters all present and typecheck clean: `totp.ts`, `vault.ts`, `google.ts`, `openai_web.ts`, `tiktok.ts::loginTikTokFromVault`, `facebook.ts::loginFacebookFromVault`, CLI `from-vault`, `scripts/import-profile.ts`. |
| `/Users/fiez/Dev/qone_corp/dashboard/chrome-extension/` (full audit via parallel Explore agent) | Manifest v3 extension complete: `manifest.json`, `popup.html`, `popup.js` (169 lines), 3 icon files, README. Captures real-Chrome cookies and POSTs to `/credentials/:id/import-warm-state`. |

## Key concrete state at recon time

### Phase 1 backend — DONE
- `dashboard/api/src/lib/crypto-envelope.ts` (63 lines) + tests
- Migration: `dashboard/api/migrations/0032_credentials.sql` (numbered 0032 not 0033 due to drift)
- Drizzle schema: `dashboard/api/src/db/schema/credentials.ts`, re-exported from `schema/index.ts:18`
- Zod schemas: `dashboard/api/src/lib/schemas/credentials.ts` (includes `CredentialUpdateBody` for PATCH)
- Service: `dashboard/api/src/orchestration/credentials/credentials-service.ts`
- Routes: `dashboard/api/src/routes/credentials.ts` (282 lines) — mounted at `routes/index.ts:43`
- `SENSITIVE_GET_PREFIXES` in `middleware/auth.ts:20` includes `/api/v1/credentials`
- Boot fail-closed on `QONE_VAULT_KEY` at `api/src/index.ts:15-20`
- `QONE_VAULT_KEY` set in `dashboard/.env` (valid 44-char base64)

### Phase 2 frontend — CODE SHIPPED, RUNTIME BROKEN
- `dashboard/frontend/lib/api-client.ts:27-28` — `get()` accepts optional `agentId`
- `dashboard/frontend/lib/types.ts:444-458` — `Credential` + `CredentialCreateInput`
- `dashboard/frontend/lib/queries/credentials.ts` — `useCredentials`, `useCreateCredential`, `useDeleteCredential` (re-exported from `lib/queries.ts:79`)
- `dashboard/frontend/app/credentials/page.tsx` (176 lines) — list + test-login + delete
- `dashboard/frontend/app/credentials/new-credential-modal.tsx` (141 lines)
- `dashboard/frontend/lib/constants.ts:50` — sidebar entry

### Phase 3 social-login — DONE
- `social-login/src/totp.ts` (wraps `otpauth@^9.0.0`)
- `social-login/src/vault.ts` (`fetchCredential`, `pushSessionState`, `reportStatus`, `VaultUnreachableError`)
- `social-login/src/browser.ts` — `OpenEphemeralOptions.fingerprintSeed`, `openContextEphemeral()`
- `social-login/src/google.ts`, `social-login/src/openai_web.ts`
- `social-login/src/tiktok.ts::loginTikTokFromVault`, `social-login/src/facebook.ts::loginFacebookFromVault`
- `social-login/src/cli.ts` — `from-vault` subcommand with platform dispatch
- `social-login/scripts/import-profile.ts` — bridge for existing on-disk warmed profiles
- `social-login/profiles/tiktok/main` and `social-login/profiles/facebook/main` — warmed sessions ready for import

### Chrome extension — DONE (Manifest v3, working)
- `dashboard/chrome-extension/manifest.json` (722 bytes)
- `dashboard/chrome-extension/popup.html` (2738 bytes)
- `dashboard/chrome-extension/popup.js` (6326 bytes, 169 lines, last touched May 19 00:34)
- Icons 16/48/128
- README
- Recent fix `c21322b`: extracted `AUTH_COOKIE_CANDIDATES` as shared module + drift test

## Root cause of "doesn't work"

Commit `0df2577` ("fix(security): harden credentials, agents, relay...") added `hasServiceToken()` guards to credential **mutation** routes. Spec §5.1 explicitly says these should be `X-Agent-ID`-only. The frontend api-client only sets `X-Agent-ID`; every "+ New Credential" / Delete / test-login UI mutation hits 403. The Chrome extension likely hits the same wall on `/import-warm-state`.

## Patterns to follow

- **Auth helper extraction** — mirror commit `c21322b`'s approach: extract a named helper, add a drift/regression test, apply at call sites. Don't inline policy logic in every route.
- **Existing helpers to reuse:** `hasServiceToken(c)`, `VALID_AGENTS`, the global `agentAuth` middleware in `api/src/index.ts:82`.
- **OpenAPIHono routes only** — every route file uses `OpenAPIHono` + `createRoute(...)`. A plain Hono router silently breaks `/openapi.json` codegen.
- **Drizzle conventions** — `text` IDs with `gen_random_uuid()::text`, base64 strings instead of `bytea`, `timestamp({ withTimezone: true })`.
- **Docker-first runtime** — `docker compose ps` / `docker compose restart api`, not bare `bun run dev`.

## Open questions deferred (per interview phase)

- **Phase 4 creds availability** — human said "not sure" whether passwords + TOTP seeds are ready for all 5 distinct accounts. Resolution: per-account, just-in-time during the walkthrough. Rows without creds get explicitly deferred in journal.md (graceful degradation).
- **Exact route list under the new hybrid guard** — confirmed: `POST /`, `DELETE /:id`, `PATCH /:id`, and (likely) `POST /:id/import-warm-state`. T1 (verification) will produce the final list before T2 patches.
- **popup.js header set** — unknown until T1 inspects it. If the extension already sends a service token (via an API-key-style field), the hybrid guard handles it for free. If it sends only `X-Agent-ID`-like header, T2's hybrid guard fixes it without extension changes; if not, T2-or-followup adds the missing header.

## Notable interview-phase decisions

- **No external delegates** (codex/gemini/glm). User override in memory `feedback_no_external_delegates.md`. Parallel Claude subagents are encouraged for fan-out (recon, exploration).
- **No auto-approve gates.** Phase 4 launches real-browser logins against the human's accounts — every `--headed --warm-up` session waits for explicit human OK. Per `feedback_never_auto_approve_gates.md`.
- **Creds never in chat** — passwords + TOTP seeds get typed directly into the New Credential modal in the browser. Modal encrypts at rest via the existing envelope. Chat history never sees the secrets.
- **Hybrid auth chosen** over revert-to-spec or token-in-frontend. Backend accepts `hasServiceToken(c) || isAdminAgent(c)`. Frontend stays X-Agent-ID-only. Service token path preserved for runners.
- **Commit shape: bundle with verification.** Small focused commits per concern, with verification scripts/tests interleaved. No PR-level meta-commit.
- **No mid-flight review gate.** Smoke tests after T3 are the gate before Phase 4.

---

## Appended findings (phases append below)

### 2026-05-23 — plan/EXPLORE phase

Two parallel Claude Explore subagents (no external delegates per user override) audited the credentials routes file + Chrome extension popup.js.

**Credentials route table (`qone_corp/dashboard/api/src/routes/credentials.ts`, single mount at `routes/index.ts:43`):**

| Method | Path | Lines | `hasServiceToken` guard? | Extra guards |
|---|---|---|---|---|
| GET | `/` | 30–33 | no (covered by `SENSITIVE_GET_PREFIXES` middleware) | — |
| POST | `/` | 35–45 | **yes (line 40)** ← regression target | — |
| DELETE | `/:id` | 47–51 | **yes (line 48)** ← regression target | — |
| PATCH | `/:id` | 56–73 | **yes (line 57)** ← regression target | payload.kind match (line 67-68) |
| POST | `/:id/use` | 76–86 | yes (line 77) — **keep** | — |
| POST | `/:id/import-warm-state` | 99–181 | **yes (line 104)** ← regression target | existence check + cookie validation |
| POST | `/:id/status` | 183–189 | yes (line 184) — **keep** | — |
| POST | `/:id/test-login` | 202–282 | **NO guard** — never had one | kind filter (api_key excluded), dedup lock |

**Confirmed regression-target route list for T2:** exactly 4 routes:
- `POST /`
- `DELETE /:id`
- `PATCH /:id`
- `POST /:id/import-warm-state`

**`POST /:id/test-login` surprise:** has no guard now; commit `0df2577` did not add one. This is **not part of T2's scope** — it's a pre-existing condition. Worth flagging as a follow-up if the test-login button initiates real-browser logins with vault payload.

**Commit `0df2577` line-level scope:** added `hasServiceToken` guards at lines 40, 48, 57, 104. No collateral changes elsewhere.

**`AUTH_COOKIE_CANDIDATES` location:** exported inline from `routes/credentials.ts:20-25` — not yet extracted to a shared module. The "extract a validator" pattern from `c21322b` actually lives in this file. The shared-module phrasing in the spec was slightly off; the precedent is "shared export consumed by tests" rather than "separate file".

**Chrome extension verdict (popup.js, 169 lines):**

- Endpoints called: `GET /credentials` (line 51) and `POST /credentials/:id/import-warm-state` (line 131)
- Headers on both: `X-Service-Token: <user-supplied secret stored in chrome.storage.local>` AND `X-Agent-ID: artemis` (hardcoded)
- Body: cookie bundle for `/import-warm-state`

**Verdict:** Extension already sends `X-Service-Token` → hybrid guard accepts it via the `hasServiceToken(c)` branch. **No popup.js change needed.** T2 is purely backend.

**Implication for T2 scope:** removes the previously-considered `fix(ext)` commit. Backend-only fix. The execution phase can drop that planned commit.

### 2026-05-23 — re-interview after plan/EXPLORE surprises

Human triggered re-interview because plan-phase findings changed scope. Resolution (minor scope expansion, no full re-compile):

1. **`/test-login` added to T2 patch list** (5 routes total now: `POST /`, `DELETE /:id`, `PATCH /:id`, `POST /:id/import-warm-state`, `POST /:id/test-login`). Same hybrid guard, same tests. `0df2577` missed this route; we close the gap as part of "really work".
2. **T5 (extension end-to-end) stays.** Even though no code change needed, the operational confidence of proving real-Chrome → vault round-trips still earns the slice.
3. **No other scope additions** — KEK rotation script (Task 23 in original plan) stays deferred; Phase 5 runner adapter scaffolding (spec §13) stays deferred.

Spec.md, tasks.md updated inline. Re-handoff to df-deep-build-plan to resume DESIGN sub-phase from the same point (architecture for `isAdminAgent` helper).

### 2026-05-23 — T1 reproduction findings (execute phase)

**Environment state:**
- Docker daemon up.
- `qone-api` container `Up 2 days (healthy)` at `0.0.0.0:5501`.
- `qone-frontend` container `Up 3 days` at `0.0.0.0:5500`.
- `qone-postgres` `Up 5 days (healthy)` at `127.0.0.1:5532`.
- Latest applied migration: `0049_goal_events_actor_kind.sql` (matches files in `api/migrations/`).
- `dashboard/api/.env` exists (chmod 600).

**Reproduction matrix (X-Agent-ID: artemis only, NO X-Service-Token):**

| Route | Method | Path | HTTP | Body | Verdict |
|---|---|---|---|---|---|
| Create | POST | `/api/v1/credentials` | **403** | `{"error":"service token required"}` | Regression confirmed |
| Delete | DELETE | `/api/v1/credentials/<uuid>` | **403** | `{"error":"service token required"}` | Regression confirmed |
| Patch | PATCH | `/api/v1/credentials/<uuid>` | **403** | `{"error":"service token required"}` | Regression confirmed |
| Import warm state | POST | `/api/v1/credentials/<uuid>/import-warm-state` | **403** | `{"error":"service token required"}` | Regression confirmed |
| Test login | POST | `/api/v1/credentials/<uuid>/test-login` | **404** | `{"error":"credential not found"}` | No auth guard — handler proceeded past auth to existence check |

The first 4 prove the `0df2577` regression. The 5th proves the pre-existing no-guard gap on `/test-login`.

**Note on error body shape (architecture Q2):** The 403 body is `{"error":"service token required"}`. The hybrid guard's new body will be `{"error":"admin agent or service token required"}`. Confirmed harmless: api-client + popup.js handle 403 generically (no string-match).

**VALID_AGENTS membership (architecture Q1):** Confirmed `VALID_AGENTS` is a `Set` defined at `middleware/auth.ts:4-10` containing:
```
artemis, atlas, forge, pixel, shield, deploy,
iris, luna, sage, vox, nova, reel,
herald, echo, pulse, flux,
axiom, metric, prism, spark,
dashboard, runner, system
```
Critically: `runner` IS a valid agent. **`ADMIN_AGENTS = ['artemis']` correctly excludes it.** A `runner`-tagged request must continue to require `X-Service-Token` for `/use` and `/status` — the spec's runner-vs-UI separation holds.

**SERVICE_SECRET behavior:** `middleware/auth.ts:42-49` warn-logs only on missing env var (NOT `process.exit(1)`). The fail-closed behavior lives in `hasServiceToken()` line 57: returns false if `SERVICE_SECRET` is unset. This matches spec §4.3's stated difference from `QONE_VAULT_KEY` (which fails closed at boot per `api/src/index.ts:15-20`).

**Chrome extension popup.js header set (re-verified):**
- Line 51-52: `GET /credentials` sends `X-Service-Token: secret` + `X-Agent-ID: artemis`
- Line 131-135: `POST /credentials/:id/import-warm-state` sends both headers
- After the hybrid guard, both branches are accepted (via `hasServiceToken`). **No popup.js change needed.**

**T1 conclusion:** All diagnostic evidence aligns with the audit + architecture decision. Ready for T2.
