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
