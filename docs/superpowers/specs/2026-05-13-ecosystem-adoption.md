# Ecosystem Adoption Plan — agent-browser-mcp, mission-control, hermes-web-ui

**Date:** 2026-05-13
**Status:** Draft. Pairs with [AI Inspire Pipeline Integration spec](2026-05-13-ai-inspire-pipeline-integration.md).
**Source:** Hermes Atlas catalog (`/Users/fiez/Dev/hermes-ecosystem`), local clones at `/Users/fiez/Dev/_research/`.

Scope per the user's pick: adopt items **1, 2, and 4** from the earlier research note.

- **#1**: `335234131/agent-browser-mcp` (167★, Plugins & Extensions)
- **#2**: `builderz-labs/mission-control` (3,875★, Multi-Agent & Orchestration)
- **#4**: dashboard choice between `EKKOLearnAI/hermes-web-ui` (1,844★), `nesquena/hermes-webui` (2,479★), and `fathah/hermes-desktop` (65★)

---

## 1. `agent-browser-mcp` — replace our cloakbrowser stack

### What it does
A 3-layer MCP server that lets any MCP-capable agent (Hermes, Claude Desktop, Cursor) drive **the user's already-running Chrome** — keeping login state, cookies, open tabs, and real page context:

```
┌─ user's real Chrome ───────────────────────────────────────┐
│  Chrome extension                                          │
│     ↓ (Chrome APIs: tabs, cookies, debugger, management)   │
└────┬───────────────────────────────────────────────────────┘
     ↓ ws/http
┌─ TMWebDriver (local bridge) — 127.0.0.1:18765 + 18766 ─────┐
│  routes messages between extension and MCP server          │
└────┬───────────────────────────────────────────────────────┘
     ↓ MCP
┌─ MCP server (Python) ──────────────────────────────────────┐
│  Exposes: tabs(), navigate(), scan(), exec_js(),           │
│           cdp(cmd|batch), screenshot_page/desktop(),        │
│           cookies(), mouse, keyboard, hotkey                │
└─────────────────────────────────────────────────────────────┘
```

Key features:
- Real Chrome tab discovery + switching
- Page scan & simplified content extraction (HTML/text)
- Inline `evaluate` JS execution
- Raw CDP single & batch commands
- Page screenshot (CDP) + desktop screenshot
- HttpOnly-cookie read
- Physical mouse move/click/drag + keyboard typing/hotkeys

### How it overlaps with this session's work
| Today (built this session) | With agent-browser-mcp |
|---|---|
| `social-login/src/facebook.ts:postFacebookFromVault` (~250 LOC playwright/cloakbrowser script) | One MCP tool call from pulse's prompt |
| `scripts/import-from-cdp.mjs` (Playwright connectOverCDP) | Built in — `cookies()` MCP tool |
| `dashboard/chrome-extension/` (our own) | Their extension already does this |
| Per-platform anti-bot fights (TikTok/OpenAI/Google) | Real Chrome with real fingerprint and real session |
| `loginFacebookFromVault`/`loginGoogleFromVault`/`loginOpenAIWebFromVault` | Operator just signs in to each site once in their normal Chrome; MCP reads cookies from that session |

### Recommended workflow to adopt
1. **Install agent-browser-mcp + its Chrome extension** in the user's actual Chrome (the one logged into FB/TikTok/Google/OpenAI). README on the local clone at `_research/agent-browser-mcp/README.md`.
2. **Add MCP server entry to `~/.hermes/config.yaml`** so every Hermes agent can call it:
   ```yaml
   mcp_servers:
     agent_browser:
       command: agent-browser-mcp
       args: []
   ```
3. **Rewrite `pulse-post-facebook` procedure in `agents-v2/pulse/AGENTS.md`**:
   - Before: bun shell → `social-login post-facebook --id <uuid>` → cloakbrowser/CDP
   - After: MCP `agent_browser.navigate("https://www.facebook.com/<page>")`, `exec_js(...)` to type caption, MCP click via real mouse, screenshot, return result.
4. **Deprecate** `social-login/src/{facebook,tiktok,google,openai_web}.ts:postXxxFromVault` and `scripts/import-from-cdp.mjs` after the MCP path is working.
5. **Keep** the credential vault (`/credentials` endpoint, dashboard UI) — still useful for tracking which accounts exist + last-known status, but cookies/session-state now live in the actual Chrome profile (agent-browser-mcp reads them on demand).

### Non-goals
- We do NOT replace the workflow engine, fan-out, gates, all-reject loop, or process versioning. agent-browser-mcp only replaces the "drive a browser" layer of `social-login`.

