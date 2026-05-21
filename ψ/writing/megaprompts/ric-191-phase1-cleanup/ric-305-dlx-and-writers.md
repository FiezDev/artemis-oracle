# RIC-305 — DLX consumer + cooldown / delivery_state / access_audit writers

## Role

You are a senior Bun/TypeScript backend engineer with strong systems-engineering instincts: RabbitMQ topology + DLX, PostgreSQL state machines, observability patterns, and PDPA-aware access auditing. You think in terms of dead-letter recovery, idempotency, and writer-reader contracts. You implement carefully and test the failure modes, not just the happy paths.

## Objective

Wire **four** writers/consumers that the schema is ready for but no code exercises:

1. **`alert_cooldowns` writer** — persist cooldown state so it survives container restart (currently in-memory only, race-condition risk).
2. **`alert_delivery_state` writer** — record per-alert pending/sent/failed state for escalation-engine consumers.
3. **`alert_access_audit` writer** — log all alert-namespace GraphQL operations (queries, mutations, subscriptions) for PDPA compliance.
4. **DLX consumer** (`src/consumers/dlx.consumer.ts`) — subscribe to `q.alert.dlx`, log poison messages, write `failed` rows to `alert_delivery_state`.

Out of scope (do NOT implement here): escalation worker that promotes P2 → P1 if `pending` for 30 min. Separate ticket.

## Context

<existing_context>
**Repo:** `/home/bjgdr/dev-work/RG/Rice-Guard-API` (branch `develop`)
**Stack:** Bun + Elysia + GraphQL Yoga + `@graphql-tools/schema` + Drizzle ORM + TimescaleDB + RabbitMQ (`amqplib@0.10.9`) + Redis
**Test runner:** `bun test`

**Audit finding (2026-05-20):**

| Table | Rows | Schema present | Writer | Issue |
|---|---|---|---|---|
| `alert_cooldowns` | 0 | yes | none | `alert_rules.cooldown_minutes` references it; suspected in-memory cooldown only — race on container restart. Introduced 2026-04 in **RIC-203 S2-A**. |
| `alert_delivery_state` | 0 | yes | none | UNIQUE on `alert_id`, ENUM (`pending`/`sent`/`failed`) — escalation-ready, no writer. Introduced 2026-04 in **RIC-222 S3-A** originally as the **LoRa ACK state machine** for offline mesh delivery. The UNIQUE(alert_id) constraint was added in **RIC-191 code-review remediation (commit `4e4906e`, HIGH 2)** specifically because at-least-once redelivery was creating duplicates. **Heads-up:** writing `pending` here from `alertService.publish()` means the row's lifecycle is shared between the cloud cron pipeline and the LoRa ACK path. Re-read `src/domains/alert/` and any LoRa code (`src/domains/alert/sla.ts`, RIC-222 commits) before designing the writer to avoid stepping on the LoRa state-machine. If the schema doesn't support both clients cleanly, STOP and report. |
| `alert_access_audit` | 0 | yes | none | PDPA-driven RBAC view/ack audit — schema introduced in **RIC-207 S6**. `recordAlertAccess()` writer ALREADY EXISTS at `src/domains/audit/delivery-log.ts:79` (also from RIC-207 S6) — only callers are missing. |
| `q.alert.dlx` (RabbitMQ) | ~88K dead messages once (16h stall) | n/a | no consumer | poison messages stuck silently |

**Existing files to read before designing:**
- `src/infrastructure/cron/alertRulesCron.ts` — where to insert cooldown row
- `src/domains/alert/` — alertService that publishes to RabbitMQ (insert `pending` here)
- `src/graphql/` — schema + resolvers + context (where to hook GraphQL operation auditing)
- `src/consumers/mod.ts` — consumer registry (add `dlx.consumer.ts` here)
- `src/infrastructure/rabbitmq/` — connection + types (for DLX subscription)

**Sibling tickets — do NOT execute:**
- RIC-301 (creds), RIC-302 (LINE silent-skip), RIC-303 (line_user_id seed), RIC-304 (FCM silent-skip)
- This ticket is independent of all four and can ship before/after/parallel.

**Important pre-existing code (verified 2026-05-20 against `develop`):**

