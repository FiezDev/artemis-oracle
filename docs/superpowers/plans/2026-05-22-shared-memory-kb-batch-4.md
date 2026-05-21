# Shared Memory KB — Batch 4: `/kb` curator skill (memory source)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the dev-facing `/kb` skill at `artemis-oracle/skills/kb/`. It runs inside a Claude Code session, scans the dev's local `ψ/memory/` files, applies a heuristic gate → secret scan → LLM judge → user approval pipeline, then calls the MCP `kb_ingest` tool (the live server we shipped in batch 3) to upload approved chunks. Also wraps `kb_search` / `kb_get` / `kb_retract` as friendlier subcommands. Memory source ONLY in this batch — Jira ingestion stays deferred.

**Architecture:** Skill is a directory at `artemis-oracle/skills/kb/` with `SKILL.md` (procedural body Claude follows) + small Python helpers in `scripts/` for the deterministic parts (state I/O, secret patterns, candidate collection from globs). Claude — running in-session — orchestrates the pipeline: invoke scripts for the deterministic gates, do the LLM judging itself, render the approval UI in the chat, then call the `kb_*` MCP tools already loaded in the session. Per-dev state lives in `~/.config/kb/` (config.json, state.json, token). Nothing about this skill is jira-fetch-specific — any artemis-oracle clone with the MCP server registered can use it.

