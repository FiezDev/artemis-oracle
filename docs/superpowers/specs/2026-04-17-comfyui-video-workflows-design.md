# ComfyUI Video/Image Processing Workflows

**Date:** 2026-04-17
**Status:** Approved
**Author:** Artemis (for FiezDev)

---

## Overview

Six standalone ComfyUI API-format workflow JSON files for video and image processing, targeting the local ComfyUI instance (AMD Radeon 8060S, 120GB VRAM, ROCm 7.12, Docker `comfyui-gfx1151-wsl2`).

All files follow the existing project pattern: API-format JSONs in `workflows/model-tests/saved/`, runnable via `run.py` against `localhost:8188`.

LTX 2.3 workflows (17, 18) use the `SamplerCustom` + `LTXVConditioning` + `ModelSamplingLTXV` pattern established in the existing `10_ltx23_t2v.json`.
Workflow 20 (StoryDiffusion) uses SDXL with consistent self-attention for character-consistent image generation.

## File Inventory

| # | File | Purpose | Primary Model |
|---|------|---------|---------------|
| 15 | `15_video_upscaler_ltx23.json` | 2x spatial video upscale | LTX 2.3 spatial upscaler |
| 16 | `16_image_upscaler_zimage.json` | Image upscale (img2img) | Z-Image turbo |
| 17 | `17_face_swap_bfs_ltx23.json` | Video face swap (persistent template) | LTX 2.3 + BFS V3 LoRA |
| 18 | `18_motion_control_sdsteady_ltx23.json` | I2V with pose/motion control | LTX 2.3 + SDPose + SteadyDancer |
| 19 | `19_lipsync_latentsync.json` | Lip sync from audio | LatentSync |
| 20 | `20_storydiffusion_sdxl.json` | Character-consistent image gen | SDXL + StoryDiffusion |

---

## LTX 2.3 Common Pattern (Workflows 17, 18)

All LTX 2.3 video generation workflows share this node configuration, derived from the working `10_ltx23_t2v.json`:

| Component | class_type | Notes |
|-----------|-----------|-------|
| Model load | `CheckpointLoaderSimple` | `ltx-2.3-22b-dev-fp8.safetensors` (loads UNET+CLIP+VAE) |
| Optional LoRA | `LoraLoaderModelOnly` | Chains off model output |
| Text encoder | `LTXAVTextEncoderLoader` | NOT plain CLIPLoader — LTX 2.3 requires this specialized loader |
| Conditioning | `LTXVConditioning` | Wraps positive/negative with `frame_rate: 24` |
| Sampling setup | `ModelSamplingLTXV` | `max_shift: 2.05, base_shift: 0.95` |
| Sigmas | `LTXVScheduler` | `steps: 8, stretch: true, terminal: 0.1` |
| Sampler | `SamplerCustom` | Uses `KSamplerSelect` + `RandomNoise`, not plain KSampler |
| VAE decode | `VAEDecode` | VAE from `CheckpointLoaderSimple` output slot 2 |
| Video output | `VHS_VideoCombine` | `frame_rate: 24, format: "video/h264-mp4"` |

---

## Workflow 15 — Video Upscaler

**Goal:** Load a video, upscale 2x in latent space preserving aspect ratio, output upscaled MP4.

### Pipeline

