# Windows Compatibility - Learnings

## Session: ses_3137c7df1ffeNxM14u1BpsTKps
## Started: 2026-03-14T14:04:52.146Z

### Platform Guardrails
- All Windows fixes MUST use explicit platform checks: `if platform.system() == "Windows"` or `if SYSTEM == "Windows"`
- macOS code paths MUST remain unchanged
- No new dependencies (psutil, etc.)
- No abstraction layers or utility classes for path resolution

### PyInstaller Behavior
- **onefile mode** (Windows): All bundled files extracted to `sys._MEIPASS` at runtime
- **onedir/bundle mode** (macOS): `sys._MEIPASS` is NOT set; files are in `Resources/` directory
- Web assets bundled at: `webview_ui/web` in spec
- Icon assets bundled at: `resources/` in spec

### File Locations
- `App/webview_ui/main.py` - `get_web_dir()` (lines 59-66)
- `App/webview_ui/backend/tray.py` - `get_icon_path()` (lines 46-86)
- `App/webview_ui/main_tray.py` - `_is_webview_running()` (lines 136-175)
- `App/agent/agent/config.py` - `MSG_ROOT` / `OPENCODE_DB_PATH` (lines 26-30)

### Windows Adaptation Folder
- Found `Windows Adaptation/` folder with previous Windows adaptation work
- Contains: `WINDOWS_ADAPTATION.md`, `create_registry.reg`, `set_shortcut_appid.py`, etc.
- This appears to be from a different architecture (PyQt6-based, not pywebview)
- Current codebase uses pywebview, not PyQt6
- Registry implementation mentioned in user interview was NOT found in git history
- Windows notifications already use `win10toast` in `api.py` — no registry work needed

### Task 1: get_web_dir() Fix (2026-03-14)
- Modified `App/webview_ui/main.py` lines 59-66
- Added `sys._MEIPASS` check for PyInstaller onefile builds (Windows)
- Logic: Check `sys._MEIPASS` first → return `os.path.join(meipass, "webview_ui", "web")`
- Fallback preserved: macOS Resources path unchanged
- Syntax verified: `python -m py_compile App/webview_ui/main.py` passes

### Task 3: get_icon_path() Fix (2026-03-14)
- Modified `App/webview_ui/backend/tray.py` lines 46-86
- Added `sys._MEIPASS` check for PyInstaller onefile builds (Windows)
- Logic: Check `sys._MEIPASS` first → return `os.path.join(meipass, "resources")`
- macOS .app bundle path unchanged: `os.path.join(os.path.dirname(sys.executable), "..", "Resources", "resources")`
- Onedir fallback preserved: `_internal/resources` → `resources`
- Dev mode path unchanged: `web/assets/`
- Syntax verified: `python -m py_compile App/webview_ui/backend/tray.py` passes

### Task 4: _is_webview_running() Fix (2026-03-14)
- Modified `App/webview_ui/main_tray.py` lines 136-175
- Added `platform.system() == "Windows"` check for process verification
- Windows: Uses `tasklist /FI "PID eq {pid}" /NH` to check process existence
- Unix/macOS: Preserved original `ps` command logic for process verification
- Basic `os.kill(pid, 0)` check preserved (works on all platforms)
- No new dependencies added (psutil not used)
- Syntax verified: `python -m py_compile App/webview_ui/main_tray.py` passes
