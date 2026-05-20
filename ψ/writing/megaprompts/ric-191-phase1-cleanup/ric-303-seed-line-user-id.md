# RIC-303 — Seed `users.line_user_id` + design LIFF onboarding BE

## Role

You are a senior Bun/TypeScript backend engineer with experience in LINE Messaging API + LIFF (LINE Front-end Framework) integration. You operate carefully on production DB; you dry-run every UPDATE before applying it. You write clear design docs that a frontend engineer (Wasun) can pick up without ambiguity. You ship the BE endpoint with integration tests; you do **not** write FE code.

## Objective

Two-phase work in a single PR:

**Phase 1** — Seed `users.line_user_id` for farm owners via SQL UPDATE (manual seed for E2E test), with dry-run-first discipline.

**Phase 2** — Design and implement the LIFF onboarding BE endpoint (`POST /api/users/bind-line`) that lets a logged-in farmer self-bind their LINE user ID via the LIFF flow. Includes design doc + endpoint + integration tests. **No FE work** — Wasun owns that.

## Context

<existing_context>
**Repo:** `/home/bjgdr/dev-work/RG/Rice-Guard-API` (branch `develop`)
**Stack:** Bun + Elysia + Drizzle ORM + TimescaleDB + GraphQL Yoga + LINE Messaging API
**DB:** `riceguard` PostgreSQL (TimescaleDB extension)
**Test runner:** `bun test`

**Audit finding (2026-05-20):**
- 6 farms total in prod DB
- 2 farm owners: `test-admin@riceguard.com` (5 farms) + `kwang-test+farmer1@riceguard.ai` (1 farm)
- Both have NULL `line_user_id`
- 7 other users have `line_user_id` (all auto-created via LINE login, emails `line_U***@temp.line`), but none own any farm
- Result: every LINE alert hits the `!user?.lineUserId` guard in `line.consumer.ts:66` and skips

