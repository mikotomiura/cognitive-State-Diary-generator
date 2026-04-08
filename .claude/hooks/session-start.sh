#!/bin/bash
# Session start hook - display project status
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 0

echo "════════════════════════════════════════"
echo "CSDG Session Info"
echo "  Branch: $(git branch --show-current 2>/dev/null)"
echo "  Last commit: $(git log -1 --oneline 2>/dev/null)"
echo "  Modified files: $(git status --short 2>/dev/null | wc -l | tr -d ' ')"

todo_count=$(grep -r "TODO\|FIXME\|HACK" csdg/ tests/ 2>/dev/null | wc -l | tr -d ' ')
echo "  Open TODOs: $todo_count"

recent=$(ls -1 .steering/ 2>/dev/null | grep -E '^[0-9]{8}-' | tail -3)
if [ -n "$recent" ]; then
    echo "  Recent tasks:"
    echo "$recent" | sed 's/^/    - /'
fi
echo "════════════════════════════════════════"
