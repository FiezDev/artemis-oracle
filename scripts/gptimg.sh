#!/usr/bin/env bash
# gptimg — generate an image via Codex CLI's built-in image_generation tool
#
# Codex CLI uses the user's ChatGPT auth (no OPENAI_API_KEY required) and
# its agent decides to call image_generation when the prompt asks for one.
# We wrap that into a deterministic CLI: pass a prompt + a target file path,
# get the image saved at exactly that path or exit non-zero.
#
# Usage:
#   gptimg --prompt "<text>" --output /abs/path/img.png [--size 1024x1024]
#   gptimg --prompt-file post.txt --output /abs/path/img.png [--size 1024x1024]
#
# Flags:
#   --prompt <text>      Image description (or use --prompt-file)
#   --prompt-file <path> Read prompt text from file
#   --output <path>      Destination PNG path (parent dir created if needed)
#   --size <WxH>         Target dimensions (default 1024x1024). Codex generates
#                        roughly square images then we resize via PIL.
#   --quiet              Suppress codex chatter; print only the saved path
#
# Exit codes:
#   0  success — image saved to --output
#   1  bad args
#   2  codex exec failed
#   3  no image landed in ~/.codex/generated_images during this run

set -euo pipefail

PROMPT=""
PROMPT_FILE=""
OUTPUT=""
SIZE="1024x1024"
QUIET=0
REF_IMAGES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--prompt)      PROMPT="$2"; shift 2 ;;
    --prompt-file)    PROMPT_FILE="$2"; shift 2 ;;
    -o|--output)      OUTPUT="$2"; shift 2 ;;
    -s|--size)        SIZE="$2"; shift 2 ;;
    --image|--ref-image|--reference-image)
                      REF_IMAGES+=("$2"); shift 2 ;;
    --quiet|-q)       QUIET=1; shift ;;
    -h|--help)        sed -n '2,/^$/p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -n "$PROMPT_FILE" ]]; then
  [[ -f "$PROMPT_FILE" ]] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 1; }
  PROMPT="$(cat "$PROMPT_FILE")"
fi
[[ -n "$PROMPT" ]] || { echo "missing --prompt or --prompt-file" >&2; exit 1; }
[[ -n "$OUTPUT" ]] || { echo "missing --output" >&2; exit 1; }
for IMG in "${REF_IMAGES[@]}"; do
  [[ -f "$IMG" ]] || { echo "reference image not found: $IMG" >&2; exit 1; }
done

mkdir -p "$(dirname "$OUTPUT")"

# Snapshot existing images so we can identify the new one even if codex
# doesn't echo the path in a parseable form.
TMP_BEFORE="$(mktemp)"
find "$HOME/.codex/generated_images/" -name 'ig_*.png' 2>/dev/null > "$TMP_BEFORE" || true

# Templated prompt: instruct the agent to generate, save to OUTPUT, resize
# to SIZE, and echo the path on a deterministic line we can grep for.
read -r -d '' INSTRUCTIONS <<EOF || true
Generate an image based on this description:

$PROMPT

Use GPT Image 2 for the image generation. Use high thinking/reasoning before calling image generation:
first internally plan the composition against the attached reference image(s), then generate.

After generation, save the PNG to exactly this absolute path:
  $OUTPUT

If the image is not exactly ${SIZE} pixels, resize it to ${SIZE} using PIL
(python3 -c "from PIL import Image; im=Image.open('$OUTPUT'); im.resize((W,H), Image.Resampling.LANCZOS).save('$OUTPUT')").

When done, print one line on its own:
GPTIMG_OUTPUT=$OUTPUT

Do not ask follow-up questions; just execute and report the output path.
EOF

LOG="$(mktemp)"
CODEX_CMD=(codex exec --skip-git-repo-check -c model_reasoning_effort='"xhigh"')
for IMG in "${REF_IMAGES[@]}"; do
  CODEX_CMD+=(--image "$IMG")
done
if [[ "$QUIET" -eq 1 ]]; then
  printf '%s' "$INSTRUCTIONS" | "${CODEX_CMD[@]}" - >"$LOG" 2>&1 || {
    echo "codex exec failed (see $LOG)" >&2
    tail -80 "$LOG" >&2 || true
    exit 2
  }
else
  printf '%s' "$INSTRUCTIONS" | "${CODEX_CMD[@]}" - 2>&1 | tee "$LOG"
fi

# 1) Did codex's agent successfully save the file at the requested path?
if [[ -f "$OUTPUT" ]] && file "$OUTPUT" 2>/dev/null | grep -qi "PNG image"; then
  echo "$OUTPUT"
  exit 0
fi

# 2) Fallback: find a freshly generated image in ~/.codex/generated_images
#    that did not exist before this run and copy it to OUTPUT.
TMP_AFTER="$(mktemp)"
find "$HOME/.codex/generated_images/" -name 'ig_*.png' 2>/dev/null > "$TMP_AFTER" || true
NEW_IMG="$(comm -13 <(sort "$TMP_BEFORE") <(sort "$TMP_AFTER") | head -1)"
rm -f "$TMP_BEFORE" "$TMP_AFTER"

if [[ -n "$NEW_IMG" && -f "$NEW_IMG" ]]; then
  install -D -m 0644 "$NEW_IMG" "$OUTPUT"
  # Resize to requested size if PIL is available
  if python3 -c "import PIL" 2>/dev/null; then
    W="${SIZE%x*}"; H="${SIZE#*x}"
    python3 -c "from PIL import Image; im=Image.open('$OUTPUT'); im=im.resize(($W,$H), Image.Resampling.LANCZOS); im.save('$OUTPUT')"
  fi
  echo "$OUTPUT"
  exit 0
fi

echo "no image landed in ~/.codex/generated_images during this run; codex log: $LOG" >&2
exit 3
