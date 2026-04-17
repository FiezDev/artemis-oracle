# ComfyUI Video/Image Processing Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create 6 ComfyUI API-format workflow JSON files (WF 15-20) for video/image processing, validated against the local ComfyUI instance.

**Architecture:** Standalone JSON files in `workflows/model-tests/saved/`, each a flat dict keyed by string node IDs. Three workflows (15, 16, 19) are fully specified in the spec. Three workflows (17, 18, 20) have TBD class_types that must be resolved by querying ComfyUI's `/object_info` endpoint before writing.

**Tech Stack:** ComfyUI API-format JSON, Python `run.py` for submission/testing, `api_to_ui.py` for UI format conversion.

**Spec:** `docs/superpowers/specs/2026-04-17-comfyui-video-workflows-design.md`

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `workflows/model-tests/saved/15_video_upscaler_ltx23.json` | Create | LTX 2.3 spatial 2x video upscaler |
| `workflows/model-tests/saved/16_image_upscaler_zimage.json` | Create | Z-Image turbo 2x image upscaler |
| `workflows/model-tests/saved/17_face_swap_bfs_ltx23.json` | Create | BFS V3 + LTX 2.3 face swap |
| `workflows/model-tests/saved/18_motion_control_sdsteady_ltx23.json` | Create | SDPose + SteadyDancer + LTX 2.3 motion control |
| `workflows/model-tests/saved/19_lipsync_latentsync.json` | Create | LatentSync lip sync |
| `workflows/model-tests/saved/20_storydiffusion_sdxl.json` | Create | StoryDiffusion + SDXL character image gen |
| `workflows/model-tests/README.md` | Modify | Update results table with new workflows |

---

## Task 1: Resolve TBD Class Types

**Goal:** Query ComfyUI's `/object_info` endpoint to discover exact class_types and input schemas for nodes marked TBD in the spec (BFS template prep, SDPose, SteadyDancer, StoryDiffusion nodes).

**Files:**
- Read: spec doc (for TBD list)
- Write: none (results feed into Tasks 5-7)

- [ ] **Step 1: Query BFS nodes**

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
bfs = {k: v for k, v in data.items() if 'bfs' in k.lower() or 'BFS' in k or 'head_swap' in k.lower() or 'face_swap' in k.lower()}
json.dump(bfs, sys.stdout, indent=2)
"
```

Expected: class_type for BFS template prep node with its input schema. If no results, the custom node isn't installed — note this and move on.

- [ ] **Step 2: Query SDPose nodes**

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
pose = {k: v for k, v in data.items() if 'sdpose' in k.lower() or 'pose' in k.lower()}
json.dump(pose, sys.stdout, indent=2)
"
```

- [ ] **Step 3: Query SteadyDancer nodes**

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
dance = {k: v for k, v in data.items() if 'steady' in k.lower() or 'dancer' in k.lower()}
json.dump(dance, sys.stdout, indent=2)
"
```

- [ ] **Step 4: Query StoryDiffusion nodes**

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
sd = {k: v for k, v in data.items() if 'story' in k.lower() or 'storydiffusion' in k.lower()}
json.dump(sd, sys.stdout, indent=2)
"
```

- [ ] **Step 5: Query CLIPVisionLoader (for WF 20)**

```bash
curl -s http://localhost:8188/object_info/CLIPVisionLoader | python3 -m json.tool
```

- [ ] **Step 6: Record results**

Save the resolved class_types and input schemas. If a custom node isn't installed, mark it as blocked and skip its workflow for now — the JSON can be written with placeholder class_types once the node is installed.

- [ ] **Step 7: Commit findings (if any changes to spec)**

```bash
git add docs/superpowers/specs/2026-04-17-comfyui-video-workflows-design.md
git commit -m "docs: resolve TBD class_types from ComfyUI object_info query"
```

---

## Task 2: Write Workflow 15 — Video Upscaler

**Goal:** Create `15_video_upscaler_ltx23.json`. Fully specified in spec — no TBDs.

