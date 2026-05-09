#!/usr/bin/env python3
"""Prepare and generate the corrected AI Inspire shortform queue for 7r_WJ9xpne0."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aiinspire_infographic_batch as old  # noqa: E402
import aiinspire_onego_batch as onego  # noqa: E402


BKK = timezone(timedelta(hours=7))
SOURCE_URL = "https://www.youtube.com/watch?v=7r_WJ9xpne0"
DEFAULT_INPUT = Path("/tmp/qone-redo/redo-short-7rWJ9xpne0/artemis-shortform-queue.json")
OUT_DIR = ROOT / "output/facebook/qone-redo-short-7rWJ9xpne0"
PROMPTS_DIR = OUT_DIR / "prompts"
IMAGES_DIR = OUT_DIR / "images"
CAPTIONS_DIR = OUT_DIR / "captions"
QUEUE_JSON = OUT_DIR / "schedule-queue.json"
MANIFEST_JSON = OUT_DIR / "manifest.json"
CONTACT_SHEET = OUT_DIR / "contact-sheet.jpg"
FINAL_SHARE_DIR = Path("/mnt/c/MyDoc/claw_file/projects/qone-redo-short-7rWJ9xpne0")

REUSE_IMAGES = {
    "Recursive multi-agent systems": "/mnt/c/MyDoc/claw_file/projects/qone-gptimage2-redo/final/recursive-agents-onego.png",
    "Vista 4D turns video into editable 4D scenes": "/mnt/c/MyDoc/claw_file/projects/qone-gptimage2-redo/final/vista-4d.png",
    "Agent-native research artifacts / ARA": "/mnt/c/MyDoc/claw_file/projects/qone-gptimage2-redo/final/ara-v2.png",
    "Claude for Creative Work connectors": "/mnt/c/MyDoc/claw_file/projects/qone-gptimage2-redo/final/claude-creative.png",
    "Talkie 13B vintage model": "/mnt/c/MyDoc/claw_file/projects/qone-gptimage2-redo/final/talkie-13b.png",
}

HASHTAGS = "#AINews #AIInspire #GenerativeAI #AIAgents #ArtificialIntelligence"


def slugify(text: str) -> str:
    return old.slugify(text)


def ensure_dirs() -> None:
    for path in (OUT_DIR, PROMPTS_DIR, IMAGES_DIR, CAPTIONS_DIR, FINAL_SHARE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def parse_start(value: str) -> datetime:
    raw = value.strip().replace("Z", "+00:00")
    if "T" not in raw and " " in raw:
        raw = raw.replace(" ", "T", 1)
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BKK)
    return dt.astimezone(BKK)


def caption_text(item: dict) -> str:
    text = (item["textThai"] or "").strip()
    timestamp = item.get("sourceTimestampRange", "").strip()
    return (
        f"{item['hook'].strip()}\n\n"
        f"{text}\n\n"
        f"ช่วงในคลิป: {timestamp}\n"
        f"ที่มา: AI Search — {SOURCE_URL}\n\n"
        f"{HASHTAGS}"
    )


def image_prompt(item: dict) -> str:
    bullets = "\n".join(f"- {bullet}" for bullet in item["bulletsForImage"])
    return f"""Use local image {onego.TEMPLATE} as the fixed AI Inspire Facebook template reference.

Create ONE finished square Facebook infographic in a single generated image. Do not rely on later compositing for the main design.

STRICT TEMPLATE RULES:
- Preserve the bottom bar exactly as shown in the template reference.
- Do not cover, move, crop, repaint, blur, distort, or alter the bottom bar.
- Keep the AI INSPIRE text/logo on bottom left exactly visible.
- Keep the circular brain logo on bottom right exactly visible and unobstructed.
- All new infographic content must stay above the bottom bar.
- No rectangular patch around the brain logo. The brain logo area must remain circular.

LAYOUT:
- Left side: clean infographic content.
- Right side: meaningful visual/image area, about 40% of total width.
- Keep the left 60% mostly white/light so the Thai infographic text is readable.
- Blend the split naturally with smoke, soft particles, diagonal light, or brush texture. Do not use a hard straight vertical mask.
- Main visual objects must stay mostly in the upper-right content area, away from the footer and brain logo.

INFOGRAPHIC TEXT:
Headline: {item['subject']}
Subheadline: {item['hook']}

Key points, all complete and readable with no ellipsis:
{bullets}

VISUAL:
{item['visualDirection']}

