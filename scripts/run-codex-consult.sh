#!/bin/bash
# run-codex-consult.sh
# 設計相談 (consult) 用の codex exec wrapper。
# - sandbox: read-only
# - reasoning_effort: low (軽量、ブレスト用途)
# - input は最小限の公開可能スニペットに限定 (呼び出し側で確保すること)
# - secrets-filter で機密検査 → fail-closed
#
# 使い方:
#   echo "設計の質問" | scripts/run-codex-consult.sh
#   または:
#   scripts/run-codex-consult.sh "質問テキスト"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 入力: 引数 or stdin
if [ $# -ge 1 ]; then
  INPUT="$*"
else
  INPUT=$(cat)
fi

# 機密フィルタ (fail-closed)
FILTERED=$(echo "$INPUT" | "$SCRIPT_DIR/secrets-filter.sh")

# 予算チェック (簡易) — daily token budget の枠内か
BUDGET_FILE="$PROJECT_DIR/.codex/budget.json"
if [ -f "$BUDGET_FILE" ]; then
  DAILY=$(jq -r '.daily_token_budget' "$BUDGET_FILE")
  USED=$(jq -r '.today.tokens_used' "$BUDGET_FILE")
  if [ "$USED" -ge "$DAILY" ]; then
    echo "[run-codex-consult] BLOCKED: daily token budget ($USED >= $DAILY)" >&2
    exit 3
  fi
fi

# codex exec (read-only / low reasoning)
exec codex exec \
  --sandbox read-only \
  -m gpt-5 \
  -c model_reasoning_effort=low \
  "$FILTERED"
