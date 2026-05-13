#!/usr/bin/env bash
# install-iso-doc-creator.sh
#
# Installs the `iso-doc-creator` skill into Claude Code CLI's skill directory
# on a target machine (designed for the `tools` EC2 in the ittipol AWS account).
#
# Usage:
#   bash install-iso-doc-creator.sh [VERSION] [INSTALL_DIR]
#
# Defaults:
#   VERSION      = v1.0
#   INSTALL_DIR  = ~/.claude/skills/iso-doc-creator
#
# Source of truth: GitHub Release on FiezDev/artemis-oracle named
# `iso-doc-creator-<VERSION>`, asset `iso-doc-creator-<VERSION>.tar.gz`.
#
# Exit codes:
#   0  install succeeded, verifications passed
#   1  download or extraction failed
#   2  validation failed (missing required files in bundle)
#   3  Python dependency check failed
#   4  agent-browser / mmdc not on PATH (warning, not fatal)

set -euo pipefail

VERSION="${1:-v1.0}"
INSTALL_DIR="${2:-$HOME/.claude/skills/iso-doc-creator}"
RELEASE_OWNER="FiezDev"
RELEASE_REPO="artemis-oracle"
ASSET="iso-doc-creator-${VERSION}.tar.gz"
RELEASE_URL="https://github.com/${RELEASE_OWNER}/${RELEASE_REPO}/releases/download/iso-doc-creator-${VERSION}/${ASSET}"

log() { printf '[iso-doc-creator] %s\n' "$*"; }
die() { printf '[iso-doc-creator] ERROR: %s\n' "$*" >&2; exit "${2:-1}"; }

log "Target version: ${VERSION}"
log "Install dir:    ${INSTALL_DIR}"
log "Release URL:    ${RELEASE_URL}"

# ─── 1. Working directory + cleanup trap ──────────────────────────────
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

# ─── 2. Back up any existing install ──────────────────────────────────
mkdir -p "$(dirname "$INSTALL_DIR")"
if [[ -d "$INSTALL_DIR" ]]; then
    BACKUP="${INSTALL_DIR}.backup.$(date +%s)"
    log "Existing install found — backing up to ${BACKUP}"
    mv "$INSTALL_DIR" "$BACKUP"
fi

# ─── 3. Download tarball ──────────────────────────────────────────────
log "Downloading ${ASSET}…"
if ! curl -fSL "$RELEASE_URL" -o "$TMPDIR/${ASSET}"; then
    die "curl failed for ${RELEASE_URL}"
fi

# ─── 4. Validate tarball structure ────────────────────────────────────
log "Validating tarball…"
if ! tar -tzf "$TMPDIR/${ASSET}" >/dev/null 2>&1; then
    die "tarball is not a valid gzipped tar"
fi
for required in SKILL.md scripts/run.py scripts/config.py; do
    if ! tar -tzf "$TMPDIR/${ASSET}" | grep -qE "(^|/)${required}$"; then
        die "required file missing from bundle: ${required}" 2
    fi
done

# ─── 5. Extract + locate root ─────────────────────────────────────────
mkdir -p "$TMPDIR/extract"
tar -xzf "$TMPDIR/${ASSET}" -C "$TMPDIR/extract"

# Tarball may have a wrapper directory or be flat — find the dir with SKILL.md
EXTRACT_ROOT="$(find "$TMPDIR/extract" -maxdepth 3 -name SKILL.md -printf '%h\n' | head -n 1)"
if [[ -z "$EXTRACT_ROOT" ]]; then
    die "SKILL.md not found in extracted bundle" 2
fi
log "Extracted root: ${EXTRACT_ROOT}"

# ─── 6. Install ───────────────────────────────────────────────────────
log "Installing to ${INSTALL_DIR}…"
mkdir -p "$INSTALL_DIR"
cp -R "$EXTRACT_ROOT"/. "$INSTALL_DIR/"

# Make scripts executable (harmless if they aren't shebanged)
find "$INSTALL_DIR/scripts" -maxdepth 1 -name '*.py' -exec chmod +x {} + 2>/dev/null || true

# ─── 7. Python dependency check ───────────────────────────────────────
log "Checking Python deps…"
if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found on PATH" 3
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "  python3 = ${PY_VER}"

if ! python3 -c 'import docx' 2>/dev/null; then
    log "  WARNING: python-docx not importable. Install with:"
    log "           pip3 install --user python-docx"
fi

# ─── 8. System binary checks (non-fatal) ──────────────────────────────
WARNS=0
for bin in agent-browser mmdc; do
    if command -v "$bin" >/dev/null 2>&1; then
        log "  ${bin} = $(command -v "$bin")"
    else
        log "  WARNING: ${bin} not on PATH"
        WARNS=$((WARNS + 1))
    fi
done

# Thai font check (Ubuntu/Debian)
if command -v fc-list >/dev/null 2>&1; then
    if fc-list | grep -qi 'thai'; then
        log "  Thai fonts: present"
    else
        log "  WARNING: no Thai fonts detected (TH screenshots will tofu)"
        WARNS=$((WARNS + 1))
    fi
fi

# ─── 9. Verify skill is discoverable by Claude Code CLI ───────────────
log "Verifying installation…"
if [[ -f "$INSTALL_DIR/SKILL.md" ]]; then
    log "  SKILL.md present at ${INSTALL_DIR}/SKILL.md"
else
    die "SKILL.md missing after install" 2
fi

# ─── 10. Summary ──────────────────────────────────────────────────────
log "Install complete."
log "  Version:  ${VERSION}"
log "  Location: ${INSTALL_DIR}"
if [[ $WARNS -gt 0 ]]; then
    log "  ${WARNS} warning(s) above — review before first run."
    exit 4
fi
exit 0