```
VHS_LoadVideo → VAEEncode → LTXVLatentUpsampler(2x) → VAEDecode → VHS_VideoCombine
                 ↑            ↑           ↑
            VAELoader    UpscaleModel  VAELoader
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `VHS_LoadVideo` | `video: "dance_cute1.mp4", frame_load_cap: 16, force_rate: 0, custom_width: 0, custom_height: 0, skip_first_frames: 0, select_every_nth: 1` |
| 2 | `VAELoader` | `vae_name: "ltx-2.3-22b-dev_video_vae.safetensors"` |
| 3 | `LatentUpscaleModelLoader` | `model_name: "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"` |
| 4 | `VAEEncode` | `pixels: [1, 0], vae: [2, 0]` |
| 5 | `LTXVLatentUpsampler` | `samples: [4, 0], upscale_model: [3, 0], vae: [2, 0]` |
| 6 | `VAEDecode` | `samples: [5, 0], vae: [2, 0]` |
| 7 | `VHS_VideoCombine` | `images: [6, 0], frame_rate: 8, loop_count: 0, filename_prefix: "upscale_video", format: "video/h264-mp4", pingpong: false, save_output: true` |

**Verified against:** `templates/video_ltx2_3_i2v_edit.json` — `LTXVLatentUpsampler` takes three inputs: `samples` (LATENT), `upscale_model` (LATENT_UPSCALE_MODEL), `vae` (VAE). No sampling step needed — the upscaler model IS the processor.

### Output
- `upscale_video_00001.mp4` — 2x spatial upscale of input video

---

## Workflow 16 — Image Upscaler

**Goal:** Load an image, upscale 2x and refine with Z-Image turbo via img2img, output high-quality PNG.

### Pipeline

```
LoadImage → ImageScale(2x) → VAEEncode → KSampler(denoise=0.4) → VAEDecode → SaveImage
                                          ↑
                          UNETLoader(z_image_turbo_bf16)
                          ModelSamplingAuraFlow(shift=3.0)
                          CLIPLoader(qwen_3_4b, lumina2)
                          VAELoader(ae.safetensors)
                          CLIPTextEncode (positive + negative)
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `LoadImage` | `image: "risa_body.jpeg"` |
| 2 | `ImageScaleBy` | `image: [1, 0], upscale_method: "nearest-exact", scale_by: 2.0` |
| 3 | `UNETLoader` | `unet_name: "z_image_turbo_bf16.safetensors", weight_dtype: "default"` |
| 4 | `ModelSamplingAuraFlow` | `shift: 3.0, model: [3, 0]` |
| 5 | `CLIPLoader` | `clip_name: "qwen_3_4b.safetensors", type: "lumina2"` |
| 6 | `VAELoader` | `vae_name: "ae.safetensors"` |
| 7 | `VAEEncode` | `pixels: [2, 0], vae: [6, 0]` |
| 8 | `CLIPTextEncode` | `text: "high quality, detailed, sharp, 4k, professional photo", clip: [5, 0]` |
| 9 | `ConditioningZeroOut` | `conditioning: [8, 0]` |
| 10 | `KSampler` | `seed: 20260417, steps: 4, cfg: 1.0, sampler_name: "res_multistep", scheduler: "simple", denoise: 0.4, model: [4, 0], positive: [8, 0], negative: [9, 0], latent_image: [7, 0]` |
| 11 | `VAEDecode` | `samples: [10, 0], vae: [6, 0]` |
| 12 | `SaveImage` | `images: [11, 0], filename_prefix: "upscale_image"` |

**Verified against:** `saved/02_zimage_turbo_risa.json` — exact model names and sampler settings confirmed. `ModelSamplingAuraFlow` with `shift: 3.0` is required for Z-Image quality. Uses `ConditioningZeroOut` for negative (same as working workflow). The upscale approach: `ImageScale` resizes the raw image to 2x, then img2img refines at `denoise: 0.4` to add detail without losing content.

### Output
- `upscale_image_00001_.png` — upscaled and refined version of input image

---

## Workflow 17 — Video Face Swap (BFS V3)

**Goal:** Swap a reference face onto every frame of a guide video using BFS V3 persistent-template method + LTX 2.3.

### Pipeline

