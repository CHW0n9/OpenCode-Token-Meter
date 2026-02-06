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
    from .backend.tray_rumps import TrayManager
except ImportError:
    from backend.tray_rumps import TrayManager

# Import agent config for socket paths - THIS IS THE CORRECT WAY
from agent.config import BASE_DIR, SOCKET_PATH, TCP_HOST, TCP_PORT, USE_TCP

# PID file to track webview process
WEBVIEW_PID_FILE = os.path.join(BASE_DIR, "webview.pid")
NAV_FILE = os.path.join(BASE_DIR, "nav.json")


class TrayAppWithSubprocess:
    """Main application that runs tray and manages webview subprocess"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.webview_process = None
        self.platform = platform.system()
        self.agent_client = None
        
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
        
        # Agent paths - from webview_ui perspective
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
            agent_main = os.path.join(agent_path, "agent", "__main__.py")
            print(f"[DEBUG] Checking agent path: {agent_path}, exists: {os.path.exists(agent_path)}")
            
            if os.path.exists(agent_path):
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

        # Get the current script path
        if hasattr(sys, 'frozen'):
            webview_script = os.path.join(os.path.dirname(sys.executable), '..', 'Resources', 'webview_runner.py')
        else:
            webview_script = os.path.join(os.path.dirname(__file__), 'webview_runner.py')

        if not os.path.exists(webview_script):
            print(f"[ERROR] Webview runner script not found: {webview_script}")
            return

        # Build command with page parameter
        cmd = [sys.executable, webview_script, '--page', page]
        if self.debug:
            cmd.append('--debug')

        print(f"[INFO] Starting webview subprocess...")

        # Start subprocess
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
        if self.webview_process is not None:
            try:
                self.webview_process.terminate()
                self.webview_process.wait(timeout=5)
            except Exception as e:
                print(f"[WARN] Error cleaning up webview process: {e}")
            self.webview_process = None
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
        self.cleanup_webview()
        sys.exit(0)
        
    def run(self):
        """Run the application"""
        print(f"[INFO] Starting OpenCode Token Meter (Tray Mode) on {self.platform}")
        
        # Ensure BASE_DIR exists
        os.makedirs(BASE_DIR, exist_ok=True)
        
        # Ensure agent is running before starting tray
        self._ensure_agent_running()
        
        # Create and run tray with all callbacks
        tray = TrayManager(
            api=None,
            on_show=self.on_show_window,
            on_refresh=self.on_refresh,
            on_quit=self.on_quit,
            on_details=self.on_details,
            on_export=self.on_export,
            on_settings=self.on_settings,
            on_reconnect=self.on_reconnect,
            on_navigate=self.on_show_window
        )
        
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