**Files:**
- Create: `workflows/model-tests/saved/15_video_upscaler_ltx23.json`
- Reference: spec section "Workflow 15"

- [ ] **Step 1: Write the workflow JSON**

```json
{
  "1": {"class_type": "VHS_LoadVideo", "inputs": {"video": "dance_cute1.mp4", "force_rate": 0, "custom_width": 0, "custom_height": 0, "frame_load_cap": 16, "skip_first_frames": 0, "select_every_nth": 1}},
  "2": {"class_type": "VAELoader", "inputs": {"vae_name": "ltx-2.3-22b-dev_video_vae.safetensors"}},
  "3": {"class_type": "LatentUpscaleModelLoader", "inputs": {"model_name": "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"}},
  "4": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 0]}},
  "5": {"class_type": "LTXVLatentUpsampler", "inputs": {"samples": ["4", 0], "upscale_model": ["3", 0], "vae": ["2", 0]}},
  "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["2", 0]}},
  "7": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["6", 0], "frame_rate": 8, "loop_count": 0, "filename_prefix": "upscale_video", "format": "video/h264-mp4", "pingpong": false, "save_output": true}}
}
```

- [ ] **Step 2: Validate JSON parses**

```bash
python3 -c "import json; json.load(open('workflows/model-tests/saved/15_video_upscaler_ltx23.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Submit to ComfyUI to check validation**

```bash
cd workflows/model-tests && python3 run.py saved/15_video_upscaler_ltx23.json
```

Expected: `queued prompt_id=...` then eventually `status: ok` (or timeout if upscaler takes long). If `validate_error`, fix the reported issue.

- [ ] **Step 4: Commit**

```bash
git add workflows/model-tests/saved/15_video_upscaler_ltx23.json
git commit -m "feat: add WF 15 video upscaler (LTX 2.3 spatial 2x)"
```

---

## Task 3: Write Workflow 16 — Image Upscaler

**Goal:** Create `16_image_upscaler_zimage.json`. Fully specified — modeled after `02_zimage_turbo_risa.json` with upscale pipeline added.

**Files:**
- Create: `workflows/model-tests/saved/16_image_upscaler_zimage.json`
- Reference: `workflows/model-tests/saved/02_zimage_turbo_risa.json`, spec section "Workflow 16"

- [ ] **Step 1: Write the workflow JSON**

```json
{
  "1": {"class_type": "LoadImage", "inputs": {"image": "risa_body.jpeg"}},
  "2": {"class_type": "ImageScaleBy", "inputs": {"image": ["1", 0], "upscale_method": "nearest-exact", "scale_by": 2.0}},
  "3": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
  "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"shift": 3.0, "model": ["3", 0]}},
  "5": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2"}},
  "6": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
  "7": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["6", 0]}},
  "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "high quality, detailed, sharp, 4k, professional photo", "clip": ["5", 0]}},
  "9": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["8", 0]}},
  "10": {"class_type": "KSampler", "inputs": {"seed": 20260417, "steps": 4, "cfg": 1.0, "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 0.4, "model": ["4", 0], "positive": ["8", 0], "negative": ["9", 0], "latent_image": ["7", 0]}},
  "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["6", 0]}},
  "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": "upscale_image"}}
}
```

- [ ] **Step 2: Validate JSON parses**

```bash
python3 -c "import json; json.load(open('workflows/model-tests/saved/16_image_upscaler_zimage.json')); print('OK')"
```

- [ ] **Step 3: Submit to ComfyUI**

```bash
cd workflows/model-tests && python3 run.py saved/16_image_upscaler_zimage.json
```

- [ ] **Step 4: Commit**

```bash
git add workflows/model-tests/saved/16_image_upscaler_zimage.json
git commit -m "feat: add WF 16 image upscaler (Z-Image turbo img2img)"
```

---

## Task 4: Write Workflow 19 — Lip Sync

**Goal:** Create `19_lipsync_latentsync.json`. Exact copy of verified `gen-output/comfyui-tests/14-latentsync.json` with consistent naming.

**Files:**
- Create: `workflows/model-tests/saved/19_lipsync_latentsync.json`
- Reference: `gen-output/comfyui-tests/14-latentsync.json`

- [ ] **Step 1: Write the workflow JSON**

```json
{
  "1": {"class_type": "LoadImage", "inputs": {"image": "fashion_face1.jpeg"}},
  "2": {"class_type": "LoadAudio", "inputs": {"audio": "dance_cute1.mp4"}},
  "3": {"class_type": "LatentSyncNode", "inputs": {"images": ["1", 0], "audio": ["2", 0], "seed": 42, "lips_expression": 1.5, "inference_steps": 20}},
  "4": {"class_type": "VHS_VideoCombine", "inputs": {"frame_rate": 16, "loop_count": 0, "filename_prefix": "lipsync", "format": "video/h264-mp4", "pingpong": false, "save_output": true, "images": ["3", 0]}}
}
```

- [ ] **Step 2: Validate JSON parses**

```bash
python3 -c "import json; json.load(open('workflows/model-tests/saved/19_lipsync_latentsync.json')); print('OK')"
```

- [ ] **Step 3: Submit to ComfyUI**

```bash
cd workflows/model-tests && python3 run.py saved/19_lipsync_latentsync.json
```

- [ ] **Step 4: Commit**

```bash
git add workflows/model-tests/saved/19_lipsync_latentsync.json
git commit -m "feat: add WF 19 lip sync (LatentSync)"
```

---

## Task 5: Write Workflow 17 — Video Face Swap (BFS V3)

**Goal:** Create `17_face_swap_bfs_ltx23.json`. Depends on Task 1 results for BFS template prep class_type.

**Blocked by:** Task 1 (BFS node resolution)

**Files:**
- Create: `workflows/model-tests/saved/17_face_swap_bfs_ltx23.json`
- Reference: spec section "Workflow 17", `workflows/model-tests/saved/10_ltx23_t2v.json` (LTX 2.3 pattern)

- [ ] **Step 1: Verify BFS node resolved**

Check Task 1 results. If BFS custom node is not installed, this task is **blocked** — skip and note in README.

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
bfs = [k for k in data if 'bfs' in k.lower() or 'head_swap' in k.lower()]
print(bfs if bfs else 'NOT FOUND')
"
```

