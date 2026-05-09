---
name: google-flow-gen
description: Generate and edit AI videos and images using Google Flow (labs.google/flow). Use this skill when the user wants to use Google Flow, create AI videos with Veo, animate images, extend videos, control camera angles, insert/remove objects in videos, or build scenes with Scenebuilder. Also trigger for motion control, video composition, and professional AI video production.
---

# Google Flow Generation Skill

## Account
- **Vault service**: `google`
- **Email**: Bjgdrx@gmail.com
- **Login**: Direct Google sign-in
- **URL**: `https://labs.google/flow`

## What is Google Flow?

Google Flow is an **AI creative studio** built by Google Labs. It lets you create, refine, and compose videos and images using Google's **Veo** model (currently Veo 3.1). Think of it as Google's answer to Runway, Pika, and Sora — a professional-grade platform for AI visual storytelling.

## Generation Capabilities

| Capability | Description |
|-----------|-------------|
| **Text to Video** | Generate video from text prompts |
| **Frames to Video** | Turn image frames into video |
| **Ingredients to Video** | Tag elements to guide generation |
| **Animate an Image** | Bring static images to life |
| **Insert Object** | Add objects into existing scenes |
| **Remove Object** | Take objects out of scenes |
| **Extend a Video** | Lengthen existing video clips |
| **Control Camera Angle** | Direct camera movement |
| **Change View** | Shift perspective |
| **Scenebuilder** | Compose scenes from components |
| **Image Upscaling** | 2K / 1080p / 4K depending on plan |

## Motion Control

Flow's camera control features:
- **Camera angle direction**: Specify pan, tilt, zoom, dolly, tracking shots
- **View changes**: Shift perspective between shots
- **Scene extension**: Continue existing video with consistent motion
- **Object insertion with motion**: Add moving elements into scenes

## Steps to Generate

1. Login to Google (use encrypted vault)
2. Navigate to `https://labs.google/flow`
3. Create or open a project/collection
4. Choose generation type (Text to Video, Frames to Video, etc.)
5. Enter prompt describing the video/scene
6. Use the workspace to compose and refine
7. Export when done

## Pricing

| Tier | Price | Credits | Key Features |
|------|-------|---------|--------------|
| **Free** | $0 | 100 initial + 50 daily | Veo 3.1, basic generation, 2K upscale |
| **Google AI Pro** | $19.99/mo | 1,000 monthly | 1080p upscale, higher limits, Gemini 3.1 Pro |
| **Google AI Ultra** | $124.99/mo | 25,000 monthly | 4K upscale, Deep Think, YouTube Premium |

## Available in 149+ countries

## Notes
- Flow uses Veo 3.1 as the underlying model
- The workspace is a drag-and-drop creative canvas
- Assets can be organized into Collections
- Free tier gives enough credits for experimentation
- Sign-in requires Google account — TOTP must be in vault for automation
