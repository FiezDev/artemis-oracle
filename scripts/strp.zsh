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

	local dirs=()
	local dir_paths=()

	# Collect folders from each scan directory
	for scan_dir in "${SCAN_DIRS[@]}"; do
		if [[ -d "$scan_dir" ]]; then
			for d in "$scan_dir"/*/; do
				[[ -d "$d" ]] || continue
				local name=$(basename "$d")
				dirs+=("$name")
				dir_paths+=("$d")
			done
		fi
	done

	echo "Select:"
	echo "-----------------------------------"
	echo "1) Open Artemis (system oracle)"
	echo "2) Open Zenith (coding oracle)"
	echo "-----------------------------------"
	local idx=3
	for folder in "${dirs[@]}"; do
		printf "%2d) %s\n" $idx "$folder"
		((idx++))
	done
	echo "-----------------------------------"

	read "choice? "
	case "$choice" in
		1)
			echo "Starting Artemis (system oracle)..."
			cd "$ARTEMIS_DIR" && clother-zai --dangerously-skip-permissions
			;;
		2)
			echo "Starting Zenith (coding oracle)..."
			cd "$ZENITH_DIR" && clother-zai --dangerously-skip-permissions
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
