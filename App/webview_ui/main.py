"""Main entry point for OpenCode Token Meter - Working Window Version"""

import os
import sys
import webview
import argparse
import time
import json
import threading
import atexit
import traceback


# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
# Add App/agent directory to path to allow 'from agent import ...' (finding App/agent/agent package)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

# Support both module import and direct execution
try:
    from .backend.api import JsApi
except ImportError:
    # Direct execution
    from backend.api import JsApi

from agent.config import BASE_DIR
from agent.logger import log_info, log_warn, log_error, log_debug

NAV_FILE = os.path.join(BASE_DIR, "nav.json")
PID_FILE = os.path.join(BASE_DIR, "webview.pid")

# Event to signal when webview app is ready to receive navigation commands
app_ready_event = threading.Event()


def cleanup_pid_file():
    """Clean up PID file on exit"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            log_info("Main", "Cleaned up webview PID file")
    except Exception as e:
        log_warn("Main", f"Failed to clean up PID file: {e}")


def save_pid():
    """Save current process PID to file"""
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        log_info("Main", f"Saved PID {os.getpid()} to {PID_FILE}")
    except Exception as e:
        log_warn("Main", f"Failed to save PID: {e}")


def get_web_dir():
    """Get the web directory path"""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            # PyInstaller onefile build (Windows/Linux): all assets extracted to sys._MEIPASS
            # Spec bundles web assets at: (web_dir, 'webview_ui/web')
            return os.path.join(meipass, "webview_ui", "web")
        # macOS .app bundle (onedir): Resources layout
        # sys.executable is .../Contents/MacOS/OpenCode Token Meter
        # Web files are in .../Contents/Resources/webview_ui/web
        return os.path.join(
            os.path.dirname(sys.executable), "..", "Resources", "webview_ui", "web"
        )
    return os.path.join(os.path.dirname(__file__), "web")


def create_window(api, debug=False, initial_page="dashboard"):
    """Create the main webview window"""
    web_dir = get_web_dir()
    index_path = os.path.join(web_dir, "index.html")

    if os.path.exists(index_path):
        # Pass local file path directly; pywebview's http_server will serve it
        # Append ?page= query parameter for JS-side routing
        url = index_path + f"?page={initial_page}"
        log_info("Main", f"Loading path: {url}")
    else:
        log_error("Main", f"index.html not found at {index_path}")
        url = "about:blank"

    # Create window
    window = webview.create_window(
        title="OpenCode Token Meter",
        url=url,
        js_api=api,
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True,
        fullscreen=False,
        hidden=False,
        background_color="#171717",  # Dark background to prevent white flash
    )

    return window


def apply_windows_titlebar_color(window):
    """Apply native Windows 10/11 dark mode and custom titlebar color"""
    import platform
    if platform.system() != "Windows":
        return
        
    try:
        import ctypes
        
        # Give the window a moment to initialize its handle
        time.sleep(0.5)
        
        # Try to find the window by its initial title
        hwnd = ctypes.windll.user32.FindWindowW(None, "OpenCode Token Meter")
        if not hwnd:
            hwnd = ctypes.windll.user32.FindWindowW(None, window.title)
            
        if not hwnd:
            log_debug("Main", "Could not find window handle for titlebar color")
            return
            
        # DWMWA constants for dark mode and colors
        DWMWA_USE_IMMERSIVE_DARK_MODE_V1 = 19  # Windows 10 1809
        DWMWA_USE_IMMERSIVE_DARK_MODE_V2 = 20  # Windows 10 1903+
        DWMWA_CAPTION_COLOR = 35               # Windows 11 Build 22000+
        DWMWA_TEXT_COLOR = 36                  # Windows 11 Build 22000+
        
        # #171717 is RGB(23, 23, 23) -> COLORREF is 0x00bbggrr
        bg_color = 0x17 | (0x17 << 8) | (0x17 << 16)
        
        # 1. Enable Dark Mode for title bar (Windows 10+)
        value = ctypes.c_int(1)
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_V2, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_V1, ctypes.byref(value), ctypes.sizeof(value))
            except Exception:
                pass
                
        # 2. Change Caption Color and Text Color (Windows 11+)
        try:
            bg_color_c = ctypes.c_int(bg_color)
            # Set background color to #171717
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(bg_color_c), ctypes.sizeof(bg_color_c))
            # Set text color to same as background to hide it
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(bg_color_c), ctypes.sizeof(bg_color_c))
        except Exception:
            pass
            
        # 3. Explicitly clear the window text to hide it on Windows 10 as well
        # Using zero-width space so it doesn't default to class name
        ctypes.windll.user32.SetWindowTextW(hwnd, "\u200b")
        log_info("Main", "Applied Windows dark titlebar styling")
        
    except Exception as e:
        log_debug("Main", f"Failed to apply Windows titlebar colors: {e}")


def nav_watcher(window, nav_file):
    """Watch for navigation commands from tray menu"""
    last_nav = None
    while True:
        try:
            if os.path.exists(nav_file):
                with open(nav_file, "r") as f:
                    nav_data = json.load(f)
                target = nav_data.get("target")
                timestamp = nav_data.get("timestamp", 0)
                nav_id = f"{target}_{timestamp}"

                if target and nav_id != last_nav:
                    last_nav = nav_id

                    # Wait for app to be ready before executing nav command
                    if not app_ready_event.is_set():
                        log_debug("Main", f"App not ready, skipping nav to '{target}'")
                        continue

                    log_info("Main", f"Executing nav switch to: {target}")
                    try:
                        result = window.evaluate_js(
                            f"if(window.app && window.app.switchView) {{ window.app.switchView('{target}'); true; }} else {{ false; }}"
                        )
                        log_debug("Main", f"Nav execution result: {result}")
                    except Exception as e:
                        log_warn("Main", f"Failed to execute nav: {e}")

                    # Remove nav file after processing
                    try:
                        os.remove(nav_file)
                        log_debug("Main", f"Removed nav file: {nav_file}")
                    except Exception as e:
                        log_debug("Main", f"Failed to remove nav file: {e}")
        except Exception as e:
            log_warn("Main", f"Nav watcher error: {e}")
        time.sleep(1)  # Poll every 1 second


def main(debug=False, no_tray=False, initial_page="dashboard"):
    """Main entry point"""
    try:
        log_info("Main", "Starting OpenCode Token Meter...")
        log_info("Main", "Press Ctrl+C to quit.")

        # Save PID and register cleanup
        save_pid()
        atexit.register(cleanup_pid_file)

        # Create API instance
        log_info("Main", "Initializing API...")
        try:
            api = JsApi()
            log_info("Main", "API initialized successfully")
        except Exception as e:
            log_error("Main", f"Failed to initialize API: {e}")
            log_error("Main", traceback.format_exc())
            raise

        # Create window
        log_info("Main", "Creating window...")
        window = create_window(api, debug=debug, initial_page=initial_page)
        log_info("Main", "Window created successfully")

        # Pass window to API for dialogs
        if hasattr(api, "set_window"):
            api.set_window(window)

        # Define callback for when webview is ready
        def on_webview_ready():
            """Called when webview DOM is ready"""
            log_info("Main", "Webview DOM is ready, enabling navigation")
            app_ready_event.set()
            
            # Apply Windows custom titlebar color
            apply_windows_titlebar_color(window)

        # Subscribe to loaded event
        window.events.loaded += on_webview_ready

        # Start nav watcher (unless explicitly running standalone without tray support, though harmless to run)
        nav_thread = threading.Thread(
            target=nav_watcher, args=(window, NAV_FILE), daemon=True
        )
        nav_thread.start()

        # Just run webview on main thread
        # Tray is handled by run_full_app.py in a separate process
        log_info("Main", "Starting webview...")
        webview.start(debug=debug, http_server=True, private_mode=False)

    except Exception as e:
        log_error("Main", f"Fatal error: {e}")
        log_error("Main", traceback.format_exc())
        raise


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--page",
        default="dashboard",
        help="Initial page (dashboard, details, settings)",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Skip tray initialization (for subprocess launch)",
    )
    args = parser.parse_args()

    main(debug=args.debug, no_tray=args.no_tray, initial_page=args.page)
