#!/usr/bin/env python3
"""Clear all visible AI Inspire scheduled rows from Meta Business Suite."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AB = "/home/bjgdr/.linuxbrew/bin/agent-browser"
PAGE_ID = "1136813799507714"
SCHEDULED_URL = f"https://business.facebook.com/latest/posts/scheduled_posts/?asset_id={PAGE_ID}"
OUT = ROOT / "output/facebook/aisearch-onego-v3/content-scheduled-clear-results.jsonl"


def ab(*args: str, check: bool = True, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([AB, *args], cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc


def eval_js(script: str) -> str:
    raw = ab("eval", script).stdout.strip()
    try:
        value = json.loads(raw)
        if isinstance(value, str):
            return value
    except json.JSONDecodeError:
        pass
    return raw


def open_scheduled() -> None:
    ab("open", SCHEDULED_URL, timeout=120)
    time.sleep(1)
    ab("press", "Escape", check=False)
    ab("reload", timeout=120)
    time.sleep(5)


def mark_first_row_menu() -> str:
    return eval_js(
        """
(() => {
  document.querySelectorAll('[data-ai-row-menu]').forEach(e => e.removeAttribute('data-ai-row-menu'));
  const btn = Array.from(document.querySelectorAll('[role=button], button, div'))
    .map(e => {
      const r = e.getBoundingClientRect();
      return { e, r, text: (e.innerText || e.getAttribute('aria-label') || '').trim() };
    })
    .filter(o =>
      /Open Drop-down/.test(o.text) &&
      o.r.y > 235 &&
      o.r.width >= 30 &&
      o.r.width <= 55 &&
      o.r.height > 20
    )
    .sort((a, b) => a.r.y - b.r.y)[0];
  if (!btn) return 'no-row-menu';
  const row = btn.e.closest('[role=row], tr') || btn.e.parentElement;
  const rowText = row ? (row.innerText || '').slice(0, 350) : '';
  btn.e.setAttribute('data-ai-row-menu', '1');
  return JSON.stringify({
    status: 'marked',
    x: Math.round(btn.r.x),
    y: Math.round(btn.r.y),
    rowText,
  });
})()
"""
    )


def mark_visible_text(text: str, attr: str) -> str:
    return eval_js(
        f"""
(() => {{
  document.querySelectorAll('[{attr}]').forEach(e => e.removeAttribute('{attr}'));
  const target = Array.from(document.querySelectorAll('[role=button], button, [role=menuitem], div'))
    .find(e => {{
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0 &&
        (e.innerText || e.getAttribute('aria-label') || '').trim() === {json.dumps(text)};
    }});
  if (!target) return 'not-found';
  target.setAttribute('{attr}', '1');
  target.scrollIntoView({{ block: 'center', inline: 'center' }});
  return 'marked';
}})()
"""
    )


def mark_regex(pattern: str, attr: str) -> str:
    return eval_js(
        f"""
(() => {{
  document.querySelectorAll('[{attr}]').forEach(e => e.removeAttribute('{attr}'));
  const re = new RegExp({json.dumps(pattern)}, 'i');
  const target = Array.from(document.querySelectorAll('[role=button], button, [role=menuitem], div'))
    .find(e => {{
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0 &&
        re.test((e.innerText || e.getAttribute('aria-label') || '').trim());
    }});
  if (!target) return 'not-found';
  target.setAttribute('{attr}', '1');
  target.scrollIntoView({{ block: 'center', inline: 'center' }});
  return 'marked';
}})()
"""
    )


def click_text(text: str) -> None:
    ab("find", "text", text, "click")


def visible_exact_text_exists(text: str) -> bool:
    raw = eval_js(
        f"""
(() => {{
  const targets = Array.from(document.querySelectorAll('[role=button], button, [role=menuitem], div'))
    .filter(e => {{
      const r = e.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0 &&
        (e.innerText || e.getAttribute('aria-label') || '').trim() === {json.dumps(text)})) return false;
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return top && (e === top || e.contains(top) || top.contains(e));
    }});
  return String(targets.length > 0);
}})()
"""
    )
    return raw == "true"


def click_marked(attr: str) -> None:
    raw = eval_js(
        f"""
