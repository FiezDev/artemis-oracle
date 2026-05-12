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

			# Untitled session — fall back to AI response, then user message.
			# Active untitled sessions get a meaningful name from the first
			# substantive AI text line. Sterile sessions (no AI response yet)
			# degrade to the first non-boilerplate user message.
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
			;;

		codex)
			# First-line session_meta carries id + cwd.
			id="$(jq  -r 'select(.type=="session_meta") | .payload.id'  "$file" 2>/dev/null | head -n 1)"
			cwd="$(jq -r 'select(.type=="session_meta") | .payload.cwd' "$file" 2>/dev/null | head -n 1)"

			# Name preference: thread_name (named threads) → first real user text → timestamp.
			if [[ -n "$id" && -f "$HOME/.codex/session_index.jsonl" ]]; then
				name="$(jq -r --arg id "$id" \
					'select(.id==$id) | .thread_name' \
					"$HOME/.codex/session_index.jsonl" 2>/dev/null | tail -n 1)"
			fi
			if [[ -z "$name" ]]; then
				# First real user input_text — skip boilerplate that opens with an
				# XML-ish tag like <environment_context>, <permissions>, etc.
				# jq emits the first non-whitespace line per input_text; awk then
				# picks the first one that isn't empty and doesn't start with '<'.
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
				# Last-resort: first substantive AI output_text line.
				name="$(jq -r '
					select(.type=="response_item" and .payload.role=="assistant")
					| .payload.content[]?
					| select(.type=="output_text")
					| .text' "$file" 2>/dev/null \
					| awk 'length >= 15 && /[a-zA-Z0-9]/ {print; exit}' | head -c 80)"
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
