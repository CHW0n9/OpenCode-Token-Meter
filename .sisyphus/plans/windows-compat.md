# Windows Compatibility Fixes

## TL;DR

> **Quick Summary**: Fix all Windows-specific issues: blank webview, empty tray data, missing icons, `ps` command failure, and `is_failed` schema crash on existing databases.
>
> **Deliverables**:
> - `App/webview_ui/main.py` — `get_web_dir()` uses `sys._MEIPASS` on Windows frozen builds ✅ DONE
> - `App/webview_ui/backend/tray.py` — `get_icon_path()` uses `sys._MEIPASS` on Windows frozen builds ✅ DONE
> - `App/agent/agent/config.py` — `MSG_ROOT` / `OPENCODE_DB_PATH` verified correct for Windows ✅ DONE
> - `App/webview_ui/main_tray.py` — `_is_webview_running()` no longer calls Unix `ps` on Windows ✅ DONE
> - `App/agent/agent/db.py` — `idx_dedup_v2` index moved after `mark_failed_requests()` migration ← NEW
> - `App/webview_ui/backend/db_read.py` — `is_failed` filter conditional on column existence ← NEW
>
> **Estimated Effort**: Short (all changes are small, targeted, platform-guarded)
> **Parallel Execution**: YES — Tasks 6 and 7 can run in parallel
> **Critical Path**: Task 0 (validate) → Tasks 6+7 (schema fix) → Task 5 (QA)

---

## Context

### Original Request
User reported Windows compatibility issues:
1. Tray shows no data; webview window is a blank frame with no content
2. No icon in tray or app notifications

### Interview Summary
**Key Discussions**:
- User confirmed `index.db` is empty on Windows
- User mentioned "registry-based notification icon implementation" previously — investigation found **zero evidence of this in git history** (stash only contained binary/build artifacts, no Python source changes). The `winreg` API was never committed to this repo.
- Windows notifications currently use `win10toast` in `api.py` — this is the correct existing approach, no registry work is needed.
- User wants all Windows issues fixed together.

**Research Findings**:
- `config.py`: `BASE_DIR` → `%APPDATA%\OpenCode Token Meter` ✅ already correct for Windows
- `main.py:get_web_dir()`: frozen branch returns macOS `../Resources/` path — no Windows branch ❌
- `tray.py:get_icon_path()`: checks `_internal/resources/` and `resources/` next to exe — misses `sys._MEIPASS` for onefile builds ❌
- `config.py`: `MSG_ROOT` and `OPENCODE_DB_PATH` hardcoded to `~/.local/share/opencode/` — **unvalidated on Windows** ⚠️
- `main_tray.py:_is_webview_running()`: calls Unix `ps` subprocess — fails on Windows ❌
- PyInstaller spec: Windows uses **onefile** mode; all bundled files extracted to `sys._MEIPASS` at runtime
- Web assets bundled at `webview_ui/web` in spec; icon at `resources/` — both should appear under `sys._MEIPASS`

### Metis Review
**Identified Gaps (addressed)**:
- OpenCode Windows data path is an **unvalidated assumption** — plan includes Task 0 to verify before making changes
- `sys._MEIPASS` is the correct mechanism for onefile PyInstaller builds on Windows — incorporated into all resource path fixes
- Guardrails added: no new dependencies, no macOS path changes, no abstraction layers, no multiple fallbacks

---

## Work Objectives

### Core Objective
Fix all 4 Windows-specific runtime failures so the packaged Windows EXE shows the webview UI, populates tray data, displays the app icon, and runs process management without errors.

### Concrete Deliverables
- `App/webview_ui/main.py` — modified `get_web_dir()`
- `App/webview_ui/backend/tray.py` — modified `get_icon_path()`
- `App/agent/agent/config.py` — corrected `MSG_ROOT` / `OPENCODE_DB_PATH` (if needed after validation)
- `App/webview_ui/main_tray.py` — patched `_is_webview_running()`

### Definition of Done
- [ ] `python -c "import sys; sys._MEIPASS_test = True"` type check passes in frozen context (conceptual — each fix is verified by running path resolution test)
- [ ] `get_web_dir()` returns a path ending in `webview_ui/web` or `web` that contains `index.html`
- [ ] `get_icon_path()` returns a path ending in `AppIcon.ico` that exists
- [ ] `_is_webview_running()` does not call `ps` on Windows; returns True/False without exception
- [ ] After fix, webview loads content (not `about:blank`) on Windows EXE

### Must Have
- `sys._MEIPASS` used for resource lookup in frozen Windows builds
- Explicit `if SYSTEM == "Windows":` or `if platform.system() == "Windows":` guards — no implicit platform assumptions
- macOS code paths remain unchanged
- No new pip dependencies