### Risks
- Single point of failure: if the user's real Chrome dies, all agents can't post. (Acceptable for a single-tenant dev box; not for production multi-tenant.)
- MCP setup adds a `chrome-extension` + a bridge process the user has to launch. Slightly more moving parts than a self-contained cloakbrowser script.

---

## 2. `mission-control` — peer to qone_corp

### What it is
3,875-star self-hosted dashboard for **the same problem space as qone_corp**. Built on Next.js 16 + TypeScript 5.7 + better-sqlite3 (SQLite, no Postgres/Redis/Docker needed). 577 tests (282 unit + 295 E2E). MIT licensed.

### Feature comparison

| Capability | qone_corp (us) | mission-control | Notes |
|---|---|---|---|
| Tasks + agents + comments + activities | ✅ | ✅ | Both have the core. |
| Workflows (multi-step DAG) | ✅ (workflow_nodes engine) | ✅ ("pipelines") | We have richer fan-out + jsonpath. |
| **Process versioning** | ✅ (this session #6-#9) | ❌ | Our differentiator. |
| **All-reject feedback loop** | ✅ (#10-#11) | Partial ("Aegis review system" blocks task completion) | Their gate is simpler — single sign-off, no draft-new-prompt. |
| Human gates / approval | ✅ (#12-#13 Telegram inline) | ✅ ("Aegis") | They do role-based (viewer/operator/admin). We don't. |
| **Token cost tracking** | ❌ | ✅ | Their feature, we lack. |
| **Skills Hub** (browse/install/security-scan from registries) | ❌ | ✅ (ClawdHub + skills.sh, disk ↔ DB sync) | Their feature. |
| **Multi-gateway** (multiple agent runtimes simultaneously) | ❌ (one hermes gateway) | ✅ (OpenClaw, CrewAI, LangGraph, AutoGen, Claude SDK) | Their feature; we'd need adapters. |
| **MCP audit log** | ❌ | ✅ | Their feature. |
| Recurring tasks / cron | ✅ (workflow_schedules) | ✅ (natural language: "every morning at 9am") | Theirs has nicer UX. |
| Real-time updates | SSE keepalive (this session) | WebSocket + SSE with smart polling pause | Theirs is more mature. |
| Auth | X-Agent-ID + X-Service-Token | Session + API key + Google Sign-In + role-based | Theirs is production-grade; ours is dev-grade. |
| DB | Postgres (Docker) | SQLite (single file) | Their footprint is smaller; ours scales further. |
| Memory graph | ❌ | ✅ | Their feature. |
| Credential vault | ✅ (this session + cred-vault session) | ❌ (no dedicated vault) | **Our differentiator.** |
| **AI Inspire-style content pipeline** (per-topic gate + 2hr Bangkok scheduler) | ✅ (#14, #16) | ❌ | **Our differentiator.** |

### Strategic decision needed
Three honest options:

**A. Stay independent (recommended for now).** We keep building qone_corp. Treat mission-control as a reference design — mine their schema for the features we lack (token tracking, skills hub, MCP audit), reimplement the ones that matter.

**B. Migrate to mission-control + bolt our differentiators on top.** Port process_versioning, all-reject, AI Inspire workflow, credential vault, fan-out engine onto mission-control's foundation. Gain their multi-gateway + token tracking + auth + tests. Lose our Postgres-based migration history + a month's worth of qone-specific schema.

**C. Hybrid — adopt their adapter layer only.** Their `src/lib/adapters/`, `framework-templates.ts`, `hermes-tasks.ts`, `hermes-memory.ts`, `hermes-sessions.ts` are the multi-gateway abstraction. If we lift JUST that into qone_corp, we gain the ability to run CrewAI / LangGraph / AutoGen agents alongside hermes. Everything else stays ours.

### Recommended workflow
1. **Run mission-control locally once** to see its UX:
   ```bash
   cd /Users/fiez/Dev/_research/mission-control
   bash install.sh --local      # or: docker compose up
   open http://localhost:3000/setup
   ```
2. **Read their `src/lib/schema.sql`** alongside our `dashboard/api/migrations/0001-0038`. Document the diff. (~30 min.)
3. **Decide A/B/C above.** Default: **A (independent) + steal features from C** — port `hermes-tasks.ts` / `hermes-memory.ts` / `framework-templates.ts` into `qone_corp/dashboard/api/src/services/` so we can later add non-hermes gateways. ~1-2 days work; reversible.
4. **Track features they have that we want** in a "qone-roadmap" doc: token tracking, MCP audit log, role-based auth, natural-language cron.
5. **DON'T** copy code wholesale — their codebase is Next.js 16 SQLite; ours is Bun/Hono/Drizzle/Postgres. Read for ideas, write our version.

### Non-goals
- We do NOT replace qone_corp with mission-control. The process versioning + all-reject + AI Inspire pipeline we built this session is non-trivial to migrate, and mission-control doesn't have equivalents.

---

## 4. Dashboard choice — run alongside or copy features?

### Three contenders compared

| | qone_corp dashboard (us) | EKKOLearnAI/hermes-web-ui | nesquena/hermes-webui | fathah/hermes-desktop |
|---|---|---|---|---|
| **Stars** | (private) | 1,844 | 2,479 | 65 |
| **Stack** | Next.js + Bun/Hono + Postgres | TypeScript Node + Socket.io | **Python + vanilla JS** (no build) | Electron + better-sqlite3 |
| **Install** | `docker compose up` | `npm install -g hermes-web-ui` | `./start.sh` / Docker | Download `.dmg` / `.exe` / `.AppImage` |
| **Focus** | Workflow + task + process + credential orchestration | Chat sessions + channel config + analytics | 1:1 web parity with Hermes CLI | Desktop UX + Hermes installer |
| **Chat UI (per-session)** | ❌ | ✅ SSE streaming, multi-session, search | ✅ three-panel, workspace browser | ✅ |
| **Channel config (8 platforms)** | ❌ | ✅ Telegram/Discord/Slack/WhatsApp/Matrix/Feishu/WeChat/WeCom | (less detail) | (less) |
| **Token analytics + 30-day trends** | ❌ | ✅ | (less detail) | ? |
| **Model/provider mgmt + OAuth (Codex, Nous Portal)** | ❌ | ✅ | profile support | ? |
| **Multi-profile / multi-gateway** | ❌ | ✅ clone/import/export | profile support | ? |
| **File browser (local/Docker/SSH/Singularity)** | ❌ | ✅ | ✅ workspace panel | ? |
| **Group chat (multi-agent @mention)** | ❌ | ✅ Socket.io | ? | ? |
| **Web terminal (node-pty / xterm)** | ❌ | ✅ | ? | ? |
| **Scheduled cron UI** | partial (workflow_schedules row exists but no editor) | ✅ with presets | ? | ✅ |
| **Workflow engine + process versioning** | ✅ | ❌ | ❌ | ❌ |
| **All-reject loop + Telegram inline gates** | ✅ | ❌ | ❌ | ❌ |
| **Credential vault + encrypted warm sessions** | ✅ | ❌ | ❌ | ❌ |
| **AI Inspire-style pipeline** | ✅ | ❌ | ❌ | ❌ |
| **Mobile-first** | partial | partial | partial | desktop-only |
| **MCP server built-in** | ❌ | ❌ | ✅ `mcp_server.py` | ❌ |

### Decision: run EKKOLearnAI/hermes-web-ui alongside qone_corp + cherry-pick UI patterns

**Why not replace qone_corp:**
- None of the three offer the workflow engine, process versioning, all-reject loop, or AI Inspire pipeline. Replacing would lose this session's core work.

**Why not just copy features into qone_corp:**
- EKKOLearnAI's web-ui has 8-platform channel config and SSE-streamed chat. Reimplementing these from scratch is weeks. They're already-built, mature, MIT-licensed.

**Why EKKOLearnAI over nesquena:**
- EKKOLearnAI has the wider feature set (channel config, analytics, group chat, model mgmt).
- nesquena is more minimalist (Python + vanilla JS, no build). Great for SSH-tunnel access but lighter on features.
- fathah is a desktop installer wrapper — wrong shape for our "run-alongside web dashboard" goal.

**Why not fathah:**
- Desktop installer is the wrong abstraction for our case. We already have a web dashboard. We don't need an Electron app to install hermes (we install it once on the server).

### Recommended workflow
1. **Install EKKOLearnAI/hermes-web-ui** as a separate service on this Mac:
   ```bash
   npm install -g hermes-web-ui
   hermes-web-ui start --port 3838   # or any free port
   ```
   It reads `~/.hermes/` directly — no DB schema changes, no migration. Auto-detects models from `~/.hermes/auth.json`.

2. **Reverse-proxy under qone-frontend** so it's at `http://localhost:5500/chat`:
   - Add to `dashboard/frontend/next.config.js` rewrites:
     ```js
     { source: '/chat/:path*', destination: 'http://localhost:3838/:path*' }
     ```
   - Add a "Chat" link in the nav rail of qone-frontend so the user toggles between qone's workflow UI and EKKOLearnAI's chat UI.

3. **Keep qone_corp's dashboard as the workflow-and-orchestration UI.** No code duplication; the two tools serve different purposes:
   - `localhost:5500/` (qone) — workflows, processes, tasks, credentials, gates, blockers, runs
   - `localhost:5500/chat` (proxied to EKKOLearnAI) — chat with agents, channel config, analytics, cron, profiles

4. **Cherry-pick TWO features into qone_corp** that don't duplicate EKKOLearnAI's strengths:
   - **Cron scheduler UI** — EKKOLearnAI's cron editor is generic. Ours needs workflow-aware scheduling (with `workflow_id` reference, Bangkok-timezone presets, etc). Build a small `/workflows/:id/schedule` page using their cron-presets pattern as inspiration.
   - **Token cost tracking** — useful as a workflow-run cost summary, not just per-session. Adopt EKKOLearnAI's "tokens by model" chart pattern, scope it per-workflow-run.

### Non-goals
- Don't run all three. Pick one (EKKOLearnAI) and stop there.
- Don't try to feature-merge their codebase into ours. They're MIT, we can keep their npm package as a black-box dependency reverse-proxied alongside.

### Risks
- EKKOLearnAI writes config to `~/.hermes/.env` and `~/.hermes/config.yaml`. If both qone_corp and EKKOLearnAI try to write the same files, we get conflicts. Mitigation: pick one as "owner" of those files. Our convention says hermes config is shared per-agent under `~/.hermes-agents/<agent>/`, so EKKOLearnAI's writes to shared `~/.hermes/` should be safe.
- Port conflicts if 3838 is in use. Mitigation: configurable.

---

## Roll-up plan: order of operations

| # | Action | Effort | Output |
|---|---|---|---|
| 1 | Install agent-browser-mcp + extension in real Chrome | 30 min | MCP available; verify by calling `tabs()` from Hermes CLI |
| 2 | Wire agent_browser MCP into `~/.hermes/config.yaml` for nova + pulse | 15 min | Both agents can call MCP tools |
| 3 | Re-write `pulse-post-facebook` AGENTS.md to use MCP instead of social-login CLI | 1 hr | Pulse posts via real Chrome session |
| 4 | Verify AI Inspire daily workflow end-to-end with MCP-driven posting | 1 hr | One FB post lands on AI Inspire page |
| 5 | After validation: deprecate `social-login/src/*FromVault` post functions, leave login probes intact | 30 min | Smaller codebase |
| 6 | `bash install.sh --local` mission-control; read their schema diff vs ours | 2 hr | "qone-roadmap" doc with features-to-port |
| 7 | Port `hermes-tasks.ts` / `hermes-memory.ts` / `framework-templates.ts` adapter pattern into qone_corp | 1-2 days | Multi-gateway support (future-proof) |
| 8 | `npm install -g hermes-web-ui && hermes-web-ui start --port 3838`; add reverse-proxy in qone-frontend | 1 hr | Unified dashboard at localhost:5500 |
| 9 | Build `/workflows/:id/schedule` page in qone-frontend using EKKOLearnAI's cron-preset patterns | 4 hr | Operator can edit cron from UI |
| 10 | Build per-workflow-run token-cost summary in qone-frontend using EKKOLearnAI's analytics patterns | 4 hr | Cost visibility |

Total ≈ 3-4 days of work to fully realize this plan; first 5 items (~3hr) deliver immediate value.

## Cross-references

- Previous session integration spec: [2026-05-13-ai-inspire-pipeline-integration.md](./2026-05-13-ai-inspire-pipeline-integration.md)
- Cred-vault design: [2026-05-10-qone-credential-vault-design.md](./2026-05-10-qone-credential-vault-design.md)
- Local clones: `/Users/fiez/Dev/_research/` (shallow, MIT/Apache licensed)
- Catalog source: `/Users/fiez/Dev/hermes-ecosystem` (cloned from `ksimback/hermes-ecosystem`)

## Open questions for the operator

1. Which of A/B/C for mission-control? Default = A.
2. Are you OK with operator-driven Chrome being the production browser-automation surface, or do we eventually want a server-side headless option? (Affects whether to drop social-login's post functions entirely or keep them as fallback.)
3. Should EKKOLearnAI's hermes-web-ui be reverse-proxied UNDER our dashboard (one URL, one nav), or live on its own port and the user opens both? Default = reverse-proxy.
