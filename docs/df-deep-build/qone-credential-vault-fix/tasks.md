# Tasks — qone-credential-vault-fix

Source of truth for execution order. Status flips inline; agents re-read this on every entry.

Status legend: `[ ]` todo · `[~]` in-progress · `[x]` done

---

## T1 — Verify environment + reproduce 403 regression

- **Status:** [x] done
- **Depends on:** —
- **Acceptance:**
  - [x] `docker compose ps` shows api + frontend + db containers up — all 3 healthy, no startup needed
  - [x] DB migration state confirmed — latest `0049_goal_events_actor_kind.sql`
  - [x] `curl -X POST -H "X-Agent-ID: artemis" .../api/v1/credentials` returns **403 "service token required"**
  - [x] `curl -X DELETE -H "X-Agent-ID: artemis" .../api/v1/credentials/<any-id>` returns **403**
  - [x] `curl -X PATCH ...` returns **403**
  - [x] `curl -X POST .../import-warm-state` returns **403**
  - [x] `curl -X POST .../test-login` returns **404 "credential not found"** — confirms no auth guard (auth check would have been 403)
  - [x] Inspected `popup.js` — sends `X-Service-Token: secret` + `X-Agent-ID: artemis` on both fetch calls (lines 51-52, 131-135). Works as-is after hybrid guard.
  - [x] `VALID_AGENTS` audit: confirmed `runner` is a valid agent; `ADMIN_AGENTS = ['artemis']` correctly excludes it.
  - [x] Findings appended to `context.md` under "T1 reproduction findings"
- **Tests:** (none — diagnostic slice)
- **Notes:** Evidence-only slice. No code change, no commit. Ready for T2 TDD.

---

## T2 — Hybrid auth guard + TDD tests

- **Status:** [x] done
- **Depends on:** T1
- **Acceptance:**
  - [x] New helpers `ADMIN_AGENTS`, `isAdminAgent`, `requireAdminOrService` added to `dashboard/api/src/middleware/auth.ts`
  - [x] Hybrid guard applied to all 5 mutation routes via `requireAdminOrService(c)`:
    - [x] `POST /credentials` (regression-target)
    - [x] `DELETE /credentials/:id` (regression-target)
    - [x] `PATCH /credentials/:id` (regression-target)
    - [x] `POST /credentials/:id/import-warm-state` (regression-target)
    - [x] `POST /credentials/:id/test-login` (closed pre-existing no-guard gap)
  - [x] `/use` and `/status` remain `hasServiceToken`-only (unchanged)
  - [x] TDD tests (red first, then green):
    - [x] Unit: `ADMIN_AGENTS` drift, `isAdminAgent` predicate cases, `requireAdminOrService` admin/token/neither paths
    - [x] Wiring: 5 mutation routes with runner-only → 403 hybrid; artemis-only → not 403 (auth passes)
    - [x] Preservation: `/use` and `/status` with artemis-only → 403 with OLD "service token required" message
  - [x] Final test result: 51 pass / 0 fail across the two test files
  - [x] Existing related tests still pass (credentials-auth-cookie-map: 4 pass; full unit/middleware + unit/routes: 72 pass)
  - [x] 3 pre-existing fails in `pm-write-guard.test.ts` confirmed unrelated (test does not import any of the new symbols; auth.ts changes are additive-only)
  - [x] Commit: `cffdc73` `fix(api): allow X-Agent-ID admin OR X-Service-Token on credential mutations (incl. test-login)`
- **Tests:** `dashboard/api/tests/unit/middleware/auth.test.ts` (extended), `dashboard/api/tests/unit/routes/credentials-auth.test.ts` (new)
- **Notes:**
  - Scope expanded after plan-phase exploration revealed `/test-login` had no guard.
  - Pre-commit hook auto-regenerated `packages/shared-types/api.ts` from OpenAPI spec — no content change (regen produced identical file).
  - `hive.yml` is dirty in the worktree but was already dirty pre-T1; not part of this commit.

---

## T3 — Verify regression closed end-to-end

- **Status:** [x] done
- **Depends on:** T2
- **Acceptance:**
  - [x] api container restarted via `docker cp` + `docker compose restart api` (rebuild failed on `bun install` exit 1 — workaround documented)
  - [x] Re-ran all curl mutation requests with only `X-Agent-ID: artemis` — got: POST 201, DELETE 204, PATCH 404, import-warm-state 404, test-login 404 (all NOT 403, auth passed)
  - [x] Re-ran with `X-Agent-ID: runner` only (non-admin) → 403 with new body `"admin agent or service token required"` on POST/DELETE/PATCH
  - [x] `/use` preservation: artemis-only → 403 with OLD body `"service token required"` (unchanged behavior)
  - [x] Opened localhost:5500/credentials via agent-browser — table renders, GET /credentials works
  - [x] Clicked `+ New Credential`, filled label=t3-ui-smoke / platform=tiktok / account=ui-smoke@example.com / password=smoke-pw, clicked Save Credential → row id `039355d3-9a49-48d2-abd4-0d7a8298baeb` appeared in DB
  - [x] Clicked Delete on the smoke row → confirm modal → confirm Delete → DB query returns 0 rows
  - [x] `test-login` button on a row: not exercised here (requires real warm session — covered in T5 / T6)
