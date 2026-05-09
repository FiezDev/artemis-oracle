# Handoff — `news-ai` Codex Session

**Source session**: `019df2fe-7d7d-7c52-91cd-1226a0567301` ("news-ai")
**Span**: 2026-05-04 12:38 UTC → 2026-05-06 13:26 UTC (48 turns, ~2 days)
**Where**: `/home/bjgdr/.codex/sessions/2026/05/04/rollout-2026-05-04T19-37-37-019df2fe-...jsonl` (131 MB, 7,735 lines)
**Last state**: Aborted mid-run (`turn_aborted` 13:23 UTC). Multiple "continue" prompts after; no further assistant work landed. Image regen for shortform v2 set is blocked on GPT Image 2 quota reset.

---

## What the session was for

Two YouTube videos → news posts on the AI Inspire FB page, driven through the QOne Dashboard + TaskNet pipeline, scheduled via FB browser automation.

| Form | Video | Output dir |
|---|---|---|
| **Longform** | `XJUpuOBpT-4` | `output/facebook/qone-redo-2026-05-06/` |
| **Shortform** | `7r_WJ9xpne0` | `output/facebook/qone-redo-short-7rWJ9xpne0/` |

---

## Done ✅

### Longform (XJUpuOBpT-4) — COMPLETE
- 6 posts scheduled in Meta on 2026-05-06, 12:58 → 22:58 +07 (2-hour cadence). All `rc:0`, screenshots captured.
- Subjects: DeepSeek V4 longform, Recursive AI agents, Vista 4D, Claude creative tools, Talkie 1930, ARA.
- Schedule receipts: `output/facebook/qone-redo-2026-05-06/browser-schedule-results.jsonl`.

### Shortform (7r_WJ9xpne0) — PARTIAL
- **Topic inventory rebuilt from full transcript** by spawned subagent `019dfcf2-941b-...` (covered 24 raw topics; 20 selected, 7 already-scheduled excluded).
  - `/tmp/qone-redo/redo-short-7rWJ9xpne0/artemis-topic-inventory.md`
  - `/tmp/qone-redo/redo-short-7rWJ9xpne0/artemis-shortform-queue.json`  (20 items, validated)
  - `/tmp/qone-redo/redo-short-7rWJ9xpne0/artemis-qa.md`
  - `/tmp/qone-redo/redo-short-7rWJ9xpne0/transcript-clean.txt`
- **20 captions + 20 prompts** written: `output/facebook/qone-redo-short-7rWJ9xpne0/{captions,prompts}/`.
- **7 images approved & locked** in `images/pass/` (reference style = `18-talkie-13b-vintage-model.png`).
- **11 v1 images** sit in `images/` — these are the rejected ones the user wants redone.
- **First batch of 5 + ARA shortform images already scheduled** in Meta earlier (the "5 posts scheduled and verified" plan step from 08:17 UTC).
- **Telegram runbook** drafted: `output/facebook/qone-redo-short-7rWJ9xpne0/artemis-telegram-runbook.md` — describes the Artemis-via-Telegram flow for future repeats.

### Engine / pipeline patches landed (committed)
| Commit | Title |
|---|---|
| `780c29c` | add facebook browser posting helper |
| `c9561bb` | add qone gpt image redo prompts |
| `ce02f67` | fix ai inspire circular logo masking (rectangle around brain icon → circular mask, applied to all queued posts) |