- [ ] **Step 2: Write the workflow JSON**

Use the spec node table, substituting the resolved BFS class_type for node 6. Also resolve the BFS LoRA filename. The LTX 2.3 generation pattern (nodes 3-5, 8-15) mirrors `10_ltx23_t2v.json`.

```json
{
  "1": {"class_type": "VHS_LoadVideo", "inputs": {"video": "dance_cute1.mp4", "force_rate": 0, "custom_width": 0, "custom_height": 0, "frame_load_cap": 49, "skip_first_frames": 0, "select_every_nth": 1}},
  "2": {"class_type": "LoadImage", "inputs": {"image": "risa_face.jpeg"}},
  "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"}},
  "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": "<RESOLVED_BFS_LORA_FILENAME>", "strength_model": 1.0, "model": ["3", 0]}},
  "5": {"class_type": "LTXAVTextEncoderLoader", "inputs": {"text_encoder": "ltx-2.3-22b-dev_embeddings_connectors.safetensors", "ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors", "device": "default"}},
  "6": {"class_type": "<RESOLVED_BFS_TEMPLATE_PREP>", "inputs": {"guide_video": ["1", 0], "reference_face": ["2", 0]}},
  "7": {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["3", 2]}},
  "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "head_swap: FACE: young Thai-Japanese woman with long dark hair ACTION: dancing gracefully", "clip": ["5", 0]}},
  "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, deformed", "clip": ["5", 0]}},
  "10": {"class_type": "LTXVConditioning", "inputs": {"positive": ["8", 0], "negative": ["9", 0], "frame_rate": 24}},
  "11": {"class_type": "ModelSamplingLTXV", "inputs": {"max_shift": 2.05, "base_shift": 0.95, "model": ["4", 0]}},
  "12": {"class_type": "LTXVScheduler", "inputs": {"steps": 8, "max_shift": 2.05, "base_shift": 0.95, "stretch": true, "terminal": 0.1}},
  "13": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "14": {"class_type": "RandomNoise", "inputs": {"noise_seed": 20260417}},
  "15": {"class_type": "SamplerCustom", "inputs": {"add_noise": true, "noise_seed": 20260417, "cfg": 3.0, "model": ["11", 0], "positive": ["10", 0], "negative": ["10", 1], "sampler": ["13", 0], "sigmas": ["12", 0], "latent_image": ["7", 0]}},
  "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["3", 2]}},
  "17": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["16", 0], "frame_rate": 24, "loop_count": 0, "filename_prefix": "face_swap", "format": "video/h264-mp4", "pingpong": false, "save_output": true}}
}
```

