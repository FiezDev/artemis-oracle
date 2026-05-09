📡 Session: 7bb59da9 | qone_corp + artemis-oracle | multi-hour

# Handoff: FB Content Poster Full Stack Shipped (G5→G9)

**Date**: 2026-05-04 17:24
**Repo focus**: `~/dev-personal/qone_corp` (125 commits to main today); artemis-oracle vault for retro + wiki

## What We Did

- **G5 — Sub-workflow primitive**: fourth `workflow_nodes.node_type='sub_workflow'`, dispatch + resume + depth limit + cancel cascade + fan-out via `iterations[]` + reaper. Migration `0023`.
- **G6 — Universal source resolver registry**: 29 Tier-1 resolvers (YouTube ×5, Web ×2, Social ×6, Discussion ×3, Reference ×2, Newsletter ×2, Files ×4, Direct ×2, Internal ×3); detection chain + Zod canonical-output validator at boundary; SSRF defense in shared `_context.ts`. Final cross-cutting review caught SSRF + env-leakage + IDOR (per-task review approved cleanly).
- **G7 — FB Content Poster workflow**: 4-node DAG (resolver → conditional → 2× sub_workflow). Migrations `0025` (rename + sourceUrl + language) + `0026` (4-node seed).
- **G8 — Easy-to-use UX as LAW**: smart input, recent runs strip with rerun + edit-and-rerun, run detail page, mobile-first pass, **The 10 Laws** in `dashboard/CLAUDE.md`, custom `no-jargon` ESLint rule.
- **G9 — Trigger surface area**: `workflow_schedules` table, NL→cron translator, 60s-tick scheduler worker with FOR UPDATE SKIP LOCKED, schedule editor UI, webhook with timingSafeEqual + Idempotency-Key, sourceboard pick rerouted to FB Content Poster (old AI Inspire workflow preserved per Nothing is Deleted). Migrations `0027` + `0028`.
- **Engine bugs (live-test discovered, post-G9)**: B1 stale step_runs after wakeup completion (`0395b04`), B2 `review_items.gate_step_run_id` always NULL (`905f629`), B3 `advanceAfterNode` used stale `stepRun.input` snapshot vs live `runVars` (`6cd6c2b`).
- **UI bugs (intensive-test discovered)**: sourceInput required blocking eligibility (`c8b9cb3`), missing `app/workflows/[id]/page.tsx` causing RSC 404s (`556edda`), `listRuns()` no ORDER BY (`dc2ef55`).
- **Retro saved**: `ψ/memory/retrospectives/2026-05/04/17.10_fb-content-poster-stack-shipped.md`.
- **Wiki filed**: 1 source + 1 entity (`fb-content-poster`) + 5 concepts (`sub-workflow-primitive`, `source-resolver-registry`, `the-10-laws-easy-to-use`, `stale-docker-pattern`, `plan-per-batch`) + qone-corp entity update + index/log entries. Counts now 47/12/62/1/1 (121 pages).
- **Oracle synced**: 6 `arra_learn` calls (sub-workflow primitive, source resolver registry, stale docker, live-pipeline bug discovery, UX as LAW, plan-per-batch).

## Pending

### qone_corp uncommitted (review before next session)
- [ ] `dashboard/frontend/Dockerfile` — modified (the `npm install` + base-image fix from session)
- [ ] `dashboard/frontend/package-lock.json` — deleted (workspace lockfile lives at `dashboard/package-lock.json`)
- [ ] `dashboard/frontend/tsconfig.tsbuildinfo` — modified (probably build artifact, gitignore candidate)
- [ ] `dashboard/package-lock.json` — modified

### qone_corp stale branches (G5/G6 work merged to main; safe to delete after verifying)
- [ ] Delete `feat/sourceboard-workflow-g5`
- [ ] Delete `feat/sourceboard-workflow-g6`
- [ ] Delete `fix/agent-config-baseline`

### Verification still owed
- [ ] Verify long-form (`XJUpuOBpT-4` Deepseek V4) run actually completes through to FB post now that B3 is fixed
- [ ] Watch step 6 (Reel infographic via GPT Image) on the approved Short run — was last seen dispatching after gate submit

### G6 review backlog (deferred but tracked)
- [ ] FK constraints on `parent_run_id` + `parent_node_id` (Important #6)
- [ ] Shared types between FE/BE — `SubWorkflowConfig` is duplicated (Important #4)
- [ ] 3 Important + 3 Minor items still tracked from G6 final cross-cutting review

### Future
- [ ] Tier 2 source resolver additions as needed (Spotify, Vimeo, Bluesky) — pluggable, no engine changes
- [ ] End-to-end golden test for long-form (Deepseek V4) once B3 fix is verified

## Next Session

- [ ] Run a full long-form pipeline test against `XJUpuOBpT-4` to confirm B3 fix
- [ ] Confirm Reel infographic step 6 produces output on the approved Short run
- [ ] Review and commit (or revert) the 4 uncommitted files in `dashboard/frontend/`
- [ ] Delete the 3 merged feature branches in qone_corp
- [ ] Triage G6 review backlog — FK constraints + shared FE/BE types are the highest-leverage

## Key Files

- `dashboard/api/src/services/workflow-service.ts` — engine; B1/B2/B3 fixes here, plus `dispatchSubWorkflow`, `resumeParentAfterChild`, `reapStuckSubworkflowChildren`, `bootstrapRunFromNodes`, `listRuns`
- `dashboard/api/src/lib/source-resolvers/` — 29 resolver files + `_types.ts` / `_canonical-schema.ts` / `_detect.ts` / `_registry.ts` / `_context.ts` / `index.ts`
- `dashboard/api/src/workers/cron-scheduler.ts` — G9 60s-tick scheduler
- `dashboard/api/src/routes/webhooks.ts` — G9 webhook with timingSafeEqual + Idempotency-Key
- `dashboard/frontend/components/workflow-smart-input.tsx` — G8 smart input
- `dashboard/frontend/components/workflow-recent-runs-strip.tsx` — G8 recent runs
- `dashboard/frontend/eslint-rules/no-jargon.js` — G8 LAW enforcement
- `dashboard/CLAUDE.md` — The 10 Laws
- `dashboard/api/migrations/0023..0028` — all session migrations
- Vault retro: `ψ/memory/retrospectives/2026-05/04/17.10_fb-content-poster-stack-shipped.md`
- Wiki source: `wiki/sources/2026-05-04-fb-content-poster-stack-shipped.md`
