# AGENTS.md — Developer Guidance

This document codifies how to work with the **OpenCode Token Meter** codebase. It covers development, testing, and build requirements for both macOS and Windows.

---

## 1) Execution & Development Workflow

### Running in Development Mode

To run the application directly from source:

```bash
# macOS/Windows
python App/webview_ui/main_tray.py --debug
```

*Note: The tray application will automatically start the background agent and stats worker as threads.*

### Environment Requirements

- **Python**: 3.9+
- **Conda Environment**: Recommended to use the `opencode` environment.
- **Dependencies**:
  - `pip install pyinstaller pywebview pystray pillow pyperclip`
  - macOS specific: `pip install rumps pyobjc-framework-Cocoa`
  - Windows specific: `pip install win10toast`

---

## 2) Component Architecture

- **Agent**: Monitors `~/.local/share/opencode/storage/message/` (all platforms) for new JSON messages.
- **Stats Worker**: Periodically aggregates database data for the tray display.
- **Webview UI**: Frontend built with HTML/CSS/JS (Tailwind, Chart.js, Lato font), communicating with Python via a `JsApi` bridge.
- **Database**: Local SQLite database stored at:
  - macOS: `~/Library/Application Support/OpenCode Token Meter/index.db`
  - Windows: `%APPDATA%\OpenCode Token Meter\index.db`

---

## 3) Testing & Verification

### Manual GUI Checklist

Before releasing, verify the following:

1. **Startup**: App launches into the system tray/menubar.
2. **Webview**: Selecting "Show Dashboard" opens the UI window.
3. **Data**: Counters (In/Out/Cost) update correctly after message activity.
4. **Theme**: Verify dark mode aesthetics and high-weight (900) typography for headers/charts.
5. **Export**: Verify CSV/JSON export functionality from the Details page.

### Code Integrity

- **Syntax Check**: `python -m py_compile <path>`
- **Formatting**: Adhere to PEP 8. Headers and specific UI text use **Lato** with a font-weight of **900** for a premium look.

---

## 4) Build & Packaging

This repository uses a **unified spec file** (`OpenCodeTokenMeter.spec`) for all platforms.

- **Build Commands**:
  - macOS: `./build.sh` (produces `.app` and `.dmg`)
  - Windows: `.\build_windows.bat` (produces `.exe`)
- **Cleanup**: `rm -rf build/ dist/`

---

## 5) Contributor Guidelines

1. **SQL Safety**: Always use parameterized queries (`?`). Never use f-strings for SQL inputs.
2. **Deduplication**: Message counting must use the deduplication logic in `App/agent/agent/db.py`.
3. **Version Control**: Follow Semantic Versioning. Update `CHANGELOG.md` for every release.