Replace `<RESOLVED_BFS_TEMPLATE_PREP>` and `<RESOLVED_BFS_LORA_FILENAME>` with values from Task 1.

- [ ] **Step 3: Validate JSON parses**

```bash
python3 -c "import json; json.load(open('workflows/model-tests/saved/17_face_swap_bfs_ltx23.json')); print('OK')"
```

- [ ] **Step 4: Submit to ComfyUI**

```bash
cd workflows/model-tests && python3 run.py saved/17_face_swap_bfs_ltx23.json
```

- [ ] **Step 5: Commit**

```bash
git add workflows/model-tests/saved/17_face_swap_bfs_ltx23.json
git commit -m "feat: add WF 17 video face swap (BFS V3 + LTX 2.3)"
```

---

## Task 6: Write Workflow 18 — I2V with Motion Control

**Goal:** Create `18_motion_control_sdsteady_ltx23.json`. Depends on Task 1 results for SDPose and SteadyDancer class_types.

**Blocked by:** Task 1 (SDPose + SteadyDancer node resolution)

**Files:**
- Create: `workflows/model-tests/saved/18_motion_control_sdsteady_ltx23.json`
- Reference: spec section "Workflow 18", `workflows/model-tests/saved/10_ltx23_t2v.json`

- [ ] **Step 1: Verify SDPose and SteadyDancer nodes resolved**

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
for kw in ['sdpose', 'steady', 'dancer', 'pose']:
    found = [k for k in data if kw in k.lower()]
    if found: print(f'{kw}: {found}')
