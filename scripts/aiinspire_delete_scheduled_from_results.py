#!/usr/bin/env python3
"""Delete scheduled Meta rows that match a browser-schedule results file."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AB = "/home/bjgdr/.linuxbrew/bin/agent-browser"
PAGE_ID = "1136813799507714"
SCHEDULED_URL = f"https://business.facebook.com/latest/posts/scheduled_posts/?asset_id={PAGE_ID}"


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


def open_scheduled() -> None:
    ab("open", SCHEDULED_URL, timeout=120)
    time.sleep(4)
    ab("press", "Escape", check=False)


def click_marked(attr: str) -> None:
    raw = eval_js(
        f"""
(() => {{
  const target = document.querySelector('[{attr}="1"]');
  if (!target) return 'not-found';
  const r = target.getBoundingClientRect();
  return JSON.stringify({{
    x: Math.round(r.left + r.width / 2),
    y: Math.round(r.top + r.height / 2)
  }});
}})()
"""
    )
    point = json.loads(raw)
    ab("mouse", "move", str(point["x"]), str(point["y"]))
    ab("mouse", "down")
    ab("mouse", "up")


def hover_marked(attr: str) -> bool:
    raw = eval_js(
        f"""
(() => {{
  const target = document.querySelector('[{attr}="1"]');
  if (!target) return 'not-found';
  const r = target.getBoundingClientRect();
  return JSON.stringify({{
    x: Math.round(r.left + r.width / 2),
    y: Math.round(r.top + r.height / 2)
  }});
}})()
"""
    )
    if raw == "not-found":
        return False
    point = json.loads(raw)
    ab("mouse", "move", str(point["x"]), str(point["y"]))
    return True


def visible_count() -> int:
    raw = eval_js(
        """
(() => String(Array.from(document.querySelectorAll('input[aria-label*="Tick item with caption"]'))
  .filter(e => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }).length))()
"""
    )
    try:
        return int(raw)
    except ValueError:
        return -1


def mark_matching_row(headlines: list[str]) -> dict:
    raw = eval_js(
        f"""
(() => {{
  document.querySelectorAll('[data-ai-row-menu]').forEach(e => e.removeAttribute('data-ai-row-menu'));
  const headlines = {json.dumps(headlines, ensure_ascii=False)};
  const rows = Array.from(document.querySelectorAll('input[aria-label*="Tick item with caption"]'))
    .map(input => {{
      const row = input.closest('[role=row], tr') || input.closest('[role=grid] > div') || input.parentElement;
      const r = input.getBoundingClientRect();
      return {{ input, row, label: input.getAttribute('aria-label') || '', y: r.y }};
    }})
    .filter(o => {{
      const r = o.input.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && headlines.some(h => o.label.includes(h));
    }})
    .sort((a, b) => a.y - b.y);
  if (!rows.length) return JSON.stringify({{status: 'no-match'}});
  const row = rows[0].row;
  const menu = Array.from(row.querySelectorAll('[role=button], button, div'))
    .map(e => {{
      const r = e.getBoundingClientRect();
      return {{ e, r, text: (e.innerText || e.getAttribute('aria-label') || '').trim() }};
    }})
    .filter(o => /Open Drop-down/.test(o.text) && o.r.width > 20 && o.r.height > 15)
    .filter(o => o.text.split('\\n')[0] === 'Open Drop-down')
    .sort((a, b) => (b.r.x + b.r.width) - (a.r.x + a.r.width))[0];
  if (!menu) return JSON.stringify({{status: 'no-menu', label: rows[0].label.slice(0, 160)}});
  menu.e.setAttribute('data-ai-row-menu', '1');
  menu.e.scrollIntoView({{block: 'center', inline: 'center'}});
  return JSON.stringify({{
    status: 'marked',
    label: rows[0].label.slice(0, 220),
    x: Math.round(menu.r.left + menu.r.width / 2),
    y: Math.round(menu.r.top + menu.r.height / 2)
  }});
}})()
"""
    )
    return json.loads(raw)


def mark_text(text: str, attr: str, scope_re: str | None = None) -> str:
    raw = eval_js(
        f"""
