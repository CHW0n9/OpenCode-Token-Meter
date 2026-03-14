# Windows Compatibility - Decisions

## Session: ses_3137c7df1ffeNxM14u1BpsTKps
## Started: 2026-03-14T14:04:52.146Z

### Task 0 Decision
- **Status**: ✅ COMPLETED
- **Result**: OpenCode on Windows uses `~/.local/share/opencode/` (same as macOS/Linux)
- **Evidence**: User confirmed `opencode.db` at `C:\Users\<username>\.local\share\opencode\opencode.db`
- **Action**: Evidence recorded in `.sisyphus/evidence/windows-opencode-path.txt`

### Task 2 Decision
- **Status**: ✅ COMPLETED (comment update only)
- **Result**: No code changes needed — existing paths are correct
- **Action**: Updated config.py comment to reflect validation: "(validated on Windows)"
- **Commit**: `docs(windows): validate OpenCode data path on Windows`

### Parallel Execution Strategy
- **Wave 2**: Tasks 1, 3, 4 can run in parallel (no dependencies on Task 0)
- **Wave 3**: Task 2 after Task 0 completes
- **Wave 4**: Task 5 (final QA) after all implementation tasks complete

### Commit Strategy
- Tasks 1, 3, 4: Single commit with message `fix(windows): use sys._MEIPASS for resource paths in frozen builds`
- Task 2: Separate commit with message `fix(windows): correct OpenCode data paths for Windows`
- Task 5: Final integration commit with message `fix(windows): complete Windows compatibility — webview, tray icon, data paths, process check`
