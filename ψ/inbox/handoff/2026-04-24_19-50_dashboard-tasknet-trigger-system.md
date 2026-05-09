# Handoff: Dashboard TaskNet — Trigger Node System + Tabbed UI + Code Review

📡 Session: e1897b92 | qone_corp/dashboard | ~12h
**Date**: 2026-04-24 19:50 BKK
**Context**: heavy (1M); near reset

## Context
**Oracle**: Artemis (overseer) | **Human**: Fiez (FiezDev)
**Repo**: `/home/bjgdr/dev-personal/qone_corp/dashboard` (separate from artemis-oracle)
**Branch**: main (uncommitted)

## What We Did
- **Affiliate workflow restructured** — dropped storyboard/frames; repointed N5 to `reel-video-veo31` with fixed product prompt; deprecated `reel-generate-video` + `reel-extract-motion`; deleted 18 orphan scaffolding processes (42 → 24)
- **Trigger as new node type** — migration 0009 adds `node_type='trigger'` + `trigger_config jsonb`; modes manual/interval/scheduled (stacked). Auto-backfill for existing workflows. Editor UI in workflow-node-editor with mode selector + per-mode config fields
- **Trigger scheduler** — new `services/trigger-scheduler.ts`, ticks every 60s. Replaced legacy `scheduler-poller.ts`. Pg advisory lock for multi-replica safety, 24h backlog cap, structured tick log, `getLastTickAt()` for /health
- **Schedules system deleted** — migrations 0010 (migrate enabled schedules → trigger nodes) + 0011 (drop table + schedule_id column). Backend routes/service/schema removed. Frontend page + types + hooks removed. Sidebar nav cleaned
- **Tabbed Workflows UI** — `/workflows` rewritten with Configured / Builder / Running tabs. Running tab auto-refreshes (5s), shows pending-review violet badge, expandable cards with inline `<GateReviewPanel>`. New run detail page `/workflows/[id]/runs/[runId]/page.tsx` with node timeline + embedded gate
- **Inline gate review** — extracted `<GateReviewPanel>` component from old `/gates/[gateId]/runs/[runId]/review/page.tsx`. Old route kept as thin wrapper for backwards compat. `/gates` removed from nav
- **Auto-regenerate workflow descriptions** — `regenerateDescription()` in workflow-service runs on `replaceWorkflowNodes`. One-shot SQL refresh on existing 5 workflows
- **Cascade bug fixed** — `completeStep` now also triggers `advanceAfterNode` for node-linked step_runs (legacy depends_on_step was empty for some workflows)
- **I/O schemas filled** for `nova-research-products`, `nova-research-viral-clips`, `pulse-publish`, `sage-write-captions`
- **`/df-code-review` ran** — 7 parallel agents, verdict **Needs Work**. Report at `dashboard/.reviews/2026-04-24-1730_dashboard-tasknet-integration.md`. 5 Critical, 13 High, 14 Medium, 2 Low
- **Critical fixes started** — out-of-band edits during this session (visible in system reminders) applied: gate-review-panel payload fix, partial unique index on workflow_nodes, trigger-scheduler advisory lock + backlog cap + extractSchemaDefaults hardening, GateReviewPanel canSelect/canEdit props wired through both callers, 0010 now also migrates schedules → trigger nodes

## Pending
- [ ] Verify out-of-band fixes built + deployed (frontend + api Docker images)
- [ ] Fix Critical #1 — gate approvals impersonate `artemis` (server must read agentId from header, not body)
- [ ] Fix High #6 — `replaceWorkflowNodes` not transactional
- [ ] Fix High #7 — `validateTriggerConfig` bounds (cap times[], cap every, integer enforce)
- [ ] Fix Critical #5 — Tab + RunCard a11y (role=tab, role=button disclosure, keyboard nav)
- [ ] Fix High #13 — Delete BuilderTab; collapse into ConfiguredTab
- [ ] Write `0011_rollback.sql` (per Nothing-Is-Deleted spirit)
- [ ] Decide on structural: `workflows.triggers jsonb` refactor (dissolves Critical #3 + High #12)
- [ ] Re-review patched scope after fixes land
- [ ] Daily Dance Clip workflow: still cancelled, awaiting decision on Vortex motion-extraction or skip

## Cleanup
- [ ] Many uncommitted files in `dashboard/` (none committed this session — Fiez owns commit timing)
- [ ] No open PRs
- [ ] Stale runs: all cancelled
- [ ] AI Search test run `66ede4c0` parked at gate, auto-completed by self during demo

## Key Files
**Backend (modified):**
- `api/src/services/workflow-service.ts` — TriggerConfig types, validateTriggerConfig, regenerateDescription, listRunsAcrossWorkflows, completeStep cascade fix
- `api/src/services/trigger-scheduler.ts` (new) — pollOnce, advisory lock, backlog cap, extractSchemaDefaults
- `api/src/services/loop-manager.ts` — scheduleId/workflowSchedules removed
- `api/src/db/schema/workflows.ts` — workflowNodes triggerConfig + lastFiredAt + firedTimes columns; partial unique index excluding triggers
- `api/src/routes/workflows.ts` — `/runs` cross-workflow endpoint
- `api/src/index.ts` — boots trigger-scheduler

**Backend (new migrations):**
- `api/migrations/0009_trigger_nodes.sql`
- `api/migrations/0010_trigger_scheduler.sql` (now also migrates schedules → triggers)
- `api/migrations/0011_drop_schedules.sql`

**Frontend (new + modified):**
- `frontend/app/workflows/page.tsx` — tabbed Configured/Builder/Running
- `frontend/app/workflows/[id]/runs/[runId]/page.tsx` (new) — run detail with node timeline + inline gate
- `frontend/components/workflow/gate-review-panel.tsx` (new) — payload fix, canSelect/canEdit props
- `frontend/components/workflow-node-editor.tsx` — Trigger button + TriggerConfigEditor
- `frontend/components/workflow-form.tsx` — passes triggers through
- `frontend/lib/queries.ts` — useRunsAcrossWorkflows, useSubmitGateReview invalidations, schedule hooks gone
- `frontend/lib/types.ts` — TriggerMode, TriggerConfig added; WorkflowSchedule removed
- `frontend/lib/constants.ts` + `frontend/components/sidebar.tsx` — Schedules + Gates nav items removed

**Review report:**
- `dashboard/.reviews/2026-04-24-1730_dashboard-tasknet-integration.md`

## Next Session

| Option | Command | What It Does |
|--------|---------|--------------|
| **Continue critical fixes** | `/recap` then resume #1, #6, #7, #5, #13 | Pick up the post-review fix queue |
| **Structural refactor** | `/recap` then "do triggers as workflows.triggers jsonb" | Dissolves 4 findings in one move |
| **Commit + PR first** | `git add` selective files, `gh pr create`, then continue | Lock in what works before more changes |
| **Fresh** | `/recap --quick` | Minimal context for new direction |
