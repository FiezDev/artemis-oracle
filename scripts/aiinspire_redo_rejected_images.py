#!/usr/bin/env python3
"""Regenerate rejected qone-redo-short images with the approved Talkie style."""

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
OUT_DIR = ROOT / "output/facebook/qone-redo-short-7rWJ9xpne0"
IMAGES_DIR = OUT_DIR / "images"
PROMPTS_DIR = OUT_DIR / "redo-prompts-v2"
MANIFEST = OUT_DIR / "redo-rejected-v2-manifest.json"
CONTACT = OUT_DIR / "redo-rejected-v2-contact-sheet.jpg"
REFERENCE = IMAGES_DIR / "pass/18-talkie-13b-vintage-model.png"
QUEUE = Path("/tmp/qone-redo/redo-short-7rWJ9xpne0/artemis-shortform-queue.json")
SHARE_DIR = Path("/mnt/c/MyDoc/claw_file/projects/qone-redo-short-7rWJ9xpne0")


REDO = {
    1: {
        "display": "Omnishot Cut",
        "kicker": "AI VIDEO EDIT DETECTION",
        "thai": "โมเดลตรวจคัตและทรานซิชันในวิดีโอ",
        "bullets": [
            ("Cut detection", "หาจุดตัดต่อบน timeline อัตโนมัติ"),
            ("Transition labels", "แยก hard cut, fade, dissolve, slide"),
            ("Small model", "ขนาดประมาณ 164 MB ใช้งานง่าย"),
            ("Creator workflow", "ช่วยหา timestamp ในคลิปยาวเร็วขึ้น"),
        ],
        "visual": (
            "a premium video-editing timeline command center: film strips, cut markers, transition cards, "
            "timecode ruler, and a glowing AI analysis lens. The visual must clearly explain video cut detection."
        ),
    },
    2: {
        "display": "Happy Horse",
        "kicker": "LEADERBOARD VS REAL TEST",
        "thai": "อันดับสูง แต่ prompt ยากยังหลุดได้",
        "bullets": [
            ("Leaderboard #1", "คะแนนสูงไม่ได้แปลว่าดีทุก workflow"),
            ("Real prompt stress", "ฉากต่อเนื่องยากยังหลุดลำดับเหตุการณ์"),
            ("Physics breaks", "motion และ object consistency ยังแกว่ง"),
            ("Seed Dance wins", "ตัวอย่างนี้ Seed Dance 2.0 ทำได้แน่นกว่า"),
        ],
        "visual": (
            "side-by-side evaluation board: left is a gold leaderboard medal, right is a broken video sequence "
            "with frames of a horse/dragon/princess prompt glitching, plus a clear 'real test' diagnostic graph."
        ),
    },
    4: {
        "display": "Link 2.6 Flash",
        "kicker": "EFFICIENT OPEN MODEL",
        "thai": "104B total แต่ active เพียง 7.4B",
        "bullets": [
            ("104B total", "พารามิเตอร์รวมขนาดใหญ่"),
            ("7.4B active", "ตอนใช้งานเปิดจริงน้อยกว่าเยอะ"),
            ("Long context", "เด่นขึ้นเมื่องาน context ยาว"),
            ("Cost focus", "เน้นเร็วและต้นทุนต่ำ"),
        ],
        "visual": (
            "MoE model efficiency dashboard: large 104B parameter block feeding a smaller 7.4B active-core chip, "
            "long-context speed curve, compute-cost gauge, and clean benchmark panel."
        ),
    },
    5: {
        "display": "Zanime",
        "kicker": "FAST ANIME IMAGE MODEL",
        "thai": "โมเดล anime ที่รันเร็วและเบา",
        "bullets": [
            ("6B model", "ขนาดเล็กกว่า image model ใหญ่หลายตัว"),
            ("FP8 + GGUF", "เหมาะกับ local GPU หลายแบบ"),
            ("4-step version", "distilled generation เร็วมาก"),
            ("Full model", "ไม่ใช่แค่ LoRA ธรรมดา"),
        ],
        "visual": (
            "anime image-generation lab: polished character sheet thumbnails, local GPU module, 4-step pipeline, "
            "FP8/GGUF badges. Make it tasteful and clean, not childish."
        ),
    },
    8: {
        "display": "Meta Tuna 2",
        "kicker": "IMAGE GEN + EDIT",
        "thai": "สร้างภาพ แก้ภาพ และทำ text rendering ได้ดี",
        "bullets": [
            ("Generate", "สร้างภาพจาก prompt ได้เข้าใจบริบท"),
            ("Edit", "เปลี่ยน style และ object ได้"),
            ("Text render", "ทำตัวหนังสือในภาพดีขึ้น"),
            ("Weight issue", "น่าเสียดายที่ยังไม่ปล่อยเต็ม"),
        ],
        "visual": (
            "image editor workflow with before/after panels: person to LEGO, object replacement, style transfer, "
            "and text-rendering check. No fake brand logos and no tiny unreadable UI text."
        ),
    },
    9: {
        "display": "AnyRecon",
        "kicker": "SPARSE PHOTOS TO 3D",
        "thai": "รูปไม่กี่มุมก็รวมเป็นฉาก 3D ได้",
        "bullets": [
            ("2-5 views", "รับภาพน้อยและมุมไม่เป็นระเบียบ"),
            ("Scene memory", "จำภาพก่อนหน้าเพื่อคุมโครงสร้าง"),
            ("Point cloud", "รวมเป็นฉาก 3D ที่สอดคล้องกัน"),
            ("Small code", "โค้ดประมาณ 614 MB"),
        ],
        "visual": (
            "four casual photos floating into a coherent 3D point-cloud room, with camera rays, memory nodes, "
            "and a reconstructed scene in navy/gold wireframe."
        ),
    },
    11: {
        "display": "Kai Tactile Humanoid",
        "kicker": "SYNTHETIC SKIN ROBOT",
        "thai": "หุ่น humanoid ที่เริ่มมีผิวสัมผัสทั้งตัว",
        "bullets": [
            ("115 body DOF", "ขยับละเอียดระดับงานบ้านและกีฬา"),
            ("36 hand DOF", "มือมีองศาอิสระสูง"),
            ("Tactile skin", "มีแผ่นผิวสังเคราะห์พร้อม sensor ทั่วแขนและมือ"),
            ("Self-correction", "world model ช่วยแก้งานระยะยาว"),
        ],
        "visual": (
            "humanoid robot Kai with visible synthetic skin panels and tactile sensor grid on arms, hands, torso, "
            "and shoulder; close-up of skin-like flexible surface with glowing pressure points. Do not show a plain "
            "white plastic robot only. The visual must clearly represent full-body tactile skin."
        ),
    },
    13: {
        "display": "Android Heads",
        "kicker": "REALISTIC ROBOT FACES",
        "thai": "หัวหุ่นยนต์เริ่มมี micro-expression เหมือนคน",
        "bullets": [
            ("Synthetic skin", "ผิว ขนตา และตาเริ่มสมจริง"),
            ("Blink + gaze", "กะพริบตาและขยับสายตาได้"),
            ("Micro-expression", "แสดงอารมณ์ละเอียดขึ้น"),
            ("Companion market", "ถูกวางตำแหน่งเป็น robot companion"),
        ],
        "visual": (
            "two realistic android heads on a display bench: one half-transparent showing facial servos under "
            "synthetic skin, with expression control curves and gaze-tracking diagram. Not creepy, premium editorial."
        ),
    },
    14: {
        "display": "SenseNova U1",
        "kicker": "UNIFIED MULTIMODAL MODEL",
        "thai": "คิดและสร้างภาพในระบบเดียว",
        "bullets": [
            ("Text + image input", "รับข้อมูลภาพและข้อความพร้อมกัน"),
            ("Text + image output", "ตอบกลับเป็นภาพหรือข้อความได้"),
            ("Infographic strength", "เด่นกับ poster และ diagram ซับซ้อน"),
            ("Visual reasoning", "เข้าใจภาพและถามตอบจากภาพได้"),
        ],
        "visual": (
            "unified multimodal pipeline: input card with text+image flows through one central model core and outputs "
            "a poster, diagram, and answer card. Use clean node graph and infographic panels."
        ),
    },
    15: {
        "display": "Neotron Nano Omni",
        "kicker": "OPEN OMNI MODEL",
        "thai": "วิดีโอ เสียง ภาพ และข้อความในโมเดลเดียว",
        "bullets": [
            ("Video + audio", "เข้าใจคลิปและเสียงร่วมกัน"),
            ("Image + text", "ทำ OCR และ document reasoning ได้"),
            ("30B MoE", "3B active เพื่อประหยัด compute"),
            ("Open release", "ปล่อยโมเดลและ tooling ให้ต่อยอด"),
        ],
        "visual": (
            "one open-source omni model hub receiving four streams: video, audio waveform, image/document, and text; "
            "central Neotron core, OCR/document panel, video frame strip, and audio spectrogram."
        ),
    },
}


