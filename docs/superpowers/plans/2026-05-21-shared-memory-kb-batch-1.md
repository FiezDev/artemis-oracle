# Shared Memory KB — Batch 1: Embed sidecar + DB migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the thinnest infrastructure slice — a Python FastAPI embed sidecar (mpnet 768-dim) running on the jira-fetch EC2 as a new systemd unit, plus the `memory_chunk` Postgres table behind a migration — without touching the running `jirafetch-api` process at all.

**Architecture:** Copy-adapt `riceguard-kb-api/embed-service.py` into a new `apps/memory-embed/` workspace inside `jira-fetch`. Sidecar binds to `127.0.0.1:3897` (no nginx exposure yet). The DB migration creates the `pgvector` extension and the `memory_chunk` table; jira-fetch's existing GH Actions pipeline auto-runs the migration on push to `master` because the file lands under `apps/api/db/migrations/`. Sidecar provisioning is manual one-time SSH on EC2 (venv setup + systemd install) — automating that lives in a later batch.

**Tech Stack:** Python 3 + FastAPI + uvicorn + sentence-transformers (`paraphrase-multilingual-mpnet-base-v2`), PostgreSQL + pgvector, systemd, Bun (existing migration runner).

**Spec:** `docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md`

**Out of scope for this batch (deferred):**
- HTTP KB routes inside `jirafetch-api` (§6.1 of spec)
- MCP server (§6.2)
- `/kb` skill in artemis-oracle (§8)
- nginx changes (§9.3)
- GH Actions deploy.yml extensions for the sidecar (§9.5) — manual provisioning for batch 1
- `KB_API_KEY` (no auth surface yet — sidecar only listens on loopback)

**Note on spec drift:** Spec §9.1 / §11 said migrations live in `db/migrations/`; the actual jira-fetch path is `apps/api/db/migrations/`. This plan uses the correct path. Spec §9.2 said `User=ec2-user`; actual EC2 user is `runner` and root is `/opt/jira-fetch/`. Both corrections are reflected below.

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/db/migrations/20260521000001_create_memory_chunk.sql` | create | Adds `pgvector` extension + `memory_chunk` table + indexes |
| `apps/memory-embed/requirements.txt` | create | Python deps for the sidecar |
| `apps/memory-embed/embed_service.py` | create | FastAPI app: `/health` + `/embed` |
| `apps/memory-embed/test_embed_service.py` | create | pytest tests (FastAPI TestClient, model mocked) |
| `apps/memory-embed/.env.example` | create | env template for the sidecar |
| `apps/memory-embed/README.md` | create | One-time provisioning steps + how to test locally |
| `deploy/memory-kb-embed.service` | create | systemd unit |

No edits to existing files in batch 1.

---

## Task 1: Create the `memory_chunk` migration

**Files:**
- Create: `apps/api/db/migrations/20260521000001_create_memory_chunk.sql`

- [ ] **Step 1: Write the migration file**

```sql
-- 20260521000001_create_memory_chunk.sql
-- Shared memory KB: pgvector extension + memory_chunk table
-- Spec: docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md §5
-- (Before running: confirm `apps/api/db/migrate.ts` either ignores SQL comments
--  or uses bare SQL — if it needs `-- up` / `-- down` markers, add them.)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_chunk (
  id            BIGSERIAL PRIMARY KEY,
  source        TEXT NOT NULL,
  scope         TEXT NOT NULL,
  external_id   TEXT NOT NULL,
  title         TEXT,
  body          TEXT NOT NULL,
  body_hash     TEXT NOT NULL,
  embedding     vector(768) NOT NULL,
  metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ,
  UNIQUE (source, external_id, body_hash)
);

CREATE INDEX memory_chunk_embedding_idx
  ON memory_chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX memory_chunk_scope_source_idx
  ON memory_chunk (scope, source) WHERE revoked_at IS NULL;

CREATE INDEX memory_chunk_metadata_idx
  ON memory_chunk USING GIN (metadata);
```

- [ ] **Step 2: Verify migration syntax with bun db:status (no-op check)**

Run from a local clone of jira-fetch with a dev DB available, or skip if no local DB is set up:

```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/api
bun db:status
```

Expected: lists `20260521000001_create_memory_chunk.sql` under "pending". If this fails because no local DB is available, skip this step — the migration will be validated when GH Actions applies it in Task 7.

- [ ] **Step 3: Commit**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
git checkout -b feat/shared-memory-kb-batch-1
git add apps/api/db/migrations/20260521000001_create_memory_chunk.sql
git commit -m "feat(memory-kb): add memory_chunk migration with pgvector

Adds pgvector extension and memory_chunk table per spec §5. Indexes:
ivfflat cosine on embedding, partial btree on (scope, source) WHERE
revoked_at IS NULL, GIN on metadata. Server-side schema is freeform
(no CHECK constraints) — all filtering lives in the /kb skill."
```

