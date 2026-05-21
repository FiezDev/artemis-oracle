# RIC-302 — LINE consumer: log silent-skip paths to `alert_delivery_log`

## Role

You are a senior Bun/TypeScript engineer working on the RiceGuard alert pipeline. You are precise, minimal, and test-first by default. You understand RabbitMQ consumer patterns, Drizzle ORM, and the "no silent sentinels" rule from `vibe-engineer §D1`. You do not refactor neighboring code unless asked.

## Objective

Fix two silent `return;` paths in `src/consumers/line.consumer.ts` that bypass `logDelivery()`, causing the LINE alert channel to be invisible in `alert_delivery_log`. Both paths must call `await logDelivery('failed', { errorMessage })` before `return`, using an explanatory error message that discriminates the failure reason.

## Context

<existing_context>
**Repo:** `/home/bjgdr/dev-work/RG/Rice-Guard-API` (branch `develop`)
**Stack:** Bun 1.0+ + Elysia + Drizzle ORM + TimescaleDB + RabbitMQ
**Test runner:** `bun test` (units in `src/**/*.test.ts`, integration in `src/test/integration/`)

**Audit finding (2026-05-20):** LINE consumer is registered and processing ~110 alerts/day, but `alert_delivery_log` has **0** LINE rows over 7 days. Root cause: two silent `return;` paths bypass `logDelivery()` entirely.

**Affected file (verified 2026-05-20):** `src/consumers/line.consumer.ts`

**Silent-skip path #1 — farm not found (lines 45-49):**
```typescript
const farm = farmResult[0];
if (!farm) {
  console.error(`[LINE Consumer] Farm ${message.farmId} not found`);
  return;  // <-- no logDelivery
}
```

**Silent-skip path #2 — owner has no LINE UID (lines 65-69):**
```typescript
const user = userResult[0];
if (!user?.lineUserId) {
  console.log(`[LINE Consumer] Farm owner has no LINE user ID`);
  return;  // <-- no logDelivery
}
```

**Schema (no migration needed):** `alert_delivery_log` already has `failed`, `skipped_pref`, `skipped_gateway_down`, `sent`, `delivered`, `acked` enum values. Use `failed` with explanatory `errorMessage` for both paths.

**logDelivery contract (see `src/domains/audit/deliveryTimer`):**
```typescript
const logDelivery = deliveryTimer(message.alertId, 'LINE');
await logDelivery('failed', { errorMessage: '...' });
```

Existing successful paths in the same file already call `logDelivery('skipped_gateway_down')`, `logDelivery('skipped_pref')`, `logDelivery('sent')`, and `logDelivery('failed', { errorMessage })` — follow their style exactly.

**Sibling ticket — DO NOT execute, but be aware:** RIC-304 mirrors this pattern in `src/consumers/fcm.consumer.ts`. They are independent PRs; do not bundle them.

**Reference branch on Kwang's machine (NOT pushed, DO NOT fetch):** `fix-line-consumer-silent-skip` @ `fd7c1c6`. Re-implement from scratch — do not coordinate fetch.

**Jira:** https://mobileai.atlassian.net/browse/RIC-302
</existing_context>

## Examples

In the same file (`src/consumers/line.consumer.ts`), three patterns already follow the convention. Mimic them:

- **Line 27:** `await logDelivery('skipped_gateway_down');` then `return;` (LINE push not available)
- **Line 54:** `await logDelivery('skipped_pref');` then `return;` (user opted out)
- **Line 97:** `await logDelivery('failed', { errorMessage: String(result.error ?? 'unknown') });` then `throw new Error(...)` (push failed)

Error message wording suggestion (you may refine):
- Path #1: `errorMessage: \`farm ${message.farmId} not found\``
- Path #2: `errorMessage: 'farm owner has no LINE user ID'`

## Output Format

**Branch:** `ric-302-line-silent-skip` off `develop`
**Commit format:** `fix(consumers): RIC-302 — log silent-skip paths in LINE consumer`
**PR title:** `RIC-302: log silent-skip paths in LINE consumer to alert_delivery_log`
**PR target:** `develop`
**Human merges** — do not self-merge.

Files modified:
- `src/consumers/line.consumer.ts` (+~6 lines)

Files added:
- `src/consumers/line.consumer.test.ts` (unit tests for both new failure-log paths; mock `db` and `deliveryTimer`)

PR description must include:
- Link to RIC-302
- Diff summary
- Before/after acceptance query output (run the verification query in dev or against staging)

## Reasoning Approach

**Test-first.** This is the smallest-possible surface and high-leverage observability fix. Follow red → green → refactor:

