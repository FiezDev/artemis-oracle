# RIC-191 Phase 1 Cleanup — Mega-Prompts

Five self-contained per-ticket prompts, each in COSTAR format, ready to feed to **Claude Code (Sonnet/Opus) with the `feature-dev` plugin** one at a time.

| Ticket | File | Type | Surface |
|---|---|---|---|
| RIC-301 | [`ric-301-restore-alert-creds.md`](ric-301-restore-alert-creds.md) | Ops / config | Prod EC2 env vars + 3rd-party consoles |
| RIC-302 | [`ric-302-line-silent-skip.md`](ric-302-line-silent-skip.md) | Code fix | `src/consumers/line.consumer.ts` |
| RIC-303 | [`ric-303-seed-line-user-id.md`](ric-303-seed-line-user-id.md) | Data + BE | DB seed + LIFF onboarding BE |
| RIC-304 | [`ric-304-fcm-silent-skip.md`](ric-304-fcm-silent-skip.md) | Code fix | `src/consumers/fcm.consumer.ts` |
| RIC-305 | [`ric-305-dlx-and-writers.md`](ric-305-dlx-and-writers.md) | Infra | DLX consumer + 3 audit writers |

## Recommended order

```
RIC-301 → (RIC-302 ∥ RIC-304) → RIC-303 → RIC-305
```

RIC-301 unblocks RIC-303 end-to-end verification. RIC-302 and RIC-304 are independent code fixes that can run in parallel sessions. RIC-305 is independent infra and can interleave anywhere.

## How to use

1. Open a fresh Claude Code session in `/home/bjgdr/dev-work/RG/Rice-Guard-API`
2. Paste one prompt verbatim as the first message
3. Let the executor work; gate the PR merge yourself
4. Move to the next prompt when the prior PR is merged to `develop`

## Conventions (encoded in every prompt)

- Branch: `ric-NNN-slug` off `develop`
- Commits: conventional (`fix(consumers): RIC-302 — ...`, `feat(infra): RIC-305 — ...`)
- One PR per ticket against `develop`
- **Human merges** — agent never self-merges
- Pre-PR gate: `bun test` + `bun run lint` green AND `feature-dev:code-reviewer` agent pass

## Memory anchors (baked into every prompt)

- Never `git push --force`, never `--no-verify`, never merge PR autonomously
- No opportunistic refactor outside ticket surface
- Dry-run SQL on prod before any UPDATE/DELETE
- If architecture won't work, STOP and report — don't go off-plan
- Land structural; defer end-to-end verification when blocked by orthogonal infra
- Backport mid-execution fixes to source spec/prompt

## Repo-state findings (verified 2026-05-20 against `develop`)

- **`bun run lint` is broken repo-wide** — ESLint 9 config migration not applied; `.eslintrc` not migrated to `eslint.config.js`. Prompts skip lint and suggest a follow-up ticket.
- **`recordAlertAccess` already exists** at `src/domains/audit/delivery-log.ts:79` with zero callers. RIC-305 prompt was updated to instruct "wire callers" not "write writer".
- **`recordDelivery` + `deliveryTimer` already exist** at the same file (lines 29 + 58) — RIC-302/304 prompts use these helpers, no new writer needed.
- **LIFF client already exists** at `src/infrastructure/line/client.ts:87` (`verifyAccessToken`) and `:114` (`getProfile`). RIC-303 prompt now points at this client instead of describing a new HTTP layer.
- **No `mock.module` usage in the test suite** — the repo prefers integration tests against the shared TimescaleDB harness (`src/test/harness/db-setup.ts` + `fixtures.ts`). RIC-302/304 prompts updated to write integration tests, not unit-with-mocks.
- **`handleLINEConsumer` / `handleFCMConsumer` take TWO args** `(message, context)` — typecheck fails if you call with one. Prompts updated with a stub `ConsumerContext`.
- **Test DB port 5432 may conflict** with other local services (qone-postgres in this environment). If conflict, document in PR and leave test execution to the reviewer.

## Historical context (mined from git history + Oracle memory 2026-05-20)

- **Boris #102 = Phase 1 parent** (commit `8b3305e`, 2026-04-11). Established the alert-rules engine + 5-min cron + SMS-CRITICAL-only policy. All 5 prompts cite this audit.
- **RIC-191 Phase 2 shipped 2026-04-27** (`4ac2040`). RIC-202 (4-tier priority), RIC-203 S2-A/B/C (DISEASE/STAGE/CALENDAR), RIC-205 (image annotation; voice/IVR withdrawn), RIC-206 (channel prefs), RIC-207 (alertDeliveryLog + audit table + writers), RIC-222 (LoRa ACK state machine).
- **RIC-191 code-review HIGH findings** (`4e4906e`): MockCAProvider env gate, `alert_delivery_state` UNIQUE constraint, `sweepTimeouts` row-lock, migration idempotency, missing LoRa tests. The UNIQUE(alert_id) constraint is load-bearing — see RIC-305 prompt's "at-least-once redelivery" memory anchor.
- **`alert_delivery_state` was designed for LoRa ACK** (RIC-222 S3-A, commit `032b109`), not for general escalation. RIC-305 prompt now flags the shared-lifecycle risk.
- **Prod deploy is SSM-based, not SSH** (`.github/workflows/README-CICD.md`). The 2026-05-06 cutover dropped env vars because the prod `.env` lives on the EC2 host, not in CI secrets. RIC-301 prompt updated.
- **Disconnected-code lesson** (2026-04-07 retrospective on RIC-159/160): files created but never wired into schema/startup are invisible. RIC-305 prompt now reinforces this for the DLX consumer registration.
- **Severity-enum FE/BE coupling risk** (zenith-oracle reference doc): FE hardcodes `INFO|WARNING|CRITICAL`; BE migrated to P-tier. RIC-303 prompt flags this in the LIFF design doc as a Wasun follow-up.

## Execution log

- **2026-05-20** — All four code/structural tickets shipped to `develop`:
   - PR #23 (RIC-302 LINE silent-skip) merged 12:47 UTC
   - PR #24 (RIC-304 FCM silent-skip) merged 12:47 UTC
   - PR #25 (RIC-303 seed script + LIFF design doc) merged 13:09 UTC — discovered the LIFF BE endpoint already exists (`Mutation.linkLineAccount`)
   - PR #26 (RIC-305 DLX consumer + audit wiring) merged 13:10 UTC — two scope corrections recorded (cooldown writer not needed; `alert_delivery_state` is the LoRa ACK table, not generic delivery state)
   - RIC-301 remaining: confirmed via direct SSM into `i-0aa46f0468a9fd61e` that prod's `.env` has only placeholders. Fresh-issuance task pending vendor calls (LINE Console, Firebase Console, SMS vendor).

---

Compiled 2026-05-20 from Jira tickets RIC-301 through RIC-305 + parent epic RIC-191.