---

## Task 2: Scaffold the embed sidecar workspace

**Files:**
- Create: `apps/memory-embed/requirements.txt`
- Create: `apps/memory-embed/.env.example`
- Create: `apps/memory-embed/README.md`

- [ ] **Step 1: Create the requirements.txt**

```
# apps/memory-embed/requirements.txt
fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
sentence-transformers==3.3.1
# Test-only — numpy is pinned because tests fully mock sentence-transformers,
# so the transitive numpy from sentence-transformers isn't available.
pytest==8.3.3
httpx==0.27.2
numpy==2.1.3
```

- [ ] **Step 2: Create the .env.example**

```
# apps/memory-embed/.env.example
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
EMBED_HOST=127.0.0.1
EMBED_PORT=3897
```

- [ ] **Step 3: Create the README**

```markdown
# memory-embed

Python FastAPI sidecar for the shared-memory KB. Loads
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768-dim,
Thai-capable) once at startup and exposes:

- `GET  /health` — `{status, model, dim}`
- `POST /embed`  — `{text}` → `{embedding, dim, model}` (L2-normalised, cosine-friendly)

Listens on `127.0.0.1:3897` by default. Not reachable from the internet —
only the in-process jira-fetch API will call it.

## Local test

```bash
cd apps/memory-embed
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -v
```

## One-time EC2 provisioning

See `docs/superpowers/plans/2026-05-21-shared-memory-kb-batch-1.md` Task 6.
```

- [ ] **Step 4: Commit**

```bash
git add apps/memory-embed/requirements.txt apps/memory-embed/.env.example apps/memory-embed/README.md
git commit -m "feat(memory-embed): scaffold sidecar workspace

Empty Python workspace for the embedding sidecar (FastAPI + mpnet
768-dim). requirements pinned; README documents the local-test flow."
```

---

## Task 3: Write failing tests for the embed service

**Files:**
- Create: `apps/memory-embed/test_embed_service.py`

- [ ] **Step 1: Write the failing tests**

The tests mock `SentenceTransformer` so we don't load the 1GB model in CI. Tests cover `/health` shape, `/embed` happy path (returns 768-dim normalised vector), and request validation.

```python
# apps/memory-embed/test_embed_service.py
"""Tests for embed_service. The mpnet model is mocked to keep tests fast."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Build a TestClient with SentenceTransformer mocked before import."""
    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 768
    # encode() must return shape (N, 768) — we make it deterministic per call
    fake_model.encode.return_value = np.array(
        [[0.1] * 768], dtype=np.float32
    )

    fake_st_module = MagicMock()
    fake_st_module.SentenceTransformer.return_value = fake_model
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st_module)

    # Force re-import of the service under the mocked module
    sys.modules.pop("embed_service", None)
    import embed_service  # noqa: WPS433 — intentional in-test import

    return TestClient(embed_service.app)


def test_health_returns_model_and_dim(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["dim"] == 768
    assert "mpnet" in body["model"]  # current model name contains 'mpnet'


def test_embed_returns_768_dim_vector(client):
    resp = client.post("/embed", json={"text": "monsoon damages rice"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["dim"] == 768
    assert len(body["embedding"]) == 768
    assert all(isinstance(x, float) for x in body["embedding"])


def test_embed_rejects_empty_text(client):
    resp = client.post("/embed", json={"text": ""})
    assert resp.status_code == 422  # pydantic min_length=1


def test_embed_rejects_oversize_text(client):
    resp = client.post("/embed", json={"text": "x" * 2001})
    assert resp.status_code == 422  # pydantic max_length=2000


def test_embed_missing_field(client):
    resp = client.post("/embed", json={})
    assert resp.status_code == 422
```

- [ ] **Step 2: Set up a local venv and run the tests to see them fail**

```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/memory-embed
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -v
```

Expected: tests collected, all fail with `ModuleNotFoundError: No module named 'embed_service'` (or `ImportError`).

**Note:** `requirements.txt` already pins `numpy` in the test-only section, so no separate install is needed. If your `python3` is 3.14+ and `pip install` fails on `pydantic-core` (no wheels yet), retry with `python3.12 -m venv .venv` (or any 3.10-3.13).

- [ ] **Step 3: Commit (failing tests as documentation of contract)**