def stem_for(index: int, subject: str) -> str:
    return f"{index:02d}-{old.slugify(subject)}"


def prompt_for(item: dict, spec: dict) -> str:
    bullet_text = "\n".join(f"{i}. {head}\n{body}" for i, (head, body) in enumerate(spec["bullets"], start=1))
    return f"""Use local image {onego.TEMPLATE} as the fixed AI Inspire blank template.
Use local image {REFERENCE} as the APPROVED visual reference for style, density, spacing, and polish.

Regenerate this rejected AI Inspire Facebook infographic so it matches the approved Talkie 13B example more closely.

ABSOLUTE TEMPLATE RULES:
- Bottom bar must remain exactly unchanged.
- Keep AI INSPIRE text/logo on bottom left exactly visible.
- Keep circular brain logo on bottom right exactly visible.
- Do not draw a rectangle around the brain logo; the logo area must remain circular.
- All new content must stay above the bottom bar.

COMPOSITION TARGET:
- Premium editorial infographic like the approved Talkie 13B image.
- White/light left half with a strong navy/gold headline block.
- Rich topic-specific technical visual on the center-right and right side.
- No large empty blank spaces and no plain generic UI card.
- Use navy, white, gold, and restrained cool blue. Avoid neon cyberpunk.
- Blend the right visual naturally into the template brush/shade areas.
- Left margin must be generous: keep all headline text at least 85 px from the left edge.
- Headline must fit fully inside the left half. Use the short display headline below, not the long source title.
- No text clipping, no ellipsis, no cropped words, no overflow outside boxes.
- No fake source paths, QR codes, watermarks, or random logos.

TEXT TO PLACE:
Kicker: {spec['kicker']}
Headline: {spec['display']}
Thai subheadline: {spec['thai']}

Four key points:
{bullet_text}

SOURCE TOPIC:
{item['subject']}
Source timestamp: {item['sourceTimestampRange']}

RIGHT-SIDE VISUAL MUST MATCH THIS TOPIC:
{spec['visual']}

QUALITY BAR:
- The visual must explain the topic at a glance, like the Talkie image explains time-capsule training.
- Use numbered badges, line connectors, labels, and a central/right illustrative object.
- Make the final image look ready to post, not like a draft.
"""


