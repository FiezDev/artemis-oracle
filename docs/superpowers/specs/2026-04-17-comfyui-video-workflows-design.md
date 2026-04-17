# ComfyUI Video/Image Processing Workflows

**Date:** 2026-04-17
**Status:** Approved
**Author:** Artemis (for FiezDev)

---

## Overview

Five standalone ComfyUI API-format workflow JSON files for video and image processing, targeting the local ComfyUI instance (AMD Radeon 8060S, 120GB VRAM, ROCm 7.12, Docker `comfyui-gfx1151-wsl2`).

All files follow the existing project pattern: API-format JSONs in `workflows/model-tests/saved/`, runnable via `run.py` against `localhost:8188`.

## File Inventory

| # | File | Purpose | Primary Model |
|---|------|---------|---------------|
| 15 | `15_video_upscaler_ltx23.json` | 2x spatial video upscale | LTX 2.3 spatial upscaler |
| 16 | `16_image_upscaler_zimage.json` | Image upscale | Z-Image turbo |
| 17 | `17_face_swap_bfs_ltx23.json` | Video face swap (persistent template) | LTX 2.3 + BFS V3 LoRA |
| 18 | `18_motion_control_sdsteady_ltx23.json` | I2V with pose/motion control | LTX 2.3 + SDPose + SteadyDancer |
| 19 | `19_lipsync_latentsync.json` | Lip sync from audio | LatentSync |

---

## Workflow 15 — Video Upscaler

**Goal:** Load a video, upscale 2x in latent space preserving aspect ratio, output upscaled MP4.

### Pipeline

```
VHS_LoadVideo → VAEEncode → LTXVLatentUpsampler(2x) → VAEDecode → VHS_VideoCombine
                 ↑                    ↑
            VAELoader      LatentUpscaleModelLoader
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `VHS_LoadVideo` | `video: "dance_cute1.mp4"` |
| 2 | `VAELoader` | `vae_name: "ltx-2.3-22b-dev_video_vae.safetensors"` |
| 3 | `LatentUpscaleModelLoader` | `model_name: "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"` |
| 4 | `VAEEncode` | `pixels: [1, 0], vae: [2, 0]` |
| 5 | `LTXVLatentUpsampler` | `samples: [4, 0], upscale_model: [3, 0]` |
| 6 | `VAEDecode` | `samples: [5, 0], vae: [2, 0]` |
| 7 | `VHS_VideoCombine` | `images: [6, 0], frame_rate: 8, filename_prefix: "upscale_video", format: "video/h264-mp4"` |

### Output
- `upscale_video_00001.mp4` — 2x spatial upscale of input video

---

## Workflow 16 — Image Upscaler

**Goal:** Load an image, upscale using Z-Image turbo model, output high-quality PNG.

### Pipeline

```
LoadImage → VAEEncode → KSampler → VAEDecode → SaveImage
                           ↑
              UNETLoader(z_image_turbo_bf16)
              CLIPLoader + VAELoader
              CLIPTextEncode (positive + negative)
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `LoadImage` | `image: "risa_body.jpeg"` |
| 2 | `UNETLoader` | `unet_name: "z_image_turbo_bf16.safetensors"` |
| 3 | `CLIPLoader` | `clip_name: "...", type: "..."` |
| 4 | `VAELoader` | `vae_name: "..."` (Z-Image VAE) |
| 5 | `VAEEncode` | `pixels: [1, 0], vae: [4, 0]` |
| 6 | `CLIPTextEncode` | `text: "high quality, detailed, sharp, 4k", clip: [3, 0]` |
| 7 | `CLIPTextEncode` | `text: "blurry, low quality, artifacts", clip: [3, 0]` |
| 8 | `KSampler` | `model: [2, 0], positive: [6, 0], negative: [7, 0], latent_image: [5, 0], steps: 4, cfg: 1.0, sampler: "euler", scheduler: "normal", denoise: 0.5` |
| 9 | `VAEDecode` | `samples: [8, 0], vae: [4, 0]` |
| 10 | `SaveImage` | `images: [9, 0], filename_prefix: "upscale_image"` |

### Output
- `upscale_image_00001_.png` — upscaled version of input image

---

