AGENTS.md

Agent Guidelines for OpenCode Token Meter
=======================================

Purpose
-------
This document orients agents and contributors to the OpenCode Token Meter repository.
It summarizes build/run/test commands, coding style expectations, database safety rules,
and the exact deduplication behavior implemented in the agent.

Workdir
-------
Repository root: the working directory where AGENTS.md lives (example):
`/Users/<you>/Desktop/OpenCode Token Meter`

Quick commands
--------------
- Build (production):
  - From repo root: `./build.sh` — builds both agent and menubar with PyInstaller
- Development build (agent):
  - `cd App/agent` then:
    - `python3 -m PyInstaller --onefile --name opencode-agent agent/__main__.py`
- Development build (menubar):
  - `cd App/menubar` then:
    - `python3 -m PyInstaller -y --clean opencode-menubar.spec`
- Clean build artifacts:
  - `rm -rf build/ App/menubar/dist/ App/menubar/build/`
  - `rm -rf App/agent/dist/ App/agent/build/`
  - `rm -f opencode-agent.spec`

Run (development)
-----------------
- Run agent (development):
  - `cd App/agent` then `python3 -m agent`
- Run menubar (development):
  - `cd App/menubar` then `python3 -m menubar`

Syntax / quick checks
---------------------
- Quick syntax check for a file:
  - `python3 -m py_compile <path>` e.g. `python3 -m py_compile App/agent/agent/db.py`
- Run a small import test for menubar:
  - `cd App/menubar && python3 -c "from menubar.app import OpenCodeTokenMeter, SettingsDialog; print('Import successful')"`

Database paths and inspection
-----------------------------
- Default DB path used by code: `~/Library/Application Support/OpenCode Token Meter/index.db`
- Socket path: `~/Library/Application Support/OpenCode Token Meter/agent.sock`
- Inspect DB with sqlite3 CLI:
  - `sqlite3 "~/Library/Application Support/OpenCode Token Meter/index.db" ".tables"`
  - Run queries with: `sqlite3 "<path>" "SELECT ...;"`

Testing
-------
- Currently there are no unit tests in the repository by default. Recommended patterns:
  - Use pytest for unit tests.
  - Example single-test run:
    - `python -m pytest tests/test_db_dedup.py::test_deduped_counts -q`
- Suggested test files to add:
  1. `tests/test_db_dedup.py` — exercises dedup SQL on a temporary SQLite DB.
  2. `tests/test_settings_dialog.py` — basic tests for SettingsDialog behavior (preset vs custom).
  3. `tests/test_uds_client.py` — socket/client integration checks against a running agent (optional).

Linting and formatting
----------------------
- Recommended tools and commands:
  - Black: `black .` (88 char line length by default)
  - isort: `isort .` (use to keep imports grouped)
  - flake8: `flake8 .` (project specific ignores can be added)
  - mypy: `mypy .` (optional — gradually adopt for public APIs)

Code style guidelines (for agents)
---------------------------------
Follow these rules to keep changes consistent and predictable for automated agents.

1) Imports
   - Group imports: stdlib → third-party → local
   - Use absolute imports inside packages (e.g. `from agent.config import DB_PATH`)
   - Keep import statements at top of file except for guarded imports (platform/bundled checks)

2) Formatting
   - Use Black formatting (88 char width). Keep simple, machine-enforced style.
   - Use isort for import ordering.

3) Naming
   - Files/modules: `snake_case.py`
   - Classes: `PascalCase`
   - Functions/Methods: `snake_case()`
   - Constants: `UPPER_SNAKE_CASE`

4) Type hints
   - Prefer lightweight type hints on public APIs. Be pragmatic — gradual typing is fine.
   - Annotate return types for functions that are part of the public package surface.

5) SQL and DB safety
   - Always use parameterized queries for user-supplied values: `?` placeholders in sqlite3.
   - Avoid f-strings or string concatenation to build SQL with external inputs.
   - Use `get_conn()` helper patterns and close connections (use context managers).
   - Enable WAL mode: `conn.execute("PRAGMA journal_mode=WAL;")` near connection initialization.
   - Keep long-running transactions off the UI thread (menubar). Do DB work in a worker thread or the agent.

6) Error handling
   - Catch specific exceptions where possible (e.g. `sqlite3.OperationalError`).
   - Log errors to stderr: `print(f"Error: {e}", file=sys.stderr)`.
   - Fail gracefully in the UI: return empty data structures rather than raising uncaught exceptions.

7) Tests
   - Write unit tests for DB logic (dedup, aggregates) and small integration tests for UDS client/server.
   - Keep tests isolated: create temporary files/DBs and remove them after tests.

