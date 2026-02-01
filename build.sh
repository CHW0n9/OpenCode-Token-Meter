#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Support project layout either at root/agent or App/agent
if [ -d "$ROOT_DIR/agent" ]; then
  AGENT_DIR="$ROOT_DIR/agent"
elif [ -d "$ROOT_DIR/App/agent" ]; then
  AGENT_DIR="$ROOT_DIR/App/agent"
else
  echo "Agent directory not found under $ROOT_DIR/agent or $ROOT_DIR/App/agent"
  exit 1
fi

if [ -d "$ROOT_DIR/menubar" ]; then
  MENUBAR_DIR="$ROOT_DIR/menubar"
elif [ -d "$ROOT_DIR/App/menubar" ]; then
  MENUBAR_DIR="$ROOT_DIR/App/menubar"
else
  echo "Menubar directory not found under $ROOT_DIR/menubar or $ROOT_DIR/App/menubar"
  exit 1
fi
BUILD_DIR="$ROOT_DIR/build"
AGENT_DIST="$BUILD_DIR/agent_dist"
MENUBAR_DIST="$BUILD_DIR/menubar_dist"

PYTHON="$(which python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "python3 not found in PATH"
  exit 1
fi

echo "Using python: $PYTHON"

mkdir -p "$BUILD_DIR"
rm -rf "$AGENT_DIST" "$MENUBAR_DIST"

echo "Installing build dependencies (pyinstaller, PyQt6)..."
"$PYTHON" -m pip install --user --upgrade pyinstaller PyQt6 || true

echo "Building agent (pyinstaller)..."
mkdir -p "$AGENT_DIST"
"$PYTHON" -m PyInstaller --onefile --name opencode-agent \
  --distpath "$AGENT_DIST" "$AGENT_DIR/agent/__main__.py"

AGENT_BIN="$AGENT_DIST/opencode-agent"
if [ ! -f "$AGENT_BIN" ]; then
  echo "Agent binary not found at $AGENT_BIN"
  exit 1
fi

echo "Building menubar app (pyinstaller using spec) and creating .app bundle..."

# Build menubar app with PyInstaller (which creates the complete .app bundle via BUNDLE)
cd "$MENUBAR_DIR"
# Ensure previous build output won't block PyInstaller
rm -rf "$MENUBAR_DIR/dist" "$MENUBAR_DIR/build" || true
"$PYTHON" -m PyInstaller -y --clean opencode-menubar.spec

# PyInstaller's BUNDLE should have created the .app
APP_BUNDLE="$MENUBAR_DIR/dist/OpenCode Token Meter.app"

# Verify the .app was created by PyInstaller
if [ ! -d "$APP_BUNDLE" ]; then
  echo "ERROR: .app bundle not created by PyInstaller at $APP_BUNDLE"
  echo "Check opencode-menubar.spec BUNDLE configuration"
  ls -la "$MENUBAR_DIR/dist/"
  exit 1
fi

echo "PyInstaller created .app bundle at: $APP_BUNDLE"

# Copy agent binary into the .app bundle's Resources/bin
mkdir -p "$APP_BUNDLE/Contents/Resources/bin"
cp "$AGENT_BIN" "$APP_BUNDLE/Contents/Resources/bin/opencode-agent"
chmod 755 "$APP_BUNDLE/Contents/Resources/bin/opencode-agent"
echo "Agent binary copied to bundle"

# Cleanup unnecessary Qt frameworks to reduce bundle size
echo ""
echo "Cleaning up unnecessary Qt frameworks..."
CLEANUP_SCRIPT="$MENUBAR_DIR/cleanup-bundle.sh"
if [ -f "$CLEANUP_SCRIPT" ]; then
  bash "$CLEANUP_SCRIPT" "$APP_BUNDLE"
else
  echo "Warning: cleanup-bundle.sh not found, skipping cleanup"
fi

# Show final app size
echo ""
echo "Final app bundle size:"
du -sh "$APP_BUNDLE"

cd "$ROOT_DIR"

# Create DMG installer
DMG_SCRIPT="$ROOT_DIR/create_dmg.sh"
if [ -f "$DMG_SCRIPT" ]; then
  echo ""
  echo "Creating DMG installer..."
  bash "$DMG_SCRIPT"
else
  echo "Warning: create_dmg.sh not found, skipping DMG creation"
fi

echo "Build complete. Artifacts in: $BUILD_DIR and $MENUBAR_DIR/dist"
exit 0
