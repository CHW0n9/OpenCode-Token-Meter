"""Webview Runner - Runs in subprocess to display the main window"""
import os
import sys
import webview
import argparse
import time
import json
import threading
import atexit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

try:
    from agent.config import BASE_DIR
except ImportError:
    BASE_DIR = os.path.expanduser("~/Library/Application Support/OpenCode Token Meter")

NAV_FILE = os.path.join(BASE_DIR, "nav.json")
PID_FILE = os.path.join(BASE_DIR, "webview.pid")

# Event to signal when webview app is ready to receive navigation commands
app_ready_event = threading.Event()


def cleanup_pid_file():
    """Clean up PID file on exit"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            print("[INFO] Cleaned up webview PID file")
    except Exception as e:
        print(f"[WARN] Failed to clean up PID file: {e}")


def save_pid():
    """Save current process PID to file"""
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        print(f"[INFO] Saved PID {os.getpid()} to {PID_FILE}")
    except Exception as e:
        print(f"[WARN] Failed to save PID: {e}")

try:
    from .backend.api import JsApi
except ImportError:
    from backend.api import JsApi


def get_web_dir():
    return os.path.join(os.path.dirname(__file__), "web")


def create_window(api, debug=False, initial_page='dashboard'):
    web_dir = get_web_dir()
    index_path = os.path.join(web_dir, "index.html")
    
    if os.path.exists(index_path):
        # Pass initial page as query parameter
        url = f"file://{os.path.abspath(index_path)}?page={initial_page}"
        print(f"[INFO] Loading URL: {url}")
    else:
        print(f"[ERROR] index.html not found at {index_path}")
        url = "about:blank"
    
    window = webview.create_window(
        title="OpenCode Token Meter",
        url=url,
        js_api=api,
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True,
        fullscreen=False,
        hidden=False
    )
    
    return window


def nav_watcher(window, nav_file):
    """Watch for navigation commands from tray menu"""
    last_nav = None
    while True:
        try:
            if os.path.exists(nav_file):
                with open(nav_file, 'r') as f:
                    nav_data = json.load(f)
                target = nav_data.get('target')
                timestamp = nav_data.get('timestamp', 0)
                nav_id = f"{target}_{timestamp}"
                
                if target and nav_id != last_nav:
                    last_nav = nav_id
                    
                    # Wait for app to be ready before executing nav command
                    if not app_ready_event.is_set():
                        print(f"[DEBUG] App not ready, skipping nav to '{target}'")
                        continue
                    
                    print(f"[INFO] Executing nav switch to: {target}")
                    try:
                        result = window.evaluate_js(f"if(window.app && window.app.switchView) {{ window.app.switchView('{target}'); true; }} else {{ false; }}")
                        print(f"[DEBUG] Nav execution result: {result}")
                    except Exception as e:
                        print(f"[WARN] Failed to execute nav: {e}")
                    
                    # Remove nav file after processing
                    try:
                        os.remove(nav_file)
                        print(f"[DEBUG] Removed nav file: {nav_file}")
                    except Exception as e:
                        print(f"[DEBUG] Failed to remove nav file: {e}")
        except Exception as e:
            print(f"[WARN] Nav watcher error: {e}")
        time.sleep(1)  # Poll every 1 second


def main(debug=False, initial_page='dashboard'):
    try:
        print("[INFO] Starting webview subprocess...")
        
        # Save PID and register cleanup
        save_pid()
        atexit.register(cleanup_pid_file)
        
        api = JsApi()
        window = create_window(api, debug=debug, initial_page=initial_page)
        
        # Define callback for when webview is ready
        def on_webview_ready():
            """Called when webview DOM is ready"""
            print("[INFO] Webview DOM is ready, enabling navigation")
            app_ready_event.set()
        
        # Subscribe to loaded event
        window.events.loaded += on_webview_ready
        
        # Start nav watcher
        nav_thread = threading.Thread(target=nav_watcher, args=(window, NAV_FILE), daemon=True)
        nav_thread.start()
        
        # Start webview (blocks)
        webview.start(debug=debug, http_server=False, private_mode=False)
        print("[INFO] Webview closed, exiting...")
        
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode Token Meter - Webview")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--page", default="dashboard", help="Initial page (dashboard, details, settings)")
    args = parser.parse_args()
    
    main(debug=args.debug, initial_page=args.page)
