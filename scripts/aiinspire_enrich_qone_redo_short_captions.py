#!/usr/bin/env python3
"""Enrich the QOne short-form captions with source-checked details.

This intentionally updates only the add-only queue topics. The older topics that
were already scheduled previously remain excluded from the direct browser run.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "output/facebook/qone-redo-short-7rWJ9xpne0"
BKK = timezone(timedelta(hours=7))
VIDEO_URL = "https://www.youtube.com/watch?v=7r_WJ9xpne0&t=4s"


CAPTIONS = {
    "01-omnishot-cut-detects-video-edits-automatically.txt": """AI ตัดต่อวิดีโอเริ่มเข้าใจ "จังหวะคัต" ไม่ใช่แค่เห็นภาพทีละเฟรมแล้ว

OmniShotCut เป็นงานใหม่สาย Shot Boundary Detection หรือการจับจุดเปลี่ยนช็อตในวิดีโอ ถ้าพูดแบบคนทำคอนเทนต์ มันคือโมเดลที่ช่วยบอกว่า "ตรงนี้คือตัดฉาก", "ตรงนี้คือ dissolve/fade/wipe", หรือ "ตรงนี้ยังเป็นช็อตเดิม" โดยไม่ต้องลาก timeline หาเองทีละจุด

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- โมเดล/README ของ UVA Computer Vision Lab ระบุว่า OmniShotCut ใช้แนวคิด Shot-Query-based Video Transformer เพื่อจับความสัมพันธ์ของช็อตแบบทั้งบริบท ไม่ใช่ดูแค่ความต่างของเฟรมติดกัน
- จุดขายคือ detect ได้จากวิดีโอหลายแหล่ง เช่น anime, vlog, game, shorts, sports และ screen recording ซึ่งตรงกับปัญหาจริงของ editor ที่ footage ไม่ได้สะอาดเหมือน dataset
- มันไม่ได้แค่บอก "มีคัต" แต่พยายามแยก sudden jump กับ transition แบบ dissolve, fade, wipe ด้วย นี่สำคัญกับ workflow ตัดต่อ เพราะ transition แต่ละแบบควรถูกจัดการต่างกัน
- เมื่องานนี้ไปอยู่ใน pipeline จริง ประโยชน์คือทำ auto chaptering, highlight extraction, short clipping, recap, และตรวจงานตัดต่อยาว ๆ ได้ละเอียดขึ้น

มุมที่ต้องระวัง: leaderboard/คำว่า SoTA เป็น claim จากทีมงานและ paper/model card ต้องดูการใช้งานจริงกับ footage ไทย, video meme, และคลิป social ที่มี overlay หนัก ๆ อีกที

ช่วงในคลิป: 00:00:49-00:02:05
แหล่งเช็ก: Hugging Face/uva-cv-lab OmniShotCut, paper arXiv 2604.24762
ที่มา: AI Search — {video}

