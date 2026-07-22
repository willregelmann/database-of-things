#!/usr/bin/env bash
# One tick of the scheduled collections-audit-review job: run the skill in
# a Claude Code session with full file/git/gh access (unlike the
# audit-fix job, this one's whole point is git/gh authority — merging
# audit-finding PRs and opening+merging PRs that resolve audit-finding
# issues), scoped by the skill's own instructions to exactly that label,
# never anything else in the repo.
#
# No deterministic submit.mjs step here — the skill itself drives
# branch/commit/push/PR/merge per item, since fixing an issue can require
# arbitrary file writes submit.mjs's changelog-based pipeline was never
# built to handle (that pipeline is specific to collections-mcp tool
# calls, which is exactly the narrow surface this skill exists to work
# around).
#
# Must run from a checkout dedicated to this job (see the sync step below
# for why) -- never point cron at the primary interactive checkout, and
# never at the audit-fix job's own dedicated checkout (concurrent ticks of
# the two jobs would otherwise race on the same working tree).
set -euo pipefail

# cron runs with a minimal PATH that doesn't include nvm's node or a
# user-local claude/gh install -- prepend them so this works unattended,
# not just when fired from an interactive shell that already has them.
export PATH="/home/will/.nvm/versions/node/v22.22.0/bin:/home/will/.local/bin:$PATH"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="tools/collections-mcp/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date -u +%Y%m%dT%H%M%SZ)-review.log"

ALLOWED_TOOLS="Read Write Edit WebSearch WebFetch Bash(git *) Bash(gh *) Bash(npm *) Bash(node *) Bash(uuidgen*) Bash(curl *) Bash(mkdir *)"

{
  echo "=== collections-audit-review run: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

  # Same rationale as run-audit-job.sh: this checkout drifts behind
  # origin/main between ticks otherwise (including changes to
  # tools/collections-validate/validate.mjs itself), and a detached
  # checkout is unconditionally resettable regardless of what branch a
  # prior tick left it on -- `git pull` has no ref to merge into if HEAD
  # is stray, which is a real failure mode this same fix already
  # addressed for the audit-fix job.
  echo "--- syncing checkout with origin/main ---"
  git fetch origin main
  git checkout --detach origin/main
  # A crashed prior tick can leave uncommitted edits or a dirty working
  # tree (mid-fix, before that item's own commit) -- by design, anything
  # worth keeping should already be on its own pushed branch before this
  # runs again, so a hard reset here is safe and is what keeps one bad
  # tick from wedging every tick after it.
  git reset --hard origin/main
  git clean -fd

  set +e
  claude -p "/collections-audit-review" \
    --model claude-sonnet-5 \
    --allowedTools "$ALLOWED_TOOLS" \
    --output-format text \
    --no-session-persistence
  claude_exit=$?
  set -e

  echo "--- claude -p exited $claude_exit ---"

  # No submit.mjs equivalent to run afterward -- the skill itself commits,
  # pushes, opens, and merges PRs per item as it goes, and is instructed to
  # return the checkout to a clean detached origin/main between items. Just
  # re-sync once more here as a final safety net in case the session ended
  # mid-item (e.g. mid-fix, before returning to detached HEAD), so the next
  # tick never inherits a dirty or stray-branch working tree.
  echo "--- final re-sync ---"
  git fetch origin main
  git checkout --detach origin/main
  git reset --hard origin/main
  git clean -fd

  exit "$claude_exit"
} 2>&1 | tee -a "$LOG_FILE"
