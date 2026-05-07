#!/bin/bash
# pre-edit-steering.sh — PreToolUse(Edit/Write) hook
# 実装ファイル (csdg/, prompts/) の編集時に .steering/ にアクティブなタスクが
# あるかチェックする。なければ警告 (BLOCK ではなく WARN) を出力。
# docs/ / tests/ / .claude/ / .steering/ 自体への編集は対象外 (偽陽性回避)。

set -euo pipefail

FILE="${CLAUDE_FILE_PATH:-}"
[ -z "$FILE" ] && exit 0

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REL_PATH="${FILE#$PROJECT_DIR/}"

# 対象パス: csdg/ または prompts/ のみ
case "$REL_PATH" in
  csdg/*|prompts/*) ;;
  *)
    echo "[guard] PASS: steering (non-impl path: $REL_PATH)"
    exit 0
    ;;
esac

# Today (UTC日付ベース) のタスクが存在するか
TODAY=$(date +%Y%m%d)
RECENT_TASK_DAYS=7  # 過去 7 日以内にタスクが作られていれば「アクティブ」とみなす
ACTIVE=0

for offset in $(seq 0 $RECENT_TASK_DAYS); do
  D=$(date -v-${offset}d +%Y%m%d 2>/dev/null || date -d "$offset days ago" +%Y%m%d 2>/dev/null || echo "")
  [ -z "$D" ] && continue
  if ls "$PROJECT_DIR/.steering/" 2>/dev/null | grep -q "^${D}-"; then
    ACTIVE=1
    break
  fi
done

if [ "$ACTIVE" -eq 0 ]; then
  echo "[guard] WARN: editing $REL_PATH but no active task in .steering/ (past ${RECENT_TASK_DAYS}d)" >&2
  echo "[guard] hint: run /start-task before substantive code changes" >&2
  # WARN のみ、BLOCK はしない
  exit 0
fi

echo "[guard] PASS: steering ($REL_PATH; active task found)"
exit 0
