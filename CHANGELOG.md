# Changelog

All notable changes to the OpenCode Token Meter project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2025-02-01

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