```bash
# Add .venv to .gitignore at workspace root if not already there
echo "apps/memory-embed/.venv/" >> /home/bjgdr/dev-personal/jira-fetch/.gitignore

git add apps/memory-embed/test_embed_service.py /home/bjgdr/dev-personal/jira-fetch/.gitignore
git commit -m "test(memory-embed): contract tests for /health and /embed

Tests mock SentenceTransformer so the 1GB model is not loaded in CI.
Covers shape of /health, happy path /embed (768-dim L2-normalised), and
pydantic validation (empty text, oversize, missing field). Currently
failing — implementation lands in the next commit."
```

---

## Task 4: Implement `embed_service.py` to pass the tests

**Files:**
- Create: `apps/memory-embed/embed_service.py`

- [ ] **Step 1: Write the minimal implementation**

Copy-adapted from `riceguard-kb-api/embed-service.py`. Changes from riceguard:
1. Hyphen → underscore in module name (Python imports need `embed_service`, not `embed-service`)
2. `print()` calls wrapped so import-time prints don't pollute pytest output (keep them — they go to journald in prod and stdout-buffered in tests)
3. Add `if __name__ == "__main__"` for `python embed_service.py` local runs

```python
#!/usr/bin/env python3
"""Shared-memory KB embedding sidecar — jira-fetch.

FastAPI service. Loads sentence-transformers/paraphrase-multilingual-mpnet-base-v2
(768-dim, Thai-capable) once at startup. Each /embed call returns a normalised
unit vector (cosine-friendly).

Run: uvicorn embed_service:app --host 127.0.0.1 --port 3897
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.environ.get(
    "EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)

print(f"Loading {MODEL_NAME}...", flush=True)
model = SentenceTransformer(MODEL_NAME)
DIM = model.get_sentence_embedding_dimension()
print(f"Model ready. Dim={DIM}", flush=True)

app = FastAPI(title="jira-fetch memory KB embed sidecar", version="0.1.0")


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim: int
    model: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_NAME, "dim": DIM}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vec = model.encode([req.text], normalize_embeddings=True)[0].tolist()
    return EmbedResponse(embedding=vec, dim=len(vec), model=MODEL_NAME)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("EMBED_HOST", "127.0.0.1"),
        port=int(os.environ.get("EMBED_PORT", "3897")),
    )
```

- [ ] **Step 2: Run the tests, expect all green**

```bash
cd /home/bjgdr/dev-personal/jira-fetch/apps/memory-embed
.venv/bin/pytest -v
```

Expected:
```
test_embed_service.py::test_health_returns_model_and_dim PASSED
test_embed_service.py::test_embed_returns_768_dim_vector PASSED
test_embed_service.py::test_embed_rejects_empty_text PASSED
test_embed_service.py::test_embed_rejects_oversize_text PASSED
test_embed_service.py::test_embed_missing_field PASSED
```

- [ ] **Step 3: Commit**

```bash
git add apps/memory-embed/embed_service.py
git commit -m "feat(memory-embed): implement /health and /embed

Loads mpnet (768-dim multilingual) at startup; /embed returns
L2-normalised vectors. EMBED_MODEL / EMBED_HOST / EMBED_PORT env-overridable.
Tests green."
```

---

## Task 5: Add the systemd unit

**Files:**
- Create: `deploy/memory-kb-embed.service`

- [ ] **Step 1: Write the systemd unit**

Differences from riceguard (whose box uses `ec2-user` + `/home/ec2-user/kb-api`): jira-fetch's box is `runner` + `/opt/jira-fetch`, with env files under `/home/runner/.env.d/`.

```ini
# deploy/memory-kb-embed.service
[Unit]
Description=jira-fetch memory KB embed sidecar (sentence-transformers mpnet)
After=network-online.target

[Service]
Type=simple
User=runner
WorkingDirectory=/opt/jira-fetch/apps/memory-embed
EnvironmentFile=-/home/runner/.env.d/memory-embed.sh
ExecStart=/opt/jira-fetch/apps/memory-embed/.venv/bin/uvicorn embed_service:app --host 127.0.0.1 --port 3897
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

The `-` prefix on `EnvironmentFile` means "ignore if missing" — so the unit starts even before the env file has been provisioned on the box.

- [ ] **Step 2: Commit**

```bash
git add deploy/memory-kb-embed.service
git commit -m "feat(memory-embed): systemd unit