**Tech Stack:** Python 3.10+ (matches the iso-doc-creator skill convention in this repo) for the deterministic scripts; pytest for unit tests; SKILL.md as the slash-command body. MCP tools (`mcp__jira-fetch-kb__kb_*` or whatever the dev's `~/.claude.json` names them) called from inside the Claude session — no SDK shipped in the skill itself.

**Spec:** `docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md` §8.

**Prerequisites:**
- Batches 1-3 deployed and verified (they are — `/mcp` smoke is green as of 2026-05-22).
- The dev running this skill has `mcpServers.jira-fetch-kb` configured in their `~/.claude.json` pointing at `http://43.208.150.191:6501/mcp` with their `KB_API_KEY` bearer.
- Python 3.10+ on the dev's workstation (every Mac/Linux box already has this; no venv needed for the helpers — they use only stdlib).

**Out of scope for this batch (deferred):**
- Jira source ingestion (will land in a follow-up — needs a "since-cursor" query against jira-fetch's Postgres OR a new API endpoint there).
- Public nginx exposure of `/mcp` + HTTPS (batch 5 — devs use plain HTTP via IP for now, behind their dev VPN or via SSH tunnel).
- GH Actions automation for the sidecar venv (batch 5).
- Auto-installing the skill into `~/.claude/skills/`; we document the symlink/install step in README, dev runs it once.
- Anything Jira-specific. **Memory source only in this batch.**

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `skills/kb/SKILL.md` | create | Slash-command body — frontmatter (name/description) + step-by-step procedure Claude follows for each subcommand |
| `skills/kb/README.md` | create | Human-facing install + usage doc (one-time `~/.config/kb/` setup, `~/.claude.json` MCP wiring, troubleshooting) |
| `skills/kb/config.example.json` | create | Template for `~/.config/kb/config.json` — allowlist, classifier threshold, secret-scan defaults |
| `skills/kb/secret-patterns.json` | create | Gitleaks-style regex set as JSON (AWS keys, GitHub PATs, Slack tokens, Firebase configs, JWT-shaped, `.env` high-entropy) |
| `skills/kb/scripts/kb_state.py` | create | Load/save `~/.config/kb/state.json`; cursor get/set; last-run summary append |
| `skills/kb/scripts/kb_secret_scan.py` | create | Apply patterns from `secret-patterns.json` + Shannon entropy on candidate bodies; CLI takes JSON-stdin, returns JSON-stdout with rejects |
| `skills/kb/scripts/kb_collect_memory.py` | create | Glob memory files modified since cursor; parse YAML frontmatter (`repo:`, `scope:`); emit candidates as JSON |
| `skills/kb/tests/test_kb_state.py` | create | pytest for state helpers |
| `skills/kb/tests/test_kb_secret_scan.py` | create | pytest for secret scanner (known-positive and known-negative cases) |
| `skills/kb/tests/test_kb_collect_memory.py` | create | pytest for memory collector (cursor + frontmatter filtering) |

All paths are relative to `/home/bjgdr/oracle/artemis-oracle/`. No changes to existing files.

---

## Task 1: Branch + scaffold the skill directory

**Files:**
- Create: `skills/kb/SKILL.md` (placeholder; filled in Task 5)
- Create: `skills/kb/README.md`
- Create: `skills/kb/config.example.json`
- Create: `skills/kb/secret-patterns.json`

- [ ] **Step 1: Create the feature branch**

```bash
cd /home/bjgdr/oracle/artemis-oracle
git fetch origin main 2>&1 | tail -3 || true
git checkout -b feat/kb-skill-batch-4 origin/main 2>/dev/null || git checkout -b feat/kb-skill-batch-4
```

(`artemis-oracle` may not have a remote tracking `origin/main` set up; falling back to a plain `git checkout -b` from current HEAD is fine — this repo is the user's personal `psi/` monorepo, not a multi-dev codebase.)

- [ ] **Step 2: Write a placeholder `SKILL.md`**

`skills/kb/SKILL.md`:

```markdown
---
name: kb
description: Shared-memory KB curator. Use this skill when the user invokes /kb scan, /kb search, /kb show, /kb retract, /kb status, /kb list, or /kb config — or when they ask to push curated knowledge into the shared memory store, or to search/retract chunks already in it. Wraps the jira-fetch-kb MCP server (kb_health, kb_search, kb_get, kb_ingest, kb_retract).
---

# /kb — Shared Memory KB curator (placeholder)

(Task 5 fills this in.)
```

The frontmatter `description` is what Claude reads to decide whether the skill is relevant — keep it crisp and triggerable on the natural ways a dev would ask.

- [ ] **Step 3: Write `config.example.json`**

`skills/kb/config.example.json`:

```json
{
  "api_url": "http://43.208.150.191:6501",
  "mcp_server_alias": "jira-fetch-kb",
  "token_ref": "file:~/.config/kb/token",
  "allowlist": {
    "memory_globs": [
      "ψ/memory/learnings/**/*.md",
      "ψ/memory/retrospectives/**/*.md"
    ],
    "scope_tags": {
      "mobileai": ["mobileai", "rice-guard", "ric-"],
      "gothailand": ["gothailand", "go-thailand"]
    }
  },
  "classifier": {
    "threshold": 0.7
  },
  "secret_scan": {
    "action": "reject",
    "extra_patterns": []
  },
  "ingest": {
    "max_chunks_per_run": 50
  }
}
```

Notes baked into this default:
- `api_url` is informational only; the skill calls MCP tools, not HTTP. Kept for the rare "let me curl this for debugging" moment.
- `mcp_server_alias` tells the skill which MCP server name to look for in the session's tool list (`mcp__<alias>__kb_*`).
- `scope_tags` is the heuristic: if a memory file's frontmatter has `repo: x` OR its body case-insensitively matches any tag string under that scope, the chunk is in scope.
- `classifier.threshold` is the cutoff for "benefits other devs?" — Claude does the judging in-session.
- `secret_scan.action: reject` matches spec §8 (reject, not redact).

- [ ] **Step 4: Write `secret-patterns.json`**

`skills/kb/secret-patterns.json`:

```json
{
  "patterns": [
    { "name": "aws_access_key_id", "regex": "AKIA[0-9A-Z]{16}" },
    { "name": "aws_secret_access_key", "regex": "(?i)aws.{0,20}?(secret|key).{0,20}?['\"\\s:=]+[A-Za-z0-9/+=]{40}" },
    { "name": "github_pat_classic", "regex": "ghp_[A-Za-z0-9]{36,}" },
    { "name": "github_pat_fine_grained", "regex": "github_pat_[A-Za-z0-9_]{82}" },
    { "name": "github_oauth", "regex": "gho_[A-Za-z0-9]{36,}" },
    { "name": "github_user_token", "regex": "ghu_[A-Za-z0-9]{36,}" },
    { "name": "github_server_token", "regex": "ghs_[A-Za-z0-9]{36,}" },
    { "name": "slack_token", "regex": "xox[abprs]-[A-Za-z0-9-]{10,}" },
    { "name": "firebase_api_key", "regex": "AIza[0-9A-Za-z_-]{35}" },
    { "name": "jwt_shaped", "regex": "eyJ[A-Za-z0-9_=-]{10,}\\.eyJ[A-Za-z0-9_=-]{10,}\\.[A-Za-z0-9_=.+/-]{10,}" },
    { "name": "private_key_pem", "regex": "-----BEGIN [A-Z ]*PRIVATE KEY[A-Z ]*-----" },
    { "name": "stripe_live_key", "regex": "sk_live_[A-Za-z0-9]{20,}" },
    { "name": "openai_api_key", "regex": "sk-[A-Za-z0-9]{20,}" },
    { "name": "anthropic_api_key", "regex": "sk-ant-[A-Za-z0-9_-]{20,}" }
  ],
  "entropy": {
    "min_length_to_check": 24,
    "shannon_threshold": 4.0
  },
  "envstyle": {
    "key_value_regex": "[A-Z][A-Z0-9_]{4,}\\s*[:=]\\s*['\"]?([A-Za-z0-9/+=_-]{20,})['\"]?",
    "shannon_threshold": 3.5
  }
}
```

- [ ] **Step 5: Write `README.md`**

`skills/kb/README.md`:

````markdown
# /kb — Shared Memory KB curator

Push curated knowledge to and query the team's shared memory store from inside any Claude Code session.

## One-time setup (per developer workstation)

### 1. Install the skill into Claude Code

```bash
# Adjust target dir if your Claude Code installation uses a different skills path.
mkdir -p ~/.claude/skills
ln -s /home/bjgdr/oracle/artemis-oracle/skills/kb ~/.claude/skills/kb
```

(Alternative: this repo may already be auto-loaded by `oracle-skills` — check with `oracle-skills list -g | grep kb`. If it appears, skip the symlink.)

### 2. Register the MCP server in Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "jira-fetch-kb": {
      "type": "http",
      "url": "http://43.208.150.191:6501/mcp",
      "headers": { "Authorization": "Bearer <KB_API_KEY>" }
    }
  }
}
```

Get `KB_API_KEY` from the team's secret store. Restart Claude Code so the MCP server is loaded.

### 3. Create the per-dev config

```bash
mkdir -p ~/.config/kb
cp /home/bjgdr/oracle/artemis-oracle/skills/kb/config.example.json ~/.config/kb/config.json
# Optional: edit the allowlist + thresholds for your workflow.
```

### 4. Verify

In a Claude Code session, invoke `/kb status`. You should see the MCP server reachable and the local config + state paths reported.

## Subcommands

| Command | Purpose |
|---|---|
| `/kb scan [--since YYYY-MM-DD] [--scope mobileai\|gothailand] [--dry-run]` | The curator pipeline. Collects memory files modified since the cursor → heuristic gate → secret-scan reject → LLM judge "benefits other devs?" → user approval → MCP `kb_ingest`. |
| `/kb search <query> [--scope …] [--top-k 5]` | Wraps MCP `kb_search`. Prints results table. |
| `/kb show <id>` | Wraps MCP `kb_get`. Prints full chunk. |
| `/kb retract <id> [--reason …]` | Wraps MCP `kb_retract`. Confirms before calling. |
| `/kb status` | Local state cursors + MCP `kb_health`. |
| `/kb list [--mine] [--since …] [--source …] [--scope …]` | Local report from `~/.config/kb/state.json` of recent uploads. |
| `/kb config [--show \| --edit]` | Inspect or open `~/.config/kb/config.json`. |

## Files this skill writes

- `~/.config/kb/state.json` — cursors per source + last-run summary.

That's it. The skill never writes to your repo working tree.
````

- [ ] **Step 6: Commit**

```bash
cd /home/bjgdr/oracle/artemis-oracle
git add skills/kb/SKILL.md skills/kb/README.md skills/kb/config.example.json skills/kb/secret-patterns.json
git commit -m "feat(kb-skill): scaffold skill directory + config template + secret patterns

