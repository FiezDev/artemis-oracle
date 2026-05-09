📡 Session: 0ebcba9d | artemis-oracle | ~24h

# Handoff: AI Search Daily Pipeline — ready to exercise end-to-end

**Date**: 2026-04-23 00:54
**Context**: ~92% used (pre-compaction)
**Focus next session**: First real run of the "AI Search Daily — Producer" workflow against `https://www.youtube.com/@theAIsearch`, driving all the new pieces (Z.ai MCP fact-check, TH+EN polishing, Gate review UI with TH/EN tabs). Then a real Publisher tick posting to the AI Inspired Facebook Page.

## What We Did This Session (chunked)

### Chunk 1 — Universal Gate Review UI (migration 0008)
- `review_items` table (universal kind: text/image/video/doc/table/json) + one-time backfill of the old `topic_drafts` rows.
- 6 pluggable frontend renderers in `components/review/` (Text/Image/Video/Doc/Table/Json).
- Gate review page at `/gates/[gateId]/runs/[runId]/review` — select/edit/approve/reject per item, sticky submit bar.
- API: POST/GET/PATCH/bulk-review + atomic `dequeue-for-publish`.

### Chunk 2 — Workflow/Process authoring UI
- Deleted 22 test workflows (JSON backup first). Deprecated 22 orphan processes (legacy migration 0006 backfill).
- Workflow + node CRUD routes (POST/PATCH/DELETE /workflows/:id/nodes + atomic PUT).
- Workflows list renders inline node sequence; each card has Edit link.
- Processes list now shows description + prompt excerpt + schema field counts + pointer to `agents-v2/<agent>/AGENTS.md`.
- New pages: `/processes/new`, `/processes/[id]/edit`, `/workflows/new`, `/workflows/[id]/edit`.
- Drag-and-drop node editor via `@dnd-kit/sortable`.

### Chunk 3 — AI Search Daily pipeline rebuild
Replaced the old YouTube Summarize workflow with producer/publisher split:
- **Producer** (`0 9 * * * Asia/Bangkok`): channel-watch → topic-summary → factcheck-expand → translate-polish ×5 → Gate.
- **Publisher** (`0 18 * * *` EN + `0 20 * * *` TH Asia/Bangkok): dequeue → nanobanana-pro image → pulse-post-facebook --page-id 61563629127518 (AI Inspired).
- 4 new processes: `nova-youtube-channel-watch`, `nova-factcheck-expand`, `nova-translate-polish`, `pulse-dequeue-approved-topic`. Full how-tos in Nova/Pulse AGENTS.md.
- TH/EN tabs in `TextReviewItem` (detects `{en, th}` content shape).

### Chunk 4 — Facebook direct post (no n8n)
- `scripts/facebook-post.py` + vault-backed creds + headed agent-browser with persistent profile at `~/.agent-browser/fb-profile`.
- Detects reCAPTCHA / 2FA / checkpoints; auto-dismisses WhatsApp upsell modals after post.
- `--page-id` support: first real post landed on AI Inspired via the page-mode composer (5 self-test posts now live).

### Chunk 5 — Z.ai MCP wiring
All 4 Z.ai MCP servers installed at clother-zai user scope via `scripts/install-zai-mcp.sh`: `zai-web-search`, `zai-web-reader`, `zai-zread`, `zai-vision` — all ✓ Connected. Key sourced from `~/.openclaw/agents/main/agent/auth-profiles.json`.

### Chunk 6 — Memory + wiki
- `/df-residian` retro filed: `ψ/memory/retrospectives/2026-04/23/00.41_ai-search-pipeline-plus-zai-mcp.md`
- Wiki: new source + 4 concepts (`producer-publisher-workflow-split`, `recaptcha-html-false-positive`, `cdp-trusted-click-vs-synthetic`, `z-ai-mcp-servers`), qone-corp entity updated.
- `/df-obsidian lint` run: added `created:` to 25 sources, refreshed stale `overview.md`, logged. 0 orphans, 0 contradictions, 4 minor missing-link stubs left for human.
- 5 learnings synced to Oracle via `arra_learn`.

## Pending