```
VHS_LoadVideo (guide) ──┐
LoadImage (ref face) ───┤
                         ├→ [BFS Template Prep] → VAEEncode → SamplerCustom → VAEDecode → VHS_VideoCombine
CheckpointLoader (LTX) ─┤                              ↑
LoraLoader (BFS LoRA) ──┤                         LTXVConditioning
LTXAVTextEncoder ───────┘                         ModelSamplingLTXV
                                                  LTXVScheduler + KSamplerSelect + RandomNoise
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `VHS_LoadVideo` | `video: "dance_cute1.mp4", frame_load_cap: 49, force_rate: 0, custom_width: 0, custom_height: 0, skip_first_frames: 0, select_every_nth: 1` |
| 2 | `LoadImage` | `image: "risa_face.jpeg"` |
| 3 | `CheckpointLoaderSimple` | `ckpt_name: "ltx-2.3-22b-dev-fp8.safetensors"` |
| 4 | `LoraLoaderModelOnly` | `lora_name: "BFS-Best-Face-Swap-Video-V3.safetensors", strength_model: 1.0, model: [3, 0]` |
| 5 | `LTXAVTextEncoderLoader` | `text_encoder: "ltx-2.3-22b-dev_embeddings_connectors.safetensors", ckpt_name: "ltx-2.3-22b-dev-fp8.safetensors", device: "default"` |
| 6 | **BFS template prep** (class_type TBD) | `guide_video: [1, 0], reference_face: [2, 0]` → outputs IMAGE |
| 7 | `VAEEncode` | `pixels: [6, 0], vae: [3, 2]` (VAE from checkpoint slot 2) |
| 8 | `CLIPTextEncode` | `text: "head_swap: FACE: [identity description] ACTION: [action description]", clip: [5, 0]` |
| 9 | `CLIPTextEncode` | `text: "blurry, low quality, deformed", clip: [5, 0]` |
| 10 | `LTXVConditioning` | `positive: [8, 0], negative: [9, 0], frame_rate: 24` |
| 11 | `ModelSamplingLTXV` | `max_shift: 2.05, base_shift: 0.95, model: [4, 0]` |
| 12 | `LTXVScheduler` | `steps: 8, max_shift: 2.05, base_shift: 0.95, stretch: true, terminal: 0.1` |
| 13 | `KSamplerSelect` | `sampler_name: "euler"` |
| 14 | `RandomNoise` | `noise_seed: 20260417` |
| 15 | `SamplerCustom` | `add_noise: true, noise_seed: 20260417, cfg: 3.0, model: [11, 0], positive: [10, 0], negative: [10, 1], sampler: [13, 0], sigmas: [12, 0], latent_image: [7, 0]` |
| 16 | `VAEDecode` | `samples: [15, 0], vae: [3, 2]` |
| 17 | `VHS_VideoCombine` | `images: [16, 0], frame_rate: 24, loop_count: 0, filename_prefix: "face_swap", format: "video/h264-mp4", pingpong: false, save_output: true` |

**Verified against:** `saved/10_ltx23_t2v.json` — uses identical LTX 2.3 generation pattern (CheckpointLoaderSimple + LTXAVTextEncoderLoader + LTXVConditioning + SamplerCustom chain).

### Open Items (resolve during implementation)
1. **BFS template prep class_type** — Must query `/object_info` on `localhost:8188` after installing `ComfyUI-BFSNodes`. The BFS V3 workflow file from the repo (`workflows/workflow_ltx2_head_swap_drag_and_drop_v3.0`) contains the exact node names.
2. **BFS LoRA filename** — Must be confirmed after download from `Alissonerdx/BFS-Best-Face-Swap-Video` on HuggingFace.
3. **frame_load_cap** — Set to 49 (2 seconds at 24fps). Adjust based on VRAM availability.
4. **Positive/negative from LTXVConditioning** — `LTXVConditioning` outputs two slots: `[10, 0]` = positive, `[10, 1]` = negative. `SamplerCustom` takes both.

### Output
- `face_swap_00001.mp4` — guide video with reference face swapped in

---

## Workflow 18 — I2V with Motion Control

**Goal:** Generate video from a character image, following pose/motion extracted from a reference dance video.

### Pipeline

```
LoadImage (character) ─────┐
                            ├→ SteadyDancer → VAEEncode → SamplerCustom → VAEDecode → VHS_VideoCombine
VHS_LoadVideo → SDPose ────┘                      ↑
                                            LTXVConditioning
