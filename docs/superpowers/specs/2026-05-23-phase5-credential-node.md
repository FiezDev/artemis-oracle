# Phase 5 — Credential Workflow Node + Direct-Action Adapter

**Date:** 2026-05-23
**Status:** Draft, in active implementation
**Owner:** Fiez
**Builds on:** [2026-05-10 qone_corp Credential Vault](2026-05-10-qone-credential-vault-design.md) (v1, shipped)
**Implementation target:** `qone_corp/dashboard/` + `qone_corp/social-login/`

---

## 1. Problem statement

The v1 credential vault stores encrypted credentials and provides `/use` for runners to fetch the decrypted payload. But there's no first-class way for workflows to declare "use this credential for this branch of work." Today's processes (`pulse-post-facebook`, `hermes-fb-post`) are LLM-driven — they emit prompt templates to an agent whose skills handle credentials internally. That works for LLM-judgment workflows but doesn't support deterministic, direct-action flows (e.g., "log into FB as account X, post this exact thing, return the post URL").

Phase 5 adds:

1. **A new workflow node type `credential`** that selects a credential and propagates it to downstream nodes via the workflow run's `variables` jsonb.
2. **A direct-action runner adapter `social-login.ts`** that calls the social-login worker (the host-side daemon from [the T9 commit](https://github.com/fiezdev/qone_corp/commit/29fbb41)) with a structured action verb (`validate`, `post`, `scrape`, etc.).
3. **A first direct process** (`social-login-validate-credential`) that proves the adapter works end-to-end.
4. **Pre-flight gating** — if the credential validates as `needs_human`, the workflow pauses on a gate review pathway, just like every other human-intervention point in the system today.
5. **CredentialPicker UI** in the workflow builder so the new node type is configurable from the dashboard.
6. **Per-credential advisory locking** so two concurrent workflows can't race on the same warm session.

These pieces coexist with existing LLM-driven processes; nothing existing changes.

---

## 2. Decisions log

| # | Question | Choice | Rationale |
|---|---|---|---|
| 1 | New node type or reuse existing `process` with a special process? | **New `node_type='credential'`** | First-class visual representation in the workflow diagram. Cleaner separation of concerns: a credential node is config (not work), so it gets its own type rather than masquerading as a process. |
| 2 | How does credentialId reach downstream nodes? | **Write to `workflow_runs.variables.currentCredentialId`** | Existing infrastructure — `variables` jsonb is already merged into every downstream node's `input` per `_step-engine-advance.ts:153-156`. No new schema. |
| 3 | Multiple credentials in one workflow? | **Yes, via multiple credential nodes** | Each credential node writes to the run variables with its own scope (e.g., `currentCredentialId` for the latest, plus a numbered array). Initial v5.0 ships with single-credential support (just `currentCredentialId`); array-based scoping is a follow-up if needed. |
| 4 | Where does the adapter live? | **`api/runner/adapters/social-login.ts`** | Mirrors existing pattern (`hermes-cli.ts`, `openclaw-cli.ts`). Implements the same `Adapter` interface from `runner/adapters/types.ts`. |
| 5 | Action verbs? | **Start with `validate` only; add `post`, `scrape` as platform-specific processes ship** | Avoid premature design of the action surface. The first direct process is `social-login-validate-credential` which uses `validate`. Future verbs follow when there's a concrete consumer. |
| 6 | What does `validate` actually do? | **Call worker `/from-vault` headless** | Same code path the dashboard's "Test" button uses today. Returns logged_in / needs_human / bad_credentials / error. |
| 7 | needs_human handling | **Reuse `gate-handler.ts::parkAtGate`** | Per spec §13, existing infrastructure supports `waiting_for_human` + `gate_review` jsonb. Credential node sets up a "credential review" gate that the operator approves after re-warming. |
| 8 | Concurrency lock scope | **Per-credentialId, via `pg_advisory_lock` on a hash-derived bigint key** | Mirrors `trigger-scheduler.ts:63-76` exactly. Pinned client connection, `lock()` / `unlock()` pair. |
| 9 | UI scope for v5.0 | **CredentialPicker + node card; no inline credential creation from the workflow builder** | Reuse existing `/credentials` modal for creation. The picker just selects from `useCredentials()`. |
| 10 | Backward compat | **Existing 5 node types (`trigger`/`process`/`gate`/`subworkflow`/`conditional`) unchanged.** New type is purely additive. | Zero risk to existing workflows. |

---

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Workflow Run                                                              │
│  ─────────────                                                             │
│                                                                            │
│  ┌─ trigger ─┐                                                             │
│  │ (manual)  │                                                             │
│  └─────┬─────┘                                                             │
│        ▼                                                                   │
│  ┌─ credential ─┐                                                          │
│  │ nodeId: c1   │  variable_overrides:                                     │
│  │              │  { credentialId: "39e872c6...", preflight: true }        │
│  └──────┬───────┘                                                          │
│         │                                                                  │
│         │  runner side-effect:                                             │
│         │  1. Acquire pg_advisory_lock(hash(credentialId)) on pinned conn  │
│         │  2. If preflight: fetch worker /from-vault headless              │
│         │     → if needs_human → parkAtGate() with payload={credentialId,  │
│         │                          reason: 'needs_human', lastError}      │
│         │                          → workflow pauses, run.status='blocked' │
│         │  3. Otherwise → UPDATE workflow_runs SET variables = jsonb_set(  │
│         │     variables, '{currentCredentialId}', '"39e872c6..."'::jsonb)  │
│         │  4. Mark step_run done                                           │
│         │  5. Lock RELEASED on workflow-run completion (advisory_unlock    │
│         │     via finalize hook in workflow-runs.ts)                       │
│         ▼                                                                  │
│  ┌─ process ──────────────────────────────────────────────┐                │
│  │ direct-post-facebook  (future; v5.0 ships *-validate)  │                │
│  │ adapter: runner/adapters/social-login.ts               │                │
│  │ adapter.invoke({                                       │                │
│  │   action: 'validate',  // or 'post', 'scrape', ...     │                │
│  │   credentialId: input.currentCredentialId,             │                │
│  │   args: { ... }                                        │                │
│  │ }) → fetch worker host.docker.internal:5510            │                │
│  │      with X-Service-Token                              │                │
│  └────────────────────────────────────────────────────────┘                │
└────────────────────────────────────────────────────────────────────────────┘
```

The credential node is **light** at runtime: it acquires a lock, optionally pre-flights via the worker, and writes one field to the run's variables. The heavy lifting stays in the worker + adapter layer.

---

## 4. Data model

### 4.1 No schema migration

The credential node reuses existing columns on `workflow_nodes`:

| Column | Used for |
|---|---|
| `node_type` | New value: `'credential'` |
| `variable_overrides` (jsonb) | `{ credentialId: string; preflight?: boolean }` |
| `depends_on_node_order` (int[]) | Standard dependency wiring |

And reuses `workflow_runs.variables` (jsonb) for the per-run propagation:

```jsonc
{
  "currentCredentialId": "39e872c6-9399-4c3e-bbe3-9631c7e40754"
  // future: "credentialsByPlatform": { "facebook": "...", "tiktok": "..." }
}
```

### 4.2 Validation

Zod schema in `api/src/lib/schemas/workflows.ts` (or wherever node config validation lives) gets a new branch:

```ts
const CredentialNodeConfig = z.object({
  credentialId: z.string().uuid(),
  preflight: z.boolean().optional().default(false),
});
```

The existing workflow_nodes-write validation rejects `node_type='credential'` unless `variable_overrides` parses against this schema.

---

## 5. Backend dispatch — `_step-engine-advance.ts`

A new 5th branch in the dispatch chain at lines 140–194 (the `else if` chain). Right after the `subworkflow` branch:

```ts
} else if (ds.nodeType === 'credential') {
  await credentialNodeHandler.execute({
    runId,
    stepRunId: dsStepRun.id,
    nodeId: ds.id,
    config: parseCredentialConfig(ds.variableOverrides),
    runVars,
  });
}
```

The handler in a new file `api/src/orchestration/workflows/credential-node/handler.ts`:

```ts
export async function execute(opts: {
  runId: string;
  stepRunId: string;
  nodeId: string;
  config: { credentialId: string; preflight: boolean };
  runVars: Record<string, unknown>;
}): Promise<void> {
  // 1. Per-credential advisory lock (pinned client; pattern from trigger-scheduler.ts:63-76)
  const lockKey = credentialIdToLockKey(opts.config.credentialId);
  const lockAcquired = await acquireRunCredentialLock(opts.runId, lockKey);
  if (!lockAcquired) {
    // Another workflow run is holding this credential. Mark step_run blocked
    // with a clear message; the engine will retry on the next advance pass.
    await markStepRunBlocked(opts.stepRunId, 'credential in use by another run');
    return;
  }

  // 2. Optional pre-flight via worker
  if (opts.config.preflight) {
    const validation = await callWorkerValidate(opts.config.credentialId);
    if (validation.status === 'needs_human') {
      await gateHandler.parkAtGate({
        runId: opts.runId,
        stepRunId: opts.stepRunId,
        nodeId: opts.nodeId,
        upstreamOutputs: [{ kind: 'credential_needs_human',
                            credentialId: opts.config.credentialId,
                            lastError: validation.message }],
        upstreamStepRunIds: [],
      });
      return;
    }
    if (validation.status === 'bad_credentials' || validation.status === 'error') {
      await markStepRunFailed(opts.stepRunId,
        `credential validation failed: ${validation.message}`);
      return;
    }
  }

  // 3. Write to run variables — readable by all downstream nodes
  await db.update(workflowRuns)
    .set({
      variables: sql`jsonb_set(${workflowRuns.variables}, '{currentCredentialId}',
                               to_jsonb(${opts.config.credentialId}::text))`,
    })
    .where(eq(workflowRuns.id, opts.runId));

  // 4. Mark step done — outputs include the resolved credentialId for visibility
  await db.update(workflowStepRuns)
    .set({
      status: 'done',
      output: { credentialId: opts.config.credentialId, validated: opts.config.preflight },
      completedAt: new Date(),
    })
    .where(eq(workflowStepRuns.id, opts.stepRunId));

  // 5. Lock release happens on workflow-run finalize (completed | failed | cancelled)
  // tracked in workflow_run_credential_locks table (see §6.3)
}
```

---

## 6. Per-credential advisory lock

### 6.1 Lock key derivation

```ts
import { createHash } from 'node:crypto';

export function credentialIdToLockKey(credentialId: string): bigint {
  // Postgres advisory locks are bigint (8 bytes). Take the first 8 bytes of
  // SHA-256(credentialId) and interpret as a signed bigint. Stable across
  // restarts; deterministic per credential.
  const buf = createHash('sha256').update(credentialId).digest().subarray(0, 8);
  // Force the high bit off so the bigint is positive (Postgres accepts
  // signed bigint but mixing signed/unsigned in queries is fiddly).
  buf[0] &= 0x7f;
  return buf.readBigInt64BE(0);
}
```

### 6.2 Lock acquisition — pinned client

Mirrors `trigger-scheduler.ts:63-76` exactly. A new helper at `api/src/orchestration/workflows/credential-node/lock.ts`:

```ts
export async function acquireRunCredentialLock(
  runId: string,
  lockKey: bigint,
): Promise<boolean> {
  const client = await pool.connect();
  try {
    const res = await client.query<{ locked: boolean }>(
      `SELECT pg_try_advisory_lock($1::bigint) AS locked`,
      [lockKey.toString()],
    );
    const locked = res.rows[0]?.locked === true;
    if (!locked) {
      client.release();
      return false;
    }
    // Persist the (runId, lockKey, client) triple so the finalize hook can
    // release on this exact connection. Postgres advisory locks are
    // connection-scoped — release must come from the same client.
    await db.insert(workflowRunCredentialLocks).values({
      runId, lockKey: lockKey.toString(), acquiredAt: new Date(),
    });
    pinnedClients.set(`${runId}:${lockKey}`, client);
    return true;
  } catch (e) {
    client.release();
    throw e;
  }
}

export async function releaseRunCredentialLocks(runId: string): Promise<void> {
  const rows = await db.select().from(workflowRunCredentialLocks)
    .where(eq(workflowRunCredentialLocks.runId, runId));
  for (const row of rows) {
    const client = pinnedClients.get(`${runId}:${row.lockKey}`);
    if (client) {
      await client.query(`SELECT pg_advisory_unlock($1::bigint)`, [row.lockKey]);
      client.release();
      pinnedClients.delete(`${runId}:${row.lockKey}`);
    }
  }
  await db.delete(workflowRunCredentialLocks).where(eq(workflowRunCredentialLocks.runId, runId));
}
```

### 6.3 New table: `workflow_run_credential_locks`

Migration `0050_workflow_run_credential_locks.sql`:

```sql
CREATE TABLE IF NOT EXISTS workflow_run_credential_locks (
  run_id      TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
  lock_key    TEXT NOT NULL,
  acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, lock_key)
);
```

(Lock keys stored as text since Drizzle's bigint binding can be awkward; we convert at query time.)

### 6.4 Release hook

The existing workflow-run finalize path (wherever `workflow_runs.status` transitions to `completed`/`failed`/`cancelled`) calls `releaseRunCredentialLocks(runId)`. Single new line. Also add to the runner restart / crash-recovery sweep.

---

## 7. Runner adapter — `social-login.ts`

New file at `api/runner/adapters/social-login.ts`. Implements the existing `Adapter` interface from `api/runner/adapters/types.ts`.

```ts
import type { Adapter, AdapterInvokeInput, AdapterInvokeResult } from './types.js';
import { hasServiceToken } from '../../src/middleware/auth.js';  // for typing

