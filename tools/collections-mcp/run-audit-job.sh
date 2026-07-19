#!/usr/bin/env bash
# One tick of the hourly collections-audit-fix job: run the skill in a
# throwaway, tool-restricted Claude Code session, then deterministically
# submit whatever it changed (if anything) — the model has no Bash/Edit/
# Write/Read access at all in its own session, so it cannot touch
# collections/** except through the collections-mcp MCP tools. Submission
# itself happens here, after the session ends, not inside it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="tools/collections-mcp/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date -u +%Y%m%dT%H%M%SZ).log"

MCP_TOOLS="mcp__collections-mcp__choose_random_collection mcp__collections-mcp__get_collection_context mcp__collections-mcp__get_collection_details mcp__collections-mcp__list_items mcp__collections-mcp__list_collections mcp__collections-mcp__get_item_details mcp__collections-mcp__upsert_item mcp__collections-mcp__upsert_collection"

{
  echo "=== collections-audit-fix run: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

  set +e
  claude -p "/collections-audit-fix" \
    --model claude-sonnet-5 \
    --mcp-config .mcp.json \
    --strict-mcp-config \
    --allowedTools "$MCP_TOOLS WebSearch WebFetch" \
    --disallowedTools "Bash Edit Write Read" \
    --max-budget-usd 2 \
    --output-format text \
    --no-session-persistence
  claude_exit=$?
  set -e

  echo "--- claude -p exited $claude_exit ---"

  if [ "$claude_exit" -ne 0 ]; then
    echo "Skipping submit.mjs: the audit session itself failed."
    exit "$claude_exit"
  fi

  echo "--- running submit.mjs ---"
  node tools/collections-mcp/submit.mjs
} 2>&1 | tee -a "$LOG_FILE"