### Must NOT Have (Guardrails)
- ❌ No `psutil` dependency — use `tasklist` or `os.kill` equivalent
- ❌ No changes to macOS `get_web_dir()` or macOS `get_icon_path()` logic
- ❌ No path-searching fallback chains (try path A, B, C...) — one correct path per platform
- ❌ No `PathResolver` utility class or abstraction layers
- ❌ No environment variable overrides for paths
- ❌ No changes to PyInstaller spec (unless web assets genuinely missing from bundle)
- ❌ No `winreg` / Windows Registry code — notifications already work via `win10toast`
- ❌ No Linux / "other platform" fixes while we're at it

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO (no test framework in project)
- **Automated tests**: NONE
- **Framework**: none
- **Agent-Executed QA**: YES (mandatory) — via Bash/PowerShell commands on Windows machine

### Agent-Executed QA Scenarios (Mandatory)

**Verification Tool**: Bash (PowerShell on Windows machine)

**All verification must be run on a Windows machine with the packaged EXE.**

#### For Task 0 (Path Validation — Blocking)
```
Scenario: Confirm OpenCode data path on Windows
  Tool: Bash (PowerShell)
  Steps:
    1. Test-Path "$env:USERPROFILE\.local\share\opencode\opencode.db"
    2. Test-Path "$env:APPDATA\opencode\opencode.db"
    3. Test-Path "$env:LOCALAPPDATA\opencode\opencode.db"
    4. Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "opencode.db" -ErrorAction SilentlyContinue | Select-Object FullName
  Expected Result: Exactly one path returns True; record it — this is the correct OPENCODE_DB_PATH
  Evidence: Record output in .sisyphus/evidence/windows-opencode-path.txt
```

#### For Task 1 (get_web_dir fix)
```
Scenario: Webview loads content on Windows frozen EXE
  Tool: Bash (PowerShell)
  Preconditions: App built with build_windows.bat; EXE launched
  Steps:
    1. In Python (frozen context simulation — run in installed EXE):
       python -c "import sys; sys.frozen = True; sys._MEIPASS = r'C:\path\to\_MEIPASS'; exec(open('App/webview_ui/main.py').read()); print(get_web_dir())"
    2. Assert: returned path ends with 'webview_ui\web' or 'web'
    3. Assert: os.path.exists(os.path.join(get_web_dir(), 'index.html')) == True
    4. Launch EXE and verify window title "OpenCode Token Meter" appears with content
  Expected Result: index.html found; no "[ERROR] index.html not found" in stdout
  Evidence: .sisyphus/evidence/task1-webview-load.txt (copy EXE stdout log)
```

#### For Task 2 (config.py paths)
```
Scenario: Scanner finds OpenCode data on Windows
  Tool: Bash (PowerShell)
  Preconditions: OpenCode installed and has been used (opencode.db exists)
  Steps:
    1. python -c "from App.agent.agent.config import OPENCODE_DB_PATH, MSG_ROOT; import os; print('DB:', OPENCODE_DB_PATH, 'exists:', os.path.exists(OPENCODE_DB_PATH)); print('MSG:', MSG_ROOT, 'exists:', os.path.isdir(MSG_ROOT))"
    2. Assert: 'DB: ... exists: True'
  Expected Result: Both paths exist and are accessible
  Evidence: .sisyphus/evidence/task2-paths.txt
```

#### For Task 3 (icon fix)
```
Scenario: Tray icon shows AppIcon.ico (not blue square) on Windows
  Tool: Bash (PowerShell)
  Preconditions: EXE built and launched
  Steps:
    1. python -c "import sys; sys.frozen = True; sys._MEIPASS = r'<actual_meipass>'; from App.webview_ui.backend.tray import TrayManager; t = TrayManager(); p = t.get_icon_path(); import os; print(p, os.path.exists(p))"
    2. Assert: path ends with 'AppIcon.ico'
    3. Assert: os.path.exists(path) == True
  Expected Result: Icon path valid and file exists
  Evidence: .sisyphus/evidence/task3-icon-path.txt

Scenario: No blue square fallback icon
  Tool: Bash (PowerShell)
  Steps:
    1. Confirm TrayManager.create_icon() opens file (not Image.new fallback)
    2. Assert: No "blue" color in the 10x10 pixel center sample of returned image
  Expected Result: Real icon loaded
  Evidence: .sisyphus/evidence/task3-no-fallback.txt
```