#AINews #AIInspire #VideoAI #ContentCreator #ArtificialIntelligence""",
    "02-alibaba-happy-horse-underperforms-in-real-tests.txt": """Leaderboard ชนะ ไม่ได้แปลว่างานจริงจะชนะทุกโจทย์

HappyHorse-1.0 เป็นหนึ่งในข่าว AI video ที่คนพูดถึงมาก เพราะชื่อไปโผล่บน Artificial Analysis Video Arena แล้วถูกโยงกับ Alibaba/ATH แต่ประเด็นของคลิปนี้ไม่ได้บอกว่าโมเดลแย่ ประเด็นคือ "อันดับสูงมาก" กับ "งาน production จริง" ยังเป็นคนละเรื่อง

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- หลายแหล่งที่อ้างถึง Artificial Analysis ระบุว่า HappyHorse-1.0 ทำคะแนนสูงมากในหมวด text-to-video และ image-to-video แบบ no audio ช่วงเมษายน 2026
- แหล่งทดสอบเชิงรีวิวอย่าง fal.ai ระบุว่าโมเดลถูกโปรโมตเป็นวิดีโอ 15B จาก Alibaba พร้อม native audio ใน pass เดียว แต่ข้อจำกัดเรื่องราคา/ความยาวคลิปยังต้องดู
- แหล่งที่พูดเรื่อง "open source" ยังไม่เสถียร มีหลายเว็บที่ใช้คำนี้แรงเกินหลักฐาน เพราะยังไม่เห็น first-party model card/weights ที่ตรวจสอบง่ายเหมือน Hugging Face ของโมเดล open weight ทั่วไป
- ในคลิป ผู้พูดเอา prompt ยากกว่า benchmark เช่นฉากต่อเนื่องหลายเหตุการณ์ การซูมไกลมาก และวัตถุที่ต้องรักษาฟิสิกส์ พบว่างานยังหลุด continuity/follow-through ได้

สรุปที่ควรโพสต์แบบแฟร์: HappyHorse น่าจับตาเพราะ blind arena signal แรง แต่ยังไม่ควรสรุปว่า "ดีที่สุดจริง" จนกว่าจะดูตัวอย่างยาก ๆ, API/model card ทางการ, ราคา, และข้อจำกัดการใช้งานเชิง production

ช่วงในคลิป: 00:02:05-00:05:27
แหล่งเช็ก: fal.ai HappyHorse review, Artificial Analysis references, public HappyHorse/Alibaba coverage
ที่มา: AI Search — {video}

#AINews #AIInspire #AIVideo #Alibaba #ArtificialIntelligence""",
    "03-mocap-anything-v2-turns-video-into-animation-skeletons.txt": """วิดีโอคนหรือคาแรกเตอร์ อาจกลายเป็น motion capture ได้โดยไม่ต้องใส่ชุด mocap

MoCapAnything V2 คือสายงานที่น่าจะกระทบเกม, แอนิเมชัน, virtual production และ creator workflow ตรง ๆ เพราะเป้าหมายคือเอา monocular video แล้วแปลงเป็น animation-ready motion สำหรับ skeleton ที่ต่างกันได้

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- paper page ระบุชัดว่า V2 เป็น fully end-to-end framework สำหรับ arbitrary-skeleton motion capture
- ต่างจาก pipeline เดิมที่แยก video-to-pose แล้วค่อยใช้ inverse kinematics แปลงเป็น rotation งานนี้เรียน video-to-pose และ pose-to-rotation ร่วมกัน
- ปัญหาหลักที่แก้คือ joint position อย่างเดียวไม่ได้บอก rotation ครบ โดยเฉพาะ bone-axis twist ถ้าแก้ไม่ดี ตัวละครจะบิดแปลกแม้ตำแหน่ง joint ดูถูก
- ทีมงานใช้ reference pose-rotation pair เพื่อ anchor ระบบพิกัดของ skeleton เป้าหมาย ทำให้ output ไปลง rig ได้แม่นกว่า
- รายงานบน Hugging Face paper page ระบุว่าลด rotation error จากประมาณ 17 องศาเหลือประมาณ 10 องศา และเหลือ 6.54 องศาบน unseen skeletons พร้อม inference เร็วขึ้นราว 20x เมื่อเทียบกับ mesh-based pipelines

ความหมายเชิง production: ไม่ใช่แค่ "เอาท่าเต้นไปใส่ตัวละคร" แต่คือการลดเวลางาน retargeting และ cleanup ที่ animator เสียเวลามากที่สุด

ช่วงในคลิป: 00:05:29-00:07:23
แหล่งเช็ก: Hugging Face Papers MoCapAnything V2, project page animotionlab
ที่มา: AI Search — {video}

#AINews #AIInspire #MotionCapture #Animation #ArtificialIntelligence""",
    "04-inclusion-ai-link-2-6-flash-efficient-open-model.txt": """แก้ชื่อก่อน: ตัวนี้คือ Ling 2.6 Flash ไม่ใช่ Link

Ling-2.6-Flash จาก inclusionAI/Ant Group เป็น open instruct model ที่ออกแบบมาเพื่อ agent workload มากกว่าการโชว์ reasoning ยาว ๆ อย่างเดียว จุดที่น่าสนใจคือมันใช้ MoE ขนาดรวม 104B แต่ active ระหว่าง inference เพียง 7.4B ทำให้ positioning ของมันคือ intelligence ต่อ cost ไม่ใช่ parameter ใหญ่ที่สุด

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- model card บน Hugging Face ระบุ official open-source release, 104B total parameters และ 7.4B active parameters
- ทีมงานบอกว่า optimize เพื่อ inference efficiency, token efficiency และ agent performance โดยเฉพาะงาน tool use, planning, execution
- model card ระบุ speed สูงสุดถึง 340 tokens/s บน 4x H20 setup ซึ่งเป็น claim จากทีมงาน แต่เป็นตัวเลขที่บอกทิศทางชัดว่าเน้น throughput
- evaluation ที่ทีมยกมาเกี่ยวกับ BFCL-V4, TAU2-bench, SWE-bench Verified, Claw-Eval และ PinchBench ซึ่งเป็นกลุ่ม benchmark ที่ใกล้ agent/coding มากกว่า chat ทั่วไป
- มี variant BF16, FP8, INT4 และ license MIT จึงเหมาะให้ทีม infra ทดลองจริงมากกว่าแค่ดู demo

ข้อสรุป: ถ้าทีมคุณทำ agent ที่ต้องเรียก tool ซ้ำ ๆ หรืออ่าน context ยาว ๆ โมเดลแบบนี้น่าสนใจกว่าโมเดลที่ตอบยาวแต่กิน token หนัก

ช่วงในคลิป: 00:07:24-00:08:30
แหล่งเช็ก: Hugging Face inclusionAI/Ling-2.6-flash-fp8 model card
ที่มา: AI Search — {video}

#AINews #AIInspire #OpenModels #AIAgents #ArtificialIntelligence""",
    "05-zanime-anime-image-generation-model.txt": """สาย anime image generation มีโมเดลที่ควรดู เพราะมันไม่ใช่แค่ LoRA อีกตัว

Z-Anime เป็นโมเดลจาก SeeSee21 ที่ fine-tune จาก Alibaba Z-Image Base แบบเต็ม จุดเด่นคือทำให้ Z-Image กลายเป็น base สำหรับงาน anime โดยตรง พร้อม variant สำหรับคุณภาพและความเร็วหลายระดับ

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- model card ระบุว่า Z-Anime เป็น full fine-tune บน Z-Image Base ไม่ใช่ LoRA merge
- สถาปัตยกรรมฐานคือ S3-DiT ขนาด 6B parameters และมี full negative prompt support
- มีหลาย variant: Base, Distill-8-Step และ Distill-4-Step สำหรับ trade-off ระหว่างคุณภาพกับความเร็ว
- รองรับ BF16, FP8, GGUF และ AIO variants ทำให้คนใช้ ComfyUI/เครื่อง VRAM ไม่สูงมีทางเลือกมากขึ้น
- model card ระบุ 8GB VRAM compatible และ GGUF สำหรับ lower memory/CPU/AMD-friendly workflows

มุมที่น่าสนใจจริง ๆ คือ ecosystem: ถ้าโมเดล 6B ที่รันง่ายขึ้นเริ่มให้ quality ดีพอ งาน anime production จะเปลี่ยนจาก "ใช้โมเดลใหญ่ใน cloud" เป็น "วน prompt/แก้ pose/style บนเครื่องตัวเอง" ได้เร็วขึ้น

ข้อควรระวัง: นี่เป็น experimental model family คุณภาพ character consistency, anatomy และ complex scene ยังต้องทดสอบกับ workflow จริง ไม่ควรดูแค่ภาพตัวอย่างสวย ๆ

ช่วงในคลิป: 00:08:32-00:09:37
แหล่งเช็ก: Hugging Face SeeSee21/Z-Anime model card
ที่มา: AI Search — {video}

#AINews #AIInspire #AnimeAI #ImageGeneration #ArtificialIntelligence""",
    "08-meta-tuna-2-image-generator-editor.txt": """Meta กำลังลองทางใหม่ของ image AI: ไม่ฝากชีวิตไว้กับ vision encoder

Tuna-2 ของ Meta/FAIR เป็น unified multimodal model ที่ทำทั้ง understanding และ generation โดยใช้ pixel embeddings ตรง ๆ แนวคิดหลักคือเลิกบีบภาพผ่าน vision encoder/VAE แบบเดิม แล้วให้โมเดลเรียนจาก patch/pixel representation เพื่อเก็บรายละเอียดละเอียดขึ้น

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- GitHub facebookresearch/tuna-2 เป็น official implementation ของงาน "Pixel Embeddings Beat Vision Encoders for Unified Understanding and Generation"
- arXiv/paper summary ระบุว่า Tuna-2 ตัด pretrained vision encoder และ VAE ออก ใช้ patch embedding layers เข้ารหัส visual input โดยตรง
- เป้าคือแก้ misalignment ระหว่างงาน understanding กับ generation ที่มักเกิดจากการใช้ representation คนละชุด
- paper ระบุว่า encoder-free design ทำได้ดีขึ้นเมื่อ scale มากขึ้น โดยเฉพาะงาน fine-grained visual perception
- จุดนี้สำคัญกับงานอ่าน UI, table, text เล็ก ๆ, diagram หรือภาพที่รายละเอียดเล็กมีผลต่อคำตอบ

ข่าวที่ต้องพูดให้ชัด: Meta เปิด code/paper แล้ว แต่เรื่อง full model weights ต้องดู release note ของ repo ไม่ควรเขียนเหมือนเป็น consumer image generator ที่พร้อมใช้เทียบ GPT Image 2 ได้ทันที

ช่วงในคลิป: 00:15:47-00:17:00
แหล่งเช็ก: GitHub facebookresearch/tuna-2, arXiv 2604.24763
ที่มา: AI Search — {video}

#AINews #AIInspire #MetaAI #ImageGeneration #ArtificialIntelligence""",
    "09-anyrecon-reconstructs-3d-from-sparse-photos.txt": """ถ่ายภาพไม่ครบมุม ก็อาจ reconstruct ฉาก 3D ได้ดีขึ้นกว่าเดิม

AnyRecon คือ paper สาย sparse-view 3D reconstruction ที่ใช้ video diffusion model เพื่อช่วยสร้างมุมมองที่ขาดหาย แล้วนำไปใช้ reconstruct 3D จากภาพที่ถ่ายแบบ casual ได้ดีขึ้น เป้าหมายคือโลกจริงที่เราไม่ได้มี camera rig เป๊ะ ๆ แต่มีรูป/วิดีโอไม่กี่มุม

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- arXiv ระบุหัวข้อ "Arbitrary-View 3D Reconstruction with Video Diffusion Model" และโจทย์คือ sparse-view 3D reconstruction จากภาพมุมน้อย
- จุดต่างจาก pipeline reconstruct แบบ non-generative คือใช้พลังของ diffusion model เพื่อเติม arbitrary views ที่สอดคล้องกับฉาก
- บทสรุปจาก paper discovery ระบุว่ามีการใช้ 4-step diffusion distillation และ context-window sparse attention เพื่อลด complexity
- ในคลิปอธิบายว่า global memory ช่วยให้ฉากที่สร้างจากมุม sparse ไม่หลุดง่าย เพราะระบบพยายามจำบริบทของฉากก่อนหน้า
- ถ้าเทคโนโลยีนี้นิ่งขึ้น จะมีผลกับ scan สถานที่, game asset, virtual tour, robotics simulation และ VFX previsualization

ข้อควรระวัง: reconstruction จากภาพน้อยยังเสี่ยง hallucination สูง โดยเฉพาะด้านหลังวัตถุหรือพื้นที่ที่กล้องไม่เคยเห็น ดังนั้น output ต้องใช้เป็น draft/assist มากกว่าหลักฐานเชิงวัดระยะจริง

ช่วงในคลิป: 00:17:00-00:19:17
แหล่งเช็ก: arXiv 2604.19747 AnyRecon
ที่มา: AI Search — {video}

#AINews #AIInspire #3DAI #ComputerVision #ArtificialIntelligence""",
    "11-kinetics-ai-kai-humanoid-robot.txt": """KAI ไม่ควรถูกจำแค่ว่าเป็นหุ่นหน้าขาว แต่มันคือข่าว tactile robotics

Kinetix AI/Kinetics AI KAI เป็น humanoid ที่คลิปย้ำเรื่อง 115 degrees of freedom, มือ 36 DoF และ full-body tactile skin จุดนี้สำคัญกว่า demo พับผ้าหรือเล่นปิงปอง เพราะ humanoid ที่อยู่ใกล้คนจริงต้อง "รู้ว่าถูกแตะ" และ "รู้ว่าจับแรงแค่ไหน" ไม่ใช่แค่เดินได้

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- รายงาน Gasgoo และ RobotsBeat ระบุ KAI มี 115 DoF และ dexterous hand 36 DoF
- แหล่งข่าวเดียวกันระบุ full-body tactile skin มีประมาณ 18,000 sensing points
- รายงานระบุว่าสามารถตรวจสัมผัสเบาระดับ 0.1N ซึ่งถ้าทำได้จริงจะช่วยให้ close-range collaboration ปลอดภัยขึ้นมาก
- รูปแบบงาน demo เช่นรูดซิป พับผ้า หยิบของ และเล่นกับเด็ก สื่อถึงโจทย์ contact-rich manipulation ที่กล้องอย่างเดียวไม่พอ
- ราคาที่ถูกพูดถึงในรายงานบางแหล่งอยู่ระดับ sub-$40,000 แต่ควรมองเป็น positioning/claim จนกว่าจะมี spec sheet และสัญญาขายจริง

ข้อสรุป: ข่าวนี้ไม่ได้ใหญ่เพราะหุ่นเหมือนคน แต่เพราะ tactile skin + dexterous hand อาจเป็นชิ้นส่วนที่ทำให้ humanoid เริ่มทำงานบ้าน/บริการได้จริงขึ้น

ช่วงในคลิป: 00:24:53-00:26:30
แหล่งเช็ก: Gasgoo, RobotsBeat coverage on KAI humanoid
ที่มา: AI Search — {video}

#AINews #AIInspire #HumanoidRobot #Robotics #ArtificialIntelligence""",
    "12-robot-era-l7-warehouse-humanoid-fleet.txt": """Humanoid ในคลังสินค้าเริ่มขยับจาก demo เดี่ยว เป็นระบบ fleet

RobotEra/星动纪元 L7 ถูกพูดถึงในคลิปเพราะมีหลายตัวทำงานใน logistics center ไม่ใช่แค่หุ่นหนึ่งตัวโชว์ท่าเดิน ข่าวนี้จึงน่าสนใจตรงการเอา humanoid เข้า "งานซ้ำจริง" อย่างตรวจพัสดุ หยิบของจากสายพาน และคัดแยกลง lane

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- หน้า official ของ RobotEra มีข้อมูล L7 ในฐานะ full-size bipedal humanoid robot
- รายงาน RoboHorizon และสื่อจีนระบุว่า RobotEra วาง L7 ในแนวทาง end-to-end VLA สำหรับ logistics application
- L7 ถูกพูดถึงพร้อม embodied brain/ERA-42 และงาน "goods-to-person" picking ซึ่งเป็นโจทย์ warehouse ที่ automation แบบเดิมยังติด flexible picking gap
- ข้อมูลสาธารณะระบุ L7 เป็นหุ่น full-size ประมาณ 171 ซม., มี DoF จำนวนมาก และใช้ dexterous hands ในงานหยิบจับ
- ตัวเลข "หลายพันตัว/หลายศูนย์ logistics" ยังควรถูกมองเป็น deployment claim หรือ roadmap จนกว่าจะมีเอกสารลูกค้า/ปริมาณติดตั้งจริงที่ตรวจได้

ความหมายเชิงธุรกิจ: ถ้าหุ่นปรับตัวเข้าคลังเดิมได้โดยไม่ redesign ทั้งอาคาร มูลค่าจะไม่ใช่ตัวหุ่นอย่างเดียว แต่อยู่ที่ orchestration, uptime, maintenance และ integration กับ WMS

ช่วงในคลิป: 00:26:33-00:27:31
แหล่งเช็ก: RobotEra L7 official page, RoboHorizon logistics coverage
ที่มา: AI Search — {video}

#AINews #AIInspire #WarehouseAutomation #HumanoidRobot #ArtificialIntelligence""",
    "13-noix-and-tfbot-realistic-android-heads.txt": """หุ่น companion กำลังชนโจทย์ยากที่สุด: ใบหน้าที่คนเชื่อได้

ช่วงนี้มีหลาย demo ของ robotic head / android face ที่เริ่มขยับตา กระพริบตา ทำ micro-expression และใช้ synthetic skin ดีขึ้น คลิปพูดถึง Noix/TFbot/Ella ในฐานะสัญญาณว่า robot companion กำลังออกจากโซนของเล่นไปสู่ humanoid interface ที่หน้าตาเหมือนคนมากขึ้น

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- แหล่งเปิดที่ตรวจได้ชัดในหมวดนี้มี Noetix HOBBS และ NeuroFace ซึ่งพูดเรื่อง bionic/hyper-realistic robotic head, micro-expression, gaze และ synthetic skin
- Noetix ระบุ HOBBS เป็น bionic robot head ที่มี high DoF สำหรับ facial expression และ human-robot interaction
- NeuroFace วางตัวเป็น hyper-realistic robotic head system สำหรับ humanoid robots และ embodied AI โดยเน้น micro-expression, gaze และ biomimetic skin
- เทรนด์ที่ชัดคือ "หน้า" กลายเป็น interface ของ embodied AI ไม่ใช่แค่เปลือกสวย เพราะ gaze, timing, blink และ expression มีผลต่อ trust อย่างมาก
- สำหรับ TFbot/Ella ยังไม่พบ primary source ที่ตรวจได้แน่นจาก web search รอบนี้ จึงควรพูดเป็น demo/rumor watch ไม่ใช่ประกาศผลิตภัณฑ์ที่ verify แล้ว

ประเด็นใหญ่: robot companion จะไม่วัดกันแค่ LLM ข้างใน แต่วัดที่ uncanny valley, safety, consent, privacy และความรับผิดชอบเมื่อหุ่นทำหน้าที่ใกล้ชิดกับคน

ช่วงในคลิป: 00:27:33-00:28:50
แหล่งเช็ก: Noetix HOBBS, NeuroFace public pages; TFbot/Ella ยังไม่พบ primary source ชัด
ที่มา: AI Search — {video}

#AINews #AIInspire #Robotics #HumanoidRobot #ArtificialIntelligence""",
    "14-sensenova-u1-unified-multimodal-model.txt": """SenseNova U1 น่าสนใจเพราะมันพยายามรวม "เข้าใจภาพ" กับ "สร้างภาพ" ไว้ในโมเดลเดียว

SenseTime เปิด SenseNova U1 เป็น native unified multimodal model series ที่รวม multimodal understanding, reasoning และ generation ใน monolithic framework จุดที่ต่างจาก image model ทั่วไปคือมันไม่ได้ถูกวางเป็นแค่เครื่องสร้างภาพสวย แต่เป็นโมเดลที่ทำงานกับ text+image context ต่อเนื่องได้

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- press release ของ SenseTime ระบุว่า SenseNova U1 built on NEO-unify architecture และ open-source บางส่วนของ U1 Lite series
- SenseTime เคลมว่า U1 ทำ continuous image-text creative generation ได้ โดยเก็บ visual/text signals ไว้ใน contextual information เดียวกัน
- press release ระบุว่า U1 Lite ทำงาน complex infographic generation ได้ในระดับ commercial performance โดยเฉพาะ layout coherence และ text rendering accuracy
- มี GitHub และ Hugging Face collection สำหรับ open-source deployment รวมถึง SenseNova-Skills สำหรับตัวอย่าง prompt/generation
- นี่ทำให้ U1 อยู่ในกลุ่มเดียวกับโมเดลที่พยายามแก้โจทย์ poster, infographic, storyboard และ visual reasoning ไม่ใช่แค่ portrait

มุมใช้งาน: ถ้าโมเดลอ่านข้อมูลแล้วสร้าง infographic ได้ดีขึ้นจริง มันจะกระทบงาน social creative, report, slide, education และ dashboard visualization โดยตรง

ช่วงในคลิป: 00:28:52-00:32:13
แหล่งเช็ก: SenseTime official SenseNova U1 release, OpenSenseNova GitHub/Hugging Face links
ที่มา: AI Search — {video}

#AINews #AIInspire #MultimodalAI #ImageGeneration #ArtificialIntelligence""",
    "15-nvidia-neotron-3-nano-omni.txt": """แก้ชื่อก่อน: ตัวนี้คือ NVIDIA Nemotron 3 Nano Omni ไม่ใช่ Neotron

Nemotron 3 Nano Omni เป็น open multimodal model จาก NVIDIA ที่รวม text, image, video และ audio understanding ไว้ในโมเดลเดียว จุดที่ควรสนใจคือมันถูกวางเป็น perception/context sub-agent สำหรับ agentic systems มากกว่าจะเป็น chatbot ทั่วไป

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- NVIDIA technical blog ระบุว่าโมเดลเป็น 30B hybrid MoE ที่รองรับ text, image, video และ audio inputs ใน unified multimodal context
- สถาปัตยกรรมใช้ Mamba layers เพื่อ sequence/memory efficiency ผสม transformer layers เพื่อ reasoning
- สำหรับ video มี 3D convolutions และ Efficient Video Sampling layer เพื่อลด visual token จากหลายเฟรมไม่ให้ท่วม context
- training pipeline ขยาย context จาก 16K ไป 49K แล้ว 262K และมี post-SFT RL มากกว่า 2.3M environment rollouts ตาม blog
- NVIDIA ระบุว่าเปิด weights, datasets และ training recipes เพื่อให้ customize/on-prem ได้มากขึ้น

ทำไมข่าวนี้สำคัญ: enterprise agent จำนวนมากไม่ได้ขาดแค่ LLM แต่ขาดโมดูลอ่านเอกสาร, screenshot, เสียงประชุม และวิดีโอในระบบเดียว ถ้า Nemotron Omni ทำงานได้จริง มันลดการต่อหลายโมเดลหลาย pipeline ลงได้

ช่วงในคลิป: 00:32:15-00:34:17
แหล่งเช็ก: NVIDIA Technical Blog, Hugging Face nvidia/Nemotron-3-Nano-Omni-30B-A3B
ที่มา: AI Search — {video}

#AINews #AIInspire #NVIDIA #MultimodalAI #ArtificialIntelligence""",
    "17-moonlink-3d-world-building-agent.txt": """AI สำหรับ 3D เริ่มขยับจาก generate asset ไปเป็น agent ที่ทำงานใน Blender

Moonlink ในคลิปถูกอธิบายเป็น 3D world-building agent ที่เข้าไปแก้ scene, object, lighting, structure และ animation ใน Blender ได้เอง แนวคิดนี้น่าสนใจเพราะ workflow 3D จริงไม่ได้จบที่ "สร้างภาพหนึ่งภาพ" แต่มันต้องมีไฟล์, hierarchy, material, camera, animation และ revision loop

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- รอบนี้ยังไม่พบ primary source ที่ยืนยัน Moonlink โดยตรงแบบ official model card/paper/GitHub
- แต่ทิศทาง "LLM/agent เชื่อม Blender" ตรวจได้จาก ecosystem อย่าง Blender MCP และ 3D-agent tools ที่ให้ AI ควบคุม Blender ผ่าน protocol/tool layer
- ถ้า Moonlink ทำตามคลิปจริง จุดสำคัญจะอยู่ที่ feedback loop: agent ต้อง inspect scene, run/preview, แก้ error และจัด asset ให้ใช้งานต่อได้
- งาน 3D ต่างจาก image gen เพราะ output ต้อง editable ไม่ใช่ raster ที่ดูสวยอย่างเดียว
- โจทย์ production ที่ควรถามคือ export format, material consistency, scale/units, polygon budget, rig/animation compatibility และ license ของ assets

ดังนั้นโพสต์นี้ควรเล่าแบบ trend watch: Moonlink เป็นสัญญาณของ AI agent สำหรับ 3D pipeline แต่ยังต้องรอแหล่งหลักเพื่อยืนยันรายละเอียดผลิตภัณฑ์

ช่วงในคลิป: 00:35:34-00:37:58
แหล่งเช็ก: ยังไม่พบ primary source ของ Moonlink โดยตรง; เทียบแนวทางกับ Blender MCP/agent-to-Blender ecosystem
ที่มา: AI Search — {video}

#AINews #AIInspire #Blender #3DAI #ArtificialIntelligence""",
    "19-xai-grok-4-3-beta.txt": """Grok 4.3 ไม่ได้มีข่าวแค่ "เก่งขึ้น" แต่คือ xAI กำลังดัน agent + ราคาถูก

ในคลิปพูดถึง Grok 4.3 beta ว่า reasoning ดีขึ้น มีเครื่องมือช่วยทำงานเอกสาร/code/file มากขึ้น แต่ยังไม่ใช่ตัวท็อปของ leaderboard เมื่อเทียบกับ frontier models ที่แรงที่สุด ข่าวนี้ควรเล่าแบบสมดุล: improvement มีจริง แต่ยังต้องดู benchmark แยกตามงาน

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- xAI docs แสดงการใช้งาน model name `grok-4.3` ผ่าน API และแนะนำ migration สำหรับ reasoning workloads
- Oracle Cloud docs ระบุ `xai.grok-4.3` เป็น reasoning model, multimodal text+image input, function calling, structured outputs และ context length 1 million tokens
- VentureBeat รายงานราคา API $1.25 ต่อ 1M input tokens และ $2.50 ต่อ 1M output tokens พร้อมข้อสังเกตว่า cost-performance ดีขึ้นเมื่อเทียบกับรุ่นก่อน
- แหล่งเดียวกันรายงานว่า Grok 4.3 ดีขึ้นจาก Grok 4.2 ใน third-party benchmarks แต่ยังไม่ถึง state-of-the-art ของ OpenAI/Anthropic ล่าสุด
- เครื่องมือ web search, X search, code execution, file/RAG มีผลต่อ economics จริง เพราะมีค่า tool call เพิ่ม ไม่ใช่ดูแค่ token price

สรุป: Grok 4.3 น่าสนใจถ้าคุณต้องการ agent ราคาคุมได้และ context ใหญ่ แต่ถ้างานต้องการ reasoning คุณภาพสูงสุด ควร benchmark กับโจทย์ตัวเองก่อนย้าย

ช่วงในคลิป: 00:42:09-00:43:22
แหล่งเช็ก: xAI Docs, Oracle Cloud Grok 4.3 docs, VentureBeat
ที่มา: AI Search — {video}

#AINews #AIInspire #xAI #Grok #ArtificialIntelligence""",
    "20-mistral-medium-3-5.txt": """Mistral Medium 3.5 เป็นโมเดลใหญ่ที่ต้องถามเรื่อง "คุ้ม" มากกว่า "ใหญ่ไหม"

Mistral Medium 3.5 เปิดตัวเป็น dense 128B multimodal model พร้อม context 256K และ open weights ภายใต้ Modified MIT license ข้อดีคือรวม instruction-following, reasoning และ coding ไว้ในโมเดลเดียว แต่ในมุมใช้งานจริง คำถามคือทีมไหนควรเลือกมันแทนโมเดลเล็ก/ถูกกว่า

สิ่งที่เช็กเพิ่มจากแหล่งจริง:
- Hugging Face model card ระบุว่าเป็น dense 128B model, 256k context window และรองรับ text+image input with text output
- Mistral docs วางตำแหน่งเป็น frontier-class multimodal model สำหรับ agentic/coding use cases
- model card ระบุว่าแทน Mistral Medium 3.1, Magistral ใน Le Chat และ Devstral 2 ใน Vibe coding agent
- ราคาใน Mistral docs อยู่ที่ $1.5 ต่อ 1M input tokens และ $7.5 ต่อ 1M output tokens
- ฟีเจอร์สำคัญคือ function calling, structured outputs, document QnA, OCR และ reasoning effort ที่ปรับได้

มุมวิจารณ์ที่ควรเก็บไว้: 128B dense หมายถึง self-host/local inference ไม่เบาเลย ต่อให้ open weights ก็ไม่ใช่โมเดลสำหรับเครื่องเล็ก และถ้า workload ไม่ต้องการ compliance/European vendor/open-weight control อาจมีตัวเลือกที่ถูกกว่า

สรุป: เป็นโมเดลจริงจังสำหรับองค์กรและทีม infra มากกว่าโมเดล "ลองเล่นฟรีบนเครื่องบ้าน"

ช่วงในคลิป: 00:43:24-00:44:42
แหล่งเช็ก: Mistral docs, Hugging Face mistralai/Mistral-Medium-3.5-128B
ที่มา: AI Search — {video}

#AINews #AIInspire #MistralAI #OpenModels #ArtificialIntelligence""",
}


