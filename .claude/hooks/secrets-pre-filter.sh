#!/bin/bash
# secrets-pre-filter.sh
# PreToolUse(Bash) hook — codex 起動前に機密 / proprietary 拡張子の混入を検査。
# 1. 早期 exit: codex を含まない Bash 呼び出しは即通過
# 2. コマンド文字列の中に proprietary 拡張子のファイルパスが含まれていればブロック
# 3. 通過時は [guard] PASS: secrets-pre-filter を出力
#
# 注: 詳細な内容検査は scripts/secrets-filter.sh が pipeline 内で実施する。
#     このフックは「コマンドラインに proprietary 拡張子が混入していないか」の事前チェック。

set -euo pipefail

COMMAND="${CLAUDE_TOOL_INPUT:-${1:-}}"

case "$COMMAND" in
  *codex*) ;;
  *) exit 0 ;;
esac

# Proprietary 拡張子 (docs/external-skills.md と同期)
PROPRIETARY_EXTS=(
  "\\.pdf"
  "\\.docx"
  "\\.xlsx"
  "\\.pptx"
)

for ext in "${PROPRIETARY_EXTS[@]}"; do
  if echo "$COMMAND" | grep -qE "${ext}([^a-zA-Z]|$)"; then
    echo "[guard] BLOCKED: proprietary extension $ext in codex command" >&2
    echo "[guard] hint: extract content as plain text first; do not pass proprietary files to external LLM" >&2
    exit 1
  fi
done

echo "[guard] PASS: secrets-pre-filter (no proprietary extensions in command)"
exit 0
