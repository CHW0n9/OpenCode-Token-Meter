# Fix Navigation and Agent Issues

## TL;DR

> **Quick Summary**: Fix three critical issues - menu page navigation not working, tab clicks requiring double-click, and agent not restarting properly.
>
> **Deliverables**:
> - Navigation watcher waits for pywebviewready event before accepting commands
> - Tab click handler fixed to work on single click
> - Agent startup includes cleanup of stale socket files
>
> **Estimated Effort**: Medium
> **Parallel Execution**: NO - sequential (tests each fix)
> **Critical Path**: Task 1 → Task 2 → Task 3

---

## Context

### Original Request
Continue fixing the pywebview migration issues - specifically menu page navigation, tab double-click, and agent restart.

### Interview Summary
**Key Discussions**:
- User reported menu items (Show Main Window, Settings, Details) don't switch pages in webview
- Tab clicks require double-click instead of single-click
- Agent not restarting properly from tray menu

**Research Findings**:
- Nav_watcher thread starts immediately but app.js waits for pywebviewready event
- Socket files may be stale from previous agent runs
- Tab click handler has CSS class timing issues

### Metis Review
**Identified Gaps** (addressed):
- Timing issue: nav_watcher may call switchView before app is ready - add readiness check
- Socket cleanup: remove stale socket files before starting agent
- Tab CSS: check class update timing and transitions

---

## Work Objectives

### Core Objective
Fix navigation and agent startup issues to achieve full functionality of the pywebview-based application.

### Concrete Deliverables
- Navigation waits for app ready state before executing commands
- Tab clicks work on single click
- Agent starts reliably after being stopped

### Definition of Done
- [x] Clicking tray menu items (Show Main Window, Settings, Details) switches to correct page in webview
- [x] Clicking navigation tabs works on first click
- [x] Agent can be started/stopped/restarted reliably from tray menu

### Must Have
- Menu-to-window page navigation working
- Tab clicks work on single click
- Agent restarts properly after being stopped

### Must NOT Have (Guardrails)
- No polling for app readiness more than once per second
- No blocking the main thread during agent startup
- No removing socket files while agent is actually using them

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> This is NOT conditional — it applies to EVERY task, regardless of test strategy.
>
> **FORBIDDEN** — acceptance criteria that require:
> - "User manually tests..." / "사용자가 직접 테스트..."
> - "User visually confirms..." / "사용자가 눈으로 확인..."
> - "User interacts with..." / "사용자가 직접 조작..."
> - "Ask user to verify..." / "사용자에게 확인 요청..."
> - ANY step where a human must perform an action
>
> **ALL verification is executed by the agent** using tools (Playwright, interactive_bash, curl, etc.). No exceptions.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: Tests-after
- **Framework**: pytest

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

> Whether TDD is enabled or not, EVERY task MUST include Agent-Executed QA Scenarios.

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |  |  | 
|------|------|-------------------|------|------|
| **Python Logic** | Bash (python -c, pytest) | Run Python code, assertions |  |  |
| **File Operations** | Bash (ls, cat, rm) | File existence and content checks |  |  |
| **Event Ordering** | Bash (time, sleep) | Verify timing and sequence |  |  |

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.

