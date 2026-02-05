#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ROOT_DIR/build"

PYTHON="$(which python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "python3 not found in PATH"
  exit 1
fi

echo "Using python: $PYTHON"

# Install dependencies
echo "Installing build dependencies (pyinstaller, PyQt6)..."
"$PYTHON" -m pip install --user --upgrade pyinstaller PyQt6 || true

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "$BUILD_DIR" dist build

# Build using unified spec file
echo "Building with unified spec file (OpenCodeTokenMeter.spec)..."
cd "$ROOT_DIR"
"$PYTHON" -m PyInstaller --clean OpenCodeTokenMeter.spec

# Verify the .app was created
APP_BUNDLE="$ROOT_DIR/dist/OpenCode Token Meter.app"
if [ ! -d "$APP_BUNDLE" ]; then
  echo "ERROR: .app bundle not created at $APP_BUNDLE"
  ls -la "$ROOT_DIR/dist/"
  exit 1
fi

echo "macOS .app bundle created at: $APP_BUNDLE"

# Show final app size
echo ""
echo "Final app bundle size:"
du -sh "$APP_BUNDLE"

# Create DMG installer (optional)
DMG_SCRIPT="$ROOT_DIR/create_dmg.sh"
if [ -f "$DMG_SCRIPT" ]; then
  echo ""
  echo "Creating DMG installer..."
  bash "$DMG_SCRIPT"
else
  echo "Note: create_dmg.sh not found, skipping DMG creation"
fi

echo ""
echo "Build complete!"
echo "App location: $APP_BUNDLE"
exit 0