1. Write `src/consumers/line.consumer.test.ts` as an **integration test** (not a unit test with module mocks — the repo does not use `mock.module` anywhere and prefers integration with the shared TimescaleDB harness):
   - Import `getTestDb`, `truncateAll` from `@/test/harness/db-setup`, and `seedTestUser`, `seedTestFarm` from `@/test/harness/fixtures`.
   - Set `process.env.LINE_CHANNEL_ACCESS_TOKEN ??= 'test-fake-token'` and `process.env.LINE_CHANNEL_ID ??= 'test-channel'` at the **top of the file, before** importing `@/infrastructure/line`. (Both silent-skip paths return before any real LINE API call, so a fake token is safe.)
   - **`handleLINEConsumer` takes TWO arguments**: `(message: AlertMessage, context: ConsumerContext)`. Build a stub `ConsumerContext = { queue: 'q.alert.line', messageId: 'test-message', retryCount: 0, routingKey: 'alert.WARNING.SYSTEM' }`. The TS type lets you call with one arg, but it will fail typecheck if you do — pass both.
   - Insert a real `alerts` row with a valid `farmId` so the `alertDeliveryLog.alertId` FK is satisfied.
   - Test 1 ("farm not found"): pass a ghost UUID `'00000000-0000-0000-0000-000000000000'` as the `message.farmId`. Assert `alert_delivery_log` has one row with `status='failed'` and `errorMessage` containing the ghost UUID.
   - Test 2 ("no lineUserId"): seed user (default `lineUserId=null`) + farm + alert. Pass the real `farm.id`. Assert one row with `status='failed'` and `errorMessage='farm owner has no LINE user ID'`.
2. Note: docker test DB must be running (`docker compose -f docker-compose.test.yml up -d timescaledb`). If port 5432 conflicts with another service, document the conflict in the PR description and leave the test for the reviewer to run.
3. Add the two `await logDelivery('failed', { errorMessage })` calls before each silent `return`. Net +2 lines in `line.consumer.ts`.
4. Run `bun test src/consumers/line.consumer.test.ts` if docker is up. Otherwise `npx tsc --noEmit --skipLibCheck` to at least typecheck the diff.
5. **Skip `bun run lint`** — repo-wide ESLint 9 config migration is broken on `develop`; lint errors are not yours. Note the gap in PR description as a follow-up ticket suggestion.
6. Dispatch the `feature-dev:code-reviewer` agent for a pre-PR review (simplicity, correctness, conventions). Fix high-priority findings.
7. Commit + push + open PR against `develop`.

## Constraints

**Hard NOs:**
- Never `git push --force`.
- Never `git commit --no-verify`.
- Never merge the PR autonomously.
- Do not touch files outside `src/consumers/line.consumer.ts` and the new test file. No "while I'm here" refactor of the FCM consumer (that's RIC-304's job).
- Do not add new npm/Bun dependencies — `bun:test` and Drizzle are already in place.
- Do not change the `alert_delivery_log` schema or any migration — the `failed` enum value already exists.
- Do not change the error log lines (`console.error` / `console.log`) — only add `logDelivery` before the `return`.
- Do not import or run anything from `q.alert.dlx` — that's RIC-305.

**Required behaviors:**
- Read the entire `line.consumer.ts` file before editing. Match its exact import / formatting / quote style.
- The new test file MUST use Bun's built-in `bun:test` (`import { describe, it, expect, mock } from 'bun:test'`), matching the existing tests under `src/domains/.../*.test.ts`.
- After the fix, manually inspect: `git diff src/consumers/line.consumer.ts` — diff should be ≤ ~6 net new lines.

## Success Criteria

1. Both silent return paths now call `await logDelivery('failed', { errorMessage })` before `return`.
2. New tests in `src/consumers/line.consumer.test.ts` cover both new failure-log paths and pass under `bun test`.
3. Full `bun test` passes (no regressions).
4. `bun run lint` passes.
5. Verification query (run after deploy by reviewer; you do **not** deploy in this ticket):
   ```sql
   SELECT channel, status, count(*)
   FROM alert_delivery_log
   WHERE created_at > now() - interval '1 hour'
   GROUP BY channel, status;
   ```
   should show LINE rows with status `failed` and explanatory `errorMessage` (assuming RIC-303 line_user_id seed has not yet landed — that's expected during this transitional window).
6. PR opened against `develop`, awaiting human merge.

## Memory anchors

- **Per-batch plan only.** This ticket is one batch. Do not write a plan that anticipates RIC-304's fix — that's a separate execution.
- **Final cross-cutting review.** Before opening the PR, dispatch the `feature-dev:code-reviewer` agent across the full diff. Don't trust per-task review alone.
- **No opportunistic refactor.** If you notice unrelated code smells in `line.consumer.ts`, leave them. Open a separate ticket if they matter.