Skeleton SKILL.md (frontmatter only — Task 5 fills in the body), the
config example dev clones to ~/.config/kb/config.json, a gitleaks-style
secret-pattern set, and a README walking through the one-time install."
```

---

## Task 2: `kb_state.py` — cursor + run-summary helpers (TDD)

**Files:**
- Create: `skills/kb/scripts/kb_state.py`
- Create: `skills/kb/tests/test_kb_state.py`

State file shape:

```json
{
  "cursors": {
    "memory": "2026-05-22T00:00:00Z"
  },
  "runs": [
    {
      "ts": "2026-05-22T12:00:00Z",
      "source": "memory",
      "scope": "mobileai",
      "ingested": 3,
      "secret_rejected": 1,
      "classifier_rejected": 2,
      "user_skipped": 0
    }
  ]
}
```

- [ ] **Step 1: Write the failing tests**

`skills/kb/tests/test_kb_state.py`:

```python
"""Tests for kb_state. Uses a temp HOME so the real ~/.config/kb is untouched."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _import_module():
    # Local import so the HOME monkeypatch lands before the module reads env.
    import importlib
    import sys
    sys.modules.pop("kb_state", None)
    spec = importlib.util.spec_from_file_location(
        "kb_state",
        str(Path(__file__).parent.parent / "scripts" / "kb_state.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_default_state_file_path_uses_home(tmp_home):
    m = _import_module()
    p = m.state_file_path()
    assert str(p).startswith(str(tmp_home))
    assert p.name == "state.json"
    assert p.parent.name == "kb"


def test_load_state_when_file_missing_returns_empty_skeleton(tmp_home):
    m = _import_module()
    state = m.load_state()
    assert state == {"cursors": {}, "runs": []}


def test_save_then_load_roundtrip(tmp_home):
    m = _import_module()
    m.save_state({"cursors": {"memory": "2026-05-22T00:00:00Z"}, "runs": []})
    state = m.load_state()
    assert state["cursors"]["memory"] == "2026-05-22T00:00:00Z"


def test_get_cursor_default_when_unset(tmp_home):
    m = _import_module()
    assert m.get_cursor("memory") is None


def test_set_cursor_persists(tmp_home):
    m = _import_module()
    m.set_cursor("memory", "2026-05-22T00:00:00Z")
    assert m.get_cursor("memory") == "2026-05-22T00:00:00Z"


def test_record_run_appends_entry(tmp_home):
    m = _import_module()
    m.record_run({
        "ts": "2026-05-22T12:00:00Z",
        "source": "memory",
        "scope": "mobileai",
        "ingested": 3,
        "secret_rejected": 1,
        "classifier_rejected": 2,
        "user_skipped": 0,
    })
    state = m.load_state()
    assert len(state["runs"]) == 1
    assert state["runs"][0]["ingested"] == 3


def test_record_run_caps_history_at_50_entries(tmp_home):
    m = _import_module()
    for i in range(60):
        m.record_run({"ts": f"2026-05-22T12:00:{i:02d}Z", "source": "memory", "scope": "mobileai", "ingested": i, "secret_rejected": 0, "classifier_rejected": 0, "user_skipped": 0})
    state = m.load_state()
    assert len(state["runs"]) == 50
    # FIFO trim — oldest entries dropped first
    assert state["runs"][0]["ingested"] == 10
    assert state["runs"][-1]["ingested"] == 59
```

- [ ] **Step 2: Run the tests, expect ImportError / ModuleNotFoundError**

```bash
cd /home/bjgdr/oracle/artemis-oracle
python3 -m pytest skills/kb/tests/test_kb_state.py -v 2>&1 | tail -10
```

Expected: all 7 tests fail because `kb_state.py` doesn't exist yet.

- [ ] **Step 3: Implement `kb_state.py`**

`skills/kb/scripts/kb_state.py`:

```python
"""State file management for the /kb skill.

Stores cursors per source + a rolling buffer of the last 50 run summaries
at ~/.config/kb/state.json. Pure stdlib — no extra deps for the dev.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

MAX_RUN_HISTORY = 50


def _config_dir() -> Path:
    return Path(os.path.expanduser("~")) / ".config" / "kb"


def state_file_path() -> Path:
    return _config_dir() / "state.json"


