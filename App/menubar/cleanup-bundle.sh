#!/bin/bash
# Cleanup unnecessary Qt frameworks from the app bundle after PyInstaller build

set -e

APP_BUNDLE="$1"
if [ -z "$APP_BUNDLE" ]; then
    echo "Usage: $0 <path-to-app-bundle>"
    exit 1
fi

if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: App bundle not found at $APP_BUNDLE"
    exit 1
fi

echo "Cleaning up unnecessary Qt frameworks from $APP_BUNDLE..."

QT_LIB_DIR="$APP_BUNDLE/Contents/Frameworks/PyQt6/Qt6/lib"
if [ ! -d "$QT_LIB_DIR" ]; then
    echo "Warning: Qt6/lib directory not found, skipping cleanup"
    exit 0
fi

cd "$QT_LIB_DIR"

# List of frameworks to remove (we don't use them)
# NOTE: QtDBus is needed by QtGui, don't remove it
FRAMEWORKS_TO_REMOVE=(
    "QtNetwork.framework"
    "QtPdf.framework"
    "QtSvg.framework"
    "QtWebEngine.framework"
    "QtWebEngineCore.framework"
    "QtWebEngineWidgets.framework"
    "QtWebChannel.framework"
    "QtOpenGL.framework"
    "QtOpenGLWidgets.framework"
    "QtMultimedia.framework"
    "QtMultimediaWidgets.framework"
    "QtPrintSupport.framework"
    "QtQml.framework"
    "QtQuick.framework"
    "QtQuickWidgets.framework"
    "QtSql.framework"
    "QtTest.framework"
    "QtXml.framework"
    "Qt3D.framework"
    "QtBluetooth.framework"
    "QtDesigner.framework"
    "QtHelp.framework"
    "QtLocation.framework"
    "QtNfc.framework"
    "QtPositioning.framework"
    "QtRemoteObjects.framework"
    "QtSensors.framework"
    "QtSerialPort.framework"
    "QtTextToSpeech.framework"
)

REMOVED_COUNT=0
SAVED_SIZE=0

for framework in "${FRAMEWORKS_TO_REMOVE[@]}"; do
    if [ -d "$framework" ]; then
        # Calculate size before removal
        SIZE=$(du -sk "$framework" | cut -f1)
        echo "  Removing $framework ($(numfmt --to=iec-i --suffix=B ${SIZE}000 2>/dev/null || echo ${SIZE}K))"
        rm -rf "$framework"
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
        SAVED_SIZE=$((SAVED_SIZE + SIZE))
    fi
done

# Also check for orphaned plugin directories
PLUGINS_DIR="$APP_BUNDLE/Contents/Frameworks/PyQt6/Qt6/plugins"
if [ -d "$PLUGINS_DIR" ]; then
    cd "$PLUGINS_DIR"
    
    # Remove entire plugin directories we don't need
    for plugin_dir in webengineview sqldrivers printsupport; do
        if [ -d "$plugin_dir" ]; then
            SIZE=$(du -sk "$plugin_dir" | cut -f1 2>/dev/null || echo 0)
            if [ "$SIZE" -gt 0 ]; then
                echo "  Removing plugin dir: $plugin_dir ($(numfmt --to=iec-i --suffix=B ${SIZE}000 2>/dev/null || echo ${SIZE}K))"
                rm -rf "$plugin_dir"
                SAVED_SIZE=$((SAVED_SIZE + SIZE))
            fi
        fi
    done
    
    # Remove unused image format plugins (keep only PNG support)
    # We only need PNG for the menubar icon
    if [ -d "imageformats" ]; then
        cd imageformats
        for plugin in libqgif.dylib libqicns.dylib libqico.dylib libqjpeg.dylib libqmacheif.dylib libqmacjp2.dylib libqpdf.dylib libqsvg.dylib libqtga.dylib libqtiff.dylib libqwbmp.dylib libqwebp.dylib; do
            if [ -f "$plugin" ]; then
                SIZE=$(du -sk "$plugin" | cut -f1 2>/dev/null || echo 0)
                if [ "$SIZE" -gt 0 ]; then
                    echo "  Removing image plugin: $plugin ($(numfmt --to=iec-i --suffix=B ${SIZE}000 2>/dev/null || echo ${SIZE}K))"
                    rm -f "$plugin"
                    SAVED_SIZE=$((SAVED_SIZE + SIZE))
                fi
            fi
        done
        cd "$PLUGINS_DIR"
    fi
    
    # Remove unused platform plugins (keep only qcocoa for macOS)
    if [ -d "platforms" ]; then
        cd platforms
        for plugin in libqoffscreen.dylib libqminimal.dylib; do
            if [ -f "$plugin" ]; then
                SIZE=$(du -sk "$plugin" | cut -f1 2>/dev/null || echo 0)
                if [ "$SIZE" -gt 0 ]; then
                    echo "  Removing platform plugin: $plugin ($(numfmt --to=iec-i --suffix=B ${SIZE}000 2>/dev/null || echo ${SIZE}K))"
                    rm -f "$plugin"
                    SAVED_SIZE=$((SAVED_SIZE + SIZE))
                fi
            fi
        done
        cd "$PLUGINS_DIR"
    fi
    
    # Remove generic plugins (we don't use touch input)
    if [ -d "generic" ]; then
        SIZE=$(du -sk "generic" | cut -f1 2>/dev/null || echo 0)
        if [ "$SIZE" -gt 0 ]; then
            echo "  Removing generic plugins: $(numfmt --to=iec-i --suffix=B ${SIZE}000 2>/dev/null || echo ${SIZE}K)"
            rm -rf "generic"
            SAVED_SIZE=$((SAVED_SIZE + SIZE))
        fi
    fi
fi

echo ""
echo "Cleanup complete!"
echo "  Removed frameworks: $REMOVED_COUNT"
echo "  Space saved: $(numfmt --to=iec-i --suffix=B ${SAVED_SIZE}000 2>/dev/null || echo ${SAVED_SIZE}K)"
