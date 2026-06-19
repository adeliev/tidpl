#!/bin/bash
# Manage tidpl scheduled service via launchd.
# Usage: ./service.sh {install|uninstall|status}

HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL=com.tidpl.scheduler

case "${1:-}" in
    install)
        PLIST_SRC="$HERE/com.tidpl.scheduler.plist"
        PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
        if [ ! -f "$PLIST_SRC" ]; then
            if [ -f "$HERE/com.tidpl.scheduler.plist.example" ]; then
                echo "Edit com.tidpl.scheduler.plist.example with your paths,"
                echo "rename to com.tidpl.scheduler.plist, and re-run this command."
            else
                echo "com.tidpl.scheduler.plist not found."
            fi
            exit 1
        fi
        cp "$PLIST_SRC" "$PLIST_DST"
        launchctl load "$PLIST_DST"
        echo "Installed and loaded."
        ;;
    uninstall)
        launchctl unload "$HOME/Library/LaunchAgents/$LABEL.plist" 2>/dev/null
        rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
        echo "Unloaded and removed."
        ;;
    status)
        launchctl list | grep "$LABEL" || echo "Not loaded."
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status}"
        exit 1
        ;;
esac