- `src/domains/audit/delivery-log.ts:79` already exports `recordAlertAccess(accessorUserId, action, opts)` — a fire-and-log writer for `alert_access_audit`. The function exists and is correct. **Zero callers in the codebase.** Your task on the audit writer is to **wire callers in the alert-namespace GraphQL resolvers**, not to write the function.
- `src/domains/alert/cooldown.ts` exists — read it first to understand the current in-memory cooldown logic before adding the DB writer.
- `src/db/schema/index.ts:2069` defines `alertAccessAudit` with columns `(accessorUserId, targetFarmId, targetAlertId, action, createdAt)`. Note: there is **no** `ip` / `user_agent` / `request_id` column. If the GraphQL plugin needs to capture these, STOP and report — a schema migration is out of scope for this ticket. Action strings should be operation names like `'alerts.list'`, `'alert.read'`, `'alert.acknowledge'`, `'alert.subscribe'`.
- `alertDeliveryLog` schema (lines 2044-2064) has `(alertId FK, channel, status, latencyMs, retryCount, userAck, errorMessage)` — already correct for the consumer-side `pending → sent/failed` updates.
- `recordDelivery()` and `deliveryTimer()` already exist in the same file as `recordAlertAccess` — use them for consumer writes; do not duplicate.

**Jira:** https://mobileai.atlassian.net/browse/RIC-305
</existing_context>

## Examples

- **Consumer pattern:** mimic `src/consumers/line.consumer.ts` for the DLX consumer shape — `handleDLXConsumer` exported function, registered in `src/consumers/mod.ts`.
- **Cron writer pattern:** read `alertRulesCron.ts` for the existing flow — your cooldown INSERT goes right next to wherever `cooldown_minutes` is currently consulted in memory.
- **GraphQL audit pattern:** GraphQL Yoga supports plugins via `useExtendContext` / `plugins: []`. Hook into the schema with an `envelop`-style plugin that fires on operation execution and records to `alert_access_audit` if the operation touches the alert namespace. Confirm exact plugin API by reading existing GraphQL setup in `src/graphql/`.

## Output Format

**Branch:** `ric-305-dlx-and-writers` off `develop`
**Commits (multiple, ordered, each independently revertable):**
1. `feat(cron): RIC-305 — persist alert cooldowns to alert_cooldowns table`
2. `feat(alerts): RIC-305 — write pending row to alert_delivery_state on publish`
3. `feat(consumers): RIC-305 — update alert_delivery_state on consumer outcome (sent/failed)`
4. `feat(graphql): RIC-305 — plugin to audit alert-namespace operations`
5. `feat(consumers): RIC-305 — DLX consumer for q.alert.dlx poison messages`
6. `test(*): RIC-305 — integration tests for all four writers`

**PR title:** `RIC-305: DLX consumer + cooldown / delivery_state / access_audit writers`
**PR target:** `develop`
**Human merges.**

Files added:
- `src/consumers/dlx.consumer.ts`
- `src/test/integration/cooldown-writer.test.ts`
- `src/test/integration/delivery-state-writer.test.ts`
- `src/test/integration/alert-audit.test.ts`
- `src/test/integration/dlx-consumer.test.ts`
- (Optional, only if you choose the plugin approach in 4f) `src/graphql/plugins/alert-audit.plugin.ts`

Files modified:
- `src/infrastructure/cron/alertRulesCron.ts` — INSERT to `alert_cooldowns` after rule eval
- `src/domains/alert/*.ts` (alertService publish flow) — INSERT `pending` to `alert_delivery_state`
- `src/consumers/line.consumer.ts`, `fcm.consumer.ts`, `sms.consumer.ts`, `sse.consumer.ts` — UPDATE `alert_delivery_state` to `sent` or `failed` after delivery (**coordinate carefully with RIC-302 / RIC-304 PRs to avoid merge conflicts**)
- `src/consumers/mod.ts` — register DLX consumer
- `src/domains/alert/resolver.ts`, `rules-resolver.ts`, `prefs-resolver.ts`, `src/domains/audit/resolver.ts`, `delivery-log-resolver.ts` — call `recordAlertAccess(...)` at the top of each operation (writer already exists at `src/domains/audit/delivery-log.ts:79`; do NOT add it again)

PR description must include:
- Link to RIC-305
- Architecture diagram (markdown / mermaid) showing: publish → `pending` → consumer → `sent`/`failed`, plus DLX path
- Coordination note: "If RIC-302 / RIC-304 are unmerged, this PR's consumer-update edits will conflict — rebase order should be 302 → 304 → 305"
- Acceptance-criteria checklist with verification queries