```
Wave 1 (Start Immediately):
└── Task 1: Fix Nav Watcher - App Ready Check

Wave 2 (After Wave 1):
└── Task 2: Fix Tab Double-Click Issue

Wave 3 (After Wave 2):
└── Task 3: Fix Agent Restart - Socket Cleanup

Critical Path: Task 1 → Task 2 → Task 3
Parallel Speedup: None (sequential dependencies)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | None |
| 2 | 1 | 3 | None |
| 3 | 1, 2 | None | None (final) |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.

- [x] 1. Fix Navigation Watcher - Wait for App Ready

  **What to do**:
  - Modify `App/webview_ui/webview_runner.py` to ensure nav_watcher waits for pywebviewready event before executing navigation commands
  - Add a flag to track app readiness state
  - Only evaluate JS when both nav file exists AND app is ready
  - Change polling interval from 0.5s to 1s (less frequent, still responsive)
  - Add debug logging to track when nav commands are executed vs skipped

  **Must NOT do**:
  - Don't use busy waiting (keep polling with reasonable interval)
  - Don't block the main thread
  - Don't remove nav file before command is executed

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Simple logic change in existing Python file - straightforward modification
  - **Skills**: `[]` (no special skills needed)
  - **Skills Evaluated but Omitted**:
    - None needed for this Python code change

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (starts immediately)
  - **Blocks**: Task 2, Task 3
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `App/webview_ui/web/js/app.js:90-109` - pywebviewready event handling pattern (window.pywebviewready)
  - `App/webview_ui/webview_runner.py:80-102` - Current nav_watcher implementation (needs modification)

  **API/Type References** (contracts to implement against):
  - `window.evaluate_js()` - pywebview API for executing JavaScript
  - `threading.Event()` - Python threading primitive for signaling

  **Test References** (testing patterns to follow):
  - No specific test patterns - verify changes manually through app behavior

  **Documentation References** (specs and requirements):
  - `AGENTS.md` - Agent behavior requirements

  **External References** (libraries and frameworks):
  - pywebview docs: `https://pywebview.flowrl.com/guide/api.html#window-evaluate-js` - JavaScript evaluation API
  - threading docs: `https://docs.python.org/3/library/threading.html#event-objects` - Thread synchronization

  **WHY Each Reference Matters**:
  - `app.js:90-109`: Shows how to wait for pywebviewready event - we need to signal this from Python side
  - `webview_runner.py:80-102`: Current implementation we need to modify
  - `threading.Event`: Simple way to communicate app readiness between threads

  **Acceptance Criteria**:
  - [ ] nav_watcher has `app_ready` flag that waits to be set before executing nav commands
  - [ ] Python syntax check passes: `python -m py_compile App/webview_ui/webview_runner.py`
  - [ ] Logging shows "App not ready, skipping nav" when nav file arrives before pywebviewready
  - [ ] Logging shows "Executing nav switch to: {page}" when nav file arrives after app ready

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  **Python Logic Verification:**

  ```
  Scenario: Nav watcher waits for app ready signal
    Tool: Bash (python -c)
    Preconditions: None
    Steps:
      1. Create test script that simulates nav_watcher behavior:
         ```python
         import threading
         import time

         nav_file_found = False
         app_ready = False

         # Simulate nav_watcher loop
         def watcher():
             global nav_file_found
             for i in range(3):
                 if nav_file_found and app_ready:
                     print(f"Execute nav (iteration {i})")
                     break
                 elif nav_file_found and not app_ready:
                     print(f"Skip nav - app not ready (iteration {i})")
                 else:
                     print(f"Waiting (iteration {i})")
                 time.sleep(0.1)

         t = threading.Thread(target=watcher)
         t.start()

         # Nav file appears before app ready
         nav_file_found = True
         time.sleep(0.05)
         print("Nav file found, but app not ready yet")

         # App ready signal arrives later
         time.sleep(0.1)
         app_ready = True
         print("App is now ready")

         t.join()
         ```
      2. Run test script
      3. Assert: Output contains "Skip nav - app not ready (iteration 0)"
      4. Assert: Output contains "Execute nav (iteration 1)"
      5. Assert: Output does NOT execute nav before app ready

    Expected Result: Nav commands are skipped until app_ready is True
    Evidence: Test script output captured
  ```

  **File Structure Verification:**

  ```
  Scenario: Modified webview_runner.py compiles without errors
    Tool: Bash (python -m py_compile)
    Preconditions: File exists at App/webview_ui/webview_runner.py
    Steps:
      1. Run: python -m py_compile App/webview_ui/webview_runner.py
      2. Check exit code

    Expected Result: Exit code is 0 (no syntax errors)
    Evidence: Exit code captured
  ```

  **Evidence to Capture**:
  - [ ] Test script output in .sisyphus/evidence/task-1-nav-ready-test.txt
  - [ ] Compiler output in .sisyphus/evidence/task-1-syntax-check.txt

  **Commit**: NO (groups with task 2 and 3)

