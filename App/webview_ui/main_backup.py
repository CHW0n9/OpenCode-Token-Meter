"""Main entry point for OpenCode Token Meter - pywebview version"""
import os
import sys
import webview
import argparse
from pathlib import Path

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

# Support both module import and direct execution
try:
    from .backend.api import JsApi
    from .backend.tray import TrayManager
except ImportError:
    # Direct execution
    from backend.api import JsApi
    from backend.tray import TrayManager


def get_web_dir():
    """Get the web directory path"""
    return os.path.join(os.path.dirname(__file__), "web")


def create_window(api, debug=False):
    """Create the main webview window"""
    web_dir = get_web_dir()
    index_path = os.path.join(web_dir, "index.html")
    
    # Use file:// protocol for local files
    if os.path.exists(index_path):
        url = f"file://{os.path.abspath(index_path)}"
        print(f"[INFO] Loading URL: {url}")
    else:
        print(f"[ERROR] index.html not found at {index_path}")
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
        hidden=False
    )
    
    return window


def main(debug=False):
    """Main entry point"""
    tray = None
    try:
        print("[INFO] Starting OpenCode Token Meter...")
        
        # Create API instance
        print("[INFO] Initializing API...")
        try:
            api = JsApi()
            print("[INFO] API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize API: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Create window
        print("[INFO] Creating window...")
        window = create_window(api, debug=debug)
        print("[INFO] Window created successfully")
        
        # Start webview first (blocks main thread)
        print("[INFO] Starting webview...")
        print("[INFO] Window should appear now. Press Ctrl+C to quit.")
        
        # Start tray in background thread after webview window is created
        def start_tray():
            import time
            time.sleep(1)  # Wait for window to be fully created
            print("[INFO] Starting system tray...")
            tray = TrayManager(
                on_show=lambda: window.show(),
                on_quit=lambda: os._exit(0)
            )
            tray.run()
            print("[INFO] System tray started")
            return tray
        
        import threading
        tray_thread = threading.Thread(target=start_tray)
        tray_thread.daemon = True
        tray_thread.start()
        
        # Start webview (this blocks)
        webview.start(
            debug=debug,
            http_server=False,
            private_mode=False
        )
        
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cleanup
        print("[INFO] Cleaning up...")
        if tray:
            try:
                tray.stop()
            except:
                pass


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    main(debug=args.debug)