User=runner (matches jirafetch-api convention), WorkingDirectory under
/opt/jira-fetch/apps/memory-embed, EnvironmentFile optional so the unit
can start before /home/runner/.env.d/memory-embed.sh exists."
```

---

## Task 6: One-time provision on EC2 + smoke test

This is manual SSH work. The commands assume the GH Actions deploy has *not yet* run (so the code isn't on the box). We do it in this order: open a PR, merge to master, let GH Actions rsync the files (which it does for ALL files under `/opt/jira-fetch/` since it's a `git reset --hard`), then SSH and provision Python.

- [ ] **Step 1: Push the branch and open a PR**

```bash
cd /home/bjgdr/dev-personal/jira-fetch
git push -u origin feat/shared-memory-kb-batch-1
gh pr create --base master --title "feat(memory-kb): batch 1 — embed sidecar + DB migration" \
  --body "$(cat <<'EOF'
## Summary
- Adds `pgvector` extension + `memory_chunk` table behind a migration (auto-applied by deploy.yml)
- Adds `apps/memory-embed/` Python FastAPI sidecar (mpnet 768-dim) + tests
- Adds `deploy/memory-kb-embed.service` systemd unit

## Out of scope (batch 1 only)
- Hono KB routes, MCP server, /kb skill, nginx changes, deploy.yml automation for the sidecar

## Spec
docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md

## Test plan
- [ ] CI: pytest green inside `apps/memory-embed/`
- [ ] Merge to master triggers deploy.yml; migration runs on the box
- [ ] One-time SSH provisioning of venv + systemd (see plan Task 6)
- [ ] Curl `http://127.0.0.1:3897/health` from the EC2 returns 200 with `dim=768`
- [ ] Curl `/embed` with sample text returns a 768-element vector
- [ ] `psql -c "\dt memory_chunk"` confirms the table exists

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Wait for the user to approve and merge. **Do not auto-merge.**

- [ ] **Step 2: After merge, confirm GH Actions deploy.yml ran cleanly**

In the GH Actions UI (or `gh run list -L 1 -w deploy.yml`), confirm:
- `bun db:migrate` step ran (file under `apps/api/db/migrations/` changed → trigger fires)
- Pipeline ended green
- External health check still passes

The deploy pipeline will **not** start the sidecar yet — it doesn't know how to provision Python venvs for `apps/memory-embed/`. That's the next step, done manually.

- [ ] **Step 3: SSH to the EC2 and provision the venv**

```bash
# from a workstation that has the EC2 SSH key
ssh -i /path/to/rice_guard.pem ubuntu@<TOOLS_EC2_HOST>

# on the box, become runner
sudo -iu runner

# build the venv (this downloads ~1GB of PyTorch — takes 2-5 min)
cd /opt/jira-fetch/apps/memory-embed
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# smoke the model load + embed in one shot (this loads the 1GB model — first run pulls weights from HuggingFace, takes ~1-3 min)
.venv/bin/python -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
v = m.encode(['monsoon rice variety'], normalize_embeddings=True)[0]
print('dim=', len(v), 'first 4 =', v[:4].tolist())
"
```

Expected:
```
dim= 768 first 4 = [0.0123..., -0.0456..., 0.0789..., -0.0987...]
```
(Exact values will differ.) If the print works, the model + venv are healthy.

- [ ] **Step 4: Install + enable + start the systemd unit (as root)**

```bash
# exit back to the ubuntu user (which has sudo)
exit

sudo cp /opt/jira-fetch/deploy/memory-kb-embed.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable memory-kb-embed
sudo systemctl start memory-kb-embed
sleep 30  # model load takes ~20-30s on first start (already cached from Step 3)
sudo systemctl status memory-kb-embed --no-pager
```

Expected: `active (running)` and recent journal lines show `Model ready. Dim=768`.

- [ ] **Step 5: Smoke `/health` + `/embed` from the box**

```bash
curl -fsS http://127.0.0.1:3897/health | jq
# expect: {"status":"ok","model":"sentence-transformers/paraphrase-multilingual-mpnet-base-v2","dim":768}

curl -fsS -X POST http://127.0.0.1:3897/embed \
  -H 'content-type: application/json' \
  -d '{"text":"riceguard variety RD43 lodges in monsoon"}' | jq '{dim, embedding_first_4: .embedding[:4]}'
# expect: {"dim":768, "embedding_first_4":[...4 floats...]}
```

If both succeed, the sidecar is live in prod (loopback-only, per design).

- [ ] **Step 6: Tail journal and confirm no errors**

```bash
sudo journalctl -u memory-kb-embed -n 50 --no-pager
```

Expected: `Model ready. Dim=768` line + two `INFO` lines from uvicorn for the smoke curls. No exceptions.

---

## Task 7: Confirm the migration applied + spot-check the schema

- [ ] **Step 1: Connect to the prod DB and verify the table + extension**

