# Lesson Learned: AMD ComfyUI Native ROCm Setup

**Date**: 2026-03-22
**Context**: Beelink GTR9 Pro with Radeon 8060S (gfx1151 architecture)

## The Pattern

AMD's official AI Bundle for ComfyUI is fundamentally broken for AMD GPUs - it ships with CPU PyTorch and NVIDIA-only comfy_aimdo code that crashes on import. The clean solution is a fresh ComfyUI installation with native ROCm PyTorch.

## Key Insights

### 1. AMD AI Bundle Problems
- PyTorch is CPU version (2.4.1+cpu) not ROCm
- comfy_aimdo is NVIDIA-only but hard-imported everywhere
- Requires extensive patching to work

### 2. Native ROCm Solution
- PyTorch nightly from `https://rocm.nightlies.amd.com/v2/gfx1151/`
- Creates stub modules for comfy_aimdo to prevent import errors
- Uses bf16-unet + fp16-vae flags (not plain bf16 which causes errors)

### 3. Required Environment Variables
```
PYTORCH_ALLOC_CONF=garbage_collection_threshold:0.8,max_split_size_mb:512
HSA_OVERRIDE_GFX_VERSION=11.5.1
TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1
PYTORCH_TUNABLEOP_ENABLED=1
```

### 4. gfx1151 Specifics
- Very new architecture (Radeon 8060S)
- First image generation takes 5+ minutes (MIOpen kernel compilation)
- VAE Decode (Tiled) may be needed to avoid black images
- Disable browser hardware acceleration to save VRAM

## Tags

`amd` `rocm` `comfyui` `gfx1151` `radeon-8060s` `pytorch` `gpu-setup` `troubleshooting`
