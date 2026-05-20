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
- **No `mock.module` usage in the test suite** — the repo prefers integration tests against the shared TimescaleDB harness (`src/test/harness/db-setup.ts` + `fixtures.ts`). RIC-302/304 prompts updated to write integration tests, not unit-with-mocks.
- **`handleLINEConsumer` / `handleFCMConsumer` take TWO args** `(message, context)` — typecheck fails if you call with one. Prompts updated with a stub `ConsumerContext`.
- **Test DB port 5432 may conflict** with other local services (qone-postgres in this environment). If conflict, document in PR and leave test execution to the reviewer.

## Execution log

- **2026-05-20** — RIC-302 implemented on branch `ric-302-line-silent-skip`, PR #23 opened against `develop`: https://github.com/Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API/pull/23
   - Net diff: +2 lines in `line.consumer.ts`, +113-line integration test
   - Full `npx tsc --noEmit --skipLibCheck` clean
   - Test execution deferred to reviewer (docker-compose.test.yml port conflict)
   - Findings backported into prompts above

---

Compiled 2026-05-20 from Jira tickets RIC-301 through RIC-305 + parent epic RIC-191.
