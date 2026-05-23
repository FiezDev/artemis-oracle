# qone-credential-vault-fix — df-deep-build doc pack

Bring the qone_corp credential vault back to working order: fix the auth-mutations regression introduced by commit `0df2577`, verify the QOne Vault Importer Chrome extension end-to-end, and walk through Phase 4 to get the spec §10 credential rows to 🟢 (graceful degradation for accounts without creds-on-hand).

- **Spec:** [spec.md](spec.md) (immutable)
- **Context:** [context.md](context.md) (append findings here)
- **Tasks:** [tasks.md](tasks.md) (status updated inline)
- **Journal:** [journal.md](journal.md) (decisions + bug-loop)
- **Architecture:** added by df-deep-build-plan after design

**Started:** 2026-05-23
**Closed:** 2026-05-23 (single-day session)
**Status:** core scope complete (T1–T5, T7, T8, T9 done); Phase 5 partial (T10 slices 1–3); T6, T10 slice 4, T11 deferred to next session
**Slug:** `qone-credential-vault-fix`
**Scope:** Full breakdown — 8 vertical slices (T1–T8)
**Owner:** Artemis (Fiez supervising)

## Quick links — source repos

| Repo | Path | Touched in |
|---|---|---|
| qone_corp dashboard (api) | `/Users/fiez/Dev/qone_corp/dashboard/api/` | T2, T3, T4 |
| qone_corp dashboard (frontend) | `/Users/fiez/Dev/qone_corp/dashboard/frontend/` | T3, T6 |
| qone_corp dashboard (chrome-extension) | `/Users/fiez/Dev/qone_corp/dashboard/chrome-extension/` | T5 |
| qone_corp social-login | `/Users/fiez/Dev/qone_corp/social-login/` | T4, T6 |
| artemis-oracle (cleanup only) | `/Users/fiez/Dev/artemis-oracle/` | T7 |

## Phase chain

1. ✅ df-deep-build-interview (recon, COSTAR mega-prompt approved)
2. ✅ df-deep-build-docs (you are here — doc pack written)
3. ⏭️ df-deep-build-plan (explore + architecture for the auth guard helper)
4. ⏭️ df-deep-build-execute (TDD per task, one slice at a time)
5. ⏭️ df-deep-build-review (parallel multi-agent review + manual QA gate)
6. ⏭️ df-deep-build-summarize
