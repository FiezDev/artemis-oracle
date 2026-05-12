# AI Inspire Pipeline — Integration Spec

**Date:** 2026-05-13
**Status:** Draft, post live-test discoveries (this session)
**Owner:** Fiez
**Pairs with:** [Credential Vault + Social Login design](2026-05-10-qone-credential-vault-design.md) (Phase 1–4 already shipped)
**Implementation target:** `qone_corp/dashboard/`, `qone_corp/social-login/`, `qone_corp/agents-v2/*/AGENTS.md`

---

## 0. Why this doc exists

Two recent sessions independently shipped large pieces of an AI-content pipeline:

- **Cred-vault session (2026-05-10):** built `qone_corp/social-login/` adapters (tiktok, facebook, google, openai_web), TOTP, `from-vault --id` CLI, profile-import bridge, and the dashboard `credentials` table + CRUD UI.
- **This session (2026-05-12 → 13):** built process versioning (issues #6–#9), all-reject feedback loop (#10–#11), Telegram inline-button gates (#12–#13), AI Inspire daily workflow seed (#14), nova prompt v2 (#15), 2hr Bangkok scheduler (#16), workflow engine dynamic fan-out (#17), Mac runner adapter, dashboard SSE keepalive, and a *parallel* `scripts/facebook-post-cloak.mjs` (which duplicates work that should live in `social-login`).

The pieces ship green tests but **fail to compose end-to-end** when actually run:

1. Nova spawns inside hermes' docker terminal sandbox, so `curl localhost:5501` from the LLM tool calls hits the container loopback, not the host API. (Fix landed mid-session: `TERMINAL_ENV=local` in `~/.hermes/.env`.)
2. The legacy `YouTube Summarize to Facebook Post` workflow uses `workflow_steps` (step-id keyed) while the new engine endpoint `POST /workflows/runs/:runId/iterations` requires `nodeId`. Nova picks the wrong endpoint and the run stalls.
3. The dispatch envelope passes the ORIGINAL workflow `variables` to every step but NOT upstream step output. Pulse can read step 1's task row, sees `output: null` (output lives in `workflow_step_runs`, not `tasks`), concludes there's no data, and self-blocks.
4. Headless cloakbrowser hits Facebook's anti-bot trust filter on first login and bounces back to `/login`; a one-time visible login is required per profile.
5. `pulse-post-facebook` AGENTS.md still references the linux-rooted `/home/bjgdr/oracle/artemis-oracle/scripts/facebook-post.py`. The Mac path exists at `/Users/fiez/Dev/artemis-oracle/scripts/facebook-post.py` (legacy, uses `agent-browser`) and now a duplicate at `facebook-post-cloak.mjs` (cloakbrowser). Pulse doesn't know which to invoke or that `social-login` even exists.

This doc unifies the pieces, marks what's done vs left, and locks the architectural decisions so future builds aim at the same target.

---

## 1. North star

> One human types a YouTube URL into a workflow's `--variables`. Twelve hours later, that video's top topics are posted to the AI Inspire Facebook page on a 2-hour drip during Bangkok working hours, with all-rejected runs surfacing a "fix the prompt" gate in Telegram. No manual login, no manual endpoint juggling, no zombie Chromium processes.

The 12 steps the user originally described map to existing pieces:

| Step | Capability | Owned by |
|---|---|---|
| 1. Interval trigger (daily) | `workflow_schedules` cron | `dashboard/api/src/cron/cron-scheduler.ts` |
| 2. New-video check + history | `nova-youtube-channel-watch` + `source_board.lastSeenCursor` | nova agent |
| 3. Stop-if-no-new | Workflow conditional / empty fan-out | engine (#17) |
| 4. Multi-topic summary | `nova-youtube-topic-summary` v2 | nova (#15) |
| 5. Factcheck + expand | `nova-factcheck-expand` | nova |
| 6+7. Translate-to-TH + polish | `nova-translate-polish` v2 (de-AI rules) | nova (#15) |
| 8. De-AI rules | (folded into step 6/7; no separate process) | nova v2 prompt |
| 9. Image per topic | `reel-aiinspire-gpt-image-infographic` | reel agent |
| 10. Per-topic user gate (fix/redo) | `human_gate` node + Telegram inline buttons (#12) + all-reject loop (#10/#11) | gate-service + telegram router |
| 11. Login to FB page | `social-login` package — `loginFacebookFromVault` | pulse runner shell |
| 12. 2hr scheduler 08–22 Bangkok | `approved_topic_queue` + `bangkok-scheduler` (#16) | api/src/services/approved-queue |

Every primitive is shipped. The gaps are integration, not capability.

---

## 2. What's already built (component inventory)

### 2.1 Credential vault (cred-vault session — done, in production)

- `credentials` table (migration `0032_credentials.sql`), envelope encryption (KEK in `dashboard/api/.env:QONE_VAULT_KEY`, per-row DEK).
- `dashboard/api/src/routes/credentials.ts` — list/create/delete/`use`/`status`.
- `dashboard/frontend/app/credentials/page.tsx` — table + new-credential modal.
- `social-login/src/{tiktok,facebook,google,openai_web}.ts` — `loginXxxFromVault({ credentialId, ... })`. Each handles `web_password` + optional TOTP, captures `storage_state`, pushes warm session back via `pushSessionState`.
- `social-login/src/cli.ts from-vault --id <uuid>` — platform-dispatching CLI; exit codes `0=logged_in, 1=needs_human, 2=bad_credentials, 3=error`.
- `social-login/src/browser.ts` — `openContext` (persistent on-disk profile) and `openContextEphemeral` (warm-state-JSON-only, no `userDataDir`). Cloakbrowser-based; `--fingerprint=<seed>` stable.
- `import-profile.ts` (cred-vault) — one-shot tool to migrate existing on-disk profiles into the vault as warm session state.

### 2.2 Process versioning (this session, #6–#9)

- `process_versions` table; `processes.defaultVersionId`; `workflow_nodes.processVersionId` for pinning.
- Default vs latest banner; explicit `v3 📌 (pinned · default v7 · latest v9)` rendering.
- Hard delete with referential gates (409 on only/default/pinned).
- Frontend timeline at `/processes/[id]/versions`.

### 2.3 All-reject feedback (this session, #10–#11)

- `workflows.onAllReject = 'noop' | 'process-revision'`.
- `all_reject_sessions` table; status state machine `pending_a → pending_b → resolved/dismissed/cancelled`.
- `maybeOpenGateA`, `resolveGateA`, `resolveGateBCreateNew`, `resolveGateBRollback`, `resolveGateBCancel`.
- `ProcessReviser` interface — `PrismProcessReviser` (Axiom-prism delegated) and `ManualFillReviser` (placeholder draft, NOT auto-promoted to default — security).

### 2.4 Workflow engine fan-out (this session, #17)

- `workflow_nodes.fanOutFrom` (jsonpath like `upstream.topics`) + `fanOutMaxItems`.
- `startProcessNode` resolves the path at dispatch time, sizes `iterationOutputs`, dispatches iteration 0 with `__currentItem`.
- `handleIterationSettled` reads dynamic count from `iterationOutputs.length` (not static `node.repeatCount`).

### 2.5 AI Inspire daily workflow (this session, #14)

- Workflow row `wf-ai-inspire-daily-mp317w5t` with 6 nodes (trigger + 5 process), opts into `onAllReject='process-revision'`.
- Soft-retire mechanism: `workflows.retired = true` + `retiredAt`.
- Approved-queue + 2hr Bangkok scheduler (#16): `auto-enqueue` on gate approve, `bangkok-scheduler.ts` drains via `FOR UPDATE SKIP LOCKED`.

### 2.6 Telegram inline-button gates (this session, #12–#13)

- `POST /api/v1/telegram/callback/:agentId` with HMAC-signed callback_data + single-use `telegram_callback_nonces` table.
- Per-agent bots; auth bypass for `/telegram/callback/*` via `EXTERNAL_POST_PREFIXES`.
- Per-topic gate buttons + Gate A / Gate B buttons for all-reject.

### 2.7 Mac dev parity (this session, infra)

- `runner/adapters/hermes-cli.ts`; per-agent `HERMES_HOME` symlink layout under `~/.hermes-agents/<agent>/`.
- `agent-dispatch.ts` reads `AGENTS_V2_ROOT` → falls back to `QONE_AGENTS_DIR` → linux default.
- `~/.hermes/.env` `TERMINAL_ENV=local` so hermes terminal runs on host, not docker sandbox.
- Bun.serve `idleTimeout: 180s` (so long-running endpoints don't 502).

### 2.8 Dashboard ergonomics (this session)

- `/credentials` Test button + Visible Login button per Facebook row (this session). **Should be replaced by `social-login` adapter invocations, not the parallel `facebook-post-cloak.mjs` script.**
- SSE keepalive at `GET /api/v1/events`.
- Frontend Docker `--add-host=api:host-gateway` so the baked `api:5501` proxy works.

---

## 3. Live-test discoveries (the gaps)

Things that pass tests in isolation but fail when actually composed:

| # | Symptom | Root cause | Owns | Fix scope |
|---|---|---|---|---|
| G1 | `pulse-post-facebook` AGENTS.md points at a linux script | Procedure was authored on the linux dev host; never updated for Mac. There are now THREE candidates (legacy `.py` agent-browser, new `.mjs` cloakbrowser, the real `social-login/from-vault` CLI). | pulse AGENTS.md, social-login docs | Edit AGENTS.md to dispatch via `social-login` CLI; archive the two scripts |
| G2 | Step 3 (pulse) sees `tasks/WF-…-S3.output = null` and self-blocks | The dispatch envelope only carries the root workflow `variables`, not upstream `workflow_step_runs.output`. `pulse-dequeue-approved-topic` / pulse-post needs the topic text + image path from steps 1/2. | `agent-dispatch.ts`, envelope writer | Add `previousStepOutputs: { [stepOrder]: output }` to the envelope; update AGENTS.md to read it |
| G3 | Nova picks `/workflows/runs/:runId/steps/:stepId/complete` instead of `/iterations` | Two completion endpoints exist (legacy steps-based, new node-based). Nova can't tell which to call from the envelope alone. | runner-prompt template, AGENTS.md | Drop legacy steps-based `/complete` for any workflow whose run has `nodeId`; OR have the dispatcher write the exact completion URL into the envelope |
| G4 | Headless FB login bounces to `/login` | FB's anti-bot does not trust a fresh stealth Chromium profile. One human-completed login per profile (cookies) establishes trust. | Operator workflow | Visible Login button (already shipped) covers this; **must be run once per Facebook credential per machine before headless will succeed** |
| G5 | Concurrent Test buttons crash with `SingletonLock` | All facebook creds share one cloakbrowser profile `~/.config/facebook-browser-profile`. Two simultaneous launches fight. | dashboard route | Single-flight mutex in `POST /credentials/:id/test-login` (shipped). Long-term: each credential gets its own profile dir keyed by `id` |
| G6 | The new node-based `wf-ai-inspire-daily-mp317w5t` doesn't show "composed" cards on `/workflows` | Workflows list UI reads `steps[]` (legacy), the new workflow uses `nodes[]`. | dashboard list page | Render either `steps[]` or `nodes[]` (whichever non-empty) in the card |
| G7 | I built `scripts/facebook-post-cloak.mjs` instead of using `social-login` | Cross-session blind spot. The cred-vault session built the right abstraction and I missed it. | this doc + future PRs | Delete `facebook-post-cloak.mjs` once `social-login` gains a `post-facebook` subcommand (see §5.3) |
| G8 | Existing nova-runner prompt instructs `curl ... /iterations` but nova invents `/steps/.../complete` anyway | Model quality / mid-prompt drift | runner prompt | Tighten prompt: include literal exit-on-completion check; OR add a thin client helper `qone-tasknet complete-iteration` so there's only one entrypoint |

---

## 4. Decisions to lock in

### D1 — One CLI for stealth-browser social work: `social-login from-vault`

Nothing else writes a parallel cloakbrowser entry point. `scripts/facebook-post-cloak.mjs` (this session) **will be deleted** once `social-login` grows a posting subcommand (§5.3).

**Why:** Two implementations means two places that need anti-bot tweaks, two places that bind to the vault API, two places that own the profile dir. The cred-vault session already converged on `social-login`; further work extends it.

### D2 — Envelope carries upstream outputs

`dispatchToAgent` writes the inbox envelope today as `{ runId, stepRunId, stepOrder, input, dispatchedAt }`. **Add `previousStepOutputs: Record<number, unknown>`** populated from `workflow_step_runs.output` for every completed predecessor in the same run.

**Why:** Today downstream agents have to recursively query the API to reconstruct what their predecessors produced. That's both a latency hit and a path for "tasks table says null but step_runs has the data" confusion (G2). The dispatcher already has the data — just hand it over.

### D3 — One completion endpoint

`POST /workflows/runs/:runId/iterations` is the canonical agent → engine completion path. The legacy `POST /workflows/runs/:runId/steps/:stepId/complete` keeps working for old node-less workflows (`workflow_steps`-only model) but is **deprecated**. New workflows MUST use `workflow_nodes`. The runner-prompt only ever shows the iterations endpoint.

**Why:** Two paths → model gets confused (G3). The legacy path also lacks the iteration-fan-out semantics that the new engine needs.

### D4 — One Facebook profile per credential, not per platform

Move from `~/.config/facebook-browser-profile` (shared) to `~/.config/social-login-profiles/<credential-id>` (per-credential). Multiple FB accounts coexist; tests can run in parallel.

**Why:** G5. Plus: when we rotate a credential, blowing away its profile is now safe (no other accounts depend on it).

### D5 — Posting is a `social-login` subcommand, not a workflow process body

The runtime path is: `pulse-post-facebook` process → AGENTS.md tells pulse to invoke `bun run from-vault post-facebook --credential-id <uuid> --text "..." --image /path`. The `social-login` package gains `post-facebook` (and later `post-tiktok`, `post-instagram`).

**Why:** Today the process *prompts* describe browser automation step-by-step, which the LLM has to follow correctly every time (it doesn't — G8). Hardening this means making the LLM call a single deterministic command, not perform browser ops itself.

### D6 — The cred vault is the source of truth for warm session state

Cred-vault session §10.1 already locked this. Reaffirmed here: nothing else stores Facebook cookies on disk beyond what `openContext` writes to the per-credential profile dir, AND that profile dir is periodically uploaded to the vault as `warm_state_*` after each successful login. On failure, the next attempt restores from vault.

### D7 — Visible Login is the documented onboarding step

For every new Facebook credential, the operator clicks **Visible Login** on `/credentials` exactly once. The Chromium window opens, they sign in (including any 2FA / device verification), and the resulting cookies populate the profile + push to the vault. After that, headless posts work indefinitely (until FB's next device-trust roll).

**Why:** Headless-from-scratch is fighting FB. Visible-once-then-headless is a battle-tested pattern.

---

## 5. Concrete next-steps (priority order)

### 5.1 [P0] Add `post-facebook` to social-login [D5]

```ts
// qone_corp/social-login/src/facebook.ts
export async function postFacebookFromVault(opts: {
  credentialId: string;
  pageId: string;
  text: string;
  imagePath?: string;
  allowTextOnly?: boolean;
  headed?: boolean;
}): Promise<{ ok: true; url: string; screenshot: string } | { ok: false; reason: string }>;
```

CLI: `bun run from-vault post-facebook --id <uuid> --page-id 1136813799507714 --text "..." --image /path/to/img.jpg`. Output: single JSON line on stdout.

Internally: reuse `openContext` with persistent profile keyed by credential-id (D4); call existing `runFacebookFlow` to ensure logged-in; on success, open composer, type, attach, click Post; screenshot; on 2FA/checkpoint return `needs_human` (exit 1).

**Then delete** `artemis-oracle/scripts/facebook-post-cloak.mjs` and the dashboard's parallel test endpoint, replacing both with calls to the CLI.

### 5.2 [P0] Envelope carries upstream outputs [D2]

Edit `dashboard/api/src/services/agent-dispatch.ts` — when writing the envelope, query the run's completed step_runs and inline their outputs as:

```jsonc
{
  "runId": "...",
  "stepRunId": "...",
  "stepOrder": 3,
  "input": { /* root variables, unchanged */ },
  "previousStepOutputs": {
    "1": { "topics": [...], "videoTitle": "..." },
    "2": { "approvedTopics": [0], "humanSelection": {...} }
  },
  "dispatchedAt": "..."
}
```

Update each agent's AGENTS.md ("Read `previousStepOutputs[N]` for step N's output"). Drop the recursive `curl` pattern.

### 5.3 [P1] Update pulse AGENTS.md [G1]

Replace the current "verify the browser helper exists" + `python3 scripts/facebook-post.py` section with:

```
1. Compose your final caption + image (from previousStepOutputs).
2. Invoke: cd $QONE_CORP_DIR/social-login && bun run from-vault post-facebook \
     --id <process.input.fb_credential_id> --page-id 1136813799507714 \
     --text "$CAPTION" --image "$IMAGE_PATH"
3. Parse stdout JSON. If ok=true, POST /iterations with output=<json>.
   If ok=false, POST /iterations with status=failed, error=<reason>.
```

### 5.4 [P1] Dispatch envelope writes the canonical completion URL [D3, G3, G8]

Add `"completionUrl": "http://localhost:5501/api/v1/workflows/runs/<runId>/iterations"` directly to the envelope. AGENTS.md tells nova/pulse/herald to `curl -X POST $envelope.completionUrl` — no URL synthesis, no endpoint guessing.

### 5.5 [P1] Workflow list renders nodes-based workflows [G6]

`dashboard/frontend/app/workflows/page.tsx` workflow card: render the composition from `nodes[]` when `steps.length === 0 && nodes.length > 0`. Currently it shows "No composition yet — add nodes via Edit" for any node-based workflow, hiding `wf-ai-inspire-daily-*` from human awareness.

### 5.6 [P2] Per-credential profile dir [D4, G5]

Move `~/.config/facebook-browser-profile` (shared) → `~/.config/social-login-profiles/<credential-id>` everywhere. Cleanup script removes the old shared profile after migration; warm states already in the vault don't care about disk layout.

### 5.7 [P2] Profile-import for cookies harvested via Visible Login [D6, D7]

After a Visible Login completes successfully, the script should:

1. Capture `storage_state` from the persistent profile.
2. `pushSessionState(credentialId, JSON.stringify(state))` to the vault.
3. Next headless run on a different machine restores from the vault (via `openContextEphemeral`) — instant trust, no FB challenge.

(The cred-vault session already wrote the `pushSessionState` and `openContextEphemeral` primitives — they just aren't being called by anyone yet. §10.1 of the cred-vault spec is the binding.)

### 5.8 [P3] Multi-channel YouTube source-board + watermarks [step 2 of north star]

Today `wf-ai-inspire-daily-mp317w5t` has `nova-youtube-channel-watch` with `repeatCount: 1`. Real production wants N channels driven by `source_board WHERE type='youtube-channel' AND enabled=true`. Use the existing fan-out (§2.4) by pointing `fanOutFrom: 'sources'` at a tiny source-list-emitter node.

### 5.9 [P3] Workflow run page surfaces upstream step outputs

`/workflows/runs/:runId` should render each step_run's `output` as collapsed JSON cards. Today the user has to query the DB to see what nova produced. The frontend Workflow Run detail page exists but doesn't render outputs cleanly.

### 5.10 [P4] Move FB poster, approved-queue scheduler, and reel image-gen onto cron-driven service tokens

Right now the 2hr Bangkok scheduler ticks but each post requires pulse to be alive (runner ticking, hermes spawnable). For lights-out operation, the scheduler should directly invoke `social-login from-vault post-facebook` as a child process — no agent involvement for the deterministic posting step.

---

## 6. What "v1 production-ready" looks like

A morning checklist when this is done:

1. `oracle-skills status` shows `bangkok-scheduler` and `cron-scheduler` running.
2. `/credentials` shows green dot on the AI Inspire FB credential row (last Test succeeded).
3. `/workflows` shows `wf-ai-inspire-daily-mp317w5t` with the 6-node composition rendered.
4. `gh issue list --label "ai-inspire-pipeline"` is empty.
5. Yesterday's run shows: trigger → channel-watch fan-out → topic-summary → factcheck → polish → image → gate → enqueue → 8-slot drip across the day, with FB post URLs in `workflow_step_runs.output` for each iteration.

Failure cases handled:

- A channel returns no new videos → branch ends silently, no gate spam.
- All topics from a video are rejected → onAllReject Gate A fires Telegram with "fix the prompt?" buttons; admin clicks Yes → Gate B picks the offending process → Prism drafts a new version → admin promotes → next day's run uses v(N+1).
- FB credential expires → next post fails with `needs_human`, run goes blocked, Telegram alert. Admin clicks `Visible Login` on `/credentials`, signs in, headless resumes.

---

## 7. Cross-references

- **Cred-vault design:** [`2026-05-10-qone-credential-vault-design.md`](./2026-05-10-qone-credential-vault-design.md) — §3 architecture, §4 data model, §7 adapters, §10 warm-state SSOT.
- **Cred-vault implementation plan:** [`../plans/2026-05-10-qone-credential-vault.md`](../plans/2026-05-10-qone-credential-vault.md) — task-by-task build (already shipped).
- **This session's commits:** `feature/issue-6-process-versioning-foundation` branch in `qone_corp` (commits `e3b5cc0` → `d3767f0`).
- **Code review trail:** `.reviews/2026-05-12-2030_session-implement-review.md` in qone_corp.

---

## 8. Open questions

These don't block the priority work but should be answered before the corresponding phase:

| # | Question | Best guess |
|---|---|---|
| Q1 | When pulse-post fails with `needs_human`, does the workflow run get auto-retried after manual Visible Login? | No retry today. Either add a "Retry from this step" button on the run detail page, or make `gate-service.unblockTask` reset the step_run to `available`. |
| Q2 | Should the scheduler drain queue regardless of the credential's last_status, or skip the row when last_status=bad_credentials? | Skip and alert. Posting with known-bad creds wastes profile trust budget with FB. |
| Q3 | When all-reject Gate B drafts a new prompt version via ManualFillReviser, who is responsible for promoting it to default? | The admin, via the dashboard `Set as default` button on the version timeline. The current Gate B flow stops at "draft created". |
| Q4 | Per-credential profile dir (§5.6) vs shared — does cloakbrowser's fingerprint seed alone suffice for FB account-distinct sessions in one profile? | Probably not — FB device-trust is bound to the cookies in the profile, not just the fingerprint. Per-credential dirs are safer. |
| Q5 | Should Q3's "promote new version" itself fire a Telegram confirmation? | Yes — Q3 means a live prompt change; admins want a single-click "yes, ship it" path mirroring Gate A/B. Folds into a future "version-promote gate". |

---

## 9. Changelog

| Date | Change |
|---|---|
| 2026-05-13 | Initial draft after live-testing the AI Inspire daily workflow exposed the integration gaps (G1–G8). |
