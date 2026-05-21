---
name: kb
description: Shared-memory KB curator. Use this skill when the user invokes /kb scan, /kb search, /kb show, /kb retract, /kb status, /kb list, or /kb config — or when they ask to push curated knowledge into the shared memory store, or to search/retract chunks already in it. Wraps the jira-fetch-kb MCP server (kb_health, kb_search, kb_get, kb_ingest, kb_retract).
---

# /kb — Shared Memory KB curator

When the user runs `/kb <subcommand> [args]`, follow the procedure for that subcommand below.

**Preconditions every subcommand checks first:**

1. `~/.config/kb/config.json` exists. If missing, tell the user to copy `skills/kb/config.example.json` to `~/.config/kb/config.json` and stop.
2. The session has an MCP server matching `config.mcp_server_alias` (default `jira-fetch-kb`) with tools `kb_health`, `kb_search`, `kb_get`, `kb_ingest`, `kb_retract`. If not, tell the user to register the server in `~/.claude.json` (see `skills/kb/README.md`) and stop.

When this skill needs to call an MCP tool, the actual tool name in the session will be `mcp__<alias>__<tool>` (e.g. `mcp__jira-fetch-kb__kb_search`). Substitute the alias from the loaded config.

---

## `/kb scan [--since YYYY-MM-DD] [--scope mobileai|gothailand] [--source memory] [--dry-run]`

This is the curator pipeline. Memory source ONLY in this batch — if the user passes `--source jira`, tell them Jira ingestion isn't implemented yet and stop.

**Flags:**
- `--since YYYY-MM-DD` — defaults to the cursor in `state.json` for the chosen source. If neither is set, default to 7 days ago.
- `--scope mobileai|gothailand` — required. (Don't default; force the user to pick so they don't accidentally cross scopes.)
- `--source memory` — only valid value right now.
- `--dry-run` — run the pipeline but skip the final `kb_ingest` call.

**Procedure:**

1. **Read config** at `~/.config/kb/config.json`. Resolve the bearer token via `config.token_ref` (only `file:` URIs supported right now — read the path, take the first non-empty line).

2. **Read the since-cursor.** Run:
   ```bash
   python3 -c "
   import sys, json
   sys.path.insert(0, '<artemis-oracle-root>/skills/kb/scripts')
   import kb_state
   print(kb_state.get_cursor('memory') or '')
   "
   ```
   Use `--since` if provided; else the cursor; else `(today − 7d).isoformat()+'Z'`.

3. **Collect candidates** by running `skills/kb/scripts/kb_collect_memory.py` with the resolved arguments. The `--root` should be the artemis-oracle clone path on this dev's machine (default: `/home/bjgdr/oracle/artemis-oracle`).

   ```bash
   python3 <root>/skills/kb/scripts/kb_collect_memory.py \
     --root <root> \
     --globs "$(python3 -c 'import json; print(json.dumps(<from-config>.allowlist.memory_globs))')" \
     --scope <scope> \
     --scope-tags "$(python3 -c 'import json; print(json.dumps(<from-config>.allowlist.scope_tags))')" \
     --since <since-cursor>
   ```

   Parse the `{candidates:[…]}` JSON. If empty, tell the user "no candidates since <cursor>" and stop.

4. **Secret-scan** the candidates by piping them through `kb_secret_scan.py`:
   ```bash
   echo "$(python3 -c 'import json; print(json.dumps({"chunks": [{"idx":i,"body":c["body"]} for i,c in enumerate(candidates)]}))')" \
     | python3 <root>/skills/kb/scripts/kb_secret_scan.py --patterns <root>/skills/kb/secret-patterns.json
   ```
   Remove rejected indices from `candidates`. Remember the reject list for the run summary.

5. **LLM judge** — for each remaining candidate, ask yourself (Claude, in-session):

   > "Does this content benefit other devs working on <scope>?
   > Reply STRICT JSON: {benefits: boolean, confidence: number 0..1, reason: string ≤ 100 chars}"

   Use the content's title + body. Drop candidates where `benefits === false` or `confidence < config.classifier.threshold`. Attach the judge verdict to each survivor's `metadata.judge`.

6. **Approval gate.** Print a numbered table to the user:

   ```
   #  external_id                                 scope     judge.confidence  judge.reason (truncated)
   1  ψ/memory/learnings/feedback_iso-…           mobileai  0.92              ISO doc image hygiene…
   2  ψ/memory/retrospectives/2026-05/13/…        mobileai  0.81              QOne batch retro…
   ```

   Ask: "Approve which? `a` for all, comma-list (e.g. `1,3`), or `n` for none." Wait for the response.

7. **Upload** the approved subset. For each approved candidate, call the MCP `kb_ingest` tool with `{chunks: [<one chunk>]}`. (Single-chunk batches keep failures isolated — if one ingest fails, the others still land.) Attach `metadata.uploaded_by` from `config.owner_email` if set, and `metadata.judge` from step 5.

   If `--dry-run`, skip this step.

8. **Advance the cursor** to `max(mtime over all approved candidates)` ONLY IF at least one ingest succeeded. Call `kb_state.set_cursor("memory", <max-mtime-iso>)`.

9. **Record the run.** Call `kb_state.record_run({...})` with `{ts, source:"memory", scope, ingested:N, secret_rejected:M, classifier_rejected:K, user_skipped:L}`.

10. **Summary.** Print to the user: `N ingested · M secret-rejected · K classifier-rejected · L user-skipped`. Include the new cursor value if it advanced.

---

## `/kb search <query> [--scope …] [--source …] [--top-k 5]`

Resolve config → call the MCP `kb_search` tool with the literal args. Pretty-print the response as a numbered list: `# | similarity | scope | source | external_id | title — snippet`.

---

## `/kb show <id>`

Call MCP `kb_get` with `{id: <id>}`. Pretty-print the full chunk including metadata + `revoked_at`.

---

## `/kb retract <id> [--reason "…"]`

Ask the user to confirm (show the chunk via `kb_get` first), then call MCP `kb_retract` with `{id, reason}`. Print the resulting `revoked_at`.

---

## `/kb status`

1. Call MCP `kb_health`. Report `db_ok` and `embed_ok`.
2. Read `~/.config/kb/state.json` via `kb_state.load_state()` and print cursors + the most recent run summary.

---

## `/kb list [--mine] [--since …] [--source …] [--scope …]`

Local-only. Read `state.json` runs, filter by the optional args, print a chronological table.

---

## `/kb config [--show | --edit]`

`--show` (default): cat `~/.config/kb/config.json` redacting the `token_ref` line's resolved value.
`--edit`: tell the user where the file lives. Don't open editors directly from the skill.

---

## Important conventions

- **Server is dumb; this skill is the gatekeeper.** Never call MCP `kb_ingest` without running the secret-scan + judge + approval pipeline first. If you find yourself reaching for `kb_ingest` outside `/kb scan`, stop.
- **One chunk per `kb_ingest` call.** Single-chunk batches keep the audit trail clean and isolate failures.
- **Never write to the dev's working tree.** The skill only writes to `~/.config/kb/`.
- **Secret-scan rejects; it never redacts.** A redacted secret in the KB is still a leak; refusal is the right answer.
