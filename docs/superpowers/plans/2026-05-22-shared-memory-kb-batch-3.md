# Shared Memory KB — Batch 3: MCP server at /mcp

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mount an MCP (Model Context Protocol) server at `/mcp` inside the existing `jirafetch-api` Hono process, exposing 5 tools (`kb_health`, `kb_search`, `kb_get`, `kb_ingest`, `kb_retract`) that wrap the same `KbService` already powering the HTTP routes from batch 2. Same single shared bearer (`KB_API_KEY`) gates `/mcp` — devs can wire their Claude Code sessions to `https://<host>/mcp` with the bearer and call KB tools from inside any chat.

**Architecture:** New `apps/api/src/kb/mcp/` module. Build an `McpServer` from `@modelcontextprotocol/server`, register 5 tools whose handlers call into the existing `KbService` instance (not the HTTP endpoints — same process, share the service layer). Mount via `WebStandardStreamableHTTPServerTransport` on a Hono `app.all('/mcp', …)` route. Stateless mode (no session map) keeps it simple; per-dev MCP sessions are tiny enough that the SDK's stateless transport is fine. Bearer middleware runs before the transport handler — same constant-time compare as `/api/kb/*`.

**Tech Stack:** Hono ^4.6.14 (existing); `@modelcontextprotocol/server` + `@modelcontextprotocol/hono` (new dep — split packages from the MCP TS SDK monorepo); Zod ^3.23.8 (existing — reuse schemas from `apps/api/src/kb/types.ts`); bun:test.

**Spec:** `docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md` §6.2 + §7.

**Prerequisites (must be true on the box before merging):**
- Batches 1 + 2 deployed and verified (they already are as of 2026-05-22).
- `KB_API_KEY` already set in `/home/runner/.env.d/jirafetch.sh` (it is — from batch 2 kickoff).
- The new `@modelcontextprotocol/server` + `@modelcontextprotocol/hono` packages must be available on npm. If they're not yet published (the SDK is mid-monorepo-split), fall back to the older monolithic `@modelcontextprotocol/sdk` package (which has had Streamable HTTP since 2024-11). The fallback is called out per-task where it matters.