"
```

If either node is missing, this task is **blocked**.

- [ ] **Step 2: Write the workflow JSON**

Use the spec node table, substituting resolved class_types for nodes 5 and 6. Watch the VAEEncode input: spec says `[6, 0]` (SteadyDancer output) but notes fallback to `[1, 0]` if SteadyDancer doesn't produce IMAGE output.

```json
{
  "1": {"class_type": "LoadImage", "inputs": {"image": "risa_body.jpeg"}},
  "2": {"class_type": "VHS_LoadVideo", "inputs": {"video": "dance_cute1.mp4", "force_rate": 0, "custom_width": 0, "custom_height": 0, "frame_load_cap": 49, "skip_first_frames": 0, "select_every_nth": 1}},
  "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"}},
  "4": {"class_type": "LTXAVTextEncoderLoader", "inputs": {"text_encoder": "ltx-2.3-22b-dev_embeddings_connectors.safetensors", "ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors", "device": "default"}},
  "5": {"class_type": "<RESOLVED_SDPOSE>", "inputs": {"video": ["2", 0]}},
  "6": {"class_type": "<RESOLVED_STEADYDANCER>", "inputs": {"image": ["1", 0], "pose": ["5", 0]}},
  "7": {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["3", 2]}},
  "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "character dancing gracefully, fluid movement, cinematic lighting", "clip": ["4", 0]}},
  "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, static, deformed", "clip": ["4", 0]}},
  "10": {"class_type": "LTXVConditioning", "inputs": {"positive": ["8", 0], "negative": ["9", 0], "frame_rate": 24}},
  "11": {"class_type": "ModelSamplingLTXV", "inputs": {"max_shift": 2.05, "base_shift": 0.95, "model": ["3", 0]}},
  "12": {"class_type": "LTXVScheduler", "inputs": {"steps": 8, "max_shift": 2.05, "base_shift": 0.95, "stretch": true, "terminal": 0.1}},
  "13": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "14": {"class_type": "RandomNoise", "inputs": {"noise_seed": 20260417}},
  "15": {"class_type": "SamplerCustom", "inputs": {"add_noise": true, "noise_seed": 20260417, "cfg": 3.0, "model": ["11", 0], "positive": ["10", 0], "negative": ["10", 1], "sampler": ["13", 0], "sigmas": ["12", 0], "latent_image": ["7", 0]}},
  "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["3", 2]}},
  "17": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["16", 0], "frame_rate": 24, "loop_count": 0, "filename_prefix": "motion_control", "format": "video/h264-mp4", "pingpong": false, "save_output": true}}
}
```

- [ ] **Step 3: Validate JSON parses**

```bash
python3 -c "import json; json.load(open('workflows/model-tests/saved/18_motion_control_sdsteady_ltx23.json')); print('OK')"
```

- [ ] **Step 4: Submit to ComfyUI**

```bash
cd workflows/model-tests && python3 run.py saved/18_motion_control_sdsteady_ltx23.json
```

- [ ] **Step 5: Commit**

```bash
git add workflows/model-tests/saved/18_motion_control_sdsteady_ltx23.json
git commit -m "feat: add WF 18 I2V motion control (SDPose + SteadyDancer + LTX 2.3)"
```

---

## Task 7: Write Workflow 20 — StoryDiffusion Character Image

**Goal:** Create `20_storydiffusion_sdxl.json`. Depends on Task 1 results for StoryDiffusion and CLIPVisionLoader class_types.

**Blocked by:** Task 1 (StoryDiffusion node resolution), SDXL checkpoint availability

**Files:**
- Create: `workflows/model-tests/saved/20_storydiffusion_sdxl.json`
- Reference: spec section "Workflow 20"

- [ ] **Step 1: Verify StoryDiffusion nodes and SDXL checkpoint**

```bash
# Check StoryDiffusion nodes
curl -s http://localhost:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
sd = [k for k in data if 'story' in k.lower()]
print(f'StoryDiffusion nodes: {sd}' if sd else 'StoryDiffusion: NOT FOUND')
"

