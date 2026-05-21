# /kb — Shared Memory KB curator

Push curated knowledge to and query the team's shared memory store from inside any Claude Code session.

## One-time setup (per developer workstation)

### 1. Install the skill into Claude Code

````bash
# Adjust target dir if your Claude Code installation uses a different skills path.
mkdir -p ~/.claude/skills
ln -s /home/bjgdr/oracle/artemis-oracle/skills/kb ~/.claude/skills/kb
````

(Alternative: this repo may already be auto-loaded by `oracle-skills` — check with `oracle-skills list -g | grep kb`. If it appears, skip the symlink.)

### 2. Register the MCP server in Claude Code

Add to `~/.claude.json`:

````json
{
  "mcpServers": {
    "jira-fetch-kb": {
      "type": "http",
      "url": "http://43.208.150.191:6501/mcp",
      "headers": { "Authorization": "Bearer <KB_API_KEY>" }
    }
  }
}
````

Get `KB_API_KEY` from the team's secret store. Restart Claude Code so the MCP server is loaded.

### 3. Create the per-dev config

````bash
mkdir -p ~/.config/kb
cp /home/bjgdr/oracle/artemis-oracle/skills/kb/config.example.json ~/.config/kb/config.json
# Optional: edit the allowlist + thresholds for your workflow.
````

### 4. Verify

In a Claude Code session, invoke `/kb status`. You should see the MCP server reachable and the local config + state paths reported.

## Subcommands

| Command | Purpose |
|---|---|
| `/kb scan [--since YYYY-MM-DD] [--scope mobileai\|gothailand] [--dry-run]` | The curator pipeline. Collects memory files modified since the cursor → heuristic gate → secret-scan reject → LLM judge "benefits other devs?" → user approval → MCP `kb_ingest`. |
| `/kb search <query> [--scope …] [--top-k 5]` | Wraps MCP `kb_search`. Prints results table. |
| `/kb show <id>` | Wraps MCP `kb_get`. Prints full chunk. |
| `/kb retract <id> [--reason …]` | Wraps MCP `kb_retract`. Confirms before calling. |
| `/kb status` | Local state cursors + MCP `kb_health`. |
| `/kb list [--mine] [--since …] [--source …] [--scope …]` | Local report from `~/.config/kb/state.json` of recent uploads. |
| `/kb config [--show \| --edit]` | Inspect or open `~/.config/kb/config.json`. |

## Files this skill writes

- `~/.config/kb/state.json` — cursors per source + last-run summary.

That's it. The skill never writes to your repo working tree.
