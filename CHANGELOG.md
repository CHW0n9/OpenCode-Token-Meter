# Changelog

All notable changes to the OpenCode Token Meter project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-02-11

### Added

- **Modern UI Architecture**: Fully transitioned from PyQt6 to `pywebview`, enabling a modern, responsive web-based interface while reducing bundle size.
- **Embedded Lifecycle**: Unified the Agent and Stats Worker as background threads within a single application process for both Windows and macOS.
- **Enhanced Typography**: Standardized on **Lato** with a font-weight of **900** for headers and chart labels for a premium, bold aesthetic.
- **Dashboard Visualization**: New real-time usage trend charts and distribution analytics.

### Changed

- **Packaging Refactor**: Completely redesigned the build system with a unified `.spec` file and improved sub-process handling (fixing the "window not opening" bug in packaged apps).
- **Documentation Consolidation**: Merged `BUILD.md` and `PROJECT_ARCHITECTURE.md` into the main `README.md` for a single-source-of-truth.
- **Project Structure Cleanup**: Removed legacy main files, redundant scripts, and standalone installer folders to streamline the codebase.

### Fixed

- **Subprocess Launch**: Resolved a critical issue where the webview window failed to open in the packaged `.app` bundle due to module path resolution errors.
- **Layout Alignment**: Centered navigation controls and refined padding across all pages for better visual balance.
- **Import Robustness**: Improved module loading logic in `__main__.py` to handle both development and frozen environments.

---

## [1.0.1] - 2026-02-05

### Added

- **Windows Support**: Full support for Windows platform with native system tray integration.
- **Unified Build System**: Single `.spec` file for building on Windows and macOS.
- **Embedded Agent**: Background agent now runs as a thread within the main application, eliminating the need for a separate process.
- **Platform-Aware Paths**: Standardized data and settings locations for Windows (`%APPDATA%`) and macOS (`Library/Application Support`).
- **Settings Migration**: Automatic migration of settings from legacy macOS-style paths on Windows to the correct platform-appropriate directory.
- **Model Management UI**:
  - "(customized)" label for models with user-defined pricing.
  - "Mark as Deleted" to hide default models.
  - "Reset to Default" and "Reset All to Default" functionality.
- **Registry Integration (Windows)**: Added scripts for setting AppUserModelID and handling shortcuts for better toast notification support.

### Changed

- **Settings Refactor**: Stabilized settings logic to separate user overrides from default model definitions.
- **Normalization**: User settings now only store values that differ from defaults, keeping `settings.json` clean.
- **Build Process**: Windows builds now use `build_windows.bat` for a single-executable output.

### Fixed

- **Settings Data Loss**: Fixed a bug where merging user settings could inadvertently delete default models due to shallow copying.
- **Pathing Issues**: Resolved hardcoded macOS paths in settings and IPC logic.
- **Windows Icon Support**: Integrated multi-size `.ico` resource for Windows executables.
- **IPC Reliability**: Standardized Unix Domain Socket (macOS) and TCP (Windows) for inter-process communication.

---

## [1.0.0] - 2026-02-01

### Added

#### Core Features

- **Real-time Token Tracking**: Monitor AI token usage from OpenCode message directory
- **Token Calculation**: Automatic input/output token counting from message files
- **Cost Calculation**: Model-specific pricing with automatic cost computation
- **Menubar Display**: Compact 2×3 grid showing key metrics (In, Req, Out, Cost, Token%, Cost%)
- **Details Window**: Comprehensive statistics with provider/model breakdown
- **Custom Date Range Export**: Export usage data for specific time periods
- **Settings Dialog**: Two-tab interface for cost configuration and notifications

#### Architecture

- **Background Agent**: Unix Domain Socket server for continuous message scanning
- **Deduplication System**: Prevents double-counting of messages across sessions
- **SQLite Database**: Local storage at `~/Library/Application Support/OpenCode Token Meter/`
- **Async Loading**: Non-blocking UI with spinner indicators for long operations
- **Cost Caching**: Efficient in-memory caching to avoid recalculating costs

