# AI Inspire — NotebookLM-driven Video Summary Stage

**Date:** 2026-05-24
**Status:** Draft / design — one architectural decision needed
**Owner:** Artemis (planner) → nova (implementer)
**Related:** [2026-05-24 AI Inspire video→FB-post UI test](./2026-05-24-ai-inspire-video-to-fbpost-ui-test.md)

## Why

Today nova's `nova-aiinspire-topic-summary` / `nova-youtube-topic-summary` are *"NotebookLM-**style**"* — a prompt asking the LLM to behave like a NotebookLM analyst, operating on the **yt-dlp auto-caption transcript**. That's fragile (yt-dlp + PO-token issues, caption truncation, no visual grounding) and the output quality is bounded by transcript fidelity.

The user wants **real NotebookLM** (`notebooklm.google.com`) — upload the YouTube URL as a source, let NotebookLM ingest video + audio + captions, then pull a high-quality structured summary back into the pipeline.

## Available pieces

- **`google-notebooklm` skill** (`~/Dev/artemis-oracle/skills/google-notebooklm/SKILL.md`) — drives the NotebookLM web UI; account `Bjgdrx@gmail.com` via the encrypted Google vault.
- **`agent-browser-mcp`** — already in `~/.hermes/config.yaml` (`mcp_servers.agent_browser` → `agent-browser-mcp` binary, 120s connect timeout). nova/reel/sage agents can drive Chrome through it today.
- **Workflow engine** (`qone_corp-dashboard-refactor`) — supports producer (in-process, sync) and agent (async via wakeups) step types.

## The shape

NotebookLM ingestion is **asynchronous** (minutes per video) — too long for a synchronous in-process producer. The natural fit is an **agent step**: a new process slug whose handler drives the browser, waits for the audio/summary to finish, and returns the structured output. Hermes' agent-step model already handles long-running asynchronously via wakeup claims; we just lean on it.

**Proposed process:** `nova-notebooklm-video-summarize` (agent: nova or a new `sage` agent — see Fork below).

```
Input  : { videoUrl, language?, targetFormat? }
Output : {
  topics: [
    { title, hook, body, sourceTimestamp?, suggestedHashtags },
    ...
  ],
  meta: { videoTitle, durationSec, notebookId, audioOverviewUrl? }
}
```

Skill flow:
1. Open `notebooklm.google.com`, sign in via vault.
2. **New Notebook**, add the YouTube URL as a source.
3. Poll the source-ingestion status until ready (timeout 10 min).
4. Use the Notebook Guide / chat to ask the same questions the current `nova-aiinspire-topic-summary` asks (segment into N topics, return structured JSON).
5. Optionally generate an Audio Overview (kept as `meta.audioOverviewUrl` for later use).
6. Scrape the JSON response, validate against the output envelope, return.

## Pipeline integration — the one fork

The current AI Inspire flow has *two* transcript-dependent steps:
- **Format Decision** sub-workflow: `nova-yt-transcript-fetch` → `nova-topic-relatedness-checker` → `dedup-video-check` → format-decision gate.
- **Content Generation** sub-workflow: `nova-aiinspire-topic-summary` → factcheck → polish → infographic → post-review gate.

Where does the new stage fit?

| Option | Description | Trade-off |
|---|---|---|
| **A — Replace transcript-fetch only** | Keep both sub-workflows; swap `nova-yt-transcript-fetch` for `nova-notebooklm-video-summarize`, which returns BOTH a transcript-like blob AND the topic candidates. Topic-summary downstream then refines those. | Minimal pipeline change; NotebookLM's quality is preserved through both sub-workflows; still pays the LLM-summary cost in content-gen. |
| **B — New stage between intake and content-gen** | Insert `nova-notebooklm-video-summarize` as a new subworkflow that runs *before* content-gen, producing the canonical topic list. Content-gen's N1 topic-summary becomes a no-op pass-through (or is removed). Format-decision still uses the transcript blob from NotebookLM. | Cleanest architecturally; NotebookLM owns the summary contract; content-gen simplifies. Bigger pipeline restructure (one new workflow, two old steps demoted). |
| **C — Fully replace content-gen N1** | Skip transcript-fetch entirely; `nova-notebooklm-video-summarize` becomes content-gen's N1. Format-decision is reshaped to read the NotebookLM blob too, OR is bypassed for the manual-intake path. | Most invasive; format-decision and content-gen both have to take NotebookLM directly. Best quality, highest blast radius. |

## What I need from you

The fork above. **Recommendation: B** — it cleanly establishes NotebookLM as the canonical source of topics without ripping format-decision apart, and content-gen's later steps (factcheck/polish/infographic) stay intact. But A is the smallest step if we want fewer moving parts; C is the right end-state if we're committed to NotebookLM as the only summarizer.

## Open considerations (separate from the fork)

- **Auth & vault**: NotebookLM is Google OAuth via the encrypted vault — the skill handles this, but the first run needs the vault unlocked. The fact that agent-browser runs in the agent shell (not Claude's session) means the user's standard Google session cookies / vault password apply.
- **Latency budget**: 10 min per video means slow throughput. Acceptable for manual intake (~1 video/day); cron-driven daily intake should still work but won't be near-realtime.
- **Rate limits / Google account guardrails**: NotebookLM Free is limited per account. If we hit caps, fall back to the existing `nova-aiinspire-topic-summary` path (keep the old process as the backup, not deleted).
- **Output validation**: NotebookLM responses are scraped text — we need a strict zod parser before downstream steps consume them.

## Out of scope for this doc

- Implementing the skill itself (the `google-notebooklm` skill already exists; we'd extend or alias it).
- Audio Overview consumption (deferred; just capture the URL in meta).
- Multi-account routing if we exceed Free tier (revisit if we hit it).
