"""Main entry point for OpenCode Token Meter - Tray version with subprocess webview

This version runs the system tray on the main thread and spawns a subprocess 
for the webview window, solving the macOS threading conflict.
"""
import os
import sys
import subprocess
import argparse
import atexit
import signal
import platform
import time
import json
import socket
import threading
import asyncio

# Add paths for imports
# 1. Agent path (App/agent)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
# 2. App root path (App/) to allow imports like 'webview_ui.stats_worker'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# 3. Webview UI path (App/webview_ui) to allow imports like 'backend'
sys.path.insert(0, os.path.dirname(__file__))


TrayManager = None
try:
    if platform.system() == "Darwin":
        from .backend.tray_rumps import TrayManager
    else:
        from .backend.tray import TrayManager
except ImportError as e1:
    try:
        if platform.system() == "Darwin":
            from backend.tray_rumps import TrayManager
        else:
            from backend.tray import TrayManager
    except ImportError as e2:
        print(f"[WARN] Failed to import TrayManager: {e2}")
        TrayManager = None

# Import agent config for socket paths - THIS IS THE CORRECT WAY
from agent.config import BASE_DIR, SOCKET_PATH, TCP_HOST, TCP_PORT, USE_TCP
from backend.settings import Settings

# Import modules for threading
try:
    import agent.__main__ as agent_main
    # Try different import paths for stats_worker
    try:
        # If running from App/, this works
        import webview_ui.stats_worker as stats_worker
    except ImportError:
        # If running from App/webview_ui/, this works
        import stats_worker
except ImportError as e:
    print(f"[ERROR] Failed to import modules for threading: {e}")

# PID file to track webview process
WEBVIEW_PID_FILE = os.path.join(BASE_DIR, "webview.pid")
STATS_FILE = os.path.join(BASE_DIR, "tray_stats.json")
NAV_FILE = os.path.join(BASE_DIR, "nav.json")


