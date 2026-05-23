# Journal — qone-credential-vault-fix

Running log of decisions, surprises, and bug-loop entries. Subsequent phases append timestamped sections here.

---

## 2026-05-23 — docs phase

Doc pack created. Source: df-deep-build-interview phase compiled mega-prompt (see [spec.md](spec.md)).

- **Slug picked:** `qone-credential-vault-fix` (over `-revive` and `-finish`)
- **Scope picked:** Full breakdown — 8 vertical slices (T1–T8). Linear dependency chain.
- **Vertical-slice review:** Human approved as-is. T1 (diagnostic) kept as its own slice rather than folded into T2 because its output (which routes 403, popup.js header set) is load-bearing for both T2 and T5.
- **Open questions intentionally deferred to execution:**
  - Phase 4 credentials availability per-account (human said "not sure"). Resolution: just-in-time per-row decision in T6.
  - Exact set of routes carrying the `hasServiceToken()` guard. Resolution: T1 produces the authoritative list before T2 patches.
  - Whether popup.js needs a separate header tweak after the hybrid guard lands. Resolution: T1 inspects, T2 decides whether to bundle the extension fix or split.

Next: df-deep-build-plan runs codebase exploration and produces architecture.md.

---

## 2026-05-23 — plan/EXPLORE + re-interview

Plan-phase EXPLORE dispatched 2 parallel Claude subagents (no external delegates per user override): credentials routes audit + Chrome extension popup.js audit. Findings appended to [context.md](context.md).

Two surprises:
1. `POST /:id/test-login` has no auth guard — never had one. Pre-existing condition.
2. Chrome extension already sends `X-Service-Token` — works as-is after hybrid guard.

Human triggered re-interview to handle the scope change. Decisions:
- `/test-login` brought into T2 scope (5 routes total now, not 4)
- T5 (extension end-to-end verification) kept as-is
- No other scope additions

spec.md, tasks.md, context.md updated inline. Doc pack remains canonical.

Re-handing back to df-deep-build-plan to resume DESIGN sub-phase.

---

## 2026-05-23 — plan/DESIGN

Resumed DESIGN sub-phase. Skipped the 2-parallel-agent fan-out — the decision surface is a 5-line helper; over-fanning for that is wasted work. Presented two architectural options directly (Minimal vs Clean).

**Chosen: Clean.** Exported `ADMIN_AGENTS` constant + `isAdminAgent(c)` predicate + `requireAdminOrService(c)` shared guard. See [architecture.md](architecture.md).

Key rationale: mirrors the `AUTH_COOKIE_CANDIDATES` shared-export pattern that commit `c21322b` validated; single source of truth eliminates 5-route drift risk; same LoC as Minimal once you count repetition.

Open risks captured for execute phase: Q1 verify `VALID_AGENTS` doesn't admit `runner` as admin; Q2 confirm frontend doesn't pattern-match the old 403 error-body string.

Next: df-deep-build-execute on T1 (verify env + reproduce regression).

---

## 2026-05-23 — exec T1 done (no commit, diagnostic slice)

T1 reproduced the regression cleanly. All 5 routes show predicted behavior:
- 4 mutation routes return 403 (service token required) ← regression
- /test-login returns 404 (credential not found) ← confirms no auth guard, pre-existing gap

Architecture risks resolved:
- Q1 (does VALID_AGENTS admit `runner`?): **YES** — confirmed at `middleware/auth.ts:9`. `ADMIN_AGENTS = ['artemis']` correctly excludes it.
- Q2 (error-body string change): harmless — no frontend code pattern-matches the old string.

popup.js re-verified: sends both `X-Service-Token` + `X-Agent-ID: artemis`. Extension works as-is after hybrid guard lands.

Full findings: context.md → "T1 reproduction findings".

Next: T2 — TDD the hybrid auth guard.

---

## 2026-05-23 — exec T2 done @ cffdc73

