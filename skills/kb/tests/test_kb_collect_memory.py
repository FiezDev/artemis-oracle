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