class TrayAppWithSubprocess:
    """Main application that runs tray and manages webview subprocess"""
    
    def __init__(self, debug=False, show_window=False):
        self.debug = debug
        self.show_window = show_window
        self.webview_process = None
        self.platform = platform.system()
        self.agent_client = None
        self._cleanup_called = False
        
        # Threading controls
        self.agent_thread = None
        self.agent_stop_event = threading.Event()
        self.stats_thread = None
        self.stats_stop_event = threading.Event()

    def _start_agent_thread(self):
        """Start the agent in a background thread"""
        print("[INFO] Starting Agent thread...")
        
        def agent_runner():
            try:
                # asyncio.run() creates a new event loop for this thread
                asyncio.run(agent_main.main(threading_stop_event=self.agent_stop_event))
            except Exception as e:
                print(f"[ERROR] Agent thread failed: {e}")

        self.agent_thread = threading.Thread(target=agent_runner, name="AgentThread", daemon=True)
        self.agent_thread.start()

    def _start_stats_thread(self):
        """Start the stats worker in a background thread"""
        print("[INFO] Starting Stats Worker thread...")
        
        def stats_runner():
            try:
                stats_worker.main(stop_event=self.stats_stop_event)
            except Exception as e:
                print(f"[ERROR] Stats worker thread failed: {e}")
                
        self.stats_thread = threading.Thread(target=stats_runner, name="StatsThread", daemon=True)
        self.stats_thread.start()

    def _get_webview_pid(self):
        """Get stored webview PID"""
        try:
            if os.path.exists(WEBVIEW_PID_FILE):
                with open(WEBVIEW_PID_FILE, 'r') as f:
                    return int(f.read().strip())
        except:
            pass
        return None
    
    def _save_webview_pid(self, pid):
        """Store webview PID"""
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(WEBVIEW_PID_FILE, 'w') as f:
            f.write(str(pid))
    
    def _clear_webview_pid(self):
        """Clear stored webview PID"""
        try:
            if os.path.exists(WEBVIEW_PID_FILE):
                os.remove(WEBVIEW_PID_FILE)
        except:
            pass

    def _is_webview_running(self):
        """Check if webview process is still running with robust verification"""
        pid = self._get_webview_pid()
        if pid is None:
            return False
            
        try:
            # Basic existence check
            os.kill(pid, 0)
        except OSError:
            self._clear_webview_pid()
            return False

        # Advanced check: Verify the process is actually ours
        # This prevents PID reuse conflicts (stale PID file pointing to a new unrelated process)
        try:
            # Use ps to get command line for the pid
            # Output format: "command_args"
            cmd = ["ps", "-p", str(pid), "-o", "command="]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout.strip()
                # Check keywords that should be in our webview process
                # Frozen: "OpenCode Token Meter" or similar
                # Dev: "python" and "main.py"
                if "main.py" in output or "OpenCode Token Meter" in output or "webview" in output:
                    return True
                else:
                    print(f"[INFO] PID {pid} exists but seems to be a different process: {output[:50]}...")
                    self._clear_webview_pid()
                    return False
            else:
                # ps failed? Assume running if kill changed nothing, but maybe not?
                # If ps failed, satisfy with kill check
                return True
        except Exception as e:
            print(f"[WARN] Failed to verify process args: {e}")
            return True # Fallback to trusting os.kill logic if ps fails
            
        return True

    def _write_nav_file(self, page):
        """Write navigation command to file for webview to read"""
        nav_data = {"target": page, "timestamp": time.time()}
        try:
            os.makedirs(BASE_DIR, exist_ok=True)
            with open(NAV_FILE, 'w') as f:
                json.dump(nav_data, f)
        except Exception as e:
            print(f"[WARN] Failed to write nav file: {e}")

    def start_webview_subprocess(self, page='dashboard'):
        """Start webview in a separate subprocess (only if not already running)"""
        # Check if already running
        if self._is_webview_running():
            print(f"[INFO] Webview already running (PID: {self._get_webview_pid()}), navigating to {page}")
            self._write_nav_file(page)
            return

        if self.webview_process is not None:
            if self.webview_process.poll() is None:
                print(f"[INFO] Webview subprocess already running (PID: {self.webview_process.pid})")
                self._write_nav_file(page)
                return
            else:
                self.webview_process = None

        # Build command with page parameter
        if getattr(sys, 'frozen', False):
            # In frozen mode, call the executable with --webview flag
            cmd = [sys.executable, '--webview', '--page', page]
        else:
            # Get the current script path
            # Use main.py instead of webview_runner.py
            webview_script = os.path.join(os.path.dirname(__file__), 'main.py')
            if not os.path.exists(webview_script):
                print(f"[ERROR] Webview script not found: {webview_script}")
                return
            cmd = [sys.executable, webview_script, '--no-tray', '--page', page]

        if self.debug:
            cmd.append('--debug')

        print(f"[INFO] Starting webview subprocess with command: {cmd}")

        # Start subprocess - capture output for debugging
        stdout_dest = None if self.debug else subprocess.DEVNULL
        stderr_dest = None if self.debug else subprocess.DEVNULL

        if getattr(sys, 'frozen', False):
            # In frozen mode, log subprocess output to a file if needed, or let it go to system log
            self.webview_process = subprocess.Popen(
                cmd,
                stdout=stdout_dest,
                stderr=stderr_dest,
                start_new_session=True
            )
        else:
            # In dev mode, inherit stdout/stderr so we can see it in terminal
            self.webview_process = subprocess.Popen(
                cmd,
                stdout=stdout_dest, 
                stderr=stderr_dest,
                start_new_session=True
            )

        # Store PID
        self._save_webview_pid(self.webview_process.pid)
        print(f"[INFO] Webview started (PID: {self.webview_process.pid})")

        # Register cleanup
        atexit.register(self.cleanup_webview)

    def cleanup_webview(self):
        """Clean up webview subprocess"""
        pid = None
        if self.webview_process is not None:
            try:
                pid = self.webview_process.pid
                self.webview_process.terminate()
                self.webview_process.wait(timeout=5)
            except Exception as e:
                print(f"[WARN] Error cleaning up webview process: {e}")
            self.webview_process = None

        if pid is None:
            pid = self._get_webview_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        self._clear_webview_pid()
            
    def on_show_window(self, page='dashboard'):
        """Called when user requests to show window"""
        print(f"[INFO] Show window requested with page: {page}")
        self.start_webview_subprocess(page=page)

    def on_refresh(self):
        """Called when user requests refresh"""
        print("[INFO] Refresh requested")
        # Since agent is running in this process (different thread), we could technically call it directly?
        # But for thread safety, using the IPC mechanism is still safest and simplest without refactoring everything.
        try:
            msg = json.dumps({"cmd": "refresh"}) + "\n"
            if USE_TCP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((TCP_HOST, TCP_PORT))
                sock.sendall(msg.encode())
                sock.close()
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(SOCKET_PATH)
                sock.sendall(msg.encode())
                sock.close()
            print("[INFO] Refresh command sent to agent")
        except Exception as e:
            print(f"[WARN] Failed to send refresh command: {e}")

    def on_details(self):
        """Called when user requests details view"""
        print("[INFO] Show details requested")
        self.on_show_window(page='details')

    def on_export(self, scope):
        """Called when user requests export"""
        print(f"[INFO] Export requested: {scope}")
        self.on_show_window(page='details')

    def on_settings(self):
        """Called when user requests settings"""
        print("[INFO] Settings requested")
        self.on_show_window(page='settings')

    def on_reconnect(self):
        """Called when user requests agent reconnect"""
        print("[INFO] Reconnect requested - Restarting Agent Thread")
        
        # Stop existing
        self.agent_stop_event.set()
        if self.agent_thread and self.agent_thread.is_alive():
            self.agent_thread.join(timeout=2)
            
        # Restart
        self.agent_stop_event.clear()
        self._start_agent_thread()
        
    def on_quit(self):
        """Called when user requests quit"""
        print("[INFO] Quit requested")
        self._cleanup_on_exit()
        # Do NOT call sys.exit(0) here - let rumps handle the exit loop
        # The TrayManager will call rumps.quit_application() after this callback returns

    def _cleanup_on_exit(self):
        if self._cleanup_called:
            return
        self._cleanup_called = True
        
        print("[INFO] Cleaning up threads and processes...")
        
        # Signal threads to stop
        self.agent_stop_event.set()
        self.stats_stop_event.set()
        
        # Cleanup webview
        self.cleanup_webview()
        
        # Wait for threads? (Optional, daemon threads will be killed anyway on exit)
        # But better to be explicit if possible.
        
    def run(self):
        """Run the application"""
        print(f"[INFO] Starting OpenCode Token Meter (Tray Mode) on {self.platform}")
        
        # Ensure BASE_DIR exists
        os.makedirs(BASE_DIR, exist_ok=True)
        
        # Start background threads
        self._start_agent_thread()
        self._start_stats_thread()

        atexit.register(self._cleanup_on_exit)
        
        # Create and run tray with all callbacks
        if TrayManager is None:
            print("[ERROR] TrayManager not available. Falling back to window-only mode.")
            # Launch window directly and exit tray process since we can't show tray
            self.start_webview_subprocess(page='dashboard')
            # Wait for subprocess?
            if self.webview_process:
                self.webview_process.wait()
            return

        settings = Settings()

        refresh_interval = settings.get("refresh_interval", 5)
        notifications_enabled = settings.get("notifications_enabled", True)
        tray = TrayManager(
            on_show=self.on_show_window,
            on_quit=self.on_quit,
            notifications_enabled=notifications_enabled
        )
        try:
            refresh_interval = max(1, int(refresh_interval))
        except (TypeError, ValueError):
            refresh_interval = 5
        tray.start_auto_update(STATS_FILE, interval=refresh_interval)
        
        # Auto-show window if requested
        if self.show_window:
            print("[INFO] Auto-showing window on startup")
            # We need to defer this slightly to ensure tray is ready? 
            # Or just call it directly. subprocess call is non-blocking to tray loop.
            self.start_webview_subprocess(page='dashboard')
            
        tray.run()


def main(debug=False, show_window=False):
    """Main entry point"""
    app = TrayAppWithSubprocess(debug=debug, show_window=show_window)
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode Token Meter - Tray Mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--window", action="store_true", help="Show window on startup")
    args = parser.parse_args()
    
    main(debug=args.debug, show_window=args.window)