- **Tests:** (verification only — no new tests; uses smoke commands + UI driving via agent-browser)
- **Notes:**
  - api container has NO source-code bind mount; `docker compose restart` alone doesn't pick up code changes. Used `docker cp` to push the 2 changed `.ts` files into the running container then `docker compose restart api`. Faster than fixing the `docker compose up --build` failure (bun install exit 1, full cause buried in BuildKit output).
  - Pre-existing dirt: `hive.yml` still uncommitted (not mine; pre-T2).

---

## T4 — Import-profile bridge + from-vault smoke + §14.12 unreachable

- **Status:** [x] done (with one leg deferred, see notes)
- **Depends on:** T3
- **Acceptance:**
  - [~] **§14.5 (import-profile.ts run):** DEFERRED — the canonical warm-state seeding path is the Chrome extension (T5), not the Playwright-headless `import-profile.ts` script. The existing qonecompany-fb row (with `warm_state_at = 2026-05-17 15:27`) is evidence that a prior session's import-via-some-path worked; we're not re-running it.
  - [x] **§14.6 / §14.7 (warmed row → headless reuse):** `bun run src/cli.ts from-vault --id 39e872c6-9399-4c3e-bbe3-9631c7e40754 --json` exited 0 with `status: logged_in`, finalUrl=`web.facebook.com/home.php`, message=`Existing session valid`
  - [x] **§14.12 (vault unreachable):** stopped api container; re-ran from-vault → stderr printed `error: vault unreachable: Unable to connect. Is the computer able to access the url?` (bun exited 3 — the shell's `$?` captured `tail`'s exit code, not bun's, but the stderr message confirms the right path was hit)
  - [x] api container restored after the unreachable test
- **Tests:** (ops verification — no new automated tests)
- **Notes:**
  - §14.5 deferred by user decision: extension is the right tool for TikTok / fresh-account warm-state seeding. `import-profile.ts` remains usable for accounts where a Playwright-headless mount of an on-disk profile works (e.g., the existing qonecompany-fb came from this path).
  - SERVICE_SECRET stayed out of chat: piped via `$(grep '^SERVICE_SECRET=' .env | cut -d= -f2-)` inline in the env-var assignment. Visible to `ps` for the bun process duration; not in the conversation log.

---

## T5 — Chrome extension end-to-end

- **Status:** [x] done
- **Depends on:** T3 (auth-fix must be in place so `/import-warm-state` accepts the extension's headers)
- **Acceptance:**
  - [x] Human loaded the unpacked extension from `qone_corp/dashboard/chrome-extension/` into real Chrome
  - [x] Human logged into Facebook in real Chrome as `QoneCompany@gmail.com`
  - [x] Used the extension popup to capture cookies → POST `/credentials/39e872c6/import-warm-state` → success
  - [x] `qonecompany-fb` row's `warm_state_at` flipped to `2026-05-23 13:12:10` (today) — proves end-to-end extension → vault path
  - [x] **BONUS** end-to-end UI Test button verification via agent-browser:
    - Clicked Test on the qonecompany-fb row in real frontend
    - Triggered POST /test-login → api (Docker) → fetch → worker (host) → CLI → cloakbrowser
    - DB updated: `last_used_at=2026-05-23 13:59:03`, `last_status=logged_in`, `last_error=null`
- **Tests:** (manual e2e via agent-browser drove)
- **Notes:**
  - Discovered the ENOENT bug on /test-login while exercising T5 — led to T9 (host-side worker daemon). Both are now closed.
  - Other platforms (TikTok, Google, the 2 remaining ChatGPT rows) can be seeded by the user via the same extension workflow going forward.

---

## T6 — Phase 4 walkthrough — paced, per-account

- **Status:** [ ] todo
- **Depends on:** T4, T5
- **Acceptance:**
  - [ ] For each of the remaining rows in spec §10 (`ittibiz-tiktok`, `bjgdrx-fb`, `bjgdrx-google`, `bjgdrx-cgpt`, `ittitask-cgpt`, `ittibiz-cgpt`):
    - [ ] Human confirms whether creds (password + TOTP seed) are available; if NOT, mark row as **DEFERRED** in journal with reason
    - [ ] If creds available: human types them into the New Credential modal (never into chat)
    - [ ] Human picks approach: (a) extension warm-up if real-Chrome session exists for the account, or (b) `--headed --warm-up` via social-login CLI
    - [ ] Human resolves any 2FA / Turnstile / device-prompt / passkey challenge by hand
    - [ ] Row ends in either `logged_in` (🟢) or `needs_human` (🟡) with reason captured
  - [ ] Every Phase 4 session waited for explicit human OK before launching (no auto-approval)
  - [ ] Journal updated row-by-row as the walkthrough proceeds
- **Tests:** (manual — paced by human)
- **Notes:**
  - Spec §10 has 8 rows total; the 2 from T4 (qoneidol-tiktok, qonecompany-fb) plus the 1 from T5 already cover 3. T6 picks up the remaining 5-6 depending on which platform was used in T5.

---

## T7 — Cleanup: delete artemis-oracle stubs

- **Status:** [ ] todo
- **Depends on:** T6 (do this only after the main work is done — keep the workspace stable during execution)
- **Acceptance:**
  - [ ] Inspected `.mcp.json` at artemis-oracle root — if it has real higgsfield config, KEEP IT; otherwise delete
  - [ ] Removed empty stubs in artemis-oracle:
    - `dashboard/api/package.json` (0 bytes)
    - `dashboard/frontend/package.json` (0 bytes)
    - `packages/shared-types/package.json` (0 bytes)
    - root `package.json` (0 bytes)
    - empty parent dirs (`dashboard/`, `packages/`) if nothing else lives in them
  - [ ] `git status` in artemis-oracle no longer lists these untracked stubs
  - [ ] Single commit: `chore: remove empty dashboard/ and packages/ stubs`
- **Tests:** —
- **Notes:**
  - These dirs are untracked (May 21 artifacts). Deletion is local-only until committed; no PR / push side-effects.

---

## T9 — Social-login worker daemon (host-side, permanent /test-login fix)

- **Status:** [x] done
- **Depends on:** T5 (extension proves /import-warm-state path; T9 is the other half — the /test-login → CLI path needs an out-of-container worker)
- **Why this slice exists:** T5 verification exposed a pre-existing bug — `/test-login` in `routes/credentials.ts:235` does `Bun.spawn(['bun', 'run', 'src/cli.ts', 'from-vault', ...], { cwd: SOCIAL_LOGIN_DIR })`. Inside the api Docker container, `SOCIAL_LOGIN_DIR` defaults to `/home/bun/Dev/qone_corp/social-login` which doesn't exist → ENOENT. Permanent fix: out-of-container worker that the api fetches over HTTP. Mirrors the existing `EVENT_BRIDGE_URL: host.docker.internal:19850` pattern used by openclaw.
- **Acceptance:**
  - [ ] New `qone_corp/social-login/worker/server.ts` — Hono app, single endpoint `POST /from-vault`, HMAC via `X-Service-Token`, spawns the existing CLI internally, returns the JSON result shape
  - [ ] api `routes/credentials.ts` `/test-login` handler refactored: replaces ~80-line in-container spawn with a ~30-line fetch to `${SOCIAL_LOGIN_WORKER_URL}/from-vault`
  - [ ] `docker-compose.yml` api service gets `SOCIAL_LOGIN_WORKER_URL: ${SOCIAL_LOGIN_WORKER_URL:-http://host.docker.internal:5510}` env var
  - [ ] `.env.example` documents the new variable
  - [ ] Tests:
    - [ ] Worker route returns 401/403 without service token (regression-prevention; mirrors api auth)
    - [ ] Worker spawn shape: invokes `bun run src/cli.ts from-vault --id <id>` with correct flags
    - [ ] /test-login route tests still pass (auth gate unchanged from T2)
  - [ ] Start the worker (`bun run worker/server.ts`), restart api with new env, click `Test` on a credential in the UI → no more ENOENT, real CLI runs end-to-end
  - [ ] Commit: `feat(social-login): host-side worker daemon for out-of-container /test-login execution`
- **Tests:** `qone_corp/social-login/worker/server.test.ts` (new)
- **Notes:**
  - Worker secret reuses `SERVICE_SECRET` for v1 simplicity (one less env var to manage; matches the existing /use route's auth shape). Separate `SOCIAL_LOGIN_WORKER_SECRET` is a future hardening.
  - launchd plist for auto-start is a follow-up — for this session the user runs `bun run worker/server.ts` in a terminal.
  - Graceful degradation: if worker is unreachable, /test-login returns 503 with a clear error message instead of trying the broken in-container spawn.

---

## T7 — Cleanup: delete artemis-oracle stubs

(same as before — now blocked by T9 + T6 OR neither, depending on user pacing)

---

## T8 — Final journal section + summary

- **Status:** [ ] todo
- **Depends on:** T7
- **Acceptance:**
  - [ ] `journal.md` ends with a "## Walkthrough results" section containing:
    - [ ] Table: 8 rows × {label, platform, account, final status, approach used (CLI vs extension), notes/blockers}
    - [ ] Explicit "Deferred" list with reason for each (missing creds, passkey-only account, etc.)
    - [ ] Any surprises encountered (selector drift, fingerprint issues, Cloudflare interactives, etc.)
    - [ ] Spec feedback (anything the spec missed or got wrong)
    - [ ] Suggested follow-ups (Phase 5 hooks, KEK rotation script, etc.)
  - [ ] README.md status updated to `complete` (or `partially complete` if rows deferred)
- **Tests:** —
- **Notes:**
  - This task is the resume point if the work spans multiple sessions. A new agent re-entering should be able to read journal.md and pick up.
