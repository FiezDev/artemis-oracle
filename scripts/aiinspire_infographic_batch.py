#!/usr/bin/env python3
"""Regenerate AI Inspire Facebook infographic assets and schedule payloads.

This script consumes the already-collected AI Search post data under
output/facebook/aisearch-reschedule and creates final AI Inspire images using
the approved format:

- protected AI Inspire footer and brain logo
- left-side infographic area
- topic-specific right-side visual, generated as roughly 40% of the canvas
- no ellipsis truncation in bullet copy
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aiinspire_recheck_samples import (  # noqa: E402
    BRAIN_LOGO_BBOX,
    FOOTER_Y,
    GOLD,
    H,
    INK,
    LINE,
    MUTED,
    NAVY,
    PAPER,
    TEMPLATE,
    W,
    brain_logo_mask,
    clean_base_from_template,
    draw_ref_icon,
    draw_strong,
    fit_font,
    font,
    hex_to_rgb,
    paste_brain_logo,
    text_width,
    wrap_text,
)

SOURCE_POSTS = ROOT / "output/facebook/aisearch-reschedule/posts.json"
SOURCE_CAPTIONS = ROOT / "output/facebook/aisearch-reschedule/captions"
SONY_DIR = ROOT / "output/facebook/sony-project-ace"
OUT_DIR = ROOT / "output/facebook/aisearch-final-v2"
IMAGES_DIR = OUT_DIR / "images"
UPPER_DIR = OUT_DIR / "upper"
PROMPT_DIR = OUT_DIR / "upper-prompts"
CAPTIONS_DIR = OUT_DIR / "captions"
QUEUE_JSON = OUT_DIR / "schedule-queue.json"
CONTACT_SHEET = OUT_DIR / "contact-sheet.jpg"
MANIFEST_JSON = OUT_DIR / "manifest.json"
GPTIMG = ROOT / "scripts/gptimg.sh"

BKK = timezone(timedelta(hours=7))


@dataclass(frozen=True)
class Brief:
    key: str
    source_index: int | None
    subject: str
    kicker: str
    subtitle: str
    badge: str
    bullets: tuple[tuple[str, str, str], ...]
    visual_prompt: str
    image_path: Path
    caption_path: Path
    output_stem: str


SHORT_BRIEFS: dict[int, dict] = {
    0: {
        "subject": "Multiworld",
        "kicker": "MULTI-VIEW GAME DATA",
        "subtitle": "AI สร้างฉากเกมหลายตัวละครพร้อมหลายมุมกล้อง",
        "badge": "WORLD",
        "bullets": [
            ("Multi-character scenes", "ฉากหลายตัวละครซิงก์กันในหลายมุมกล้อง", "people"),
            ("Synced camera views", "แต่ละกล้องเห็นโลกเดียวกันจากมุมที่ต่างกัน", "camera"),
            ("Open code + data", "เปิดโค้ด dataset และ checkpoint ให้ต่อยอดได้", "code"),
            ("Robotics training", "เหมาะกับข้อมูลฝึกหุ่นยนต์แบบหลายมุมมอง", "robot"),
        ],
        "visual_prompt": "multi-agent game world generation, several characters in one coherent scene, synchronized camera feeds, robotics training data, cinematic game-development dashboard",
    },
    1: {
        "subject": "OpenGame",
        "kicker": "AGENTIC GAME DEV",
        "subtitle": "AI agent ที่สร้างเกมได้ตั้งแต่ design จน playable",
        "badge": "DEV",
        "bullets": [
            ("End-to-end agent", "ออกแบบ เขียน และทดสอบเกมใน workflow เดียว", "game"),
            ("GameCoder-27B", "โมเดลโค้ดเฉพาะทางทำงานคู่กับ skill library", "code"),
            ("Debug memory", "จดบัคและวิธีแก้เพื่อใช้ซ้ำในโปรเจกต์ถัดไป", "debug"),
            ("Playable demos", "โชว์เกมที่เล่นได้จริง ไม่ใช่แค่ mockup จาก prompt", "play"),
        ],
        "visual_prompt": "agentic game development pipeline, pixel platform game preview on a futuristic workstation, code panels, debug memory nodes, clean product infographic art",
    },
    2: {
        "subject": "UniGenDet",
        "kicker": "IMAGE GEN + DETECT",
        "subtitle": "โมเดลเดียวที่สร้างภาพและตรวจภาพ AI ได้พร้อมกัน",
        "badge": "CV",
        "bullets": [
            ("Generate + detect", "โมเดลเดียวทำทั้งสร้างภาพและตรวจภาพ AI", "image"),
            ("Shared learning loop", "งานตรวจช่วยให้งานสร้างภาพสมจริงขึ้น", "loop"),
            ("Detection score", "รายงาน accuracy 98.6% และ F1 99.1%", "shield"),
            ("Creator + fact-check", "ใช้ได้ทั้งฝั่งผลิตภาพและตรวจความน่าเชื่อถือ", "check"),
        ],
        "visual_prompt": "computer vision system comparing real and AI-generated images, forensic image detection, creator tools, clean neural image grid, subtle camera optics",
    },
    3: {
        "subject": "Kimi K2.6",
        "kicker": "OPEN-WEIGHTS AGENT",
        "subtitle": "โอเพนซอร์สอันดับต้นที่คุม sub-agent ได้ 300 ตัว",
        "badge": "LLM",
        "bullets": [
            ("Open-weights leader", "ขึ้นนำหลาย benchmark ฝั่ง open-weights", "core"),
            ("300-agent swarm", "คุม sub-agent จำนวนมากในงานเดียวกันได้", "network"),
            ("MoE model design", "ใช้ 1T parameters และ 32B active ต่อ token", "chip"),
            ("Long-run work", "เด่นกับงาน agent ที่ต้องเดินหลายพัน step", "flow"),
        ],
        "visual_prompt": "open-weights large language model coordinating a swarm of agents, central MoE chip, many connected worker nodes, benchmark command center",
    },
    4: {
        "subject": "Open CoDesign",
        "kicker": "SELF-HOSTED DESIGN",
        "subtitle": "AI design tool แบบ local-first และเปิด MIT license",
        "badge": "UI",
        "bullets": [
            ("Local-first design", "ใช้งานบนเครื่องและคุม workflow ได้เอง", "window"),
            ("BYOK support", "ต่อ Claude, GPT, Gemini, Kimi หรือ Ollama ได้", "key"),
            ("Format export", "ส่งออก HTML, PDF, PPTX, ZIP และ Markdown", "export"),
            ("Design skills", "มีโมดูลสำหรับ UI, slide, dashboard และ web", "layout"),
        ],
        "visual_prompt": "self-hosted AI design studio, interface boards, design components, export formats, calm local-first workstation",
    },
    5: {
        "subject": "MiMo-V2.5-Pro",
        "kicker": "OPEN MODEL RACE",
        "subtitle": "Xiaomi ส่งโมเดลโอเพนซอร์สที่ไล่ระดับ frontier",
        "badge": "LLM",
        "bullets": [
            ("Open-source model", "Xiaomi ขยับจริงจังในสนามโมเดลเปิด", "core"),
            ("Reasoning focus", "เน้นงานคิดเป็นขั้นตอนและ coding benchmark", "flow"),
            ("Cost pressure", "เพิ่มแรงกดดันให้โมเดล frontier ด้านราคา", "chip"),
            ("Builder signal", "ทีม dev มีตัวเลือกเพิ่มสำหรับงาน self-host", "key"),
        ],
        "visual_prompt": "open-source language model benchmark arena, compact high-performance AI core, Xiaomi-inspired lab without logos, cost-performance charts as abstract shapes",
    },
    6: {
        "subject": "ml-intern",
        "kicker": "RESEARCH AGENT",
        "subtitle": "agent จาก HuggingFace ที่อ่าน paper และ train model เอง",
        "badge": "LAB",
        "bullets": [
            ("Paper to experiment", "อ่าน paper แล้วเปลี่ยนเป็นแผนทดลองได้", "window"),
            ("Training loop", "ลงมือ train model และเก็บผลลัพธ์ต่อเนื่อง", "flow"),
            ("Research memory", "บันทึกสิ่งที่ลองแล้วเพื่อปรับรอบถัดไป", "debug"),
            ("Lab automation", "ช่วยลดงานซ้ำใน pipeline วิจัย ML", "robot"),
        ],
        "visual_prompt": "AI research intern reading papers, running model training experiments, lab notebooks, charts, GPU workstation, research automation",
    },
    7: {
        "subject": "Honor Lightning",
        "kicker": "HUMANOID RUNNING",
        "subtitle": "หุ่นยนต์ humanoid วิ่งฮาล์ฟมาราธอนแบบ autonomous",
        "badge": "BOT",
        "bullets": [
            ("Half marathon run", "โชว์ความอึดในระยะทางระดับนักวิ่งจริง", "robot"),
            ("Autonomous control", "วิ่งด้วยระบบควบคุมของตัวเอง ไม่ใช่รีโมตโชว์", "flow"),
            ("Human benchmark", "เทียบกับสถิติคนเพื่อวัดความเร็วเชิงกายภาพ", "people"),
            ("Field robotics", "สัญญาณว่าหุ่นเริ่มออกจาก lab สู่พื้นที่จริง", "network"),
        ],
        "visual_prompt": "humanoid robot running a half marathon on a city road, autonomous robotics telemetry, endurance race, realistic athletic motion",
    },
    8: {
        "subject": "Unitree G1",
        "kicker": "MOBILITY TEST",
        "subtitle": "หุ่น humanoid ใส่ล้อและรองเท้าสเก็ตน้ำแข็งได้",
        "badge": "BOT",
        "bullets": [
            ("Hybrid mobility", "ทดลองล้อและรองเท้าสเก็ตบนร่าง humanoid", "robot"),
            ("Balance control", "ต้องคุมแรง จุดศูนย์ถ่วง และพื้นผิวพร้อมกัน", "core"),
            ("Real terrain", "ทดสอบความยืดหยุ่นมากกว่าการเดินพื้นเรียบ", "flow"),
            ("Consumer robot signal", "Unitree ยังเร่งลดช่องว่างจาก demo สู่สินค้า", "check"),
        ],
        "visual_prompt": "humanoid robot testing wheels and ice skates, balance control visualized, motion trails, engineering test rink, grounded robotics aesthetic",
    },
    9: {
        "subject": "Uni Geo",
        "kicker": "CAMERA-AWARE EDIT",
        "subtitle": "image edit ที่สั่งกล้องเลื่อนกี่องศาก็ได้",
        "badge": "IMG",
        "bullets": [
            ("Camera control", "สั่งมุมกล้องเป็นองศาแทนการเดาสุ่ม", "camera"),
            ("Geometry aware", "รักษาโครงสร้างภาพเมื่อ viewpoint เปลี่ยน", "layout"),
            ("Creative workflow", "เหมาะกับงาน product shot และ scene planning", "image"),
            ("More controllable", "ทำให้งาน edit ใกล้เครื่องมือ 3D มากขึ้น", "check"),
        ],
        "visual_prompt": "camera-aware image editing, viewpoint rotation controls, product scene changing angle, geometric grid, photographic studio preview",
    },
    10: {
        "subject": "Edit Crafter",
        "kicker": "4K IMAGE EDIT",
        "subtitle": "image editor ที่รองรับภาพ 4K และงานละเอียด",
        "badge": "IMG",
        "bullets": [
            ("High-res editing", "รองรับงานภาพ 4K ที่ต้องเก็บรายละเอียด", "image"),
            ("Local details", "แก้เฉพาะจุดโดยยังรักษาพื้นผิวเดิม", "check"),
            ("Production use", "เหมาะกับงานครีเอทีฟที่ต้องส่งไฟล์ใหญ่", "export"),
            ("Cleaner control", "ลดอาการภาพเละเมื่อแก้หลายรอบ", "layout"),
        ],
        "visual_prompt": "4K AI image editor interface, high-resolution photo retouching, detail-preserving edits, clean creative workstation",
    },
    11: {
        "subject": "LTX HDR LoRA",
        "kicker": "AI VIDEO HDR",
        "subtitle": "เปลี่ยนวิดีโอ AI ให้เป็น HDR ได้",
        "badge": "VID",
        "bullets": [
            ("HDR upgrade", "ยก dynamic range ของวิดีโอ AI ให้ดูมีมิติ", "image"),
            ("LoRA workflow", "ใช้ adapter เพื่อปรับ look โดยไม่เริ่มใหม่", "chip"),
            ("Video polish", "ช่วยงาน final pass ก่อนนำไปใช้จริง", "check"),
            ("Creator tool", "เหมาะกับทีมที่ผลิตคลิปจำนวนมาก", "export"),
        ],
        "visual_prompt": "AI video HDR grading studio, before-after dynamic range panels, cinematic color scopes, LoRA adapter module",
    },
    12: {
        "subject": "Vision Banana",
        "kicker": "PIXEL UNDERSTANDING",
        "subtitle": "Google ออกโมเดลที่เข้าใจภาพระดับ pixel",
        "badge": "CV",
        "bullets": [
            ("Pixel-level vision", "เข้าใจรายละเอียดเล็กในภาพได้แม่นขึ้น", "image"),
            ("Precise grounding", "จับตำแหน่งวัตถุและขอบเขตได้ละเอียด", "shield"),
            ("Better editing base", "เป็นฐานที่ดีสำหรับ image edit แบบควบคุมได้", "layout"),
            ("Developer signal", "งาน vision เริ่มขยับจากคำบรรยายสู่พิกัดจริง", "check"),
        ],
        "visual_prompt": "pixel-level computer vision analysis, image segmentation overlays, precise object grounding, clean Google-style research lab without logos",
    },
    13: {
        "subject": "Hunyuan Hy3",
        "kicker": "COMPACT 295B MODEL",
        "subtitle": "Tencent ส่งโมเดล 295B ที่เล็กลงแต่ยังแข่งได้",
        "badge": "LLM",
        "bullets": [
            ("295B scale", "ขนาดเล็กกว่ารุ่นยักษ์แต่ยังตั้งใจชน benchmark", "chip"),
            ("Efficiency push", "เน้นสมดุลระหว่าง performance และต้นทุน", "core"),
            ("Open ecosystem", "เพิ่มตัวเลือกฝั่งโมเดลจีนสำหรับ builder", "network"),
            ("Model race", "การแข่งขันเริ่มวัดที่ความคุ้มค่ามากขึ้น", "flow"),
        ],
        "visual_prompt": "efficient large language model architecture, compact AI server core, benchmark comparison wall, Tencent-inspired lab without logos",
    },
    14: {
        "subject": "Deepseek V4 Preview",
        "kicker": "COST-PERFORMANCE",
        "subtitle": "ราคาต่อ vibe code score ดีที่สุดในกลุ่มหนึ่ง",
        "badge": "LLM",
        "bullets": [
            ("Preview release", "ยังไม่ใช่ตัวเต็มแต่คะแนนเริ่มน่าสนใจ", "window"),
            ("Code value", "เด่นตรงราคาต่อคะแนนงาน coding", "code"),
            ("Practical benchmark", "เหมาะกับทีมที่คิดเรื่องต้นทุนจริง", "check"),
            ("Market pressure", "ทำให้ตลาดต้องแข่งกันที่ value มากขึ้น", "flow"),
        ],
        "visual_prompt": "AI coding model cost-performance dashboard, terminal benchmark, value chart, practical developer workstation",
    },
    15: {
        "subject": "CoInteract",
        "kicker": "UGC VIDEO AGENT",
        "subtitle": "AI ถ่ายวิดีโอรีวิวสินค้าแทน influencer",
        "badge": "UGC",
        "bullets": [
            ("Product review video", "สร้างคลิปรีวิวสินค้าแบบ UGC ได้อัตโนมัติ", "camera"),
            ("Actor interaction", "ตัวละครโต้ตอบกับสินค้าเหมือนถ่ายจริง", "people"),
            ("Commerce workflow", "ลดเวลาทำ ad variation สำหรับ e-commerce", "export"),
            ("Quality gap", "จุดต้องดูต่อคือความเนียนและ brand safety", "shield"),
        ],
        "visual_prompt": "AI-generated UGC product review studio, creator holding product, camera rig, ecommerce video workflow, tasteful realistic composition",
    },
    16: {
        "subject": "Qwen 3.6-27B",
        "kicker": "MID-SIZE OPEN MODEL",
        "subtitle": "โมเดลโอเพนซอร์ส medium-sized ที่น่าจับตา",
        "badge": "LLM",
        "bullets": [
            ("27B class", "ขนาดกลางแต่คะแนนดีในหลายงานใช้งานจริง", "chip"),
            ("Open deployment", "เหมาะกับทีมที่อยากคุมระบบเอง", "key"),
            ("Coding ability", "ใช้กับงาน dev และ agent workflow ได้มากขึ้น", "code"),
            ("Cost control", "ช่วยบาลานซ์คุณภาพกับค่า inference", "check"),
        ],
        "visual_prompt": "mid-sized open-source AI model running on private servers, coding assistant terminal, balanced cost-performance dashboard",
    },
    17: {
        "subject": "UniMesh",
        "kicker": "3D MODEL EDIT",
        "subtitle": "AI สร้างและ edit 3D model พร้อม description",
        "badge": "3D",
        "bullets": [
            ("Text to 3D", "สร้างโมเดล 3D จากคำอธิบายได้ครบขึ้น", "layout"),
            ("Editable mesh", "แก้รูปทรงต่อได้ ไม่ใช่แค่ export ครั้งเดียว", "window"),
            ("Description link", "ผูกคำบรรยายกับโครงสร้างโมเดล", "code"),
            ("Production path", "น่าสนใจสำหรับ game asset และ product mockup", "export"),
        ],
        "visual_prompt": "AI 3D mesh generation and editing workspace, wireframe object, sculpting handles, game asset pipeline, clean technical art",
    },
    18: {
        "subject": "GPT-5.5",
        "kicker": "FRONTIER MODEL",
        "subtitle": "โมเดลแรงสุดในรอบนี้บนงาน terminal bench",
        "badge": "LLM",
        "bullets": [
            ("Terminal bench lead", "คะแนนนำ Opus 4.7 อยู่ 13 จุดในรายงาน", "core"),
            ("Agentic coding", "เด่นกับงาน coding ที่ต้องวางแผนและแก้เอง", "code"),
            ("Tool use", "เหมาะกับ workflow ที่ต้องคุม terminal ยาว", "window"),
            ("Real cost check", "ตัวเลขดีแต่ต้องดูค่าใช้จ่ายตอนใช้จริง", "check"),
        ],
        "visual_prompt": "frontier AI coding model controlling terminal tasks, benchmark scoreboard as abstract bars, developer command center, premium restrained style",
    },
    19: {
        "subject": "GPT Image 2",
        "kicker": "IMAGE ARENA LEAD",
        "subtitle": "image generator ที่ทิ้งคู่แข่งห่างบน Arena",
        "badge": "IMG",
        "bullets": [
            ("Arena lead", "รายงานนำคู่แข่ง 242 จุดบน image arena", "shield"),
            ("Prompt fidelity", "ทำตาม brief ซับซ้อนได้ดีขึ้น", "check"),
            ("Production quality", "เหมาะกับงาน social, ad และ concept visual", "image"),
            ("Workflow impact", "ลดรอบแก้ภาพเมื่อ prompt ชัด", "flow"),
        ],
        "visual_prompt": "premium AI image generation studio, polished social creative grid, quality comparison arena, camera lenses and art boards",
    },
    20: {
        "subject": "Prompt Relay",
        "kicker": "MULTI-SCENE VIDEO",
        "subtitle": "เทคนิค inference-time สำหรับวิดีโอหลายฉาก",
        "badge": "VID",
        "bullets": [
            ("Scene handoff", "ส่ง context จากฉากหนึ่งไปยังฉากถัดไป", "flow"),
            ("Inference-time trick", "ไม่ต้อง train ใหม่เพื่อคุมหลาย shot", "chip"),
            ("Wan 2.2 workflow", "นำไปใช้กับ pipeline วิดีโอที่มีอยู่", "export"),
            ("Story consistency", "ช่วยให้คลิปยาวไม่หลุดคาแรกเตอร์ง่าย", "people"),
        ],
        "visual_prompt": "multi-scene AI video storyboard, connected shots flowing through relay nodes, cinematic timeline, consistency control",
    },
    21: {
        "subject": "Ternary Bonsai",
        "kicker": "EDGE AI MODEL",
        "subtitle": "โมเดล 1.58-bit ที่รันบน edge device เร็วมาก",
        "badge": "EDGE",
        "bullets": [
            ("1.58-bit weights", "ลดขนาดโมเดลเพื่อรันบนเครื่องเล็ก", "chip"),
            ("100+ tokens/sec", "รายงานความเร็วเกิน 100 token ต่อวินาที", "flow"),
            ("Edge deployment", "เหมาะกับอุปกรณ์ที่ไม่อยากส่งข้อมูลขึ้น cloud", "key"),
            ("Efficiency signal", "สนามโมเดลเริ่มแข่งที่การใช้งานปลายทาง", "check"),
        ],
        "visual_prompt": "tiny efficient AI model running on edge devices, bonsai-like chip sculpture, mobile hardware, low-power inference dashboard",
    },
    22: {
        "subject": "GPT Rosalind",
        "kicker": "LIFE SCIENCE AI",
        "subtitle": "โมเดล OpenAI สำหรับงานวิจัย life sciences",
        "badge": "BIO",
        "bullets": [
            ("Research model", "ออกแบบสำหรับโจทย์ชีววิทยาและการค้นคว้า", "shield"),
            ("Lab reasoning", "ช่วยอ่านข้อมูลทดลองและตั้งสมมติฐาน", "flow"),
            ("Domain workflow", "AI เฉพาะทางเริ่มแยกจาก chatbot ทั่วไป", "core"),
            ("High-stakes use", "ต้องจับคู่กับการตรวจสอบจากนักวิจัยจริง", "check"),
        ],
        "visual_prompt": "AI for life sciences research, molecular structures, lab data dashboard, microscope and neural network, calm scientific style",
    },
    23: {
        "subject": "WildDet 3D",
        "kicker": "MOBILE 3D TRACKING",
        "subtitle": "AI track 3D bounding box บน iPhone ได้",
        "badge": "3D",
        "bullets": [
            ("3D bounding box", "จับวัตถุเป็นกล่อง 3D ได้จากมือถือ", "layout"),
            ("On-device capture", "ทำงานบน iPhone ในสถานการณ์จริง", "camera"),
            ("AR foundation", "เป็นฐานสำหรับ AR, robotics และ scene mapping", "network"),
            ("Practical vision", "งาน vision เริ่มใกล้ผู้ใช้ทั่วไปมากขึ้น", "check"),
        ],
        "visual_prompt": "mobile phone tracking 3D bounding boxes in a real scene, AR object detection, spatial mapping, practical computer vision",
    },
    24: {
        "subject": "Motif Video 2B",
        "kicker": "SMALL VIDEO MODEL",
        "subtitle": "video generator 2B param ที่เทียบ Wan 2.2 ได้",
        "badge": "VID",
        "bullets": [
            ("2B parameters", "ขนาดเล็กแต่ตั้งใจชนรุ่นใหญ่กว่า", "chip"),
            ("Video quality", "รายงานคุณภาพใกล้ Wan 2.2 ในบางงาน", "image"),
            ("Faster iteration", "โมเดลเล็กช่วยให้ทดลองคลิปได้ไวขึ้น", "flow"),
            ("Creator access", "เปิดทางให้ทีมเล็กใช้ video gen ได้ง่ายกว่าเดิม", "export"),
        ],
        "visual_prompt": "compact AI video generation model, storyboard frames, efficient render engine, creator video workstation",
    },
    25: {
        "subject": "AniGen",
        "kicker": "ANIMATABLE 3D",
        "subtitle": "AI สร้าง 3D model พร้อม skeleton ใช้ animate ได้ทันที",
        "badge": "3D",
        "bullets": [
            ("Ready skeleton", "สร้างโมเดลพร้อมกระดูกสำหรับ animate", "robot"),
            ("3D asset pipeline", "ลดขั้นตอน rigging เบื้องต้นให้ทีมสร้างเกม", "layout"),
            ("Motion ready", "เอาไปลอง pose และ animation ต่อได้เร็ว", "flow"),
            ("Production caveat", "ยังต้องเช็ก topology ก่อนใช้จริง", "check"),
        ],
        "visual_prompt": "AI-generated 3D character with rig skeleton, animation control bones, game asset pipeline, clean studio render",
    },
    26: {
        "subject": "Happy Oyster",
        "kicker": "OPEN WORLD MODEL",
        "subtitle": "Genie 3 competitor จาก Alibaba ที่เปิด source",
        "badge": "WORLD",
        "bullets": [
            ("World model", "สร้างโลกที่โต้ตอบได้จาก input สั้น", "network"),
            ("Open source", "เปิดทางให้ community ทดลองและเทียบผล", "code"),
            ("Genie competitor", "แข่งในสนาม interactive environment", "game"),
            ("Research signal", "โลกจำลองกำลังกลายเป็นพื้นที่ทดสอบ agent", "robot"),
        ],
        "visual_prompt": "open-source interactive world model, simulated environment, controllable scene, game-like AI research world",
    },
    27: {
        "subject": "Nvidia Lyra 2.0",
        "kicker": "VIDEO TO 3D WORLD",
        "subtitle": "แปลงวิดีโอเป็น 3D world ที่ explore ได้",
        "badge": "3D",
        "bullets": [
            ("Video to world", "เปลี่ยนคลิปเป็นฉาก 3D ที่เดินสำรวจได้", "camera"),
            ("Explorable space", "ไม่ใช่แค่ render แต่ขยับมุมมองต่อได้", "layout"),
            ("Simulation use", "เหมาะกับ digital twin และ training environment", "robot"),
            ("Nvidia stack", "สอดรับกับงาน GPU และ world simulation", "chip"),
        ],
        "visual_prompt": "video transformed into explorable 3D world, digital twin reconstruction, Nvidia-style simulation lab without logos, 3D scene grid",
    },
    28: {
        "subject": "Tencent HY World 2.0",
        "kicker": "PIPELINE WORLD MODEL",
        "subtitle": "multimodal world model ที่พร้อมเข้า pipeline มากขึ้น",
        "badge": "WORLD",
        "bullets": [
            ("Multimodal input", "รวมภาพ วิดีโอ และคำสั่งเพื่อสร้างโลก", "network"),
            ("Pipeline ready", "เน้นนำไปต่อใน workflow มากกว่าโชว์ demo", "export"),
            ("Scene consistency", "ช่วยให้ฉากคงตัวเมื่อสร้างหลายมุม", "layout"),
            ("Builder focus", "เหมาะกับทีมที่ทำ simulation และ content tool", "check"),
        ],
        "visual_prompt": "multimodal world model production pipeline, scene generation nodes, stable virtual environment, professional simulation dashboard",
    },
    29: {
        "subject": "ByteDance OmniShow",
        "kicker": "AUDIO + POSE UGC",
        "subtitle": "UGC video gen ที่ใส่ audio และ pose skeleton ได้",
        "badge": "UGC",
        "bullets": [
            ("Audio driven", "ใช้เสียงช่วยกำหนดจังหวะและการแสดง", "flow"),
            ("Pose skeleton", "คุมท่าทางด้วยโครงกระดูกแทน prompt ล้วน", "robot"),
            ("UGC workflow", "ทำคลิปรีวิวหรือ presenter ได้เป็นระบบขึ้น", "camera"),
            ("Control layer", "จุดแข็งคือคุม performance ได้ละเอียดกว่าเดิม", "check"),
        ],
        "visual_prompt": "AI UGC video generation with audio waveform and pose skeleton controls, virtual presenter studio, social commerce workflow",
    },
    30: {
        "subject": "Claude Opus 4.7",
        "kicker": "AUTONOMOUS MODEL",
        "subtitle": "Anthropic ส่งโมเดลที่ทำงานเองได้นานขึ้น",
        "badge": "LLM",
        "bullets": [
            ("Autonomous work", "โฟกัสงานที่ต้องคิดและลงมือหลายขั้นตอน", "flow"),
            ("Coding strength", "ยังเป็นตัวเลือกหลักของงาน dev หนัก", "code"),
            ("Agent reliability", "จุดสำคัญคือความนิ่งเมื่อเจอ task ยาว", "shield"),
            ("Model race", "ตลาด frontier เริ่มแข่งกันที่ความทนของ agent", "network"),
        ],
        "visual_prompt": "autonomous AI coding agent planning long tasks, calm terminal workspace, task graph, reliability monitoring dashboard",
    },
    31: {
        "subject": "Qwen 3.6 35B A3B",
        "kicker": "MOE OPEN MODEL",
        "subtitle": "MoE มาตรฐานใหม่ของโอเพนซอร์ส 35B",
        "badge": "LLM",
        "bullets": [
            ("35B MoE", "ใช้ mixture-of-experts เพื่อคุมต้นทุนต่อ token", "chip"),
            ("A3B active", "เปิดใช้ expert เฉพาะส่วนที่จำเป็น", "core"),
            ("Open model bar", "ยกระดับมาตรฐานของโมเดลเปิดขนาดกลาง", "network"),
            ("Deployment fit", "น่าสนใจสำหรับทีมที่มี infra จำกัด", "key"),
        ],
        "visual_prompt": "mixture-of-experts open model architecture, expert nodes lighting selectively, private AI server, benchmark board",
    },
    32: {
        "subject": "Unitree H1",
        "kicker": "ROBOT SPEED RECORD",
        "subtitle": "หุ่น humanoid ทำลายสถิติโลกที่ 10 m/s",
        "badge": "BOT",
        "bullets": [
            ("10 m/s speed", "รายงานความเร็วระดับ 36 km/h", "flow"),
            ("Humanoid balance", "ต้องคุมขา ลำตัว และแรงกระแทกพร้อมกัน", "robot"),
            ("Record signal", "การแข่งขันหุ่นเริ่มวัดด้วย performance จริง", "shield"),
            ("Next challenge", "หลังจากเร็วแล้วต้องดูเรื่องความทนและ safety", "check"),
        ],
        "visual_prompt": "humanoid robot sprinting at record speed on a test track, telemetry lines, high-speed robotics engineering",
    },
    33: {
        "subject": "Leju Robotics",
        "kicker": "HUMANOID PRODUCTION",
        "subtitle": "สาย production ของหุ่น humanoid ตัวแรกของโลก",
        "badge": "BOT",
        "bullets": [
            ("Production line", "ขยับจาก prototype ไปสู่การผลิตจริง", "window"),
            ("Factory robotics", "โรงงานเริ่มเตรียม scale หุ่น humanoid", "robot"),
            ("Supply chain", "จุดท้าทายคือชิ้นส่วนและคุณภาพซ้ำได้", "network"),
            ("Market signal", "สนามนี้เริ่มเข้าเฟสอุตสาหกรรมมากขึ้น", "check"),
        ],
        "visual_prompt": "humanoid robot production line in a modern factory, assembly stations, quality control, industrial robotics scale-up",
    },
    34: {
        "subject": "Adobe Token Relight",
        "kicker": "3D LIGHT CONTROL",
        "subtitle": "สั่งย้ายแสง 3D ในรูปได้แม่นถึงระดับองศา",
        "badge": "IMG",
        "bullets": [
            ("Lighting tokens", "คุมตำแหน่งแสงในภาพได้เป็นระบบ", "image"),
            ("3D direction", "สั่งมุมและองศาของแสงได้ละเอียด", "layout"),
            ("Photo workflow", "ช่วยงาน retouch และ product visual", "camera"),
            ("Creative control", "ภาพ AI เริ่มเข้าใกล้เครื่องมือ studio จริง", "check"),
        ],
        "visual_prompt": "AI photo relighting studio, movable 3D light rigs, product portrait preview, token-based lighting controls",
    },
    35: {
        "subject": "Game World",
        "kicker": "BROWSER GAME BENCH",
        "subtitle": "benchmark วัด AI เล่น 34 เกมบราว์เซอร์",
        "badge": "GAME",
        "bullets": [
            ("34 browser games", "ใช้เกมจริงเป็นสนามวัดความสามารถ agent", "game"),
            ("Interactive benchmark", "ต้องมองหน้าจอ ตัดสินใจ และกดเล่นต่อเนื่อง", "camera"),
            ("General agent test", "วัดมากกว่าการตอบคำถามใน chat", "robot"),
            ("Failure insight", "เห็นชัดว่า agent พลาดตรงไหนในโลก interactive", "debug"),
        ],
        "visual_prompt": "AI agent playing multiple browser games, grid of game screens, interaction benchmark dashboard, controller and cursor telemetry",
    },
    36: {
        "subject": "Gemini 3.1 Flash TTS",
        "kicker": "EMOTION-CONTROL TTS",
        "subtitle": "TTS ที่สั่งอารมณ์ด้วย metatag ได้",
        "badge": "TTS",
        "bullets": [
            ("Metatag control", "ใส่ tag เพื่อคุมอารมณ์และน้ำเสียง", "code"),
            ("Fast TTS", "ออกแบบสำหรับงานเสียงที่ต้องตอบไว", "flow"),
            ("Creator workflow", "เหมาะกับ voiceover, bot และ content batch", "export"),
            ("Voice direction", "งานเสียงเริ่มคุมได้เหมือนกำกับนักพากย์", "people"),
        ],
        "visual_prompt": "AI text-to-speech studio, voice waveform with emotion control tags, narrator booth, audio mixing console",
    },
    37: {
        "subject": "Ernie Image",
        "kicker": "OPEN IMAGE MODEL",
        "subtitle": "open-source 8B จาก Baidu ที่ text rendering แม่นขึ้น",
        "badge": "IMG",
        "bullets": [
            ("8B open model", "ขนาดไม่ใหญ่แต่เปิดให้ชุมชนต่อยอด", "chip"),
            ("Text rendering", "จุดขายคือการวางตัวอักษรในภาพแม่นขึ้น", "image"),
            ("Chinese model race", "ฝั่งจีนยังเร่งแข่งในสนาม image generation", "network"),
            ("Practical output", "เหมาะกับงาน poster และ creative ที่ต้องมีข้อความ", "check"),
        ],
        "visual_prompt": "open-source image model generating posters with accurate text layout, typography grid without readable words, creative design studio",
    },
}

SONY_BRIEF = {
    "subject": "Sony Project Ace",
    "kicker": "REAL-WORLD ROBOTICS",
    "subtitle": "AI ปิงปองที่ย้ายจากซิมมาแข่งกับมนุษย์จริง",
    "badge": "BOT",
    "bullets": [
        ("9-camera vision", "ตามลูกและไม้ตีแบบ 3D ด้วยระบบกล้องรอบโต๊ะ", "camera"),
        ("9,000 RPM spin", "อ่านลูกหมุนเร็วและเปลี่ยนทิศกลางอากาศ", "flow"),
        ("RL + sim-to-real", "ฝึกจาก trial and error แล้วถ่ายความรู้สู่หุ่นจริง", "core"),
        ("Mid-air replan", "ปรับแผนหลังลูกชนเน็ตก่อนตีจริงได้ทัน", "robot"),
    ],
    "visual_prompt": "Sony Project Ace table tennis robot, real-world robotics, high-speed ping pong vision system, sim-to-real reinforcement learning, professional lab screenshots",
}


def slugify(text: str) -> str:
    text = text.lower().replace("+", " plus ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "post"


def ensure_dirs() -> None:
    for path in (OUT_DIR, IMAGES_DIR, UPPER_DIR, PROMPT_DIR, CAPTIONS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def sanitize_caption(text: str, *, sony: bool = False, subject: str = "") -> str:
    text = text.replace("—", "-").replace("–", "-").replace("→", "->")
    blocks = [b.strip() for b in text.strip().split("\n\n") if b.strip()]
    if sony:
        replacement = (
            "สำหรับสาย AI หรือ robotics, Project Ace เป็นเคสที่ควรเก็บไว้ดูต่อ เพราะมันโชว์ว่า "
            "sim-to-real ไม่ได้อยู่ใน paper อย่างเดียวแล้ว แต่เริ่มจับต้องได้ในโลกจริงแบบชัดมาก"
        )
        blocks = [
            replacement
            if b.startswith("💬") or "คอมเมนต์" in b or "คุณว่า" in b
            else b
            for b in blocks
        ]
    else:
        friendly = f"{subject} เป็นอีกสัญญาณที่น่าตาม เพราะมันขยับจากเดโมไปใกล้ workflow ใช้งานจริงมากขึ้น"
        for i in range(len(blocks) - 1, -1, -1):
            b = blocks[i]
            if b.startswith("#") or b.startswith("ที่มา") or b.startswith("http"):
                continue
            if "?" in b or "คุณว่า" in b or "คิดเห็นยังไง" in b or "คอมเมนต์" in b:
                blocks[i] = friendly
            break
    return "\n\n".join(blocks).strip() + "\n"


def build_upper_prompt(brief: Brief) -> str:
    return f"""Create a square 1254x1254 polished Facebook infographic background for AI Inspire.

