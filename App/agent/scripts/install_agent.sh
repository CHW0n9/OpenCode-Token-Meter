#!/usr/bin/env bash
#
# Installation script for OpenCode Token Meter Agent
#
set -e

echo "OpenCode Token Meter - Agent Installation"
echo "=========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"

# Paths
APP_SUPPORT_DIR="$HOME/Library/Application Support/OpenCode Token Meter"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOGS_DIR="$HOME/Library/Logs/OpenCode Token Meter"
PLIST_NAME="com.opencode.token.agent.plist"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Find Python 3
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "Error: python3 not found in PATH"
    echo "Please install Python 3.8 or later"
    exit 1
fi

echo "Using Python: $PYTHON_PATH"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p "$APP_SUPPORT_DIR"
mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$LOGS_DIR"

# Install agent package
echo "Installing agent package..."
cd "$AGENT_DIR"
$PYTHON_PATH -m pip install --user -e .

# Create plist file
echo "Creating launchd plist..."
cp "$SCRIPT_DIR/com.opencode.token.agent.plist" "$PLIST_PATH"

# Replace placeholders in plist
sed -i '' "s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" "$PLIST_PATH"
sed -i '' "s|HOMEDIR_PLACEHOLDER|$HOME|g" "$PLIST_PATH"

# Set permissions
chmod 600 "$PLIST_PATH"

# Unload existing agent if running
echo "Stopping any existing agent..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load the agent
echo "Starting agent..."
launchctl load "$PLIST_PATH"

echo ""
echo "Installation complete!"
echo ""
echo "The agent is now running in the background."
echo "Logs can be found at: $LOGS_DIR"
echo ""
echo "To manually control the agent:"
echo "  Start:  launchctl load $PLIST_PATH"
echo "  Stop:   launchctl unload $PLIST_PATH"
echo "  Status: launchctl list | grep opencode"
echo ""
echo "You can now run the menubar app."