## Workflow 17 — Video Face Swap (BFS V3)

**Goal:** Swap a reference face onto every frame of a guide video using BFS V3 persistent-template method + LTX 2.3.

### Pipeline

```
VHS_LoadVideo (guide) ──┐
LoadImage (ref face) ───┤
                         ├→ BFS Template Prep → VAEEncode → KSampler → VAEDecode → VHS_VideoCombine
UNETLoader (LTX 2.3) ───┤      ↑
LoraLoader (BFS LoRA) ──┤      │
CLIPLoader (prompt) ─────┘  Latent
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `VHS_LoadVideo` | `video: "dance_cute1.mp4"` |
| 2 | `LoadImage` | `image: "risa_face.jpeg"` |
| 3 | `UNETLoader` | `unet_name: "ltx-2.3-22b-dev-fp8.safetensors"` |
| 4 | `LoraLoaderModelOnly` | `lora_name: "BFS-Best-Face-Swap-Video-V3.safetensors", strength_model: 1.0, model: [3, 0]` |
| 5 | `CLIPLoader` | `clip_name: "ltx-2.3-22b-dev_embeddings_connectors.safetensors", type: "ltxv"` |
| 6 | `VAELoader` | `vae_name: "ltx-2.3-22b-dev_video_vae.safetensors"` |
| 7 | BFS template prep node | `guide_video: [1, 0], reference_face: [2, 0]` |
| 8 | `VAEEncode` | `pixels: [7, 0], vae: [6, 0]` |
| 9 | `CLIPTextEncode` | `text: "head_swap: FACE: [description] ACTION: [description]", clip: [5, 0]` |
| 10 | `ConditioningZeroOut` | `conditioning: [9, 0]` |
| 11 | `KSampler` | `model: [4, 0], positive: [9, 0], negative: [10, 0], latent_image: [8, 0], steps: 20, cfg: 4.0, sampler: "euler", scheduler: "normal", denoise: 1.0` |
| 12 | `VAEDecode` | `samples: [11, 0], vae: [6, 0]` |
| 13 | `VHS_VideoCombine` | `images: [12, 0], frame_rate: 8, filename_prefix: "face_swap", format: "video/h264-mp4"` |

### Notes
- BFS V3 requires `ComfyUI-BFSNodes` custom node (`github.com/alisson-anjos/ComfyUI-BFSNodes`)
- The BFS LoRA must be downloaded to `/data/models/loras/`
- BFS V3 trigger prompt: `head_swap: FACE: ... ACTION: ...`
- The green chroma-key strip from the composite guide is NOT present in the final output

### Output
- `face_swap_00001.mp4` — guide video with reference face swapped in

---

## Workflow 18 — I2V with Motion Control

**Goal:** Generate video from a character image, following pose/motion extracted from a reference dance video.

### Pipeline

```
LoadImage (character) → VAEEncode ──────────────→ KSampler → VAEDecode → VHS_VideoCombine
                                                         ↑
VHS_LoadVideo (ref) → SDPose → SteadyDancer ─────────────┘
                                                         ↑
