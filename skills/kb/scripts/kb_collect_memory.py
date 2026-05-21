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
    """Tolerant ISO date parser. Accepts:
    - 'YYYY-MM-DD'
    - 'YYYY-MM-DDTHH:MM:SSZ'
    - 'YYYY-MM-DDTHH:MM:SS.ffffffZ' (datetime.isoformat() output)
    """
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(iso, fmt)
            return parsed.replace(tzinfo=dt.timezone.utc).timestamp()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse ISO date: {iso!r}")


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
