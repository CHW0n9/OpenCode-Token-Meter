# Essential Project Files

This document identifies which files in the project are necessary for the application to run and build, and which are redundant or safely removable.

## 🛠️ Essential Files (Keep)

### Application Core (`App/`)

- `App/agent/`: All files within the background agent package.
- `App/webview_ui/main.py`: Core logic for the webview window.
- `App/webview_ui/main_tray.py`: Main entry point for the tray + subprocess launcher.
- `App/webview_ui/stats_worker.py`: Background stats processor for the tray.
- `App/webview_ui/backend/`: All API and logic files.
- `App/webview_ui/web/`: All frontend assets (HTML, CSS, JS).

### Build System (Root)

- `build.sh`: macOS build script.
- `build_windows.bat`: Windows build script.
- `create_dmg.sh`: Required for macOS DMG creation.
- `OpenCodeTokenMeter.spec`: Unified PyInstaller configuration.
- `run_full_app.py`: Main launcher for running from source.

### Documentation & Legal (Root)

- `LICENSE`: GNU GPL v3.0 license.
- `README.md` & `README_CN.md`: User documentation.
- `CHANGELOG.md`: Version history.
- `PROJECT_ARCHITECTURE.md`: Technical overview.
- `PROJECT_SUMMARY.md`: Brief project description.
- `RELEASE_CHECKLIST.md`: Steps for releasing new versions.

---

## 🗑️ Redundant/Unnecessary Files (Safe to Remove)

These files are either outdated, development-only, or redundant backups.

### Outdated Documentation

- `Codex Planning.md`: Old design doc from early development.
- `MIGRATION_COMPLETE.md`: Documentation of the PyQt6 → pywebview migration.
- `BUILD_FILES_CHECKLIST.md`: Outdated file checklist.
- `APP/webview_ui/FUNCTIONS.md`: Likely redundant API documentation.

### Development & Legacy Scripts

- `debug_stats.py`: Used for debugging API outputs.
- `fix_window.sh`: Emergency fix script for old threading issues.
- `test_macos.sh`: Manual testing script.
- `test_migration.sh`: Old script for testing the migration process.
- `App/webview_ui/main_backup.py`: Backup of an older version.
- `App/webview_ui/main_rumps.py`: Legacy rumps-only version.
- `App/webview_ui/main_simple.py`: Simplified legacy version.

### App/webview_ui/backend/

- `test_appkit.py`: Emergency test script for macOS AppKit imports.
- `App/webview_ui/main_backup.py`: Backup of the main app.
