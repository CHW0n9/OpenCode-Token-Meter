# Build Instructions for OpenCode Token Meter

## Unified Build System

This project uses a **single unified spec file** (`OpenCodeTokenMeter.spec`) with automatic platform detection for building on Windows and macOS.

---

## Quick Build

### Windows
```bash
.\build_windows.bat
```

### macOS
```bash
./build.sh
```

---

## What Gets Built

### Windows
- **Output**: `dist\OpenCodeTokenMeter.exe`
- **Type**: Single unified executable
- **Includes**: 
  - Menubar UI with system tray
  - **Embedded agent module** (runs in background thread)
  - Application icon
  - All dependencies (PyQt6, SQLite, etc.)
- **Size**: ~50-100MB

### macOS
- **Output**: `dist/OpenCode Token Meter.app`
- **Type**: Native .app bundle
- **Includes**:
  - Menubar UI
  - **Embedded agent module** (runs in background thread)
  - Application icon
  - All dependencies
  - **Size**: ~100-150MB (includes Qt frameworks)

---

## Key Features

### Embedded Agent (No Separate Process!)
✅ Agent runs as **background thread** inside the main app  
✅ **No need for separate agent executable**  
✅ Automatically starts when app launches  
✅ Faster startup (no subprocess overhead)  
✅ True single-file distribution  

### Platform-Specific Behavior
The unified spec file automatically:
- Detects the build platform
- Uses correct icon format (`.ico` for Windows, `.icns` for macOS)
- Configures platform-specific options
- Creates appropriate package format

---

## Build Files

### Root Directory
- **`OpenCodeTokenMeter.spec`** - Unified spec with platform detection ⭐
- `build_windows.bat` - Windows build script
- `build.sh` - macOS build script
- `clean_windows.bat` - Clean Windows artifacts

### No More Scattered Spec Files!
Previously there were multiple spec files in different directories. Now there's only **one** unified spec in the project root.

---

## Manual Build (Advanced)

### All Platforms
```bash
# From project root
python -m PyInstaller --clean OpenCodeTokenMeter.spec
```

### Clean Build
```bash
# Windows
.\clean_windows.bat
.\build_windows.bat

# macOS
rm -rf build dist
./build.sh
```

---

## How It Works

### Platform Detection in Spec
```python
import sys

IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'

if IS_WINDOWS:
    # Windows: Single EXE configuration
    exe = EXE(..., console=False, icon='AppIcon.ico')

elif IS_MACOS:
    # macOS: .app bundle configuration
    exe = EXE(...)
    app = BUNDLE(exe, ..., icon='AppIcon.icns')
```

### Embedded Agent Architecture
```python
# When PyInstaller bundle detected:
if getattr(sys, 'frozen', False):
    # Start agent in background thread
    import agent.uds_server
    thread = threading.Thread(target=agent.uds_server.main, daemon=True)
    thread.start()
```

**Benefits:**
- No separate agent process to manage
- Agent starts automatically with app
- Simpler deployment (one file instead of two)
- Faster communication (in-process)

---

## Troubleshooting

### Windows: Icon not showing
**Solution**: Icon is embedded during build. Check:
1. `App/menubar/resources/AppIcon.ico` exists
2. Rebuild with `.\build_windows.bat`
3. Icon shows in file properties after build

### Windows: "Agent not found"
**Solution**: With embedded agent, this shouldn't happen. If it does:
1. Check console output for "Found embedded agent module"
2. Verify agent module was included in bundle
3. Try clean rebuild: `.\clean_windows.bat` then `.\build_windows.bat`

### macOS: .app bundle not created
**Solution**: 
1. Ensure you're using unified spec: `./build.sh`
2. Check for build errors in output
3. Verify PyInstaller installed: `pip3 install pyinstaller`

### Build is slow
- **First build**: 2-5 minutes (PyQt6 compilation)
- **Subsequent builds**: 1-2 minutes
- Use `--clean` flag only when needed

### Exe/App is too large
- PyQt6 adds 40-50MB (required for UI)
- UPX compression enabled by default
- Can't reduce much without breaking functionality

---

## Development Mode

### Run without building
```bash
# Windows
cd App/menubar
python -m menubar

# macOS
cd App/menubar
python3 -m menubar
```

The app will auto-detect it's running from source and start agent appropriately.

---

## Dependencies

### Required
- Python 3.9+
- PyQt6
- PyInstaller

### Install
```bash
# Windows
pip install PyQt6 pyinstaller

# macOS
pip3 install PyQt6 pyinstaller
```

---

## Build Output Structure

### Windows
```
dist/
└── OpenCodeTokenMeter.exe   (single unified executable with embedded agent)
```

### macOS
```
dist/
└── OpenCode Token Meter.app/
    └── Contents/
        ├── MacOS/
        │   └── OpenCode Token Meter (main binary with embedded agent)
        └── Resources/
            └── (app resources and icon)
```

---

## Comparison: Old vs New

| Aspect | Old (Multi-Spec) | New (Unified) |
|--------|------------------|---------------|
| Spec files | 3+ scattered | 1 in root |
| Agent | Separate exe/binary | Embedded thread |
| Windows output | 2 exe files | 1 exe file |
| macOS output | .app + agent binary | .app with embedded |
| Startup time | Slower (subprocess) | Faster (thread) |
| Deployment | Multiple files | Single file |
| Maintenance | Complex | Simple |

---

## Platform-Specific Notes

### Windows
- Icon format: `.ico`
- No console window (`console=False`)
- Single file distribution
- Agent embedded as module

### macOS
- Icon format: `.icns`
- App bundle format
- `LSUIElement=True` (no Dock icon, system tray only)
- Agent embedded as module
- DMG installer optional

---

## Success Indicators

After successful build:

✅ **Windows**: 
- `dist\OpenCodeTokenMeter.exe` exists
- File size 50-100MB
- Icon visible in Windows Explorer
- No console window when running
- System tray icon appears

✅ **macOS**:
- `dist/OpenCode Token Meter.app` exists
- Can launch by double-clicking
- System tray/menu bar icon appears
- No Dock icon (LSUIElement)