const WORKER_URL = process.env.SOCIAL_LOGIN_WORKER_URL
  ?? 'http://host.docker.internal:5510';
const SERVICE_SECRET = process.env.SERVICE_SECRET ?? '';

interface SocialLoginInvokeInput extends AdapterInvokeInput {
  action: 'validate' | 'post' | 'scrape';  // expanded over time
  credentialId: string;
  args?: Record<string, unknown>;
}

export const socialLoginAdapter: Adapter = {
  name: 'social-login',
  async invoke(input: SocialLoginInvokeInput): Promise<AdapterInvokeResult> {
    // For v5.0, only 'validate' is wired. Future actions add their own
    // worker endpoints; the adapter routes by action.
    if (input.action !== 'validate') {
      return {
        ok: false,
        exitCode: 3,
        error: `social-login adapter: action '${input.action}' not yet implemented in v5.0`,
      };
    }

    const res = await fetch(`${WORKER_URL}/from-vault`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Service-Token': SERVICE_SECRET },
      body: JSON.stringify({ credentialId: input.credentialId, headed: false, warmUp: false }),
    });
    if (!res.ok) {
      return { ok: false, exitCode: 3, error: `worker ${res.status}: ${await res.text()}` };
    }
    const body = await res.json() as {
      ok: boolean; status: string; exitCode: number; result: any; stderrTail: string;
    };
    return {
      ok: body.ok,
      exitCode: body.exitCode,
      output: { status: body.status, result: body.result },
      error: body.ok ? undefined : body.stderrTail,
    };
  },
};
```

Mounted in `api/runner/adapters/index.ts` next to the existing adapters.

---

## 8. First direct process — `social-login-validate-credential`

Seed data (a migration or a one-shot insert) that creates a `processes` row:

```sql
INSERT INTO processes (id, slug, name, agent_id, prompt_template, input_schema, output_schema)
VALUES (
  gen_random_uuid()::text,
  'social-login-validate-credential',
  'Validate a credential is still usable',
  'system',
  '',  -- direct adapters don't use prompt templates
  '{"type":"object","required":["credentialId"],"properties":{"credentialId":{"type":"string","format":"uuid"}}}'::jsonb,
  '{"type":"object","properties":{"status":{"type":"string"},"result":{"type":"object"}}}'::jsonb
);
```

The processExecutor dispatches direct processes via the social-login adapter when the process's agent_id is `system` and the slug matches a `social-login-*` pattern (or via an explicit `adapter` column on processes — see §11 open Q1).

---

## 9. UI — workflow builder

### 9.1 `<CredentialPicker>` component

New file `frontend/components/credential-picker.tsx`. Mirrors `ProcessPicker` from `workflow-node-editor.tsx:254-267`:

```tsx
'use client';
import { useCredentials } from '@/lib/queries';
import type { Credential } from '@/lib/types';

