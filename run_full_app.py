#!/usr/bin/env python3
"""
OpenCode Token Meter - Main Application Launcher

This script launches the full application with:
1. System Tray (macOS/Windows)
2. Background Agent (as a thread)
3. Stats Worker (as a thread)
4. Webview UI (as a subprocess)

It delegates the actual logic to App/webview_ui/main_tray.py
"""
import os
import sys

# Add App/ directory to path so we can import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, "App")
sys.path.insert(0, app_dir)

def main():
    """Main entry point"""
    try:
        import argparse
        from webview_ui import main_tray
        
        # Parse arguments
        parser = argparse.ArgumentParser(description="OpenCode Token Meter Launcher")
        parser.add_argument("--debug", action="store_true", help="Enable debug mode")
        parser.add_argument("--window", action="store_true", help="Show window on startup")
        
        # Use parse_known_args in case other args are passed
        args, unknown = parser.parse_known_args()
        
        if unknown:
            print(f"[Launcher] Warning: Unknown arguments: {unknown}")

        print(f"[Launcher] Starting OpenCode Token Meter (Debug={args.debug}, Window={args.window})...")
        
        # Run main tray app
        main_tray.main(debug=args.debug, show_window=args.window)
        
    except ImportError as e:
        print(f"[ERROR] Failed to import application modules: {e}")
        print(f"PYTHONPATH: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Application crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