#### For Task 4 (ps command fix)
```
Scenario: _is_webview_running() runs without exception on Windows
  Tool: Bash (PowerShell)
  Steps:
    1. python -c "import sys; sys.platform = 'win32'; import platform; platform.system = lambda: 'Windows'; from App.webview_ui.main_tray import TrayAppWithSubprocess; a = TrayAppWithSubprocess.__new__(TrayAppWithSubprocess); a._webview_pid = 99999; result = a._is_webview_running(); print('Result:', result)"
    2. Assert: No FileNotFoundError or CalledProcessError
    3. Assert: Result is True or False (not exception)
  Expected Result: Function returns bool, no ps-related error
  Evidence: .sisyphus/evidence/task4-ps-fix.txt
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — Blocking):
└── Task 0: Validate OpenCode Windows data path (MUST complete first) ✅ DONE

Wave 2 (After Task 0 — All Parallel) ✅ DONE:
├── Task 1: Fix get_web_dir() in main.py ✅
├── Task 2: Fix config.py MSG_ROOT / OPENCODE_DB_PATH ✅
├── Task 3: Fix get_icon_path() in tray.py ✅
└── Task 4: Fix _is_webview_running() in main_tray.py ✅

Wave 3 (Newly discovered after Windows dev-mode test — Both Parallel):
├── Task 6: Fix db.py — move idx_dedup_v2 index after mark_failed_requests()
└── Task 7: Fix db_read.py — make is_failed filter conditional on column existence

Wave 4 (After Wave 3 — Integration):
└── Task 5: Rebuild Windows EXE and run all QA scenarios end-to-end

Critical Path: Task 0 → Tasks 6+7 → Task 5
Parallel Speedup: Tasks 6 and 7 can run simultaneously
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|-----------|--------|---------------------|
| 0 | None | 2 | None (must complete first) |
| 1 | None (but start after 0) | 5 | 3, 4 |
| 2 | 0 (needs path result) | 5 | 1, 3, 4 |
| 3 | None (but start after 0) | 5 | 1, 2, 4 |
| 4 | None (but start after 0) | 5 | 1, 2, 3 |
| 6 | None (can start now) | 5 | 7 |
| 7 | None (can start now) | 5 | 6 |
| 5 | 1, 2, 3, 4, 6, 7 | None | None (final) |

---

## TODOs

---

- [ ] 0. Validate OpenCode Windows data path (BLOCKING — run before all other tasks)

  **What to do**:
  - On the Windows machine where OpenCode is installed, run the following PowerShell commands and record output:
    ```powershell
    Test-Path "$env:USERPROFILE\.local\share\opencode\opencode.db"
    Test-Path "$env:APPDATA\opencode\opencode.db"
    Test-Path "$env:LOCALAPPDATA\opencode\opencode.db"
    Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "opencode.db" -ErrorAction SilentlyContinue | Select-Object FullName
    ```
  - Record which path returns `True` — that is the correct `OPENCODE_DB_PATH` for Windows
  - Similarly, check for `storage\message` directory:
    ```powershell
    Test-Path "$env:USERPROFILE\.local\share\opencode\storage\message"
    Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "message" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.FullName -like "*opencode*" } | Select-Object FullName
    ```
  - Record the result — it determines whether Task 2 needs code changes at all

  **Must NOT do**:
  - Do NOT modify any files in this task
  - Do NOT assume the path — validate empirically

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure investigation/validation, no implementation
  - **Skills**: none required (just run PowerShell commands and report)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (blocking)
  - **Blocks**: Task 2 (depends on the validated path)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `App/agent/agent/config.py:26-30` — current hardcoded paths for context
  - Code comment: "OpenCode uses .local/share on all platforms including Windows" — to verify or disprove

  **Acceptance Criteria**:
  - [ ] PowerShell commands run and output recorded in `.sisyphus/evidence/windows-opencode-path.txt`
  - [ ] Correct `OPENCODE_DB_PATH` value identified (exact full path on Windows)
  - [ ] Correct `MSG_ROOT` value identified (exact full path on Windows)
  - [ ] Decision recorded: "config.py needs change: YES/NO"

  **Commit**: NO (investigation only)

---

- [ ] 1. Fix `get_web_dir()` in `main.py` — Windows frozen resource path

  **What to do**:
  - File: `App/webview_ui/main.py`, function `get_web_dir()` (lines 59-66)
  - Current frozen branch only handles macOS `../Resources/webview_ui/web` path
  - Add Windows frozen branch using `sys._MEIPASS`:
    ```python
    def get_web_dir():
        """Get the web directory path"""
        if getattr(sys, 'frozen', False):
            # PyInstaller: sys._MEIPASS is the extraction temp dir (onefile)
            meipass = getattr(sys, '_MEIPASS', None)
            if meipass:
                # Onefile build (Windows/Linux): assets extracted to _MEIPASS
                return os.path.join(meipass, "webview_ui", "web")
            # macOS .app bundle (onedir): Resources layout
            return os.path.join(os.path.dirname(sys.executable), "..", "Resources", "webview_ui", "web")
        return os.path.join(os.path.dirname(__file__), "web")
    ```
  - Rationale: PyInstaller onefile extracts all bundled files to `sys._MEIPASS` at runtime; the spec bundles web assets at `webview_ui/web` (confirmed in OpenCodeTokenMeter.spec)
  - macOS uses COLLECT/BUNDLE (onedir), so macOS will have `sys.frozen = True` but `sys._MEIPASS` will NOT be set → falls through to macOS Resources path — behavior preserved

  **Must NOT do**:
  - Do NOT change the macOS Resources path fallback
  - Do NOT add path searching (try multiple paths)
  - Do NOT modify `create_window()` or any other function

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single function, ~5 line change, clear spec
  - **Skills**: none required
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI changes

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3, 4)
  - **Blocks**: Task 5
  - **Blocked By**: Task 0 (start after Task 0 completes, even though not technically dependent)

  **References**:
  - `App/webview_ui/main.py:59-66` — current `get_web_dir()` to modify
  - `App/webview_ui/main.py:69-97` — `create_window()` for context (do NOT modify)
  - `OpenCodeTokenMeter.spec` — confirms web assets bundled at `webview_ui/web`: look for `(web_dir, 'webview_ui/web')` datas entry
  - PyInstaller docs: `sys._MEIPASS` is only set in onefile mode, not onedir/bundle mode

  **Acceptance Criteria**:
  - [ ] `get_web_dir()` modified as above
  - [ ] `python -m py_compile App/webview_ui/main.py` → no syntax errors
  - [ ] Manual test (frozen Windows): launch EXE, stdout shows `[INFO] Loading URL: file://...index.html` (not `[ERROR] index.html not found`)
  - [ ] `about:blank` no longer appears in webview on Windows EXE

  **Commit**: YES (groups with Tasks 3, 4 in Wave 2)
  - Message: `fix(windows): use sys._MEIPASS for resource paths in frozen builds`
  - Files: `App/webview_ui/main.py`
  - Pre-commit: `python -m py_compile App/webview_ui/main.py`