interface Props {
  value?: string;
  platform?: Credential['platform'];  // optional filter
  onChange: (credentialId: string) => void;
}

export function CredentialPicker({ value, platform, onChange }: Props) {
  const { data: credentials = [] } = useCredentials();
  const filtered = platform
    ? credentials.filter((c) => c.platform === platform)
    : credentials;
  return (
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value)} className="input">
      <option value="">— pick a credential —</option>
      {filtered.map((c) => (
        <option key={c.id} value={c.id}>
          {c.label} · {c.platform} · {c.account} · {c.lastStatus ?? '—'}
        </option>
      ))}
    </select>
  );
}
```

### 9.2 Credential node card

In `workflow-node-editor.tsx`'s `SortableNodeRow`, add a 5th branch in the switch around lines 214–250:

```tsx
case 'credential':
  return (
    <NodeCard icon={Key} color="emerald">
      <CredentialPicker
        value={(node.variableOverrides as any)?.credentialId}
        onChange={(id) => updateNode(node.id, {
          variableOverrides: { ...node.variableOverrides, credentialId: id },
        })}
      />
      <label className="text-xs">
        <input
          type="checkbox"
          checked={!!(node.variableOverrides as any)?.preflight}
          onChange={(e) => updateNode(node.id, {
            variableOverrides: { ...node.variableOverrides, preflight: e.target.checked },
          })}
        />
        Pre-flight validate before next step
      </label>
    </NodeCard>
  );
