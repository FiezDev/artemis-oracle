# strp - Startup script for folder selection and oracle launching
# Updated: 2026-05-12
#
# v3 (2026-05-12) — Added:
#   - JSONL run history at ~/.strp_history.jsonl (one line per finalized action).
#   - "0) Recent sessions" sub-menu showing the top-10 most-recently-updated
#     CLI sessions (Claude / Codex / Gemini), interleaved by file mtime.
#     Selecting a row cd's to the session's original folder and resumes the
#     matching CLI, with a fallback to the existing bypass-flagged launch on
#     any failure. The 0) entry is hidden when no sessions exist.
#
# Dependencies: jq is required for the v3 features. Without jq, the menu still
# works for v2 paths but the recent-sessions list is hidden and history is not
# logged.

# ============================================================================
# Private helpers (prefixed _strp_)
# ============================================================================

# _strp_log <action> <choice_label> <runner> <folder> [session_id] [session_name]
# Appends one JSON line to ~/.strp_history.jsonl. Silent no-op if jq missing.
_strp_log () {
	command -v jq >/dev/null 2>&1 || return 0
	local action="$1" choice_label="$2" runner="$3" folder="$4"
	local session_id="${5:-}" session_name="${6:-}"
	local ts
	ts="$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)"
	local log_file="$HOME/.strp_history.jsonl"
	jq -nc \
		--arg ts "$ts" \
		--arg choice_label "$choice_label" \
		--arg runner "$runner" \
		--arg folder "$folder" \
		--arg action "$action" \
		--arg session_id "$session_id" \
		--arg session_name "$session_name" \
		'{ts:$ts, choice_label:$choice_label, runner:$runner, folder:$folder, action:$action}
		 + (if $session_id   != "" then {session_id:   $session_id}   else {} end)
		 + (if $session_name != "" then {session_name: $session_name} else {} end)' \
		>> "$log_file" 2>/dev/null
}

# =============== zai-powered session naming (cached + async) ================
#
# When a session lacks an auto-generated title (Claude's ai-title row or
# Codex's thread_name in session_index), we ask zai (clother-zai → GLM-5.1)
# to read the last 20 turns and produce a 4-7 word session name. Generation
# is async (background, ~27s per call) and cached persistently — the menu
# never blocks. First strp run with a new untitled session shows the
# heuristic fallback (first AI response / first user message); the zai name
# appears on the next run.

_strp_zai_cache_file () { echo "$HOME/.strp_session_names.jsonl"; }

_strp_zai_cache_get () {
	local sid="$1"
	[[ -z "$sid" ]] && return 0
	local cache; cache="$(_strp_zai_cache_file)"
	[[ -f "$cache" ]] || return 0
	jq -r --arg sid "$sid" 'select(.session_id == $sid) | .name' "$cache" 2>/dev/null | tail -n 1
}

_strp_zai_cache_put () {
	local sid="$1" name="$2" cli="$3" file="$4"
	[[ -z "$sid" || -z "$name" ]] && return 0
	command -v jq >/dev/null 2>&1 || return 0
	local cache; cache="$(_strp_zai_cache_file)"
	local ts; ts="$(date -Iseconds 2>/dev/null || date)"
	jq -nc \
		--arg sid "$sid" --arg name "$name" --arg cli "$cli" --arg file "$file" --arg ts "$ts" \
		'{session_id:$sid, name:$name, cli:$cli, file:$file, generated_at:$ts}' \
		>> "$cache" 2>/dev/null
}

