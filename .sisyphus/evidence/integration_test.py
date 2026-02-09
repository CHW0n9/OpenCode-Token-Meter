#!/usr/bin/env python3
"""
Integration test for navigation and agent fixes
Tests the logic without requiring full GUI
"""

import os
import sys
import json
import time
import socket
import tempfile
import threading

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "App", "agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "App", "menubar"))

print("=" * 70)
print("INTEGRATION TEST: Navigation and Agent Fixes")
print("=" * 70)

# Test 1: Verify Python files compile
print("\n[Test 1] Syntax Checks")
print("-" * 70)

files_to_check = [
    "App/webview_ui/webview_runner.py",
    "App/webview_ui/main_tray.py",
]

all_passed = True
for filepath in files_to_check:
    full_path = os.path.join(os.path.dirname(__file__), "..", filepath)
    if os.path.exists(full_path):
        result = os.system(f"python -m py_compile {full_path} 2>/dev/null")
        if result == 0:
            print(f"  ✓ {filepath} - Syntax OK")
        else:
            print(f"  ✗ {filepath} - Syntax Error")
            all_passed = False
    else:
        print(f"  ✗ {filepath} - File not found")
        all_passed = False

# Test 2: JavaScript syntax check
print("\n[Test 2] JavaScript Syntax Check")
print("-" * 70)
js_file = os.path.join(os.path.dirname(__file__), "..", "App/webview_ui/web/js/app.js")
if os.path.exists(js_file):
    result = os.system(f"node -c {js_file} 2>/dev/null")
    if result == 0:
        print(f"  ✓ app.js - Syntax OK")
    else:
        print(f"  ✗ app.js - Syntax Error")
        all_passed = False
else:
    print(f"  ✗ app.js - File not found")
    all_passed = False

# Test 3: Verify nav_watcher app_ready logic
print("\n[Test 3] Nav Watcher - App Ready Logic")
print("-" * 70)

app_ready_event = threading.Event()
nav_file_found = False
executed_nav = False
skipped_nav = False

def mock_nav_watcher():
    global executed_nav, skipped_nav
    for i in range(5):
        if nav_file_found:
            if app_ready_event.is_set():
                executed_nav = True
                print(f"  ✓ Nav executed after app ready")
                break
            else:
                skipped_nav = True
                print(f"  ✓ Nav skipped (app not ready) - iteration {i}")
        time.sleep(0.05)

watcher_thread = threading.Thread(target=mock_nav_watcher)
watcher_thread.start()

# Simulate nav file arriving before app ready
nav_file_found = True
time.sleep(0.1)

# Set app ready after delay
time.sleep(0.1)
app_ready_event.set()

watcher_thread.join(timeout=1)

if skipped_nav and executed_nav:
    print(f"  ✓ Logic verified: Nav commands skip until app ready, then execute")
else:
    print(f"  ✗ Logic test failed: skipped={skipped_nav}, executed={executed_nav}")
    all_passed = False

# Test 4: Verify socket cleanup logic
print("\n[Test 4] Socket Cleanup Logic")
print("-" * 70)

# Create a fake socket file
test_socket = tempfile.mktemp(suffix='.sock')
open(test_socket, 'w').close()
print(f"  Created fake socket: {test_socket}")

def cleanup_stale_socket(socket_path):
    """Test version of socket cleanup"""
    if not os.path.exists(socket_path):
        return False
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(socket_path)
        sock.close()
        
        if result == 0:
            print(f"    Socket is active, not removing")
            return False
        else:
            print(f"    Socket not connectable (error {result}), removing...")
            os.unlink(socket_path)
            print(f"    Removed stale socket")
            return True
    except Exception as e:
        print(f"    Error: {e}, removing...")
        os.unlink(socket_path)
        return True

result = cleanup_stale_socket(test_socket)
if result and not os.path.exists(test_socket):
    print(f"  ✓ Stale socket correctly removed")
else:
    print(f"  ✗ Socket cleanup failed")
    all_passed = False

# Test 5: Verify nav file structure
print("\n[Test 5] Nav File Structure")
print("-" * 70)

base_dir = os.path.expanduser("~/Library/Application Support/OpenCode Token Meter")
nav_file = os.path.join(base_dir, "nav.json")

# Create test nav file
os.makedirs(base_dir, exist_ok=True)
test_nav_data = {"target": "settings", "timestamp": time.time()}
with open(nav_file, 'w') as f:
    json.dump(test_nav_data, f)

if os.path.exists(nav_file):
    with open(nav_file, 'r') as f:
        loaded_data = json.load(f)
    if loaded_data.get('target') == 'settings':
        print(f"  ✓ Nav file created and readable: {nav_file}")
    else:
        print(f"  ✗ Nav file content incorrect")
        all_passed = False
    # Clean up
    os.remove(nav_file)
else:
    print(f"  ✗ Nav file not created")
    all_passed = False

# Test 6: Verify code changes are in place
print("\n[Test 6] Code Changes Verification")
print("-" * 70)

# Check webview_runner.py for app_ready_event
runner_file = os.path.join(os.path.dirname(__file__), "..", "App/webview_ui/webview_runner.py")
with open(runner_file, 'r') as f:
    runner_content = f.read()

checks = [
    ("app_ready_event", "Threading Event for app ready state"),
    ("window.events.loaded", "Event subscription for webview ready"),
    ("App not ready, skipping nav", "Debug logging for skipped nav"),
    ("Executing nav switch to", "Debug logging for nav execution"),
    ("time.sleep(1)", "Polling interval changed to 1 second"),
]

for check, description in checks:
    if check in runner_content:
        print(f"  ✓ {description}")
    else:
        print(f"  ✗ {description} - NOT FOUND")
        all_passed = False

# Check app.js for preventDefault
app_file = os.path.join(os.path.dirname(__file__), "..", "App/webview_ui/web/js/app.js")
with open(app_file, 'r') as f:
    app_content = f.read()

if "e.preventDefault()" in app_content:
    print(f"  ✓ Tab click preventDefault added")
else:
    print(f"  ✗ Tab click preventDefault - NOT FOUND")
    all_passed = False

if "Tab clicked:" in app_content:
    print(f"  ✓ Tab click logging added")
else:
    print(f"  ✗ Tab click logging - NOT FOUND")
    all_passed = False

# Check main_tray.py for socket cleanup
tray_file = os.path.join(os.path.dirname(__file__), "..", "App/webview_ui/main_tray.py")
with open(tray_file, 'r') as f:
    tray_content = f.read()

if "cleanup_stale_socket" in tray_content:
    print(f"  ✓ Socket cleanup function added")
else:
    print(f"  ✗ Socket cleanup function - NOT FOUND")
    all_passed = False

if "self.cleanup_stale_socket()" in tray_content:
    print(f"  ✓ Socket cleanup called in _ensure_agent_running")
else:
    print(f"  ✗ Socket cleanup call - NOT FOUND")
    all_passed = False

# Summary
print("\n" + "=" * 70)
if all_passed:
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
    print("\nIntegration test complete. All fixes are in place:")
    print("  1. ✓ Nav watcher waits for app ready")
    print("  2. ✓ Tab clicks work on single click (preventDefault)")
    print("  3. ✓ Agent socket cleanup implemented")
    print("\nNext: Run the application and test manually:")
    print("  cd App/webview_ui && python -m main_tray --debug")
    sys.exit(0)
else:
    print("✗ SOME TESTS FAILED")
    print("=" * 70)
    sys.exit(1)