- [x] 2. Fix Tab Double-Click Issue

  **What to do**:
  - Investigate why navigation tabs require double-click in `App/webview_ui/web/js/app.js`
  - Check if switchView function is called correctly on first click
  - Fix any CSS class issues or event propagation problems
  - Ensure tab visual state updates immediately on first click
  - Add debug logging to switchView function to track execution

  **Must NOT do**:
  - Don't change the overall app.js structure
  - Don't break other navigation methods (tray menu)
  - Don't add workarounds that hide the real problem

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: JavaScript+CSS debugging for UI interaction issues - requires understanding DOM, event handling, and styling
  - **Skills**: `['playwright']`
    - `playwright`: For testing tab clicks in browser, verifying DOM updates and class changes
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Not needed - this is a bug fix, not new UI design

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: Task 1 (navigation system should be working first)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `App/webview_ui/web/js/app.js:28-35` - Tab event listener setup
  - `App/webview_ui/web/js/app.js:61-87` - switchView function implementation
  - `App/webview_ui/web/css/styles.css` - Tab CSS classes and transitions

  **API/Type References** (contracts to implement against):
  - DOM API: `element.classList.add()`, `element.classList.remove()`
  - Event API: `element.addEventListener()`, event object properties

  **Test References** (testing patterns to follow):
  - No specific test patterns - browser-based testing via Playwright

  **Documentation References** (specs and requirements):
  - Tailwind CSS docs: `https://tailwindcss.com/docs` - CSS class system

  **External References** (libraries and frameworks):
  - MDN: `https://developer.mozilla.org/en-US/docs/Web/API/Element/classList` - DOM class manipulation
  - MDN: `https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener` - Event handling

  **WHY Each Reference Matters**:
  - `app.js:28-35` and `app.js:61-87`: Tab click handler and view switching logic - need to debug why double-click is needed
  - `styles.css`: Tab CSS might have transitions or states that cause timing issues
  - MDN docs: Understanding DOM and event APIs for correct implementation

  **Acceptance Criteria**:
  - [ ] Single tab click triggers view switch
  - [ ] Tab visual state (text-white, bg-black-700) updates on first click
  - [ ] No additional debugging code remains in production
  - [ ] All existing functionality remains intact (tray menu nav, initial page load)

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  **Browser Testing:**

  ```
  Scenario: Tab click works on single click
    Tool: Playwright (playwright skill)
    Preconditions: Dev server running or app in browser mode
    Steps:
      1. Navigate to: http://localhost:8080 (or open app index.html in browser)
      2. Wait for: .nav-tab elements visible (timeout: 5s)
      3. Capture initial state: Screenshot of nav tabs
      4. Click: First tab (e.g., Dashboard tab) with data-view="dashboard"
      5. Wait for: 100ms (verify immediate update, no second click needed)
      6. Check: Active tab has class "text-white" and "bg-black-700"
      7. Check: Dashboard view section has class "animate-fade-in" (visible)
      8. Check: Other views have class "hidden" (not visible)
      9. Click: Second tab (e.g., Settings tab)
      10. Wait for: 100ms
      11. Check: Settings tab now has active class
      12. Check: Settings view is visible, other views hidden
      13. Screenshot: Final state after both clicks
    Expected Result: Each single click immediately switches view and updates tab styling
    Evidence: Screenshots in .sisyphus/evidence/task-2-tab-click-*.png

  Scenario: Initial page loads with correct view and active tab
    Tool: Playwright (playwright skill)
    Preconditions: Dev server or browser mode
    Steps:
      1. Navigate to: http://localhost:8080/?page=settings
      2. Wait for: page load (timeout: 5s)
      3. Check: Settings view section visible (not hidden)
      4. Check: Settings tab has active class (text-white, bg-black-700)
      5. Navigate to: http://localhost:8080/?page=details
      6. Check: Details view visible
      7. Check: Details tab active
    Expected Result: Query parameters correctly set initial view
    Evidence: Screenshots showing each page load
  ```

  **JavaScript Syntax Verification:**

  ```
  Scenario: app.js has no syntax errors after changes
    Tool: Bash (node)
    Preconditions: Node.js installed
    Steps:
      1. Run: node -c App/webview_ui/web/js/app.js
      2. Check exit code

    Expected Result: Exit code is 0 (no syntax errors)
    Evidence: Exit code captured
  ```

  **Evidence to Capture**:
  - [ ] Screenshots in .sisyphus/evidence/task-2-tab-click-*.png
  - [ ] Node.js syntax check output in .sisyphus/evidence/task-2-js-syntax.txt

  **Commit**: NO (groups with task 3)