8) Git / PR expectations
   - Create small focused PRs with a single logical change.
   - Commit messages: present-tense, short summary + optional body. Example: `docs: add AGENTS.md with build/lint/test commands`
   - Run `python -m py_compile` and `black .` before pushing.

Deduplication details (exact behavior)
-------------------------------------
Deduplication is implemented entirely at the database query level to avoid double counting messages
that OpenCode sometimes duplicates across sessions.

- Implementation location: `App/agent/agent/db.py`
  - Function: `_get_deduplicated_messages_subquery(where_clause="")`
  - Other aggregates updated to use deduped subquery: `aggregate()`, `aggregate_range()`,
    `aggregate_by_provider()`, `aggregate_by_model()`, `get_message_count*`, `get_request_count*`.

- Dedup rule (precise):
  - Group messages by the following stable fields:
    - `ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id`
  - For each group keep the row whose `msg_id` is lexicographically smallest (SQL: `HAVING msg_id = MIN(msg_id)`).
  - The aggregates and exports operate over this deduplicated derived table (subquery).

Why this approach
------------------
- OpenCode can copy the same message into multiple sessions — these duplicates are identical for all token/usage
  relevant fields but differ in `msg_id` and sometimes `session_id`.
- Grouping by token-relevant fields and selecting a deterministic canonical `msg_id` prevents double counting
  while preserving one representative record for exports.

Performance & optional DB improvements
-------------------------------------
- Consider adding a composite index to speed the dedup query:
  - `CREATE INDEX IF NOT EXISTS idx_dedup ON messages(ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id);`
- Optionally create a view for debugging:
  - `CREATE VIEW IF NOT EXISTS dedup_messages AS SELECT * FROM (<dedup subquery>);`

Files of interest (where to look first)
--------------------------------------
- Agent DB + dedup: `App/agent/agent/db.py`
- Agent config: `App/agent/agent/config.py`
- Menubar app & SettingsDialog: `App/menubar/menubar/app.py`
- Menubar settings helpers: `App/menubar/menubar/settings.py`

Recommended unit tests to add (starter outlines)
----------------------------------------------
1) tests/test_db_dedup.py
   - Create a temporary sqlite DB file and a `messages` table with the same schema.
   - Insert multiple duplicate rows (same ts, role, inputs/outputs, provider/model, different msg_id and session_id).
   - Run the aggregate function(s) or run the dedup subquery and assert duplicates collapse.

2) tests/test_settings_dialog.py (UI-level, minimal)
   - Instantiate `SettingsDialog` in a headless Qt test harness (or mock UI state).
   - Assert selecting a preset model fills and disables provider/model inputs.
   - Assert selecting `Custom model` clears and enables provider/model inputs.

3) tests/test_agent_socket.py (integration)
   - Start the agent in subprocess mode (dev binary), connect with `menubar/uds_client.AgentClient`, verify `is_online()`.

How to run a single test file
-----------------------------
- With pytest installed:
  - `python -m pytest tests/test_db_dedup.py -q`
  - Or a single test function: `python -m pytest tests/test_db_dedup.py::test_deduped_counts -q`

Cursor/Copilot hints
--------------------
- Check for workspace-specific AI/cursor rules in these locations (if present, include or adapt):
  - `.cursor/`, `.cursorrules`, `.github/copilot-instructions.md`

Agent checklist for changes
---------------------------
When making code changes, follow this checklist:
1. Run `python -m py_compile` on modified files.
2. Run `black .` and `isort .`.
3. Add or update unit tests; run them locally with `pytest`.
4. Ensure SQL uses parameterized placeholders for external inputs.
5. Update AGENTS.md if workflows or build commands change.

Suggested next steps (pick one)
1) Add `AGENTS.md` (done) and run the quick syntax checks:
   - `python3 -m py_compile App/agent/agent/db.py`
   - `python3 -m py_compile App/menubar/menubar/app.py`
2) Add unit tests for the dedup SQL (suggested path: `tests/test_db_dedup.py`).
3) Add the composite index and/or the `dedup_messages` view to speed debugging.

Notes & caveats
---------------
- The dedup approach uses `ts` (integer seconds). If messages have sub-second precision, consider
  adjusting the grouping key.
- The canonicalization uses `MIN(msg_id)`. If `msg_id` ordering is non-deterministic in some environments,
  consider switching to `MIN(rowid)` or a deterministic tiebreaker.

Contact
-------
If anything in this document is unclear, open an issue or ask in the repository's primary communication channel.

End of AGENTS.md