## Reasoning Approach

**Fix-first, then test** for the writers (they're additive, low risk). **Test-first** for the DLX consumer (failure-handling is the whole point of DLX).

Order of work:

1. **Cooldown writer (smallest blast radius first):**
   a. Read `alertRulesCron.ts` end-to-end. Find where `cooldown_minutes` is currently evaluated.
   b. Add `INSERT INTO alert_cooldowns (...)` after a rule fires. Drizzle insert via the existing client.
   c. Add TTL purge: a daily cron that deletes rows older than `now() - max(cooldown_minutes)` OR use a `deleted_at` sweep — pick one and document choice in PR.
   d. Write integration test: trigger a rule, assert row appears in `alert_cooldowns`.
2. **Delivery-state writer (publish side):**
   a. In `alertService` (whichever file publishes to RabbitMQ), INSERT `(alert_id, status='pending')` before `publish()`.
   b. Use `ON CONFLICT (alert_id) DO NOTHING` for idempotency.
   c. Integration test: publish an alert, assert `pending` row.
3. **Delivery-state writer (consumer side):**
   a. In each of `line.consumer.ts`, `fcm.consumer.ts`, `sms.consumer.ts`, `sse.consumer.ts`, UPDATE `alert_delivery_state.status` to `sent` or `failed` after the final outcome.
   b. Critical: coordinate with RIC-302 / RIC-304 to avoid conflict. If those are unmerged, suggest rebasing 305 last.
   c. Integration tests per consumer.
4. **GraphQL audit wiring (writer already exists — just add callers):**
   a. **Do not write a new writer.** `recordAlertAccess(accessorUserId, action, opts)` already exists at `src/domains/audit/delivery-log.ts:79`. It is fire-and-log (never throws), idempotent in spirit, and writes the columns the schema actually has: `accessorUserId`, `targetFarmId`, `targetAlertId`, `action`.
   b. Read existing alert-namespace GraphQL resolvers — `src/domains/alert/resolver.ts`, `src/domains/alert/rules-resolver.ts`, `src/domains/alert/prefs-resolver.ts`, `src/domains/audit/resolver.ts`, `src/domains/audit/delivery-log-resolver.ts`. Identify every Query, Mutation, and Subscription resolver in the alerts namespace.
   c. At the top of each resolver function, after auth context is resolved, call `recordAlertAccess(ctx.userId, '<operation-name>', { targetFarmId, targetAlertId })`. Use action strings like `'alerts.list'`, `'alert.read'`, `'alert.acknowledge'`, `'alertRule.create'`, `'alertRule.update'`, `'alertPref.update'`, etc.
   d. **Schema constraint:** there is no `ip` / `user_agent` / `request_id` column in `alert_access_audit`. Do NOT add migrations. If the team decides those are needed, that's a separate ticket.
   e. **PDPA defensiveness already handled by `recordAlertAccess`** (try/catch internal). Do not add extra wrapping.
   f. Optional alternative considered: a single envelop/Yoga plugin that auto-instruments all alert-namespace ops. Document tradeoffs in PR — explicit per-resolver calls are clearer at first; plugin is DRYer but harder to grep. Pick one and explain.
   g. Integration test: invoke Query.alerts via the resolver (existing test harness), then `SELECT * FROM alert_access_audit WHERE accessor_user_id = $1` and assert row exists with the right action.
5. **DLX consumer:**
   a. Test-first. Write `src/test/integration/dlx-consumer.test.ts`:
      - Inject a poison message into `q.alert.dlx` (or mock).
      - Assert DLX consumer logs the message to file + writes `failed` row to `alert_delivery_state` with `errorMessage: 'DLX after N retries'`.
   b. Implement `dlx.consumer.ts` modeled on `line.consumer.ts`'s shape.
   c. Register in `src/consumers/mod.ts`.
   d. Optional (note in PR, do NOT implement): Sentry forward — separate ticket.

After all five batches:
- Full `bun test` passes.
- `bun run lint` passes.
- Dispatch `feature-dev:code-reviewer` agent across the entire diff (this is a large PR — review is critical).
- Open PR.

## Constraints

**Hard NOs:**
- Never `git push --force`.
- Never `git commit --no-verify`.
- Never merge the PR autonomously.
- Never add a new RabbitMQ exchange, queue, or binding. The DLX queue (`q.alert.dlx`) and the alert exchange topology are already configured — only add a *consumer*.
- Never block GraphQL responses on audit-write failure (PDPA writer must be fire-and-log-failure, not throw).
- Never make the cooldown writer block alert publish — INSERT failures must be logged and tolerated (cooldown is observability/safety, not the critical path).
- Never bundle the escalation worker (P2→P1 promote) — that's a separate ticket.
- Never modify the `alert_cooldowns`, `alert_delivery_state`, `alert_access_audit` schemas. They exist; use them as-is. If they're insufficient, STOP and report — do not migrate.
- Do not add Sentry / external observability shipping in this PR — note as follow-up.

**Required behaviors:**
- All writers must be **idempotent** where the schema allows (UNIQUE constraints honored via `ON CONFLICT`).
- The DLX consumer must use the same connection / topology code as existing consumers — read `src/infrastructure/rabbitmq/` to find the helper.
- Audit writer must capture: `alert_id` (nullable for list queries), `user_id` (from GraphQL context), `action` (operation name), `ip`, `user_agent`, `created_at`. If `ip` or `user_agent` not available in context, NULL is fine.
- Coordinate sequencing with RIC-302 / RIC-304: if those are open as PRs, note in PR description that this PR should rebase after them.

## Success Criteria

1. **Cooldown:** within 5 min of deploy, `SELECT count(*) FROM alert_cooldowns` returns non-zero (assuming any alert rule fires).
2. **Delivery state (publish):** `SELECT count(*) FROM alert_delivery_state WHERE status='pending' AND created_at > now() - interval '1 hour'` returns non-zero after deploy.
3. **Delivery state (consumer):** rows progress from `pending` → `sent`/`failed` within the consumer cycle. Verify with: `SELECT status, count(*) FROM alert_delivery_state WHERE created_at > now() - interval '1 hour' GROUP BY status`.
4. **Access audit:** `SELECT count(*) FROM alert_access_audit WHERE created_at > now() - interval '1 hour'` returns non-zero after any GraphQL Query.alerts / Query.alert / Mutation.acknowledgeAlert / Subscription.alertCreated hit.
5. **DLX:** RabbitMQ Management UI shows `q.alert.dlx` either empty OR with non-zero "delivered" counter (proving the consumer is consuming). For each consumed message: a `failed` row appears in `alert_delivery_state`.
6. All integration tests pass under `bun test`.
7. `bun run lint` passes.
8. PR opened against `develop`, awaiting human merge.

## Memory anchors

- **Per-batch plan only.** Even though this ticket has 4 sub-deliverables, treat each as a sub-batch with its own plan. Do not pre-write the escalation worker.
- **Final cross-cutting review.** This is a large multi-file PR — `feature-dev:code-reviewer` agent across the full diff is non-negotiable before opening.
- **Land structural; defer verification when infra blocks.** If RIC-302 / RIC-304 are still open, land the consumer-side delivery-state updates anyway and document the rebase order. Don't wait.
- **Backport fixes to source.** If you discover the audit schema is missing a needed column (e.g., `request_id`), STOP and report — do not silently add a migration.
- **Disconnected code is invisible code.** Past lesson (2026-04-07 RIC-159/160 retrospective): files created but never registered in GraphQL schema / DB schema / app startup are dead weight. Apply here: the DLX consumer MUST be registered in `src/consumers/mod.ts` *and* boot-time wiring in `src/index.ts` (or wherever consumers are started); same for any audit-plugin hook. Verify by reading the startup path end-to-end, not just by writing the file.
- **at-least-once redelivery creates duplicates.** Past lesson (2026-04-27 RIC-191 code-review HIGH 2, commit `4e4906e`): the `alert_delivery_state.alert_id` UNIQUE constraint exists precisely because retries can re-enter. The publish-side INSERT must use `ON CONFLICT (alert_id) DO NOTHING` (or `DO UPDATE` if you're explicit about which fields are safe to update). The consumer-side UPDATE must be tolerant of races between consumer attempts. Do not skip the conflict handling — it is load-bearing.
- **No `--force`, no `--no-verify`, no self-merge.** Standard rule.
