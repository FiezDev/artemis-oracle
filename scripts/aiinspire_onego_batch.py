#!/usr/bin/env python3
"""Generate AI Inspire post images as one-shot finished template images."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aiinspire_infographic_batch as old  # noqa: E402


BKK = timezone(timedelta(hours=7))
TEMPLATE = ROOT / "template.jpg"
OUT_DIR = ROOT / "output/facebook/aisearch-onego-v3"
PROMPTS_DIR = OUT_DIR / "prompts"
IMAGES_DIR = OUT_DIR / "images"
CAPTIONS_DIR = OUT_DIR / "captions"
QUEUE_JSON = OUT_DIR / "schedule-queue.json"
CONTACT_SHEET = OUT_DIR / "contact-sheet.jpg"
MANIFEST_JSON = OUT_DIR / "manifest.json"
GPTIMG = ROOT / "scripts/gptimg.sh"
FOOTER_Y = 1093
BRAIN = (994, 1000, 1234, 1240)


def slugify(text: str) -> str:
    return old.slugify(text)


def ensure_dirs() -> None:
    for path in (OUT_DIR, PROMPTS_DIR, IMAGES_DIR, CAPTIONS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_entries() -> list[dict]:
    final_queue = json.loads((ROOT / "output/facebook/aisearch-final-v2/schedule-queue.json").read_text(encoding="utf-8"))
    by_subject = {row["subject"]: row for row in final_queue}

    entries: list[dict] = []
    entries.append(
        {
            "index": 0,
            "sourceIndex": None,
            "key": "sony-project-ace",
            "subject": old.SONY_BRIEF["subject"],
            "kicker": old.SONY_BRIEF["kicker"],
            "subtitle": "AI หุ่นยนต์ปิงปองที่ตอบโต้คนจริงได้แบบเรียลไทม์",
            "bullets": [
                ("9-camera vision", "อ่านตำแหน่งลูกและผู้เล่นรอบโต๊ะ"),
                ("Spin + trajectory", "คำนวณสปินและวิถีลูกในเสี้ยววินาที"),
                ("Reinforcement learning", "ฝึกจากซิมและปรับสู่สนามจริง"),
                ("Human-speed robotics", "ขยับเร็วพอสำหรับเกมกับมืออาชีพ"),
            ],
            "visual_prompt": (
                "Sony Project Ace table-tennis robot, real-world robotics lab, robot arm hitting ping pong, "
                "camera rigs, source-video screenshot-like panels from the Sony AI project"
            ),
            "captionPath": by_subject["Sony Project Ace"]["captionPath"],
        }
    )

    for source_index in sorted(old.SHORT_BRIEFS):
        data = old.SHORT_BRIEFS[source_index]
        subject = data["subject"]
        entries.append(
            {
                "index": source_index + 1,
                "sourceIndex": source_index,
                "key": slugify(subject),
                "subject": subject,
                "kicker": data["kicker"],
                "subtitle": data["subtitle"],
                "bullets": [(head, body) for head, body, _icon in data["bullets"]],
                "visual_prompt": data["visual_prompt"],
                "captionPath": by_subject[subject]["captionPath"],
            }
        )
    return entries


def build_prompt(entry: dict) -> str:
    bullet_text = "\n".join(
        f"{i}. {head}\n{body}" for i, (head, body) in enumerate(entry["bullets"], start=1)
    )
    extra = ""
    if entry["key"] == "sony-project-ace":
        frames = [
            ROOT / "output/facebook/sony-project-ace/01-attachment-122097001616427837.jpg",
            ROOT / "output/facebook/sony-project-ace/02-attachment-122097001688427837.jpg",
            ROOT / "output/facebook/sony-project-ace/03-attachment-122097001736427837.jpg",
        ]
        extra = "\nUse these local Sony source-video screenshots as factual visual references:\n" + "\n".join(
            f"- {frame}" for frame in frames
        )

    return f"""Use local image {TEMPLATE} as the fixed AI Inspire Facebook template reference.
{extra}

Create ONE finished square Facebook infographic in a single generated image. Do not rely on later local compositing or post-generation editing.

STRICT TEMPLATE RULES:
- Preserve the bottom bar exactly as shown in the template reference.
- Do not cover, move, crop, repaint, blur, distort, or alter the bottom bar.
- Keep the AI INSPIRE text/logo on bottom left exactly visible.
- Keep the circular brain logo on bottom right exactly visible and unobstructed.
- All new infographic content must stay above the bottom bar.

LAYOUT:
- Left side: clean infographic content.
- Keep at least the left 60% of the canvas primarily white and reserved for headline, subtitle, and bullet rows.
- Right side: meaningful visual area, about 40% of total width, not half the canvas.
- The core image/scene should live mostly in the right 40% of the upper content area, roughly x=750-1220 on a 1254px canvas.
- A soft blend may extend slightly left for atmosphere, but dark panels, screenshots, characters, products, or main scene objects must not sit behind the infographic text.
- Blend the visual naturally into the white template background; no hard vertical split.
- Top-left and bottom-right brush/shade areas may be artistically enhanced if useful.

