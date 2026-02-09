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


# Global window reference
window = None
api = None


def get_web_dir():
    """Get the web directory path"""
    return os.path.join(os.path.dirname(__file__), "web")


def create_window(debug=False):
    """Create the main webview window"""
    global api
    
    web_dir = get_web_dir()
    index_path = os.path.join(web_dir, "index.html")
    
    # Use file:// protocol for local files
    if os.path.exists(index_path):
        url = f"file://{os.path.abspath(index_path)}"
        print(f"[INFO] Loading URL: {url}")
    else:
        print(f"[ERROR] index.html not found at {index_path}")
        url = "about:blank"
    
    # Create API if not exists
    if api is None:
        api = JsApi()
    
    # Create window
    win = webview.create_window(
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
    
    # Pass window to API for dialogs
    if hasattr(api, 'set_window'):
        api.set_window(win)
    
    return win


def show_window(debug=False):
    """Show or create the main window"""
    global window
    
    if window is None:
        print("[INFO] Creating window...")
        window = create_window(debug=debug)
        print("[INFO] Window created")
    else:
        try:
            window.show()
            window.restore()
            print("[INFO] Window shown")
        except:
            print("[INFO] Recreating window...")
            window = create_window(debug=debug)


def main(debug=False):
    """Main entry point - start with tray only"""
    global api
    
    print("[INFO] Starting OpenCode Token Meter...")
    
    # Initialize API
    print("[INFO] Initializing API...")
    api = JsApi()
    print("[INFO] API initialized")
    
    # Create tray manager with window callback
    print("[INFO] Creating system tray...")
    def _on_quit():
        global window
        try:
            if window:
                window.destroy()
        except Exception:
            pass
        os._exit(0)

    tray = TrayManager(
        on_show=lambda: show_window(debug=debug),
        on_quit=_on_quit
    )
    
    # Start tray (this blocks on macOS)
    print("[INFO] Starting system tray (blocking)...")
    tray.run()


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    main(debug=args.debug)
