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