The final compositor will add all readable copy and the fixed AI Inspire footer. Generate only the upper visual composition.

Hard layout rules:
- Left side must be clean infographic space: about 60% of the width, off-white paper texture, low contrast, enough room for headline and 4 bullet rows.
- Right visual must be designed specifically for about 40% of the width. It can softly feather into the left side, but it must not dominate more than 40% of the canvas.
- No hard vertical separator, no straight blur strip, no torn divider. Blend naturally with atmospheric depth.
- Keep the bottom footer zone visually quiet because the fixed brand bar will be pasted over it.
- Do not place important content under the future brain logo area near bottom-right.
- No readable text, no letters, no numbers, no logos, no watermark. Abstract UI marks are fine if unreadable.

Style:
- Professional AI/tech editorial infographic.
- Dark navy, clean white, muted steel blue, warm gold accents.
- Avoid obvious neon purple, rainbow cyberpunk, and overly AI-ish color.
- Rich, artistic, complex right-side background that actually relates to the post.
- Crisp, high-end social media finish, balanced lighting, readable left area.

Post subject: {brief.subject}
Topic category: {brief.kicker}
Visual direction: {brief.visual_prompt}
"""


def generate_upper(brief: Brief, *, force: bool = False) -> None:
    if brief.key == "sony-project-ace":
        return
    out_path = UPPER_DIR / f"{brief.output_stem}.png"
    prompt_path = PROMPT_DIR / f"{brief.output_stem}.txt"
    prompt = build_upper_prompt(brief)
    prompt_path.write_text(prompt, encoding="utf-8")
    if out_path.exists() and not force:
        print(f"upper exists: {brief.output_stem}", flush=True)
        return
    print(f"generating upper: {brief.output_stem} - {brief.subject}", flush=True)
    cmd = [
        str(GPTIMG),
        "--prompt-file",
        str(prompt_path),
        "--output",
        str(out_path),
        "--size",
        "1254x1254",
        "--quiet",
    ]
    run_gptimg(cmd)
    print(f"generated upper: {brief.output_stem}", flush=True)


def usage_limit_delay(output: str) -> int | None:
    if "usage limit" not in output.lower() and "try again at" not in output.lower():
        return None
    match = re.search(r"try again at\\s+(\\d{1,2}):(\\d{2})\\s*([AP]M)", output, re.I)
    if not match:
        return 30 * 60
    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = match.group(3).upper()
    if ampm == "PM" and hour != 12:
        hour += 12
    if ampm == "AM" and hour == 12:
        hour = 0
    now = datetime.now(BKK)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max(60, int((target - now).total_seconds()) + 75)


def run_gptimg(cmd: list[str]) -> None:
    attempts = 0
    while True:
        attempts += 1
        proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
        if proc.stdout:
            print(proc.stdout.strip(), flush=True)
        if proc.stderr:
            print(proc.stderr.strip(), flush=True)
        if proc.returncode == 0:
            return
        combined = f"{proc.stdout}\n{proc.stderr}"
        delay = usage_limit_delay(combined)
        if delay is not None and attempts <= 4:
            print(f"usage limit hit; retrying in {delay} seconds", flush=True)
            time.sleep(delay)
            continue
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)


def paste_rounded(base: Image.Image, im: Image.Image, box: tuple[int, int, int, int], radius: int) -> None:
    x1, y1, x2, y2 = box
    fitted = ImageOps.fit(im, (x2 - x1, y2 - y1), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
    mask = Image.new("L", fitted.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, fitted.size[0] - 1, fitted.size[1] - 1), radius=radius, fill=255)
    base.paste(fitted, (x1, y1), mask)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(box, radius=radius, outline=GOLD, width=4)


def compose_sony_visual(base: Image.Image) -> None:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.rounded_rectangle((690, 132, 1182, 950), radius=42, fill=(*hex_to_rgb(NAVY), 24))
    for i, y in enumerate(range(160, 900, 92)):
        d.line((700, y, 1176, y + 64), fill=(*hex_to_rgb(GOLD if i % 3 == 0 else "#7AB8CA"), 34), width=2)
    for x, y in [(726, 220), (1038, 188), (1142, 346), (772, 706), (1110, 824)]:
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(*hex_to_rgb(GOLD), 128))
    base.alpha_composite(layer)

    frames = [
        SONY_DIR / "01-attachment-122097001616427837.jpg",
        SONY_DIR / "02-attachment-122097001688427837.jpg",
        SONY_DIR / "03-attachment-122097001736427837.jpg",
    ]
    boxes = [(736, 204, 1168, 396), (736, 454, 1168, 646), (736, 704, 1168, 896)]
    for frame, box in zip(frames, boxes):
        paste_rounded(base, Image.open(frame).convert("RGB"), box, 22)


def draw_infographic(base: Image.Image, brief: Brief) -> None:
    draw = ImageDraw.Draw(base)
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel, "RGBA")
    pd.rounded_rectangle((82, 96, 704, 1018), radius=34, fill=(255, 255, 255, 104))
    pd.rounded_rectangle((98, 112, 680, 352), radius=28, fill=(255, 255, 255, 132))
    base.alpha_composite(panel)

    title_font = fit_font(draw, brief.subject, 580, 72, latin=True)
    draw_strong(draw, (112, 132), brief.subject, title_font, NAVY)

    kicker_font = fit_font(draw, brief.kicker, 570, 34, latin=True)
    draw_strong(draw, (112, 222), brief.kicker, kicker_font, GOLD)

    subtitle_lines = wrap_text(draw, brief.subtitle, font(31), 552)
    y = 278
    for line in subtitle_lines[:3]:
        draw_strong(draw, (112, y), line, font(31), NAVY)
        y += 40
    divider_y = y + 8
    draw.line((112, divider_y, 654, divider_y), fill=GOLD, width=4)
    draw.ellipse((648, divider_y - 6, 662, divider_y + 8), fill=GOLD)

    cy = max(424, divider_y + 74)
    body_size = 25
    head_size = 30
    for _ in range(6):
        test_y = cy
        for i, (head, body, _icon) in enumerate(brief.bullets, start=1):
            head_font = fit_font(draw, f"{i}. {head}", 470, head_size, latin=True)
            body_lines = wrap_text(draw, body, font(body_size), 446)
            yy = test_y + 2 + (31 * len(body_lines))
            sep_y = max(test_y + 70, yy + 8)
            test_y = sep_y + 70
        if test_y <= 1012 or body_size <= 20:
            break
        body_size -= 1
        head_size -= 1

    for i, (head, body, icon) in enumerate(brief.bullets, start=1):
        draw_ref_icon(draw, 132, cy, icon)
        head_text = f"{i}. {head}"
        head_font = fit_font(draw, head_text, 470, head_size, latin=True)
        draw_strong(draw, (216, cy - 42), head_text, head_font, NAVY)
        body_lines = wrap_text(draw, body, font(body_size), 446)
        yy = cy + 2
        for line in body_lines:
            draw.text((218, yy), line, font=font(body_size), fill=INK)
            yy += body_size + 6
        sep_y = max(cy + 70, yy + 8)
        draw.line((216, sep_y, 646, sep_y), fill=GOLD, width=3)
        draw.ellipse((642, sep_y - 5, 652, sep_y + 5), fill=GOLD)
        cy = sep_y + 70


def compose_image(brief: Brief) -> dict:
    original = Image.open(TEMPLATE).convert("RGBA")
    base = clean_base_from_template(original)
    upper_path = UPPER_DIR / f"{brief.output_stem}.png"
    if brief.key == "sony-project-ace":
        compose_sony_visual(base)
    elif upper_path.exists():
        art = Image.open(upper_path).convert("RGB")
        art = ImageOps.fit(art, (W, H), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
        base.alpha_composite(art)

    draw_infographic(base, brief)

    base.alpha_composite(original.crop((0, FOOTER_Y, W, H)), (0, FOOTER_Y))
    paste_brain_logo(base, original)
    brief.image_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(brief.image_path, quality=95)

    rendered = Image.open(brief.image_path).convert("RGB")
    template = Image.open(TEMPLATE).convert("RGB")
    bottom_ok = ImageChops.difference(template.crop((0, FOOTER_Y, W, H)), rendered.crop((0, FOOTER_Y, W, H))).getbbox() is None
    brain_diff = ImageChops.difference(template.crop(BRAIN_LOGO_BBOX), rendered.crop(BRAIN_LOGO_BBOX)).convert("L")
    masked_brain_diff = Image.new("L", brain_diff.size, 0)
    masked_brain_diff.paste(brain_diff, mask=brain_logo_mask())
    brain_ok = masked_brain_diff.getbbox() is None
    ellipsis = any("..." in part or "…" in part for pair in brief.bullets for part in pair[:2])
    return {
        "key": brief.key,
        "image": str(brief.image_path),
        "caption": str(brief.caption_path),
        "bottom_bar_identical": bottom_ok,
        "brain_logo_identical": brain_ok,
        "contains_ellipsis": ellipsis,
    }


def make_contact_sheet(records: list[dict]) -> None:
    cols = 6
    cell_w, cell_h = 250, 292
    rows = (len(records) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#E9EEF2")
    for i, record in enumerate(records):
        im = Image.open(record["image"]).convert("RGB")
        im.thumbnail((230, 230), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (cell_w, cell_h), "#F5F7F9")
        tile.paste(im, ((cell_w - im.width) // 2, 10))
        d = ImageDraw.Draw(tile)
        d.text((12, 248), Path(record["image"]).stem[:25], font=font(15, latin=True), fill=NAVY)
        sheet.paste(tile, ((i % cols) * cell_w, (i // cols) * cell_h))
    sheet.save(CONTACT_SHEET, quality=92)


def load_briefs() -> list[Brief]:
    posts = json.loads(SOURCE_POSTS.read_text(encoding="utf-8"))
    briefs: list[Brief] = []

    sony_caption = sanitize_caption((SONY_DIR / "caption.txt").read_text(encoding="utf-8"), sony=True, subject="Sony Project Ace")
    sony_caption_path = CAPTIONS_DIR / "00-sony-project-ace.txt"
    sony_caption_path.write_text(sony_caption, encoding="utf-8")
    briefs.append(
        Brief(
            key="sony-project-ace",
            source_index=None,
            subject=SONY_BRIEF["subject"],
            kicker=SONY_BRIEF["kicker"],
            subtitle=SONY_BRIEF["subtitle"],
            badge=SONY_BRIEF["badge"],
            bullets=tuple(SONY_BRIEF["bullets"]),
            visual_prompt=SONY_BRIEF["visual_prompt"],
            image_path=IMAGES_DIR / "00-sony-project-ace.png",
            caption_path=sony_caption_path,
            output_stem="00-sony-project-ace",
        )
    )

    for post in posts:
        idx = int(post["item_index"])
        data = SHORT_BRIEFS[idx]
        source_caption_path = SOURCE_CAPTIONS / f"{idx:02d}.txt"
        caption_source = source_caption_path.read_text(encoding="utf-8") if source_caption_path.exists() else post.get("caption") or post.get("finalText") or ""
        caption = sanitize_caption(caption_source, subject=data["subject"])
        caption_path = CAPTIONS_DIR / f"{idx + 1:02d}-{slugify(data['subject'])}.txt"
        caption_path.write_text(caption, encoding="utf-8")
        output_stem = f"{idx + 1:02d}-{slugify(data['subject'])}"
        briefs.append(
            Brief(
                key=slugify(data["subject"]),
                source_index=idx,
                subject=data["subject"],
                kicker=data["kicker"],
                subtitle=data["subtitle"],
                badge=data["badge"],
                bullets=tuple(tuple(x) for x in data["bullets"]),
                visual_prompt=data["visual_prompt"],
                image_path=IMAGES_DIR / f"{output_stem}.png",
                caption_path=caption_path,
                output_stem=output_stem,
            )
        )
    return briefs


def default_start_time() -> datetime:
    now = datetime.now(BKK)
    start = now + timedelta(minutes=45)
    minute = 0 if start.minute < 30 else 30
    if minute == 0 and start.minute >= 30:
        start += timedelta(hours=1)
    return start.replace(minute=minute, second=0, microsecond=0)


def parse_start(value: str | None) -> datetime:
    if not value:
        return default_start_time()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BKK)
    return dt.astimezone(BKK)


def write_queue(briefs: list[Brief], *, start_at: datetime, interval_hours: float) -> list[dict]:
    queue = []
    for i, brief in enumerate(briefs):
        when = start_at + timedelta(hours=interval_hours * i)
        queue.append(
            {
                "index": i,
                "key": brief.key,
                "sourceIndex": brief.source_index,
                "subject": brief.subject,
                "scheduledAt": when.isoformat(),
                "captionPath": str(brief.caption_path),
                "imagePath": str(brief.image_path),
                "text": brief.caption_path.read_text(encoding="utf-8").strip(),
                "images": [str(brief.image_path)],
            }
        )
    QUEUE_JSON.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return queue


def selected(items: list[Brief], start_index: int, limit: int | None) -> Iterable[Brief]:
    subset = items[start_index:]
    if limit is not None:
        subset = subset[:limit]
    return subset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-upper", action="store_true", help="generate missing GPT image upper backgrounds")
    parser.add_argument("--force-generate", action="store_true", help="regenerate upper backgrounds even if present")
    parser.add_argument("--start-index", type=int, default=0, help="queue index, 0 is Sony long-form")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start-at", help="first scheduled time, ISO, defaults to about 45 minutes from now")
    parser.add_argument("--interval-hours", type=float, default=2.0)
    args = parser.parse_args()

    ensure_dirs()
    briefs = load_briefs()
    manifest = []
    for brief in selected(briefs, args.start_index, args.limit):
        if args.generate_upper:
            generate_upper(brief, force=args.force_generate)
        manifest.append(compose_image(brief))

    # Recompose all images for the final contact sheet when running the full pass.
    if args.start_index == 0 and args.limit is None:
        rendered = manifest
    else:
        rendered = [compose_image(b) for b in briefs]
    make_contact_sheet(rendered)
    queue = write_queue(briefs, start_at=parse_start(args.start_at), interval_hours=args.interval_hours)
    MANIFEST_JSON.write_text(
        json.dumps(
            {
                "count": len(briefs),
                "imagesDir": str(IMAGES_DIR),
                "upperDir": str(UPPER_DIR),
                "contactSheet": str(CONTACT_SHEET),
                "queue": str(QUEUE_JSON),
                "verification": rendered,
                "firstScheduledAt": queue[0]["scheduledAt"],
                "lastScheduledAt": queue[-1]["scheduledAt"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "count": len(briefs),
                "rendered": len(rendered),
                "contactSheet": str(CONTACT_SHEET),
                "queue": str(QUEUE_JSON),
                "firstScheduledAt": queue[0]["scheduledAt"],
                "lastScheduledAt": queue[-1]["scheduledAt"],
                "allVerified": all(r["bottom_bar_identical"] and r["brain_logo_identical"] and not r["contains_ellipsis"] for r in rendered),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