(() => {{
  const target = document.querySelector('[{attr}="1"]');
  if (!target) return 'not-found';
  const r = target.getBoundingClientRect();
  return JSON.stringify({{
    x: Math.round(r.left + r.width / 2),
    y: Math.round(r.top + r.height / 2),
  }});
}})()
"""
    )
    try:
        point = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cannot click marked {attr}: {raw}") from exc
    ab("mouse", "move", str(point["x"]), str(point["y"]))
    ab("mouse", "down")
    ab("mouse", "up")


def click_point(x: int, y: int) -> None:
    ab("mouse", "move", str(x), str(y))
    ab("mouse", "down")
    ab("mouse", "up")


def wait_for_mark_visible_text(text: str, attr: str, timeout_s: float = 8.0) -> str:
    deadline = time.monotonic() + timeout_s
    last = "not-found"
    while time.monotonic() < deadline:
        last = mark_visible_text(text, attr)
        if last == "marked":
            return last
        time.sleep(0.5)
    return last


def wait_for_mark_regex(pattern: str, attr: str, timeout_s: float = 8.0) -> str:
    deadline = time.monotonic() + timeout_s
    last = "not-found"
    while time.monotonic() < deadline:
        last = mark_regex(pattern, attr)
        if last == "marked":
            return last
        time.sleep(0.5)
    return last


def mark_visible_text_rightmost(text: str, attr: str) -> str:
    return eval_js(
        f"""
(() => {{
  document.querySelectorAll('[{attr}]').forEach(e => e.removeAttribute('{attr}'));
  const targets = Array.from(document.querySelectorAll('[role=button], button, [role=menuitem], div'))
    .map(e => {{
      const r = e.getBoundingClientRect();
      return {{ e, r, t: (e.innerText || e.getAttribute('aria-label') || '').trim() }};
    }})
    .filter(o => {{
      if (!(o.r.width > 0 && o.r.height > 0 && o.t === {json.dumps(text)})) return false;
      const cx = o.r.left + o.r.width / 2;
      const cy = o.r.top + o.r.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return top && (o.e === top || o.e.contains(top) || top.contains(o.e));
    }})
    .sort((a, b) => (b.r.x + b.r.width) - (a.r.x + a.r.width));
  if (!targets.length) return 'not-found';
  targets[0].e.setAttribute('{attr}', '1');
  targets[0].e.scrollIntoView({{ block: 'center', inline: 'center' }});
  return 'marked';
}})()
"""
    )


def wait_for_mark_visible_text_rightmost(text: str, attr: str, timeout_s: float = 8.0) -> str:
    deadline = time.monotonic() + timeout_s
    last = "not-found"
    while time.monotonic() < deadline:
        last = mark_visible_text_rightmost(text, attr)
        if last == "marked":
            return last
        time.sleep(0.5)
    return last


def count_scheduled_rows() -> int:
    raw = eval_js(
        """
(() => {
  const rows = Array.from(document.querySelectorAll('input[aria-label*="Tick item with caption"]'))
    .filter(e => {
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });
  return String(rows.length);
})()
"""
    )
    try:
        return int(raw)
    except ValueError:
        return -1


def clear_top_row() -> dict:
    row_marker = mark_first_row_menu()
    try:
        record = json.loads(row_marker)
    except json.JSONDecodeError:
        return {"status": "no-row-menu", "marker": row_marker}

    ab("click", "[data-ai-row-menu=\"1\"]")
    time.sleep(1)
    click_text("Manage post")
    time.sleep(0.8)
    click_text("Manage post")
    time.sleep(0.8)
    record["manage"] = "clicked"
    click_text("Delete post")
    time.sleep(1)

    confirm = wait_for_mark_visible_text_rightmost("Delete", "data-ai-confirm-delete", timeout_s=8.0)
    record["confirm_button"] = confirm
    if confirm != "marked":
        record["status"] = "delete-confirm-missing"
        return record
    click_marked("data-ai-confirm-delete")
    time.sleep(6)
    record["confirm"] = "clicked"
    record["status"] = "deleted"
    return record


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    open_scheduled()
    for i in range(40):
        remaining = count_scheduled_rows()
        if remaining == 0:
            print(json.dumps({"status": "empty", "iteration": i}, ensure_ascii=False), flush=True)
            return 0
        record = clear_top_row()
        record["iteration"] = i
        record["remaining_before"] = remaining
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if record.get("status") not in {"deleted"}:
            shot = ROOT / "gen-output" / f"fb-clear-scheduled-failed-{int(time.time())}.png"
            ab("screenshot", str(shot), check=False)
            return 1
        open_scheduled()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