# Check SDXL checkpoint availability
curl -s http://localhost:8188/object_info/CheckpointLoaderSimple | python3 -c "
import json, sys
data = json.load(sys.stdin)
ckpt = data['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
sdxl = [c for c in ckpt if 'sdxl' in c.lower()]
print(f'SDXL checkpoints: {sdxl}' if sdxl else 'No SDXL checkpoints found')
"
```

If StoryDiffusion or SDXL not available, this task is **blocked**.

- [ ] **Step 2: Write the workflow JSON**

Use the spec node table, substituting resolved class_types for nodes 3 and 4. Replace `sdxl_base_1.0.safetensors` with the actual SDXL checkpoint name found.

```json
{
  "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "<RESOLVED_SDXL_CHECKPOINT>"}},
  "2": {"class_type": "LoadImage", "inputs": {"image": "risa_avatar.jpeg"}},
  "3": {"class_type": "<RESOLVED_CLIP_VISION_LOADER>", "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"}},
  "4": {"class_type": "<RESOLVED_STORYDIFFUSION_NODE>", "inputs": {"model": ["1", 0], "reference_image": ["2", 0], "clip_vision": ["3", 0], "seed": 20260417}},
  "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "a young woman sitting at a cafe table, warm lighting, detailed face, portrait photo, 4k", "clip": ["1", 1]}},
  "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
  "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
  "8": {"class_type": "KSampler", "inputs": {"seed": 20260417, "steps": 25, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0]}},
  "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["1", 2]}},
  "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "storydiffusion"}}
}
```

- [ ] **Step 3: Validate JSON parses**

```bash
python3 -c "import json; json.load(open('workflows/model-tests/saved/20_storydiffusion_sdxl.json')); print('OK')"
```

- [ ] **Step 4: Submit to ComfyUI**

```bash
cd workflows/model-tests && python3 run.py saved/20_storydiffusion_sdxl.json
```

- [ ] **Step 5: Commit**

```bash
git add workflows/model-tests/saved/20_storydiffusion_sdxl.json
git commit -m "feat: add WF 20 StoryDiffusion character image (SDXL)"
```

---

## Task 8: Generate UI Format Variants

**Goal:** Convert all validated API-format workflows to UI/graph format using `api_to_ui.py`, so they render correctly on the ComfyUI canvas.

**Blocked by:** Tasks 2-7 (all workflows must be written first)

**Files:**
- Create: `workflows/model-tests/saved/*_ui.json` for each workflow

- [ ] **Step 1: Convert all workflows**

```bash
cd workflows/model-tests
for f in saved/15_*.json saved/16_*.json saved/17_*.json saved/18_*.json saved/19_*.json saved/20_*.json; do
  if [ -f "$f" ]; then
    python3 api_to_ui.py "$f"
    echo "Converted: $f"
  fi
done
```

- [ ] **Step 2: Verify UI files exist**

```bash
ls -la saved/*_ui.json
```

- [ ] **Step 3: Commit**

```bash
git add workflows/model-tests/saved/*_ui.json
git commit -m "feat: add UI format variants for workflows 15-20"
```

---

## Task 9: Update README

**Goal:** Add the 6 new workflows to the results table in `workflows/model-tests/README.md`.

**Files:**
- Modify: `workflows/model-tests/README.md`

- [ ] **Step 1: Add rows to results table**

Add after the existing last row (Animatediff SDXL):

```markdown
| 15 | `15_video_upscaler_ltx23.json` | LTX 2.3 spatial upscaler | Video upscale | queued | — | — |
| 16 | `16_image_upscaler_zimage.json` | Z-Image turbo | Image upscale | queued | — | — |
| 17 | `17_face_swap_bfs_ltx23.json` | LTX 2.3 + BFS V3 LoRA | Face swap | queued | — | — |
| 18 | `18_motion_control_sdsteady_ltx23.json` | LTX 2.3 + SDPose + SteadyDancer | I2V motion | queued | — | — |
| 19 | `19_lipsync_latentsync.json` | LatentSync | Lip sync | queued | — | — |
| 20 | `20_storydiffusion_sdxl.json` | SDXL + StoryDiffusion | Character image | queued | — | — |
```

- [ ] **Step 2: Commit**

```bash
git add workflows/model-tests/README.md
git commit -m "docs: add workflows 15-20 to model test README"
```

---

## Execution Notes

**Dependency graph:**
- Tasks 2, 3, 4 can run in parallel (no TBDs, no dependencies)
- Task 1 must complete before Tasks 5, 6, 7
- Task 8 requires all of Tasks 2-7
- Task 9 can run any time after Tasks 2-7

**Blocked workflow handling:** If a custom node (BFS, SDPose, SteadyDancer, StoryDiffusion) isn't installed, the corresponding workflow JSON can still be written with placeholder class_types. The ComfyUI submission will fail validation, but the file serves as a template once the node is installed. Mark as "blocked" in README.

**Timeout considerations:** Video workflows (15, 17, 18) may take several minutes on the AMD 8060S. The default `run.py` timeout is 1800s (30 min). Image workflows (16, 19, 20) should complete within a few minutes.
