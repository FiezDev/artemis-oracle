#!/usr/bin/env python3
"""Move the previously scheduled AI Inspire posts back to drafts via Meta Planner."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AB = "/home/bjgdr/.linuxbrew/bin/agent-browser"
OUT = ROOT / "output/facebook/aisearch-onego-v3/old-schedule-draft-results.jsonl"
PAGE_ID = "1136813799507714"
URL = f"https://business.facebook.com/latest/content_calendar?asset_id={PAGE_ID}"

# Old browser scheduling run successfully created these slots. The 00:00 slot
# was already moved manually while developing this cleaner.
TARGETS = [
    ("Thu", "02:00", 614),
    ("Thu", "04:00", 614),
    ("Thu", "06:00", 614),
    ("Thu", "08:00", 614),
    ("Thu", "10:00", 614),
    ("Thu", "12:00", 614),
    ("Thu", "14:00", 614),
    ("Thu", "16:00", 614),
    ("Thu", "18:00", 614),
    ("Thu", "20:00", 614),
    ("Thu", "22:00", 614),
]


def ab(*args: str, check: bool = True, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([AB, *args], cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc


def eval_js(script: str) -> str:
    raw = ab("eval", script).stdout.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            return parsed
    except json.JSONDecodeError:
        pass
    return raw


def snapshot(tag: str) -> str:
    path = ROOT / "gen-output" / f"fb-clear-{int(time.time())}-{tag}.png"
    ab("screenshot", str(path), check=False)
    return str(path)


def open_planner() -> None:
    ab("open", URL, timeout=120)
    time.sleep(5)


def mark_target(time_text: str, x_hint: int) -> str:
    js = f"""
(() => {{
  document.querySelectorAll('[data-ai-target]').forEach(e => e.removeAttribute('data-ai-target'));
  const timeText = {json.dumps(time_text)};
  const xHint = {x_hint};
  const candidates = Array.from(document.querySelectorAll('a, [role="link"]')).map((e) => {{
    const r = e.getBoundingClientRect();
    const text = (e.innerText || e.getAttribute('aria-label') || '').trim();
    return {{ e, text, x: r.x, y: r.y, w: r.width, h: r.height }};
  }}).filter(o =>
    o.text.split('\\n')[0] === timeText &&
    Math.abs(o.x - xHint) < 35 &&
    o.w > 80 && o.w < 160 &&
    o.h > 80 && o.h < 180
  ).sort((a, b) => Math.abs(a.x - xHint) - Math.abs(b.x - xHint));
  if (!candidates.length) return 'not-found';
  const target = candidates[0].e;
  target.setAttribute('data-ai-target', '1');
  target.scrollIntoView({{ block: 'center', inline: 'center' }});
  const r = target.getBoundingClientRect();
  return ['marked', Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)].join('|');
}})()
"""
    return eval_js(js)


def mark_dialog_button(regex: str, attr: str) -> str:
    js = f"""
(() => {{
  document.querySelectorAll('[{attr}]').forEach(e => e.removeAttribute('{attr}'));
  const re = new RegExp({json.dumps(regex)}, 'i');
  const dialogs = Array.from(document.querySelectorAll('[role=dialog]'));
  const roots = dialogs.length ? [...dialogs.reverse(), document] : [document];
  for (const d of roots) {{
    const btn = Array.from(d.querySelectorAll('[role=button], button, [role=menuitem]'))
      .find(b => {{
        const r = b.getBoundingClientRect();
        const text = (b.innerText || b.getAttribute('aria-label') || '').trim();
        return r.width > 0 && r.height > 0 && re.test(text);
      }});
    if (btn) {{
      btn.setAttribute('{attr}', '1');
      btn.scrollIntoView({{ block: 'center' }});
      return 'marked:' + (btn.innerText || btn.getAttribute('aria-label') || '').trim();
    }}
  }}
  return 'not-found';
}})()
"""
    return eval_js(js)


def dialog_state() -> dict:
    raw = eval_js(
        """
(() => JSON.stringify(Array.from(document.querySelectorAll('[role=dialog]')).map(d => ({
  text: (d.innerText || '').slice(0, 700),
  id: ((d.innerText || '').match(/ID:\\s*(\\d+)/) || [])[1] || ''
}))))()
"""
    )
    return {"dialogs": json.loads(raw) if raw else []}


def close_dialogs() -> None:
    for _ in range(3):
        marked = mark_dialog_button("^Close", "data-ai-close")
        if not marked.startswith("marked"):
            break
        ab("click", "[data-ai-close=\"1\"]", check=False)
        time.sleep(1)


def clear_one(day: str, time_text: str, x_hint: int) -> dict:
    record = {"day": day, "time": time_text, "x_hint": x_hint, "status": "started"}
    marker = mark_target(time_text, x_hint)
    record["marker"] = marker
    if not marker.startswith("marked|"):
        record["status"] = "not-found"
        return record

    ab("click", "[data-ai-target=\"1\"]")
    time.sleep(3)
    record["opened"] = dialog_state()

    action = mark_dialog_button("^Actions", "data-ai-actions")
    record["action_button"] = action
    if action.startswith("marked"):
        ab("click", "[data-ai-actions=\"1\"]")
        time.sleep(1)

    move = mark_dialog_button("^Move to Drafts$", "data-ai-move")
    if move.startswith("marked"):
        record["operation"] = "move-to-drafts"
        ab("click", "[data-ai-move=\"1\"]")
        time.sleep(1)
        confirm = mark_dialog_button("^Move to drafts$", "data-ai-confirm-move")
        record["confirm"] = confirm
        if confirm.startswith("marked"):
            ab("click", "[data-ai-confirm-move=\"1\"]")
            time.sleep(4)
            record["status"] = "moved-to-drafts"
        else:
            record["status"] = "confirm-missing"
            record["screenshot"] = snapshot("confirm-missing")
        return record

    delete = mark_dialog_button("^Delete post$", "data-ai-delete")
    if delete.startswith("marked"):
        record["operation"] = "delete-published"
        ab("click", "[data-ai-delete=\"1\"]")
        time.sleep(1)
        confirm = mark_dialog_button("^Delete$", "data-ai-confirm-delete")
        record["confirm"] = confirm
        if confirm.startswith("marked"):
            ab("click", "[data-ai-confirm-delete=\"1\"]")
            time.sleep(4)
            record["status"] = "deleted"
        else:
            record["status"] = "delete-confirm-missing"
            record["screenshot"] = snapshot("delete-confirm-missing")
        return record

    record["status"] = "no-move-or-delete"
    record["screenshot"] = snapshot("no-action")
    close_dialogs()
    return record


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    open_planner()
    for day, time_text, x_hint in TARGETS:
        record = clear_one(day, time_text, x_hint)
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if record["status"] in {"confirm-missing", "delete-confirm-missing"}:
            return 1
        close_dialogs()
        open_planner()
        time.sleep(1)
    open_planner()
    snapshot("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
