#!/bin/bash
# stop-check.sh — Stop hook (旧 type:prompt の置換)
# セッション終了時に簡易チェックを実行し、問題があれば [stop] WARN を 1 行出す。
# - ファイル変更が一切なければ skip
# - ruff format --check / ruff check で違反があれば WARN
# - tests/ への変更があった場合は pytest 簡易疎通の WARN ヒント
# 出力は問題時のみ。すべて緑なら無言。

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 0

# このセッションでファイル変更があったか (git status で判定)
MODIFIED=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODIFIED" -eq 0 ]; then
  exit 0
fi

RUFF="$PROJECT_DIR/.venv/bin/ruff"
WARNS=()

# ruff format --check
if [ -x "$RUFF" ]; then
  if ! "$RUFF" format --check csdg/ tests/ >/dev/null 2>&1; then
    WARNS+=("ruff format --check failed; run 'ruff format csdg/ tests/'")
  fi
  if ! "$RUFF" check csdg/ tests/ >/dev/null 2>&1; then
    WARNS+=("ruff check failed; run 'ruff check csdg/ tests/ --fix'")
  fi
fi

# tests/ に変更があれば pytest 推奨
if git status --short 2>/dev/null | grep -qE '^.M tests/|^.. tests/'; then
  WARNS+=("tests/ modified — run 'pytest tests/ -v' before commit")
fi

# .steering/ のタスクに対応する tasklist.md が更新されているか
RECENT_TASK=$(ls -1 .steering/ 2>/dev/null | grep -E '^[0-9]{8}-' | tail -1)
if [ -n "$RECENT_TASK" ]; then
  TASKLIST=".steering/${RECENT_TASK}/tasklist.md"
  if [ -f "$TASKLIST" ]; then
    UNCHECKED=$(grep -c '^- \[ \]' "$TASKLIST" 2>/dev/null || echo 0)
    if [ "$UNCHECKED" -gt 5 ]; then
      WARNS+=("$RECENT_TASK has $UNCHECKED unchecked tasklist items — review before /finish-task")
    fi
  fi
fi

for w in "${WARNS[@]}"; do
  echo "[stop] WARN: $w" >&2
done

exit 0
