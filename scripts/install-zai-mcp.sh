#!/usr/bin/env bash
# Install the four Z.ai MCP servers into clother-zai / Claude Code at user scope.
#
#   scripts/install-zai-mcp.sh
#
# Reads the API key from:
#   1. $ZAI_API_KEY env var, or
#   2. scripts/auth-vault.py get zai apiKey  (if MASTER_PASSWORD is set)
#
# Servers installed:
#   - zai-web-search  (HTTP)  tool: webSearchPrime
#   - zai-web-reader  (HTTP)  tool: webReader
#   - zai-zread       (HTTP)  tools: search_doc, get_repo_structure, read_file
#   - zai-vision      (stdio) 8 vision tools via @z_ai/mcp-server
#
# Idempotent: removes an existing registration before re-adding.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${CLOTHER_ZAI_BIN:-clother-zai}"

if ! command -v "$BIN" >/dev/null 2>&1; then
  echo "ERROR: $BIN not found on PATH" >&2
  exit 1
fi

# Resolve API key: env first, vault fallback.
KEY="${ZAI_API_KEY:-}"
if [[ -z "$KEY" ]]; then
  if [[ -f "$REPO_ROOT/.venv/bin/python3" ]] && [[ -n "${MASTER_PASSWORD:-}" ]]; then
    if KEY_FROM_VAULT="$("$REPO_ROOT/.venv/bin/python3" "$REPO_ROOT/scripts/auth-vault.py" get zai apiKey 2>/dev/null)"; then
      KEY="$KEY_FROM_VAULT"
      echo "Using ZAI_API_KEY from vault service 'zai'."
    fi
  fi
fi
if [[ -z "$KEY" ]]; then
  echo "ERROR: ZAI_API_KEY not set. Either 'export ZAI_API_KEY=...' or add it to the vault:" >&2
  echo "  MASTER_PASSWORD=... $REPO_ROOT/.venv/bin/python3 $REPO_ROOT/scripts/auth-vault.py set zai" >&2
  echo "  (use field name 'apiKey' when prompted)" >&2
  exit 2
fi

add_http() {
  local name="$1" url="$2"
  echo "→ $name ($url)"
  "$BIN" mcp remove -s user "$name" >/dev/null 2>&1 || true
  "$BIN" mcp add -s user -t http "$name" "$url" --header "Authorization: Bearer $KEY"
}

add_stdio_npx() {
  local name="$1"; shift
  local package="$1"; shift
  echo "→ $name (stdio: npx $package)"
  "$BIN" mcp remove -s user "$name" >/dev/null 2>&1 || true
  # Name must come BEFORE -e flags so the variadic env list doesn't eat the name.
  "$BIN" mcp add -s user "$name" \
    -e "Z_AI_API_KEY=$KEY" \
    -e "Z_AI_MODE=ZAI" \
    -- npx -y "$package"
}

add_http  zai-web-search  https://api.z.ai/api/mcp/web_search_prime/mcp
add_http  zai-web-reader  https://api.z.ai/api/mcp/web_reader/mcp
add_http  zai-zread       https://api.z.ai/api/mcp/zread/mcp
add_stdio_npx zai-vision  @z_ai/mcp-server

echo
echo "Done. Verify:"
echo "  $BIN mcp list"
