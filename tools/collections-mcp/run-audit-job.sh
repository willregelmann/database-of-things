#!/usr/bin/env bash
# One tick of the hourly collections-audit-fix job: run the skill in a
# throwaway, tool-restricted Claude Code session, then deterministically
# submit whatever it changed (if anything) — the model has no Bash/Edit/
# Write/Read access at all in its own session, so it cannot touch
# collections/** except through the collections-mcp MCP tools. Submission
# itself happens here, after the session ends, not inside it.
#
# Must run from a checkout dedicated to this job (see the sync step below
# for why) -- never point cron at the primary interactive checkout.
set -euo pipefail

# cron runs with a minimal PATH that doesn't include nvm's node or a
# user-local claude install -- prepend them so this works unattended, not
# just when fired from an interactive shell that already has them.
export PATH="/home/will/.nvm/versions/node/v22.22.0/bin:/home/will/.local/bin:$PATH"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="tools/collections-mcp/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date -u +%Y%m%dT%H%M%SZ).log"

MCP_TOOLS="mcp__collections-mcp__choose_random_collection mcp__collections-mcp__get_collection_context mcp__collections-mcp__get_collection_details mcp__collections-mcp__list_items mcp__collections-mcp__list_components mcp__collections-mcp__list_collections mcp__collections-mcp__get_item_details mcp__collections-mcp__upsert_item mcp__collections-mcp__upsert_component mcp__collections-mcp__upsert_collection mcp__collections-mcp__rename_item mcp__collections-mcp__flag_finding"

{
  echo "=== collections-audit-fix run: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

  # This checkout is never touched between ticks otherwise, so it silently
  # drifts behind origin/main as PRs merge -- including PRs that change
  # tools/collections-validate/validate.mjs itself. A stale local validator
  # can pass writes here that a fresh one (what CI actually runs on the PR)
  # rejects.
  #
  # Detached checkout, not `git pull --ff-only`: this checkout must be
  # unconditionally resettable to origin/main's tip regardless of what
  # branch it was left on. `submit.mjs` always returns here to a real
  # branch name after a run, but a session that dies before submit.mjs
  # runs (or a leftover branch from manual testing) can leave HEAD
  # somewhere else with no upstream tracking -- `git pull` has no ref to
  # merge into and dies, which took the whole job down on 2026-07-20 when
  # this checkout was left on a stray feature branch. Detached HEAD never
  # "claims" a branch, so it can always resync from any prior state.
  #
  # `--force` because a plain checkout also aborts when an untracked file here
  # collides with one that main has since started tracking -- and it aborts
  # even when the contents are byte-identical. `.mcp.json` hit exactly this:
  # it lived untracked in this checkout until it was committed upstream, which
  # would have failed every tick from then on. --force overwrites only the
  # colliding path; unrelated untracked/ignored files (.changelog.json,
  # audit-ledger.jsonl) are left alone, which is what this step wants anyway.
  echo "--- syncing checkout with origin/main ---"
  git fetch origin main
  git checkout --detach --force origin/main

  # Clear any changelog left behind by a previous tick, AFTER the sync above.
  #
  # submit.mjs only calls clear() once it has finished successfully, so a tick
  # where submit.mjs itself dies partway (gh rate-limited, push rejected,
  # network gone) leaves entries on disk. .changelog.json is gitignored, so the
  # sync above wipes the working-tree *file changes* those entries describe
  # while leaving the *entries* untouched. The next tick then commits a diff
  # that doesn't match its own PR body -- an entry claiming a change the branch
  # doesn't contain. PR #196 is exactly that: it advertised seven changes and
  # carried six, and the review job caught the seventh had never happened.
  # PR #157 bundled stale Batman entries from an unrelated earlier run the same
  # way.
  #
  # The existing note further down covers the *other* half of this failure --
  # a session dying before submit.mjs runs, which strands good entries. That
  # one is handled by always running submit.mjs. This is the inverse, and the
  # only safe moment to clear is here: after the reset, before the session
  # starts writing entries this tick actually owns.
  echo "--- clearing any stale changelog from a prior tick ---"
  rm -f tools/collections-mcp/.changelog.json

  set +e
  claude -p "/collections-audit-fix" \
    --model claude-sonnet-5 \
    --mcp-config .mcp.json \
    --strict-mcp-config \
    --allowedTools "$MCP_TOOLS WebSearch WebFetch" \
    --disallowedTools "Bash Edit Write Read" \
    --output-format text \
    --no-session-persistence
  claude_exit=$?
  set -e

  echo "--- claude -p exited $claude_exit ---"

  if [ "$claude_exit" -ne 0 ]; then
    echo "note: the audit session itself exited non-zero -- still attempting"
    echo "submit.mjs below, since any upsert_item/upsert_collection calls made"
    echo "before the failure already wrote real, individually-validated changes"
    echo "to disk. Leaving those unsubmitted just strands them until some"
    echo "future run's submit.mjs happens to pick them up alongside its own"
    echo "(unrelated) changelog entries -- which is exactly how this failure"
    echo "mode was discovered. submit.mjs's own validate-before-commit step is"
    echo "the real safety net regardless of why the session ended."
  fi

  echo "--- running submit.mjs ---"
  set +e
  node tools/collections-mcp/submit.mjs
  submit_exit=$?
  set -e

  if [ "$claude_exit" -ne 0 ]; then
    exit "$claude_exit"
  fi
  exit "$submit_exit"
} 2>&1 | tee -a "$LOG_FILE"