---

- [ ] 2. Fix `MSG_ROOT` / `OPENCODE_DB_PATH` in `config.py` — Windows OpenCode data path

  **What to do**:
  - **PREREQUISITE**: Task 0 must be completed first — this task uses the validated path
  - File: `App/agent/agent/config.py` (lines 26-30)
  - Current code:
    ```python
    # Message storage root - OpenCode uses .local/share on all platforms including Windows
    MSG_ROOT = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "storage", "message")
    OPENCODE_DB_PATH = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db")
    ```
  - **If Task 0 confirms `~/.local/share/opencode/` IS correct on Windows**: No code change needed. Update comment only to remove misleading "including Windows" implication.
  - **If Task 0 reveals a different path** (e.g., `%APPDATA%\opencode\`): Add a Windows-specific branch:
    ```python
    if SYSTEM == "Windows":
        _opencode_base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "opencode")
        MSG_ROOT = os.path.join(_opencode_base, "storage", "message")
        OPENCODE_DB_PATH = os.path.join(_opencode_base, "opencode.db")
    else:
        MSG_ROOT = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "storage", "message")
        OPENCODE_DB_PATH = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db")
    ```
  - Use the exact path found in Task 0 — not a guess

  **Must NOT do**:
  - Do NOT add multiple fallback paths (try `%APPDATA%`, then `%LOCALAPPDATA%`, then `~/.local/share`)
  - Do NOT add environment variable overrides for path configuration
  - Do NOT change any other config values
  - Do NOT modify `BASE_DIR` or `DB_PATH` (already correct for Windows)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small targeted change; exact content depends on Task 0 result
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: NO (must wait for Task 0 result)
  - **Parallel Group**: Wave 2 (but Task 0 must complete first)
  - **Blocks**: Task 5
  - **Blocked By**: Task 0

  **References**:
  - `App/agent/agent/config.py:26-30` — lines to modify
  - `App/agent/agent/config.py:11-18` — `BASE_DIR` Windows logic pattern to follow (use same `SYSTEM == "Windows"` branching style)
  - `App/agent/agent/scanner.py` — `_sync_from_opencode_db()` and `scan_once()` for context; they use `OPENCODE_DB_PATH` and `MSG_ROOT` directly from config

  **Acceptance Criteria**:
  - [ ] `python -m py_compile App/agent/agent/config.py` → no syntax errors
  - [ ] On Windows: `python -c "from App.agent.agent.config import OPENCODE_DB_PATH, MSG_ROOT; import os; print(os.path.exists(OPENCODE_DB_PATH))"` → `True`
  - [ ] Scanner logs show "Scanning messages from MSG_ROOT" rather than "MSG_ROOT not found" after fix

  **Commit**: YES (with Task 2 commit)
  - Message: `fix(windows): correct OpenCode data paths for Windows`
  - Files: `App/agent/agent/config.py`
  - Pre-commit: `python -m py_compile App/agent/agent/config.py`

---

- [ ] 3. Fix `get_icon_path()` in `tray.py` — Windows frozen icon resource path

  **What to do**:
  - File: `App/webview_ui/backend/tray.py`, function `get_icon_path()` (lines 46-86)
  - Current frozen Windows/Linux branch checks `exe_dir/_internal/resources/` and `exe_dir/resources/` — neither exists for onefile builds (files are in `sys._MEIPASS`)
  - Replace Windows frozen branch to check `sys._MEIPASS` first:
    ```python
    def get_icon_path(self):
        import sys
        system = platform.system()

        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', None)
            if meipass:
                # Onefile build (Windows/Linux): extracted to _MEIPASS
                resources_dir = os.path.join(meipass, "resources")
            elif system == "Darwin":
                # macOS .app bundle
                resources_dir = os.path.join(os.path.dirname(sys.executable), "..", "Resources", "resources")
            else:
                # Onedir fallback (unlikely but safe)
                exe_dir = os.path.dirname(sys.executable)
                resources_dir = os.path.join(exe_dir, "_internal", "resources")
                if not os.path.exists(resources_dir):
                    resources_dir = os.path.join(exe_dir, "resources")
        else:
            # Dev mode
            base_dir = os.path.dirname(os.path.dirname(__file__))
            resources_dir = os.path.join(base_dir, "web", "assets")

        if system == "Darwin":
            path = os.path.join(resources_dir, "icon_template@2x.png")
            if not os.path.exists(path):
                path = os.path.join(resources_dir, "icon_template.png")
            return path

        if system == "Windows":
            return os.path.join(resources_dir, "AppIcon.ico")

        return os.path.join(resources_dir, "AppIcon.png")
    ```
  - Verify in `OpenCodeTokenMeter.spec` that `AppIcon.ico` is bundled at `resources/AppIcon.ico` (look for `resources_dir, 'resources'` datas entry). If the spec bundles it elsewhere, adjust the path accordingly.

  **Must NOT do**:
  - Do NOT change macOS icon logic (template PNG at `resources_dir`)
  - Do NOT change dev mode path (`web/assets/`)
  - Do NOT add Linux-specific fixes beyond what's already handled

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single function, clear pattern to follow from Task 1
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 1, 2, 4)
  - **Blocks**: Task 5
  - **Blocked By**: None (but start after Task 0 completes)

  **References**:
  - `App/webview_ui/backend/tray.py:46-86` — `get_icon_path()` to modify
  - `App/webview_ui/backend/tray.py:88-92` — `create_icon()` for context (do NOT modify; uses `get_icon_path()` result)
  - `OpenCodeTokenMeter.spec` — confirms icon bundled at `resources/` directory: look for `(resources_dir, 'resources')` datas entry
  - `App/webview_ui/web/assets/AppIcon.ico` — source icon file (already exists in repo)
  - Task 1 fix for `get_web_dir()` — follow same `sys._MEIPASS` pattern

  **Acceptance Criteria**:
  - [ ] `python -m py_compile App/webview_ui/backend/tray.py` → no syntax errors
  - [ ] On Windows frozen EXE: `TrayManager().get_icon_path()` returns path ending in `AppIcon.ico` and `os.path.exists()` returns `True`
  - [ ] Tray shows actual app icon (not a blue square) when EXE is launched
  - [ ] No `[Tray] Failed to start:` error in stdout

  **Commit**: YES (group with Tasks 1, 4)
  - Message: `fix(windows): use sys._MEIPASS for resource paths in frozen builds`
  - Files: `App/webview_ui/backend/tray.py`
  - Pre-commit: `python -m py_compile App/webview_ui/backend/tray.py`

---

- [ ] 4. Fix `_is_webview_running()` in `main_tray.py` — remove Unix `ps` command

  **What to do**:
  - File: `App/webview_ui/main_tray.py`, function `_is_webview_running()` (approximately lines 152-170)
  - Find the section that calls `subprocess.run(["ps", "-p", pid, "-o", "command="])` and guard it with a platform check
  - Replace Windows path with `tasklist /FI "PID eq {pid}"`:
    ```python
    def _is_webview_running(self):
        """Check if the webview subprocess is still running"""
        if self._webview_pid is None:
            return False
        try:
            import platform
            if platform.system() == "Windows":
                # Windows: use tasklist to check process existence
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {self._webview_pid}", "/NH"],
                    capture_output=True, text=True
                )
                return str(self._webview_pid) in result.stdout
            else:
                # Unix: use os.kill(pid, 0) to check existence
                os.kill(self._webview_pid, 0)
                return True
        except (OSError, subprocess.SubprocessError):
            return False
    ```
  - IMPORTANT: Read the actual current implementation of `_is_webview_running()` before editing to understand the full existing logic — only change the `ps`-specific part, preserve other logic
  - Note: if the function currently already has a fallback to `os.kill`, that part can remain

  **Must NOT do**:
  - Do NOT add `psutil` as a new dependency
  - Do NOT change macOS/Linux behavior (keep `os.kill` or `ps` for Unix)
  - Do NOT refactor the entire function — minimal targeted fix only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small platform-guarded change to one function
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 1, 2, 3)
  - **Blocks**: Task 5
  - **Blocked By**: None (but start after Task 0 completes)

  **References**:
  - `App/webview_ui/main_tray.py:152-170` (approximate) — `_is_webview_running()` current implementation to read carefully before modifying
  - `App/webview_ui/main_tray.py` — check for `_webview_pid` attribute definition and how `_is_webview_running` is called (context)
  - Existing platform pattern in `main_tray.py` — look for other `if platform.system() == "Windows":` branches to follow style

  **Acceptance Criteria**:
  - [ ] `python -m py_compile App/webview_ui/main_tray.py` → no syntax errors
  - [ ] On Windows: `_is_webview_running()` with a non-existent PID (99999) returns `False` without raising any exception
  - [ ] No `FileNotFoundError: [WinError 2] The system cannot find the file specified` error when method is called

  **Commit**: YES (group with Tasks 1, 3)
  - Message: `fix(windows): use sys._MEIPASS for resource paths in frozen builds`
  - Files: `App/webview_ui/main_tray.py`
  - Pre-commit: `python -m py_compile App/webview_ui/main_tray.py`

---

- [x] 6. Fix `is_failed` schema: move `idx_dedup_v2` index creation after migration in `db.py`

  **Status**: DISCOVERED during Windows dev-mode testing (error_log.txt). Root cause: on a pre-existing DB that lacks the `is_failed` column, `init_db()` runs `executescript()` which tries to `CREATE INDEX idx_dedup_v2 ON messages(..., is_failed)` — this fails immediately because the column doesn't exist yet. The `ALTER TABLE` migration in `mark_failed_requests()` runs *after* `executescript`, too late.

  **What to do**:
  - In `App/agent/agent/db.py`, inside `init_db()`:
    1. **Remove** the `idx_dedup_v2` line from inside the `executescript("""...""")` block (delete this line):
       ```sql
       CREATE INDEX IF NOT EXISTS idx_dedup_v2 ON messages(ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id, is_failed);
       ```
    2. **After** the calls to `migrate_fix_roles()` and `mark_failed_requests()` (which ensure `is_failed` column exists), add the index creation as a separate `c.execute(...)` call:
       ```python
       c.execute("""
       CREATE INDEX IF NOT EXISTS idx_dedup_v2
       ON messages(ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id, is_failed)
       """)
       conn.commit()
       ```
    3. Keep everything else in `init_db()` identical.

  **Why this works**: `CREATE TABLE IF NOT EXISTS` is a no-op on an existing DB (column not added). The index creation then fails because `is_failed` doesn't exist. By moving it after `mark_failed_requests()`, we guarantee the column is present before the index is built.

  **Must NOT do**:
  - Do NOT change any logic in `mark_failed_requests()` or `migrate_fix_roles()`
  - Do NOT change the index definition itself (columns are correct)
  - Do NOT touch any macOS code paths

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Tiny surgical change — remove one line from one block, add three lines after
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 7)
  - **Parallel Group**: Wave (new) — Tasks 6 and 7 can run in parallel
  - **Blocks**: Task 5 (rebuild + QA)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `App/agent/agent/db.py:46-92` — `init_db()` function, full body
  - `App/agent/agent/db.py:602-659` — `mark_failed_requests()` — the migration that adds `is_failed`
  - `error_log.txt:8` — `Agent thread failed: no such column: is_failed`

  **Acceptance Criteria**:
  - [ ] `python -m py_compile App/agent/agent/db.py` → no syntax errors
  - [ ] On Windows: `python -c "from agent.db import init_db; init_db(); print('OK')"` (with a pre-existing DB lacking `is_failed`) → prints `OK`, no `OperationalError`
  - [ ] After running, `PRAGMA table_info(messages)` shows `is_failed` column
  - [ ] `idx_dedup_v2` index exists in `sqlite_master`

  **Commit**: YES (group with Task 7)
  - Message: `fix(windows): fix is_failed schema migration crash on existing databases`
  - Files: `App/agent/agent/db.py`
  - Pre-commit: `python -m py_compile App/agent/agent/db.py`

---

- [x] 7. Fix `db_read.py`: make `is_failed` filter resilient to old schemas ✅ DONE (commit 8406ea5)

---

- [ ] 8. Fix webview file:// URL format on Windows

  **Status**: DISCOVERED via user testing. The webview shows "File not found" because the URL uses incorrect `file://` format with backslashes and unencoded spaces. Using `pathlib.Path.as_uri()` generates correct URLs.

  **What to do**:
  - In `App/webview_ui/main.py`, function `create_window()`, replace the manual `file://` URL construction with `pathlib.Path.as_uri()`:

  Current code (line ~82):
  ```python
  url = f"file://{os.path.abspath(index_path)}?page={initial_page}"
  ```

  Replace with:
  ```python
  from pathlib import Path
  abs_path = os.path.abspath(index_path)
  file_url = Path(abs_path).as_uri()
  url = f"{file_url}?page={initial_page}"
  ```

  **Why this works**: `Path.as_uri()` correctly converts Windows backslashes to forward slashes (`file:///`) and encodes spaces and special characters for all platforms.

  **Must NOT do**:
  - Do NOT change any other logic
  - Do NOT modify the debug flag handling

  **Acceptance Criteria**:
  - [ ] `python -m py_compile App/webview_ui/main.py` → no syntax errors
  - [ ] On Windows: webview loads and displays the dashboard (not "File not found")

  **Commit**: YES (standalone fix)
  - Message: `fix(windows): use pathlib.Path.as_uri() for correct file:// URL format`
  - Files: `App/webview_ui/main.py`
  - Pre-commit: `python -m py_compile App/webview_ui/main.py`

