#!/bin/bash
# Create DMG installer for OpenCode Token Meter

set -e

APP_NAME="OpenCode Token Meter"
APP_PATH="App/menubar/dist/${APP_NAME}.app"
DMG_NAME="OpenCodeTokenMeter-1.0.0"
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
echo "Creating temporary DMG..."
hdiutil create -size 200m -fs HFS+ -volname "$VOLUME_NAME" "$TMP_DMG" -ov

# Mount the DMG with read-write access
echo "Mounting DMG..."
MOUNT_INFO=$(hdiutil attach "$TMP_DMG" -readwrite -noverify -noautoopen)
MOUNT_DIR=$(echo "$MOUNT_INFO" | grep "/Volumes" | sed 's/.*\(\/Volumes\/.*\)/\1/')

if [ -z "$MOUNT_DIR" ]; then
    echo "Error: Failed to mount DMG"
    exit 1
fi

echo "Mounted at: $MOUNT_DIR"

# Wait for mount to complete
sleep 2

# Copy app to DMG
echo "Copying app to DMG..."
cp -R "$APP_PATH" "$MOUNT_DIR/" || { echo "Copy failed"; hdiutil detach "$MOUNT_DIR"; exit 1; }

# Create Applications symlink
echo "Creating Applications symlink..."
ln -s /Applications "$MOUNT_DIR/Applications" || echo "Symlink creation failed (non-fatal)"

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
echo "Unmounting DMG..."
hdiutil detach "$MOUNT_DIR" || hdiutil detach "$MOUNT_DIR" -force

# Convert to compressed DMG
echo "Converting to compressed DMG..."
hdiutil convert "$TMP_DMG" -format UDZO -o "$DMG_PATH" -ov

# Remove temporary DMG
rm -f "$TMP_DMG"

echo ""
echo "✅ DMG created successfully!"
echo "   Location: $DMG_PATH"
ls -lh "$DMG_PATH"
