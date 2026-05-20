# RIC-304 — FCM consumer: log silent-skip paths to `alert_delivery_log`

## Role

You are a senior Bun/TypeScript engineer working on the RiceGuard alert pipeline. Test-first by default. You understand RabbitMQ consumer patterns, Drizzle ORM, Firebase Cloud Messaging, and the user-preference filtering flow (`shouldSendPush`). You do not refactor neighboring code unless asked.

## Objective

Fix three silent `return;` paths in `src/consumers/fcm.consumer.ts` that bypass `logDelivery()`. Two paths log `failed` with an explanatory message; one path (preferences-filtered) reuses the existing `skipped_pref` enum value.

## Context

<existing_context>
**Repo:** `/home/bjgdr/dev-work/RG/Rice-Guard-API` (branch `develop`)
**Stack:** Bun 1.0+ + Elysia + Drizzle ORM + RabbitMQ + Firebase Admin SDK (`firebase-admin@13.6.1`)
**Test runner:** `bun test`

**Audit finding (2026-05-20):** FCM consumer is the sibling pattern to RIC-302. Three silent `return;` paths bypass `logDelivery()`:

**Affected file (verified 2026-05-20):** `src/consumers/fcm.consumer.ts`

**Silent-skip path #1 — farm not found (lines 39-43):**
```typescript
const farm = farmResult[0];
if (!farm) {
  console.error(`[FCM Consumer] Farm ${message.farmId} not found`);
  return;  // <-- no logDelivery
}
```

**Silent-skip path #2 — no active device tokens (lines 58-62):**
```typescript
const activeTokens = tokens.filter((t) => t.isActive);
if (activeTokens.length === 0) {
  console.log(`[FCM Consumer] No active device tokens for farm owner`);
  return;  // <-- no logDelivery
}
```

**Silent-skip path #3 — push filtered by user preferences (lines 85-88):**
```typescript
if (tokensToSend.length === 0) {
  console.log(`[FCM Consumer] Push filtered out by user preferences`);
  return;  // <-- no logDelivery
}
```

**Enum mapping (no migration needed):**
- Path #1 (farm not found): `failed` with `errorMessage: \`farm ${message.farmId} not found\``
- Path #2 (no active tokens): `failed` with `errorMessage: 'no active device tokens for farm owner'`
- Path #3 (filtered by prefs): `skipped_pref` (reuse existing enum — semantics match exactly; matches the LINE consumer's line 54 pattern)

**Existing log patterns in same file already follow convention (mimic them):**
- Line 28: `await logDelivery('skipped_gateway_down');` then `return;` (Firebase unavailable)
- Line 48: `await logDelivery('skipped_pref');` then `return;` (channel opted out)
- Line 126-128: `await logDelivery(result.successCount > 0 ? 'sent' : 'failed', { errorMessage: ... });` (final outcome)

**Sibling ticket — DO NOT execute, but be aware:** RIC-302 mirrors this pattern in `line.consumer.ts`. They are independent PRs; do not bundle.

**Cross-reference RIC-301:** Once Firebase creds are restored (RIC-301), the existing `'skipped_gateway_down'` path at line 28 will no longer fire — `isPushAvailable()` will return `true`. Confirm this is the intended behavior; do not modify that path.

**Jira:** https://mobileai.atlassian.net/browse/RIC-304
</existing_context>

## Examples

Three already-correct call sites in the same file, lines 28, 48, and 126-128. Match their style for every new call you insert.

## Output Format

**Branch:** `ric-304-fcm-silent-skip` off `develop`
**Commit format:** `fix(consumers): RIC-304 — log silent-skip paths in FCM consumer`
**PR title:** `RIC-304: log silent-skip paths in FCM consumer to alert_delivery_log`
**PR target:** `develop`
**Human merges** — do not self-merge.

Files modified:
- `src/consumers/fcm.consumer.ts` (+~9 lines)

Files added:
- `src/consumers/fcm.consumer.test.ts` (unit tests for all 3 new logged paths)

PR description must include:
- Link to RIC-304
- Sibling-link to RIC-302 PR (note that LINE pattern was applied here)
- Before/after acceptance query output
- Explicit note: "Path #3 uses `skipped_pref` (not `failed`) because user-preference filtering is a normal expected outcome, not an error"

## Reasoning Approach