- [ ] `SCHEDULER_ENABLED=true` — currently `false`; the cron triggers won't fire until flipped.
- [ ] First end-to-end Producer run against @theAIsearch — manual trigger, watch Nova's fact-check actually call the Z.ai MCP search + reader.
- [ ] First Publisher run with a real approved item: atomic dequeue → image-gen → post to AI Inspired Page.
- [ ] Wire `reel-image-nanobanana-pro` to actually invoke the NanoBanana MCP (declarative only today).
- [ ] Commit the ~16 uncommitted files across dashboard/ + agents-v2/ (split by logical chunk).
- [ ] Clean up 5 `Script self-test #N` posts on AI Inspired page.
- [ ] 4 missing wiki stub pages surfaced by lint — optional: `arra-oracle`, `ollama`, `oracle-family`, `prompt-engineering`.

## Next Session

- [ ] Flip `SCHEDULER_ENABLED=true` on the qone-api container, restart, verify the poller logs picking up the 3 schedules.
- [ ] Manually trigger Producer via `POST /api/v1/workflows/c6d30c3a-.../run-v2` to kick off a one-shot run. Confirm channel-watch finds a new video (or gracefully returns empty).
- [ ] Watch Nova's OpenClaw session pick up the task, invoke `web_search_prime` + `webReader` during factcheck-expand. Verify `(UNVERIFIED)` tagging on unresolvable claims.
- [ ] Load the Gate Review UI for the new run, check TH+EN tabs render for all 5 variants, do a selection + edit + approve roundtrip.
- [ ] Manually trigger Publisher via `/run-v2`, observe the dequeue pick the approved item atomically, confirm nanobanana image gen + pulse-post-facebook post lands on AI Inspired.
- [ ] If anything breaks → patch, retry, document with a retro. The failure modes worth watching: Nova rate-limited by Z.ai quota, reCAPTCHA reappearing on the Facebook profile, dequeue race under concurrent 18:00/20:00 triggers.

## Key Files

### Code (uncommitted)
- `qone_corp/dashboard/api/src/services/review-item-service.ts` — dequeue-for-publish SQL
- `qone_corp/dashboard/api/src/routes/review-items.ts` — dequeue endpoint
- `qone_corp/dashboard/api/scripts/seed-ai-search-workflows.ts` — run if you need to re-seed
- `qone_corp/dashboard/api/scripts/yt-workflow-cleanup.ts` — cleanup script (reusable pattern)
- `qone_corp/dashboard/frontend/components/review/text-review-item.tsx` — TH/EN tabs
- `qone_corp/dashboard/frontend/components/workflow-node-editor.tsx` — dnd-kit editor
- `qone_corp/dashboard/frontend/components/workflow-form.tsx` + `process-form.tsx`
- `qone_corp/dashboard/frontend/app/{workflows,processes}/{new,[id]/edit}/page.tsx`
- `qone_corp/agents-v2/{nova,pulse}/AGENTS.md` + `TOOLS.md` — new how-tos

### Scripts (uncommitted)
- `artemis-oracle/scripts/facebook-post.py` — agent-browser FB poster with --page-id
- `artemis-oracle/scripts/install-zai-mcp.sh` — 4 Z.ai MCP servers installer
- `artemis-oracle/scripts/auth-vault.py` — has new `import-chrome` subcommand

### State (not committed — lives in vault)
- `ψ/memory/retrospectives/2026-04/23/00.41_ai-search-pipeline-plus-zai-mcp.md`
- `/mnt/c/MyDoc/OPVAULT/FIEZ/wiki/sources/2026-04-23-ai-search-pipeline-plus-zai-mcp.md` + 4 concepts
- `gen-output/workflows-backup-2026-04-22.json` + `yt-workflow-backup-2026-04-23.json`

### DB IDs for next session
- Producer workflow: `c6d30c3a-ee3b-4ec0-82bf-80198e1ff1f0`
- Publisher workflow: `98f9e116-2cc9-44bd-97a8-3bd8396173bd`
- AI Search gate: `34f2923a-13b7-421c-9224-33c0a5082f56`
- AI Inspired FB page: `61563629127518`
