#!/bin/bash
# Create DMG installer for OpenCode Token Meter

set -e

APP_NAME="OpenCode Token Meter"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="OpenCodeTokenMeter-1.1.0"
DMG_PATH="build/${DMG_NAME}.dmg"
VOLUME_NAME="OpenCode Token Meter"
TMP_DMG="build/tmp.dmg"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: App bundle not found at $APP_PATH"
    exit 1
fi

# Create build directory
mkdir -p build

# Remove old DMG if exists
rm -f "$DMG_PATH" "$TMP_DMG"

# Create temporary DMG
echo " - Creating temporary DMG..."
hdiutil create -size 200m -fs HFS+ -volname "$VOLUME_NAME" "$TMP_DMG" -ov -quiet

# Mount the DMG with read-write access
echo " - Mounting..."
MOUNT_INFO=$(hdiutil attach "$TMP_DMG" -readwrite -noverify -noautoopen 2>/dev/null)
MOUNT_DIR=$(echo "$MOUNT_INFO" | grep "/Volumes" | sed 's/.*\(\/Volumes\/.*\)/\1/')

if [ -z "$MOUNT_DIR" ]; then
    echo "Error: Failed to mount DMG"
    exit 1
fi

# Wait for mount to complete
sleep 2

# Copy app to DMG
echo " - Copying app..."
cp -R "$APP_PATH" "$MOUNT_DIR/" 2>/dev/null || { echo "Copy failed"; hdiutil detach "$MOUNT_DIR" -quiet; exit 1; }

# Create Applications symlink
echo " - Adding Applications link..."
ln -s /Applications "$MOUNT_DIR/Applications" 2>/dev/null || true

# Create a README
cat > "$MOUNT_DIR/README.txt" << 'EOREADME'
OpenCode Token Meter - Installation

1. Drag "OpenCode Token Meter.app" to the Applications folder
2. Launch the app from Applications  
3. The app will appear in your menubar

For more information, visit:
https://github.com/CHW0n9/OpenCode-Token-Meter
EOREADME

# Wait to ensure all writes complete
sleep 2

# Unmount
echo " - Compressing..."
hdiutil detach "$MOUNT_DIR" -quiet 2>/dev/null || hdiutil detach "$MOUNT_DIR" -force -quiet 2>/dev/null

# Convert to compressed DMG
hdiutil convert "$TMP_DMG" -format UDZO -o "$DMG_PATH" -ov -quiet

# Remove temporary DMG
rm -f "$TMP_DMG"

# Output for parent script to parse
echo "created: $DMG_PATH"