CheckpointLoader (LTX 2.3) ────────────    ModelSamplingLTXV
LTXAVTextEncoder ──────────────────────    LTXVScheduler + KSamplerSelect + RandomNoise
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `LoadImage` | `image: "risa_body.jpeg"` |
| 2 | `VHS_LoadVideo` | `video: "dance_cute1.mp4", frame_load_cap: 49, force_rate: 0, custom_width: 0, custom_height: 0, skip_first_frames: 0, select_every_nth: 1` |
| 3 | `CheckpointLoaderSimple` | `ckpt_name: "ltx-2.3-22b-dev-fp8.safetensors"` |
| 4 | `LTXAVTextEncoderLoader` | `text_encoder: "ltx-2.3-22b-dev_embeddings_connectors.safetensors", ckpt_name: "ltx-2.3-22b-dev-fp8.safetensors", device: "default"` |
| 5 | **SDPose node** (class_type TBD) | `video: [2, 0]` → outputs pose keypoints |
| 6 | **SteadyDancer node** (class_type TBD) | `image: [1, 0], pose: [5, 0]` → outputs IMAGE/VIDEO frames with motion applied |
| 7 | `VAEEncode` | `pixels: [6, 0], vae: [3, 2]` |
| 8 | `CLIPTextEncode` | `text: "character dancing gracefully, fluid movement, cinematic lighting", clip: [4, 0]` |
| 9 | `CLIPTextEncode` | `text: "blurry, low quality, static, deformed", clip: [4, 0]` |
| 10 | `LTXVConditioning` | `positive: [8, 0], negative: [9, 0], frame_rate: 24` |
| 11 | `ModelSamplingLTXV` | `max_shift: 2.05, base_shift: 0.95, model: [3, 0]` |
| 12 | `LTXVScheduler` | `steps: 8, max_shift: 2.05, base_shift: 0.95, stretch: true, terminal: 0.1` |
| 13 | `KSamplerSelect` | `sampler_name: "euler"` |
| 14 | `RandomNoise` | `noise_seed: 20260417` |
| 15 | `SamplerCustom` | `add_noise: true, noise_seed: 20260417, cfg: 3.0, model: [11, 0], positive: [10, 0], negative: [10, 1], sampler: [13, 0], sigmas: [12, 0], latent_image: [7, 0]` |
| 16 | `VAEDecode` | `samples: [15, 0], vae: [3, 2]` |
| 17 | `VHS_VideoCombine` | `images: [16, 0], frame_rate: 24, loop_count: 0, filename_prefix: "motion_control", format: "video/h264-mp4", pingpong: false, save_output: true` |

### Open Items (resolve during implementation)
1. **SDPose class_type** — Query `/object_info` after installing `ComfyUI-SDPose-OOD`. The node may be named `SDPose_OOD`, `SDPoseEstimator`, or similar.
2. **SteadyDancer class_type** — Query `/object_info` after installing `ComfyUI-SteadyDancer`. Input/output format needs verification.
3. **SDPose → SteadyDancer wiring** — If SDPose outputs keypoints in a format SteadyDancer doesn't accept, an adapter node may be needed (placeholder: insert between nodes 5 and 6).
4. **VAEEncode input** — Set to `[6, 0]` (SteadyDancer output with motion applied). If SteadyDancer doesn't produce suitable output, fallback to `[1, 0]` (original character image) and use pose data as conditioning input instead.

### Output
- `motion_control_00001.mp4` — character video following reference dance motion

---

## Workflow 19 — Lip Sync

**Goal:** Generate lip-synced video from a face image and audio input.

### Pipeline