(From the EC2 box, using whatever psql wrapper jira-fetch already uses — `psql "$DATABASE_URL"` after sourcing `/home/runner/.env.d/jirafetch.sh`.)

```bash
sudo -iu runner
source /home/runner/.env.d/jirafetch.sh
psql "$DATABASE_URL" -c "\dx vector"
psql "$DATABASE_URL" -c "\d memory_chunk"
psql "$DATABASE_URL" -c "SELECT indexname FROM pg_indexes WHERE tablename = 'memory_chunk';"
```

Expected:
- `\dx vector` shows the extension present (any version ≥ 0.5.0).
- `\d memory_chunk` shows all 11 columns with the right types (including `embedding vector(768)`).
- The index query lists at least: `memory_chunk_pkey`, `memory_chunk_embedding_idx`, `memory_chunk_scope_source_idx`, `memory_chunk_metadata_idx`, plus the unique index for `(source, external_id, body_hash)`.

- [ ] **Step 2: Insert and retrieve a sentinel row end-to-end (sidecar + DB together)**

This validates the full data plane will work in batch 2. Get an embedding from the sidecar, write it to the table, read it back via cosine search.

```bash
# still on the box, as runner, with $DATABASE_URL sourced
VEC=$(curl -fsS -X POST http://127.0.0.1:3897/embed \
  -H 'content-type: application/json' \
  -d '{"text":"sentinel for batch-1 smoke"}' | jq -c '.embedding')

psql "$DATABASE_URL" <<SQL
INSERT INTO memory_chunk (source, scope, external_id, title, body, body_hash, embedding, metadata)
VALUES (
  'smoke', 'smoke', 'batch-1-sentinel', 'sentinel', 'sentinel for batch-1 smoke',
  'sha256:smoke', '$VEC'::vector(768), '{"smoke":true}'::jsonb
);
SELECT id, source, scope, external_id FROM memory_chunk WHERE source = 'smoke';
SQL
```

Expected: 1 row inserted, SELECT returns it.

- [ ] **Step 3: Cosine-search the sentinel back**

```bash
QUERY_VEC=$(curl -fsS -X POST http://127.0.0.1:3897/embed \
  -H 'content-type: application/json' \
  -d '{"text":"sentinel batch"}' | jq -c '.embedding')

psql "$DATABASE_URL" <<SQL
SELECT id, external_id, 1 - (embedding <=> '$QUERY_VEC'::vector(768)) AS similarity
  FROM memory_chunk
  WHERE source = 'smoke'
  ORDER BY embedding <=> '$QUERY_VEC'::vector(768)
  LIMIT 5;
SQL
```

Expected: the sentinel row at rank 1 with similarity > 0.6 (mpnet rates near-paraphrases highly).

- [ ] **Step 4: Clean up sentinel rows**

```bash
psql "$DATABASE_URL" -c "DELETE FROM memory_chunk WHERE source = 'smoke';"
```

Expected: `DELETE 1`.

- [ ] **Step 5: Final status — log batch-1 completion**

```bash
# back on your workstation
echo "Batch 1 complete: sidecar live on $TOOLS_EC2_HOST:3897 (loopback), memory_chunk table ready." \
  >> /home/bjgdr/oracle/artemis-oracle/ψ/memory/logs/2026-05-21-shared-memory-kb-batch-1-done.md
```

(Optional — just a note for `/recap`.)

---

## Definition of Done

- [ ] PR merged to `master`; GH Actions deploy green
- [ ] `psql \d memory_chunk` shows the table with `embedding vector(768)`
- [ ] `systemctl is-active memory-kb-embed` returns `active`
- [ ] `curl 127.0.0.1:3897/health` on the box returns `{"status":"ok","dim":768,...}`
- [ ] Insert+cosine-search round-trip works against the live DB + live sidecar
- [ ] Sentinel rows cleaned up
- [ ] No errors in `journalctl -u memory-kb-embed`

When all boxes above are checked, batch 1 is done and we can plan batch 2 (Hono service layer + HTTP KB routes + auth + tests).

---

## Rollback (if anything is broken at the end of Task 6/7)

1. `sudo systemctl stop memory-kb-embed && sudo systemctl disable memory-kb-embed` — sidecar is no longer running (the rest of jira-fetch is unaffected since nothing calls the sidecar yet).
2. If the migration is the problem: it's additive (extension + new table). Drop it with `psql "$DATABASE_URL" -c "DROP TABLE memory_chunk; DROP EXTENSION vector;"` then re-deploy with the migration file removed from the branch. **Do not** drop the extension if any other table on the box uses `vector`.
3. Revert the merge commit on master; GH Actions will re-run and the codebase returns to pre-batch-1 state.
