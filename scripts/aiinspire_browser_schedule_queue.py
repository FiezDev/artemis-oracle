#!/usr/bin/env python3
"""Schedule the AI Inspire queue through the browser-based Facebook helper."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BKK = timezone(timedelta(hours=7))
DEFAULT_QUEUE = ROOT / "output/facebook/aisearch-final-v2/schedule-queue.json"
DEFAULT_RESULTS = ROOT / "output/facebook/aisearch-final-v2/browser-schedule-results.jsonl"
DEFAULT_PAGE = "1136813799507714"


def next_half_hour() -> datetime:
    now = datetime.now(BKK)
    start = now + timedelta(minutes=45)
    if start.minute == 0:
        rounded = start
    elif start.minute <= 30:
        rounded = start.replace(minute=30)
    else:
        rounded = (start + timedelta(hours=1)).replace(minute=0)
    return rounded.replace(second=0, microsecond=0)


def parse_dt(value: str) -> datetime:
    raw = value.strip()
    if "T" not in raw and " " in raw:
        raw = raw.replace(" ", "T", 1)
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BKK)
    return dt.astimezone(BKK)


def choose_base(queue: list[dict], explicit: str | None) -> datetime:
    if explicit:
        return parse_dt(explicit)
    queued = parse_dt(queue[0]["scheduledAt"])
    if queued > datetime.now(BKK) + timedelta(minutes=20):
        return queued
    return next_half_hour()


def read_successes(path: Path) -> set[int]:
    if not path.exists():
        return set()
    done: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("rc") == 0:
            done.add(int(row["index"]))
    return done


def tail_text(value: str, limit: int = 1800) -> str:
    return value[-limit:] if len(value) > limit else value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default=str(DEFAULT_QUEUE))
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--page-id", default=DEFAULT_PAGE)
    parser.add_argument("--start-at", help="ISO local/offset time for the first post")
    parser.add_argument("--interval-hours", type=float, default=2.0)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--use-vault-login", action="store_true")
    parser.add_argument("--close-between-posts", action="store_true")
    args = parser.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    base = choose_base(queue, args.start_at)
    results_path = Path(args.results)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    done = read_successes(results_path) if args.resume else set()
    pending = [item for item in queue if int(item["index"]) not in done]
    print(
        json.dumps(
            {
                "queue": len(queue),
                "alreadyDone": len(done),
                "pending": len(pending),
                "base": base.isoformat(),
                "results": str(results_path),
                "dryRun": args.dry_run,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    for item in pending:
        idx = int(item["index"])
        scheduled_at = base + timedelta(hours=args.interval_hours * idx)
        image_paths = item.get("images") or [item["imagePath"]]
        print(f"scheduling {idx:02d} {item['subject']} at {scheduled_at.isoformat()}", flush=True)

        record = {
            "index": idx,
            "subject": item["subject"],
            "scheduled_at": scheduled_at.isoformat(),
            "image_paths": image_paths,
            "dryRun": args.dry_run,
        }
        if args.dry_run:
            record["rc"] = 0
            with results_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            continue

        cmd = [
            "python3",
            "scripts/facebook-post.py",
            "--page-id",
            args.page_id,
            "--schedule-at",
            scheduled_at.isoformat(),
            "--text",
            item["text"],
        ]
        if not args.use_vault_login:
            cmd.append("--skip-login")
        if not args.close_between_posts:
            cmd.append("--keep-open")
        for image_path in image_paths:
            cmd.extend(["--image", image_path])

        started = time.monotonic()
        proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=180)
        elapsed = round(time.monotonic() - started, 1)
        record.update(
            {
                "rc": proc.returncode,
                "elapsed_s": elapsed,
                "stdout_tail": tail_text(proc.stdout),
                "stderr_tail": tail_text(proc.stderr),
            }
        )
        with results_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if proc.returncode != 0 and not args.continue_on_error:
            print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
            return proc.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