```
LoadImage (face) ──→ LatentSyncNode ──→ VHS_VideoCombine
LoadAudio ──────────┘
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `LoadImage` | `image: "fashion_face1.jpeg"` |
| 2 | `LoadAudio` | `audio: "dance_cute1.mp4"` |
| 3 | `LatentSyncNode` | `images: [1, 0], audio: [2, 0], seed: 42, lips_expression: 1.5, inference_steps: 20` |
| 4 | `VHS_VideoCombine` | `images: [3, 0], frame_rate: 16, loop_count: 0, filename_prefix: "lipsync", format: "video/h264-mp4", pingpong: false, save_output: true` |

**Verified against:** `gen-output/comfyui-tests/14-latentsync.json` — exact copy of working workflow with consistent naming.

### Output
- `lipsync_00001.mp4` — face with lip-synced animation

---

## Workflow 20 — StoryDiffusion Character Image Generation

**Goal:** Generate character-consistent images using SDXL + StoryDiffusion's consistent self-attention mechanism. Takes a reference character image and a scene prompt, outputs images that maintain the character's identity.

### Pipeline

```
LoadImage (ref character) ──→ StoryDiffusion_Apply ──→ KSampler ──→ VAEDecode ──→ SaveImage
                              ↑           ↑               ↑
                    CheckpointLoader(SDXL)  │        CLIPTextEncode
                    CLIPVisionLoader         │      ConditioningZeroOut
                    (CLIP-ViT-bigG)          │
                    ms_adapter.bin ──────────┘
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `CheckpointLoaderSimple` | `ckpt_name: "sdxl_base_1.0.safetensors"` |
| 2 | `LoadImage` | `image: "risa_avatar.jpeg"` |
| 3 | **`CLIPVisionLoader`** (class_type TBD) | `clip_name: "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"` |
| 4 | **`StoryDiffusion_Apply`** (class_type TBD) | `model: [1, 0], reference_image: [2, 0], clip_vision: [3, 0], adapter_path: "ms_adapter.bin", seed: 20260417` |
| 5 | `CLIPTextEncode` | `text: "a young woman sitting at a cafe table, warm lighting, detailed face, portrait photo, 4k", clip: [1, 1]` |
| 6 | `ConditioningZeroOut` | `conditioning: [5, 0]` |
| 7 | `EmptyLatentImage` | `width: 1024, height: 1024, batch_size: 1` |
| 8 | `KSampler` | `seed: 20260417, steps: 25, cfg: 7.0, sampler_name: "euler", scheduler: "normal", denoise: 1.0, model: [4, 0], positive: [5, 0], negative: [6, 0], latent_image: [7, 0]` |
| 9 | `VAEDecode` | `samples: [8, 0], vae: [1, 2]` |
| 10 | `SaveImage` | `images: [9, 0], filename_prefix: "storydiffusion"` |

### StoryDiffusion Details

StoryDiffusion uses **consistent self-attention** to maintain character identity across generated images. The `ms_adapter.bin` model enables the self-attention mechanism that locks in facial features from the reference image. Optional `photomaker-v1.bin` can be added for enhanced identity preservation.

**Key features:**
- Dual-role generation: prompt with `(A and B)` to place two instances of the same character in one frame
- LoRA integration: chain `LoraLoaderModelOnly` after checkpoint for style control
- img2img mode: replace `EmptyLatentImage` with `VAEEncode` of a base image for guided generation

### Open Items (resolve during implementation)
1. **Exact class_types** — Query `/object_info` after installing `ComfyUI_StoryDiffusion`. Node names may be `StoryDiffusion_ConsistentCharacter`, `StoryDiffusionSampler`, or similar.
2. **SDXL checkpoint** — Confirm which SDXL checkpoint is available in `/data/models/checkpoints/`. Alternatives: `sdxl_refiner_1.0.safetensors`, custom SDXL fine-tunes.
3. **CLIP vision encoder path** — Must be placed in `/data/models/clip_vision/` (or wherever ComfyUI expects vision encoders).
4. **ms_adapter.bin path** — Download from `https://huggingface.co/InstantX/StoryDiffusion` into the directory expected by the custom node (typically `ComfyUI_StoryDiffusion/models/`).

### Output
- `storydiffusion_00001_.png` — character-consistent image based on reference + prompt

---

## Dependencies

### Custom Nodes (must be installed)

