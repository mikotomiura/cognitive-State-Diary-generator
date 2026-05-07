#!/bin/bash
# preflight.sh — UserPromptSubmit hook
# 動的ダッシュボード: .steering 状態 / git 状態 / 直近タスクを 1 行ずつ表示。
# 必ず exit 0 で終了 (BLOCK しない)。

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 0

# 1. .steering 状態
STEERING_DIRS=$(ls -1 .steering/ 2>/dev/null | grep -E '^[0-9]{8}-' | wc -l | tr -d ' ')
RECENT_TASK=$(ls -1 .steering/ 2>/dev/null | grep -E '^[0-9]{8}-' | tail -1)
echo "[preflight] task: ${STEERING_DIRS} tasks total / latest: ${RECENT_TASK:-none}"

# 2. git 状態
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
MODIFIED=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
COMMITS_AHEAD=$(git rev-list --count main..HEAD 2>/dev/null || echo 0)
echo "[preflight] git: ${BRANCH} / ${MODIFIED} modified / ${COMMITS_AHEAD} commits ahead of main"

# 3. Codex 予算状況 (Phase 5 完了時のみ)
if [ -f .codex/budget.json ]; then
  USED=$(jq -r '.today.tokens_used' .codex/budget.json 2>/dev/null || echo 0)
  DAILY=$(jq -r '.daily_token_budget' .codex/budget.json 2>/dev/null || echo 0)
  if [ "$DAILY" -gt 0 ]; then
    PCT=$((USED * 100 / DAILY))
    echo "[preflight] codex: ${USED}/${DAILY} tokens (${PCT}%) today"
  fi
fi

exit 0