CORRECTED_SUBJECTS = {
    "04-inclusion-ai-link-2-6-flash-efficient-open-model.txt": "Inclusion AI Ling 2.6 Flash efficient open model",
    "15-nvidia-neotron-3-nano-omni.txt": "NVIDIA Nemotron 3 Nano Omni",
}


def next_half_hour() -> datetime:
    now = datetime.now(BKK)
    start = now + timedelta(minutes=60)
    if start.minute == 0:
        rounded = start
    elif start.minute <= 30:
        rounded = start.replace(minute=30)
    else:
        rounded = (start + timedelta(hours=1)).replace(minute=0)
    return rounded.replace(second=0, microsecond=0)


def main() -> int:
    for filename, caption in CAPTIONS.items():
        path = BASE / "captions" / filename
        if not path.exists():
            raise FileNotFoundError(path)
        path.write_text(caption.format(video=VIDEO_URL) + "\n", encoding="utf-8")

    caption_by_name = {
        (BASE / "captions" / filename).resolve().as_posix(): caption.format(video=VIDEO_URL)
        for filename, caption in CAPTIONS.items()
    }

    pass_dir = (BASE / "images/pass").resolve()
    start = next_half_hour()

    for queue_name in ("schedule-queue.json", "add-only-schedule-queue.json"):
        queue_path = BASE / queue_name
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        add_only = queue_name == "add-only-schedule-queue.json"
        add_idx = 0
        for item in queue:
            caption_path = item.get("captionPath")
            if caption_path in caption_by_name:
                item["text"] = caption_by_name[caption_path]
                filename = Path(caption_path).name
                if filename in CORRECTED_SUBJECTS:
                    item["subject"] = CORRECTED_SUBJECTS[filename]
                image_name = Path(item["imagePath"]).name
                image_path = (pass_dir / image_name).as_posix()
                item["imagePath"] = image_path
                item["images"] = [image_path]
                if add_only:
                    item["scheduledAt"] = (start + timedelta(hours=2 * add_idx)).isoformat()
                    item["index"] = add_idx
                    add_idx += 1
        queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "captionsUpdated": len(CAPTIONS),
                "addOnlyStart": start.isoformat(),
                "addOnlyCount": len(json.loads((BASE / "add-only-schedule-queue.json").read_text(encoding="utf-8"))),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
