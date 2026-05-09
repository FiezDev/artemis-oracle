#!/usr/bin/env python3
"""Filter an AI Inspire queue so already scheduled subjects are not scheduled again."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AB = "/home/bjgdr/.linuxbrew/bin/agent-browser"
PAGE_ID = "1136813799507714"
SCHEDULED_URL = f"https://business.facebook.com/latest/posts/scheduled_posts/?asset_id={PAGE_ID}"

DEFAULT_EXCLUDE_PATTERNS = [
    "recursive",
    "latent collaboration",
    "vista 4d",
    "ฉาก 4d",
    "agent-native research artifacts",
    "ara",
    "claude for creative work",
    "creative software",
    "talkie",
    "1931",
    "deepseek v4",
]


def ab(*args: str, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess[str]:
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


def scheduled_texts_from_meta() -> list[str]:
    ab("open", SCHEDULED_URL, timeout=120)
    time.sleep(6)
    raw = eval_js(
        """
(() => JSON.stringify(Array.from(document.querySelectorAll('input[aria-label*="Tick item with caption"]')).map((e) => {
  const row = e.closest('[role=row], tr') || e.parentElement;
  return (row?.innerText || e.getAttribute('aria-label') || '').slice(0, 1600);
})))()
"""
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def pattern_hit(text: str, patterns: list[str]) -> str | None:
    lowered = text.casefold()
    for pattern in patterns:
        if pattern.casefold() in lowered:
            return pattern
    return None


def subject_hit(subject: str, existing_texts: list[str], extra_patterns: list[str]) -> str | None:
    subject_patterns = [subject]
    if "Recursive" in subject:
        subject_patterns += ["recursive", "latent collaboration"]
    if "Vista 4D" in subject:
        subject_patterns += ["vista 4d", "ฉาก 4d"]
    if "Agent-native" in subject or "ARA" in subject:
        subject_patterns += ["agent-native research artifacts", "ara"]
    if "Claude" in subject:
        subject_patterns += ["claude", "creative software"]
    if "Talkie" in subject:
        subject_patterns += ["talkie", "1931"]
    subject_patterns += extra_patterns
    for text in existing_texts:
        hit = pattern_hit(text, subject_patterns)
        if hit:
            return hit
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--meta", action="store_true", help="Read current Meta scheduled rows before filtering")
    parser.add_argument("--exclude", action="append", default=[], help="Additional literal pattern to exclude")
    parser.add_argument("--renumber", action="store_true", help="Renumber kept queue items from zero for scheduling")
    parser.add_argument("--report", help="Write filter report JSON")
    args = parser.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    existing_texts = scheduled_texts_from_meta() if args.meta else []
    if not existing_texts:
        existing_texts = DEFAULT_EXCLUDE_PATTERNS

    kept = []
    skipped = []
    for item in queue:
        hit = subject_hit(item["subject"], existing_texts, args.exclude)
        if hit:
            skipped.append({"index": item["index"], "subject": item["subject"], "matched": hit})
        else:
            kept.append(item)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.renumber:
        kept = [{**item, "originalIndex": item["index"], "index": idx} for idx, item in enumerate(kept)]

    out.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {"input": len(queue), "kept": len(kept), "skipped": skipped, "output": str(out)}
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
