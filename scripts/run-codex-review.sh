#!/bin/bash
# run-codex-review.sh
# diff レビュー (review) 用の codex exec wrapper。
# - sandbox: read-only
# - reasoning_effort: medium (標準的なコードレビュー)
# - input: git diff の出力を想定 (呼び出し側で `git diff` を流し込む)
# - secrets-filter で機密検査 → fail-closed
# - 予算と diff 行数の両方をチェック
#
# 使い方:
#   git diff main..HEAD | scripts/run-codex-review.sh
#   または既に diff を持っている場合:
#   cat my-diff.patch | scripts/run-codex-review.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT=$(cat)

# diff 行数チェック (上限 = budget.diff_lines_threshold)
BUDGET_FILE="$PROJECT_DIR/.codex/budget.json"
if [ -f "$BUDGET_FILE" ]; then
  THRESHOLD=$(jq -r '.diff_lines_threshold' "$BUDGET_FILE")
  LINES=$(echo "$INPUT" | wc -l | tr -d ' ')
  if [ "$LINES" -gt "$THRESHOLD" ]; then
    echo "[run-codex-review] BLOCKED: diff size $LINES > threshold $THRESHOLD" >&2
    echo "[run-codex-review] hint: split the review into smaller chunks or review locally first" >&2
    exit 4
  fi

  DAILY=$(jq -r '.daily_token_budget' "$BUDGET_FILE")
  USED=$(jq -r '.today.tokens_used' "$BUDGET_FILE")
  if [ "$USED" -ge "$DAILY" ]; then
    echo "[run-codex-review] BLOCKED: daily token budget ($USED >= $DAILY)" >&2
    exit 3
  fi
fi

# 機密フィルタ (fail-closed) — diff の中にも secrets が混じる可能性がある
FILTERED=$(echo "$INPUT" | "$SCRIPT_DIR/secrets-filter.sh")

# レビュー指示 prompt を先頭に追加
PROMPT=$(cat <<'EOF'
あなたは独立した第二レビュアーです。以下の git diff をレビューしてください。

【観点】
1. 設計の妥当性 (アーキテクチャ違反、不要な複雑化)
2. バグの潜在性 (型・null・境界条件・並行性)
3. テスト充足度 (新規ロジックにテストが伴うか)
4. セキュリティ (input validation、機密情報の扱い、injection)
5. プロジェクト規約との整合 (CSDG: Pydantic 厳密型、外部プロンプト管理、Self-Healing 前提)

【出力フォーマット】
- CRITICAL: ブロッカー (マージ前に必ず修正)
- HIGH: 強く推奨 (今回の PR で対応)
- MEDIUM: 改善提案 (フォローアップ可)
- LOW: nitpick

それぞれ「ファイル:行番号」と問題点・修正提案を併記してください。

【diff】
EOF
)

INPUT_FOR_CODEX="$PROMPT
$FILTERED"

exec codex exec \
  --sandbox read-only \
  -m gpt-5 \
  -c model_reasoning_effort=medium \
  "$INPUT_FOR_CODEX"
