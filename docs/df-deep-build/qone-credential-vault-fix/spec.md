# spec.md — qone-credential-vault-fix

> **Immutable.** This document is the compiled mega-prompt approved by the human at the close of the df-deep-build-interview phase. If something here needs to change, re-run the interview phase rather than editing this file in place.

---

## ROLE

Senior backend+frontend engineer continuing the Q-One Credential Vault feature from a half-merged state. Operating as implementer in Claude Code — parallel Claude subagents OK; no Codex/Gemini/GLM delegation (per user override).

## OBJECTIVE

Make the credential vault actually work end-to-end. Three deliverables:

1. Fix the auth regression blocking UI mutations.
2. Confirm the QOne Vault Importer Chrome extension loads + the `import-warm-state` path round-trips end-to-end.
3. Walk through Phase 4 — get as many of the 8 credential rows from spec §10 to `status=logged_in` (🟢) as creds-on-hand allow. Defer the rest with a clear punch list.

## CONTEXT

<existing_context>

**Sources of truth:**
- Spec: `/Users/fiez/Dev/artemis-oracle/docs/superpowers/specs/2026-05-10-qone-credential-vault-design.md`
- Plan: `/Users/fiez/Dev/artemis-oracle/docs/superpowers/plans/2026-05-10-qone-credential-vault.md`
- Backend impl: `/Users/fiez/Dev/qone_corp/dashboard/`
- Adapters: `/Users/fiez/Dev/qone_corp/social-login/`
- Chrome ext: `/Users/fiez/Dev/qone_corp/dashboard/chrome-extension/`

**Recon findings:**
- Phase 1 backend: DONE (crypto-envelope, schema, routes, boot check, `QONE_VAULT_KEY` set)
- Phase 3 social-login: DONE (totp, vault, adapters, CLI, import-profile)
- Phase 2 frontend: code shipped — RUNTIME BROKEN by commit `0df2577`

**Regression root cause:**
`0df2577` ("fix(security): harden credentials...") added `hasServiceToken()` guard to (confirmed by plan-phase exploration):

- `POST /credentials` (line 40)
- `DELETE /credentials/:id` (line 48)
- `PATCH /credentials/:id` (line 57)
- `POST /credentials/:id/import-warm-state` (line 104)

Frontend api-client sends only `X-Agent-ID: artemis`. Spec §5.1 says UI mutations are X-Agent-ID-only. The hardening overshot.

**Additional scope (added by re-interview after EXPLORE):** `POST /credentials/:id/test-login` (lines 202-282) has **no auth guard at all** — never had one, `0df2577` didn't add one. The UI calls it to launch real-browser logins consuming vault payloads. Same threat model as the 4 routes above. Applies the same hybrid guard.

**Chrome extension status (confirmed by plan-phase exploration):** popup.js already sends both `X-Service-Token` and `X-Agent-ID: artemis` on every fetch. After the hybrid guard lands the extension works as-is — no popup.js changes needed.

**Chrome extension (QOne Vault Importer, Manifest v3):**
- `popup.js` 169 lines, captures real-browser cookies via `chrome.cookies.getAll()`, POSTs to `/credentials/:id/import-warm-state`
- User-friendly path to seed warm sessions for accounts that cloakbrowser/Playwright struggle with (Google, ChatGPT)
- Last touched May 19 00:34 (same commit window as the auth regression)
- Recent fix commit `c21322b` synced the `AUTH_COOKIE_CANDIDATES` validator with social-login's accept list

**Runtime:**
- Dashboard runs in Docker (`qone_corp/dashboard/docker-compose.yml`). Verify api+frontend containers up; if not, start them. After api edits: `docker compose restart api` (or rebuild if deps changed).

**Cleanup (separate concern, end of session):**
- Empty stubs in artemis-oracle (`dashboard/`, `packages/`, root `package.json`) — May 21 accidental artifacts, safe to delete.

</existing_context>

## EXAMPLES & REFERENCES

- Auth-guard pattern: `dashboard/api/src/middleware/auth.ts` — `hasServiceToken(c)`, `VALID_AGENTS` (includes "artemis").
- Recent precedent: commit `c21322b` — extracting validator into a shared module + adding a test guard. Mirror that pattern if any new shared helper appears.
- Extension/backend contract: `popup.js` → `POST /credentials/:id/import-warm-state`. Verify the body format and required headers on read.

