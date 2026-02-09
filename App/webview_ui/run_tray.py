#!/usr/bin/env python3
"""Standalone tray runner for macOS - run as a subprocess"""
import os
import sys
import json
import time

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))

def get_stats():
    """Get stats from database"""
    try:
        from backend import db_read
        from menubar.settings import Settings
        
        settings = Settings()
        
        today_stats = db_read.aggregate("today") or {}
        month_stats = db_read.aggregate("month") or {}
        
        today_models = db_read.by_model("today") or {}
        month_models = db_read.by_model("month") or {}
        
        # Calculate costs
        today_cost = settings.calculate_total_cost(today_models) if today_models else 0.0
        month_cost = settings.calculate_total_cost(month_models) if month_models else 0.0
        
        return {
            "today": {
                "input": today_stats.get("input", 0),
                "output": today_stats.get("output", 0),
                "reasoning": today_stats.get("reasoning", 0),
                "requests": today_stats.get("requests", 0),
                "cost": today_cost,
            },
            "month": {
                "input": month_stats.get("input", 0),
                "output": month_stats.get("output", 0),
                "reasoning": month_stats.get("reasoning", 0),
                "requests": month_stats.get("requests", 0),
                "cost": month_cost,
            },
            "thresholds_enabled": settings.get("thresholds.enabled", False),
        }
    except Exception as e:
        print(f"[Tray] Error getting stats: {e}")
        return {}


def main():
    """Main entry point for tray"""
    import platform
    
    if platform.system() != "Darwin":
        print("[Tray] This script is for macOS only")
        return
    
    try:
        from backend.tray_rumps import TrayManager
    except ImportError as e:
        print(f"[Tray] Failed to import tray_rumps: {e}")
        return
    
    print("[Tray] Starting macOS tray...")
    
    def show_window():
        """Open the webview window by launching a new process"""
        import subprocess
        main_py = os.path.join(os.path.dirname(__file__), "main.py")
        subprocess.Popen([sys.executable, main_py, "--no-tray"])
    
    def on_quit():
        """Clean up on quit"""
        print("[Tray] Quitting...")
    
    tray = TrayManager(
        on_show=show_window,
        on_quit=on_quit,
        notifications_enabled=True
    )
    
    # Create app and update stats periodically
    tray.create_app()
    
    # Initial stats update
    stats = get_stats()
    tray._apply_stats(stats)
    
    # Set up timer for periodic updates
    import rumps
    
    def refresh_stats(_=None):
        stats = get_stats()
        tray._apply_stats(stats)
    
    timer = rumps.Timer(refresh_stats, 5)
    timer.start()
    
    # Run the app (blocks main thread)
    tray.app.run()


if __name__ == "__main__":
    main()