---

- [ ] 9. Investigate Windows tray layout issues

  **Status**: User reports tray numbers display but layout is incorrect compared to macOS. Need to compare with v1.0.1 implementation.

  **What to do**:
  - Check git history for v1.0.1 tray.py to see original Windows implementation
  - Compare menu building logic between Windows (pystray) and macOS (rumps)
  - Identify tab/alignment rendering differences

  **Investigative Steps**:
  1. Run: `git show v1.0.1:App/webview_ui/backend/tray.py | head -150`
  2. Compare with current `tray.py` lines 137-168 (`_build_row`, `_tabs_to_target`)
  3. Identify any platform-specific layout differences

  **Commit**: NO (investigation only, may need separate fix task)

  **Status**: DISCOVERED during Windows dev-mode testing. `db_read.py` opens the DB read-only and injects `(is_failed = 0 OR is_failed IS NULL)` into every deduplication subquery. If the DB was created before the `is_failed` migration ran, this query crashes the stats worker immediately on startup.

  **What to do**:
  - In `App/webview_ui/backend/db_read.py`, add a helper function that checks whether `is_failed` exists in the messages table, then use it in `_dedup_subquery()` and `_dedup_export_subquery()`.

  **Exact implementation**:

  1. Add a module-level cache variable just before `_dedup_subquery()`:
     ```python
     _has_is_failed_cache = None  # None = not yet checked
     ```

  2. Add a helper function:
     ```python
     def _check_has_is_failed(conn):
         """Check if is_failed column exists in messages table (cached)."""
         global _has_is_failed_cache
         if _has_is_failed_cache is None:
             try:
                 cols = [row[1] for row in conn.execute("PRAGMA table_info(messages)")]
                 _has_is_failed_cache = 'is_failed' in cols
             except Exception:
                 _has_is_failed_cache = False
         return _has_is_failed_cache
     ```

  3. Modify `_dedup_subquery(where_clause="")` — add a `conn` parameter and make the `is_failed` filter conditional:
     ```python
     def _dedup_subquery(where_clause="", conn=None):
         base_where = f"WHERE {where_clause}" if where_clause else ""
         if conn is not None and _check_has_is_failed(conn):
             filter_failed = "(is_failed = 0 OR is_failed IS NULL)"
             if base_where:
                 final_where = f"{base_where} AND {filter_failed}"
             else:
                 final_where = f"WHERE {filter_failed}"
         else:
             final_where = base_where
         return f"""
         (SELECT ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id
          FROM messages {final_where}
          GROUP BY ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id)
         """
     ```

  4. Modify `_dedup_export_subquery(where_clause="")` — same pattern, add `conn` parameter:
     ```python
     def _dedup_export_subquery(where_clause="", conn=None):
         base_where = f"WHERE {where_clause}" if where_clause else ""
         if conn is not None and _check_has_is_failed(conn):
             filter_failed = "(is_failed = 0 OR is_failed IS NULL)"
             if base_where:
                 final_where = f"{base_where} AND {filter_failed}"
             else:
                 final_where = f"WHERE {filter_failed}"
         else:
             final_where = base_where
         return f"""
         (SELECT
             MIN(session_id) AS session_id,
             MIN(msg_id) AS msg_id,
             ts, role,
             input, output, reasoning, cache_read, cache_write,
             MIN(model) AS model,
             provider_id, model_id
          FROM messages {final_where}
          GROUP BY ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id)
         """
     ```

  5. Update every call site that passes `conn` to `_dedup_subquery()` / `_dedup_export_subquery()` — pass `conn=conn`. The affected functions are: `aggregate_range`, `by_model_range`, `by_provider_range`, `get_raw_trend_data`, `export_csv_range`. Example:
     ```python
     subquery = _dedup_subquery(where_clause, conn=conn)
     ```

  6. Also reset the cache when the DB is newly opened to avoid stale state across app restarts (the `None` default handles this correctly for fresh module import).

  **Cache invalidation note**: The `_has_is_failed_cache` module-level cache is correct here. Within a single app run, once the migration has run (by the agent), the column is present permanently. If for any reason a test needs to reset it, set `db_read._has_is_failed_cache = None`.

  **Must NOT do**:
  - Do NOT change the DB connection to read-write
  - Do NOT attempt to run `ALTER TABLE` from `db_read.py`
  - Do NOT change `aggregate()`, `by_provider()`, `by_model()` — they delegate to the `_range` functions which will get the fix
  - Do NOT change `export_csv()` — it delegates to `export_csv_range()` which gets the fix

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small targeted changes across one file — add helper, update two subquery builders, update 5 call sites
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6)
  - **Parallel Group**: Wave (new) — Tasks 6 and 7 can run in parallel
  - **Blocks**: Task 5 (rebuild + QA)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `App/webview_ui/backend/db_read.py:95-141` — `_dedup_subquery()` and `_dedup_export_subquery()` current implementations
  - `App/webview_ui/backend/db_read.py:154-185` — `aggregate_range()` call site
  - `App/webview_ui/backend/db_read.py:208-242` — `by_model_range()` call site
  - `App/webview_ui/backend/db_read.py:245-277` — `by_provider_range()` call site
  - `App/webview_ui/backend/db_read.py:280-307` — `get_raw_trend_data()` call site
  - `App/webview_ui/backend/db_read.py:330-374` — `export_csv_range()` call site
  - `error_log.txt:7,9` — stats worker and agent crash messages referencing this exact error

  **Acceptance Criteria**:
  - [ ] `python -m py_compile App/webview_ui/backend/db_read.py` → no syntax errors
  - [ ] On Windows with old DB (no `is_failed`): `python -c "from webview_ui.backend import db_read; r = db_read.aggregate('today'); print(r)"` → returns a dict (not crash)
  - [ ] On Windows with new DB (has `is_failed`): same command → returns correct dict with `is_failed` filtering active
  - [ ] `error_log.txt` line 7 (`no such column: is_failed`) no longer reproduced after fix

  **Commit**: YES (group with Task 6)
  - Message: `fix(windows): fix is_failed schema migration crash on existing databases`
  - Files: `App/webview_ui/backend/db_read.py`
  - Pre-commit: `python -m py_compile App/webview_ui/backend/db_read.py`