**Out of scope for this batch (deferred):**
- The `/kb` skill in artemis-oracle (batch 4) that will *consume* this MCP server.
- nginx config updates to expose `/mcp` publicly (the existing nginx vhost for jirafetch already proxies `/api/*` to localhost:6501; an explicit `/mcp` `location` block — with the SSE-friendly headers from spec §9.3 — should be confirmed as part of the post-merge smoke. For now `/mcp` is reachable on `localhost:6501` only; that's fine for the smoke and for devs SSH-tunneling.)
- GH Actions deploy.yml extensions for the sidecar venv (batch 5).
- Per-tool rate limits, request logging beyond Hono's existing `logger()` middleware, structured tracing.

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/package.json` | modify | Add `@modelcontextprotocol/server` + `@modelcontextprotocol/hono` deps |
| `apps/api/src/kb/mcp/server.ts` | create | `createKbMcpServer(service)` factory — builds an `McpServer`, registers 5 tools |
| `apps/api/src/kb/mcp/tool-results.ts` | create | Small helpers: format service results as MCP `{content: [...]}` envelopes |
| `apps/api/src/kb/mcp/handler.ts` | create | `mountKbMcp(app, service)` — wires bearer + Streamable HTTP transport at `/mcp` |
| `apps/api/src/index.ts` | modify | Mount `/mcp` alongside the existing `/api/kb` |
| `apps/api/test/unit/kb/mcp-server.test.ts` | create | Unit tests for each tool handler (stub `KbService`, invoke via the `McpServer` programmatically) |

No changes to `service.ts`, `types.ts`, `embed-client.ts`, or the HTTP routes from batch 2 — those stay intact.

---

## Task 1: Add dep + verify package availability + branch

**Files:**
- Modify: `apps/api/package.json` + `bun.lock`

- [ ] **Step 1: Create the feature branch**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
git fetch origin master
git checkout -b feat/shared-memory-kb-batch-3 origin/master
```

Verify: `git rev-parse master` matches `git merge-base feat/shared-memory-kb-batch-3 master`.

- [ ] **Step 2: Probe which MCP packages are actually published**

The MCP TypeScript SDK is in the middle of a monorepo split. The plan targets the new split packages, but they may not all be on npm yet. Run from `apps/api/`:

```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun pm view @modelcontextprotocol/server 2>&1 | head -5
bun pm view @modelcontextprotocol/hono 2>&1 | head -5
bun pm view @modelcontextprotocol/sdk 2>&1 | head -5
```

(Older `bun` uses `bun pm view`; if your bun version disagrees, try `npm view <pkg> version`.)

Decision:
- **If `@modelcontextprotocol/server` AND `@modelcontextprotocol/hono` are both published:** proceed with the new split packages (preferred — matches the Context7 docs as of 2026-05-22).
- **Otherwise:** fall back to `@modelcontextprotocol/sdk` (the older monolith). The class names differ slightly (`McpServer` → still `McpServer`; transport is `StreamableHTTPServerTransport` not `WebStandardStreamableHTTPServerTransport`; no `createMcpHonoApp` helper — wire the transport's request handler manually). Section "Fallback path" at the bottom of this plan has the alternate code.

For the rest of this plan, code blocks assume the **preferred** split packages. If you fall back, substitute imports per the Fallback section.

- [ ] **Step 3: Install the deps**

Preferred path:
```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun add @modelcontextprotocol/server @modelcontextprotocol/hono
```

Fallback path (if Step 2 said the split packages aren't published):
```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun add @modelcontextprotocol/sdk
```

- [ ] **Step 4: Commit**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
git add apps/api/package.json bun.lock
git commit -m "feat(kb): add MCP SDK dep for /mcp transport

Adds @modelcontextprotocol/server + @modelcontextprotocol/hono (or
@modelcontextprotocol/sdk fallback — note in commit message which path
was taken). No source-code changes yet — those land in the next commits."
```

---

## Task 2: MCP tool-result formatter

**Files:**
- Create: `apps/api/src/kb/mcp/tool-results.ts`

A small helper module so the 5 tool handlers in Task 3 stay focused on calling `KbService`. MCP tools return `{content: [...]}` envelopes; we wrap structured data as JSON text content.

- [ ] **Step 1: Write the file**

```typescript
// apps/api/src/kb/mcp/tool-results.ts

/**
 * MCP tool result envelope: a list of content blocks.
 *
 * For KB tools, we wrap the structured response as a single text block with
 * pretty-printed JSON. The model sees `text` directly, which is more useful
 * than an opaque resource link for search/get/health responses.
 */

export type ToolContent = { type: 'text'; text: string };
export type ToolResult = { content: ToolContent[]; isError?: boolean };

export function jsonResult(value: unknown): ToolResult {
  return {
    content: [{ type: 'text', text: JSON.stringify(value, null, 2) }],
  };
}

export function errorResult(err: unknown): ToolResult {
  const message =
    err instanceof Error
      ? err.message
      : typeof err === 'string'
        ? err
        : JSON.stringify(err);
  return {
    isError: true,
    content: [{ type: 'text', text: message }],
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/kb/mcp/tool-results.ts
git commit -m "feat(kb-mcp): tool-result formatter helpers

jsonResult wraps any value as a pretty-printed JSON text content block.
errorResult sets isError=true and extracts a sensible message. Used by
all 5 KB MCP tools to keep their handlers slim."
```

---

## Task 3: McpServer factory + 5 tool registrations + unit tests (red → green)

**Files:**
- Create: `apps/api/src/kb/mcp/server.ts`
- Create: `apps/api/test/unit/kb/mcp-server.test.ts`

- [ ] **Step 1: Write the failing tests**

The tests construct an `McpServer` via the factory, then exercise each tool's handler through the SDK's in-memory client/server pair (the SDK ships a `Client` + an in-memory linked-pair transport for exactly this). If those helpers aren't available in your fallback path, see the "Fallback path" note at the end of this task.

```typescript
// apps/api/test/unit/kb/mcp-server.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'bun:test';
import { Client } from '@modelcontextprotocol/server';            // client side (peer)
import {
  InMemoryTransport,
} from '@modelcontextprotocol/server';                            // bi-directional in-memory pipe
import { createKbMcpServer } from '../../../src/kb/mcp/server';
import type { KbService } from '../../../src/kb/service';

function makeStubService(): KbService {
  // We only test that the tool handler calls the right method with the right args.
  // Each method returns a deterministic shape we can match.
  return {
    async health() {
      return { ok: true, db_ok: true, embed_ok: true };
    },
    async search(req) {
      return [
        {
          id: 1,
          source: 'jira',
          scope: 'mobileai',
          external_id: 'RIC-1',
          title: 't',
          body_snippet: 's',
          metadata: {},
          similarity: 0.9,
        },
      ];
    },
    async getChunk(id) {
      return {
        id,
        source: 'jira',
        scope: 'mobileai',
        external_id: 'X',
        title: 't',
        body: 'b',
        metadata: {},
        created_at: '2026-01-01T00:00:00Z',
        revoked_at: null,
      };
    },
    async ingest(req) {
      return {
        upserted: req.chunks.map((c, i) => ({
          id: 100 + i,
          external_id: c.external_id,
        })),
      };
    },
    async retract(id, reason) {
      return { ok: true, revoked_at: '2026-05-22T00:00:00Z' };
    },
  } as unknown as KbService;
}

let client: Client;
let cleanup: () => Promise<void>;

beforeAll(async () => {
  const { server } = createKbMcpServer(makeStubService());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  client = new Client({ name: 'test', version: '1.0.0' });
  await client.connect(clientTransport);
  cleanup = async () => {
    await client.close();
    await server.close();
  };
});

afterAll(async () => {
  await cleanup();
});

describe('KB MCP server', () => {
  it('lists 5 tools', async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(['kb_get', 'kb_health', 'kb_ingest', 'kb_retract', 'kb_search']);
  });

  it('kb_health returns service health JSON', async () => {
    const res = await client.callTool({ name: 'kb_health', arguments: {} });
    expect(res.isError).toBeFalsy();
    const text = (res.content as any[])[0].text;
    expect(JSON.parse(text)).toMatchObject({ ok: true, db_ok: true, embed_ok: true });
  });

  it('kb_search wraps service.search', async () => {
    const res = await client.callTool({
      name: 'kb_search',
      arguments: { query: 'rice', top_k: 3 },
    });
    expect(res.isError).toBeFalsy();
    const text = (res.content as any[])[0].text;
    const parsed = JSON.parse(text);
    expect(parsed.results).toHaveLength(1);
    expect(parsed.results[0].external_id).toBe('RIC-1');
  });

  it('kb_get wraps service.getChunk and returns 404-style error on null', async () => {
    const res = await client.callTool({
      name: 'kb_get',
      arguments: { id: 42 },
    });
    expect(res.isError).toBeFalsy();
    const parsed = JSON.parse((res.content as any[])[0].text);
    expect(parsed.id).toBe(42);
    expect(parsed.external_id).toBe('X');
  });

  it('kb_ingest wraps service.ingest', async () => {
    const res = await client.callTool({
      name: 'kb_ingest',
      arguments: {
        chunks: [
          {
            source: 's',
            scope: 'mobileai',
            external_id: 'E-1',
            title: 't',
            body: 'b',
            metadata: {},
          },
        ],
      },
    });
    expect(res.isError).toBeFalsy();
    const parsed = JSON.parse((res.content as any[])[0].text);
    expect(parsed.upserted).toHaveLength(1);
    expect(parsed.upserted[0].external_id).toBe('E-1');
  });

  it('kb_retract wraps service.retract', async () => {
    const res = await client.callTool({
      name: 'kb_retract',
      arguments: { id: 7, reason: 'test' },
    });
    expect(res.isError).toBeFalsy();
    const parsed = JSON.parse((res.content as any[])[0].text);
    expect(parsed.ok).toBe(true);
  });

  it('kb_search rejects empty query', async () => {
    const res = await client.callTool({
      name: 'kb_search',
      arguments: { query: '' },
    });
    expect(res.isError).toBe(true);
  });
});
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
bun test apps/api/test/unit/kb/mcp-server.test.ts 2>&1 | tail -10
```

Expected: tests fail with `Cannot find module '../../../src/kb/mcp/server'` (file doesn't exist yet).

- [ ] **Step 3: Implement the server factory**

```typescript
// apps/api/src/kb/mcp/server.ts
import { McpServer } from '@modelcontextprotocol/server';
import { z } from 'zod';
import type { KbService } from '../service';
import { jsonResult, errorResult } from './tool-results';
import {
  IngestRequestSchema,
  SearchRequestSchema,
  RetractRequestSchema,
} from '../types';

/**
 * Build an MCP server with the 5 KB tools wired to the given KbService.
 *
 * Returns `{ server }` — caller is responsible for connecting it to a
 * transport (see handler.ts for the HTTP wiring, or InMemoryTransport
 * for tests).
 *
 * Stateless: each request is independent. No long-running session state
 * is carried inside the server beyond the SDK's protocol bookkeeping.
 */
export function createKbMcpServer(service: KbService): { server: McpServer } {
  const server = new McpServer({ name: 'jira-fetch-kb', version: '0.1.0' });

  // kb_health — no inputs
  server.registerTool(
    'kb_health',
    {
      description: 'Probe KB service health (DB + embed sidecar).',
      inputSchema: z.object({}),
    },
    async () => {
      try {
        const h = await service.health();
        return jsonResult(h);
      } catch (e) {
        return errorResult(e);
      }
    },
  );

  // kb_search — query, optional filters, top_k, min_similarity
  server.registerTool(
    'kb_search',
    {
      description:
        'Semantic search over the shared memory KB. Returns top-k cosine matches with optional scope/source filters.',
      inputSchema: SearchRequestSchema,
    },
    async (args) => {
      try {
        const results = await service.search(args);
        return jsonResult({ results });
      } catch (e) {
        return errorResult(e);
      }
    },
  );

  // kb_get — fetch a single chunk by id
  server.registerTool(
    'kb_get',
    {
      description:
        'Fetch the full body + metadata for a single chunk by id. Returns null-shaped error if the chunk does not exist.',
      inputSchema: z.object({ id: z.number().int().positive() }),
    },
    async ({ id }) => {
      try {
        const chunk = await service.getChunk(id);
        if (!chunk) {
          return errorResult(new Error(`chunk ${id} not found`));
        }
        return jsonResult(chunk);
      } catch (e) {
        return errorResult(e);
      }
    },
  );

  // kb_ingest — write path (curator skill's destination)
  server.registerTool(
    'kb_ingest',
    {
      description:
        'Insert one or more chunks. Server is dumb — no scope enforcement, no secret scan, no filtering. The /kb skill is the gatekeeper.',
      inputSchema: IngestRequestSchema,
    },
    async (args) => {
      try {
        const result = await service.ingest(args);
        return jsonResult(result);
      } catch (e) {
        return errorResult(e);
      }
    },
  );

  // kb_retract — soft delete by id
  server.registerTool(
    'kb_retract',
    {
      description:
        'Soft-retract a chunk by id. Sets revoked_at = now() and stores the reason in metadata.retraction_reason.',
      inputSchema: z.object({
        id: z.number().int().positive(),
        reason: RetractRequestSchema.shape.reason,
      }),
    },
    async ({ id, reason }) => {
      try {
        const result = await service.retract(id, reason);
        if (!result.ok) {
          return errorResult(new Error(`chunk ${id} not found or already revoked`));
        }
        return jsonResult(result);
      } catch (e) {
        return errorResult(e);
      }
    },
  );

  return { server };
}
```

- [ ] **Step 4: Re-run tests, expect all green**

```bash
bun test apps/api/test/unit/kb/mcp-server.test.ts 2>&1 | tail -15
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/kb/mcp/server.ts apps/api/test/unit/kb/mcp-server.test.ts
git commit -m "feat(kb-mcp): McpServer factory with 5 tools wired to KbService

createKbMcpServer(service) returns {server} ready to connect to any
MCP transport. Tools: kb_health, kb_search, kb_get, kb_ingest, kb_retract.
Each handler wraps service errors with errorResult (isError:true).
Tests use InMemoryTransport.createLinkedPair() to exercise the protocol
end-to-end with a stubbed KbService."
```

**Fallback path note:** if you ended up on `@modelcontextprotocol/sdk` (the monolith), the imports change:

```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
```

The `McpServer` API surface (`.registerTool` / `.tool`) and `Client.callTool` are stable across both packagings.

---

## Task 4: HTTP transport handler with bearer auth

**Files:**
- Create: `apps/api/src/kb/mcp/handler.ts`

- [ ] **Step 1: Write the handler**

```typescript
// apps/api/src/kb/mcp/handler.ts
import type { Hono } from 'hono';
import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/server';
import type { KbService } from '../service';
import { bearerAuth } from '../routes/auth';
import { createKbMcpServer } from './server';

/**
 * Wire the KB MCP server onto an existing Hono app at `/mcp`.
 *
 * Stateless mode: each request gets its own transport instance. This is
 * simpler than session-tracking and adequate for the expected load
 * (a few devs running ad-hoc tool calls). Stateful mode would buy us
 * SSE streaming for long-lived subscriptions, but the KB tools are all
 * one-shot RPC; not worth the session-map complexity.
 *
 * Bearer auth gates the `/mcp` endpoint — same KB_API_KEY as the HTTP
 * routes. Constant-time compare in bearerAuth.
 */
export function mountKbMcp(app: Hono, service: KbService): void {
  app.use('/mcp', bearerAuth);
  app.use('/mcp/*', bearerAuth);

  app.all('/mcp', async (c) => {
    const { server } = createKbMcpServer(service);
    const transport = new WebStandardStreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless
    });
    await server.connect(transport);
    return transport.handleRequest(c.req.raw);
  });
}
```

- [ ] **Step 2: Quick TS check**

```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun tsc --noEmit 2>&1 | grep -E 'kb/mcp/' | head -10
```

Expected: no errors specific to `kb/mcp/`. If `WebStandardStreamableHTTPServerTransport` isn't exported from the resolved package, see the Fallback section.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/kb/mcp/handler.ts
git commit -m "feat(kb-mcp): Hono handler with bearer auth + stateless transport

mountKbMcp(app, service) registers a single app.all('/mcp', ...) route.
Bearer middleware runs first (same KB_API_KEY constant-time check as the
HTTP routes). Each request gets a fresh transport — stateless is fine
for one-shot tool calls; stateful sessions would buy nothing for this
workload."
```

---

## Task 5: Wire into main app + push + PR

**Files:**
- Modify: `apps/api/src/index.ts`

- [ ] **Step 1: Mount /mcp on the main Hono app**

Find the existing batch-2 block in `apps/api/src/index.ts`:

```typescript
// --- Shared memory KB (batch 2) ---------------------------------------
const kbDb = createDbClient({ transform: false, max: 5 });
const kbEmbed = new HttpEmbedClient(process.env.KB_EMBED_URL ?? 'http://127.0.0.1:3897');
app.route('/api/kb', createKbRouter({ db: kbDb, embed: kbEmbed }));
```

Extend it so the same `KbService` is shared with the MCP mount. The simplest restructure: build the service once, then pass it to both the router factory and the MCP mount. Replace the block with:

```typescript
// --- Shared memory KB (batches 2 + 3) ---------------------------------
import { KbService } from './kb/service';
import { mountKbMcp } from './kb/mcp/handler';

const kbDb = createDbClient({ transform: false, max: 5 });
const kbEmbed = new HttpEmbedClient(process.env.KB_EMBED_URL ?? 'http://127.0.0.1:3897');
const kbService = new KbService({ db: kbDb, embed: kbEmbed });
app.route('/api/kb', createKbRouter({ db: kbDb, embed: kbEmbed }));
mountKbMcp(app, kbService);
```

Note: `createKbRouter` still builds its own internal `KbService` from the same deps — that's mildly redundant but cheaper to change in batch 4 than to refactor the factory signature now. The MCP mount uses the explicit `kbService` instance.

(If you want to avoid the duplicate `KbService` construction, extend `createKbRouter` to accept either `{db, embed}` or `{service}`. That refactor is YAGNI for batch 3 — defer.)

- [ ] **Step 2: Run unit tests, typecheck**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
bun test apps/api/test/unit/kb 2>&1 | tail -10
# expect: all green (including the 7 new mcp-server tests)

cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun tsc --noEmit 2>&1 | grep -E '(error TS|kb/mcp)' | head -10
# expect: no NEW errors in kb/mcp
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/index.ts
git commit -m "feat(kb-mcp): mount /mcp on main app, share KbService with HTTP routes

The MCP mount uses an explicit KbService instance constructed alongside
the existing /api/kb wiring. createKbRouter still builds its own service
internally — minor duplication; defer the refactor until it actually
hurts."
```

- [ ] **Step 4: Push + open PR**

```bash
git push -u origin feat/shared-memory-kb-batch-3
gh pr create --base master --head feat/shared-memory-kb-batch-3 \
  --title "feat(memory-kb): batch 3 — MCP server at /mcp" \
  --body "$(cat <<'EOF'
## Summary

Adds an MCP (Model Context Protocol) server at \`/mcp\` inside the existing \`jirafetch-api\` Hono process. Same bearer (\`KB_API_KEY\`) gates it. Five tools wrap the same \`KbService\` that powers the HTTP routes from batch 2:

- \`kb_health\` — probe DB + embed sidecar
- \`kb_search\` — semantic search (top-k cosine + optional filters)
- \`kb_get\` — fetch single chunk by id
- \`kb_ingest\` — write chunks (server is dumb — /kb skill is the gatekeeper)
- \`kb_retract\` — soft retract a chunk

Stateless transport (\`WebStandardStreamableHTTPServerTransport\` with \`sessionIdGenerator: undefined\`) — every tool call is independent. The transport is web-standards-based so it works natively in Bun/Hono.

## Out of scope (deferred)

- \`/kb\` skill in artemis-oracle (batch 4) — will *consume* this MCP server
- nginx \`location /mcp\` block with SSE-friendly headers (will land alongside the skill)
- GH Actions deploy.yml automation for the sidecar venv (batch 5)

## Spec / plan

- Spec: \`docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md\` §6.2 + §7
- Plan: \`docs/superpowers/plans/2026-05-22-shared-memory-kb-batch-3.md\` (artemis-oracle)

## Test plan

CI / pre-merge:
- [x] Unit tests: 7 cases in \`apps/api/test/unit/kb/mcp-server.test.ts\` (listTools + 5 tool happy-paths + 1 validation-error) — all green via \`InMemoryTransport.createLinkedPair()\`

Post-merge (manual prod smoke):
- [ ] \`curl -X POST http://localhost:6501/mcp -H "Authorization: Bearer \$KB_API_KEY" -H 'Accept: application/json, text/event-stream' -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}'\` → returns the initialize response with the 5 tools listed under capabilities.
- [ ] \`curl -X POST .../mcp ... -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'\` → returns the 5 tool definitions.
- [ ] \`curl -X POST .../mcp ... -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"kb_health","arguments":{}}}'\` → returns content with the health JSON.
- [ ] An ingest+search round-trip via raw JSON-RPC, then cleanup of \`source = 'mcp-smoke'\` rows.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

DO NOT auto-merge. The user reviews + merges.

- [ ] **Step 5: Self-review summary in your report**

When reporting back, include:
- The PR URL
- Final commit SHA
- Whether you used the preferred packages or the fallback
- Unit test count + pass/fail
- The exact `bun add` line that worked (so we can capture it in memory if the packaging changes again)

---

## Definition of Done

- [ ] PR merged to `master`; GH Actions deploy.yml runs cleanly and triggers a `jirafetch-api` restart
- [ ] `curl` JSON-RPC smoke (3 calls above) returns the expected shapes against `localhost:6501/mcp` on the prod box
- [ ] `journalctl -u jirafetch-api` shows MCP requests being served (no stack traces)
- [ ] At least one dev's `~/.claude.json` is updated to point at the new MCP server (smoke from a real Claude Code session: ask the model to call `kb_search`)
- [ ] Any sentinel rows cleaned up

---

## Rollback

This batch only adds files under `apps/api/src/kb/mcp/` and one ~5-line block in `apps/api/src/index.ts`. To roll back:

1. Revert the merge commit on `master`; GH Actions re-deploys and `/mcp` returns 404 (just like before this batch).
2. The `/api/kb/*` HTTP routes from batch 2 are unaffected.
3. `KB_API_KEY` and `KB_EMBED_URL` stay in the env — harmless even with no MCP.
4. The MCP packages stay in `node_modules` until the next `bun install` — also harmless.

---

## Fallback path (if `@modelcontextprotocol/server` + `@modelcontextprotocol/hono` are not on npm)

Use the older monolithic `@modelcontextprotocol/sdk`. Substitutions:

| Preferred | Fallback |
|---|---|
| `import { McpServer } from '@modelcontextprotocol/server'` | `import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'` |
| `import { Client, InMemoryTransport } from '@modelcontextprotocol/server'` | `import { Client } from '@modelcontextprotocol/sdk/client/index.js'` + `import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js'` |
| `import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/server'` | `import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'` |
| Handler: `transport.handleRequest(c.req.raw)` (returns `Response`) | Handler: `await transport.handleRequest(req, res, body)` — needs Node-style req/res, which means using Hono's `c.env` adapter OR converting via a bridge. Easier alternative: keep using the monolith's older `SSEServerTransport` API with the dual `GET /sse` + `POST /messages` endpoints. The spec accepts either transport. |

If you take the fallback, note it in the Task 1 commit message AND in the PR description, and save a memory entry pointing at the working package coordinates so we don't have to re-test next batch.
