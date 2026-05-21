# Shared Memory KB — Batch 2: HTTP API on Hono + bearer auth

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the HTTP KB API (5 endpoints + bearer auth) to jira-fetch's existing Hono process, with a dumb-server design that takes whatever the client posts (no scope enforcement, no secret scan, no filtering — those live in the `/kb` skill in a later batch).

**Architecture:** New `apps/api/src/kb/` feature module exporting `createKbRouter({db, embed})`. The route module is dep-injected with a Postgres client and an `EmbedClient` (HTTP wrapper around the loopback sidecar built in batch 1). Each handler validates a Zod schema, calls into `KbService`, returns JSON. All routes are bearer-auth-gated by a single middleware that constant-time compares against `KB_API_KEY` from env. No scope enums, no migrations needed (table already exists from batch 1).

**Tech Stack:** Hono ^4.6.14, postgres.js ^3.4.5 (jira-fetch's existing driver), pgvector (already migrated by batch 1), Zod ^3.23.8, bun:test, Node `crypto.timingSafeEqual`.

**Spec:** `docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md` §6.1 + §7.

**Prerequisites (must be true before merging this batch):**
- Batch 1 merged AND the prod EC2 has the pgvector apt package installed AND `bun db:migrate` has been replayed on the box so `memory_chunk` exists.
- The embed sidecar is provisioned and running on the box at `127.0.0.1:3897`. (Otherwise `/api/kb/search` and `/api/kb/ingest` will 502 in prod — but `/api/iso/*` and the rest of jira-fetch keep working.)

**Out of scope for this batch (deferred):**
- MCP server at `/mcp` (batch 3)
- `/kb` skill in artemis-oracle (batch 4)
- nginx changes / public exposure (batch 5)
- GH Actions deploy.yml extensions for the sidecar venv (batch 5)
- Multi-key auth, per-dev tokens, audit logging — spec §7 explicitly chose single shared bearer

**Gotcha caught during the final cross-cutting review (folded into commit `aeff5cb`):** `apps/api/src/db/client.ts`'s `createDbClient()` applies `transform: { column: postgres.toCamel }` unconditionally — every SELECT returns camelCase keys. The KB module uses snake_case end-to-end (matching the DDL), so this would silently break every API response (`external_id` → `undefined`, etc.) in prod. Unit tests don't catch it because the fake DB bypasses the transform. **Fix:** added a `transform?: false` opt-out to `DbClientOptions`; the KB pool calls `createDbClient({ transform: false, max: 5 })`. Lesson for future batches: any new feature that uses snake_case end-to-end needs `transform: false`; any opt-in integration test that exists should be run at least once locally before opening the PR — otherwise the SQL→TS contract is unverified.

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/.env.example` | modify | Add `KB_API_KEY` + `KB_EMBED_URL` |
| `apps/api/src/kb/types.ts` | create | Zod schemas + exported TS types (ChunkInput, SearchInput, etc.) |
| `apps/api/src/kb/embed-client.ts` | create | `EmbedClient` interface + `HttpEmbedClient` class (POST to sidecar `/embed`) |
| `apps/api/src/kb/service.ts` | create | `KbService` class — orchestrates DB + embed sidecar for all 5 verbs |
| `apps/api/src/kb/_helpers.ts` | create | `KbError` class + `handleError()` helper (mirrors iso convention) |
| `apps/api/src/kb/routes/auth.ts` | create | `bearerAuth` middleware (constant-time compare against `KB_API_KEY`) |
| `apps/api/src/kb/routes/health.ts` | create | `mountHealth(router, service)` — `/health` handler |
| `apps/api/src/kb/routes/ingest.ts` | create | `mountIngest(router, service)` — `POST /ingest` |
| `apps/api/src/kb/routes/search.ts` | create | `mountSearch(router, service)` — `POST /search` |
| `apps/api/src/kb/routes/chunks.ts` | create | `mountChunks(router, service)` — `GET` + `DELETE` `/chunks/:id` |
| `apps/api/src/kb/routes/index.ts` | create | `createKbRouter({db, embed})` factory — assembles middleware + handlers |
| `apps/api/src/index.ts` | modify | Import `createKbRouter`, construct deps, mount at `/api/kb` |
| `apps/api/test/unit/kb/auth.test.ts` | create | Bearer middleware unit tests |
| `apps/api/test/unit/kb/service.test.ts` | create | `KbService` unit tests with stub `EmbedClient` + stub `db` |
| `apps/api/test/integration/kb/routes.test.ts` | create | Full HTTP round-trip — real Postgres, stub `EmbedClient`. Opt-in via `KB_INTEGRATION_TESTS=1`. |

---

## Task 1: Branch + env vars + bearer auth middleware (red tests)

**Files:**
- Create: `apps/api/src/kb/routes/auth.ts`
- Create: `apps/api/test/unit/kb/auth.test.ts`
- Modify: `apps/api/.env.example`

- [ ] **Step 1: Create the feature branch**

Working dir: `/home/bjgdr/dev-personal/jira-fetch`. Branch from current `master` (which now contains the batch-1 merge commit `d5356d8`).

```bash
cd /home/bjgdr/dev-personal/jira-fetch
git fetch origin master
git checkout -b feat/shared-memory-kb-batch-2 origin/master
```

Verify: `git rev-parse master` matches `git merge-base feat/shared-memory-kb-batch-2 master`.

- [ ] **Step 2: Add env vars to `.env.example`**

Append to `apps/api/.env.example`:

```bash

# --- Shared Memory KB (batch 2) ------------------------------------
# Single shared bearer key for /api/kb/* and (later) /mcp. Issue once,
# distribute out-of-band. Constant-time compared in apps/api/src/kb/routes/auth.ts.
KB_API_KEY=change-me-to-a-long-random-string

# URL of the loopback embed sidecar (batch 1: apps/memory-embed/). Override
# only for local dev pointing at a remote/alternative embed service.
KB_EMBED_URL=http://127.0.0.1:3897
```

- [ ] **Step 3: Write the failing auth middleware tests**

Create `apps/api/test/unit/kb/auth.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { Hono } from 'hono';
import { bearerAuth } from '../../../src/kb/routes/auth';

function makeApp() {
  const app = new Hono();
  app.use('*', bearerAuth);
  app.get('/protected', (c) => c.json({ ok: true }));
  return app;
}

describe('bearerAuth middleware', () => {
  const originalKey = process.env.KB_API_KEY;

  beforeEach(() => {
    process.env.KB_API_KEY = 'test-key-do-not-use-in-prod';
  });
  afterEach(() => {
    if (originalKey === undefined) delete process.env.KB_API_KEY;
    else process.env.KB_API_KEY = originalKey;
  });

  it('rejects with 401 when no Authorization header is present', async () => {
    const res = await makeApp().fetch(new Request('http://x/protected'));
    expect(res.status).toBe(401);
  });

  it('rejects with 401 when header is not Bearer-scheme', async () => {
    const res = await makeApp().fetch(
      new Request('http://x/protected', { headers: { Authorization: 'Basic abc' } }),
    );
    expect(res.status).toBe(401);
  });

  it('rejects with 401 when bearer value is wrong', async () => {
    const res = await makeApp().fetch(
      new Request('http://x/protected', { headers: { Authorization: 'Bearer wrong' } }),
    );
    expect(res.status).toBe(401);
  });

  it('rejects with 401 when bearer value has different length (constant-time)', async () => {
    const res = await makeApp().fetch(
      new Request('http://x/protected', { headers: { Authorization: 'Bearer short' } }),
    );
    expect(res.status).toBe(401);
  });

  it('returns 500 when KB_API_KEY env var is not configured', async () => {
    delete process.env.KB_API_KEY;
    const res = await makeApp().fetch(
      new Request('http://x/protected', { headers: { Authorization: 'Bearer anything' } }),
    );
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toBe('KB_API_KEY_NOT_CONFIGURED');
  });

  it('passes through with correct bearer', async () => {
    const res = await makeApp().fetch(
      new Request('http://x/protected', {
        headers: { Authorization: 'Bearer test-key-do-not-use-in-prod' },
      }),
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });
});
```

- [ ] **Step 4: Run the failing test**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
bun test apps/api/test/unit/kb/auth.test.ts 2>&1 | tail -20
```

Expected: tests fail with `Cannot find module '../../../src/kb/routes/auth'` (the file doesn't exist yet).

- [ ] **Step 5: Implement the auth middleware**

Create `apps/api/src/kb/routes/auth.ts`:

```typescript
import type { Context, Next } from 'hono';
import { timingSafeEqual } from 'node:crypto';

/**
 * Constant-time bearer check against KB_API_KEY env var. Used as Hono
 * middleware via `router.use('*', bearerAuth)`.
 *
 * Returns 401 for any auth failure (missing header, wrong scheme, wrong key).
 * Returns 500 if KB_API_KEY is not configured — that's a deploy-time bug,
 * not a client bug, so don't pretend the request was authorised.
 */
export async function bearerAuth(c: Context, next: Next): Promise<Response | void> {
  const expected = process.env.KB_API_KEY;
  if (!expected) {
    return c.json(
      { error: 'KB_API_KEY_NOT_CONFIGURED', message: 'Server misconfiguration: KB_API_KEY env var is empty' },
      500,
    );
  }

  const header = c.req.header('Authorization') ?? '';
  if (!header.startsWith('Bearer ')) {
    return c.json({ error: 'UNAUTHORIZED', message: 'Bearer auth required' }, 401);
  }
  const provided = header.slice('Bearer '.length);

  // timingSafeEqual requires equal-length buffers; pre-checking length is fine
  // (length leakage is well-known and not the threat we're avoiding here).
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    return c.json({ error: 'UNAUTHORIZED', message: 'Bearer token invalid' }, 401);
  }

  await next();
}
```

- [ ] **Step 6: Re-run tests, expect all green**

```bash
bun test apps/api/test/unit/kb/auth.test.ts 2>&1 | tail -15
```

Expected: all 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/.env.example apps/api/src/kb/routes/auth.ts apps/api/test/unit/kb/auth.test.ts
git commit -m "feat(kb): bearer auth middleware + env additions

Constant-time bearer check against KB_API_KEY. 500 when env unset, 401
otherwise. Tests cover missing header, wrong scheme, wrong key, length
mismatch, unset env, happy path."
```

---

## Task 2: Types + EmbedClient

**Files:**
- Create: `apps/api/src/kb/types.ts`
- Create: `apps/api/src/kb/embed-client.ts`

- [ ] **Step 1: Define Zod schemas + TS types**

Create `apps/api/src/kb/types.ts`:

```typescript
import { z } from 'zod';

/**
 * Schema for a single chunk in an ingest request. Server-side validation is
 * minimal (length caps + types) — semantic filtering happens in the /kb skill.
 */
export const ChunkInputSchema = z.object({
  source: z.string().min(1).max(100),
  scope: z.string().min(1).max(100),
  external_id: z.string().min(1).max(255),
  title: z.string().max(500).nullable().optional(),
  body: z.string().min(1).max(50_000),
  metadata: z.record(z.unknown()).default({}),
});
export type ChunkInput = z.infer<typeof ChunkInputSchema>;

export const IngestRequestSchema = z.object({
  chunks: z.array(ChunkInputSchema).min(1).max(100),
});
export type IngestRequest = z.infer<typeof IngestRequestSchema>;

export const IngestResponseSchema = z.object({
  upserted: z.array(z.object({ id: z.number(), external_id: z.string() })),
});
export type IngestResponse = z.infer<typeof IngestResponseSchema>;

export const SearchRequestSchema = z.object({
  query: z.string().min(1).max(2_000),
  scope: z.string().min(1).max(100).optional(),
  source: z.string().min(1).max(100).optional(),
  top_k: z.number().int().min(1).max(50).default(5),
  min_similarity: z.number().min(0).max(1).default(0),
});
export type SearchRequest = z.infer<typeof SearchRequestSchema>;

export const SearchResultSchema = z.object({
  id: z.number(),
  source: z.string(),
  scope: z.string(),
  external_id: z.string(),
  title: z.string().nullable(),
  body_snippet: z.string(),
  metadata: z.record(z.unknown()),
  similarity: z.number(),
});
export type SearchResult = z.infer<typeof SearchResultSchema>;

export const ChunkSchema = z.object({
  id: z.number(),
  source: z.string(),
  scope: z.string(),
  external_id: z.string(),
  title: z.string().nullable(),
  body: z.string(),
  metadata: z.record(z.unknown()),
  created_at: z.string(),  // ISO datetime
  revoked_at: z.string().nullable(),
});
export type Chunk = z.infer<typeof ChunkSchema>;

export const RetractRequestSchema = z.object({
  reason: z.string().min(1).max(500).optional(),
});
export type RetractRequest = z.infer<typeof RetractRequestSchema>;
```

- [ ] **Step 2: Define the EmbedClient interface + HttpEmbedClient**

Create `apps/api/src/kb/embed-client.ts`:

```typescript
/**
 * Talks to the loopback embed sidecar (batch 1: apps/memory-embed/).
 * Sidecar contract: POST /embed {text} -> {embedding: number[768], dim, model}
 *                   GET /health -> {status: 'ok', model, dim}
 *
 * Interface exists so tests can inject a stub instead of running the real sidecar.
 */
export interface EmbedClient {
  embed(text: string): Promise<number[]>;
  health(): Promise<{ ok: boolean; model?: string; dim?: number; error?: string }>;
}

export class HttpEmbedClient implements EmbedClient {
  constructor(private readonly baseUrl: string) {}

  async embed(text: string): Promise<number[]> {
    const res = await fetch(`${this.baseUrl}/embed`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      throw new Error(`embed sidecar HTTP ${res.status}: ${await res.text()}`);
    }
    const body = (await res.json()) as { embedding: number[]; dim: number };
    if (!Array.isArray(body.embedding) || body.embedding.length !== 768) {
      throw new Error(`embed sidecar returned bad shape: dim=${body.dim}`);
    }
    return body.embedding;
  }

  async health(): Promise<{ ok: boolean; model?: string; dim?: number; error?: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
      const body = (await res.json()) as { status: string; model: string; dim: number };
      return { ok: body.status === 'ok', model: body.model, dim: body.dim };
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/kb/types.ts apps/api/src/kb/embed-client.ts
git commit -m "feat(kb): Zod schemas + EmbedClient interface

types.ts: schemas for ingest/search/chunk/retract — body length capped at
50k chars (so a single ingest doesn't exceed embedding token window).
embed-client.ts: HttpEmbedClient against the loopback sidecar; EmbedClient
interface lets tests swap a stub."
```

---

## Task 3: KbService skeleton + failing tests

**Files:**
- Create: `apps/api/src/kb/service.ts`
- Create: `apps/api/test/unit/kb/service.test.ts`

- [ ] **Step 1: Write the failing service tests**

Create `apps/api/test/unit/kb/service.test.ts`:

```typescript
import { describe, it, expect, mock } from 'bun:test';
import { KbService } from '../../../src/kb/service';
import type { EmbedClient } from '../../../src/kb/embed-client';

// Fake DB that records template-tag calls and returns canned rows.
// postgres.js's `sql` is a function that returns a promise of rows when
// invoked as a template tag, and exposes helpers like sql.json(). We
// recreate just enough of that surface for unit tests.
function makeFakeDb(canned: { rows: unknown[]; capture?: (s: string[], v: unknown[]) => void }) {
  const fn: any = (strings: TemplateStringsArray, ...values: unknown[]) => {
    canned.capture?.(Array.from(strings), values);
    return Promise.resolve(canned.rows);
  };
  fn.json = (v: unknown) => ({ __json: v });
  fn.unsafe = (s: string) => ({ __unsafe: s });
  return fn;
}

const fakeEmbed: EmbedClient = {
  embed: mock(async () => Array(768).fill(0.1)),
  health: mock(async () => ({ ok: true, dim: 768, model: 'fake' })),
};

describe('KbService.ingest', () => {
  it('embeds each chunk body and upserts with body_hash', async () => {
    const seen: { strings: string[]; values: unknown[] }[] = [];
    const db = makeFakeDb({
      rows: [{ id: 42, external_id: 'X-1' }],
      capture: (s, v) => seen.push({ strings: s, values: v }),
    });
    const svc = new KbService({ db, embed: fakeEmbed });

    const result = await svc.ingest({
      chunks: [
        {
          source: 'jira',
          scope: 'mobileai',
          external_id: 'RIC-100',
          title: 'Test',
          body: 'sample body text',
          metadata: { tags: ['t1'] },
        },
      ],
    });

    expect(result.upserted).toHaveLength(1);
    expect(result.upserted[0]).toEqual({ id: 42, external_id: 'X-1' });
    // body_hash should appear as a parameter — compute sha256 of body
    const allValues = seen.flatMap((c) => c.values);
    expect(allValues).toContain('jira');
    expect(allValues).toContain('mobileai');
    expect(allValues).toContain('RIC-100');
    expect(allValues).toContain('sample body text');
  });

  it('rejects an empty chunks array', async () => {
    const db = makeFakeDb({ rows: [] });
    const svc = new KbService({ db, embed: fakeEmbed });
    await expect(svc.ingest({ chunks: [] as any })).rejects.toThrow();
  });
});

describe('KbService.search', () => {
  it('returns rows from the DB query and filters by min_similarity', async () => {
    const db = makeFakeDb({
      rows: [
        {
          id: 1,
          source: 'jira',
          scope: 'mobileai',
          external_id: 'X-1',
          title: 'T1',
          body_snippet: 'snippet',
          metadata: {},
          similarity: 0.9,
        },
        {
          id: 2,
          source: 'jira',
          scope: 'mobileai',
          external_id: 'X-2',
          title: 'T2',
          body_snippet: 'snippet',
          metadata: {},
          similarity: 0.3,
        },
      ],
    });
    const svc = new KbService({ db, embed: fakeEmbed });
    const results = await svc.search({ query: 'q', top_k: 5, min_similarity: 0.5 });
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe(1);
  });
});

describe('KbService.getChunk', () => {
  it('returns the chunk row when found', async () => {
    const db = makeFakeDb({
      rows: [
        {
          id: 7,
          source: 'jira',
          scope: 'mobileai',
          external_id: 'X-7',
          title: 't',
          body: 'b',
          metadata: {},
          created_at: '2026-01-01T00:00:00Z',
          revoked_at: null,
        },
      ],
    });
    const svc = new KbService({ db, embed: fakeEmbed });
    const chunk = await svc.getChunk(7);
    expect(chunk?.id).toBe(7);
  });

  it('returns null when not found', async () => {
    const db = makeFakeDb({ rows: [] });
    const svc = new KbService({ db, embed: fakeEmbed });
    const chunk = await svc.getChunk(999);
    expect(chunk).toBeNull();
  });
});

describe('KbService.retract', () => {
  it('marks the row revoked and stores reason in metadata', async () => {
    const seen: { strings: string[]; values: unknown[] }[] = [];
    const db = makeFakeDb({
      rows: [{ id: 7, revoked_at: '2026-05-22T00:00:00Z' }],
      capture: (s, v) => seen.push({ strings: s, values: v }),
    });
    const svc = new KbService({ db, embed: fakeEmbed });
    const out = await svc.retract(7, 'cleanup smoke test');
    expect(out.ok).toBe(true);
    const allValues = seen.flatMap((c) => c.values);
    expect(allValues).toContain(7);
  });
});

describe('KbService.health', () => {
  it('returns ok when both db and embed sidecar are healthy', async () => {
    const db = makeFakeDb({ rows: [{ ok: 1 }] });
    const svc = new KbService({ db, embed: fakeEmbed });
    const h = await svc.health();
    expect(h.ok).toBe(true);
    expect(h.db_ok).toBe(true);
    expect(h.embed_ok).toBe(true);
  });
});
```

- [ ] **Step 2: Create empty service skeleton (so the import resolves but tests fail meaningfully)**

Create `apps/api/src/kb/service.ts`:

```typescript
import type { Db } from '../db/client';
import type { EmbedClient } from './embed-client';
import type {
  IngestRequest,
  IngestResponse,
  SearchRequest,
  SearchResult,
  Chunk,
} from './types';

export interface KbServiceDeps {
  db: Db | any;  // 'any' relaxes the test-fake type; real wiring passes Db
  embed: EmbedClient;
}

export class KbService {
  constructor(private readonly deps: KbServiceDeps) {}

  async ingest(_req: IngestRequest): Promise<IngestResponse> {
    throw new Error('not implemented');
  }

  async search(_req: SearchRequest): Promise<SearchResult[]> {
    throw new Error('not implemented');
  }

  async getChunk(_id: number): Promise<Chunk | null> {
    throw new Error('not implemented');
  }

  async retract(_id: number, _reason?: string): Promise<{ ok: boolean; revoked_at: string }> {
    throw new Error('not implemented');
  }

  async health(): Promise<{ ok: boolean; db_ok: boolean; embed_ok: boolean; error?: string }> {
    throw new Error('not implemented');
  }
}
```

- [ ] **Step 3: Run tests, expect red (not implemented errors)**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
bun test apps/api/test/unit/kb/service.test.ts 2>&1 | tail -25
```

Expected: all tests fail because each method throws "not implemented".

- [ ] **Step 4: Commit the red state**

```bash
git add apps/api/src/kb/service.ts apps/api/test/unit/kb/service.test.ts
git commit -m "test(kb): contract tests for KbService (red state)

Service skeleton with throw stubs; tests cover ingest happy path + empty
rejection, search top-k + min_similarity, getChunk found/missing,
retract, health. Implementation lands in the next commit."
```

---

## Task 4: Implement KbService

**Files:**
- Modify: `apps/api/src/kb/service.ts`

- [ ] **Step 1: Implement all methods**

Replace the contents of `apps/api/src/kb/service.ts`:

```typescript
import { createHash } from 'node:crypto';
import type { Db } from '../db/client';
import type { EmbedClient } from './embed-client';
import {
  ChunkInputSchema,
  IngestRequestSchema,
  SearchRequestSchema,
  type IngestRequest,
  type IngestResponse,
  type SearchRequest,
  type SearchResult,
  type Chunk,
} from './types';

export interface KbServiceDeps {
  db: Db | any;
  embed: EmbedClient;
}

function sha256(s: string): string {
  return createHash('sha256').update(s, 'utf8').digest('hex');
}

function vectorLiteral(vec: number[]): string {
  // pgvector text format: '[0.1,0.2,...]'. Sent as a parameter and cast to
  // vector(768) in the SQL — postgres.js parameterises automatically.
  return `[${vec.join(',')}]`;
}

export class KbService {
  constructor(private readonly deps: KbServiceDeps) {}

  async ingest(req: IngestRequest): Promise<IngestResponse> {
    const parsed = IngestRequestSchema.parse(req);
    const upserted: { id: number; external_id: string }[] = [];

    for (const chunk of parsed.chunks) {
      const validated = ChunkInputSchema.parse(chunk);
      const embedding = await this.deps.embed.embed(validated.body);
      const body_hash = sha256(validated.body);
      const vec = vectorLiteral(embedding);

      const rows = await this.deps.db<{ id: number; external_id: string }[]>`
        INSERT INTO memory_chunk
          (source, scope, external_id, title, body, body_hash, embedding, metadata)
        VALUES
          (${validated.source},
           ${validated.scope},
           ${validated.external_id},
           ${validated.title ?? null},
           ${validated.body},
           ${body_hash},
           ${vec}::vector(768),
           ${this.deps.db.json(validated.metadata)})
        ON CONFLICT (source, external_id, body_hash) DO UPDATE
          SET title    = EXCLUDED.title,
              metadata = EXCLUDED.metadata
        RETURNING id, external_id
      `;
      upserted.push(rows[0]!);
    }

    return { upserted };
  }

  async search(req: SearchRequest): Promise<SearchResult[]> {
    const parsed = SearchRequestSchema.parse(req);
    const embedding = await this.deps.embed.embed(parsed.query);
    const vec = vectorLiteral(embedding);

    // Build optional WHERE fragments. postgres.js supports nested templates
    // via interpolating one tagged template into another.
    const sql = this.deps.db;
    let where = sql`WHERE revoked_at IS NULL`;
    if (parsed.scope) where = sql`${where} AND scope = ${parsed.scope}`;
    if (parsed.source) where = sql`${where} AND source = ${parsed.source}`;

    const rows = await this.deps.db<SearchResult[]>`
      SELECT id,
             source,
             scope,
             external_id,
             title,
             substring(body, 1, 300) AS body_snippet,
             metadata,
             1 - (embedding <=> ${vec}::vector(768)) AS similarity
        FROM memory_chunk
        ${where}
        ORDER BY embedding <=> ${vec}::vector(768)
        LIMIT ${parsed.top_k}
    `;
    return rows.filter((r) => r.similarity >= parsed.min_similarity);
  }

  async getChunk(id: number): Promise<Chunk | null> {
    const rows = await this.deps.db<Chunk[]>`
      SELECT id, source, scope, external_id, title, body, metadata,
             created_at::text AS created_at,
             revoked_at::text AS revoked_at
        FROM memory_chunk
        WHERE id = ${id}
    `;
    return rows[0] ?? null;
  }

  async retract(id: number, reason?: string): Promise<{ ok: boolean; revoked_at: string }> {
    const rows = await this.deps.db<{ revoked_at: string }[]>`
      UPDATE memory_chunk
         SET revoked_at = now(),
             metadata   = metadata || ${this.deps.db.json({ retraction_reason: reason ?? null })}
       WHERE id = ${id}
         AND revoked_at IS NULL
       RETURNING revoked_at::text AS revoked_at
    `;
    if (rows.length === 0) {
      return { ok: false, revoked_at: '' };
    }
    return { ok: true, revoked_at: rows[0]!.revoked_at };
  }

  async health(): Promise<{ ok: boolean; db_ok: boolean; embed_ok: boolean; error?: string }> {
    let db_ok = false;
    try {
      const rows = await this.deps.db<{ ok: number }[]>`SELECT 1 AS ok`;
      db_ok = rows[0]?.ok === 1;
    } catch {
      db_ok = false;
    }
    const embed_health = await this.deps.embed.health();
    return {
      ok: db_ok && embed_health.ok,
      db_ok,
      embed_ok: embed_health.ok,
      error: db_ok && embed_health.ok ? undefined : (embed_health.error ?? 'db_or_embed_down'),
    };
  }
}
```

- [ ] **Step 2: Run unit tests, expect green**

```bash
bun test apps/api/test/unit/kb/service.test.ts 2>&1 | tail -15
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/kb/service.ts
git commit -m "feat(kb): implement KbService (ingest/search/getChunk/retract/health)

- ingest: embed each body, upsert on (source,external_id,body_hash) with
  body_hash from sha256(body). Idempotent re-ingest of same content.
- search: embed query, cosine top-k with optional scope/source filter,
  filter by min_similarity client-side after SQL LIMIT.
- getChunk: simple SELECT by id (no revoked filter — let caller decide).
- retract: soft delete by setting revoked_at and merging reason into
  metadata; returns ok=false if already revoked or row missing.
- health: SELECT 1 + embed sidecar /health probe."
```

---

## Task 5: Routes module + /health (with integration test)

**Files:**
- Create: `apps/api/src/kb/_helpers.ts`
- Create: `apps/api/src/kb/routes/health.ts`
- Create: `apps/api/src/kb/routes/index.ts`
- Create: `apps/api/test/integration/kb/routes.test.ts`

- [ ] **Step 1: Add error helpers**

Create `apps/api/src/kb/_helpers.ts`:

```typescript
import type { Context } from 'hono';
import { ZodError } from 'zod';

export class KbError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly httpStatus: number = 400,
  ) {
    super(message);
  }
}

export function handleError(c: Context, err: unknown): Response {
  if (err instanceof KbError) {
    return c.json({ error: err.code, message: err.message }, err.httpStatus as any);
  }
  if (err instanceof ZodError) {
    return c.json(
      { error: 'BAD_REQUEST', message: 'validation failed', issues: err.flatten() },
      400,
    );
  }
  const message = err instanceof Error ? err.message : String(err);
  console.error('[kb] unexpected error:', message);
  return c.json({ error: 'INTERNAL', message }, 500);
}
```

- [ ] **Step 2: Add /health mount**

Create `apps/api/src/kb/routes/health.ts`:

```typescript
import type { Hono } from 'hono';
import type { KbService } from '../service';
import { handleError } from '../_helpers';

export function mountHealth(router: Hono, service: KbService): void {
  router.get('/health', async (c) => {
    try {
      const h = await service.health();
      return c.json(h, h.ok ? 200 : 503);
    } catch (e) {
      return handleError(c, e);
    }
  });
}
```

- [ ] **Step 3: Add the router factory**

Create `apps/api/src/kb/routes/index.ts`:

```typescript
import { Hono } from 'hono';
import type { Db } from '../../db/client';
import type { EmbedClient } from '../embed-client';
import { KbService } from '../service';
import { bearerAuth } from './auth';
import { mountHealth } from './health';

export interface CreateKbRouterDeps {
  db: Db | any;
  embed: EmbedClient;
}

export function createKbRouter(deps: CreateKbRouterDeps): Hono {
  const service = new KbService(deps);
  const router = new Hono();

  router.use('*', bearerAuth);
  mountHealth(router, service);

  // ingest/search/chunks mounted in subsequent tasks.
  return router;
}
```

- [ ] **Step 4: Write integration test for /health (opt-in via env)**

Create `apps/api/test/integration/kb/routes.test.ts`:

```typescript
/**
 * KB routes integration test. Hits a REAL Postgres (DATABASE_URL) but uses
 * a stub EmbedClient so we don't need the Python sidecar running.
 *
 * Opt-in: set KB_INTEGRATION_TESTS=1 in env before `bun test`. The whole
 * file is skipped otherwise. The local Postgres MUST have the pgvector
 * extension installed and the memory_chunk migration applied (i.e. batch 1
 * has run locally).
 */
import { describe, it, expect, beforeAll, afterAll } from 'bun:test';
import { createDbClient, closeDb } from '../../../src/db/client';
import { createKbRouter } from '../../../src/kb/routes';
import type { EmbedClient } from '../../../src/kb/embed-client';

const RUN = process.env.KB_INTEGRATION_TESTS === '1';
const DATABASE_URL =
  process.env.DATABASE_URL ??
  'postgres://jirafetch:jirafetch@localhost:5433/jirafetch';
const AUTH = 'Bearer test-integration-key';

// Stub embed client: deterministic 768-dim vector with the first slot
// derived from the input text length, so different inputs get different
// vectors and ANN ordering is observable in tests.
function makeStubEmbed(): EmbedClient {
  return {
    async embed(text: string): Promise<number[]> {
      const vec = Array(768).fill(0.001);
      vec[0] = Math.min(1, text.length / 100);
      return vec;
    },
    async health() {
      return { ok: true, model: 'stub', dim: 768 };
    },
  };
}

describe('KB routes integration', () => {
  if (!RUN) {
    it.skip('KB integration tests opted out (set KB_INTEGRATION_TESTS=1)', () => {});
    return;
  }

  process.env.KB_API_KEY = 'test-integration-key';
  const db = createDbClient({ url: DATABASE_URL });
  const router = createKbRouter({ db, embed: makeStubEmbed() });

  beforeAll(async () => {
    // Sanity: extension + table must exist (batch 1).
    await db`CREATE EXTENSION IF NOT EXISTS vector`;
    await db`SELECT 1 FROM memory_chunk LIMIT 1`.catch(() => {
      throw new Error(
        'memory_chunk table not found — run `bun db:migrate` first (batch 1 migration).',
      );
    });
  });

  afterAll(async () => {
    await db`DELETE FROM memory_chunk WHERE source = 'test-integration'`;
    await closeDb(db);
  });

  it('GET /health returns 200 when DB + (stub) embed are healthy', async () => {
    const res = await router.fetch(
      new Request('http://x/health', { headers: { Authorization: AUTH } }),
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.db_ok).toBe(true);
    expect(body.embed_ok).toBe(true);
  });

  it('GET /health returns 401 without bearer', async () => {
    const res = await router.fetch(new Request('http://x/health'));
    expect(res.status).toBe(401);
  });
});
```

- [ ] **Step 5: Run unit tests (still green) + run integration tests (skipped by default)**

```bash
bun test apps/api/test/unit/kb 2>&1 | tail -10
# expect: all green

bun test apps/api/test/integration/kb 2>&1 | tail -10
# expect: 1 skipped test, no failures

# Then opt-in once locally (requires local Postgres + pgvector + batch-1 migration applied locally)
KB_INTEGRATION_TESTS=1 bun test apps/api/test/integration/kb 2>&1 | tail -10
# expect: 2 tests pass (health-ok, health-401)
```

If the opt-in run fails because the local Postgres lacks pgvector or the migration: install pgvector locally (`sudo apt-get install -y postgresql-XX-pgvector`) and run `cd apps/api && bun db:migrate`, then retry. If you can't run the opt-in suite locally, note that in your commit message and rely on the prod smoke for verification.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/kb/_helpers.ts apps/api/src/kb/routes/health.ts \
        apps/api/src/kb/routes/index.ts apps/api/test/integration/kb/routes.test.ts
git commit -m "feat(kb): createKbRouter factory + /health route + integration test

createKbRouter wires KbService with deps and mounts the bearer middleware
on every route. /health returns 200 when both DB and embed sidecar respond,
503 otherwise. Integration test is opt-in via KB_INTEGRATION_TESTS=1 so
'bun test' stays fast on dev workstations without pgvector installed."
```

---

## Task 6: Ingest + Search routes

**Files:**
- Create: `apps/api/src/kb/routes/ingest.ts`
- Create: `apps/api/src/kb/routes/search.ts`
- Modify: `apps/api/src/kb/routes/index.ts`
- Modify: `apps/api/test/integration/kb/routes.test.ts`

- [ ] **Step 1: Add /ingest mount**

Create `apps/api/src/kb/routes/ingest.ts`:

```typescript
import type { Hono } from 'hono';
import type { KbService } from '../service';
import { IngestRequestSchema } from '../types';
import { handleError } from '../_helpers';

export function mountIngest(router: Hono, service: KbService): void {
  router.post('/ingest', async (c) => {
    try {
      const raw = await c.req.json();
      const req = IngestRequestSchema.parse(raw);
      const result = await service.ingest(req);
      return c.json(result, 200);
    } catch (e) {
      return handleError(c, e);
    }
  });
}
```

- [ ] **Step 2: Add /search mount**

Create `apps/api/src/kb/routes/search.ts`:

```typescript
import type { Hono } from 'hono';
import type { KbService } from '../service';
import { SearchRequestSchema } from '../types';
import { handleError } from '../_helpers';

export function mountSearch(router: Hono, service: KbService): void {
  router.post('/search', async (c) => {
    try {
      const raw = await c.req.json();
      const req = SearchRequestSchema.parse(raw);
      const results = await service.search(req);
      return c.json({ results }, 200);
    } catch (e) {
      return handleError(c, e);
    }
  });
}
```

- [ ] **Step 3: Wire them into the router factory**

Replace `apps/api/src/kb/routes/index.ts`:

```typescript
import { Hono } from 'hono';
import type { Db } from '../../db/client';
import type { EmbedClient } from '../embed-client';
import { KbService } from '../service';
import { bearerAuth } from './auth';
import { mountHealth } from './health';
import { mountIngest } from './ingest';
import { mountSearch } from './search';

export interface CreateKbRouterDeps {
  db: Db | any;
  embed: EmbedClient;
}

export function createKbRouter(deps: CreateKbRouterDeps): Hono {
  const service = new KbService(deps);
  const router = new Hono();

  router.use('*', bearerAuth);
  mountHealth(router, service);
  mountIngest(router, service);
  mountSearch(router, service);

  // chunks mounted in the next task.
  return router;
}
```

- [ ] **Step 4: Extend integration test with ingest + search round-trip**

Append to the `describe('KB routes integration', ...)` block in `apps/api/test/integration/kb/routes.test.ts`, after the existing 2 tests:

```typescript
  it('POST /ingest upserts a row and POST /search finds it', async () => {
    const ingestRes = await router.fetch(
      new Request('http://x/ingest', {
        method: 'POST',
        headers: { Authorization: AUTH, 'content-type': 'application/json' },
        body: JSON.stringify({
          chunks: [
            {
              source: 'test-integration',
              scope: 'test-integration',
              external_id: `T6-${Date.now()}`,
              title: 'integration sentinel',
              body: 'monsoon rains damage rice variety RD43 in lowland fields',
              metadata: { tag: 'batch-2-smoke' },
            },
          ],
        }),
      }),
    );
    expect(ingestRes.status).toBe(200);
    const ingestBody = await ingestRes.json();
    expect(ingestBody.upserted).toHaveLength(1);

    const searchRes = await router.fetch(
      new Request('http://x/search', {
        method: 'POST',
        headers: { Authorization: AUTH, 'content-type': 'application/json' },
        body: JSON.stringify({
          query: 'rice in monsoon',
          scope: 'test-integration',
          top_k: 5,
        }),
      }),
    );
    expect(searchRes.status).toBe(200);
    const searchBody = await searchRes.json();
    expect(searchBody.results.length).toBeGreaterThanOrEqual(1);
    expect(
      searchBody.results.some((r: any) => r.external_id === ingestBody.upserted[0].external_id),
    ).toBe(true);
  });

  it('POST /search returns 400 on empty query', async () => {
    const res = await router.fetch(
      new Request('http://x/search', {
        method: 'POST',
        headers: { Authorization: AUTH, 'content-type': 'application/json' },
        body: JSON.stringify({ query: '' }),
      }),
    );
    expect(res.status).toBe(400);
  });
```

- [ ] **Step 5: Run unit + integration tests**

```bash
bun test apps/api/test/unit/kb 2>&1 | tail -10
# expect: all green

KB_INTEGRATION_TESTS=1 bun test apps/api/test/integration/kb 2>&1 | tail -15
# expect: 4 tests pass (health-ok, health-401, ingest+search, search-empty)
# OR fail with a clear pgvector/migration error if local DB not ready
```

If you can't run integration locally, note that you ran unit tests only.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/kb/routes/ingest.ts apps/api/src/kb/routes/search.ts \
        apps/api/src/kb/routes/index.ts apps/api/test/integration/kb/routes.test.ts
git commit -m "feat(kb): /ingest + /search routes

POST /ingest: validates IngestRequest Zod schema and delegates to KbService.
POST /search: returns {results: SearchResult[]}. Validation errors return
400 with a flattened ZodError. Integration test covers full round-trip
(ingest then search-finds-it) and a 400 path."
```

---

## Task 7: GET + DELETE /chunks/:id

**Files:**
- Create: `apps/api/src/kb/routes/chunks.ts`
- Modify: `apps/api/src/kb/routes/index.ts`
- Modify: `apps/api/test/integration/kb/routes.test.ts`

- [ ] **Step 1: Add chunks mount**

Create `apps/api/src/kb/routes/chunks.ts`:

```typescript
import type { Hono } from 'hono';
import type { KbService } from '../service';
import { RetractRequestSchema } from '../types';
import { handleError, KbError } from '../_helpers';

export function mountChunks(router: Hono, service: KbService): void {
  router.get('/chunks/:id', async (c) => {
    try {
      const id = Number(c.req.param('id'));
      if (!Number.isInteger(id) || id <= 0) {
        throw new KbError('BAD_REQUEST', 'id must be a positive integer', 400);
      }
      const chunk = await service.getChunk(id);
      if (!chunk) {
        return c.json({ error: 'NOT_FOUND', message: `chunk ${id} not found` }, 404);
      }
      return c.json(chunk, 200);
    } catch (e) {
      return handleError(c, e);
    }
  });

  router.delete('/chunks/:id', async (c) => {
    try {
      const id = Number(c.req.param('id'));
      if (!Number.isInteger(id) || id <= 0) {
        throw new KbError('BAD_REQUEST', 'id must be a positive integer', 400);
      }
      // body is optional — only carries an optional reason
      let req = { reason: undefined } as { reason?: string };
      const raw = await c.req.text();
      if (raw && raw.trim()) req = RetractRequestSchema.parse(JSON.parse(raw));

      const result = await service.retract(id, req.reason);
      if (!result.ok) {
        return c.json(
          { error: 'NOT_FOUND_OR_ALREADY_REVOKED', message: `chunk ${id} not found or already revoked` },
          404,
        );
      }
      return c.json({ ok: true, revoked_at: result.revoked_at }, 200);
    } catch (e) {
      return handleError(c, e);
    }
  });
}
```

- [ ] **Step 2: Wire into the router factory**

Replace `apps/api/src/kb/routes/index.ts`:

```typescript
import { Hono } from 'hono';
import type { Db } from '../../db/client';
import type { EmbedClient } from '../embed-client';
import { KbService } from '../service';
import { bearerAuth } from './auth';
import { mountHealth } from './health';
import { mountIngest } from './ingest';
import { mountSearch } from './search';
import { mountChunks } from './chunks';

export interface CreateKbRouterDeps {
  db: Db | any;
  embed: EmbedClient;
}

export function createKbRouter(deps: CreateKbRouterDeps): Hono {
  const service = new KbService(deps);
  const router = new Hono();

  router.use('*', bearerAuth);
  mountHealth(router, service);
  mountIngest(router, service);
  mountSearch(router, service);
  mountChunks(router, service);

  return router;
}
```

- [ ] **Step 3: Extend integration test for chunks GET + DELETE**

Append to the `describe('KB routes integration', ...)` block in `apps/api/test/integration/kb/routes.test.ts`:

```typescript
  it('GET /chunks/:id returns the chunk; DELETE soft-retracts it', async () => {
    const ext = `T7-${Date.now()}`;
    // Ingest a fresh chunk to retrieve
    const ingestRes = await router.fetch(
      new Request('http://x/ingest', {
        method: 'POST',
        headers: { Authorization: AUTH, 'content-type': 'application/json' },
        body: JSON.stringify({
          chunks: [
            {
              source: 'test-integration',
              scope: 'test-integration',
              external_id: ext,
              title: 'T7',
              body: 'chunk-id round-trip',
              metadata: {},
            },
          ],
        }),
      }),
    );
    const { upserted } = await ingestRes.json();
    const id = upserted[0].id;

    // GET
    const getRes = await router.fetch(
      new Request(`http://x/chunks/${id}`, { headers: { Authorization: AUTH } }),
    );
    expect(getRes.status).toBe(200);
    const got = await getRes.json();
    expect(got.id).toBe(id);
    expect(got.external_id).toBe(ext);
    expect(got.revoked_at).toBeNull();

    // DELETE with reason
    const delRes = await router.fetch(
      new Request(`http://x/chunks/${id}`, {
        method: 'DELETE',
        headers: { Authorization: AUTH, 'content-type': 'application/json' },
        body: JSON.stringify({ reason: 'integration cleanup' }),
      }),
    );
    expect(delRes.status).toBe(200);
    const delBody = await delRes.json();
    expect(delBody.ok).toBe(true);

    // GET again — chunk should still exist (soft delete) with revoked_at set
    const getAgain = await router.fetch(
      new Request(`http://x/chunks/${id}`, { headers: { Authorization: AUTH } }),
    );
    expect(getAgain.status).toBe(200);
    const stillThere = await getAgain.json();
    expect(stillThere.revoked_at).not.toBeNull();
    expect(stillThere.metadata.retraction_reason).toBe('integration cleanup');

    // Second DELETE should 404 (already revoked)
    const delAgain = await router.fetch(
      new Request(`http://x/chunks/${id}`, {
        method: 'DELETE',
        headers: { Authorization: AUTH },
      }),
    );
    expect(delAgain.status).toBe(404);
  });

  it('GET /chunks/abc returns 400 for non-numeric id', async () => {
    const res = await router.fetch(
      new Request('http://x/chunks/abc', { headers: { Authorization: AUTH } }),
    );
    expect(res.status).toBe(400);
  });

  it('GET /chunks/99999999 returns 404 for missing id', async () => {
    const res = await router.fetch(
      new Request('http://x/chunks/99999999', { headers: { Authorization: AUTH } }),
    );
    expect(res.status).toBe(404);
  });
```

- [ ] **Step 4: Run tests**

```bash
bun test apps/api/test/unit/kb 2>&1 | tail -10
# expect: all green

KB_INTEGRATION_TESTS=1 bun test apps/api/test/integration/kb 2>&1 | tail -15
# expect: 7 tests pass total
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/kb/routes/chunks.ts apps/api/src/kb/routes/index.ts \
        apps/api/test/integration/kb/routes.test.ts
git commit -m "feat(kb): GET + DELETE /chunks/:id routes

GET returns the row including revoked_at. DELETE soft-retracts: sets
revoked_at=now() and merges {retraction_reason: ...} into metadata.
Second DELETE on an already-revoked row returns 404 (Nothing-is-Deleted
principle — the row stays, but the verb is no longer applicable)."
```

---

## Task 8: Mount on the main Hono app + push + PR

**Files:**
- Modify: `apps/api/src/index.ts`

- [ ] **Step 1: Wire `createKbRouter` into the main app**

Add to `apps/api/src/index.ts`. Find the existing imports block near the top and the existing `app.route(...)` calls:

```typescript
// Add to the imports block (alongside other route imports)
import { createKbRouter } from './kb/routes';
import { createDbClient } from './db/client';
import { HttpEmbedClient } from './kb/embed-client';
```

Then, after the existing `app.route('/api/claude-auth', claudeAuthRouter);` line (find the existing block of `app.route(...)` calls around line 53-56 and add right after), insert:

```typescript
// --- Shared memory KB (batch 2) ---------------------------------------
// Dedicated postgres client so the KB feature owns its own pool. The
// embed client points to the loopback sidecar from batch 1; override via
// KB_EMBED_URL only for local dev against a remote/alternate embed service.
const kbDb = createDbClient();
const kbEmbed = new HttpEmbedClient(process.env.KB_EMBED_URL ?? 'http://127.0.0.1:3897');
app.route('/api/kb', createKbRouter({ db: kbDb, embed: kbEmbed }));
```

- [ ] **Step 2: Quick typecheck**

```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun tsc --noEmit 2>&1 | tail -20
```

Expected: no errors related to the new files. If there are pre-existing errors elsewhere, ignore those; focus on `kb/`-related lines.

- [ ] **Step 3: Run the full unit-test suite to make sure nothing regressed**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
bun test apps/api/test/unit 2>&1 | tail -10
```

Expected: all green (pre-existing + the new kb/ ones).

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/index.ts
git commit -m "feat(kb): mount /api/kb on the main Hono app

Constructs a dedicated Postgres client + an HttpEmbedClient pointing at
the batch-1 sidecar (override via KB_EMBED_URL). Routes are mounted under
/api/kb/*; nothing else in jira-fetch references them yet."
```

- [ ] **Step 5: Push the branch**

```bash
git push -u origin feat/shared-memory-kb-batch-2
```

- [ ] **Step 6: Open the PR**

```bash
gh pr create --base master --head feat/shared-memory-kb-batch-2 \
  --title "feat(memory-kb): batch 2 — HTTP API on Hono + bearer auth" \
  --body "$(cat <<'EOF'
## Summary

Adds the HTTP KB API at \`/api/kb/*\` inside the existing \`jirafetch-api\` Hono process:

- \`GET    /api/kb/health\` — probes DB + embed sidecar
- \`POST   /api/kb/search\` — semantic search (returns top-k cosine matches)
- \`POST   /api/kb/ingest\` — write chunks (server is dumb; no filtering)
- \`GET    /api/kb/chunks/:id\` — fetch single chunk
- \`DELETE /api/kb/chunks/:id\` — soft retract

All routes are bearer-auth-gated by a single shared key (\`KB_API_KEY\`) using constant-time compare. Service layer (\`KbService\`) is dependency-injected with a \`Db\` and an \`EmbedClient\` so unit tests can stub both.

## Out of scope (deferred)

- MCP server at \`/mcp\` (batch 3)
- \`/kb\` skill in artemis-oracle (batch 4)
- nginx changes / public exposure (batch 5)
- GH Actions deploy.yml extensions for the sidecar venv (batch 5)

## Spec / plan

- Spec: \`docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md\` (artemis-oracle)
- Batch-2 plan: \`docs/superpowers/plans/2026-05-21-shared-memory-kb-batch-2.md\` (artemis-oracle)

## Prerequisites that must already be true on the box

- Batch 1 merged + the pgvector apt package installed + \`bun db:migrate\` replayed so \`memory_chunk\` exists.
- The embed sidecar from batch 1 is provisioned and running at \`127.0.0.1:3897\`.

## Test plan

CI / pre-merge:
- [x] Unit tests for bearerAuth (6 cases) and KbService (10+ cases) — all green
- [x] Integration tests against a real local Postgres (opt-in via \`KB_INTEGRATION_TESTS=1\`) — 7 cases covering all 5 endpoints

Post-merge (manual prod smoke):
- [ ] Add \`KB_API_KEY=<random>\` and \`KB_EMBED_URL=http://127.0.0.1:3897\` to \`/home/runner/.env.d/jirafetch.sh\` on the EC2.
- [ ] \`systemctl restart jirafetch-api\` (deploy.yml will do this automatically if changed files match the trigger pattern; verify in journalctl).
- [ ] \`curl -H "Authorization: Bearer \$KB_API_KEY" http://localhost:6501/api/kb/health\` → \`{ok:true, db_ok:true, embed_ok:true}\`.
- [ ] Round-trip via curl: ingest a canary chunk \`source=smoke\`, search for it, retract it, verify with GET.
- [ ] \`DELETE FROM memory_chunk WHERE source = 'smoke';\` on the box.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Definition of Done

- [ ] PR merged to `master`; GH Actions deploy.yml runs cleanly (this PR doesn't change deploy.yml, but it does touch `apps/api/src/` which triggers a `jirafetch-api` restart)
- [ ] `KB_API_KEY` and `KB_EMBED_URL` set on the EC2 in `/home/runner/.env.d/jirafetch.sh`
- [ ] `curl -H "Authorization: Bearer <key>" http://<host>/api/kb/health` returns `{ok:true,db_ok:true,embed_ok:true}` (requires the batch-1 sidecar to be live)
- [ ] Ingest+search round-trip via curl works end-to-end against the prod box
- [ ] No errors in `journalctl -u jirafetch-api` related to the KB routes
- [ ] Sentinel rows (`source = 'smoke'`) cleaned up after smoke

When all of the above are checked, batch 2 is done and we can plan batch 3 (MCP server at `/mcp` reusing the same `KbService` and bearer middleware).

---

## Rollback

This batch only adds files in `apps/api/src/kb/*` and one small block in `apps/api/src/index.ts`. To roll back:

1. Revert the merge commit on `master`; GH Actions re-deploys and `/api/kb/*` returns 404 again. The rest of jira-fetch is untouched.
2. Leave `KB_API_KEY` and `KB_EMBED_URL` in `/home/runner/.env.d/jirafetch.sh` — they're harmless if the code is gone.
3. The `memory_chunk` table from batch 1 is unaffected; data (if any) persists.