Other in-session changes (verified via plan trail, not all checked into commits):
- QOne handoff/prompt safeguards patched (so a too-compressed shortform can't slip through again).
- Facebook browser success detection patched.
- QOne dashboard run outputs updated for the longform batch.

---

## Blocked / In-Flight 🟡

### GPT Image 2 v2 redo of 10 shortform images — BLOCKED on quota
User rejected 9 v1 shortform images + 1 (Kai humanoid, wrong subject — showed white robot, topic is human-skin tactile). Files to redo:

```
images/01-omnishot-cut-detects-video-edits-automatically.png
images/02-alibaba-happy-horse-underperforms-in-real-tests.png
images/04-inclusion-ai-link-2-6-flash-efficient-open-model.png
images/05-zanime-anime-image-generation-model.png
images/08-meta-tuna-2-image-generator-editor.png
images/09-anyrecon-reconstructs-3d-from-sparse-photos.png
images/11-kinetics-ai-kai-humanoid-robot.png   (subject correction: tactile humanoid skin)
images/13-noix-and-tfbot-realistic-android-heads.png
images/14-sensenova-u1-unified-multimodal-model.png
images/15-nvidia-neotron-3-nano-omni.png
images/17-moonlink-3d-world-building-agent.png
```

Backups already taken under `images/rejected-backup-2026050{6}-194408 / -200629 / -201157/`.
Three v2 prompts written so far in `redo-prompts-v2/` (Omnishot, Happy Horse, Link 2.6).

**Why blocked**: GPT Image 2 quota for the Codex CLI session is exhausted; child session reports "try again at 11:27 PM". User explicitly said "no fallback image gen — only GPT Image 2".

### Runner fix — partially landed, NOT committed
`scripts/gptimg.sh` (or its callers) was passing the reference image as a *path inside the prompt text* — i.e. text-conditioned only, not a real visual reference. Codex discovered `codex exec` has a real `--image` flag and patched the wrapper:

- Now invokes `codex exec --image template.jpg --image images/pass/18-talkie-13b-vintage-model.png …`
- Forces `model_reasoning_effort="xhigh"` on the child image session
- Sends prompt via **stdin** (the `--image` mode rejects prompt-as-arg with "no prompt provided")
- Verified end-to-end: child session loads the attached image and reports `1254 x 1254` at `reasoning effort: xhigh`

**Still pending in this branch of work**:
- Patch the retry loop. Current behaviour: waits 30 min per usage-limit hit. Needed: parse the reported retry time ("try again at 11:27 PM") and sleep until that timestamp, then resume v2 redo of the 10 images using attached references (template.jpg + Talkie pass image) at xhigh.
- Re-run v2 redo of all 10 rejected images once quota resets.
- After v2 images approved → schedule the missing shortform topics (add-only, exclude the 7 already in Meta).
- Update QOne dashboard run outputs for the shortform batch (content/image/schedule nodes).
- Complete the TaskNet task with links to inventory, queue, image manifest, schedule results, QOne task IDs.
- Commit the runner + retry-loop patches.

---

## Hard rules accumulated this session

- **Each topic = its own post = its own pic.** No multi-topic combo posts.
- **Longform captions: no local resource paths.** Source URL + timestamp only.
- **AI Inspire template (`template.jpg`)** is the fixed base:
  - bottom bar / brand text / brain logo: untouched
  - circular mask around brain logo (committed in `ce02f67`)
  - left = infographic; right ≈ 40% topic visual; soft blend, not a hard mask
- **Image generator: GPT Image 2 only**, with attached visual references (template + Talkie pass image) and `xhigh` reasoning. No fallbacks.
- **Add-only scheduling.** Already-in-Meta topics must be excluded:
  - Recursive multi-agent systems · Vista 4D · ARA · Claude for Creative Work · Talkie 13B · DeepSeek V4 longform
- **Approved style anchor**: `images/pass/18-talkie-13b-vintage-model.png`. Match its density, structure, navy/gold palette, no text clipping.

---

## Next-session pickup checklist

1. Wait until **GPT Image 2** quota resets (session said ~23:27 — confirm against current time).
2. Apply the retry-loop patch (sleep-until-reported-time) and commit it together with the `gptimg.sh` `--image`/stdin/xhigh fix.
3. Re-run v2 redo for the 11 rejected images using the attached-reference workflow.
4. Inspect output against `images/pass/18-talkie-13b-vintage-model.png`. Move accepted ones into `images/pass/`.
5. Build the add-only schedule queue for the missing topics; respect the exclusion list above.
6. Schedule via `scripts/facebook-post.py` browser automation; capture `*-results.jsonl`.
7. Update QOne dashboard task outputs (content/image/schedule nodes) and complete TaskNet task.
8. Final commit batch.

---

*Generated from codex session JSONL on 2026-05-06 by Artemis (Claude Opus 4.7 1M).*