def load_state() -> dict[str, Any]:
    p = state_file_path()
    if not p.exists():
        return {"cursors": {}, "runs": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    p = state_file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def get_cursor(source: str) -> str | None:
    return load_state()["cursors"].get(source)


def set_cursor(source: str, value: str) -> None:
    state = load_state()
    state["cursors"][source] = value
    save_state(state)


def record_run(summary: dict[str, Any]) -> None:
    state = load_state()
    state["runs"].append(summary)
    if len(state["runs"]) > MAX_RUN_HISTORY:
        state["runs"] = state["runs"][-MAX_RUN_HISTORY:]
    save_state(state)
```

- [ ] **Step 4: Run the tests, expect green**

```bash
python3 -m pytest skills/kb/tests/test_kb_state.py -v 2>&1 | tail -10
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/kb/scripts/kb_state.py skills/kb/tests/test_kb_state.py
git commit -m "feat(kb-skill): kb_state — cursor + run-summary helpers

Pure stdlib. state.json under ~/.config/kb/. Cursor get/set, run-summary
append with FIFO trim at 50 entries (so the file doesn't grow forever).
Tests use HOME monkeypatching so the real config is untouched."
```

---

## Task 3: `kb_secret_scan.py` — gitleaks-pattern + Shannon-entropy reject (TDD)

**Files:**
- Create: `skills/kb/scripts/kb_secret_scan.py`
- Create: `skills/kb/tests/test_kb_secret_scan.py`

The scanner is invoked from SKILL.md as a CLI: it reads a JSON list of `{idx, body}` from stdin, returns a JSON list of `{idx, reason}` rejects on stdout. Keeps the SKILL.md procedure language-agnostic.

- [ ] **Step 1: Write the failing tests**

`skills/kb/tests/test_kb_secret_scan.py`:

```python
"""Tests for kb_secret_scan. Use a temp patterns file to keep the tests
hermetic and decoupled from any future tweaks to the shipped patterns."""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "kb_secret_scan.py"
DEFAULT_PATTERNS = Path(__file__).parent.parent / "secret-patterns.json"


def _import_module():
    sys.modules.pop("kb_secret_scan", None)
    spec = importlib.util.spec_from_file_location("kb_secret_scan", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_cli(stdin_payload: str, patterns_path: Path = DEFAULT_PATTERNS) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--patterns", str(patterns_path)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_aws_access_key_is_rejected():
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": "creds: AKIAIOSFODNN7EXAMPLE in code"}]}))
    rejected = out["rejected"]
    assert len(rejected) == 1
    assert rejected[0]["idx"] == 0
    assert "aws" in rejected[0]["reason"].lower()


def test_github_pat_classic_is_rejected():
    body = "token=ghp_" + "x" * 36
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0
    assert "github" in out["rejected"][0]["reason"].lower()


def test_jwt_shaped_is_rejected():
    body = "Bearer eyJabcdefghij.eyJklmnopqrst.uvwxyz12345abcdef"
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0


def test_pem_private_key_is_rejected():
    body = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAxxxxx\n-----END RSA PRIVATE KEY-----"
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0
    assert "private_key" in out["rejected"][0]["reason"].lower()


def test_envstyle_high_entropy_value_is_rejected():
    body = "Found in config: API_TOKEN=Z9mvX4LpQ7nRf2YbV0aS6hKjEcOiTu1wN3"
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0


def test_clean_prose_is_accepted():
    body = "The new rice variety RD43 tolerates monsoon lodging better than RD41."
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"] == []


def test_multiple_chunks_return_indexed_rejects():
    payload = json.dumps({
        "chunks": [
            {"idx": 0, "body": "clean prose about rice"},
            {"idx": 1, "body": "AKIAIOSFODNN7EXAMPLE leaked"},
            {"idx": 2, "body": "more clean prose"},
            {"idx": 3, "body": "another with ghp_" + "y" * 36},
        ],
    })
    out = _run_cli(payload)
    idxs = sorted(r["idx"] for r in out["rejected"])
    assert idxs == [1, 3]


def test_shannon_entropy_function():
    m = _import_module()
    # Known: 8 unique chars equally distributed → 3 bits.
    s = "abcdefgh" * 4
    e = m.shannon_entropy(s)
    assert 2.9 < e < 3.1
    # All same char → 0 entropy.
    assert m.shannon_entropy("aaaaaaaaaaaa") == 0.0
```

- [ ] **Step 2: Run tests, expect FileNotFoundError on the script**

```bash
cd /home/bjgdr/oracle/artemis-oracle
python3 -m pytest skills/kb/tests/test_kb_secret_scan.py -v 2>&1 | tail -15
```

Expected: all 8 tests fail (subprocess can't find the script, or import fails).

- [ ] **Step 3: Implement `kb_secret_scan.py`**

`skills/kb/scripts/kb_secret_scan.py`:

```python
#!/usr/bin/env python3
"""Secret scanner for the /kb skill.

CLI:
    echo '{"chunks":[{"idx":0,"body":"..."}]}' | \\
        python3 kb_secret_scan.py --patterns <path-to-secret-patterns.json>

Returns JSON on stdout: {"rejected": [{"idx": N, "reason": "<rule>"}]}

Rejects (never redacts) any chunk that:
- matches one of the regex patterns in --patterns
- contains an env-style KEY=value where the value clears the entropy bar
- contains any single substring (length >= min_length_to_check) whose
  Shannon entropy exceeds the global threshold
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def scan_one(body: str, patterns_data: dict[str, Any]) -> str | None:
    """Return a rejection reason string, or None if clean."""
    # 1) Regex patterns
    for p in patterns_data.get("patterns", []):
        if re.search(p["regex"], body):
            return p["name"]

    # 2) Env-style KEY=value with high-entropy value
    envstyle = patterns_data.get("envstyle")
    if envstyle:
        rx = re.compile(envstyle["key_value_regex"])
        threshold = envstyle["shannon_threshold"]
        for m in rx.finditer(body):
            value = m.group(1)
            if shannon_entropy(value) >= threshold:
                return "envstyle_high_entropy"

    return None


def scan_chunks(chunks: list[dict[str, Any]], patterns_data: dict[str, Any]) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for chunk in chunks:
        reason = scan_one(chunk["body"], patterns_data)
        if reason is not None:
            rejected.append({"idx": chunk["idx"], "reason": reason})
    return rejected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patterns", required=True, help="Path to secret-patterns.json")
    args = ap.parse_args()

    patterns_data = json.loads(Path(args.patterns).read_text(encoding="utf-8"))
    payload = json.loads(sys.stdin.read())
    rejected = scan_chunks(payload["chunks"], patterns_data)
    json.dump({"rejected": rejected}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, expect 8 green**

```bash
python3 -m pytest skills/kb/tests/test_kb_secret_scan.py -v 2>&1 | tail -15
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/kb/scripts/kb_secret_scan.py skills/kb/tests/test_kb_secret_scan.py
git commit -m "feat(kb-skill): kb_secret_scan — gitleaks-pattern + entropy reject

CLI: reads {chunks:[{idx,body}]} from stdin, writes {rejected:[{idx,reason}]}
on stdout. Pure stdlib (re + math). Rejects any chunk matching a configured
regex (AWS keys, GitHub PATs, Slack tokens, JWT-shaped, PEM private keys,
etc.) OR an env-style KEY=value where the value's Shannon entropy is at
or above the threshold. Tests cover one example from each rule + a clean
prose negative + a multi-chunk indexed-reject case."
```

---

## Task 4: `kb_collect_memory.py` — glob memory files + frontmatter parse + cursor filter (TDD)

**Files:**
- Create: `skills/kb/scripts/kb_collect_memory.py`
- Create: `skills/kb/tests/test_kb_collect_memory.py`

The collector takes globs + a since-cursor (ISO timestamp string) + a scope, glob-expands relative to a `--root`, filters by mtime > cursor AND (frontmatter `repo:` value in the scope's tags OR body case-insensitively contains any tag). Emits candidate JSON.

- [ ] **Step 1: Write the failing tests**

`skills/kb/tests/test_kb_collect_memory.py`:

```python
"""Tests for kb_collect_memory. Tests build a fake memory tree under tmp_path."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "kb_collect_memory.py"


def _write(path: Path, body: str, mtime_iso: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    if mtime_iso:
        # mtime_iso like "2026-05-20T00:00:00Z"
        import datetime as dt
        epoch = dt.datetime.strptime(mtime_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
        os.utime(path, (epoch, epoch))


def _run(root: Path, globs: list[str], scope: str, since: str | None, scope_tags: dict) -> dict:
    args = [sys.executable, str(SCRIPT),
            "--root", str(root),
            "--scope", scope,
            "--globs", json.dumps(globs),
            "--scope-tags", json.dumps(scope_tags)]
    if since:
        args.extend(["--since", since])
    proc = subprocess.run(args, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def test_picks_up_file_with_matching_frontmatter(tmp_path):
    _write(tmp_path / "ψ" / "memory" / "learnings" / "a.md",
           "---\nrepo: mobileai\n---\nNotes on the FCM silent skip.")
    out = _run(tmp_path, ["ψ/memory/learnings/**/*.md"], "mobileai", None, {"mobileai": ["mobileai"]})
    assert len(out["candidates"]) == 1
    c = out["candidates"][0]
    assert c["scope"] == "mobileai"
    assert c["source"] == "memory"
    assert c["title"]  # derived from first non-frontmatter heading or file stem
    assert "FCM silent skip" in c["body"]


def test_skips_file_without_matching_frontmatter_or_body_tag(tmp_path):
    _write(tmp_path / "ψ" / "memory" / "learnings" / "off-topic.md",
           "Notes about my dog.")
    out = _run(tmp_path, ["ψ/memory/learnings/**/*.md"], "mobileai", None, {"mobileai": ["mobileai", "ric-"]})
    assert out["candidates"] == []


def test_body_tag_match_when_no_frontmatter(tmp_path):
    _write(tmp_path / "ψ" / "memory" / "learnings" / "b.md",
           "Random note that mentions RIC-304 in passing.")
    out = _run(tmp_path, ["ψ/memory/learnings/**/*.md"], "mobileai", None, {"mobileai": ["mobileai", "ric-"]})
    assert len(out["candidates"]) == 1


def test_since_cursor_filters_by_mtime(tmp_path):
    old = tmp_path / "ψ" / "memory" / "learnings" / "old.md"
    new = tmp_path / "ψ" / "memory" / "learnings" / "new.md"
    _write(old, "---\nrepo: mobileai\n---\nold content", mtime_iso="2026-05-10T00:00:00Z")
    _write(new, "---\nrepo: mobileai\n---\nnew content", mtime_iso="2026-05-22T00:00:00Z")
    out = _run(tmp_path, ["ψ/memory/learnings/**/*.md"], "mobileai",
               since="2026-05-15T00:00:00Z",
               scope_tags={"mobileai": ["mobileai"]})
    titles = [c["title"] for c in out["candidates"]]
    assert "new" in str(titles)
    assert "old" not in str(titles)


def test_external_id_is_relative_path(tmp_path):
    p = tmp_path / "ψ" / "memory" / "learnings" / "subdir" / "x.md"
    _write(p, "---\nrepo: mobileai\n---\nbody")
    out = _run(tmp_path, ["ψ/memory/learnings/**/*.md"], "mobileai", None, {"mobileai": ["mobileai"]})
    assert out["candidates"][0]["external_id"] == "ψ/memory/learnings/subdir/x.md"


def test_no_globs_match_returns_empty(tmp_path):
    out = _run(tmp_path, ["does/not/exist/**/*.md"], "mobileai", None, {"mobileai": ["mobileai"]})
    assert out["candidates"] == []
```

- [ ] **Step 2: Run tests — fail (no script yet)**

```bash
cd /home/bjgdr/oracle/artemis-oracle
python3 -m pytest skills/kb/tests/test_kb_collect_memory.py -v 2>&1 | tail -15
```

- [ ] **Step 3: Implement `kb_collect_memory.py`**

`skills/kb/scripts/kb_collect_memory.py`:

```python
#!/usr/bin/env python3
"""Collect memory-file candidates for /kb scan.

CLI:
    python3 kb_collect_memory.py \\
        --root <repo-root> \\
        --globs '["ψ/memory/learnings/**/*.md", ...]' \\
        --scope <scope> \\
        --scope-tags '{"mobileai":["mobileai","ric-"], "gothailand":[...]}' \\
        [--since 2026-05-20T00:00:00Z]

Emits to stdout:
    {"candidates":[
       {"source":"memory","scope":"<scope>","external_id":"<rel-path>",
        "title":"<derived>","body":"<text>","metadata":{...}},
       ...
    ]}

Filtering:
  - mtime > since-cursor (if --since provided)
  - YAML frontmatter `repo:` matches one of scope-tags[scope]  OR
    body case-insensitively contains any string in scope-tags[scope]

Pure stdlib. No PyYAML — frontmatter parsed by a small inline routine
(enough for `key: value` shape).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body). Frontmatter only if file starts with ---."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, text
    rest = text.split("\n", 1)[1]
    if "\n---" not in rest:
        return {}, text
    fm_block, body = rest.split("\n---", 1)
    body = body.lstrip("\n")
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def _derive_title(rel_path: str, body: str) -> str:
    # Prefer first markdown H1 in body; fall back to file stem.
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return Path(rel_path).stem


def _iso_to_epoch(iso: str) -> float:
    return dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def collect(root: Path, globs: list[str], scope: str, scope_tags: dict[str, list[str]], since: str | None) -> list[dict[str, Any]]:
    since_epoch = _iso_to_epoch(since) if since else 0.0
    tags = [t.lower() for t in scope_tags.get(scope, [])]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for pat in globs:
        for raw in glob.iglob(str(root / pat), recursive=True):
            p = Path(raw)
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            if p.stat().st_mtime <= since_epoch:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            fm, body = _parse_frontmatter(text)
            in_scope_by_fm = fm.get("repo", "").lower() in tags
            body_lc = body.lower()
            in_scope_by_body = any(t in body_lc for t in tags)
            if not (in_scope_by_fm or in_scope_by_body):
                continue
            out.append({
                "source": "memory",
                "scope": scope,
                "external_id": rel,
                "title": _derive_title(rel, body),
                "body": body,
                "metadata": {
                    "frontmatter": fm,
                    "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--globs", required=True, help="JSON list of glob patterns")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--scope-tags", required=True, help="JSON dict scope→[tag, …]")
    ap.add_argument("--since", default=None)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    globs = json.loads(args.globs)
    scope_tags = json.loads(args.scope_tags)
    candidates = collect(root, globs, args.scope, scope_tags, args.since)
    json.dump({"candidates": candidates}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, expect 6 green**

```bash
python3 -m pytest skills/kb/tests/test_kb_collect_memory.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
git add skills/kb/scripts/kb_collect_memory.py skills/kb/tests/test_kb_collect_memory.py
git commit -m "feat(kb-skill): kb_collect_memory — glob + frontmatter + cursor filter

CLI: --root + --globs + --scope + --scope-tags + optional --since cursor.
Emits {candidates: [{source, scope, external_id, title, body, metadata}]}.
Pure stdlib (no PyYAML — small inline parser handles the key:value
frontmatter we use). Tests cover frontmatter match, body-tag match,
cursor filter, relative-path external_id, no-match negative."
```

---

## Task 5: SKILL.md procedural body (the heart of the skill)

**Files:**
- Modify: `skills/kb/SKILL.md`

- [ ] **Step 1: Replace the placeholder body**

Overwrite `skills/kb/SKILL.md` (keep the frontmatter from Task 1):

````markdown
---
name: kb
description: Shared-memory KB curator. Use this skill when the user invokes /kb scan, /kb search, /kb show, /kb retract, /kb status, /kb list, or /kb config — or when they ask to push curated knowledge into the shared memory store, or to search/retract chunks already in it. Wraps the jira-fetch-kb MCP server (kb_health, kb_search, kb_get, kb_ingest, kb_retract).
---

# /kb — Shared Memory KB curator

When the user runs `/kb <subcommand> [args]`, follow the procedure for that subcommand below.

**Preconditions every subcommand checks first:**

1. `~/.config/kb/config.json` exists. If missing, tell the user to copy `skills/kb/config.example.json` to `~/.config/kb/config.json` and stop.
2. The session has an MCP server matching `config.mcp_server_alias` (default `jira-fetch-kb`) with tools `kb_health`, `kb_search`, `kb_get`, `kb_ingest`, `kb_retract`. If not, tell the user to register the server in `~/.claude.json` (see `skills/kb/README.md`) and stop.

When this skill needs to call an MCP tool, the actual tool name in the session will be `mcp__<alias>__<tool>` (e.g. `mcp__jira-fetch-kb__kb_search`). Substitute the alias from the loaded config.

---

## `/kb scan [--since YYYY-MM-DD] [--scope mobileai|gothailand] [--source memory] [--dry-run]`

This is the curator pipeline. Memory source ONLY in this batch — if the user passes `--source jira`, tell them Jira ingestion isn't implemented yet and stop.

**Flags:**
- `--since YYYY-MM-DD` — defaults to the cursor in `state.json` for the chosen source. If neither is set, default to 7 days ago.
- `--scope mobileai|gothailand` — required. (Don't default; force the user to pick so they don't accidentally cross scopes.)
- `--source memory` — only valid value right now.
- `--dry-run` — run the pipeline but skip the final `kb_ingest` call.

**Procedure:**

1. **Read config** at `~/.config/kb/config.json`. Resolve the bearer token via `config.token_ref` (only `file:` URIs supported right now — read the path, take the first non-empty line).

2. **Read the since-cursor.** Run:
   ```bash
   python3 -c "
   import sys, json
   sys.path.insert(0, '<artemis-oracle-root>/skills/kb/scripts')
   import kb_state
   print(kb_state.get_cursor('memory') or '')
   "
   ```
   Use `--since` if provided; else the cursor; else `(today − 7d).isoformat()+'Z'`.

3. **Collect candidates** by running `skills/kb/scripts/kb_collect_memory.py` with the resolved arguments. The `--root` should be the artemis-oracle clone path on this dev's machine (default: `/home/bjgdr/oracle/artemis-oracle`).

   ```bash
   python3 <root>/skills/kb/scripts/kb_collect_memory.py \
     --root <root> \
     --globs "$(python3 -c 'import json; print(json.dumps(<from-config>.allowlist.memory_globs))')" \
     --scope <scope> \
     --scope-tags "$(python3 -c 'import json; print(json.dumps(<from-config>.allowlist.scope_tags))')" \
     --since <since-cursor>
   ```

   Parse the `{candidates:[…]}` JSON. If empty, tell the user "no candidates since <cursor>" and stop.

4. **Secret-scan** the candidates by piping them through `kb_secret_scan.py`:
   ```bash
   echo "$(python3 -c 'import json; print(json.dumps({"chunks": [{"idx":i,"body":c["body"]} for i,c in enumerate(candidates)]}))')" \
     | python3 <root>/skills/kb/scripts/kb_secret_scan.py --patterns <root>/skills/kb/secret-patterns.json
   ```
   Remove rejected indices from `candidates`. Remember the reject list for the run summary.

5. **LLM judge** — for each remaining candidate, ask yourself (Claude, in-session):

   > "Does this content benefit other devs working on <scope>?
   > Reply STRICT JSON: {benefits: boolean, confidence: number 0..1, reason: string ≤ 100 chars}"

   Use the content's title + body. Drop candidates where `benefits === false` or `confidence < config.classifier.threshold`. Attach the judge verdict to each survivor's `metadata.judge`.

6. **Approval gate.** Print a numbered table to the user:

   ```
   #  external_id                                 scope     judge.confidence  judge.reason (truncated)
   1  ψ/memory/learnings/feedback_iso-…           mobileai  0.92              ISO doc image hygiene…
   2  ψ/memory/retrospectives/2026-05/13/…        mobileai  0.81              QOne batch retro…
   ```

   Ask: "Approve which? `a` for all, comma-list (e.g. `1,3`), or `n` for none." Wait for the response.

7. **Upload** the approved subset. For each approved candidate, call the MCP `kb_ingest` tool with `{chunks: [<one chunk>]}`. (Single-chunk batches keep failures isolated — if one ingest fails, the others still land.) Attach `metadata.uploaded_by` from `config.owner_email` if set, and `metadata.judge` from step 5.

   If `--dry-run`, skip this step.

8. **Advance the cursor** to `max(mtime over all approved candidates)` ONLY IF at least one ingest succeeded. Call `kb_state.set_cursor("memory", <max-mtime-iso>)`.

9. **Record the run.** Call `kb_state.record_run({...})` with `{ts, source:"memory", scope, ingested:N, secret_rejected:M, classifier_rejected:K, user_skipped:L}`.

10. **Summary.** Print to the user: `N ingested · M secret-rejected · K classifier-rejected · L user-skipped`. Include the new cursor value if it advanced.

---

## `/kb search <query> [--scope …] [--source …] [--top-k 5]`

Resolve config → call the MCP `kb_search` tool with the literal args. Pretty-print the response as a numbered list: `# | similarity | scope | source | external_id | title — snippet`.

---

## `/kb show <id>`

Call MCP `kb_get` with `{id: <id>}`. Pretty-print the full chunk including metadata + `revoked_at`.

---

## `/kb retract <id> [--reason "…"]`

Ask the user to confirm (show the chunk via `kb_get` first), then call MCP `kb_retract` with `{id, reason}`. Print the resulting `revoked_at`.

---

## `/kb status`

1. Call MCP `kb_health`. Report `db_ok` and `embed_ok`.
2. Read `~/.config/kb/state.json` via `kb_state.load_state()` and print cursors + the most recent run summary.

---

## `/kb list [--mine] [--since …] [--source …] [--scope …]`

Local-only. Read `state.json` runs, filter by the optional args, print a chronological table.

---

## `/kb config [--show | --edit]`

`--show` (default): cat `~/.config/kb/config.json` redacting the `token_ref` line's resolved value.
`--edit`: tell the user where the file lives. Don't open editors directly from the skill.

---

## Important conventions

- **Server is dumb; this skill is the gatekeeper.** Never call MCP `kb_ingest` without running the secret-scan + judge + approval pipeline first. If you find yourself reaching for `kb_ingest` outside `/kb scan`, stop.
- **One chunk per `kb_ingest` call.** Single-chunk batches keep the audit trail clean and isolate failures.
- **Never write to the dev's working tree.** The skill only writes to `~/.config/kb/`.
- **Secret-scan rejects; it never redacts.** A redacted secret in the KB is still a leak; refusal is the right answer.
````

- [ ] **Step 2: Commit**

```bash
git add skills/kb/SKILL.md
git commit -m "feat(kb-skill): SKILL.md procedural body for all 7 subcommands

/kb scan does the full curator pipeline (collect → secret-scan → LLM judge
→ approval → MCP kb_ingest with cursor advance). The other subcommands
(search/show/retract/status/list/config) are thin wrappers over MCP tools
or local state. Memory source only — Jira deferred to a later batch.
Important conventions section at the bottom locks in 'server is dumb,
skill is gatekeeper', single-chunk ingests, no working-tree writes,
reject-not-redact on secrets."
```

---

## Task 6: Local install + smoke against the live MCP server

This task is manual (runs on the dev's workstation) — no subagent. The dev does it themselves after the previous tasks are merged. Document what they should run; the steps below are also the contents the implementer will paste into the smoke section of the PR description.

- [ ] **Step 1: Push the branch + open the PR**

```bash
cd /home/bjgdr/oracle/artemis-oracle
git push -u origin feat/kb-skill-batch-4
gh pr create --base main --head feat/kb-skill-batch-4 \
  --title "feat(kb-skill): /kb curator skill (memory source)" \
  --body "$(cat <<'EOF'
## Summary

Ships the dev-facing \`/kb\` curator skill at \`skills/kb/\`. It runs inside any Claude Code session that has the \`jira-fetch-kb\` MCP server registered, and orchestrates the spec §8 pipeline against the dev's local \`ψ/memory/\` files:

- collect candidates (glob + cursor)
- heuristic scope filter (frontmatter \`repo:\` or body tag match)
- secret-scan (gitleaks-pattern + Shannon entropy — reject, never redact)
- LLM judge (\"benefits other devs?\" — Claude does this in-session)
- user approval (\`a\` / \`1,3,5\` / \`n\`)
- MCP \`kb_ingest\` (one chunk per call)
- cursor advance + run summary persisted to \`~/.config/kb/state.json\`

Also wraps \`kb_search\`, \`kb_get\`, \`kb_retract\`, \`kb_health\` as friendlier subcommands.

## Memory source only

Jira ingestion is intentionally deferred — it needs a \"since-cursor\" query against jira-fetch's Postgres or a new API endpoint. Filed for a follow-up batch.

## Spec / plan

- Spec: \`docs/superpowers/specs/2026-05-21-shared-memory-kb-design.md\` §8
- Plan: \`docs/superpowers/plans/2026-05-22-shared-memory-kb-batch-4.md\`

## Test plan

CI / pre-merge:
- [x] pytest passes locally (21 tests across kb_state/kb_secret_scan/kb_collect_memory)

Post-merge (local smoke against the live MCP server — \`http://43.208.150.191:6501/mcp\`):
- [ ] One-time install per \`skills/kb/README.md\` (\`~/.config/kb/config.json\` + \`~/.claude.json\` MCP server registration with bearer)
- [ ] \`/kb status\` returns \`db_ok\` and \`embed_ok\` true
- [ ] \`/kb scan --scope mobileai --dry-run --since 2026-05-01\` shows candidates with judge verdicts and stops without ingesting
- [ ] \`/kb scan --scope mobileai --since 2026-05-01\` ingests at least one approved chunk; \`/kb search\` finds it
- [ ] \`/kb retract <id> --reason \"smoke test cleanup\"\` soft-deletes it
- [ ] Hard cleanup: psql \`DELETE FROM memory_chunk WHERE scope = 'mobileai' AND metadata->>'smoke' = 'true';\` (only if any rows were tagged smoke-true — by default the skill doesn't tag this way)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

DO NOT auto-merge. The user reviews + merges.

- [ ] **Step 2: Self-review summary**

When reporting back from this task, include:
- The PR URL
- All commit SHAs from Tasks 1-5
- Total pytest count (expect ~21: 7 state + 8 secret-scan + 6 collect-memory)
- Any notes about scripts/SKILL.md that diverged from the plan

---

## Definition of Done

- [ ] PR merged to `main` (or whatever the default branch is on the artemis-oracle repo)
- [ ] One-time install of the skill on at least one dev workstation
- [ ] `/kb status` green
- [ ] `/kb scan --dry-run` returns a sensible candidate list with judge verdicts
- [ ] `/kb scan` ingests ≥ 1 chunk; `/kb search` finds it; `/kb retract` soft-removes it
- [ ] No errors in `journalctl -u jirafetch-api` related to the new ingests on the EC2

When all of the above are checked, batch 4 is done. Batch 5 (Jira ingestion + nginx HTTPS + GHA sidecar automation) can be planned.

---

## Rollback

Batch 4 only adds files under `skills/kb/`. To roll back:

1. Revert the merge commit on `main`. The skill disappears; nothing else changes.
2. If any chunks were uploaded during smoke and need scrubbing, use the existing `/kb retract <id>` or psql directly: `DELETE FROM memory_chunk WHERE source = 'memory' AND scope = '<scope>';` on the EC2.
3. Per-dev `~/.config/kb/` files stay — harmless without the skill present.
