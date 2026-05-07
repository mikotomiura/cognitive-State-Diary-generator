#!/bin/bash
# codex-budget-guard.sh
# PreToolUse(Bash) hook — codex 関連コマンドのみガードする。
# 1. 早期 exit: codex を含まない Bash 呼び出しは即 exit 0 (高速通過)
# 2. .codex/budget.json から日次予算を読み、超過していたらブロック (exit 1)
# 3. 通過時は [guard] PASS: codex-budget を出力

set -euo pipefail

COMMAND="${CLAUDE_TOOL_INPUT:-${1:-}}"

# 早期 exit: codex が含まれない Bash 呼び出しは即通過
case "$COMMAND" in
  *codex*) ;;
  *) exit 0 ;;
esac

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BUDGET_FILE="$PROJECT_DIR/.codex/budget.json"

if [ ! -f "$BUDGET_FILE" ]; then
  echo "[guard] WARN: budget.json not found, allowing codex" >&2
  exit 0
fi

DAILY=$(jq -r '.daily_token_budget' "$BUDGET_FILE" 2>/dev/null || echo 0)
USED=$(jq -r '.today.tokens_used' "$BUDGET_FILE" 2>/dev/null || echo 0)

if [ "$USED" -ge "$DAILY" ] && [ "$DAILY" -gt 0 ]; then
  echo "[guard] BLOCKED: codex budget exceeded ($USED >= $DAILY tokens today)" >&2
  echo "[guard] hint: edit .codex/budget.json to reset, or wait for next day" >&2
  exit 1
fi

echo "[guard] PASS: codex-budget ($USED / $DAILY tokens today)"
exit 0