**Test-first** (red → green → refactor) — follow the **integration-test pattern** the LINE sibling PR (RIC-302, PR #23) established. The repo does not use `mock.module`; it uses the shared TimescaleDB harness.

1. Write `src/consumers/fcm.consumer.test.ts`:
   - Use `getTestDb`, `truncateAll` from `@/test/harness/db-setup` and `seedTestUser`, `seedTestFarm` from `@/test/harness/fixtures`.
   - Set `process.env.FIREBASE_PROJECT_ID ??= 'test-project'`, `process.env.FIREBASE_CLIENT_EMAIL ??= 'test@example.com'`, `process.env.FIREBASE_PRIVATE_KEY ??= '-----BEGIN PRIVATE KEY-----\\nfake\\n-----END PRIVATE KEY-----\\n'` at the top of the file BEFORE importing `@/infrastructure/firebase`. (All three silent-skip paths return before any real FCM call, so dummy creds are safe.)
   - **`handleFCMConsumer` takes TWO arguments**: `(message: AlertMessage, context: ConsumerContext)`. Always pass both; one-arg is a typecheck error.
   - Insert an `alerts` row to satisfy the `alert_delivery_log.alertId` FK before each test.
   - Test 1 ("farm not found"): ghost farmId → expect `failed` row, errorMessage contains ghost UUID.
   - Test 2 ("no active device tokens"): seed user+farm, no `device_tokens` rows → expect `failed` row, errorMessage about no tokens.
   - Test 3 ("filtered by prefs"): seed user+farm+device_tokens; configure `notification_settings` or `user_channel_prefs` so `shouldSendPush` returns false for the given category/severity → expect `skipped_pref` row.
   - For test 3, you may need to check `src/domains/push/shouldSendPush.ts` (or wherever it lives) to understand how to make it return false via DB state — read the function first, do not stub.
2. If docker test DB is up, run `bun test src/consumers/fcm.consumer.test.ts` and confirm all three are red.
3. Insert the three `await logDelivery(...)` calls. Paths #1 and #2 use `'failed'` with a discriminating errorMessage. Path #3 uses `'skipped_pref'` (no errorMessage needed — `skipped_pref` is self-describing, mirrors line 48 of the same file).
4. Run `bun test` (or at minimum `npx tsc --noEmit --skipLibCheck`). No regressions.
5. **Skip `bun run lint`** — repo-wide ESLint 9 config is currently broken on `develop`; not your responsibility.
6. Dispatch `feature-dev:code-reviewer` agent. Fix high-priority findings.
7. Commit + push + open PR against `develop`.

## Constraints

**Hard NOs:**
- Never `git push --force`.
- Never `git commit --no-verify`.
- Never merge the PR autonomously.
- Do not touch files outside `src/consumers/fcm.consumer.ts` and the new test file. No editing `line.consumer.ts` (that's RIC-302).
- Do not modify the `alert_delivery_log` schema or any migration — `failed` and `skipped_pref` enums already exist.
- Do not change the `console.log` / `console.error` lines — only add `logDelivery` before the `return`.
- Do not modify the device-token cleanup logic (lines 113-121) — that's correct and orthogonal.
- Do not add new dependencies.

**Required behaviors:**
- Read the entire `fcm.consumer.ts` file before editing.
- Distinguish path #3 (`skipped_pref`) from paths #1 and #2 (`failed`) deliberately. Don't blanket-apply `failed`.
- Tests must use `bun:test`, matching repo convention.

## Success Criteria

1. All three silent-skip paths now call `await logDelivery(...)` with the correct status enum and a discriminating `errorMessage` (for `failed` paths).
2. New tests in `src/consumers/fcm.consumer.test.ts` cover all three paths and pass.
3. Full `bun test` passes.
4. `bun run lint` passes.
5. Verification query (run after deploy):
   ```sql
   SELECT channel, status, count(*)
   FROM alert_delivery_log
   WHERE channel = 'FCM' AND created_at > now() - interval '1 hour'
   GROUP BY channel, status;
   ```
   shows distinct status values reflecting actual outcomes (`sent` / `failed` / `skipped_pref` / `skipped_gateway_down`).
6. PR opened against `develop`, awaiting human merge.

## Memory anchors

- **No opportunistic refactor.** The FCM consumer has multiple async DB writes and a token-cleanup loop. They work; leave them.
- **Final cross-cutting review.** Run `feature-dev:code-reviewer` across the diff before opening the PR.
- **Backport fixes to source.** If you discover the `logDelivery` contract has drifted from how `line.consumer.ts` uses it, flag in PR description — don't silently adapt.
