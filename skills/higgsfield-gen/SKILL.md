---
name: higgsfield-gen
description: Generate images and videos on Higgsfield.ai using Nano Banana Pro, Soul, Kling, and other models. Use this skill when the user wants to generate AI images or videos on Higgsfield, mentions Nano Banana, Soul, Kling, Seedance, Cinema Studio, or any Higgsfield creation task. Also use when the user wants to automate Higgsfield login, check credits, or batch generate content.
---

# Higgsfield.ai Generation Skill

## Account
- **Vault service**: `higgsfield`
- **Login**: Google OAuth (ittipolbiz@gmail.com) with TOTP 2FA
- **Login script**: `MASTER_PASSWORD=xxx .venv/bin/python3 scripts/higgsfield-login.py`

## URLs

| Purpose | URL |
|---------|-----|
| Home | `https://higgsfield.ai/` |
| Create Image | `https://higgsfield.ai/create/image` |
| Create Video | `https://higgsfield.ai/create/video` |
| Soul (Fashion) | `https://higgsfield.ai/image/soul` |
| Gallery | `https://higgsfield.ai/gallery` |
| Pricing | `https://higgsfield.ai/pricing` |

## Image Models

| Model | Credits/Gen | Notes |
|-------|------------|-------|
| **Nano Banana Pro** | 2 | Flagship 4K, Gemini 3.0 reasoning engine, <10s |
| Nano Banana 2 | 1 | Previous gen, faster |
| Higgsfield Soul | 2 | Ultra-realistic fashion, 60+ aesthetic presets |
| Seedream 4.5 | 1 | Alternative model |
| GPT Image 1.5 | 2 | OpenAI-based |
| Z-Image, Kling O1, FLUX.2, Wan 2.2 | varies | Additional options |

## Generation Flow

1. Login first (use encrypted vault script)
2. Navigate to `/create/image`
3. Click **"Change"** button near model name → select **Nano Banana Pro**
4. Type prompt in text field
5. Select **aspect ratio**: 4:5, 9:16, 1:1, 4:3, 16:9, 2.35:1
6. Toggle **"Enhance"** to auto-improve prompt (recommended)
7. Click **Generate**

## Advanced Settings

| Setting | Default | Range |
|---------|---------|-------|
| Quality | High | High / Basic |
| Seed | Random | Any integer (for reproducibility) |
| Steps | 20 | Controls generation iterations |
| CFG | 6.0 | Controls prompt adherence |
| Strength | 0.85 | Controls transformation intensity |

## Credit System

- **Starter ($15/mo)**: 200 credits = ~100 Nano Banana Pro gens
- **Plus ($35/mo)**: 500 credits + unlimited select models
- **Ultra ($70/mo)**: 1200 credits + Cinema Studio
- Nano Banana Pro = **2 credits per generation**

## Notes
- The `/create/image` page may 404 if not logged in — always login first
- Promo modal appears on homepage — dismiss with `dialog button` click or Escape
- Browser must use `channel="chrome"` (real Chrome) to avoid Google automation detection