- [x] 3. Fix Agent Restart - Socket Cleanup

  **What to do**:
  - Add socket file cleanup in `App/webview_ui/main_tray.py` before starting agent
  - Check if `agent.sock` exists and if it's stale (no process using it)
  - Remove stale socket files before starting new agent
  - Improve `_is_agent_online()` to verify socket is actually connected (not just file exists)
  - Add debug logging for socket cleanup steps

  **Must NOT do**:
  - Don't remove socket files while agent is actively using them
  - Don't hardcode socket paths - use config from agent module
  - Don't block tray startup on socket cleanup (continue as best effort)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: System utilities - file operations and process checking - straightforward
  - **Skills**: `[]` (no special skills needed)
  - **Skills Evaluated but Omitted**:
    - None needed for file operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Tasks 1 and 2)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 1, Task 2 (previous fixes should be complete)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `App/webview_ui/main_tray.py:94-113` - Current `_is_agent_online()` implementation
  - `App/webview_ui/main_tray.py:43-92` - Agent startup logic
  - `App/agent/agent/config.py` - SOCKET_PATH and BASE_DIR constants

  **API/Type References** (contracts to implement against):
  - `os.path.exists()` - Check if file exists
  - `os.remove()` - Remove file
  - `os.unlink()` - Alternative remove (same behavior)
  - `socket.connect_ex()` - Check if socket is connected

  **Test References** (testing patterns to follow):
  - No specific test patterns - verify by running app

  **Documentation References** (specs and requirements):
  - `AGENTS.md` - Socket communication and agent lifecycle requirements

  **External References** (libraries and frameworks):
  - Python os module: `https://docs.python.org/3/library/os.html` - File operations
  - Python socket module: `https://docs.python.org/3/library/socket.html` - Socket operations

  **WHY Each Reference Matters**:
  - `main_tray.py:94-113`: Current agent online check - needs to be more robust
  - `main_tray.py:43-92`: Agent startup - needs socket cleanup before starting
  - `config.py`: SOCKET_PATH constant - use instead of hardcoding

  **Acceptance Criteria**:
  - [ ] _is_agent_online() checks both socket file existence AND actual connection
  - [ ] Agent startup removes stale socket files before starting new agent
  - [ ] Socket file only removed if no process is actively using it
  - [ ] Python syntax check passes: `python -m py_compile App/webview_ui/main_tray.py`
  - [ ] Debug logging shows socket cleanup actions

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  **Python Logic Verification:**

  ```
  Scenario: Socket cleanup removes stale socket files
    Tool: Bash (python -c)
    Preconditions: None
    Steps:
      1. Create test directory: mkdir -p /tmp/test_agent_cleanup
      2. Create stale socket file: /tmp/test_agent_cleanup/agent.sock
      3. Create test script:
         ```python
         import os
         import socket

         SOCKET_PATH = "/tmp/test_agent_cleanup/agent.sock"

         def cleanup_stale_socket():
             """Remove socket file if it exists"""
             if os.path.exists(SOCKET_PATH):
                 print(f"Socket file exists: {SOCKET_PATH}")
                 try:
                     # Try to connect - if fails, socket is stale
                     sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                     sock.settimeout(1)
                     result = sock.connect_ex(SOCKET_PATH)
                     sock.close()

                     if result != 0:
                         print("Socket not connected, removing...")
                         os.unlink(SOCKET_PATH)
                         print(f"Removed: {SOCKET_PATH}")
                         return True
                     else:
                         print("Socket is active, not removing")
                         return False
                 except Exception as e:
                     print(f"Socket connection failed: {e}, removing...")
                     os.unlink(SOCKET_PATH)
                     print(f"Removed: {SOCKET_PATH}")
                     return True
             return False

         # Test with stale socket
         result = cleanup_stale_socket()
         assert result == True, "Should remove stale socket"
         assert not os.path.exists(SOCKET_PATH), "Socket should be removed"
         print("Test 1 passed: Stale socket removed")

         # Test with no socket
         result = cleanup_stale_socket()
         assert result == False, "Should return False when no socket"
         print("Test 2 passed: No socket case handled")
         ```
      4. Run test script
      5. Check output

    Expected Result: Socket cleanup function removes stale sockets, returns correct status
    Evidence: Test script output captured
  ```

  **File Operations Verification:**

  ```
  Scenario: main_tray.py compiles without errors
    Tool: Bash (python -m py_compile)
    Preconditions: File exists at App/webview_ui/main_tray.py
    Steps:
      1. Run: python -m py_compile App/webview_ui/main_tray.py
      2. Check exit code

    Expected Result: Exit code is 0 (no syntax errors)
    Evidence: Exit code captured
  ```

  **Evidence to Capture**:
  - [ ] Test script output in .sisyphus/evidence/task-3-socket-cleanup-test.txt
  - [ ] Compiler output in .sisyphus/evidence/task-3-syntax-check.txt

  **Commit**: YES
  - Message: `fix(navigation): fix nav watcher ready check, tab clicks, agent socket cleanup`
  - Files: App/webview_ui/webview_runner.py, App/webview_ui/web/js/app.js, App/webview_ui/main_tray.py
  - Pre-commit: `python -m py_compile App/webview_ui/webview_runner.py && python -m py_compile App/webview_ui/main_tray.py`

