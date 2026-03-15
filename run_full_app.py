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

# Add App/ and App/agent/ directory to path so we can import modules correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, "App")
agent_pkg_dir = os.path.join(app_dir, "agent")

sys.path.insert(0, app_dir)
sys.path.insert(0, agent_pkg_dir)

def main():
    """Main entry point"""
    # Define fallback loggers in case import fails
    def _fallback_log(tag, msg, level="ERROR"):
        print(f"[{tag:^10}] {msg}", file=sys.stderr if level == "ERROR" else sys.stdout)

    log_info = lambda t, m: _fallback_log(t, m, "INFO")
    log_warn = lambda t, m: _fallback_log(t, m, "WARN")
    log_error = lambda t, m: _fallback_log(t, m, "ERROR")

    try:
        import argparse
        # Try to import real loggers
        try:
            from agent.logger import log_info as li, log_error as le, log_warn as lw
            log_info, log_error, log_warn = li, le, lw
        except ImportError:
            pass # Use fallbacks
            
        from webview_ui import main_tray
        
        # Parse arguments
        parser = argparse.ArgumentParser(description="OpenCode Token Meter Launcher")
        parser.add_argument("--debug", action="store_true", help="Enable debug mode")
        parser.add_argument("--window", action="store_true", help="Show window on startup")
        
        # Use parse_known_args in case other args are passed
        args, unknown = parser.parse_known_args()
        
        if unknown:
            log_warn("Launcher", f"Unknown arguments: {unknown}")

        log_info("Launcher", f"Starting OpenCode Token Meter (Debug={args.debug}, Window={args.window})...")
        
        # Run main tray app
        main_tray.main(debug=args.debug, show_window=args.window)
        
    except ImportError as e:
        log_error("Launcher", f"Failed to import application modules: {e}")
        sys.exit(1)
    except Exception as e:
        log_error("Launcher", f"Application crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
