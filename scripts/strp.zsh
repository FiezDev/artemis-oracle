# strp - Startup script for folder selection and oracle launching
# Updated: 2026-03-30

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
			dirs+=("$(basename "$d")")
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
			dirs+=("$(basename "$d")")
			dir_paths+=("$d")
		done
	done

	echo "Select:"
	echo "-----------------------------------"
	echo "1) Open Artemis (system oracle)"
	echo "2) Open Zenith (coding oracle)"
	echo "-----------------------------------"
	local idx=3
	local i=1
	for folder in "${dirs[@]}"; do
		printf "%2d) %s\n" $idx "$folder"
		if [[ $rg_count -gt 0 && $i -eq $rg_count ]]; then
			echo "-----------------------------------"
		fi
		((idx++))
		((i++))
	done
	echo "-----------------------------------"

	read "choice? "
	case "$choice" in
		1|2)
			if [[ "$choice" == 1 ]]; then
				local oracle_name="Artemis"
				local oracle_dir="$ARTEMIS_DIR"
			else
				local oracle_name="Zenith"
				local oracle_dir="$ZENITH_DIR"
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
					cd "$oracle_dir" && clother-zai --model glm-5.1 --yolo
					;;
				2)
					cd "$oracle_dir" && claude --dangerously-skip-permissions
					;;
				3)
					cd "$oracle_dir" && codex --dangerously-bypass-approvals-and-sandbox
					;;
				*)
					echo "Invalid runner."
					return 1
					;;
			esac
			;;
		*)
			local folder_count=${#dirs[@]}

			if [[ "$choice" -lt 3 || "$choice" -gt $((folder_count + 2)) ]]; then
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
					cd "$selected_path"
					echo "Entered: $(pwd)"
					;;
				2)
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
