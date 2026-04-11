#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ROOT_DIR/build"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   OpenCode Token Meter Build Script    ${NC}"
echo -e "${BLUE}========================================${NC}"

PYTHON="/Users/chwong/miniforge3/envs/opencode/bin/python"
if [ ! -f "$PYTHON" ]; then
  PYTHON="$(which python3 || true)"
fi

if [ -z "$PYTHON" ]; then
  echo "Error: python3 not found in PATH"
  exit 1
fi

echo -e " - Python: ${GREEN}$PYTHON${NC}"

# Install dependencies
echo -e "\n${BLUE}[1/4] Checking dependencies...${NC}"
"$PYTHON" -m pip install --quiet --user --upgrade pyinstaller pywebview pystray pillow pyperclip rumps pyobjc-framework-Cocoa 2>/dev/null || true
echo -e " - Dependencies OK"

# Clean previous builds
echo -e "\n${BLUE}[2/4] Cleaning previous builds...${NC}"
rm -rf "$BUILD_DIR" dist build
echo -e " - Cleaned"

# Build using unified spec file
echo -e "\n${BLUE}[3/4] Building application...${NC}"
cd "$ROOT_DIR"

# Run PyInstaller in background and show spinner
TEMP_LOG=$(mktemp)
"$PYTHON" -m PyInstaller --clean --noconfirm --log-level=ERROR OpenCodeTokenMeter.spec > "$TEMP_LOG" 2>&1 &
PID=$!

# Spinner
SPIN_CHARS='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
i=0
while kill -0 $PID 2>/dev/null; do
  i=$(( (i+1) % ${#SPIN_CHARS} ))
  printf "\r - Building... ${YELLOW}${SPIN_CHARS:$i:1}${NC} "
  sleep 0.1
done
wait $PID
BUILD_EXIT=$?
printf "\r"

if [ $BUILD_EXIT -ne 0 ]; then
  echo -e " - ${YELLOW}Build log:${NC}"
  cat "$TEMP_LOG" | sed 's/^[0-9]* INFO:/   -/g' | head -20
  rm -f "$TEMP_LOG"
  echo "ERROR: Build failed"
  exit 1
fi

# Show key info from log
grep "^[0-9]* INFO:" "$TEMP_LOG" | sed 's/^[0-9]* INFO:/ -/g' | head -4
rm -f "$TEMP_LOG"

# Verify the .app was created
APP_BUNDLE="$ROOT_DIR/dist/OpenCode Token Meter.app"
if [ ! -d "$APP_BUNDLE" ]; then
  echo "ERROR: .app bundle not created"
  exit 1
fi

APP_SIZE=$(du -sh "$APP_BUNDLE" | cut -f1 | xargs)
echo -e " - App Bundle: ${GREEN}${APP_SIZE}${NC}"

# Create DMG installer (optional)
DMG_SCRIPT="$ROOT_DIR/create_dmg.sh"
if [ -f "$DMG_SCRIPT" ]; then
  echo -e "\n${BLUE}[4/4] Creating DMG installer...${NC}"
  
  # Run DMG creation in background
  TEMP_DMG_LOG=$(mktemp)
  bash "$DMG_SCRIPT" > "$TEMP_DMG_LOG" 2>&1 &
  DMG_PID=$!

  # Spinner
  SPIN_CHARS='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  j=0
  while kill -0 $DMG_PID 2>/dev/null; do
    j=$(( (j+1) % ${#SPIN_CHARS} ))
    printf "\r - Creating DMG... ${YELLOW}${SPIN_CHARS:$j:1}${NC} "
    sleep 0.1
  done
  wait $DMG_PID
  DMG_EXIT=$?
  printf "\r"

  if [ $DMG_EXIT -ne 0 ]; then
    echo -e " - ${YELLOW}DMG creation failed:${NC}"
    head -20 "$TEMP_DMG_LOG"
    rm -f "$TEMP_DMG_LOG"
    exit 1
  fi
  
  DMG_OUTPUT=$(cat "$TEMP_DMG_LOG")
  rm -f "$TEMP_DMG_LOG"
  DMG_PATH=$(echo "$DMG_OUTPUT" | grep "created:" | tail -1 | sed 's/.*created: //')
  
  if [ -n "$DMG_PATH" ] && [ -f "$DMG_PATH" ]; then
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1 | xargs)
    echo -e " - DMG: ${GREEN}${DMG_SIZE}${NC}"
  else
    echo -e " - DMG created"
  fi
else
  echo -e "\n${BLUE}[4/4] Skipping DMG (script not found)${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}           Build Complete!              ${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e " App:  ${GREEN}${APP_SIZE}${NC} → dist/OpenCode Token Meter.app"
if [ -n "${DMG_PATH:-}" ] && [ -f "$DMG_PATH" ]; then
  echo -e " DMG:  ${GREEN}${DMG_SIZE}${NC} → $(basename "$DMG_PATH")"
fi
exit 0
