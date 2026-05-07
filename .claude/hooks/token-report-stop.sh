#!/bin/bash
# token-report-stop.sh
# Stop hook — セッション内の codex 利用 token を集計し .codex/budget.json と _token_log.md を更新。
# 冪等性キー: ${date}:tokens=${used}:invs=${invocations}
# 同じキーが既に記録されていたら skip (重複実行対策)。
# flock で排他制御し、並列 stop 発火でも last-write-wins にならないようにする。

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BUDGET_FILE="$PROJECT_DIR/.codex/budget.json"
LOG_FILE="$PROJECT_DIR/.steering/_token_log.md"
LAST_KEY_FILE="$PROJECT_DIR/.steering/_token_log.last_key"
LOCK_FILE="$PROJECT_DIR/.codex/.budget.lock"

[ ! -f "$BUDGET_FILE" ] && exit 0  # Phase 5 skip 状態では何もしない

# このセッション中の codex 利用を集計する。
# 簡易実装: 直近のセッションログから codex exec の有無を確認 (実用上は codex が token 数を返す前提)
# 現状は heuristic として transcript からの推定を行わず、budget.json をそのまま読み更新する形。
TODAY=$(date +%Y-%m-%d)

mkdir -p "$(dirname "$LOCK_FILE")"

(
  flock -x 200

  # 日付が変わっていたら history に push して today をリセット
  CURRENT_DATE=$(jq -r '.today.date' "$BUDGET_FILE")
  if [ "$CURRENT_DATE" != "$TODAY" ]; then
    TMP=$(mktemp)
    jq --arg d "$TODAY" '.history += [.today] | .today = {date: $d, tokens_used: 0, invocations: 0}' "$BUDGET_FILE" > "$TMP"
    mv "$TMP" "$BUDGET_FILE"
  fi

  USED=$(jq -r '.today.tokens_used' "$BUDGET_FILE")
  INVS=$(jq -r '.today.invocations' "$BUDGET_FILE")
  KEY="${TODAY}:tokens=${USED}:invs=${INVS}"

  # 冪等性キー: 同じキーが直前の記録と一致していたら skip
  if [ -f "$LAST_KEY_FILE" ] && [ "$(cat "$LAST_KEY_FILE")" = "$KEY" ]; then
    exit 0
  fi

  # ログに追記
  mkdir -p "$(dirname "$LOG_FILE")"
  if [ ! -f "$LOG_FILE" ]; then
    echo "# Codex Token Usage Log" > "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo "| Date | Tokens Used | Invocations | Daily Budget |" >> "$LOG_FILE"
    echo "|---|---|---|---|" >> "$LOG_FILE"
  fi

  DAILY=$(jq -r '.daily_token_budget' "$BUDGET_FILE")
  echo "| $TODAY | $USED | $INVS | $DAILY |" >> "$LOG_FILE"

  echo "$KEY" > "$LAST_KEY_FILE"

  # ユーザー向け出力 (使用率が 80% 超でアラート)
  if [ "$DAILY" -gt 0 ]; then
    PCT=$((USED * 100 / DAILY))
    if [ "$PCT" -ge 80 ]; then
      echo "[stop] WARN: codex token usage at ${PCT}% (${USED}/${DAILY}) for $TODAY" >&2
    fi
  fi
) 200>"$LOCK_FILE"

exit 0
