# Architecture — qone-credential-vault-fix

**Chosen approach:** **Clean** — exported `ADMIN_AGENTS` constant + `isAdminAgent(c)` predicate + `requireAdminOrService(c)` shared guard. Each of the 5 mutation routes calls the guard once.

**Why:** Single source of truth eliminates drift risk across 5 routes. Mirrors the existing `AUTH_COOKIE_CANDIDATES` shared-export pattern that commit `c21322b` validated (export + test-protect against future drift). Same LoC as the inline-repeated alternative once you count repetition, but with one place to evolve when the admin list changes.

---

## Key decisions

### D1 — File location: extend `middleware/auth.ts`
- Live next to `hasServiceToken`. Don't carve out `middleware/admin-agents.ts`.
- **Why:** the existing `AUTH_COOKIE_CANDIDATES` precedent is a same-file export, not a separate module. The "extract a validator" pattern in this repo is "named export consumed by tests", not "separate file". Picking a new file would invent a convention the codebase doesn't have.

### D2 — Admin definition: hardcoded `ADMIN_AGENTS = ['artemis'] as const`
- Exported from `middleware/auth.ts`.
- **NOT** env-var driven (rejected) — adds operational surface area with no current need; YAGNI per the user's constraint "no inventing new auth shapes".
- **NOT** a role attribute on `VALID_AGENTS` — `VALID_AGENTS` is a flat `string[]`. Adding role-based filtering means a wider schema-shape change for one new use case. Defer until ≥2 callers need it.
- Initially `['artemis']`. Future expansions (e.g. `['artemis', 'admin']`) are a single-line edit.

### D3 — Helper shape: predicate + guard
- `isAdminAgent(c): boolean` — pure predicate, useful for tests + non-403 branches.
- `requireAdminOrService(c): Response | null` — returns `null` if either credential check passes, otherwise returns the 403 response. Caller usage:
  ```ts
  const denied = requireAdminOrService(c);
  if (denied) return denied;
  // actual handler
  ```
- **Why split:** the predicate is unit-testable in isolation; the guard centralizes the error shape (`{ error: 'admin agent or service token required' }`) so all 5 routes return identical 403 bodies.

### D4 — Application sites: all 5 mutation routes in `routes/credentials.ts`
- `POST /` (line 35-45)
- `DELETE /:id` (line 47-51)
- `PATCH /:id` (line 56-73)
- `POST /:id/import-warm-state` (line 99-181)
- `POST /:id/test-login` (line 202-282) — *previously unguarded; closing a pre-existing gap*

`/use` (line 76-86) and `/status` (line 183-189) remain `hasServiceToken`-only. Those are runner-internal paths; admin agents must not bypass the service-token requirement for them.

### D5 — Test surface: unit + integration
- **Unit** (`tests/unit/middleware/auth.test.ts` — new or extending existing): `isAdminAgent` returns true for `'artemis'`, false for other valid agents, false for unset agentId. `requireAdminOrService` returns `null` for both valid-paths, returns 403 for neither.
- **Integration** (`tests/unit/routes/credentials-auth.test.ts` — new): one happy-path test per mutation route with `X-Agent-ID: artemis`, one happy-path with `X-Service-Token`, one denied-path with neither. 5 routes × 3 cases = 15 integration tests. Plus 2 preservation tests on `/use`: artemis-only → 403, service-token-only → 200.
- **Drift protection test** (mirrors `c21322b`'s pattern): an explicit test asserting `ADMIN_AGENTS.includes('artemis')` so the constant can't silently drop the admin we depend on.

## Alternatives considered

- **Approach 1 — Minimal (inline checks repeated 5 times):** rejected. Same LoC; introduces drift risk across 5 identical blocks.
- **Env-var driven admin list (`QONE_ADMIN_AGENTS`):** rejected. Adds env-var management surface area with no current need.
- **Role attribute on `VALID_AGENTS`:** rejected. Wider schema-shape change than the regression deserves.
- **New file `middleware/admin-agents.ts`:** rejected. Inconsistent with the codebase's existing same-file-export pattern.

## Constraints inherited from exploration

- Must use `OpenAPIHono` route declarations — no plain Hono routers (would silently break `/openapi.json` codegen).
- Must reuse the existing `c.get('agentId')` accessor populated by the global `agentAuth` middleware (`api/src/index.ts:82`). Don't add a parallel agent-id resolution path.
- Must keep `hasServiceToken` unchanged. The hybrid guard composes existing behavior; it doesn't replace it.
- Existing tests use `bun:test` — match that style. Use the `dashboard/api/tests/helpers/test-db.ts` helpers if the test needs a DB row.

## Open questions / risks

- **Q1: Does `VALID_AGENTS` admit a `runner` value?** If yes, runner could technically pass `X-Agent-ID: runner` without a service token and bypass the service-token-only routes. T1 will verify the membership list during reproduction. Mitigation: `ADMIN_AGENTS` excludes `runner` (it's not in `['artemis']`), so `/use` and `/status` stay protected.
- **Q2: 403 error-body shape.** Current shape on `hasServiceToken`-only routes is `{ error: 'service token required' }`. The hybrid guard's new message will be `{ error: 'admin agent or service token required' }`. Any frontend code that pattern-matches the old string would break. The dashboard frontend's api-client treats 403 generically (per the audit), so this is safe.
- **Q3: PATCH route's existing extra guard.** `PATCH /:id` (line 56-73) has a payload.kind match check at line 67-68. The hybrid guard runs first; the kind-check still runs after a successful auth. No interaction risk.

## Implementation plan reminder

The order T2 should follow (TDD):

1. Write failing unit tests for `isAdminAgent` + `requireAdminOrService` in `tests/unit/middleware/auth.test.ts`.
2. Write failing integration tests for the 5 routes in `tests/unit/routes/credentials-auth.test.ts`.
3. Run tests, confirm red.
4. Implement `ADMIN_AGENTS`, `isAdminAgent`, `requireAdminOrService` in `middleware/auth.ts`.
5. Replace `hasServiceToken`-only guard in the 5 mutation routes with `requireAdminOrService`.
6. Run tests, confirm green.
7. Commit: `fix(api): allow X-Agent-ID admin OR X-Service-Token on credential mutations (incl. test-login)`
8. Run the existing dashboard/api test suite, confirm no regressions.
