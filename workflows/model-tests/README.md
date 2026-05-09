# ComfyUI Model Test Suite

Tests every downloaded model on `localhost:8188` with assets from `/mnt/c/MyDoc/biz/` (risa / motionvideo / fashion).

## Layout

```
workflows/model-tests/
├── saved/                 # API-format workflows (runnable via /prompt) + _ui.json graph versions
├── templates/             # Pulled from ComfyUI /api/userdata/workflows
├── results/               # queue_<ts>.json manifests (prompt_id per submission)
├── run.py                 # Submit + poll single workflow
├── queue_all.py           # Submit multiple workflows, return prompt_ids
├── api_to_ui.py           # Convert API-format prompt to UI/graph format
└── README.md              # This file
```

The 16 `*_ui.json` files and the 4 original stock templates were re-uploaded to ComfyUI's workflows folder in **graph format**, so they now render correctly on the canvas.

## Reference assets used

| Category | Path | Asset |
|---|---|---|
| Character (cha) | `/data/input/risa_face.jpeg`, `risa_body.jpeg`, `risa_avatar.jpeg` | Risa 19 y/o Thai-Japanese |
| Motion (cute/cool) | `/data/input/dance_cute1.mp4`, `dance_cool1.mp4` | TikTok dance clips |
| Fashion (face/edit) | `/data/input/fashion_face1.jpeg`, `fashion_face2.jpeg` | TikTok outfit/face refs |

## Results

| # | Workflow | Model | Kind | Status | Elapsed | Output |
|---|---|---|---|---|---|---|
| 01b | `01b_sdxl_baseline_risa.json` | SDXL 1.0 base | T2I | **ok** | 21 s | `test_01b_sdxl_baseline_risa_00001_.png` |
| 02 | `02_zimage_turbo_risa.json` | z_image_turbo_bf16 | T2I (4-step turbo) | **ok** | 125 s | `test_02_zimage_turbo_risa_00001_.png` |
| 06 | `06_wan22_t2v.json` | Wan 2.2 14B high-noise T2V | T2V | **ok** | 1085 s | `test_06_wan22_t2v_00002.mp4` |
| 07 | `07_wan22_i2v_risa.json` | Wan 2.2 14B high-noise I2V + risa_body | I2V | **ok** | 1958 s | `test_07_wan22_i2v_risa_00002.mp4` |
| 09 | `09_liveportrait_risa_cute.json` | LivePortrait + risa_face + dance_cute1 | face anim. | **ok** | ~1 min | `liveportrait_risa_00002.mp4` |
| 10 | `10_ltx23_t2v.json` | LTX Video 2.3 dev fp8 + distilled LoRA | T2V | queued | — | — |
| 11 | `11_animatediff_sdxl.json` | SDXL + animatediff_sdxl_fp16 | SDXL motion | **ok** | ~3 min | `animdiff_sdxl_00002.mp4` |
| 15 | `15_video_upscaler_ltx23.json` | LTX 2.3 spatial upscaler | Video upscale | **ok** | ~16 s | `upscale_video_00001.mp4` |
| 16 | `16_image_upscaler_zimage.json` | Z-Image turbo | Image upscale | **queued** | — | queued ok, needs re-run solo |
| 17 | `17_face_swap_bfs_ltx23.json` | LTX 2.3 + BFS V3 LoRA | Face swap | **blocked** | — | BFS custom node not installed |
| 18 | `18_motion_control_sdsteady_ltx23.json` | LTX 2.3 + SDPose + SteadyDancer | I2V motion | **blocked** | — | SteadyDancer not installed |
| 20 | `20_storydiffusion_sdxl.json` | SDXL + StoryDiffusion | Character image | **blocked** | — | No SDXL checkpoint |

## Re-running

```bash
cd workflows/model-tests

# single workflow, blocking
python3 run.py saved/04_wan21_t2v.json

# batch submit (returns prompt_ids), then monitor externally
python3 queue_all.py saved/04_wan21_t2v.json saved/05_wan21_i2v_risa.json
```

## Converting API → UI format

```bash
python3 api_to_ui.py path/to/api_workflow.json
# -> writes path/to/api_workflow_ui.json (graph format)
```

The converter pulls the live `/object_info` schema so widget slots/order match what the canvas expects.

## Known issues

- CLIPLoader dropdown on a slow / cached `/object_info` call may truncate to 8 items — full list includes `umt5xxl_fp16.safetensors` and types `wan`, `lumina2`, `hunyuan_image`, etc.

## Environment

- ComfyUI 0.18.1 (Docker: `comfyui-gfx1151-wsl2`)
- GPU: AMD Radeon 8060S, 120 GB VRAM, ROCm 7.12
- PyTorch 2.10.0+rocm7.12
