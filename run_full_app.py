#!/usr/bin/env python3
"""
OpenCode Token Meter - Unified Application Launcher

This script launches the complete application:
1. Tray App (runs on main thread for macOS rumps compatibility)  
2. Webview Dashboard (launches as subprocess when "Open Main Window" is clicked)

Usage:
    python run_full_app.py           # Start tray app only
    python run_full_app.py --window  # Start both tray and window immediately
"""
import os
import sys
import subprocess
import platform

# Add paths
script_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(script_dir, "App")
webview_ui_dir = os.path.join(app_dir, "webview_ui")

sys.path.insert(0, app_dir)
sys.path.insert(0, os.path.join(app_dir, "agent"))
sys.path.insert(0, os.path.join(app_dir, "menubar"))
sys.path.insert(0, webview_ui_dir)



# Global process handles
webview_process = None
agent_process = None

def launch_agent(debug=False):
    """Launch the agent as a subprocess"""
    global agent_process
    
    agent_module = "agent"  # Running as module
    
    print(f"[INFO] Launching agent module: {agent_module}")
    
    # Need to run from App directory where 'agent' package resides
    # And ensure App/agent is in PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([
        app_dir,
        os.path.join(app_dir, "agent"),
        env.get("PYTHONPATH", "")
    ])
    
    # Run agent package (looks for agent/__main__.py)
    cmd = [sys.executable, "-m", "agent"]
    
    # In debug mode, we might want to see agent output
    # But for a GUI app, usually better to let it log to file
    agent_process = subprocess.Popen(cmd, cwd=os.path.join(app_dir, "agent"), env=env)
    print(f"[INFO] Agent launched with PID {agent_process.pid}")


def launch_webview_window(debug=False):
    """Launch the webview window as a subprocess"""
    global webview_process
    
    # Check if already running
    if webview_process and webview_process.poll() is None:
        print("[INFO] Webview already running")
        return

    main_py = os.path.join(webview_ui_dir, "main.py")
    if os.path.exists(main_py):
        print(f"[INFO] Launching webview: {main_py}")
        # Launch with clear env to avoid inheriting tray's env if needed, but usually fine
        cmd = [sys.executable, main_py, "--no-tray"]
        if debug:
            cmd.append("--debug")
        webview_process = subprocess.Popen(cmd)
    else:
        print(f"[ERROR] main.py not found: {main_py}")


