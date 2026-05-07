#!/bin/bash
# secrets-filter.sh
# stdin に渡されたテキストから機密情報・proprietary 拡張子の混入を検査する。
# 通常運用: stdin → stdout (フィルタ通過)
# 検出時: exit 2 (fail-closed) — 呼び出し側は **絶対に proceed してはいけない**
#
# 使い方: cat data.txt | scripts/secrets-filter.sh > sanitized.txt
#         検出時は stderr にパターン名を出力 + exit 2

set -euo pipefail

INPUT=$(cat)

DENY_PATTERNS=(
  # API keys
  "sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{20,}"      # Anthropic
  "sk-[A-Za-z0-9]{40,}"                         # OpenAI / generic
  "AIza[0-9A-Za-z_-]{35}"                       # Google
  "AKIA[0-9A-Z]{16}"                            # AWS access key
  "ghp_[A-Za-z0-9]{36}"                         # GitHub PAT
  "github_pat_[A-Za-z0-9_]{82}"                 # GitHub fine-grained PAT
  "xoxb-[A-Za-z0-9-]+"                          # Slack bot token
  # Common credential shapes
  "-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"
  "password\\s*[:=]\\s*['\"][^'\"]{8,}['\"]"
  "secret\\s*[:=]\\s*['\"][^'\"]{8,}['\"]"
  # Project-specific env vars
  "CSDG_LLM_API_KEY\\s*=\\s*[A-Za-z0-9_-]{8,}"
  "ANTHROPIC_API_KEY\\s*=\\s*[A-Za-z0-9_-]{8,}"
  "OPENAI_API_KEY\\s*=\\s*[A-Za-z0-9_-]{8,}"
)

# Proprietary 拡張子 (anthropics/skills proprietary plugin がカバーする領域)
# docs/external-skills.md と同期する。新拡張子追加時は両方更新。
PROPRIETARY_EXTS=(
  "\\.pdf"
  "\\.docx"
  "\\.xlsx"
  "\\.pptx"
)

found_secret=0
for pat in "${DENY_PATTERNS[@]}"; do
  # `--` でオプション解析を打ち切り、`-----BEGIN ...` のような pattern を正しく扱う
  if echo "$INPUT" | grep -qE -- "$pat"; then
    echo "[secrets-filter] DENY: matched pattern $pat" >&2
    found_secret=1
  fi
done

for ext in "${PROPRIETARY_EXTS[@]}"; do
  # ファイルパス参照として混入していないか
  if echo "$INPUT" | grep -qE -- "${ext}([^a-zA-Z]|$)"; then
    echo "[secrets-filter] DENY: proprietary extension $ext detected" >&2
    found_secret=1
  fi
done

if [ "$found_secret" -ne 0 ]; then
  echo "[secrets-filter] FAIL — refusing to forward content to external LLM" >&2
  exit 2
fi

echo "$INPUT"
