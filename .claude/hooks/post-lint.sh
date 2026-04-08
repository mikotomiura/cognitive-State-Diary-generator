#!/bin/bash
# Post-tool-use lint hook - only runs ruff on Python files
FILE="${CLAUDE_FILE_PATH:-}"
[ -z "$FILE" ] && exit 0
case "$FILE" in
  *.py)
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
    "$PROJECT_DIR/.venv/bin/ruff" check --fix "$FILE" 2>/dev/null
    "$PROJECT_DIR/.venv/bin/ruff" format "$FILE" 2>/dev/null
    ;;
esac
exit 0
