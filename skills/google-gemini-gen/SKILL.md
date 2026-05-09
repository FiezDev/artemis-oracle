---
name: google-gemini-gen
description: Generate images using Google Gemini (gemini.google.com). Use this skill when the user wants to generate AI images with Gemini/Imagen, edit images with Gemini, create art, or use Google's image generation. Also trigger when the user mentions Gemini image gen, Imagen, Google AI art, or wants to automate Gemini interactions.
---

# Google Gemini Image Generation Skill

## Account
- **Vault service**: `google`
- **Email**: Bjgdrx@gmail.com
- **Login**: Direct Google sign-in (may require TOTP 2FA)
- **URL**: `https://gemini.google.com/`

## How Image Generation Works

No special mode or interface needed. Just describe the image in natural language in the chat prompt. Gemini detects image requests automatically and uses **Imagen 3** to generate.

## Steps

1. Login to Google (use encrypted vault)
2. Navigate to `https://gemini.google.com/`
3. Type your image prompt directly in the chat box
4. Gemini returns generated images inline in the conversation
5. Click images to view larger or download

## Prompt Tips

- **Be specific about style**: "watercolor painting", "photorealistic", "anime", "oil painting"
- **Specify composition**: lighting, camera angle, color palette, mood
- **Include details**: subject appearance, clothing, pose, background
- **Iterate**: "make it more colorful", "change background to forest", "add more detail"

### Example Prompts
- "Generate a photorealistic portrait of a woman with curly hair in a coffee shop"
- "Create a futuristic city at night with neon lights and flying cars"
- "Draw a cartoon-style dog playing piano in watercolor style"
- "Generate an image of a Thai street food market at golden hour, cinematic lighting"

## Capabilities

| Feature | Details |
|---------|---------|
| Text to Image | Describe what you want in natural language |
| Image Editing | Upload image + describe changes |
| Style Transfer | "Make this photo look like a Van Gogh painting" |
| People | Can generate generic people (not specific real individuals) |
| SynthID | All images have invisible AI watermark |

## Limitations

- Cannot generate real people (specific individuals)
- Cannot generate violent, explicit, or harmful content
- May refuse copyrighted characters/trademarks
- Free tier: limited daily generations
- Gemini Advanced: higher limits, newer Imagen models

## Pricing

| Tier | Price | Image Gen |
|------|-------|-----------|
| Free | $0 | Limited daily |
| Gemini Advanced | $19.99/mo | Higher limits, Imagen 3+ |

## Notes
- Google sign-in may require 2FA — TOTP secret must be in vault
- Browser must use `channel="chrome"` to avoid Google automation detection
- Gemini works as a chat — all interactions are conversational
