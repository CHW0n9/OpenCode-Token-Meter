# OpenCode Token Meter — Agent Guidance

This document codifies how to work with the OpenCode Token Meter codebase from an agent perspective. It covers build, test, lint, style, packaging, and operational requirements for both local and CI contexts.

## 1) Build, Lint, and Test Commands

- **Build (Production)**:
  - macOS: `./build.sh`
  - Windows: `.\build_windows.bat`
- **Clean Build Artifacts**: `rm -rf build/ App/menubar/dist/ App/menubar/build/ App/agent/dist/ App/agent/build/ dist/`
- **Syntax Check**: `python -m py_compile <path>` (e.g., `App/agent/agent/db.py`)
- **Lint/Format**: `black .`, `isort .`, `flake8 .`
- **Run All Tests**: `pytest tests -q`
- **Run Single Test**: `pytest tests/test_db_dedup.py::test_deduped_counts -q`

## 2) Development Workflow

### Running from Source
To run the application in development mode:
```bash
cd App/menubar
python -m menubar
```
Running the `menubar` module directly will automatically initialize the background agent as a thread if no external agent is detected.

### Environment Requirements
- **Conda**: Ensure you are in the `opencode` conda environment.
- **Dependencies**: Use `mamba` or `conda` for installing Python dependencies. Avoid `pip install`.

## 3) Platform-Specific Packaging

This repository uses a **unified spec file** (`OpenCodeTokenMeter.spec`) at the root for all platforms.

- **Windows**: Produces a single `OpenCodeTokenMeter.exe` with an embedded agent and tray icon (`AppIcon.ico`).
- **macOS**: Produces a native `.app` bundle with an embedded agent and menubar icon (`AppIcon.icns`).

## 4) Embedded Agent Lifecycle

- **Primary Distribution**: The agent runs as a background thread within the main application process (embedded).
- **Fallback**: If the embedded agent fails to start, the app will attempt to connect to an external agent via UDS (macOS) or TCP (Windows).
- **Concurrency**: Database operations and message scanning are handled off the main UI thread to ensure responsiveness.

## 5) Database and Settings Locations

The application uses platform-specific paths for persistent data:

| Platform | Base Directory (BASE_DIR) |
|----------|----------------------------|
| macOS | `~/Library/Application Support/OpenCode Token Meter` |
| Windows | `%APPDATA%\OpenCode Token Meter` |

- **Database**: `BASE_DIR/index.db`
- **Settings**: `BASE_DIR/settings.json`
- **IPC Socket**: `BASE_DIR/agent.sock` (on Windows, TCP port 49152 is used)

## 6) Deduplication and Data Safety

- **Dedup Rule**: Located in `App/agent/agent/db.py`. Messages are grouped by `ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id`. The canonical record is the one with the lexicographically smallest `msg_id`.
- **SQL Safety**: Always use parameterized queries (`?`). Never use f-strings or concatenation for SQL inputs.
- **Durability**: SQLite WAL mode is enabled for safe concurrent access.

## 7) UI/UX Guidelines

- **Style**: Mimic the native look and feel of the host OS.
- **Modularity**: Large UI files (like `app.py`) should be modularized into separate window/widget classes under `App/menubar/menubar/windows/`.
- **Customization**: Models with user-defined pricing should be marked with a "(customized)" suffix in the UI.

## 8) Contributor Checklist

1. Run `python -m py_compile` on all modified files.
2. Run `black .` and `isort .` to ensure consistent formatting.
3. Run `pytest` to verify logic changes (especially deduplication and settings merging).
4. Verify the build locally using `build.sh` or `build_windows.bat`.
5. Update `CHANGELOG.md` with a summary of changes.

## 9) Versioning

This project adheres to **Semantic Versioning (SemVer)**.
- **Patch**: Bug fixes, internal refactors.
- **Minor**: New features, platform support.
- **Major**: Breaking architectural changes.

---
*End of AGENTS.md*