---

- [ ] 5. Rebuild Windows EXE and run end-to-end QA

  **What to do**:
  - On Windows machine: rebuild the EXE using `.\build_windows.bat`
  - Run all QA scenarios from the Verification Strategy section above:
    1. Launch EXE and verify webview shows content (not blank)
    2. Verify tray shows actual icon (not blue square)
    3. After OpenCode session, verify tray updates with token data
    4. Trigger a threshold notification and verify it appears with icon
    5. Run `_is_webview_running()` test to confirm no exception
  - Capture stdout/stderr from EXE launch (redirected to file)

  **Must NOT do**:
  - Do NOT skip any QA scenario from the list above
  - Do NOT mark as complete if webview shows `about:blank` even briefly

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires running Windows build toolchain and verifying multiple behaviors
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final, sequential)
  - **Blocks**: Nothing (final task)
  - **Blocked By**: Tasks 1, 2, 3, 4 (all must complete first)

  **References**:
  - `build_windows.bat` — Windows build script
  - `OpenCodeTokenMeter.spec` — PyInstaller spec; check `datas` entries to confirm `webview_ui/web` and `resources` are included
  - All QA scenarios in Verification Strategy section above

  **Acceptance Criteria**:
  - [ ] `.\build_windows.bat` completes without error
  - [ ] EXE launches and tray icon appears (correct AppIcon.ico, not blue square)
  - [ ] Webview window opens with full UI content (Dashboard visible)
  - [ ] Stdout shows `[INFO] Loading URL: file://...index.html` (not `[ERROR] index.html not found`)
  - [ ] After OpenCode activity, tray menu shows non-zero token/cost values
  - [ ] `_is_webview_running()` does not raise exception

  **Commit**: YES (final integration commit)
  - Message: `fix(windows): complete Windows compatibility — webview, tray icon, data paths, process check`
  - Files: (all modified files in aggregate)
  - Pre-commit: `python -m py_compile App/webview_ui/main.py App/webview_ui/backend/tray.py App/agent/agent/config.py App/webview_ui/main_tray.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 0 | n/a (investigation only) | none | n/a |
| 1+3+4 (wave 2) | `fix(windows): use sys._MEIPASS for resource paths in frozen builds` ✅ | `main.py`, `tray.py`, `main_tray.py` | `python -m py_compile` each file |
| 2 | `fix(windows): correct OpenCode data paths for Windows` ✅ | `config.py` | `python -m py_compile config.py` |
| 6+7 | `fix(windows): fix is_failed schema migration crash on existing databases` | `db.py`, `db_read.py` | `python -m py_compile` each file |
| 5 | `fix(windows): complete Windows compatibility — webview, tray icon, data paths, process check` | all | full QA pass |

---

## Success Criteria

### Verification Commands
```powershell
# On Windows machine after build:
python -m py_compile App/webview_ui/main.py               # No errors
python -m py_compile App/webview_ui/backend/tray.py       # No errors
python -m py_compile App/agent/agent/config.py            # No errors
python -m py_compile App/webview_ui/main_tray.py          # No errors

# Paths valid (in frozen context):
# get_web_dir() → returns path containing index.html
# get_icon_path() → returns path containing AppIcon.ico

# On Windows EXE launch (stdout):
# [INFO] Loading URL: file://C:\...\index.html   ← NOT about:blank
# NOT: [ERROR] index.html not found
# NOT: [Tray] Failed to start:
# NOT: FileNotFoundError (ps command)
```

### Final Checklist
- [ ] All "Must Have" items present (sys._MEIPASS used, platform guards in place)
- [ ] All "Must NOT Have" items absent (no psutil, no macOS path changes, no new deps)
- [ ] Webview shows full UI on Windows EXE — not blank
- [ ] Tray shows correct icon on Windows EXE — not blue square
- [ ] Tray data populates after OpenCode activity (if OpenCode data path is correct)
- [ ] No Python exceptions related to `ps`, icon path, or web dir on Windows