def run_tray(debug=False):
    """Run the tray app on main thread (macOS requirement)"""
    
    # Launch Agent first
    launch_agent(debug=debug)
    
    if platform.system() != "Darwin":
        print("[INFO] Tray only supported on macOS, launching window only...")
        launch_webview_window(debug=debug)
        # Wait for window to close then kill agent
        if webview_process:
            webview_process.wait()
        if agent_process:
            agent_process.terminate()
        return
    
    try:
        from backend.tray_rumps import TrayManager
        from backend import db_read
        from menubar.settings import Settings
        from stats_worker import STATS_FILE
        import rumps
    except ImportError as e:
        print(f"[ERROR] Failed to import tray dependencies: {e}")
        print("[INFO] Falling back to webview only...")
        launch_webview_window(debug=debug)
        if webview_process:
            webview_process.wait()
        if agent_process:
            agent_process.terminate()
        return
    
    print("[INFO] Starting tray app...")
    
    settings = Settings()
    
    def _calc_pct(value, threshold):
        try:
            value = float(value)
            threshold = float(threshold)
        except (TypeError, ValueError):
            return 0
        if threshold <= 0:
            return 0
        return min(int((value / threshold) * 100), 999)

    def get_stats():
        """Get stats from database"""
        try:
            # Reload settings to catch changes from UI
            settings.reload()
            
            today_stats = db_read.aggregate("today") or {}
            month_stats = db_read.aggregate("month") or {}
            today_models = db_read.by_model("today") or {}
            month_models = db_read.by_model("month") or {}
            
            today_cost = settings.calculate_total_cost(today_models) if today_models else 0.0
            month_cost = settings.calculate_total_cost(month_models) if month_models else 0.0
            
            today_tokens = int(today_stats.get("input", 0) or 0) + int(today_stats.get("output", 0) or 0) + int(today_stats.get("reasoning", 0) or 0)
            month_tokens = int(month_stats.get("input", 0) or 0) + int(month_stats.get("output", 0) or 0) + int(month_stats.get("reasoning", 0) or 0)

            thresholds_enabled = bool(settings.get("thresholds.enabled", False))
            
            today_payload = {
                "input": today_stats.get("input", 0),
                "output": today_stats.get("output", 0),
                "reasoning": today_stats.get("reasoning", 0),
                "requests": today_stats.get("requests", 0),
                "cost": today_cost,
            }
            month_payload = {
                "input": month_stats.get("input", 0),
                "output": month_stats.get("output", 0),
                "reasoning": month_stats.get("reasoning", 0),
                "requests": month_stats.get("requests", 0),
                "cost": month_cost,
            }

            if thresholds_enabled:
                daily_token_thresh = settings.get("thresholds.daily_tokens", 1000000)
                daily_cost_thresh = settings.get("thresholds.daily_cost", 20.0)
                monthly_token_thresh = settings.get("thresholds.monthly_tokens", 10000000)
                monthly_cost_thresh = settings.get("thresholds.monthly_cost", 1000.0)
                
                today_payload["token_pct"] = _calc_pct(today_tokens, daily_token_thresh)
                today_payload["cost_pct"] = _calc_pct(today_cost, daily_cost_thresh)
                month_payload["token_pct"] = _calc_pct(month_tokens, monthly_token_thresh)
                month_payload["cost_pct"] = _calc_pct(month_cost, monthly_cost_thresh)

            return {
                "today": today_payload,
                "month": month_payload,
                "thresholds_enabled": thresholds_enabled,
            }
        except Exception as e:
            print(f"[Tray] Error getting stats: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def on_quit():
        print("[INFO] Quitting...")
        global webview_process, agent_process
        
        if webview_process:
            print("[INFO] Terminating webview process...")
            webview_process.terminate()
            try:
                webview_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                webview_process.kill()
        
        if agent_process:
            print("[INFO] Terminating agent process...")
            agent_process.terminate()
            try:
                agent_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                agent_process.kill()
                
        # Note: rumps.quit_application() is called by TrayManager._on_quit after this callback
    
    tray = TrayManager(
        on_show=lambda: launch_webview_window(debug=debug),
        on_quit=on_quit,
        notifications_enabled=True
    )

    # Start stats worker in background thread (daemon, so it dies with app)
    try:
        import threading
        # Ensure path is correct
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "App", "webview_ui"))
        from stats_worker import main as run_stats_worker
        t = threading.Thread(target=run_stats_worker, daemon=True)
        t.start()
        print("[INFO] Stats worker thread started.")
    except Exception as e:
        print(f"[ERROR] Failed to start stats worker: {e}")
        import traceback
        traceback.print_exc()
    
    # Use the built-in auto update mechanism which handles file reading and interval management
    tray.start_auto_update(STATS_FILE, interval=5)
    
    # Create the app (menus etc)
    tray.create_app()
    
    # Try an immediate refresh to populate data
    try:
        tray._refresh_stats()
    except Exception as e:
        print(f"[WARN] Initial stats refresh failed: {e}")

    # Show startup notification
    tray.notify_startup()
    
    print("[INFO] Tray started. Click 'Open Main Window' to show dashboard.")
    tray.app.run()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--window", action="store_true", help="Also open main window immediately")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    if args.window:
        launch_webview_window(debug=args.debug)
    
    run_tray(debug=args.debug)


if __name__ == "__main__":
    main()
