#!/usr/bin/env bash
#
# RIC-308: Scrub the leaked Firebase service account JSON from git history,
# with safety backups at every step.
#
# Usage:
#   ./scrub-firebase-from-history.sh                # full interactive run
#   ./scrub-firebase-from-history.sh --dry-run      # preview, no changes
#   ./scrub-firebase-from-history.sh --yes          # non-interactive (skip prompts)
#
# Target: ONLY the `origin` remote (Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API).
# The go-thailand/Rice-Guard-API repo is NOT touched by this script.
#
# Safety: NEVER does anything destructive without first creating:
#   1. A local-disk copy of the Firebase JSON (so you can still use it for RIC-301)
#   2. Remote backup branches on origin (visible in GitHub for collaborators)
#   3. A local git bundle (portable full-history snapshot)
#
# After the script:
#   - Local: `develop` and `main` point at filter-repo-rewritten history
#   - Remote (origin only): same, with backup/* branches preserving the pre-scrub state
#   - On disk: Firebase JSON preserved at ${BACKUP_DIR}/riceguard-sentinel-firebase-adminsdk-fbsvc-cd578b991e.json
#

set -euo pipefail

# ────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────

REPO_DIR="${REPO_DIR:-$HOME/dev-work/RG/Rice-Guard-API}"
FILE_TO_SCRUB="riceguard-sentinel-firebase-adminsdk-fbsvc-cd578b991e.json"
BACKUP_DIR="${BACKUP_DIR:-$HOME/secret/ric308-backup-$(date +%Y%m%d-%H%M%S)}"
ORIGIN_REMOTE="${ORIGIN_REMOTE:-origin}"        # Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API
DEVELOP_BRANCH="${DEVELOP_BRANCH:-develop}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
# Expected URL — script aborts if origin points anywhere else (e.g. go-thailand)
EXPECTED_ORIGIN_URL_PATTERN="Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API"

# ────────────────────────────────────────────────────────────────────────────
# Flags
# ────────────────────────────────────────────────────────────────────────────

DRY_RUN=false
ASSUME_YES=false
DO_CLEANUP_BRANCHES=false

for arg in "$@"; do
  case "$arg" in
    --dry-run)            DRY_RUN=true ;;
    --yes|-y)             ASSUME_YES=true ;;
    --cleanup-branches)   DO_CLEANUP_BRANCHES=true ;;
    --help|-h)
      sed -n '4,30p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown flag: $arg" >&2
      exit 2
      ;;
  esac
done

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

c_red()    { printf '\033[31m%s\033[0m' "$1"; }
c_green()  { printf '\033[32m%s\033[0m' "$1"; }
c_yellow() { printf '\033[33m%s\033[0m' "$1"; }
c_blue()   { printf '\033[34m%s\033[0m' "$1"; }
c_bold()   { printf '\033[1m%s\033[0m' "$1"; }

log_step() { echo; echo "$(c_bold "▶ $1")"; }
log_info() { echo "  $(c_blue "ℹ") $1"; }
log_ok()   { echo "  $(c_green "✓") $1"; }
log_warn() { echo "  $(c_yellow "⚠") $1"; }
log_err()  { echo "  $(c_red "✗") $1" >&2; }

confirm() {
  local prompt="$1"
  if $DRY_RUN; then
    log_info "dry-run auto-yes: $prompt"
    return 0
  fi
  if $ASSUME_YES; then
    log_info "auto-yes: $prompt"
    return 0
  fi
  read -rp "  $(c_yellow "?") $prompt [y/N]: " answer
  [[ "$answer" =~ ^[Yy] ]]
}

run() {
  echo "    $(c_bold "$") $*"
  if ! $DRY_RUN; then
    eval "$@"
  fi
}