| Node | Repo | Purpose | Status |
|------|------|---------|--------|
| `ComfyUI-BFSNodes` | `alisson-anjos/ComfyUI-BFSNodes` | BFS V3 template preparation | **needs install** |
| `ComfyUI-SDPose-OOD` | `judian17/ComfyUI-SDPose-OOD` | Pose estimation from video | **needs install** |
| `ComfyUI-SteadyDancer` | `1038lab/ComfyUI-SteadyDancer` | Motion transfer from pose | **needs install** |
| `ComfyUI-VideoHelperSuite` | already installed | VHS_LoadVideo, VHS_VideoCombine | installed |
| `LatentSync` | already installed | Lip sync | installed |
| `ComfyUI_StoryDiffusion` | `HvisionBiao/ComfyUI_StoryDiffusion` | Character-consistent image generation | **needs install** |

### Model Files (must be in `/data/models/`)

| File | Location | Used In | Source |
|------|----------|---------|--------|
| `ltx-2.3-22b-dev-fp8.safetensors` | `/data/models/checkpoints/` | WF 17, 18 | already present |
| `ltx-2.3-22b-dev_embeddings_connectors.safetensors` | `/data/models/clip/` | WF 17, 18 | already present |
| `ltx-2.3-22b-dev_video_vae.safetensors` | `/data/models/vae/` | WF 15, 17, 18 | already present |
| `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | `/data/models/unet/` | WF 15 | already present |
| `z_image_turbo_bf16.safetensors` | `/data/models/unet/` | WF 16 | already present |
| `qwen_3_4b.safetensors` | `/data/models/clip/` | WF 16 | already present |
| `ae.safetensors` | `/data/models/vae/` | WF 16 | already present |
| BFS V3 LoRA | `/data/models/loras/` | WF 17 | **needs download** from `Alissonerdx/BFS-Best-Face-Swap-Video` |
| `sdxl_base_1.0.safetensors` | `/data/models/checkpoints/` | WF 20 | **needs download** (or use existing SDXL checkpoint) |
| `CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors` | `/data/models/clip_vision/` | WF 20 | **needs download** from `laion/CLIP-ViT-bigG-14-laion2B-39B-b160k` |
| `ms_adapter.bin` | `ComfyUI_StoryDiffusion/models/` | WF 20 | **needs download** from `InstantX/StoryDiffusion` |

### Reference Assets (in `/data/input/`)

| Asset | Used In |
|-------|---------|
| `risa_body.jpeg` | WF 16, 18 |
| `risa_face.jpeg` | WF 17 |
| `risa_avatar.jpeg` | WF 20 |
| `fashion_face1.jpeg` | WF 19 |
| `dance_cute1.mp4` | WF 15, 17, 18 |

---

## Implementation Notes

1. **Resolve TBD class_types first** — Before writing the actual JSON files, query `localhost:8188/object_info` for BFS template prep node, SDPose node, and SteadyDancer node class_types and input schemas. This is the first implementation step.

2. **BFS V3 workflow reference** — After installing `ComfyUI-BFSNodes`, check the included workflow file `workflows/workflow_ltx2_head_swap_drag_and_drop_v3.0` for the exact node configuration.

3. **Z-Image upscale approach** — Uses img2img at 2x resolution with `denoise: 0.4`. The `ImageScale` node handles the raw pixel resize, then Z-Image refines detail. If quality is insufficient, try increasing denoise to 0.5–0.6.

4. **Aspect ratio** — Workflow 16 uses `ImageScaleBy` with `scale_by: 2.0` which preserves aspect ratio. For workflow 15, the LTX spatial upscaler operates on latents and preserves the original aspect ratio automatically.

5. **UI format variants** — After API JSONs are validated, generate `_ui.json` companions using `api_to_ui.py` for ComfyUI canvas rendering.

6. **StoryDiffusion character reference** — `risa_avatar.jpeg` is the preferred reference for WF 20 as it provides a clear face+upper-body shot for identity locking. For dual-character scenes, use `(A and B)` syntax in the prompt and provide two reference images if the node supports it.

7. **SDXL checkpoint availability** — Check `/data/models/checkpoints/` for any existing SDXL checkpoint before downloading. The workflow can use any SDXL 1.0 base or fine-tune.
