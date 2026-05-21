# Shared Memory KB — Design Spec

**Date:** 2026-05-21
**Owner:** Fiez (Ittipol Vongapai)
**Status:** Draft → awaiting user approval
**Host project:** `/home/bjgdr/dev-personal/jira-fetch`
**Reference pattern:** `/home/bjgdr/dev-work/RG/riceguard-kb-api`

---

## 1. Purpose

A shared, semantic-search-capable memory store that lets multiple devs ingest
curated knowledge (from Jira issues and Artemis memory files) and recall it
inside Claude Code sessions via MCP. The store is intentionally narrow in
scope:

- Indexed content is restricted to **gothailand** and **mobileai** repos/orgs.
- Personal notes, credentials, and secrets are never ingested.
- The server is a dumb vector store. All curation, filtering, secret-scanning,
  and classification happen client-side in a `/kb` skill that each dev runs in
  their own Claude Code session.

The goal is *knowledge that benefits other devs*, not a dump of everything one
person has touched.

## 2. Non-goals

- Multi-tenant access control (single shared bearer key for everyone)
- Per-dev audit trail with strong identity (the column was deliberately
  dropped; `metadata.uploaded_by` may be set by the skill if a dev wants it)
- Server-side scope enforcement (the `scope` column is a free string;
  enforcement is the skill's job)
- Hard deletes (soft retract only — honours the Nothing-is-Deleted rule)
- A general-purpose RAG-as-a-service product (this is a single team's KB)

## 3. High-level shape

```
            ┌─────────────────── jira-fetch EC2 ───────────────────┐
                                                                   
  Claude    │  nginx                                               │
  Code  ───►│   ├── /health      → 200 (deploy/liveness probe)     │
  session   │   ├── /api/kb/*    → jirafetch-api (Hono, NEW routes)│
  + /kb     │   └── /mcp         → jirafetch-api (Hono + MCP SSE)  │
  skill     │                          │                           │
            │                          ├─► postgres.js → Postgres+pgvector
            │                          │                  (memory_chunk)
            │                          └─► fetch         → memory-embed.service
            │                                              (Python FastAPI :3897,
            │                                               mpnet 768-dim)
            └──────────────────────────────────────────────────────┘
```

Three pieces total:

1. **KB routes inside the existing `jirafetch-api` Hono process** — new
   `apps/api/src/routes/kb/` module exposing both REST and MCP at `/mcp`.
2. **`memory-embed.service`** — Python FastAPI sidecar, copy-adapted from
   `riceguard-kb-api/embed-service.py`. Same model
   (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, 768-dim).
3. **`/kb` skill in `artemis-oracle/skills/kb/`** — the curator + KM lifecycle
   tool that each dev runs in their Claude Code session.

No new repo. One new systemd unit (the embed sidecar). One nginx block
addition (proxy `/api/kb/*` and `/mcp`).

## 4. Architecture decision: Option C (bolt onto existing Hono API)

Three options were considered:

| | A — new `apps/memory-kb` subapp | B — standalone repo | **C — bolt onto existing Hono API** |
|---|---|---|---|
| New repo? | No | Yes | No |
| New framework? | Elysia next to Hono | Elysia | None — reuses Hono |
| New CI/CD? | No (extends GH Actions) | Yes | No (extends GH Actions) |
| Copies riceguard verbatim? | ~80% | ~100% | Re-implements in Hono |
| Coupling to jira-fetch | Light (sibling app) | None | Tight (same process) |

**Selected: C.** One process, one framework, one deploy unit (plus the Python
sidecar). The implementation cost of re-implementing riceguard's handlers in
Hono is small relative to the operational simplification of one fewer service.

## 5. Data model

Two tables in jira-fetch's existing Postgres. Migration in
`db/migrations/00NN_memory_chunk.sql`.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_chunk (
  id            BIGSERIAL PRIMARY KEY,
  source        TEXT NOT NULL,             -- free string set by skill: 'jira' | 'artemis_memory' | 'learning' | 'retrospective' | ...
  scope         TEXT NOT NULL,             -- free string set by skill: 'gothailand' | 'mobileai' | ...
  external_id   TEXT NOT NULL,             -- e.g. 'RIC-304#comment-42' or 'feedback_iso-doc-images-fail-fast.md'
  title         TEXT,
  body          TEXT NOT NULL,             -- already-redacted text that was embedded
  body_hash     TEXT NOT NULL,             -- sha256 of body — dedupe + idempotent re-ingest
  embedding     vector(768) NOT NULL,
  metadata      JSONB DEFAULT '{}',        -- freeform; skill puts classifier_confidence, tags, judge_reason, uploaded_by here
  created_at    TIMESTAMPTZ DEFAULT now(),
  revoked_at    TIMESTAMPTZ,
  UNIQUE (source, external_id, body_hash)
);

CREATE INDEX ON memory_chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON memory_chunk (scope, source) WHERE revoked_at IS NULL;
CREATE INDEX ON memory_chunk USING GIN (metadata);
```

Design notes:

- `scope` and `source` are free strings — no `CHECK` constraint. The dumb
  server does not know about gothailand/mobileai; that vocabulary lives in the
  skill's config.
- `body_hash` makes re-ingest idempotent. A cursor-based scan that runs the
  same file twice will upsert, not duplicate.
- `revoked_at` is set by `kb_retract`. Soft delete only. Searches filter to
  `revoked_at IS NULL`.
- `metadata` is the freeform escape hatch: classifier verdicts, tags, judge
  reasons, optional `uploaded_by` email, etc. Indexed via GIN for filtered
  search.

**No `memory_token` table.** Auth is a single shared bearer (see §7).

## 6. API surface

### 6.1 HTTP REST (fallback path)

Mounted on the existing Hono app. Any client with the bearer can hit these
directly — primarily for backfill scripts and non-Claude-Code clients.

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/health`             | Liveness (200 "ok"). No auth — for nginx/systemd. |
| `GET`    | `/api/kb/health`      | Detailed: db ok, embed sidecar ok, version. Bearer required. |
| `POST`   | `/api/kb/search`      | Body: `{query, scope?, source?, metadata_filter?, top_k?, min_similarity?}`. Embeds query, returns top-k cosine matches. |
| `POST`   | `/api/kb/ingest`      | Body: `{chunks: [{source, scope, external_id, title, body, metadata}]}`. Server embeds via sidecar, upserts on `(source, external_id, body_hash)`. **No content filtering.** |
| `GET`    | `/api/kb/chunks/:id`  | Single chunk for citation expansion. |
| `DELETE` | `/api/kb/chunks/:id`  | Body: `{reason?}`. Soft retract — sets `revoked_at`, stores reason in `metadata.retraction_reason`. |

### 6.2 MCP (preferred path)

Mounted at `/mcp` (HTTP+SSE, same bearer). Implemented with
`@modelcontextprotocol/sdk` inside the same Hono process. MCP handlers and
HTTP handlers share one service layer (`apps/api/src/services/kb.ts`) —
single source of truth, no drift.

| Tool | Wraps | Notes |
|---|---|---|
| `kb_health`  | `GET /api/kb/health` | + probes embed sidecar |
| `kb_search`  | `POST /api/kb/search` | returns title + body snippet + similarity + scope + source + external_id |
| `kb_get`     | `GET /api/kb/chunks/:id` | full body + metadata |
| `kb_ingest`  | `POST /api/kb/ingest` | write path — server has no filtering |
| `kb_retract` | `DELETE /api/kb/chunks/:id` | soft retract |

### 6.3 Trust model

The HTTP `/api/kb/ingest` endpoint will accept whatever a caller POSTs that
matches the schema. The filtering — heuristic gate, secret scan, LLM judge,
user approval — lives **only** in the `/kb` skill, which calls `kb_ingest`
via MCP.

> ⚠ Direct HTTP ingest from a script bypasses every gate. Use the skill
> unless you have a specific reason (e.g., a one-off bulk backfill where
> you've already done your own scanning). This is enforced by convention and
> documentation, not by code — the server cannot distinguish skill-mediated
> from direct calls.

## 7. Auth

**Single shared bearer key.**

- Env var on the server: `KB_API_KEY`. Generated once, distributed to devs
  out-of-band (Slack DM / 1Password / paper).
- Every request must carry `Authorization: Bearer $KB_API_KEY`. Server does a
  constant-time compare.
- Same key gates HTTP, MCP, read, and write. No scope split.
- Rotation = change env, restart `jirafetch-api`, push new key to devs.

No per-dev tokens, no token table, no issuance script. Trade-off accepted:
cannot revoke a single dev without rotating everyone; no per-user audit at
the DB level (devs may put `uploaded_by` in `metadata` if they want it).

## 8. Curator + KM skill: `/kb`

Lives at `artemis-oracle/skills/kb/`. Drives the entire knowledge-management
lifecycle from inside a Claude Code session. Calls MCP tools that the
session has already loaded — never raw HTTP.

### 8.1 Subcommands

| Subcommand | MCP tool(s) called | Logic in skill |
|---|---|---|
| `/kb scan [--since … --source … --scope … --dry-run]` | `kb_ingest` | full pipeline (see §8.3) |
| `/kb search <query> [--scope … --source … --top-k 5]` | `kb_search` | pretty-print results table |
| `/kb show <id>` | `kb_get` | pretty-print full chunk |
| `/kb retract <id> [--reason …]` | `kb_retract` | confirm prompt before call |
| `/kb status` | `kb_health` | + local cursor + token check |
| `/kb list [--mine --since … --source … --scope …]` | (none — local only) | summary from local `state.json` |
| `/kb config [--show \| --edit]` | (none) | edit per-dev config |

### 8.2 Per-dev state

```
~/.config/kb/
├── config.json    # allowlist, classifier model+threshold, secret patterns
├── state.json     # cursors per source, last-run summary
└── token          # bearer (file mode 600) OR keyring ref
```

Example `config.json`:

```json
{
  "api_url": "https://<jira-fetch-host>",
  "token_ref": "file:~/.config/kb/token",
  "allowlist": {
    "jira_project_keys": { "mobileai": ["RIC"], "gothailand": ["<fill>"] },
    "github_orgs":       { "mobileai": ["Mobile-AI-Co-Ltd-0105567015509"], "gothailand": ["<fill>"] },
    "memory_globs":      ["ψ/memory/learnings/**/*.md", "ψ/memory/retrospectives/**/*.md"]
  },
  "classifier": { "model": "claude-haiku-4-5", "threshold": 0.7 },
  "secret_scan": { "action": "reject" }
}
```

### 8.3 `/kb scan` pipeline (every run, entirely client-side)

1. **Collect candidates.** Jira: query jira-fetch's existing Postgres for
   issues whose project key is in the allowlist, modified since the per-source
   cursor in `state.json`. Memory: glob files modified since the cursor,
   filter to those with `repo:` frontmatter in the allowlist OR body
   mentioning an allowlisted GitHub org / project key.
2. **Heuristic gate.** Deterministic. Drop anything that doesn't match the
   allowlist by path/key/org. No LLM here.
3. **Secret scan.** Gitleaks-style regex set (AWS keys, GitHub PATs, Slack
   tokens, Firebase configs, JWT-shaped strings, `.env`-style `KEY=value`
   with high-entropy values) plus a Shannon-entropy check. **Reject, do not
   redact.** Partial redactions are how secrets leak. Skipped items are
   listed in the run summary.
4. **LLM judge.** For each survivor, call `claude-haiku-4-5` (cheap) with
   *"Does this content benefit other devs working on `<scope>`? Reply JSON
   `{benefits: bool, confidence: 0-1, reason: str}`."* Keep only
   `benefits ∧ confidence ≥ threshold`.
5. **Approval gate.** Print a table (one row per survivor: source, scope,
   title, body preview, judge reason). User picks `a` (all), `1,3,5`
   (numbered), or `n` (none).
6. **Upload.** Batch-call MCP `kb_ingest`. Skill includes classifier
   confidence, judge reason, tags, and optional `uploaded_by` in `metadata`.
   Cursor advances on 2xx only.
7. **Summary.** `N ingested · M secret-rejected · K classifier-rejected · L user-skipped`.

### 8.4 What deliberately stays out

- **Token issuance/revocation.** With a single shared key there is nothing
  to issue per dev. New devs receive the key out-of-band.
- **Admin operations** (purging dead chunks, vacuuming, reindexing pgvector).
  Separate ops scripts on the EC2 box; devs do not run those.

## 9. Deploy

### 9.1 New files in `jira-fetch`

```
jira-fetch/
├── apps/api/src/routes/kb/                ← NEW: KB routes + MCP server
│   ├── index.ts          # mounts /api/kb/* + /mcp on existing Hono app
│   ├── ingest.ts
│   ├── search.ts
│   ├── chunks.ts
│   ├── mcp.ts            # @modelcontextprotocol/sdk wired to Hono
│   └── auth.ts           # constant-time bearer check
├── apps/api/src/services/kb.ts            ← NEW: shared by HTTP + MCP handlers
├── apps/memory-embed/                     ← NEW: Python sidecar
│   ├── embed_service.py
│   ├── requirements.txt
│   └── README.md
├── db/migrations/00NN_memory_chunk.sql    ← NEW
└── deploy/
    ├── memory-kb-embed.service            ← NEW systemd unit
    └── nginx-kb.snippet.conf              ← NEW nginx block
```

### 9.2 systemd unit (only one new unit needed)

`deploy/memory-kb-embed.service`:

```ini
[Unit]
Description=Memory KB embed sidecar (mpnet 768-dim)
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/jira-fetch/apps/memory-embed
EnvironmentFile=/home/ec2-user/.env.d/memory-embed.sh
ExecStart=/home/ec2-user/jira-fetch/apps/memory-embed/.venv/bin/uvicorn embed_service:app --host 127.0.0.1 --port 3897
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

KB HTTP routes and the MCP server live inside the existing
`jirafetch-api.service` — no new Bun process.

### 9.3 nginx block

Included into the existing jirafetch vhost:

```nginx
location = /health        { proxy_pass http://127.0.0.1:<jirafetch-api-port>; }
location   /api/kb/       { proxy_pass http://127.0.0.1:<jirafetch-api-port>; }

location /mcp {
    proxy_pass http://127.0.0.1:<jirafetch-api-port>;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_read_timeout 24h;
    proxy_set_header Authorization $http_authorization;
}
```

### 9.4 Env

Additions to `/home/runner/.env.d/jirafetch.sh` (already used by the existing
deploy):

```sh
KB_API_KEY=<shared-bearer>            # single secret, all devs
KB_EMBED_URL=http://127.0.0.1:3897
KB_DB_URL=$DATABASE_URL                # reuse existing Postgres
```

New file `/home/ec2-user/.env.d/memory-embed.sh`:

```sh
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
EMBED_PORT=3897
```

### 9.5 GH Actions deploy

Extend the existing `.github/workflows/deploy.yml` (push to `master`):

1. rsync (existing) — picks up the new `apps/memory-embed/` and `deploy/`
2. **NEW:** if `apps/memory-embed/requirements.txt` changed →
   `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. **NEW:** copy `deploy/memory-kb-embed.service` → `/etc/systemd/system/`
   and `systemctl daemon-reload`
4. `bun db:migrate` (existing — picks up the new migration)
5. `systemctl restart memory-kb-embed jirafetch-api` (extend existing
   restart line)
6. Health check: `curl https://<host>/health` returns 200 AND
   `curl https://<host>/api/kb/health -H "Authorization: Bearer …"` reports
   `db_ok ∧ embed_ok` — fail the deploy otherwise.

### 9.6 Secrets

`KB_API_KEY` is created once on the EC2 box (or generated locally and copied)
and lives only in `/home/runner/.env.d/jirafetch.sh`. Never committed.
Distributed to devs out-of-band.

## 10. Testing in prod

Stepped smoke test, run from a dev workstation, in order. Stop at first
failure.

- **T1** — `curl /health` → 200.
- **T2** — Bearer wired: authed `POST /api/kb/search` with `{"query":"smoke","top_k":1}` → 200; unauthed → 401.
- **T3** — `GET /api/kb/health` returns `{ok, embed_ok, db_ok}` all true.
- **T4** — HTTP write/read round-trip via canary chunk
  (`external_id = "prod-smoke-T4"`, `source = "smoke"`, `scope = "smoke"`):
  ingest → search → confirm in top-3 → soft retract.
- **T5** — Configure `~/.claude.json` to add the `jira-fetch-kb` MCP server
  with bearer; in a fresh Claude Code session `/mcp` lists 5 tools.
- **T6** — Prompt the session to call `kb_search` for the T4 chunk; confirm
  the model invokes the MCP tool and gets the row back.
- **T7** — Full skill pipeline: `/kb status` → `/kb scan --dry-run` →
  `/kb scan` with one approval → `/kb search` finds the new chunk →
  `/kb retract` with reason.
- **T8** — While T4-T7 run, `journalctl -fu jirafetch-api -u memory-kb-embed`
  on the box. No stack traces; embed latency ~100-300ms.

**Rollback plan:**

1. `systemctl stop memory-kb-embed && systemctl restart jirafetch-api` — KB
   routes will 5xx but the rest of jira-fetch keeps working.
2. Revert the deploy SHA and re-rsync. The migration is additive
   (`CREATE EXTENSION` + new tables); rollback leaves the tables in place
   harmlessly.
3. Scrub canary chunks if needed:
   `DELETE FROM memory_chunk WHERE source = 'smoke';`.

"Tested in prod" = T1-T8 green, canary chunks retracted, logs clean.

## 11. Open items to confirm before implementation

These are the only items where the spec defers to user input:

1. **`gothailand` Jira project key(s)** — fill the
   `allowlist.jira_project_keys.gothailand` config slot.
2. **`gothailand` GitHub org(s)** — fill
   `allowlist.github_orgs.gothailand`.
3. **`jirafetch-api` port** — currently parameterised as
   `<jirafetch-api-port>`; the existing systemd unit / Hono entry will tell
   us the exact value (likely 3000 or 3001).
4. **`jira-fetch-host`** — the host name behind nginx. Existing vhost
   config will tell us.
5. **Whether `db/migrations` numbering** clashes — pick the next free
   `00NN_` prefix at implementation time.

None of these block design approval; they're config values to look up before
implementation starts.

## 12. Decisions log (for posterity)

- **Server is dumb.** No content filtering, scope enums, or secret scans
  server-side. The skill on each dev's workstation owns the entire gate.
  Trade-off accepted: a misconfigured/malicious client with the bearer can
  push garbage. Mitigation: documentation + convention; no code-level guard.
- **Single shared bearer.** No per-dev tokens. Trade-off accepted: cannot
  revoke individual devs without rotating everyone.
- **Both HTTP and MCP, MCP preferred.** HTTP is the fallback for scripts and
  non-Claude clients. MCP is canonical because the skill enforces filtering
  before any call.
- **Option C (bolt onto existing Hono).** Not Option A's separate Elysia
  subapp. One process, one framework, less drift.
- **Soft retract only.** Honours "Nothing is Deleted" Golden Rule.
- **Heuristic gate + LLM judge in skill.** Not server-side. Each dev tunes
  their own classifier threshold and secret patterns.