## OUTPUT FORMAT

Small focused commits in this order on the qone_corp dashboard repo (stay on whatever branch is checked out — verify; do NOT switch branches without asking):

1. `fix(api): allow X-Agent-ID admin OR X-Service-Token on credential mutations` — hybrid guard helper, applied to `POST /`, `DELETE /:id`, `PATCH /:id`, `POST /:id/import-warm-state`, **and `POST /:id/test-login`**
2. `test(api): unit + smoke for dual-path auth on mutation routes` (including `/test-login`)
3. ~~`fix(ext)`~~ — **dropped: extension works as-is per popup.js audit**
4. `docs: append a Phase 4 walkthrough journal section with row-by-row status`

Plus, in artemis-oracle (separate concern, separate commit at the end):

- `chore: remove empty dashboard/ and packages/ stubs`

## REASONING APPROACH

1. Quick env check: `docker compose ps` for the dashboard. Bring up any container that's down. If api code changes need to take effect: `docker compose restart api`.
2. Reproduce the 403 by hand (curl against `POST /credentials` with `X-Agent-ID: artemis` and no service token).
3. Confirm the extension hits the same regression — inspect `popup.js` for its header set, simulate the call with curl.
4. Implement hybrid guard: helper `isAdminAgent(c)` (true for artemis and other admin entries in `VALID_AGENTS`). Mutation routes accept if `hasServiceToken || isAdminAgent`. Apply to: `POST /`, `DELETE /:id`, `PATCH /:id`, `POST /:id/import-warm-state`, `POST /:id/test-login`. `/use` and `/status` keep service-token-only (runner-only paths).
5. Restart api container; re-run all curl smoke tests; expect 201/204.
6. Run `import-profile.ts` for the two existing warmed on-disk profiles (qoneidol-tiktok, qonecompany-fb). Confirm `warm_state_at` populated.
7. Smoke-test `from-vault --id <uuid>` headless on qoneidol-tiktok → expect `status=logged_in`.
8. Load the Chrome extension in user's real Chrome (user action). Use it to seed warm state for one fresh account (probably Google or ChatGPT). Confirm the row flips green via `import-warm-state`.
9. Per-account Phase 4 walkthrough — for each account user has creds for: create row via UI (creds typed into modal, never into chat), either (a) use the extension if real-browser session exists, or (b) run `--headed --warm-up` via social-login CLI, user resolves any challenge. Capture row status.
10. Final journal: status of all 8 rows + any deferred.
11. Cleanup commit: delete artemis-oracle stubs.

## CONSTRAINTS & GUARDRAILS

- NO external delegates (codex/gemini/glm) — Claude only.
- NEVER auto-approve any gate. Phase 4 launches real-browser logins; wait for explicit user OK each time.
- NEVER ask user to paste passwords/TOTP into chat. Creds get typed into the dashboard New Credential modal directly.
- NEVER skip pre-commit hooks. NEVER force-push. NEVER `rm -rf` without explicit OK.
- Use existing patterns — no inventing new auth shapes or envelope formats. Mirror the `c21322b` extracted-validator approach if any new shared helper appears.

## SUCCESS CRITERIA

Spec §14:

- §14.1 — UI create + see + delete a credential ✓
- §14.2 — GET auth 401/200 ✓
- §14.3 — `/use` auth 403/200 ✓
- §14.5 — `import-profile.ts` populates a row; `from-vault` on it returns `logged_in` immediately ✓
- §14.6 / §14.7 — at least one row warmed via `--warm-up` then re-used headless ✓
- **NEW**: Chrome extension successfully seeds warm state for ≥1 row via `import-warm-state` (end-to-end, real-browser cookies → vault → 🟢)
- **NEW**: `POST /credentials/:id/test-login` rejects unauthenticated calls (neither service token nor admin agent) with 403
- §14.9 — as many of 8 rows green as creds-on-hand allow; remainder listed as deferred in journal.md
- §14.12 — vault unreachable test exits 3 with the expected message

Plus regression-specific:

- All existing dashboard/api unit tests still pass
- Empty artemis-oracle stubs removed in a clean commit at end
