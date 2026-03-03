# Design Doc: OpenCode Token Meter Migration to SQLite Data Source

**Date**: 2026-03-03
**Status**: Approved (via Brainstorming)
**Topic**: Transitioning from file-based `message.json` scanning to direct `opencode.db` ingestion.

## 1. Overview
OpenCode has updated its architecture to store all message data in a central SQLite database (`opencode.db`) instead of individual JSON files. This design ensures the Token Meter app remains compatible with both older file-based versions and new database-based versions using a **Parallel Sync** strategy.

## 2. Architecture: Dual-Source Sync
The `Scanner` class will be extended to support two concurrent ingestion streams:

### A. Legacy File Stream (Existing)
- **Path**: `~/.local/share/opencode/storage/message/`
- **Method**: `os.scandir` + `mtime` tracking.
- **Purpose**: Handles residual files from older OpenCode versions or unprocessed messages during the update transition.

### B. New Database Stream (New)
- **Path**: `/Users/chwong/.local/share/opencode/opencode.db`
- **Method**: Direct SQLite queries on the `message` table.
- **Incremental Logic**: Track the maximum `time_updated` (milliseconds) processed in a new `sync_state` table in `index.db`.
- **Query**: `SELECT id, session_id, time_updated, data FROM message WHERE time_updated > ? ORDER BY time_updated ASC`

## 3. Data Integrity & Deduplication
- Both streams will resolve to the same `msg_id` (OpenCode's native ID).
- The `index.db` schema uses `msg_id` as the `PRIMARY KEY`.
- `INSERT OR REPLACE` logic in `db.py` guarantees that even if a message is seen by both the file scanner and the DB syncer, only one unique record persists.
- **No double counting** of tokens will occur.

## 4. Performance & Efficiency
- **Reduced Disk I/O**: Database queries are indexed and significantly faster than scanning thousands of small files.
- **Polling Interval**: Can be reduced from 300s to **15-30s** to provide near real-time updates in the dashboard without noticeable CPU impact.
- **Read-Only Safety**: `opencode.db` will be opened in `mode=ro` (Read-Only) to prevent any accidental interference with OpenCode's internal data.

## 5. Implementation Steps
1. **Config**: Add `OPENCODE_DB_PATH` to `App/agent/agent/config.py`.
2. **Database**: Add `sync_state` table and helper functions to `App/agent/agent/db.py`.
3. **Syncer**: Implement `_sync_from_opencode_db` in `App/agent/agent/scanner.py`.
4. **Integration**: Call the new syncer inside `Scanner.scan_once()`.
5. **Verification**: Verify that new messages from `opencode.db` appear correctly in the UI.

## 6. Cleanup (Future)
Once the legacy file format is confirmed as completely deprecated by OpenCode, the file-scanning logic and the `files` table (tracking mtimes) can be safely removed in a future release.