abort() {
  log_err "$1"
  exit 1
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 0: Pre-flight
# ────────────────────────────────────────────────────────────────────────────

log_step "Phase 0 — pre-flight checks"

[[ -d "$REPO_DIR" ]] || abort "REPO_DIR does not exist: $REPO_DIR"
cd "$REPO_DIR"
log_ok "in repo: $REPO_DIR"

git rev-parse --git-dir >/dev/null 2>&1 || abort "not a git repo: $REPO_DIR"
log_ok "is a git repo"

command -v git-filter-repo >/dev/null 2>&1 || abort "git-filter-repo not found in PATH (install with: pip install git-filter-repo)"
log_ok "git-filter-repo available: $(command -v git-filter-repo)"

if [[ -n "$(git status --porcelain)" ]]; then
  log_warn "working tree has uncommitted changes:"
  git status --short
  confirm "continue anyway?" || abort "aborted by user"
fi

# Guard: refuse to run if origin points at go-thailand or any other unexpected repo
ACTUAL_ORIGIN_URL="$(git remote get-url "$ORIGIN_REMOTE" 2>/dev/null || true)"
if [[ -z "$ACTUAL_ORIGIN_URL" ]]; then
  abort "$ORIGIN_REMOTE remote is not configured. Run: git remote add origin https://github.com/$EXPECTED_ORIGIN_URL_PATTERN.git"
fi
if [[ "$ACTUAL_ORIGIN_URL" != *"$EXPECTED_ORIGIN_URL_PATTERN"* ]]; then
  log_err "$ORIGIN_REMOTE points to: $ACTUAL_ORIGIN_URL"
  log_err "expected to contain:      $EXPECTED_ORIGIN_URL_PATTERN"
  abort "refusing to run against a different repo than Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API"
fi
log_ok "$ORIGIN_REMOTE → $ACTUAL_ORIGIN_URL"

log_info "fetching latest from $ORIGIN_REMOTE..."
run "git fetch $ORIGIN_REMOTE $DEVELOP_BRANCH $MAIN_BRANCH"

log_info "remote-tracking state:"
git for-each-ref --format='    %(refname:short) → %(objectname:short) %(committerdate:relative)' refs/remotes/$ORIGIN_REMOTE/$DEVELOP_BRANCH refs/remotes/$ORIGIN_REMOTE/$MAIN_BRANCH 2>/dev/null

# ────────────────────────────────────────────────────────────────────────────
# Phase 1: Backup
# ────────────────────────────────────────────────────────────────────────────

log_step "Phase 1 — backup everything"

mkdir -p "$BACKUP_DIR"
log_ok "backup dir: $BACKUP_DIR"

# 1a. Disk backup of the Firebase JSON (the file we want to keep usable post-scrub)
if [[ -f "$FILE_TO_SCRUB" ]]; then
  run "cp -v '$FILE_TO_SCRUB' '$BACKUP_DIR/'"
  log_ok "Firebase JSON copied to $BACKUP_DIR/"
elif git cat-file -e "$DEVELOP_BRANCH:$FILE_TO_SCRUB" 2>/dev/null; then
  log_warn "file not on disk but in git — recovering from $DEVELOP_BRANCH..."
  run "git show '$DEVELOP_BRANCH:$FILE_TO_SCRUB' > '$BACKUP_DIR/$FILE_TO_SCRUB'"
  log_ok "Firebase JSON recovered to $BACKUP_DIR/$FILE_TO_SCRUB"
elif git rev-list --all --objects | grep -q "$FILE_TO_SCRUB"; then
  log_warn "file not on disk and not at HEAD; trying to recover from history..."
  BLOB="$(git log --all --oneline -- "$FILE_TO_SCRUB" | head -1 | awk '{print $1}')"
  if [[ -n "$BLOB" ]]; then
    run "git show '$BLOB:$FILE_TO_SCRUB' > '$BACKUP_DIR/$FILE_TO_SCRUB'"
    log_ok "Firebase JSON recovered from $BLOB to $BACKUP_DIR/$FILE_TO_SCRUB"
  else
    abort "could not locate the Firebase JSON in working tree, HEAD, or history"
  fi
else
  abort "Firebase JSON not found anywhere — refusing to proceed without preserving it"
fi

# 1b. Push backup branches to origin (preserves pre-scrub state, visible in GitHub)
BACKUP_DEVELOP="backup/pre-ric308/develop-$TIMESTAMP"
BACKUP_MAIN="backup/pre-ric308/main-$TIMESTAMP"

log_info "creating remote backup branches on $ORIGIN_REMOTE..."
run "git push $ORIGIN_REMOTE $ORIGIN_REMOTE/$DEVELOP_BRANCH:refs/heads/$BACKUP_DEVELOP"
run "git push $ORIGIN_REMOTE $ORIGIN_REMOTE/$MAIN_BRANCH:refs/heads/$BACKUP_MAIN"
log_ok "remote backups: $BACKUP_DEVELOP, $BACKUP_MAIN"

# 1c. Local git bundle (portable full-history snapshot)
BUNDLE="$BACKUP_DIR/full-repo-bundle.bundle"
run "git bundle create '$BUNDLE' --all"
log_ok "local bundle: $BUNDLE ($(du -h "$BUNDLE" 2>/dev/null | awk '{print $1}'))"

# 1d. Save the current branch tips as a manifest for reference
MANIFEST="$BACKUP_DIR/manifest.txt"
{
  echo "RIC-308 scrub backup manifest — $TIMESTAMP"
  echo "Repo: $REPO_DIR"
  echo ""
  echo "Remote $ORIGIN_REMOTE state at backup time:"
  git for-each-ref --format='  %(refname:short) → %(objectname)' refs/remotes/$ORIGIN_REMOTE/$DEVELOP_BRANCH refs/remotes/$ORIGIN_REMOTE/$MAIN_BRANCH 2>/dev/null
  echo ""
  echo "Backup branches on $ORIGIN_REMOTE:"
  echo "  $BACKUP_DEVELOP"
  echo "  $BACKUP_MAIN"
  echo ""
  echo "Recovery commands if you need to roll back:"
  echo "  git push --force-with-lease $ORIGIN_REMOTE refs/heads/$BACKUP_DEVELOP:refs/heads/$DEVELOP_BRANCH"
  echo "  git push --force-with-lease $ORIGIN_REMOTE refs/heads/$BACKUP_MAIN:refs/heads/$MAIN_BRANCH"
} > "$MANIFEST"
log_ok "manifest: $MANIFEST"

if ! $DRY_RUN; then
  log_info "backup contents:"
  ls -la "$BACKUP_DIR" | sed 's/^/    /'
fi

confirm "backup complete; proceed with destructive history rewrite?" || abort "stopped after backup — your backup is safe at $BACKUP_DIR"

# ────────────────────────────────────────────────────────────────────────────
# Phase 2: filter-repo scrub
# ────────────────────────────────────────────────────────────────────────────

log_step "Phase 2 — git-filter-repo (local history rewrite)"

# If a prior filter-repo run left state behind, archive it before re-running.
if [[ -d .git/filter-repo ]]; then
  STALE_STATE="$BACKUP_DIR/prior-filter-repo-state"
  log_warn ".git/filter-repo exists from a prior run; archiving to $STALE_STATE"
  run "mv .git/filter-repo '$STALE_STATE'"
fi

# Show current state for the file (best-effort logging, never fail the script)
set +o pipefail
COMMITS_WITH_FILE_BEFORE=$(git log --all --oneline -- "$FILE_TO_SCRUB" 2>/dev/null | wc -l | tr -d ' ' || echo "?")
BLOB_HASH_BEFORE=$(git rev-list --all --objects 2>/dev/null | grep "$FILE_TO_SCRUB" | head -1 | awk '{print $1}' || true)
set -o pipefail
log_info "commits referencing $FILE_TO_SCRUB before: ${COMMITS_WITH_FILE_BEFORE:-?}"
log_info "blob hash before: ${BLOB_HASH_BEFORE:-<none>}"

# Save the current commits-of-interest for verification post-scrub
PRE_DEVELOP_TIP=$(git rev-parse "$ORIGIN_REMOTE/$DEVELOP_BRANCH")
PRE_MAIN_TIP=$(git rev-parse "$ORIGIN_REMOTE/$MAIN_BRANCH")
log_info "pre-scrub develop tip: $PRE_DEVELOP_TIP"
log_info "pre-scrub main tip:    $PRE_MAIN_TIP"

# Reset local branches to remote tips so filter-repo rewrites the canonical state
log_info "syncing local $DEVELOP_BRANCH and $MAIN_BRANCH to remote..."
run "git checkout '$DEVELOP_BRANCH' 2>/dev/null || git checkout -b '$DEVELOP_BRANCH' '$ORIGIN_REMOTE/$DEVELOP_BRANCH'"
run "git reset --hard '$ORIGIN_REMOTE/$DEVELOP_BRANCH'"
run "git branch -f '$MAIN_BRANCH' '$ORIGIN_REMOTE/$MAIN_BRANCH'"

# Restore the disk file (reset --hard above may have removed it)
if [[ ! -f "$FILE_TO_SCRUB" ]]; then
  log_info "disk file removed by reset; restoring from backup..."
  run "cp -v '$BACKUP_DIR/$FILE_TO_SCRUB' '$FILE_TO_SCRUB'"
fi

# Run filter-repo
run "git filter-repo --invert-paths --path '$FILE_TO_SCRUB' --force"

# filter-repo removes the 'origin' remote as a safety mechanism — restore it
if ! git remote get-url "$ORIGIN_REMOTE" >/dev/null 2>&1; then
  log_info "filter-repo removed $ORIGIN_REMOTE remote; restoring..."
  ORIGIN_URL_FROM_BACKUP="https://github.com/Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API.git"
  run "git remote add '$ORIGIN_REMOTE' '$ORIGIN_URL_FROM_BACKUP'"
fi

# Look up the rewritten tips via filter-repo's commit-map
NEW_DEVELOP_TIP=$(awk -v old="$PRE_DEVELOP_TIP" '$1 == old { print $2 }' .git/filter-repo/commit-map)
NEW_MAIN_TIP=$(awk -v old="$PRE_MAIN_TIP" '$1 == old { print $2 }' .git/filter-repo/commit-map)
log_info "post-scrub develop tip (rewritten): ${NEW_DEVELOP_TIP:-<unchanged>}"
log_info "post-scrub main tip    (rewritten): ${NEW_MAIN_TIP:-<unchanged>}"

# Position local branches at the rewritten tips.
# filter-repo updates refs in-place, so usually develop/main are already at
# the new tips. We only need to move them if they differ. For the currently
# checked-out branch, git refuses `git branch -f` even on a no-op move, so
# we explicitly skip when already-at-target.
move_branch_if_needed() {
  local branch="$1" target="$2"
  if [[ -z "$target" ]]; then
    log_info "$branch: no rewritten tip in commit-map (unchanged)"
    return 0
  fi
  local current
  current="$(git rev-parse --verify "$branch" 2>/dev/null || echo "")"
  if [[ "$current" == "$target" ]]; then
    log_info "$branch: already at $target (no-op)"
    return 0
  fi
  local head_branch
  head_branch="$(git symbolic-ref --short -q HEAD 2>/dev/null || echo "")"
  if [[ "$head_branch" == "$branch" ]]; then
    # Branch is checked out — must use reset --hard, not branch -f
    run "git reset --hard '$target'"
  else
    run "git branch -f '$branch' '$target'"
  fi
}

move_branch_if_needed "$DEVELOP_BRANCH" "$NEW_DEVELOP_TIP"
move_branch_if_needed "$MAIN_BRANCH" "$NEW_MAIN_TIP"

# Restore disk file again (filter-repo may have wiped working tree)
if [[ ! -f "$FILE_TO_SCRUB" ]]; then
  log_info "disk file removed by filter-repo working-tree update; restoring..."
  run "cp -v '$BACKUP_DIR/$FILE_TO_SCRUB' '$FILE_TO_SCRUB'"
fi

# Sanity check the rewrite
log_info "verifying scrub on rewritten branches:"
for ref in "$DEVELOP_BRANCH" "$MAIN_BRANCH"; do
  TREE_HIT=$(git ls-tree -r "$ref" 2>/dev/null | grep -c "$FILE_TO_SCRUB" || true)
  HIST_HIT=$(git log --oneline "$ref" -- "$FILE_TO_SCRUB" 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$TREE_HIT" == "0" && "$HIST_HIT" == "0" ]]; then
    log_ok "$ref: clean (file not in tree and not in history)"
  else
    log_err "$ref: file still present (tree=$TREE_HIT history=$HIST_HIT)"
    abort "filter-repo did not fully scrub $ref — investigate before pushing"
  fi
done

# ────────────────────────────────────────────────────────────────────────────
# Phase 3: Force-push to origin
# ────────────────────────────────────────────────────────────────────────────

log_step "Phase 3 — force-push rewritten branches to $ORIGIN_REMOTE"

log_warn "this is the irreversible step from the remote's perspective."
log_warn "after this, anyone with a local clone of $DEVELOP_BRANCH or $MAIN_BRANCH must re-clone or rebase."
log_warn "backup branches preserved on remote: $BACKUP_DEVELOP, $BACKUP_MAIN"
echo
confirm "proceed with force-push to $ORIGIN_REMOTE?" || abort "stopped before force-push — backups intact, no remote changes made"

run "git push --force-with-lease '$ORIGIN_REMOTE' '$DEVELOP_BRANCH'"
log_ok "force-pushed $DEVELOP_BRANCH to $ORIGIN_REMOTE"

run "git push --force-with-lease '$ORIGIN_REMOTE' '$MAIN_BRANCH'"
log_ok "force-pushed $MAIN_BRANCH to $ORIGIN_REMOTE"

# ────────────────────────────────────────────────────────────────────────────
# Phase 4: Optional stale-branch cleanup (listing only)
# ────────────────────────────────────────────────────────────────────────────

if $DO_CLEANUP_BRANCHES; then
  log_step "Phase 4 — list stale branches on $ORIGIN_REMOTE that still contain the file"
  log_warn "this is read-only; deletion is manual."
  STALE=$(git ls-remote "$ORIGIN_REMOTE" 'refs/heads/*' 2>/dev/null | awk '{print $2}' | grep -v "^refs/heads/$DEVELOP_BRANCH$" | grep -v "^refs/heads/$MAIN_BRANCH$" | grep -v "^refs/heads/backup/")
  echo "    branches still on remote (may have file in their history; manually delete with 'git push $ORIGIN_REMOTE --delete <branch>' if abandoned):"
  echo "$STALE" | sed 's|refs/heads/|      - |'
fi

# ────────────────────────────────────────────────────────────────────────────
# Phase 5: Final summary
# ────────────────────────────────────────────────────────────────────────────

log_step "Done"

echo
echo "  Summary:"
echo "    - Backup dir:        $BACKUP_DIR"
echo "    - Backup branches:   $BACKUP_DEVELOP, $BACKUP_MAIN (on $ORIGIN_REMOTE)"
echo "    - Bundle file:       $BACKUP_DIR/full-repo-bundle.bundle"
echo "    - Firebase JSON:     $BACKUP_DIR/$FILE_TO_SCRUB (and $REPO_DIR/$FILE_TO_SCRUB, gitignored)"
echo "    - Rewritten tips:    develop=$NEW_DEVELOP_TIP main=$NEW_MAIN_TIP"
echo
echo "  To roll back if something is wrong:"
echo "    git push --force-with-lease $ORIGIN_REMOTE refs/heads/$BACKUP_DEVELOP:refs/heads/$DEVELOP_BRANCH"
echo "    git push --force-with-lease $ORIGIN_REMOTE refs/heads/$BACKUP_MAIN:refs/heads/$MAIN_BRANCH"
echo
echo "  Verify in a fresh clone:"
echo "    git clone https://github.com/Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API.git /tmp/verify-scrub"
echo "    cd /tmp/verify-scrub"
echo "    git log --all --oneline -- $FILE_TO_SCRUB  # expect: empty"
echo
echo "  Next: rotate the leaked Firebase key in Console (new key + roll into prod, then delete old after 24h verified live)."