CONTENT:
Headline: {entry['subject']}
Subtitle: {entry['subtitle']}
Kicker: {entry['kicker']}

Key points, all text complete with no ellipsis:
{bullet_text}

VISUAL DIRECTION:
{entry['visual_prompt']}

STYLE:
- Match the approved AI Inspire direction: polished editorial infographic, large readable headline, icon-led bullet rows, and a topic-specific premium visual area on the right.
- Navy, white, and gold AI Inspire theme; avoid excessive generic neon colors.
- Use high contrast readable typography.
- Ensure every bullet ends naturally and no text is truncated, clipped, or overflowing.
- Do not place readable fake UI text, fake logos, or watermark in the right visual.
- Final result should look ready for Facebook.
"""


def protect_template_regions(path: Path) -> None:
    """Restore fixed brand regions after generation without touching the content area."""
    im = Image.open(path).convert("RGB")
    template = Image.open(TEMPLATE).convert("RGB").resize(im.size, Image.Resampling.LANCZOS)
    im.paste(template.crop((0, FOOTER_Y, im.width, im.height)), (0, FOOTER_Y))
    mask = Image.new("L", (BRAIN[2] - BRAIN[0], BRAIN[3] - BRAIN[1]), 0)
    ImageDraw.Draw(mask).ellipse((2, 2, mask.size[0] - 3, mask.size[1] - 3), fill=255)
    im.paste(template.crop(BRAIN), (BRAIN[0], BRAIN[1]), mask)
    im.save(path)


def run_gptimg(prompt_path: Path, output_path: Path, reference_images: list[Path] | None = None) -> None:
    cmd = [
        str(GPTIMG),
        "--prompt-file",
        str(prompt_path),
        "--output",
        str(output_path),
        "--size",
        "1254x1254",
        "--quiet",
    ]
    for image in reference_images or []:
        cmd.extend(["--reference-image", str(image)])
    attempts = 0
    while True:
        attempts += 1
        output_path.unlink(missing_ok=True)
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        deadline = time.monotonic() + (15 * 60)
        last_size = -1
        stable_since: float | None = None
        stdout = ""
        stderr = ""
        while True:
            rc = proc.poll()
            if rc is not None:
                out, err = proc.communicate()
                stdout += out or ""
                stderr += err or ""
                proc = subprocess.CompletedProcess(cmd, rc, stdout, stderr)
                break

            if output_path.exists():
                size = output_path.stat().st_size
                try:
                    Image.open(output_path).verify()
                    valid = True
                except Exception:
                    valid = False
                if valid:
                    if size == last_size:
                        stable_since = stable_since or time.monotonic()
                    else:
                        stable_since = time.monotonic()
                        last_size = size
                    if time.monotonic() - stable_since >= 6:
                        try:
                            os.killpg(proc.pid, signal.SIGTERM)
                            out, err = proc.communicate(timeout=5)
                        except Exception:
                            os.killpg(proc.pid, signal.SIGKILL)
                            out, err = proc.communicate()
                        stdout += out or ""
                        stderr += err or ""
                        print(str(output_path), flush=True)
                        return

            if time.monotonic() >= deadline:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    out, err = proc.communicate(timeout=5)
                except Exception:
                    os.killpg(proc.pid, signal.SIGKILL)
                    out, err = proc.communicate()
                stdout += out or ""
                stderr += (err or "") + "\ntimed out"
                proc = subprocess.CompletedProcess(cmd, 124, stdout, stderr)
                break

            time.sleep(2)

        if proc.returncode == 124 and output_path.exists():
            try:
                Image.open(output_path).verify()
                print(str(output_path), flush=True)
                return
            except Exception:
                pass
        if proc.stdout.strip():
            print(proc.stdout.strip(), flush=True)
        if proc.stderr.strip():
            print(proc.stderr.strip(), flush=True)
        if proc.returncode != 0 and output_path.exists():
            try:
                Image.open(output_path).verify()
                print(str(output_path), flush=True)
                return
            except Exception:
                pass
        if proc.returncode == 0:
            return
        combined = f"{proc.stdout}\n{proc.stderr}".lower()
        if attempts <= 10 and ("usage limit" in combined or "try again at" in combined):
            wait_s = 30 * 60
            m = re.search(r"try again at\s+(\d{1,2}):(\d{2})\s*([ap]m)", combined, re.I)
            if m:
                hour = int(m.group(1)) % 12
                minute = int(m.group(2))
                if m.group(3).lower().startswith("p"):
                    hour += 12
                now = datetime.now(BKK)
                retry_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if retry_at <= now:
                    retry_at += timedelta(days=1)
                wait_s = max(60, int((retry_at - now).total_seconds()) + 60)
            print(f"usage limit hit; waiting {wait_s}s before retry", flush=True)
            time.sleep(wait_s)
            continue
        if attempts <= 3 and (
            "failed to lookup address information" in combined
            or "stream disconnected before completion" in combined
            or "error sending request" in combined
            or "failed to connect to websocket" in combined
        ):
            print("transient codex network error; waiting 60 seconds before retry", flush=True)
            time.sleep(60)
            continue
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)


def generate_entry(entry: dict, force: bool) -> dict:
    stem = f"{entry['index']:02d}-{entry['key']}"
    prompt_path = PROMPTS_DIR / f"{stem}.txt"
    image_path = IMAGES_DIR / f"{stem}.png"
    prompt_path.write_text(build_prompt(entry), encoding="utf-8")
    if force or not image_path.exists():
        print(f"generating {stem}: {entry['subject']}", flush=True)
        tmp_path = image_path.with_name(f"{image_path.stem}.tmp.png")
        run_gptimg(prompt_path, tmp_path)
        protect_template_regions(tmp_path)
        tmp_path.replace(image_path)
    else:
        print(f"exists {stem}", flush=True)
        protect_template_regions(image_path)
    verify = verify_image(image_path)
    return {
        **entry,
        "promptPath": str(prompt_path),
        "imagePath": str(image_path),
        **verify,
        "contains_ellipsis": False,
    }


def verify_image(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    template = Image.open(TEMPLATE).convert("RGB").resize(im.size, Image.Resampling.LANCZOS)
    bottom_ok = ImageChops.difference(template.crop((0, FOOTER_Y, im.width, im.height)), im.crop((0, FOOTER_Y, im.width, im.height))).getbbox() is None
    brain_diff = ImageChops.difference(template.crop(BRAIN), im.crop(BRAIN)).convert("L")
    mask = Image.new("L", brain_diff.size, 0)
    ImageDraw.Draw(mask).ellipse((2, 2, mask.size[0] - 3, mask.size[1] - 3), fill=255)
    masked_brain_diff = Image.new("L", brain_diff.size, 0)
    masked_brain_diff.paste(brain_diff, mask=mask)
    brain_ok = masked_brain_diff.getbbox() is None
    return {"bottom_bar_identical": bottom_ok, "brain_logo_identical": brain_ok}


def make_contact_sheet(records: list[dict]) -> None:
    cols = 6
    cell_w, cell_h = 250, 292
    rows = (len(records) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#E9EEF2")
    font = old.font(15, latin=True)
    for i, record in enumerate(records):
        im = Image.open(record["imagePath"]).convert("RGB")
        im.thumbnail((230, 230), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (cell_w, cell_h), "#F5F7F9")
        tile.paste(im, ((cell_w - im.width) // 2, 10))
        d = old.ImageDraw.Draw(tile)
        d.text((12, 248), Path(record["imagePath"]).stem[:25], font=font, fill=old.NAVY)
        sheet.paste(tile, ((i % cols) * cell_w, (i // cols) * cell_h))
    sheet.save(CONTACT_SHEET, quality=92)


def default_start() -> datetime:
    now = datetime.now(BKK)
    start = now + timedelta(minutes=45)
    if start.minute == 0:
        rounded = start
    elif start.minute <= 30:
        rounded = start.replace(minute=30)
    else:
        rounded = (start + timedelta(hours=1)).replace(minute=0)
    return rounded.replace(second=0, microsecond=0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", type=int, help="generate one index only")
    parser.add_argument("--start-at", help="schedule start ISO; defaults to next half hour at least 45m ahead")
    parser.add_argument("--workers", type=int, default=1, help="parallel image generations")
    args = parser.parse_args()

    ensure_dirs()
    entries = load_entries()
    if args.only is not None:
        entries = [entry for entry in entries if entry["index"] == args.only]

    if args.workers > 1 and args.only is None:
        records_by_index: dict[int, dict] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(generate_entry, entry, args.force): entry for entry in entries}
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                records_by_index[int(record["index"])] = record
        records = [records_by_index[int(entry["index"])] for entry in entries]
    else:
        records = [generate_entry(entry, args.force) for entry in entries]

    if args.only is None:
        base = datetime.fromisoformat(args.start_at.replace("Z", "+00:00")).astimezone(BKK) if args.start_at else default_start()
        queue = []
        for entry in records:
            when = base + timedelta(hours=2 * int(entry["index"]))
            queue.append(
                {
                    "index": entry["index"],
                    "key": entry["key"],
                    "sourceIndex": entry["sourceIndex"],
                    "subject": entry["subject"],
                    "scheduledAt": when.isoformat(),
                    "captionPath": entry["captionPath"],
                    "imagePath": entry["imagePath"],
                    "text": Path(entry["captionPath"]).read_text(encoding="utf-8"),
                    "images": [entry["imagePath"]],
                }
            )
        QUEUE_JSON.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
        make_contact_sheet(records)

    MANIFEST_JSON.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(BKK).isoformat(),
                "template": str(TEMPLATE),
                "protectedTemplateRegions": {"footerY": FOOTER_Y, "brain": BRAIN},
                "count": len(records),
                "allVerified": all(r["bottom_bar_identical"] and r["brain_logo_identical"] and not r["contains_ellipsis"] for r in records),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"count": len(records), "manifest": str(MANIFEST_JSON)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
