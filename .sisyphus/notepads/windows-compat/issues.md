# Windows Compatibility - Issues

## Session: ses_3137c7df1ffeNxM14u1BpsTKps
## Started: 2026-03-14T14:04:52.146Z

### Pre-existing LSP Errors
- Multiple import resolution errors for `agent.config`, `agent.logger`, etc.
- These are pre-existing and not related to Windows compatibility changes
- Likely due to project structure and Python path configuration
- **Action**: Ignore these errors; they are not blocking

### Task 0 Blocking Issue
- **Issue**: Task 0 requires Windows machine to run PowerShell commands
- **Impact**: Task 2 (config.py path fix) is blocked until Task 0 completes
- **Workaround**: Implement Tasks 1, 3, 4 first (no dependencies on Task 0)
- **User Action Required**: Run Task 0 on Windows machine before Task 2

### Windows Adaptation Folder Confusion
- **Issue**: `Windows Adaptation/` folder contains previous Windows adaptation work
- **Observation**: This appears to be from a different architecture (PyQt6-based)
- **Current Codebase**: Uses pywebview, not PyQt6
- **Decision**: Ignore `Windows Adaptation/` folder; follow the plan in `.sisyphus/plans/windows-compat.md`

---

## NEW Issues Discovered (2026-03-15, from error_log.txt Windows dev-mode test)

### Issue: Agent Thread + Stats Worker crash with "no such column: is_failed"

**Error log** (error_log.txt lines 7-22):
```
[Stats] Initial stats collection failed: no such column: is_failed
[Tray]  Agent thread failed: no such column: is_failed
sqlite3.OperationalError: no such column: is_failed
```

**Root Cause A — Agent crash (`db.py` `init_db()`):**
- `init_db()` calls `executescript()` which includes:
  `CREATE INDEX IF NOT EXISTS idx_dedup_v2 ON messages(..., is_failed)`
- On a pre-existing DB WITHOUT `is_failed` (older install): `CREATE TABLE IF NOT EXISTS` is a no-op, then the index creation FAILS because `is_failed` doesn't exist yet
- `mark_failed_requests()` (which does `ALTER TABLE ADD COLUMN is_failed`) runs AFTER `executescript` — too late
- **Fix**: Remove `idx_dedup_v2` from `executescript`; recreate it after `mark_failed_requests()` (Task 6)

**Root Cause B — Stats Worker crash (`db_read.py`):**
- `db_read.py` opens the DB READ-ONLY and injects `(is_failed = 0 OR is_failed IS NULL)` into every dedup subquery
- Cannot run migration from read-only mode
- Both threads start simultaneously; stats worker hits the query before the agent can migrate
- **Fix**: Make `is_failed` filter conditional on `PRAGMA table_info` check (Task 7)

**Affected files:**
- `App/agent/agent/db.py:46-92` (init_db — Task 6)
- `App/webview_ui/backend/db_read.py:95-141` (dedup subqueries — Task 7)

**Both tasks are independent and can run in parallel.**