- [x] 4. End-to-End Integration Test

  **What to do**:
  - Run the full application and verify all three fixes work together
  - Test tray menu navigation to all pages (dashboard, settings, details)
  - Test tab clicking in webview window
  - Test agent stop/start/restart from tray menu
  - Verify no regressions in other features

  **Must NOT do**:
  - Don't just verify individual fixes - test complete workflow
  - Don't skip any test scenarios

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Integration testing - run app and verify behavior - straightforward testing
  - **Skills**: `['playwright']`
    - `playwright`: For browser automation if web UI needs testing
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final)
  - **Blocks**: None (final task)
  - **Blocked By**: Tasks 1, 2, 3

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `App/webview_ui/main_tray.py` - Application entry point
  - `AGENTS.md` - Running app from source instructions

  **API/Type References** (contracts to implement against):
  - Application interface - tray menu actions and webview window behavior

  **Test References** (testing patterns to follow):
  - `AGENTS.md` - Test commands: pytest, building app

  **Documentation References** (specs and requirements):
  - Original requirements: menu navigation, tab clicks, agent restart

  **External References** (libraries and frameworks):
  - None needed - standard app testing

  **WHY Each Reference Matters**:
  - `main_tray.py`: Entry point to run the application
  - `AGENTS.md`: Instructions for running and testing the application

  **Acceptance Criteria**:
  - [ ] Tray menu navigation works: clicking "Show Main Window", "Settings", "Details" opens correct page
  - [ ] Tab clicks work on first click: all tabs switch view immediately
  - [ ] Agent start/stop/restart works: agent can be started after being stopped
  - [ ] No regressions: all original features still working

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  **Application Testing:**

  ```
  Scenario: Tray menu navigation switches webview pages correctly
    Tool: interactive_bash (tmux) - Run app and test tray menu
    Preconditions: App built and ready to run
    Steps:
      1. cd App/webview_ui
      2. Start app: python -m main_tray (in tmux session)
      3. Wait for: Tray icon appears or "Starting OpenCode Token Meter" in output
      4. Note: Record PID for cleanup
      5. Create nav files manually to simulate tray menu clicks:
         - Create ~/Library/Application Support/OpenCode Token Meter/nav.json with {"target": "settings", "timestamp": 1234567890}
         - Wait: 2 seconds for nav watcher to process
      6. Check: Log shows "Executing nav switch to: settings"
      7. Verify: Webview window is showing settings view (check window title or content if possible)
      8. Test dashboard: Update nav.json to {"target": "dashboard", "timestamp": 1234567891}
      9. Wait: 2 seconds
      10. Check: Log shows "Executing nav switch to: dashboard"
      11. Test details: Update nav.json to {"target": "details", "timestamp": 1234567892}
      12. Wait: 2 seconds
      13. Check: Log shows "Executing nav switch to: details"
      14. Cleanup: Kill app process
    Expected Result: All three nav commands execute successfully, logs show correct page switches
    Evidence: Terminal output captured, nav log file content
  ```

  **Tab Navigation Test:**

  ```
  Scenario: Tab clicks work on single click in webview window
    Tool: Playwright (if web UI can be automated) or interactive_bash
    Preconditions: App running, webview window open
    Steps:
      1. Open webview window (if not already open)
      2. If using Playwright: Attach to webview window or navigate to index.html in browser
      3. Wait for: Navigation tabs visible
      4. Click: Dashboard tab (data-view="dashboard")
      5. Wait for: 500ms
      6. Check: Dashboard view visible, dashboard tab has active class
      7. Click: Settings tab (data-view="settings")
      8. Wait for: 500ms
      9. Check: Settings view visible, settings tab has active class
      10. Click: Details tab (data-view="details")
      11. Wait for: 500ms
      12. Check: Details view visible, details tab has active class
      13. Repeat: Click each tab again to verify switching back and forth
    Expected Result: All tab switches happen immediately on first click
    Evidence: Screenshots showing each view, click counter logs (if added)
  ```

  **Agent Restart Test:**

  ```
  Scenario: Agent can be stopped and restarted from tray
    Tool: interactive_bash (tmux)
    Preconditions: App running, agent active
    Steps:
      1. Check agent status: Check if ~/Library/Application Support/OpenCode Token Meter/agent.sock exists and can connect
      2. Stop agent: Send shutdown command via socket or kill agent process if separate
      3. Wait: 3 seconds for agent to stop
      4. Check: agent.sock no longer exists or connection refused
      5. Restart agent: Trigger "Reconnect" from tray (or call _ensure_agent_running)
      6. Wait: 5 seconds for agent to start
      7. Check: agent.sock exists and connection succeeds
      8. Test: Send test command to agent (e.g., "ping" or status check)
      9. Verify: Agent responds correctly
    Expected Result: Agent stops cleanly and restarts successfully
    Evidence: Terminal output showing agent stop/restart, socket connection tests
  ```

  **Evidence to Capture**:
  - [ ] Tray navigation log in .sisyphus/evidence/task-4-tray-nav-log.txt
  - [ ] Tab click screenshots in .sisyphus/evidence/task-4-tab-*.png
  - [ ] Agent restart log in .sisyphus/evidence/task-4-agent-restart.txt

  **Commit**: NO (all changes already committed in Task 3)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1, 2, 3 | `fix(navigation): fix nav watcher ready check, tab clicks, agent socket cleanup` | webview_runner.py, app.js, main_tray.py | python -m py_compile App/webview_ui/webview_runner.py && python -m py_compile App/webview_ui/main_tray.py |
| 4 | (skipped - integration test only) | - | - |

---

## Success Criteria

### Verification Commands
```bash
# Syntax checks
python -m py_compile App/webview_ui/webview_runner.py
python -m py_compile App/webview_ui/main_tray.py

# Run app
cd App/webview_ui && python -m main_tray

# Test nav file mechanism (simulated)
cat > ~/Library/Application\ Support/OpenCode\ Token\ Meter/nav.json <<EOF
{"target": "settings", "timestamp": 1234567890}
EOF
```

### Final Checklist
- [x] Tray menu navigation works (Show Main Window, Settings, Details)
- [x] Tab clicks work on single click
- [x] Agent restarts properly after being stopped
- [x] All Python files compile without syntax errors
- [x] No regressions in existing features
- [x] Debug logging shows expected behavior
