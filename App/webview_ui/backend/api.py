"""JavaScript API - exposed to frontend via pywebview"""
import os
import sys
import json
import time

# Add agent path for settings import
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
from .settings import Settings
from agent.config import BASE_DIR, TRIGGER_FILE
from agent.logger import log_error
from .bridge import AgentBridge
from . import db_read

def trigger_stats_update():
    """Signal stats worker to update"""
    try:
        with open(TRIGGER_FILE, "w") as f:
            f.write("1")
    except Exception as e:
        log_error("API", f"Failed to write trigger file: {e}")

class JsApi:
    """API class exposed to JavaScript via pywebview"""
    
    def __init__(self):
        self.bridge = AgentBridge()
        self.settings = Settings()
    
    def _format_response(self, success, data=None, error=None):
        """Format API response"""
        response = {"success": success}
        if data is not None:
            response["data"] = data
        if error is not None:
            response["error"] = str(error)
        return response
    
    # === Stats API ===
    
    def check_updates(self, last_ts=0):
        """
        Check if updates are needed (DB changed or Trigger exists).
        Returns {needed: bool, ts: new_timestamp}
        """
        try:
            from agent.config import DB_PATH
            needed = False
            current_ts = last_ts
            
            # Check DB mtime
            if os.path.exists(DB_PATH):
                mtime = os.path.getmtime(DB_PATH)
                if mtime > last_ts:
                    needed = True
                    current_ts = mtime
            
            # Check Trigger (e.g. from Settings save)
            # StatsWorker clears it, but if we catch it before clearing?
            # Or reliance on DB mtime is enough for data.
            # Settings save triggers DB read in StatsWorker.
            # But Webview needs to know to reload settings/stats.
            # If settings.json changes?
            try:
                settings_path = self.settings.SETTINGS_FILE
                if os.path.exists(settings_path):
                    s_mtime = os.path.getmtime(settings_path)
                    # We don't track last_settings_ts passed from client yet
                    # But if we just return max(db_mtime, settings_mtime)?
                    if s_mtime > current_ts:
                        needed = True
                        current_ts = max(current_ts, s_mtime)
            except: pass

            return self._format_response(True, {"needed": needed, "ts": current_ts})
        except Exception as e:
            return self._format_response(False, error=str(e))

    def get_stats(self, scope="today"):
        """Get statistics for given scope with cost calculation"""
        print(f"[API] get_stats called for scope: {scope}")
        try:
            timezone = self.settings.get("timezone", "local")
            
            # Get basic stats from DB
            stats = db_read.aggregate(scope, timezone)
            print(f"[API] db_read.aggregate for {scope}: {stats}")
            
            if not stats:
                return self._format_response(False, error="No data from database")
            
            # Get provider breakdown for cost calculation
            provider_stats = db_read.by_model(scope, timezone)
            if provider_stats is None:
                provider_stats = {}
            
            # Calculate total cost
            total_cost = 0.0
            if provider_stats:
                total_cost = self.settings.calculate_total_cost(provider_stats)
            
            # Transform to dashboard format
            total_output = (stats.get("output", 0) or 0) + (stats.get("reasoning", 0) or 0)
            data = {
                "total_input_tokens": stats.get("input", 0),
                "total_output_tokens": total_output,
                "total_cost": total_cost,
                "request_count": stats.get("requests", 0),
                "total_cache_read_tokens": stats.get("cache_read", 0),
                "total_cache_write_tokens": stats.get("cache_write", 0),
                "total_reasoning_tokens": stats.get("reasoning", 0),
                "message_count": stats.get("messages", 0),
            }
            
            # Get provider breakdown
            providers = []
            if provider_stats:
                for provider_id, models in provider_stats.items():
                    for model_id, model_stats in models.items():
                        cost = self.settings.calculate_cost(model_stats, model_id, provider_id)
                        providers.append({
                            "name": provider_id,
                            "model": model_id,
                            "requests": model_stats.get("requests", 0),
                            "input": model_stats.get("input", 0),
                            "output": (model_stats.get("output", 0) or 0) + (model_stats.get("reasoning", 0) or 0),
                            "reasoning": model_stats.get("reasoning", 0),
                            "cache_read": model_stats.get("cache_read", 0),
                            "cache_write": model_stats.get("cache_write", 0),
                            "cost": cost
                        })
            
            data["providers"] = providers
            
            # Generate trend data from DB time series
            data["trend"] = self._build_trend(scope, timezone)
            
            # Generate cost distribution
            data["distribution"] = self._generate_distribution(providers)
            
            return self._format_response(True, data)
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            log_error("API", f"get_stats error: {e}")
            return self._format_response(False, error=str(e))
    
    def get_stats_range(self, start_ts, end_ts):
        """Get statistics for a custom time range (timestamps in seconds)"""
        try:
            timezone = self.settings.get("timezone", "local")
            
            # Get stats from DB for the range
            stats = db_read.aggregate_range(start_ts, end_ts, timezone)
            
            if not stats:
                return self._format_response(False, error="No data for this range")
            
            # Get provider breakdown for cost calculation
            provider_stats = db_read.by_model_range(start_ts, end_ts, timezone)
            if provider_stats is None:
                provider_stats = {}
            
            # Calculate total cost
            total_cost = 0.0
            if provider_stats:
                total_cost = self.settings.calculate_total_cost(provider_stats)
            
            # Transform to dashboard format
            total_output = (stats.get("output", 0) or 0) + (stats.get("reasoning", 0) or 0)
            data = {
                "total_input_tokens": stats.get("input", 0),
                "total_output_tokens": total_output,
                "total_reasoning_tokens": stats.get("reasoning", 0),
                "total_cache_read_tokens": stats.get("cache_read", 0),
                "total_cache_write_tokens": stats.get("cache_write", 0),
                "total_cost": total_cost,
                "request_count": stats.get("requests", 0),
                "message_count": stats.get("messages", 0),
            }
            
            return self._format_response(True, data)
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            log_error("API", f"get_stats_range (1) error: {e}")
            return self._format_response(False, error=str(e))
    
    def get_stats_by_provider(self, scope="today"):
        """Get statistics grouped by provider"""
        try:
            timezone = self.settings.get("timezone", "local")
            data = db_read.by_provider(scope, timezone)
            if data is None:
                return self._format_response(False, error="No data from database")
            # Attach cost per provider using model-level stats
            model_stats = db_read.by_model(scope, timezone) or {}
            provider_costs = {}
            for provider_id, models in model_stats.items():
                total = 0.0
                for model_id, stats in models.items():
                    total += self.settings.calculate_cost(stats, model_id, provider_id)
                provider_costs[provider_id] = total

            for provider_id, stats in data.items():
                stats = stats.copy()
                stats["cost"] = provider_costs.get(provider_id, 0.0)
                data[provider_id] = stats
            return self._format_response(True, data)
        except Exception as e:
            log_error("API", f"get_stats_by_provider error: {e}")
            return self._format_response(False, error=e)
    
    def get_stats_by_model(self, scope="today"):
        """Get statistics grouped by provider and model"""
        try:
            timezone = self.settings.get("timezone", "local")
            data = db_read.by_model(scope, timezone)
            if data is None:
                return self._format_response(False, error="No data from database")
            for provider_id, models in data.items():
                for model_id, stats in models.items():
                    stats["cost"] = self.settings.calculate_cost(stats, model_id, provider_id)
            return self._format_response(True, data)
        except Exception as e:
            log_error("API", f"get_stats_by_model error: {e}")
            return self._format_response(False, error=e)
    
    def get_stats_range(self, start_ts, end_ts):
        """Get statistics for custom time range"""
        print(f"[API] get_stats_range called for range: {start_ts} to {end_ts}")
        try:
            # Get basic stats from DB
            stats = db_read.aggregate_range(start_ts, end_ts)
            print(f"[API] db_read.aggregate_range result: {stats}")
            
            if stats is None:
                return self._format_response(False, error="No data from database")
            
            # Get provider breakdown for cost calculation
            provider_stats = db_read.by_model_range(start_ts, end_ts)
            if provider_stats is None:
                provider_stats = {}
            
            # Calculate total cost
            total_cost = 0.0
            if provider_stats:
                total_cost = self.settings.calculate_total_cost(provider_stats)
            
            # Transform to dashboard format (same as get_stats)
            total_output = (stats.get("output", 0) or 0) + (stats.get("reasoning", 0) or 0)
            data = {
                "total_input_tokens": stats.get("input", 0),
                "total_output_tokens": total_output,
                "total_reasoning_tokens": stats.get("reasoning", 0),
                "total_cache_read_tokens": stats.get("cache_read", 0),
                "total_cache_write_tokens": stats.get("cache_write", 0),
                "total_cost": total_cost,
                "request_count": stats.get("requests", 0),
                "message_count": stats.get("messages", 0),
            }
            
            return self._format_response(True, data)
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            log_error("API", f"get_stats_range (2) error: {e}")
            return self._format_response(False, error=str(e))
    
    def get_stats_by_model_range(self, start_ts, end_ts):
        """Get statistics by model for custom time range"""
        try:
            data = db_read.by_model_range(start_ts, end_ts)
            if data is None:
                return self._format_response(False, error="No data from database")
            for provider_id, models in data.items():
                for model_id, stats in models.items():
                    stats["cost"] = self.settings.calculate_cost(stats, model_id, provider_id)
            return self._format_response(True, data)
        except Exception as e:
            log_error("API", f"get_stats_by_model_range error: {e}")
            return self._format_response(False, error=e)
    
    def get_stats_by_provider_range(self, start_ts, end_ts):
        """Get statistics by provider for custom time range"""
        print(f"[API] get_stats_by_provider_range called for range: {start_ts} to {end_ts}")
        try:
            data = db_read.by_provider_range(start_ts, end_ts)
            if data is None:
                return self._format_response(False, error="No data from database")
            
            # Calculate cost for each provider
            model_breakdown = db_read.by_model_range(start_ts, end_ts) or {}
            for provider_id, stats in data.items():
                # Sum up costs from all models for this provider
                provider_cost = 0.0
                if provider_id in model_breakdown:
                    for model_id, model_stats in model_breakdown[provider_id].items():
                        provider_cost += self.settings.calculate_cost(model_stats, model_id, provider_id)
                stats["cost"] = provider_cost
            
            return self._format_response(True, data)
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            log_error("API", f"get_stats_by_provider_range error: {e}")
            return self._format_response(False, error=str(e))
    
    # === Settings API ===
    
    def get_settings(self):
        """Get all settings"""
        try:
            return self._format_response(True, self.settings.settings)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def _log_debug(self, msg):
        """Log debug message to file (DISABLED)"""
        pass
        # try:
        #     # Use ~/Library/Application Support/OpenCode Token Meter/
        #     log_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "OpenCode Token Meter")
        #     os.makedirs(log_dir, exist_ok=True)
        #     log_path = os.path.join(log_dir, "api_debug.log")
        #     with open(log_path, "a") as f:
        #         f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        # except:
        #     pass

    def save_settings(self, settings):
        """Save settings"""
        # self._log_debug("save_settings called")
        try:
            # Detect pricing changes
            old_pricing = self.settings.get("model_pricing", {})
            new_pricing = settings.get("model_pricing", {})
            pricing_changed = (old_pricing != new_pricing)
            
            if pricing_changed:
                pass
                # self._log_debug("Model pricing changed, will trigger threshold check")
            
            # Save settings
            self.settings.settings = settings
            self.settings.save()
            
            # Trigger immediate update in stats_worker (for Tray)
            trigger_stats_update()
            
            return self._format_response(True)
        except Exception as e:
            # self._log_debug(f"save_settings error: {e}")
            log_error("API", f"save_settings error: {e}")
            return self._format_response(False, error=e)



    def _send_notification(self, title, message):
        """Send desktop notification (Cross-platform)"""
        self._log_debug(f"Sending notification: {title} - {message}")
        import platform
        system = platform.system()
        
        try:
            if system == "Darwin":
                # macOS: Use AppKit NSUserNotificationCenter with Delegate to force display
                try:
                    from Foundation import NSUserNotificationCenter, NSUserNotification, NSObject
                    from PyObjCTools import AppHelper

                    # Define delegate class if not already defined
                    # We use a global variable to store the delegate instance to prevent GC
                    global _notification_delegate
                    if '_notification_delegate' not in globals():
                        class NotificationDelegate(NSObject):
                            def userNotificationCenter_shouldPresentNotification_(self, center, notification):
                                return True
                        _notification_delegate = NotificationDelegate.alloc().init()

                    center = NSUserNotificationCenter.defaultUserNotificationCenter()
                    center.setDelegate_(_notification_delegate)

                    notification = NSUserNotification.alloc().init()
                    notification.setTitle_(title)
                    notification.setInformativeText_(message)
                    notification.setSoundName_("NSUserNotificationDefaultSoundName")
                    
                    center.deliverNotification_(notification)
                    
                    self._log_debug("AppKit notification delivered successfully with delegate")
                except ImportError:
                    self._log_debug("AppKit not available, falling back to rumps")
                    # Fallback to rumps if AppKit not available
                    try:
                        import rumps
                        rumps.notification(title, "", message)
                        self._log_debug("rumps notification sent")
                    except:
                        self._log_debug("rumps also not available")
                except Exception as e:
                    self._log_debug(f"AppKit error: {e}")
                    # Fallback
                    try:
                        import rumps
                        rumps.notification(title, "", message)
                    except:
                        pass
                
            elif system == "Windows":
                # Windows: Try win10toast or plyer
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=5, threaded=True)
                    self._log_debug("Windows toast notification sent")
                except ImportError:
                    self._log_debug("win10toast not available")
                except Exception as e:
                    self._log_debug(f"Windows notification error: {e}")
        except Exception as e:
            self._log_debug(f"Notification failed: {e}")
            import traceback
            traceback.print_exc()
    
    def get_model_price(self, model_id):
        """Get pricing for a specific model"""
        try:
            price = self.settings.get_model_price(model_id)
            return self._format_response(True, price)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def add_model_price(self, model_id, prices):
        """Add or update model pricing"""
        try:
            self.settings.add_model_price(model_id, prices)
            return self._format_response(True)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def delete_model_price(self, model_id):
        """Delete model pricing"""
        try:
            self.settings.delete_model_price(model_id)
            return self._format_response(True)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def reset_model_to_default(self, model_id):
        """Reset model to default pricing"""
        try:
            result = self.settings.reset_model_to_default(model_id)
            return self._format_response(result)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def reset_all_models_to_default(self):
        """Reset all models to default pricing"""
        try:
            self.settings.reset_all_models_to_default()
            return self._format_response(True)
        except Exception as e:
            return self._format_response(False, error=e)

    def get_thresholds_progress(self):
        """Get threshold progress for today and month"""
        try:
            enabled = bool(self.settings.get("thresholds.enabled", False))
            today_stats = db_read.aggregate("today") or {}
            month_stats = db_read.aggregate("month") or {}

            today_models = db_read.by_model("today") or {}
            month_models = db_read.by_model("month") or {}

            today_cost = self.settings.calculate_total_cost(today_models) if today_models else 0.0
            month_cost = self.settings.calculate_total_cost(month_models) if month_models else 0.0

            today_tokens = (
                int(today_stats.get("input", 0) or 0) +
                int(today_stats.get("output", 0) or 0) +
                int(today_stats.get("reasoning", 0) or 0)
            )
            month_tokens = (
                int(month_stats.get("input", 0) or 0) +
                int(month_stats.get("output", 0) or 0) +
                int(month_stats.get("reasoning", 0) or 0)
            )

            daily_token_thresh = self.settings.get("thresholds.daily_tokens", 1000000)
            daily_cost_thresh = self.settings.get("thresholds.daily_cost", 20.0)
            monthly_token_thresh = self.settings.get("thresholds.monthly_tokens", 10000000)
            monthly_cost_thresh = self.settings.get("thresholds.monthly_cost", 1000.0)

            data = {
                "enabled": enabled,
                "today": {
                    "token_pct": self._calc_pct(today_tokens, daily_token_thresh),
                    "cost_pct": self._calc_pct(today_cost, daily_cost_thresh),
                    "tokens": today_tokens,
                    "token_threshold": daily_token_thresh,
                    "cost": today_cost,
                    "cost_threshold": daily_cost_thresh
                },
                "month": {
                    "token_pct": self._calc_pct(month_tokens, monthly_token_thresh),
                    "cost_pct": self._calc_pct(month_cost, monthly_cost_thresh),
                    "tokens": month_tokens,
                    "token_threshold": monthly_token_thresh,
                    "cost": month_cost,
                    "cost_threshold": monthly_cost_thresh
                }
            }
            return self._format_response(True, data)
        except Exception as e:
            return self._format_response(False, error=e)

    def get_pricing_catalog(self):
        """Get default pricing catalog for display"""
        try:
            from .settings import DEFAULT_SETTINGS
            data = {
                "default": DEFAULT_SETTINGS.get("prices", {}).get("default", {}),
                "models": DEFAULT_SETTINGS.get("prices", {}).get("models", {}),
            }
            return self._format_response(True, data)
        except Exception as e:
            return self._format_response(False, error=e)
    
    # === Export API ===
    
    def set_window(self, window):
        """Set the window object for dialogs"""
        self.window = window
    
    def export_csv(self, scope="this_month"):
        """Export data to CSV"""
        try:
            import webview
            
            # Use save_file_dialog if window is available
            if hasattr(self, 'window') and self.window:
                filename = f"token_stats_{scope}.csv"
                result = self.window.create_file_dialog(
                    webview.SAVE_DIALOG, 
                    directory='/', 
                    save_filename=filename,
                    file_types=("CSV Files (*.csv)", "All files (*.*)")
                )
                
                # If cancelled, result is None or empty list/tuple depending on platform
                if not result:
                    return self._format_response(False, error="Export cancelled")
                
                # Result is usually a tuple/list of strings for SAVE_DIALOG? 
                # Pywebview docs say create_file_dialog returns a tuple of strings.
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    out_path = result[0]
                else:
                    out_path = str(result)
            else:
                # Fallback to temp dir (shouldn't happen with correct runner)
                import tempfile
                out_path = os.path.join(tempfile.gettempdir(), f"token_stats_{scope}.csv")
            
            result = db_read.export_csv(out_path, scope)
            if result is None:
                return self._format_response(False, error="No data from database")
            return self._format_response(True, result)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def export_csv_range(self, start_ts, end_ts):
        """Export custom range to CSV"""
        try:
            import webview
            
            # Use save_file_dialog if window is available
            if hasattr(self, 'window') and self.window:
                result = self.window.create_file_dialog(
                    webview.SAVE_DIALOG, 
                    directory='/', 
                    save_filename="token_stats_custom.csv",
                    file_types=("CSV Files (*.csv)", "All files (*.*)")
                )
                
                if not result:
                    return self._format_response(False, error="Export cancelled")
                
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    out_path = result[0]
                else:
                    out_path = str(result)
            else:
                import tempfile
                out_path = os.path.join(tempfile.gettempdir(), "token_stats_custom.csv")

            result = db_read.export_csv_range(out_path, start_ts, end_ts)
            if result is None:
                return self._format_response(False, error="No data from database")
            return self._format_response(True, result)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def export_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return self._format_response(True)
        except Exception as e:
            return self._format_response(False, error=e)

    def save_csv(self, content, filename="export.csv"):
        """Save CSV content to a file via native dialog"""
        try:
            import webview
            if hasattr(self, 'window') and self.window:
                result = self.window.create_file_dialog(
                    webview.SAVE_DIALOG, 
                    directory='/', 
                    save_filename=filename,
                    file_types=("CSV Files (*.csv)", "All files (*.*)")
                )
                if not result:
                    return self._format_response(False, error="Save cancelled")
                
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    out_path = result[0]
                else:
                    out_path = str(result)
                
                if not out_path:
                    return self._format_response(False, error="Invalid save path")

                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return self._format_response(True, out_path)
            return self._format_response(False, error="Window not available")
        except Exception as e:
            return self._format_response(False, error=str(e))
    
    # === App Control API ===
    
    def get_version(self):
        """Get app version"""
        try:
            version = self.settings.get_app_version()
            return self._format_response(True, version)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def refresh(self):
        """Force refresh data"""
        try:
            result = self.bridge.refresh()
            return self._format_response(result)
        except Exception as e:
            return self._format_response(False, error=e)
    
    
    def get_agent_status(self):
        """Get agent status"""
        try:
            status = self.bridge.get_status()
            # Frontend expects 'active' boolean
            if status and status.get("ok"):
                status["active"] = True
            return self._format_response(True, status)
        except Exception as e:
            return self._format_response(False, error=e)
    
    def calculate_cost(self, stats, model_id=None, provider_id=None):
        """Calculate cost from stats"""
        try:
            cost = self.settings.calculate_cost(stats, model_id, provider_id)
            return self._format_response(True, cost)
        except Exception as e:
            return self._format_response(False, error=e)

    def get_details(self, scope="month", mode="provider"):
        """Get detailed rows for Details tab"""
        try:
            model_stats = db_read.by_model(scope) or {}
            rows = []

            if mode == "model":
                for provider_id, models in model_stats.items():
                    for model_id, stats in models.items():
                        cost = self.settings.calculate_cost(stats, model_id, provider_id)
                        rows.append({
                            "provider": provider_id,
                            "model": model_id,
                            "requests": stats.get("requests", 0),
                            "input": stats.get("input", 0),
                            "output": (stats.get("output", 0) or 0) + (stats.get("reasoning", 0) or 0),
                            "cost": cost
                        })
            else:
                for provider_id, models in model_stats.items():
                    total = {
                        "provider": provider_id,
                        "requests": 0,
                        "input": 0,
                        "output": 0,
                        "cost": 0.0
                    }
                    for model_id, stats in models.items():
                        total["requests"] += stats.get("requests", 0) or 0
                        total["input"] += stats.get("input", 0) or 0
                        total["output"] += (stats.get("output", 0) or 0) + (stats.get("reasoning", 0) or 0)
                        total["cost"] += self.settings.calculate_cost(stats, model_id, provider_id)
                    rows.append(total)

            rows.sort(key=lambda r: r.get("cost", 0), reverse=True)
            return self._format_response(True, rows)
        except Exception as e:
            return self._format_response(False, error=e)
    
    # === Helper Methods ===
    
    def _build_trend(self, scope, timezone="local"):
        """Build trend data based on DB time series with Python-side aggregation"""
        from .utils import DateUtils

        start_ts, end_ts = db_read.get_time_range(scope, timezone)
        if end_ts <= start_ts:
            return {"labels": [], "values": []}

        range_seconds = end_ts - start_ts
        
        # Determine bucket size and format
        if range_seconds <= 2 * 86400:
            bucket_size = 3600 # 1 hour
            label_fmt = "%m-%d %H:00"
            mode = 'hourly'
        elif range_seconds <= 32 * 86400:
            bucket_size = 86400 # 1 day
            label_fmt = "%m-%d"
            mode = 'daily'
        elif range_seconds <= 365 * 86400:
            bucket_size = 7 * 86400 # 1 week
            label_fmt = "%Y-%m-%d"
            mode = 'weekly'
        elif range_seconds <= 5 * 365 * 86400:
            bucket_size = 30 * 86400 # ~1 month
            label_fmt = "%Y-%m"
            mode = 'monthly'
        else:
            bucket_size = 365 * 86400 # ~1 year
            label_fmt = "%Y"
            mode = 'yearly'

        rows = db_read.get_raw_trend_data(start_ts, end_ts)
        
        trend_tz = DateUtils.get_timezone(timezone)
        
        # Helper to align timestamp to bucket start in Target Timezone
        def align_ts(ts, mode):
            return DateUtils.align_to_bucket(ts, mode, timezone)

        # Aggregate by (bucket, provider, model) for correct cost calculation
        # Structure: { bucket_ts: { (provider, model): { input, output, reasoning, cache_read, cache_write, requests } } }
        bucket_model_stats = {}
        
        for row in rows:
            # ts, role, provider, model, input, output, reasoning, cache_r, cache_w
            ts = row[0]
            role = row[1]
            provider_id = row[2] or "unknown"
            model_id = row[3] or "unknown"
            
            # Align TS to bucket
            bucket_ts = align_ts(ts, mode)
            
            if bucket_ts not in bucket_model_stats:
                bucket_model_stats[bucket_ts] = {}
            
            key = (provider_id, model_id)
            if key not in bucket_model_stats[bucket_ts]:
                bucket_model_stats[bucket_ts][key] = {
                    "input": 0, "output": 0, "reasoning": 0,
                    "cache_read": 0, "cache_write": 0, "requests": 0
                }
            
            s = bucket_model_stats[bucket_ts][key]
            
            # Count Requests (User messages trigger the request)
            if role == 'user':
                s["requests"] += 1
            
            # Sum tokens (Assistant messages typically have usage)
            s["input"] += row[4] or 0
            s["output"] += row[5] or 0
            s["reasoning"] += row[6] or 0
            s["cache_read"] += row[7] or 0
            s["cache_write"] += row[8] or 0
        
        # Now calculate cost per bucket by summing over all models in each bucket
        bucket_stats = {}
        for bucket_ts, models in bucket_model_stats.items():
            bucket_stats[bucket_ts] = {
                "input": 0, "output": 0, "reasoning": 0,
                "requests": 0, "cost": 0.0
            }
            b = bucket_stats[bucket_ts]
            
            for (provider_id, model_id), stats in models.items():
                b["input"] += stats["input"]
                b["output"] += stats["output"]
                b["reasoning"] += stats["reasoning"]
                b["requests"] += stats["requests"]
                
                # Calculate cost for this model's usage in this bucket
                cost = self.settings.calculate_cost(stats, model_id, provider_id)
                b["cost"] += cost

        # Fill gaps and generate arrays
        labels = []
        data_input = []
        data_output = []
        data_reasoning = []
        data_requests = []
        data_cost = []
        
        current_ts = align_ts(start_ts, mode)
        
        # Ensure we don't loop infinitely
        loop_guard = 0
        max_loops = 1000 
        
        import datetime
        
        while current_ts <= end_ts and loop_guard < max_loops:
            # Format label using target timezone
            dt = datetime.datetime.fromtimestamp(current_ts, tz=datetime.timezone.utc)
            if trend_tz:
                dt = dt.astimezone(trend_tz)
            else:
                dt = datetime.datetime.fromtimestamp(current_ts) # local fallback
                
            labels.append(dt.strftime(label_fmt))
            
            s = bucket_stats.get(current_ts, {"input":0, "output":0, "reasoning":0, "requests":0, "cost":0.0})
            data_input.append(s["input"])
            data_output.append(s["output"])
            data_reasoning.append(s["reasoning"])
            data_requests.append(s["requests"])
            data_cost.append(round(s["cost"], 4))
            
            # Increment current_ts based on mode
            if mode == 'hourly':
                current_ts += 3600
            elif mode == 'daily':
                current_ts += 86400
            elif mode == 'weekly':
                current_ts += 7 * 86400
            elif mode == 'monthly':
                # Add 1 month safely
                year = dt.year
                month = dt.month + 1
                if month > 12:
                    month = 1
                    year += 1
                try:
                    next_month = dt.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
                except ValueError: 
                    next_month = dt.replace(year=year, month=month, day=1)
                current_ts = int(next_month.timestamp())
            elif mode == 'yearly':
                current_ts = int(dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
            
            loop_guard += 1

        return {
            "labels": labels,
            "cost": data_cost,
            "input": data_input,
            "output": data_output,
            "reasoning": data_reasoning,
            "requests": data_requests
        }

    def _calc_pct(self, value, threshold):
        try:
            value = float(value)
            threshold = float(threshold)
        except (TypeError, ValueError):
            return 0
        if threshold <= 0:
            return 0
        return min(int((value / threshold) * 100), 999)
    
    def _generate_distribution(self, providers, top_n=3):
        """Generate request distribution data for pie chart.
        Groups by provider, then model. Displays top_n models with full labels.
        Others are grouped into 'Other'.
        """
        if not providers:
            return {
                "labels": [],
                "values": [],
                "meta": []
            }

        # Sort all items by requests descending
        items = []
        for p in providers:
            provider = p.get("name") or "unknown"
            model = p.get("model") or "unknown"
            try:
                requests = int(p.get("requests", 0) or 0)
            except (TypeError, ValueError):
                requests = 0
            items.append({
                "provider": provider,
                "model": model,
                "requests": requests
            })

        # Sort by provider then requests
        items.sort(key=lambda x: (x["provider"], -x["requests"]))
        
        # Calculate total requests for percentages
        total_requests = sum(i["requests"] for i in items)
        
        # Identify top N items globally for labeling
        top_n_items = sorted(items, key=lambda x: x["requests"], reverse=True)[:top_n]
        top_n_keys = set((i["provider"], i["model"]) for i in top_n_items)

        labels = []
        values = []
        meta = []

        for item in items:
            provider = item["provider"]
            model = item["model"]
            requests = item["requests"]
            
            if requests <= 0:
                continue
                
            label = f"{provider} / {model}"
            percentage = (requests / total_requests * 100) if total_requests > 0 else 0
            
            # Metadata for frontend labels
            is_top = (provider, model) in top_n_keys
            
            labels.append(label)
            values.append(requests)
            meta.append({
                "label": label,
                "provider": provider,
                "model": model,
                "requests": requests,
                "percentage": round(percentage, 1),
                "show_label": is_top
            })

        return {
            "labels": labels,
            "values": values,
            "meta": meta
        }