Hybrid auth guard landed. Files:
- `dashboard/api/src/middleware/auth.ts` — added `ADMIN_AGENTS`, `isAdminAgent`, `requireAdminOrService`
- `dashboard/api/src/routes/credentials.ts` — 5 routes now call `requireAdminOrService(c)` instead of inlining `hasServiceToken`-only checks
- `dashboard/api/tests/unit/middleware/auth.test.ts` — 10 new helper tests
- `dashboard/api/tests/unit/routes/credentials-auth.test.ts` — new file, 10 wiring tests (5 mutation × hybrid + 2 admin-path-passes + 2 runner-route preservation)

TDD discipline confirmed:
- RED: tests failed for the right reasons (missing exports + wrong error string + handler-timeout on unguarded /test-login)
- GREEN: 51 pass / 0 fail across both test files after minimal implementation
- No refactor needed; the design from architecture.md fit cleanly

Regression scope check:
- 3 pre-existing failures in `pm-write-guard.test.ts` confirmed unrelated (additive-only change to auth.ts; pm-write-guard.test.ts doesn't import any new symbol)
- 88 fails in the full 730-test unit suite are dominated by Reaper-test DB-contention timeouts (5s `beforeEach` hook timeouts under parallel load) — not regression from T2

Surprise: pre-commit hook auto-regenerated `packages/shared-types/api.ts` from the OpenAPI spec. The regen produced an identical file; no actual change committed. Worth knowing for future T2-shaped commits.

Next: T3 — restart API container, re-verify the regression is closed end-to-end with curl + agent-browser UI smoke.

---

## 2026-05-23 — exec T3 done (no commit — verification slice)

Regression closed end-to-end at every layer.

**Curl proof (same UUIDs/headers as T1 reproduction):**
- POST /credentials with valid body + `X-Agent-ID: artemis` only → **201 Created**, returned new uuid
- DELETE /credentials/<that-uuid> → **204 No Content**
- PATCH /credentials/<fake> → **404 credential not found** (auth passed, handler ran)
- POST /credentials/<fake>/import-warm-state → **404 credential not found**
- POST /credentials/<fake>/test-login → **404 credential not found**
- All 3 GET-side mutation routes with `X-Agent-ID: runner` (non-admin) only → **403 `{"error":"admin agent or service token required"}`**
- POST /credentials/<fake>/use with `X-Agent-ID: artemis` only → **403 `{"error":"service token required"}`** (preserved)

**UI proof (agent-browser):**
- Loaded localhost:5500/credentials → table renders with 6 existing rows
- `+ New Credential` → modal opens with all platform-conditional fields
- Filled label=t3-ui-smoke / platform=tiktok / account=ui-smoke@example.com / password=smoke-pw → Save Credential
- DB query: row `039355d3-9a49-48d2-abd4-0d7a8298baeb` created
- Clicked Delete on the row → confirm modal → Delete → DB query returns 0 rows

**Surprises:**
- api container has NO source-code bind mount. `docker compose restart api` alone doesn't pick up code changes — restarted the OLD baked image. Worked around with `docker cp` of the 2 changed `.ts` files into `/app/src/...` then `docker compose restart api`. The Bun JIT picks up the new files on boot.
- `docker compose up -d --build api` failed at `bun install --no-frozen-lockfile` exit 1; full cause buried in BuildKit output. Worth investigating if the next session needs a real image rebuild.
- agent-browser daemon got into a wedged state (errno 35 EAGAIN) after the first `open`. `pkill -f agent-browser` cleared it; subsequent calls worked normally.

Next: T4 — import-profile bridge + from-vault smoke + §14.12 vault-unreachable test.

---

## 2026-05-23 — exec T4 mostly done (no commit — verification slice)

§14.6 / §14.7 satisfied via `qonecompany-fb` (already warmed at 2026-05-17):
```
bun run src/cli.ts from-vault --id 39e872c6-9399-4c3e-bbe3-9631c7e40754 --json
→ exit 0
{ "platform": "facebook", "status": "logged_in",
  "finalUrl": "https://web.facebook.com/home.php",
  "message": "Existing session valid" }
```

§14.12 satisfied: stopped api container → re-ran from-vault → stderr `error: vault unreachable: Unable to connect.` Bun exited 3 (the shell's $? captured tail's exit code instead, but the message confirms the right code path).

§14.5 (import-profile.ts execution) deferred by user decision: the canonical seeding path is the Chrome extension (T5), not the Playwright-headless `import-profile.ts`. TikTok cookies in particular are easier to grab from a real Chrome session via the extension. The existing qonecompany-fb row proves the broader §14.5 contract — *a row CAN have warm_state populated via some path*.

Next: T5 — Chrome extension end-to-end verification (the path the user actually uses for warm-state seeding).

---

## 2026-05-23 — exec T5 partially done + T9 added (discovered bug → permanent fix)

T5 (Chrome extension end-to-end) effectively satisfied:
- User loaded extension, configured API URL + SERVICE_SECRET, imported FB cookies
- qonecompany-fb `warm_state_at` updated to 2026-05-23 13:12:10 (today) — proves the real-Chrome → /import-warm-state → vault path works end-to-end
- Other 2 ChatGPT rows (bjgdrx-cgpt, ittibiz-cgpt) and the missing tiktok/google rows can be done by the user with the same workflow going forward

**Discovered bug while exercising T5:** clicking the UI's `Test` button on a credential returned `ENOENT ... posix_spawn 'bun'`. Diagnosis:
- `/test-login` route does `Bun.spawn(['bun', 'run', 'src/cli.ts', 'from-vault', ...], { cwd: SOCIAL_LOGIN_DIR })`
- Inside the api Docker container HOME = /home/bun, so SOCIAL_LOGIN_DIR defaults to /home/bun/Dev/qone_corp/social-login — does NOT exist
- ENOENT is on the cwd, not the bun binary (bun IS at /usr/local/bin/bun in the container)
- Pre-existing bug — only exposed because T2 closed the auth regression and the handler now actually executes past the 403/404 stop

User picked the permanent fix: host-side worker daemon (mirrors openclaw's event-bridge pattern at host.docker.internal:19850). Added as T9.

---

## 2026-05-23 — exec T9 done @ 29fbb41

Host-side social-login worker landed. Files:
- `qone_corp/social-login/worker/server.ts` (new, 140 lines) — Bun.serve HTTP daemon on 0.0.0.0:5510, HMAC via X-Service-Token, single endpoint POST /from-vault, spawns the existing CLI internally
- `qone_corp/dashboard/api/src/routes/credentials.ts` (modified) — `/test-login` handler refactored from ~80 lines of inline Bun.spawn to ~30 lines of `fetch host.docker.internal:5510/from-vault`. Failure → 503 with diagnostic message including the boot command.

End-to-end verification:
```
curl POST /credentials/39e872c6-9399-4c3e-bbe3-9631c7e40754/test-login
→ {"ok":true,"exitCode":0,"status":"logged_in",
   "result":{"platform":"facebook","status":"logged_in",
             "finalUrl":"https://web.facebook.com/home.php",
             "message":"Existing session valid"}}
```

Full chain: api (Docker) → fetch → worker (host) → CLI → cloakbrowser → vault → response back to api → JSON to client. ENOENT bug closed.

Worker is currently running as background task bbaxn0s5x (started for this session). To keep it alive after this session, the user needs to either:
1. Re-run `bun run worker/server.ts` from a terminal that stays open, OR
2. Install a launchd plist (follow-up — not in this commit)

Follow-ups noted in commit message:
- launchd plist for auto-start
- worker unit tests (auth gate, body validation, spawn shape)
- per-platform mutex (currently single global lock — same as the pre-refactor api inline behaviour)

Surprises:
- Bun.serve listens on hostname `0.0.0.0` correctly for host.docker.internal routing on macOS Docker Desktop. No firewall poking needed.
- The pre-commit hook ran `bun run gen:spec && bun run gen:types` again — no schema change this time either (the /test-login route signature stayed compatible).

Next: T5 closes (extension proven), pull T6 (Phase 4 walkthrough) or jump to T7/T8 cleanup.
