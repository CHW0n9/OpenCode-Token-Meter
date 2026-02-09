"""Main entry point for OpenCode Token Meter - Working Window Version"""
import os
import sys
import webview
import argparse

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "menubar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

# Support both module import and direct execution
try:
    from .backend.api import JsApi
except ImportError:
    # Direct execution
    from backend.api import JsApi


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
        hidden=False,
        background_color='#1a1a1a'  # Dark background to prevent white flash
    )
    
    return window


def main(debug=False, no_tray=False):
    """Main entry point"""
    import sys
    import platform
    
    try:
        print("[INFO] Starting OpenCode Token Meter...")
        print("[INFO] Press Ctrl+C to quit.")
        
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
        
        # Pass window to API for dialogs
        if hasattr(api, 'set_window'):
            api.set_window(window)
        
        # Just run webview on main thread
        # Tray is handled by run_full_app.py in a separate process
        print("[INFO] Starting webview...")
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


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-tray", action="store_true", help="Skip tray initialization (for subprocess launch)")
    args = parser.parse_args()
    
    main(debug=args.debug, no_tray=args.no_tray)
