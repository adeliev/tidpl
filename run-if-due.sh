#!/bin/bash
# One-shot check: runs `tidpl run` only if 2+ days have passed.
# Suitable for cron/launchd: run every 6h, it does nothing if not due.
HERE="$(cd "$(dirname "$0")" && pwd)"
MARKER="$HERE/data/.last_run"
INTERVAL=$((2 * 86400))  # 2 days

now=$(date +%s)
if [ -f "$MARKER" ]; then
    last=$(cat "$MARKER")
    elapsed=$((now - last))
    if [ "$elapsed" -lt "$INTERVAL" ]; then
        exit 0
    fi
fi

"$HERE/.venv/bin/python3" -m tidpl.cli run && echo "$(date +%s)" > "$MARKER"