#### Models & Pricing

- **Preset Models**: OpenAI (GPT-4, GPT-4o, GPT-3.5-turbo), Anthropic (Claude 3), DeepSeek
- **Custom Models**: Support for any provider/model combination
- **Free Models**: Ollama and other local models show $0.00 cost
- **Configurable Pricing**: Adjust cost per token in settings

#### User Interface

- **PyQt6-based GUI**: Native macOS integration
- **Menubar Integration**: Always-accessible statistics
- **Three View Modes**: All/Provider/Model views in details dialog
- **Settings Management**: Persistent user preferences
- **Notification Support**: Optional threshold-based alerts

#### Database Features

- **Dedup Index**: Composite index for fast deduplication queries
- **Parameterized Queries**: SQL injection prevention with `?` placeholders
- **WAL Mode**: Safe concurrent database access
- **Automatic Sync**: Messages refreshed every few seconds

#### Export Capabilities

- **Statistics Export**: Copy token and cost data for custom date ranges
- **Model Breakdown**: Export aggregates by provider and model
- **Request Tracking**: Track and export request counts

#### Build & Distribution

- **PyInstaller Build**: Automated compilation to standalone binaries
- **DMG Installer**: macOS-native distribution format
- **One-Step Build**: `./build.sh` creates production-ready DMG
- **Unsigned Code**: Simplifies development (unsigned app warning on first launch)

### Technical Details

#### Message Data Location

- Source: `~/.local/share/opencode/storage/message/`
- Format: JSON files in session subdirectories (`ses_XXXXXXX/`)
- Token fields: `input_tokens`, `output_tokens`, `cached_read`, `cached_write`

#### Deduplication Algorithm

- Groups by: timestamp, role, input, output, reasoning, cache fields, provider, model
- Selection: Lexicographically smallest `msg_id` per group
- Applied to: All aggregates, exports, and statistics

#### Database Schema

- `messages` table: Core message data with token counts
- `idx_dedup` index: Composite index on dedup-relevant fields
- Automatic views: Dedup subquery for aggregations

#### Configuration

- Agent config: `App/agent/agent/config.py`
- Default pricing: `App/menubar/menubar/settings.py`
- Settings storage: `~/Library/Application Support/OpenCode Token Meter/settings.json`

#### Performance

- Non-blocking UI: All long operations use async/threading
- Efficient queries: Dedup happens at SQL level, not in Python
- Minimal overhead: Background agent uses ~2% CPU
- Fast startup: Agent checks skip 15-second blocking wait

### Bug Fixes

- Fixed agent startup hanging (replaced with QTimer async checks)
- Fixed custom range export crash with error handling
- Fixed table column ordering (Total Output after Reasoning)
- Removed legacy unused functions

### Changed

- **Menu Layout**: Changed from progress bars to percentage-only for thresholds
- **Performance**: Reduced agent startup wait from 5s to 1s
- **UI Polish**: Progress bar display (█ character for visual feedback)

### Dependencies

- Python 3.12+
- PyQt6 (GUI framework)
- SQLite3 (database)
- PyInstaller (build tool)
- Standard library only (subprocess, socket, json, sqlite3, threading)

### Known Limitations

- Unsigned app requires manual security approval on first launch
- Message scanning rate depends on filesystem polling (typically 1-5 seconds)
- Max display precision: 2 decimal places for costs
- Token thresholds are simple numeric values (not percentages)

### Development Notes

- All SQL uses parameterized queries for safety
- Dedup logic centralized in `_get_deduplicated_messages_subquery()`
- Type hints on public APIs (gradual typing approach)
- Code style: Black (88 char), isort, flake8
- Testing infrastructure not yet added (see AGENTS.md for suggestions)

---

## Version Strategy

This project uses Semantic Versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes to user-facing features or API
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes and minor improvements

The first stable release is **1.0.0**, indicating production readiness.