**Blocking dependency:** RIC-301 (LINE channel token rotation) must land first for E2E verification to succeed. If RIC-301 has NOT shipped yet when you start, land Phase 1 SQL seed anyway (it's structural) and document that Flex-card delivery verification is deferred. See "Memory anchors" below.

**Kwang's verified LINE UID (for seed):** `U19cc78ea6e16143d559d373a14145b41` (verified via line-agent.ggez.work group member list).

**Sibling tickets — DO NOT execute:**
- RIC-301 — LINE channel token rotation (blocks E2E verify here)
- RIC-302 — LINE consumer silent-skip fix (affects observability of this ticket)
- RIC-305 — DLX consumer + cooldown writer (orthogonal)

**LIFF reference (Phase 2 design):**
- LINE Developers LIFF docs: https://developers.line.biz/en/docs/liff/
- Use `liff.getProfile()` on FE → POST `userId` to `/api/users/bind-line`
- Verify the LIFF access token server-side via `POST https://api.line.me/oauth2/v2.1/verify` to confirm the userId belongs to the calling LIFF app
- Channel ID for verification: `2009081199` (RiceGuard alert OA)

**Jira:** https://mobileai.atlassian.net/browse/RIC-303
</existing_context>

## Examples

- Existing endpoint pattern: read any Elysia route in `src/domains/` or `src/graphql/` for the project's preferred shape (likely Elysia route + Zod-or-Elysia-t schema + service function).
- Existing test pattern: `src/test/integration/*.test.ts` for integration tests with the DB.
- Drizzle update pattern: search for `db.update(users).set({` in the codebase to mimic exactly.

## Output Format

**Branch:** `ric-303-seed-line-user-id` off `develop`
**Commits (multiple, ordered):**
1. `docs(design): RIC-303 — LIFF LINE binding flow design`
2. `feat(seed): RIC-303 — line_user_id seed script with dry-run + apply modes`
3. `feat(users): RIC-303 — POST /api/users/bind-line LIFF endpoint`
4. `test(users): RIC-303 — bind-line endpoint integration tests`

**PR title:** `RIC-303: seed line_user_id + LIFF onboarding BE`
**PR target:** `develop`
**Human merges.**

Files added:
- `docs/design/RIC-303-liff-line-binding.md` — design doc for Wasun (FE) covering: button placement (signup + profile settings), LIFF initialization, `liff.getProfile()` call, POST contract, error handling, FE state after success
- `scripts/seed-line-user-id.ts` — Bun script with `--dry-run` and `--apply` flags; never auto-applies
- `src/domains/users/bind-line.ts` (or repo's convention) — service that verifies LIFF access token + updates `users.line_user_id`
- `src/<route-location>/bind-line.route.ts` — Elysia route `POST /api/users/bind-line`
- `src/test/integration/bind-line.test.ts` — integration tests

Files modified:
- Whatever route-registration file pulls in the new endpoint (likely `src/index.ts` or a routes index)

PR description must include:
- Link to RIC-303
- Seed-script execution output for both `--dry-run` and (after human approval) `--apply` against staging
- Link to design doc, with explicit "@wasun please review FE contract" note in PR body
- Acceptance-criteria checklist (Phase 1 Option A + Option B + Phase 2 endpoint working)

## Reasoning Approach

**Phase 1 first, with strict dry-run discipline:**

1. Write `scripts/seed-line-user-id.ts` with two modes:
   - `bun run scripts/seed-line-user-id.ts --dry-run` → prints `SELECT id, email, line_user_id FROM users WHERE email IN ('kwang-test+farmer1@riceguard.ai','test-admin@riceguard.com')` results, then prints the proposed UPDATE statement WITHOUT executing
   - `bun run scripts/seed-line-user-id.ts --apply --email kwang-test+farmer1@riceguard.ai --line-uid U19cc78ea6e16143d559d373a14145b41` → requires interactive y/N confirmation before executing the UPDATE
2. Run `--dry-run` first. Show output in the PR description.
3. **STOP** and request human approval before running `--apply` against staging or prod.

**Phase 2 design + endpoint:**

4. Write `docs/design/RIC-303-liff-line-binding.md` — design first, no code.
5. Test-first for the endpoint:
   - `src/test/integration/bind-line.test.ts` — test happy path (valid LIFF token → users.line_user_id updated) + invalid-token + already-bound + token-userId-mismatch
   - Run tests, confirm red
6. Implement endpoint + service. Make tests green.
7. Mock the LINE OAuth verify endpoint in tests (don't hit real LINE in CI).
8. `bun run lint` + full `bun test`.
9. Dispatch `feature-dev:code-reviewer` agent on the full diff.
10. Open PR.

## Constraints

**Hard NOs:**
- Never run a destructive SQL on prod without dry-run output reviewed by a human first.
- Never embed Kwang's LINE UID (`U19cc78ea6e16143d559d373a14145b41`) as a hardcoded constant in shipped code. It belongs in the seed script's CLI args only.
- Never write FE code (no React, no LIFF SDK init in shipped code). This ticket is BE + design only.
- Never `git push --force`. Never `--no-verify`. Never self-merge.
- Never commit the staging/prod DB connection string. Use `.env` (already gitignored).
- Never bypass LIFF access-token verification — the endpoint MUST verify the token against `https://api.line.me/oauth2/v2.1/verify` before updating the DB. Trusting client-supplied `userId` alone is a hijack risk.
- Do not implement multi-tenant group mapping (`farm_id → line_group_id`). That's explicitly out of scope per the ticket — separate ticket.

**Required behaviors:**
- The endpoint requires an authenticated session (existing JWT/auth middleware). Confirm the bound LINE user matches the authenticated user.
- The endpoint must be idempotent: binding the same `line_user_id` twice returns 200 with current state, not an error.
- If a different user already has that `line_user_id`, return 409 Conflict (LINE UIDs must be unique).

## Success Criteria

**Phase 1:**
1. `scripts/seed-line-user-id.ts --dry-run` runs and prints SELECT + proposed UPDATE.
2. After human approval, `--apply` updates `kwang-test+farmer1@riceguard.ai` (Option A start) — verified by `SELECT line_user_id FROM users WHERE email = 'kwang-test+farmer1@riceguard.ai'`.
3. **If RIC-301 has landed** and RIC-302 logging is in place: within 5 min of next cron fire, `alert_delivery_log` shows a LINE row with status `sent` for kwang-test's farm.
4. **If RIC-301 has NOT landed:** document the deferred E2E verification in the PR; LINE row will appear as `failed` (auth error) until token is rotated. That's expected.

**Phase 2:**
5. `POST /api/users/bind-line` with valid LIFF access token + userId for the authenticated user → 200, DB updated.
6. Same call with invalid LIFF token → 401.
7. Same call where verified `userId` doesn't match request body → 403.
8. Same call where another user already has that `line_user_id` → 409.
9. All integration tests pass under `bun test`.
10. Design doc reviewed by Wasun (PR comment thread).
11. PR opened against `develop`, awaiting human merge.

## Memory anchors

- **Land structural; defer verification when infra blocks.** If RIC-301 hasn't shipped, ship Phase 1 SQL seed anyway. Document the deferred E2E. Don't wait.
- **Per-batch plan only.** This is the RIC-303 batch. Do not pre-write RIC-305 work (audit writer) just because you're touching the users domain. Stay in lane.
- **Never merge PRs without human approval.** Even with green CI.
- **Backport fixes to source.** If during implementation you find the LIFF design doc needs updating, update the doc — don't silently drift the code.
