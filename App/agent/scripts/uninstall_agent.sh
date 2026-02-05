#!/usr/bin/env bash
#
# Uninstallation script for OpenCode Token Meter Agent
#
set -e

echo "OpenCode Token Meter - Agent Uninstallation"
echo "============================================"
echo ""

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.opencode.token.agent.plist"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Stop and unload the agent
if [ -f "$PLIST_PATH" ]; then
    echo "Stopping agent..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    
    echo "Removing launchd plist..."
    rm "$PLIST_PATH"
    
    echo "Agent uninstalled successfully."
else
    echo "Agent is not installed."
fi

echo ""
echo "Note: Application data remains at:"
echo "  ~/Library/Application Support/OpenCode Token Meter/"
echo ""
echo "To remove all data, run:"
echo "  rm -rf ~/Library/Application\ Support/OpenCode\ Token\ Count/"
echo "  rm -rf ~/Library/Logs/OpenCode\ Token\ Count/"