LTX 2.3 UNET + CLIP + VAE ─────────────── ConditioningZeroOut (neg)
```

### Nodes

| ID | class_type | Key Inputs |
|----|-----------|------------|
| 1 | `LoadImage` | `image: "risa_body.jpeg"` |
| 2 | `VHS_LoadVideo` | `video: "dance_cute1.mp4"` |
| 3 | `UNETLoader` | `unet_name: "ltx-2.3-22b-dev-fp8.safetensors"` |
| 4 | `CLIPLoader` | `clip_name: "ltx-2.3-22b-dev_embeddings_connectors.safetensors", type: "ltxv"` |
| 5 | `VAELoader` | `vae_name: "ltx-2.3-22b-dev_video_vae.safetensors"` |
| 6 | SDPose node | `video: [2, 0]` (extract pose keypoints from reference) |
| 7 | SteadyDancer node | `image: [1, 0], pose: [6, 0]` (transfer motion to character) |
| 8 | `VAEEncode` | `pixels: [7, 0] or [1, 0], vae: [5, 0]` |
| 9 | `CLIPTextEncode` | `text: "character dancing, fluid movement, cinematic lighting", clip: [4, 0]` |
| 10 | `ConditioningZeroOut` | `conditioning: [9, 0]` |
| 11 | `KSampler` | `model: [3, 0], positive: [9, 0], negative: [10, 0], latent_image: [8, 0], steps: 20, cfg: 4.0, sampler: "euler", scheduler: "normal", denoise: 1.0` |
| 12 | `VAEDecode` | `samples: [11, 0], vae: [5, 0]` |
| 13 | `VHS_VideoCombine` | `images: [12, 0], frame_rate: 8, filename_prefix: "motion_control", format: "video/h264-mp4"` |

### Notes
- SDPose requires `ComfyUI-SDPose-OOD` custom node (`github.com/judian17/ComfyUI-SDPose-OOD`)
- SteadyDancer requires `ComfyUI-SteadyDancer` custom node (`github.com/1038lab/ComfyUI-SteadyDancer`)
- Exact SDPose output format and SteadyDancer input format need verification against installed node schemas
- May require additional pose-to-conditioning adapter nodes

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
| 4 | `VHS_VideoCombine` | `images: [3, 0], frame_rate: 16, loop_count: 0, filename_prefix: "lipsync", format: "video/h264-mp4"` |

### Notes
- Based on existing `gen-output/comfyui-tests/14-latentsync.json`
- `LatentSyncNode` is already installed and working in the current ComfyUI setup

### Output
- `lipsync_00001.mp4` — face with lip-synced animation

---

## Dependencies

### Custom Nodes (must be installed)

| Node | Repo | Purpose |
|------|------|---------|
| `ComfyUI-BFSNodes` | `alisson-anjos/ComfyUI-BFSNodes` | BFS V3 template preparation |
| `ComfyUI-SDPose-OOD` | `judian17/ComfyUI-SDPose-OOD` | Pose estimation from video |
| `ComfyUI-SteadyDancer` | `1038lab/ComfyUI-SteadyDancer` | Motion transfer from pose |
| `ComfyUI-VideoHelperSuite` | already installed | VHS_LoadVideo, VHS_VideoCombine |
| `LatentSync` (node) | already installed | Lip sync |

### Model Files (must be in `/data/models/`)

| File | Location | Used In |
|------|----------|---------|
| `ltx-2.3-22b-dev-fp8.safetensors` | `/data/models/unet/` | WF 17, 18 |
| `ltx-2.3-22b-dev_embeddings_connectors.safetensors` | `/data/models/clip/` | WF 17, 18 |
| `ltx-2.3-22b-dev_video_vae.safetensors` | `/data/models/vae/` | WF 15, 17, 18 |
| `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | `/data/models/unet/` | WF 15 |
| `z_image_turbo_bf16.safetensors` | `/data/models/unet/` | WF 16 |
| BFS V3 LoRA (TBD) | `/data/models/loras/` | WF 17 |

### Reference Assets (in `/data/input/`)

| Asset | Used In |
|-------|---------|
| `risa_body.jpeg` | WF 16, 18 |
| `risa_face.jpeg` | WF 17 |
| `fashion_face1.jpeg` | WF 19 |
| `dance_cute1.mp4` | WF 15, 17, 18 |

---

## Implementation Notes

1. **Exact node class_types and input schemas** must be verified against the live `/object_info` endpoint on `localhost:8188` before running. BFS and SteadyDancer nodes in particular may have different input names than assumed here.

2. **BFS LoRA filename** needs to be confirmed after download. The HuggingFace repo (`Alissonerdx/BFS-Best-Face-Swap-Video`) may have multiple version files.

3. **SDPose + SteadyDancer integration** — the exact wiring between pose output and motion transfer input needs validation. SDPose outputs keypoints that may need format conversion before SteadyDancer can consume them.

4. **Z-Image upscaler** — the exact upscale mechanism (img2img at higher resolution with low denoise vs. dedicated upscale node) depends on Z-Image's available nodes. The spec assumes img2img with denoise 0.5 but this should be confirmed.

5. **Aspect ratio preservation** — the upscaler workflows should use `ResizeImagesByLongerEdge` or equivalent to ensure consistent output dimensions regardless of input aspect ratio.