(() => {{
  document.querySelectorAll('[{attr}]').forEach(e => e.removeAttribute('{attr}'));
  const scopeRe = {json.dumps(scope_re)};
  const scopes = scopeRe
    ? Array.from(document.querySelectorAll('[role=dialog], div')).filter(d => new RegExp(scopeRe, 'i').test(d.innerText || ''))
    : [document];
  for (const scope of scopes) {{
      const targets = Array.from(scope.querySelectorAll('[role=button], button, [role=menuitem], div'))
        .map(e => {{
          const r = e.getBoundingClientRect();
          const role = e.getAttribute('role') || '';
          const tag = e.tagName || '';
          const clickable = role === 'button' || role === 'menuitem' || tag === 'BUTTON';
          return {{
            e,
            r,
            text: (e.innerText || e.getAttribute('aria-label') || '').trim(),
            clickable,
            area: r.width * r.height
          }};
        }})
        .filter(o => o.text === {json.dumps(text)} && o.r.width > 0 && o.r.height > 0)
        .sort((a, b) => Number(b.clickable) - Number(a.clickable)
          || a.area - b.area
          || (b.r.x + b.r.width) - (a.r.x + a.r.width));
    if (targets.length) {{
      targets[0].e.setAttribute('{attr}', '1');
      targets[0].e.scrollIntoView({{block: 'center', inline: 'center'}});
      return 'marked';
    }}
  }}
  return 'not-found';
}})()
"""
    )
    return raw.strip().strip('"')


def wait_mark_text(text: str, attr: str, scope_re: str | None = None, timeout_s: float = 8.0) -> str:
    deadline = time.monotonic() + timeout_s
    last = "not-found"
    while time.monotonic() < deadline:
        last = mark_text(text, attr, scope_re=scope_re)
        if last == "marked":
            return last
        time.sleep(0.5)
    return last


def delete_one(headlines: list[str]) -> dict:
    before = visible_count()
    record = {"remaining_before": before}
    row = mark_matching_row(headlines)
    record["row"] = row
    if row.get("status") != "marked":
        record["status"] = row.get("status", "not-found")
        return record

    click_marked("data-ai-row-menu")
    time.sleep(1)

    if wait_mark_text("Manage post", "data-ai-manage-post", timeout_s=8) != "marked":
        record["status"] = "manage-missing"
        return record
    click_marked("data-ai-manage-post")
    time.sleep(0.2)
    ab("press", "ArrowRight", check=False)
    hover_marked("data-ai-manage-post")
    time.sleep(1)

    if wait_mark_text("Delete post", "data-ai-delete-post", timeout_s=8) != "marked":
        hover_marked("data-ai-manage-post")
        ab("press", "ArrowRight", check=False)
        time.sleep(1)
    if wait_mark_text("Delete post", "data-ai-delete-post", timeout_s=3) != "marked":
        record["status"] = "delete-menu-missing"
        return record
    click_marked("data-ai-delete-post")
    time.sleep(1)

    if wait_mark_text("Delete", "data-ai-confirm-delete", scope_re="Delete post\\?", timeout_s=8) != "marked":
        record["status"] = "confirm-missing"
        return record
    click_marked("data-ai-confirm-delete")
    time.sleep(8)

    after = visible_count()
    record["remaining_after"] = after
    record["status"] = "deleted" if after < before else "delete-not-verified"
    return record


def read_headlines(queue_path: Path, results_path: Path) -> list[str]:
    queue = {int(item["index"]): item for item in json.loads(queue_path.read_text(encoding="utf-8"))}
    indexes: set[int] = set()
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("rc") == 0:
            indexes.add(int(row["index"]))
    headlines: list[str] = []
    for idx in sorted(indexes):
        text = queue[idx]["text"]
        headline = next((part.strip() for part in text.splitlines() if part.strip()), "")
        if headline:
            headlines.append(headline)
    return headlines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-delete", type=int, default=40)
    args = parser.parse_args()

    headlines = read_headlines(Path(args.queue), Path(args.results))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    open_scheduled()
    for iteration in range(args.max_delete):
        record = delete_one(headlines)
        record["iteration"] = iteration
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if record["status"] == "no-match":
            return 0
        if record["status"] != "deleted":
            return 1
        open_scheduled()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