```

Plus a new "Add Credential" button alongside the existing Add Process / Add Gate buttons.

### 9.3 Icon + color

`Key` from `lucide-react` (matches the sidebar icon for /credentials). Emerald accent to visually distinguish from process (indigo) and gate (amber).

---

## 10. Acceptance criteria

1. Workflow with `[trigger] → [credential(preflight=true) → [process: social-login-validate-credential]` runs end-to-end and writes `currentCredentialId` to `workflow_runs.variables`.
2. The direct process reads `currentCredentialId` from its merged input and calls the social-login adapter, which routes through the worker and returns `logged_in`.
3. If the credential is in `needs_human` state, the credential node parks at a gate; `workflow_step_runs.status = 'waiting_for_human'`; the existing dashboard gate UI shows the entry.
4. After the operator re-warms the credential (via the existing extension or `--warm-up` flow) and approves the gate, the workflow resumes; downstream nodes run.
5. Two workflows that reference the same credentialId serialize via `pg_advisory_lock` — the second one's credential node marks `blocked` (with a clear message) until the first releases.
6. The credential node visually appears in the workflow builder with a `<CredentialPicker>` dropdown and a "Pre-flight" checkbox.
7. The lock is released when the workflow run reaches `completed`/`failed`/`cancelled`. A crash-recovery sweep also releases dangling locks at startup.
8. All existing workflow runs continue to work unchanged (existing 5 node types unmodified).

---

## 11. Open questions / risks

- **Q1: How does processExecutor route direct adapters?** Today processes are LLM-driven via `agent_id`. For direct adapters we either:
  (a) special-case `agent_id='system'` + slug prefix `social-login-*` → social-login adapter
  (b) add an `adapter` column to processes table (small migration)
  (c) use a new processes.kind enum (`'llm' | 'direct'`)
  I lean toward (b) — explicit, doesn't require slug conventions, future-proof for other direct adapters. Decide before T10 slice 3.

- **Q2: Lock-blocking UX.** If credential is in use, the second workflow's step_run marks `blocked` with a message. The existing dashboard surfaces `blocked` runs in the runs list; we should add a tooltip on hover showing the message. Or surface as a toast notification.

- **Q3: Pre-flight cost.** Calling worker `/from-vault` per credential node adds 2-5s latency to every workflow that uses it. For hot-path workflows, `preflight=false` is the right default; reserve `preflight=true` for first-of-day runs or after long idle.

- **Q4: Multi-credential workflows in v5.0.** v5.0 ships with single-credential propagation via `currentCredentialId`. If multiple credential nodes execute in sequence within one workflow, the later one overwrites the earlier. A platform-scoped map (`credentialsByPlatform`) is the natural next step but deferred until there's a concrete consumer.

- **Q5: `from-vault` worker uptime.** If the worker is down, all credential nodes fail. Already covered by the 503 + diagnostic message in `/test-login`; we should pipe the same message into the credential node's failure path so the operator sees it.

- **Q6: Concurrent same-credential workflows that BOTH want preflight.** Lock-then-validate could thunder-herd the FB account if multiple workflows pile up. Mitigation: the lock is held through validation, so only one validates at a time; others queue. Acceptable for v5.0.

---

## 12. Out of scope for v5.0 (deferred)

- Per-platform credential maps in run variables (Q4 above)
- `post`/`scrape` action verbs in the social-login adapter (will arrive with the first real direct process for each platform)
- Inline credential creation from the workflow builder (today the operator uses the existing `/credentials` modal)
- Notifications to operator when a credential lock blocks a workflow (we'll see if it's a real pain point first)
- Lock TTL / expiry — current design holds lock for workflow run duration; if a run hangs, the lock leaks. Crash-recovery sweep at api startup mitigates, but a TTL is cleaner. Add post-v5.0 if leaks happen.

---

## 13. File-level deliverables

| Path | Action | Notes |
|---|---|---|
| `docs/superpowers/specs/2026-05-23-phase5-credential-node.md` | Create | This file |
| `api/migrations/0050_workflow_run_credential_locks.sql` | Create | New table for lock tracking |
| `api/src/db/schema/workflow_run_credential_locks.ts` | Create | Drizzle schema |
| `api/src/db/schema/index.ts` | Modify | Re-export new schema |
| `api/src/orchestration/workflows/credential-node/handler.ts` | Create | The dispatch handler |
| `api/src/orchestration/workflows/credential-node/lock.ts` | Create | Advisory-lock acquire/release |
| `api/src/orchestration/workflows/runs/_step-engine-advance.ts` | Modify | Add 5th node-type branch |
| `api/src/orchestration/workflows/runs/_step-engine-bootstrap.ts` | Modify | Allow `credential` in the no-deps-treated-as-`available` path |
| `api/src/lib/schemas/workflows.ts` (or wherever node validation lives) | Modify | Accept `node_type='credential'` + validate `variable_overrides` shape |
| `api/runner/adapters/social-login.ts` | Create | New adapter |
| `api/runner/adapters/index.ts` | Modify | Register the adapter |
| `api/src/orchestration/processes/dispatch.ts` (or processExecutor) | Modify | Route to social-login adapter based on Q1 decision |
| Migration: `INSERT INTO processes (...)` for `social-login-validate-credential` | Create | Could be in 0050 or a sibling 0051 |
| `api/tests/unit/orchestration/workflows/credential-node-handler.test.ts` | Create | Handler logic (preflight branches, lock acquisition stub) |
| `api/tests/unit/runner/adapters/social-login.test.ts` | Create | Adapter routing |
| `frontend/components/credential-picker.tsx` | Create | Picker component |
| `frontend/components/workflow-node-editor.tsx` | Modify | Add credential branch in SortableNodeRow + Add Credential button |
| `frontend/lib/types.ts` | Modify | Extend NodeSpec (or equivalent) with credential variant |
| Workflow-run finalize path (TBD: search for status='completed' transition) | Modify | Call `releaseRunCredentialLocks(runId)` |
| API startup sweep | Modify | Release dangling locks for non-running workflow_runs |

---

## 14. Test plan

### Backend unit
- `credential-node-handler.test.ts` — preflight=false writes runVars + marks done; preflight=true with worker→logged_in does the same; preflight=true with worker→needs_human calls parkAtGate; lock acquisition failure marks blocked
- `lock.test.ts` — same credentialId across two runs: first acquires, second false; release unblocks
- `social-login.adapter.test.ts` — `validate` action routes to worker URL with right body; non-validate actions return error
- `step-engine-advance.test.ts` — extends existing test file with credential-node dispatch case

### Backend integration
- A real workflow with `[trigger] → [credential] → [process: social-login-validate-credential]` run via the orchestration endpoint — exercises the whole stack against the running api + worker
- §14.12-style: stop the worker, run the workflow → credential node fails informatively

### Frontend
- `credential-picker.test.tsx` — renders all credentials, filters by platform, calls onChange
- Workflow builder integration smoke (via agent-browser)

---

## 15. Notes for the reviewer

This spec assumes the v1 vault (already shipped) and the social-login worker (T9 commit `29fbb41`) work as documented. If either has shifted, audit before implementing.

The most fragile piece is the lock release on workflow finalize — Postgres advisory locks are connection-scoped, so the `releaseRunCredentialLocks` helper has to be called on the *same* `client` from `pool.connect()` that originally acquired the lock. The `pinnedClients` map tracks this. A leak here means stuck locks; the crash-recovery sweep at startup is the safety net.

The processExecutor routing (Q1) is the other place to push back if I've called it wrong. Adding an `adapter` column to `processes` feels right but is a small migration; the slug-prefix special-case is uglier but skips schema work.