def make_contact(records: list[dict]) -> None:
    cols = 5
    cell_w, cell_h = 270, 310
    rows = (len(records) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#EDF1F5")
    font = old.font(14, latin=True)
    for pos, record in enumerate(records):
        im = Image.open(record["imagePath"]).convert("RGB")
        im.thumbnail((248, 248), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (cell_w, cell_h), "#F8FAFC")
        tile.paste(im, ((cell_w - im.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((12, 263), f"{record['index']:02d} {record['display']}", font=font, fill=old.NAVY)
        sheet.paste(tile, ((pos % cols) * cell_w, (pos // cols) * cell_h))
    sheet.save(CONTACT, quality=92)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, action="append", help="1-based source index to regenerate")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = {int(row["index"]): row for row in data}
    selected = args.only or sorted(REDO)

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    SHARE_DIR.mkdir(parents=True, exist_ok=True)

    backup = IMAGES_DIR / f"rejected-backup-{datetime.now(BKK).strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)

    records = []
    for index in selected:
        item = items[index]
        spec = REDO[index]
        stem = stem_for(index, item["subject"])
        prompt_path = PROMPTS_DIR / f"{stem}.txt"
        image_path = IMAGES_DIR / f"{stem}.png"
        shared_path = SHARE_DIR / f"{stem}.png"
        if image_path.exists():
            shutil.copy2(image_path, backup / image_path.name)
        prompt_path.write_text(prompt_for(item, spec), encoding="utf-8")
        tmp = image_path.with_name(f"{image_path.stem}.redo.tmp.png")
        if args.force or not image_path.exists() or image_path.exists():
            print(f"regenerating {index:02d}: {spec['display']}", flush=True)
            onego.run_gptimg(prompt_path, tmp, reference_images=[onego.TEMPLATE, REFERENCE])
            onego.protect_template_regions(tmp)
            tmp.replace(image_path)
        onego.protect_template_regions(image_path)
        shutil.copy2(image_path, shared_path)
        verify = onego.verify_image(image_path)
        records.append(
            {
                "index": index,
                "subject": item["subject"],
                "display": spec["display"],
                "promptPath": str(prompt_path),
                "imagePath": str(image_path),
                "sharedPath": str(shared_path),
                **verify,
            }
        )

    make_contact(records)
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(BKK).isoformat(),
                "reference": str(REFERENCE),
                "backup": str(backup),
                "count": len(records),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"count": len(records), "manifest": str(MANIFEST), "contactSheet": str(CONTACT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