# Extract the last 20 substantive user/assistant turns as plain text.
# Each turn is truncated to 300 chars; boilerplate <env>/<permissions> blocks
# are stripped to keep the prompt focused on real activity.
_strp_zai_extract_messages () {
	local file="$1" cli="$2"
	case "$cli" in
		claude)
			jq -r '
				if .type == "user" then
					((if (.message.content | type) == "string" then .message.content
					  else (.message.content // []
					        | map(select(.type=="text" or .type=="input_text") | (.text // .content // ""))
					        | join(" "))
					  end) | gsub("\\s+"; " ")) as $t
					| if ($t | length) > 5 then "USER: " + $t else empty end
				elif .type == "assistant" then
					((.message.content // []
					  | map(select(.type=="text") | .text)
					  | join(" ")) | gsub("\\s+"; " ")) as $t
					| if ($t | length) > 5 then "ASSISTANT: " + $t else empty end
				else empty end' "$file" 2>/dev/null \
				| awk '!/^USER: (<|\[Request)/' \
				| tail -n 20 \
				| awk '{print substr($0, 1, 300)}'
			;;
		codex)
			jq -r '
				if .type=="response_item" and .payload.role=="user" then
					(((.payload.content // []) | map(select(.type=="input_text") | .text) | join(" ")) | gsub("\\s+"; " ")) as $t
					| if ($t | length) > 5 then "USER: " + $t else empty end
				elif .type=="response_item" and .payload.role=="assistant" then
					(((.payload.content // []) | map(select(.type=="output_text") | .text) | join(" ")) | gsub("\\s+"; " ")) as $t
					| if ($t | length) > 5 then "ASSISTANT: " + $t else empty end
				else empty end' "$file" 2>/dev/null \
				| awk '!/^USER: </' \
				| tail -n 20 \
				| awk '{print substr($0, 1, 300)}'
			;;
	esac
}

# Synchronous: call zai with last-20 transcript, return clean name, cache it.
# Designed to be invoked from a backgrounded subshell so the menu never blocks.
_strp_zai_generate () {
	local cli="$1" file="$2" sid="$3"
	command -v clother-zai >/dev/null 2>&1 || return 1
	[[ -z "$sid" ]] && return 1

	# Atomic lock so concurrent strp invocations don't double-spend on the
	# same session. mkdir is the classic POSIX atomic lock.
	local lockdir="/tmp/strp_zai.${sid}.lock"
	mkdir "$lockdir" 2>/dev/null || return 0

	local msgs
	msgs="$(_strp_zai_extract_messages "$file" "$cli")"
	if [[ -z "$msgs" ]]; then
		rmdir "$lockdir" 2>/dev/null
		return 1
	fi

	local prompt
	prompt="Read the activity below from a coding-CLI session and output a single short title (4 to 7 words) that captures the user's main goal in this session.

Rules:
- Output ONLY the title.
- No quotes, no asterisks, no markdown, no \"Title:\" / \"Name:\" prefix.
- Do not end with a period.

Activity:
$msgs"

	local name
	# --no-session-persistence keeps this naming job from creating its own
	# session file, which strp would otherwise pick up and try to name
	# (feedback loop). Required since clother-zai → claude CLI persists by default.
	name="$(clother-zai -p --no-session-persistence --model glm-5.1 "$prompt" 2>/dev/null \
		| awk 'NF {print; exit}' \
		| tr -d '"`*' \
		| sed -E 's/^[[:space:]]*(Title|Name|Session)[[:space:]]*:[[:space:]]*//I' \
		| sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/[[:punct:]]+$//' \
		| head -c 80)"

	rmdir "$lockdir" 2>/dev/null

	if [[ -n "$name" ]]; then
		_strp_zai_cache_put "$sid" "$name" "$cli" "$file"
		printf '%s\n' "$name"
		return 0
	fi
	return 1
}

# Kick off background zai generation for a session, disowned so strp can exit.
# Skips silently if zai binary is missing, no session id, or already cached.
_strp_zai_queue () {
	local cli="$1" file="$2" sid="$3"
	[[ -z "$sid" ]] && return 0
	command -v clother-zai >/dev/null 2>&1 || return 0
	[[ -n "$(_strp_zai_cache_get "$sid")" ]] && return 0
	( _strp_zai_generate "$cli" "$file" "$sid" >/dev/null 2>&1 ) &!
}

# _strp_age <unix_seconds> — print compact age like "3m" / "2h" / "5d" / "2w"
_strp_age () {
	local mtime="${1%.*}"
	local now diff
	now=$(date +%s)
	diff=$(( now - mtime ))
	(( diff < 0 )) && diff=0
	if   (( diff < 60 ));     then echo "${diff}s"
	elif (( diff < 3600 ));   then echo "$((diff/60))m"
	elif (( diff < 86400 ));  then echo "$((diff/3600))h"
	elif (( diff < 604800 )); then echo "$((diff/86400))d"
	else                           echo "$((diff/604800))w"
	fi
}

# Quick adapters — each emits TSV `mtime\tcli\tfile` for ALL its sessions.
# Cheap: no parsing. The merger picks top-N globally, then enriches.

_strp_list_claude_quick () {
	command -v claude >/dev/null 2>&1 || return 0
	[[ -d "$HOME/.claude/projects" ]] || return 0
	# Top-level *.jsonl under each project folder. Depth 2 = project/file.jsonl.
	# Subagent transcripts live at depth 4 (project/<sid>/subagents/agent-*.jsonl)
	# and would dominate mtime sort if not filtered out.
	find "$HOME/.claude/projects" -mindepth 2 -maxdepth 2 -name '*.jsonl' \
		-printf '%T@\tclaude\t%p\n' 2>/dev/null
}

_strp_list_codex_quick () {
	command -v codex >/dev/null 2>&1 || return 0
	[[ -d "$HOME/.codex/sessions" ]] || return 0
	find "$HOME/.codex/sessions" -type f -name 'rollout-*.jsonl' \
		-printf '%T@\tcodex\t%p\n' 2>/dev/null
}

_strp_list_gemini_quick () {
	command -v gemini >/dev/null 2>&1 || return 0
	# Gemini CLI session layout is TBD — fill in once installed and stable.
	# Adapter pattern means adding support here lights up 0) for Gemini.
	return 0
}

# Enrich one quick-row → emit `mtime\tcli\tfile\tcwd\tname\tid`.
# Returns 1 if the row is unusable (no cwd recoverable).
_strp_enrich_row () {
	local mtime="$1" cli="$2" file="$3"
	local cwd="" name="" id=""

	case "$cli" in
		claude)
			# session id = filename without .jsonl
			id="${file:t:r}"
			# One jq pass: emit "C<TAB>cwd" rows and "T<TAB>title" rows.
			local both
			both="$(jq -r '
				if .cwd != null         then "C\t" + .cwd
				elif .type == "ai-title" then "T\t" + .aiTitle
				else empty end' "$file" 2>/dev/null)"
			cwd="$(printf '%s\n' "$both"  | awk -F'\t' '$1=="C"{print $2; exit}')"
			name="$(printf '%s\n' "$both" | awk -F'\t' '$1=="T"{name=$2} END{print name}')"

			# If no ai-title row, fall through: zai cache → heuristic AI →
			# heuristic user; queue a background zai job so the next strp
			# run upgrades the row from heuristic → zai-generated.
			if [[ -z "$name" ]]; then
				name="$(_strp_zai_cache_get "$id")"
				if [[ -z "$name" ]]; then
					name="$(jq -r '
						select(.type=="assistant")
						| .message.content[]?
						| select(.type=="text")
						| .text' "$file" 2>/dev/null \
						| awk 'length >= 15 && /[a-zA-Z0-9]/ {print; exit}' | head -c 80)"
				fi
				if [[ -z "$name" ]]; then
					name="$(jq -r '
						select(.type=="user")
						| .message.content
						| if type=="string" then .
						  else .[]? | select(.type=="text" or .type=="input_text") | (.text // .content // empty)
						  end' "$file" 2>/dev/null \
						| awk '{sub(/^[[:space:]]+/, "")} NF && !/^</ {print; exit}' | head -c 80)"
				fi
				# Only queue zai when there is no ai-title (don't override
				# Claude's own auto-generated titles).
				_strp_zai_queue "claude" "$file" "$id"
			fi
			;;

		codex)
			# First-line session_meta carries id + cwd.
			id="$(jq  -r 'select(.type=="session_meta") | .payload.id'  "$file" 2>/dev/null | head -n 1)"
			cwd="$(jq -r 'select(.type=="session_meta") | .payload.cwd' "$file" 2>/dev/null | head -n 1)"

			# Name preference: explicit thread_name → zai cache → heuristics →
			# (untitled). Background zai job queued when no thread_name.
			if [[ -n "$id" && -f "$HOME/.codex/session_index.jsonl" ]]; then
				name="$(jq -r --arg id "$id" \
					'select(.id==$id) | .thread_name' \
					"$HOME/.codex/session_index.jsonl" 2>/dev/null | tail -n 1)"
			fi
			if [[ -z "$name" ]]; then
				name="$(_strp_zai_cache_get "$id")"
				if [[ -z "$name" ]]; then
					# First real user input_text — skip boilerplate that opens
					# with <environment_context>, <permissions>, etc.
					name="$(jq -r '
						select(.type=="response_item" and .payload.role=="user")
						| .payload.content[]?
						| select(.type=="input_text")
						| .text
						| gsub("^[[:space:]]+"; "")
						| split("\n")[0]' "$file" 2>/dev/null \
						| awk 'NF && !/^</ {print; exit}' | head -c 80)"
				fi
				if [[ -z "$name" ]]; then
					name="$(jq -r '
						select(.type=="response_item" and .payload.role=="assistant")
						| .payload.content[]?
						| select(.type=="output_text")
						| .text' "$file" 2>/dev/null \
						| awk 'length >= 15 && /[a-zA-Z0-9]/ {print; exit}' | head -c 80)"
				fi
				_strp_zai_queue "codex" "$file" "$id"
			fi
			;;
	esac

	[[ -z "$cwd" ]] && return 1
	[[ -z "$name" ]] && name="(untitled)"
	# Collapse internal whitespace in name (newlines from snippets etc.)
	name="${name//$'\n'/ }"
	name="${name//$'\t'/ }"
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$mtime" "$cli" "$file" "$cwd" "$name" "$id"
}

# Top-10 enriched sessions across all CLIs, mtime-desc. Empty output if none.
# Over-fetches 15 quick rows so the top-10 holds even if a few sessions are
# missing recoverable cwd (e.g., brand-new sessions whose first message has
# not been written yet).
_strp_recent_sessions () {
	command -v jq >/dev/null 2>&1 || return 0
	local quick
	quick=$( { _strp_list_claude_quick
	           _strp_list_codex_quick
	           _strp_list_gemini_quick
	         } | sort -k1 -rn -t$'\t' | head -n 15 )
	[[ -z "$quick" ]] && return 0
	local mtime cli file
	while IFS=$'\t' read -r mtime cli file; do
		[[ -z "$mtime" ]] && continue
		_strp_enrich_row "$mtime" "$cli" "$file"
	done <<< "$quick" | head -n 10
}

# Render one menu line. Format: "  N) [cli ]  name             folder    Nh ago"
# Note: $4 (file) and $7 (id) are unused here — the renderer doesn't need them
# but the TSV contract carries them through to the picker dispatch.
_strp_render_row () {
	local idx="$1" mtime="$2" cli="$3" _file="$4" cwd="$5" name="$6" _id="$7"
	local age folder name_disp
	age="$(_strp_age "$mtime") ago"
	folder="${cwd:t}"
	if (( ${#name} > 42 )); then
		name_disp="${name[1,41]}…"
	else
		name_disp="$name"
	fi
	printf "%2d) [%-6s]  %-42s  %-24s  %s\n" \
		"$idx" "$cli" "$name_disp" "$folder" "$age"
}

# Per-CLI resume — cd to folder then run resume; fallback to bypass launch.

_strp_resume_claude () {
	local cwd="$1" id="$2" name="$3"
	if [[ ! -d "$cwd" ]]; then
		echo "strp: folder gone — $cwd"
		_strp_log "resume_failed" "resume[claude]" "claude" "$cwd" "$id" "$name"
		return 1
	fi
	cd "$cwd" || return 1
	_strp_log "resume_session" "resume[claude]" "claude" "$cwd" "$id" "$name"
	if ! claude --resume "$id"; then
		echo "strp: claude --resume failed — launching fresh in $cwd"
		_strp_log "resume_fallback" "resume[claude]" "claude" "$cwd" "$id" "$name"
		claude --dangerously-skip-permissions
	fi
}

_strp_resume_codex () {
	local cwd="$1" id="$2" name="$3"
	if [[ ! -d "$cwd" ]]; then
		echo "strp: folder gone — $cwd"
		_strp_log "resume_failed" "resume[codex]" "codex" "$cwd" "$id" "$name"
		return 1
	fi
	cd "$cwd" || return 1
	_strp_log "resume_session" "resume[codex]" "codex" "$cwd" "$id" "$name"
	if ! codex resume "$id"; then
		echo "strp: codex resume failed — launching fresh in $cwd"
		_strp_log "resume_fallback" "resume[codex]" "codex" "$cwd" "$id" "$name"
		codex --dangerously-bypass-approvals-and-sandbox
	fi
}

_strp_resume_gemini () {
	local cwd="$1" id="$2" name="$3"
	if [[ ! -d "$cwd" ]]; then
		echo "strp: folder gone — $cwd"
		_strp_log "resume_failed" "resume[gemini]" "gemini" "$cwd" "$id" "$name"
		return 1
	fi
	cd "$cwd" || return 1
	_strp_log "resume_session" "resume[gemini]" "gemini" "$cwd" "$id" "$name"
	# Gemini has no reliable resume — fresh launch in folder.
	gemini
}

# Sub-menu: render rows, prompt, dispatch resume.
_strp_pick_session () {
	local rows="$1"
	[[ -z "$rows" ]] && return 1

	echo ""
	echo "Recent sessions:"
	echo "-----------------------------------"

	local -a row_lines
	local idx=1
	local line mtime cli file cwd name id
	while IFS= read -r line; do
		[[ -z "$line" ]] && continue
		row_lines+=("$line")
		IFS=$'\t' read -r mtime cli file cwd name id <<< "$line"
		_strp_render_row "$idx" "$mtime" "$cli" "$file" "$cwd" "$name" "$id"
		((idx++))
	done <<< "$rows"
	echo "-----------------------------------"

	local pick
	read "pick? "
	case "$pick" in
		''|*[!0-9]*)
			echo "Invalid selection."
			return 1
			;;
	esac
	if (( pick < 1 || pick > ${#row_lines[@]} )); then
		echo "Invalid selection."
		return 1
	fi

	local selected="${row_lines[$pick]}"
	IFS=$'\t' read -r mtime cli file cwd name id <<< "$selected"

	echo ""
	echo "Resuming [$cli] $name"
	echo "Folder: $cwd"
	echo ""

	case "$cli" in
		claude) _strp_resume_claude "$cwd" "$id" "$name" ;;
		codex)  _strp_resume_codex  "$cwd" "$id" "$name" ;;
		gemini) _strp_resume_gemini "$cwd" "$id" "$name" ;;
		*)      echo "strp: unknown CLI '$cli'."; return 1 ;;
	esac
}

# ============================================================================
# Main entry
# ============================================================================

strp () {
	local ARTEMIS_DIR="$HOME/oracle/artemis-oracle"
	local ZENITH_DIR="$HOME/oracle/zenith-oracle"

	# Directories to scan for subfolders
	local SCAN_DIRS=(
		"$HOME/dev-personal"
		"$HOME/dev-work"
		"$HOME/oracle"
	)

	# Folders whose contents are flattened into the menu (the folder itself
	# is hidden from the regular list and its children appear as a section).
	local RG_DIR="$HOME/dev-work/RG"

	local dirs=()
	local dir_paths=()
	local rg_count=0

	# RG subfolders first — listed as a dedicated section.
	if [[ -d "$RG_DIR" ]]; then
		for d in "$RG_DIR"/*/; do
			[[ -d "$d" ]] || continue
			dirs+=("${${d%/}:t}")
			dir_paths+=("$d")
			((rg_count++))
		done
	fi

	# Then everything else from the scan dirs, skipping RG itself.
	for scan_dir in "${SCAN_DIRS[@]}"; do
		[[ -d "$scan_dir" ]] || continue
		for d in "$scan_dir"/*/; do
			[[ -d "$d" ]] || continue
			[[ "${d%/}" == "${RG_DIR%/}" ]] && continue
			dirs+=("${${d%/}:t}")
			dir_paths+=("$d")
		done
	done

	# v3: recent CLI sessions — compute now to decide 0) visibility.
	local recent_rows
	local -a recent_arr
	recent_rows="$(_strp_recent_sessions)"
	recent_arr=("${(@f)recent_rows}")
	# (@f) splits on newline; a trailing empty element may sneak in.
	[[ -z "${recent_arr[-1]:-}" ]] && recent_arr[-1]=()
	local recent_count=${#recent_arr[@]}

	echo "Select:"
	echo "-----------------------------------"
	if (( recent_count > 0 )); then
		echo " 0) Recent sessions ($recent_count)"
		echo "-----------------------------------"
	fi
	echo "1) Open Artemis (system oracle)"
	echo "2) Open Zenith (coding oracle)"
	echo "-----------------------------------"
	local idx=3
	local i=1
	for folder in "${dirs[@]}"; do
		printf "%2d) %s\n" "$idx" "$folder"
		if [[ $rg_count -gt 0 && $i -eq $rg_count ]]; then
			echo "-----------------------------------"
		fi
		((idx++))
		((i++))
	done
	echo "-----------------------------------"

	read "choice? "
	case "$choice" in
		0)
			if (( recent_count == 0 )); then
				echo "No recent sessions."
				return 1
			fi
			_strp_pick_session "$recent_rows"
			;;
		1|2)
			local oracle_name oracle_dir
			if [[ "$choice" == 1 ]]; then
				oracle_name="Artemis"
				oracle_dir="$ARTEMIS_DIR"
			else
				oracle_name="Zenith"
				oracle_dir="$ZENITH_DIR"
			fi
			echo ""
			echo "Starting $oracle_name ($oracle_dir)..."
			echo "Select runner:"
			echo "-----------------------------------"
			echo "1) glm   (clother-zai --model glm-5.1 --yolo)"
			echo "2) claude (claude --dangerously-skip-permissions)"
			echo "3) codex  (codex --dangerously-bypass-approvals-and-sandbox)"
			echo "-----------------------------------"
			read "runner? "
			case "$runner" in
				1)
					_strp_log "launch_oracle" "$oracle_name" "glm" "$oracle_dir"
					cd "$oracle_dir" && clother-zai --model glm-5.1 --yolo
					;;
				2)
					_strp_log "launch_oracle" "$oracle_name" "claude" "$oracle_dir"
					cd "$oracle_dir" && claude --dangerously-skip-permissions
					;;
				3)
					_strp_log "launch_oracle" "$oracle_name" "codex" "$oracle_dir"
					cd "$oracle_dir" && codex --dangerously-bypass-approvals-and-sandbox
					;;
				*)
					echo "Invalid runner."
					return 1
					;;
			esac
			;;
		*)
			# Reject empty/non-numeric input before arithmetic to avoid
			# zsh evaluating odd strings as 0 (or worse, erroring on a space).
			case "$choice" in
				''|*[!0-9]*)
					echo "Invalid selection."
					return 1
					;;
			esac

			local folder_count=${#dirs[@]}

			if (( choice < 3 || choice > folder_count + 2 )); then
				echo "Invalid selection."
				return 1
			fi

			local array_idx=$((choice - 2))
			local selected_path="${dir_paths[$array_idx]}"
			local selected_name="${dirs[$array_idx]}"

			echo ""
			echo "Selected: $selected_name"
			echo "Path: $selected_path"
			echo ""
			echo "Select action:"
			echo "-----------------------------------"
			echo "1) Open folder (cd)"
			echo "2) Open in VS Code"
			echo "-----------------------------------"

			read "action? "
			case "$action" in
				1)
					_strp_log "cd" "$selected_name" "" "$selected_path"
					cd "$selected_path"
					echo "Entered: $(pwd)"
					;;
				2)
					_strp_log "vscode" "$selected_name" "" "$selected_path"
					cd "$selected_path"
					echo "Opening VS Code..."
					code .
					;;
				*)
					echo "Invalid action."
					return 1
					;;
			esac
			;;
	esac
}
