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

# Add paths for imports - must add agent first
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))

try:
    if platform.system() == "Darwin":
        from .backend.tray_rumps import TrayManager
    else:
        from .backend.tray import TrayManager
except ImportError:
    if platform.system() == "Darwin":
        from backend.tray_rumps import TrayManager
    else:
        from backend.tray import TrayManager

# Import agent config for socket paths - THIS IS THE CORRECT WAY
from agent.config import BASE_DIR, SOCKET_PATH, TCP_HOST, TCP_PORT, USE_TCP
from menubar.settings import Settings

# PID file to track webview process
WEBVIEW_PID_FILE = os.path.join(BASE_DIR, "webview.pid")
STATS_WORKER_PID_FILE = os.path.join(BASE_DIR, "stats_worker.pid")
STATS_FILE = os.path.join(BASE_DIR, "tray_stats.json")
NAV_FILE = os.path.join(BASE_DIR, "nav.json")


class TrayAppWithSubprocess:
    """Main application that runs tray and manages webview subprocess"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.webview_process = None
        self.platform = platform.system()
        self.agent_client = None
        self._cleanup_called = False
        self._stats_log_file = None
        
    def cleanup_stale_socket(self):
        """Remove stale socket files before starting agent"""
        if USE_TCP:
            # TCP doesn't leave stale files, nothing to clean
            return False
        
        if not os.path.exists(SOCKET_PATH):
            return False
        
        try:
            # Try to connect - if fails, socket is stale
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(SOCKET_PATH)
            sock.close()
            
            if result == 0:
                print(f"[DEBUG] Socket is active, not removing")
                return False
            else:
                print(f"[INFO] Socket exists but not connectable (error {result}), removing stale file...")
                os.unlink(SOCKET_PATH)
                print(f"[INFO] Removed stale socket file: {SOCKET_PATH}")
                return True
        except Exception as e:
            print(f"[WARN] Error checking socket: {e}, attempting removal...")
            try:
                os.unlink(SOCKET_PATH)
                print(f"[INFO] Removed socket file after error: {SOCKET_PATH}")
                return True
            except Exception as e2:
                print(f"[WARN] Failed to remove socket: {e2}")
                return False
    
    def _ensure_agent_running(self):
        """Ensure the background agent is running"""
        print("[INFO] Checking agent status...")
        
        # Check if agent is already online
        if self._is_agent_online():
            print("[INFO] Agent is already running")
            return True
        
        # Clean up any stale socket files before starting
        self.cleanup_stale_socket()
        
        print("[INFO] Agent not running, attempting to start...")
        
        # Check if running in PyInstaller bundle
        if getattr(sys, 'frozen', False):
            print("[INFO] Detected PyInstaller bundle - starting embedded agent module")
            try:
                # In frozen mode, the agent module is embedded in the executable
                # We can run it by invoking the executable with -m agent
                # However, since we are the executable, we need a way to tell main to run agent
                # So we use a flag --run-agent which we will implement in __main__.py
                
                # Verify agent module is importable
                import agent
                print(f"[INFO] Agent module found: {agent.__file__}")
                
                # Log agent output to file for debugging
                log_path = os.path.expanduser("~/Library/Application Support/OpenCode Token Meter/agent_subprocess.log")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                log_file = open(log_path, "w")
                
                proc = subprocess.Popen(
                    [sys.executable, "--agent"],
                    start_new_session=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
                print(f"[INFO] Embedded agent process started with PID: {proc.pid}")
                
                # Wait for agent to initialize
                time.sleep(3)
                
                if self._is_agent_online():
                    print("[INFO] Embedded agent started successfully")
                    return True
                else:
                    print("[WARN] Embedded agent started but not online yet")
            except Exception as e:
                print(f"[ERROR] Failed to start embedded agent: {e}")

        # Development mode - look for source paths
        # webview_ui/.. = App/
        app_dir = os.path.dirname(__file__)
        agent_parent = os.path.dirname(app_dir)  # App/
        
        agent_paths = [
            # Development path: App/agent
            os.path.join(agent_parent, "agent"),
            # Desktop development path
            os.path.expanduser("~/Desktop/OpenCode Token Meter/App/agent"),
        ]
        
        for agent_path in agent_paths:
            if not os.path.exists(agent_path):
                continue
                
            print(f"[INFO] Starting agent from: {agent_path}")
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "agent"],
                    cwd=agent_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                print(f"[DEBUG] Agent process started with PID: {proc.pid}")
                
                # Wait for agent to initialize
                time.sleep(3)
                
                if self._is_agent_online():
                    print("[INFO] Agent started successfully")
                    return True
            except Exception as e:
                print(f"[WARN] Failed to start agent from {agent_path}: {e}")
        
        print("[WARN] Could not start agent - will retry when window opens")
        return False
    
    def _is_agent_online(self):
        """Check if agent is responding via socket"""
        try:
            if USE_TCP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((TCP_HOST, TCP_PORT))
                sock.close()
                return result == 0
            else:
                if not os.path.exists(SOCKET_PATH):
                    return False
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(SOCKET_PATH)
                sock.close()
                return result == 0
        except Exception as e:
            print(f"[DEBUG] Agent check error: {e}")
            return False
    
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

    def _get_stats_worker_pid(self):
        """Get stored stats worker PID"""
        try:
            if os.path.exists(STATS_WORKER_PID_FILE):
                with open(STATS_WORKER_PID_FILE, 'r') as f:
                    return int(f.read().strip())
        except:
            pass
        return None

    def _save_stats_worker_pid(self, pid):
        """Store stats worker PID"""
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(STATS_WORKER_PID_FILE, 'w') as f:
            f.write(str(pid))

    def _clear_stats_worker_pid(self):
        """Clear stored stats worker PID"""
        try:
            if os.path.exists(STATS_WORKER_PID_FILE):
                os.remove(STATS_WORKER_PID_FILE)
        except:
            pass

    def _is_pid_running(self, pid):
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def _is_webview_running(self):
        """Check if webview process is still running"""
        pid = self._get_webview_pid()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            self._clear_webview_pid()
            return False

    def _start_stats_worker(self):
        """Start stats worker process if not running"""
        pid = self._get_stats_worker_pid()
        if pid and self._is_pid_running(pid):
            return
        if pid:
            self._clear_stats_worker_pid()

        app_dir = os.path.dirname(__file__)
        app_parent = os.path.dirname(app_dir)

        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--stats-worker"]
            env = None
            cwd = app_parent
        else:
            module_name = "webview_ui"
            cwd = app_parent
            env = os.environ.copy()

            # If running from repo root with App/ package, use App.webview_ui
            if os.path.basename(app_parent) == "App" and os.path.exists(os.path.join(app_parent, "__init__.py")):
                repo_root = os.path.dirname(app_parent)
                module_name = "App.webview_ui"
                cwd = repo_root
                env["PYTHONPATH"] = os.pathsep.join([repo_root, env.get("PYTHONPATH", "")])
            else:
                env["PYTHONPATH"] = os.pathsep.join([app_parent, env.get("PYTHONPATH", "")])

            cmd = [sys.executable, "-m", module_name, "--stats-worker"]

        try:
            os.makedirs(BASE_DIR, exist_ok=True)
            log_path = os.path.join(BASE_DIR, "stats_worker.log")
            self._stats_log_file = open(log_path, "a", encoding="utf-8")
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=self._stats_log_file,
                stderr=self._stats_log_file,
                start_new_session=True,
                env=env
            )
            self._save_stats_worker_pid(proc.pid)
        except Exception as e:
            print(f"[WARN] Failed to start stats worker: {e}")

    def cleanup_stats_worker(self):
        """Terminate stats worker process"""
        pid = self._get_stats_worker_pid()
        if pid is None:
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        self._clear_stats_worker_pid()
        try:
            if self._stats_log_file:
                self._stats_log_file.close()
        except Exception:
            pass
    
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
            webview_script = os.path.join(os.path.dirname(__file__), 'webview_runner.py')
            if not os.path.exists(webview_script):
                print(f"[ERROR] Webview runner script not found: {webview_script}")
                return
            cmd = [sys.executable, webview_script, '--page', page]

        if self.debug:
            cmd.append('--debug')

        print(f"[INFO] Starting webview subprocess with command: {cmd}")

        # Start subprocess - capture output for debugging in frozen mode
        if getattr(sys, 'frozen', False):
            # In frozen mode, log subprocess output to a file
            log_path = os.path.join(BASE_DIR, "webview_subprocess.log")
            print(f"[DEBUG] Webview subprocess log: {log_path}")
            log_file = open(log_path, 'w')
            self.webview_process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        else:
            self.webview_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
        self._ensure_agent_running()
        self.start_webview_subprocess(page=page)

    def on_refresh(self):
        """Called when user requests refresh"""
        print("[INFO] Refresh requested")
        if self._is_agent_online():
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
        else:
            print("[WARN] Agent not online, cannot refresh")

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
        print("[INFO] Reconnect requested")
        try:
            msg = json.dumps({"cmd": "shutdown"}) + "\n"
            if USE_TCP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((TCP_HOST, TCP_PORT))
                sock.sendall(msg.encode())
                sock.close()
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(SOCKET_PATH)
                sock.sendall(msg.encode())
                sock.close()
        except:
            pass
        
        time.sleep(1)
        self._ensure_agent_running()
        
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
        self.cleanup_webview()
        self.cleanup_stats_worker()
        try:
            msg = json.dumps({"cmd": "shutdown"}) + "\n"
            if USE_TCP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((TCP_HOST, TCP_PORT))
                sock.sendall(msg.encode())
                sock.close()
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(SOCKET_PATH)
                sock.sendall(msg.encode())
                sock.close()
        except Exception:
            pass
        
    def run(self):
        """Run the application"""
        print(f"[INFO] Starting OpenCode Token Meter (Tray Mode) on {self.platform}")
        
        # Ensure BASE_DIR exists
        os.makedirs(BASE_DIR, exist_ok=True)
        
        # Ensure agent is running before starting tray
        self._ensure_agent_running()
        self._start_stats_worker()

        atexit.register(self._cleanup_on_exit)
        
        # Create and run tray with all callbacks
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
        tray.run()


def main(debug=False):
    """Main entry point"""
    app = TrayAppWithSubprocess(debug=debug)
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode Token Meter - Tray Mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    main(debug=args.debug)
