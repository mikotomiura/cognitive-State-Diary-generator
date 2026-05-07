#!/bin/bash
# post-fmt.sh — PostToolUse(Edit/Write) hook
# Python ファイル編集後に ruff format を実行。
# --check で先に判定し、変更が必要な時だけ format を走らせて [fmt] applied を出力。
# 変更不要なら無言通過 (ノイズ削減)。

set -euo pipefail

FILE="${CLAUDE_FILE_PATH:-}"
[ -z "$FILE" ] && exit 0

case "$FILE" in
  *.py) ;;
  *) exit 0 ;;
esac

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUFF="$PROJECT_DIR/.venv/bin/ruff"

[ ! -x "$RUFF" ] && exit 0  # ruff 未インストール時は何もしない

# --check で先に判定 (変更不要なら無言通過)
if "$RUFF" format --check "$FILE" >/dev/null 2>&1; then
  exit 0
fi

# 変更が必要 — 実行 + 報告
"$RUFF" check --fix "$FILE" >/dev/null 2>&1 || true
"$RUFF" format "$FILE" >/dev/null 2>&1 || true
echo "[fmt] applied: $(basename "$FILE")"

exit 0