STYLE:
- Match the approved AI Inspire theme: navy/dark blue, white, and gold accents.
- Polished editorial technology infographic like a premium AI news card.
- Avoid generic neon cyberpunk colors.
- Use icon-led rows, gold number badges, clear Thai typography, and high contrast.
- Do not add fake logos, watermarks, source paths, QR codes, or tiny unreadable UI text.
- Ensure all headline and bullet text is complete, readable, and not clipped.
"""


def contact_sheet(records: list[dict]) -> None:
    cols = 5
    cell_w, cell_h = 260, 302
    rows = (len(records) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#E9EEF2")
    font = old.font(15, latin=True)
    for idx, record in enumerate(records):
        im = Image.open(record["imagePath"]).convert("RGB")
        im.thumbnail((238, 238), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (cell_w, cell_h), "#F7F9FB")
        tile.paste(im, ((cell_w - im.width) // 2, 10))
        draw = ImageDraw.Draw(tile)
        draw.text((12, 252), f"{record['index'] + 1:02d} {record['subject'][:25]}", font=font, fill=old.NAVY)
        sheet.paste(tile, ((idx % cols) * cell_w, (idx // cols) * cell_h))
    sheet.save(CONTACT_SHEET, quality=92)


def generate_item(item: dict, force: bool, reuse_existing: bool) -> dict:
    idx = int(item["queueIndex"])
    key = slugify(item["subject"])
    stem = f"{idx + 1:02d}-{key}"
    prompt_path = PROMPTS_DIR / f"{stem}.txt"
    caption_path = CAPTIONS_DIR / f"{stem}.txt"
    image_path = IMAGES_DIR / f"{stem}.png"
    shared_image_path = FINAL_SHARE_DIR / f"{stem}.png"

    prompt_path.write_text(image_prompt(item), encoding="utf-8")
    caption_path.write_text(caption_text(item), encoding="utf-8")

    reused_from = REUSE_IMAGES.get(item["subject"]) if reuse_existing else None
    if reused_from and Path(reused_from).exists():
        if force or not image_path.exists():
            shutil.copyfile(reused_from, image_path)
    elif force or not image_path.exists():
        tmp_path = image_path.with_name(f"{image_path.stem}.tmp.png")
        print(f"generating {idx + 1:02d}: {item['subject']}", flush=True)
        onego.run_gptimg(prompt_path, tmp_path)
        onego.protect_template_regions(tmp_path)
        tmp_path.replace(image_path)
    else:
        onego.protect_template_regions(image_path)

    onego.protect_template_regions(image_path)
    verify = onego.verify_image(image_path)
    shutil.copyfile(image_path, shared_image_path)
    return {
        "index": idx,
        "sourceIndex": item["index"],
        "subject": item["subject"],
        "hook": item["hook"],
        "sourceTimestampRange": item["sourceTimestampRange"],
        "captionPath": str(caption_path),
        "promptPath": str(prompt_path),
        "imagePath": str(shared_image_path),
        "workspaceImagePath": str(image_path),
        "text": caption_path.read_text(encoding="utf-8"),
        "images": [str(shared_image_path)],
        "reusedFrom": reused_from,
        **verify,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--start-at", default="2026-05-06T20:30:00+07:00")
    parser.add_argument("--interval-hours", type=float, default=2.0)
    parser.add_argument("--only", type=int, help="1-based queue index to generate")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-reuse", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    raw_items = json.loads(Path(args.input).read_text(encoding="utf-8"))
    for queue_index, item in enumerate(raw_items):
        item["queueIndex"] = queue_index

    if args.only:
        raw_items = [item for item in raw_items if int(item["queueIndex"]) == args.only - 1]

    base = parse_start(args.start_at)
    records = []
    for item in raw_items:
        if args.prepare_only:
            idx = int(item["queueIndex"])
            key = slugify(item["subject"])
            stem = f"{idx + 1:02d}-{key}"
            prompt_path = PROMPTS_DIR / f"{stem}.txt"
            caption_path = CAPTIONS_DIR / f"{stem}.txt"
            prompt_path.write_text(image_prompt(item), encoding="utf-8")
            caption_path.write_text(caption_text(item), encoding="utf-8")
            continue
        records.append(generate_item(item, args.force, not args.no_reuse))

    if args.prepare_only:
        print(json.dumps({"prepared": len(raw_items), "prompts": str(PROMPTS_DIR)}, ensure_ascii=False))
        return 0

    if not args.only:
        queue = []
        for record in records:
            scheduled_at = base + timedelta(hours=args.interval_hours * int(record["index"]))
            queue.append(
                {
                    "index": record["index"],
                    "sourceIndex": record["sourceIndex"],
                    "subject": record["subject"],
                    "scheduledAt": scheduled_at.isoformat(),
                    "captionPath": record["captionPath"],
                    "imagePath": record["imagePath"],
                    "images": record["images"],
                    "text": record["text"],
                    "sourceTimestampRange": record["sourceTimestampRange"],
                }
            )
        QUEUE_JSON.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
        contact_sheet(records)

    MANIFEST_JSON.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(BKK).isoformat(),
                "sourceUrl": SOURCE_URL,
                "count": len(records),
                "allVerified": all(r["bottom_bar_identical"] and r["brain_logo_identical"] for r in records),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"count": len(records), "queue": str(QUEUE_JSON), "manifest": str(MANIFEST_JSON)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
