"""System tray for macOS using rumps (compatible with pywebview)"""
import json
import os

import rumps


class TrayManager:
    """Tray manager using rumps for macOS"""

    def __init__(self, on_show=None, on_quit=None, notifications_enabled=True):
        self.on_show = on_show
        self.on_quit = on_quit
        self.notifications_enabled = notifications_enabled
        self.app = None
        self._running = False
        self._stats_path = None
        self._timer = None
        self._interval = 5
        self._notified_startup = False # Renamed from _notified
        
        # Track threshold notification state: 0=OK, 1=80% warned, 2=100% warned
        self._threshold_state = {
            'today_token': 0, 'today_cost': 0,
            'month_token': 0, 'month_cost': 0
        }

        import sys
        if getattr(sys, 'frozen', False):
            # In cached bundle
            # sys.executable is .../Contents/MacOS/OpenCode Token Meter
            # Icons are in .../Contents/Resources/resources/
            resources_dir = os.path.join(os.path.dirname(sys.executable), "..", "Resources", "resources")
            self.icon_path = os.path.join(resources_dir, "icon_template@2x.png")
            if not os.path.exists(self.icon_path):
                # Fallback to non-retina
                self.icon_path = os.path.join(resources_dir, "icon_template.png")
        else:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            self.icon_path = os.path.join(base_dir, "web", "assets", "icon_template@2x.png")

        self._menu_items = {}
        self._tab_size = 8
        self._left_value_stop = 2
        self._right_label_stop = 4
        self._right_value_stop = 6

        # State for threshold notifications
        self._notification_state = {
            "last_reset_day": None,
            "last_reset_month": None,
            "daily_tokens": False,
            "daily_cost": False,
            "monthly_tokens": False,
            "monthly_cost": False
        }
        self._last_pricing_update_id = 0
        self._last_thresholds = {}

    def create_app(self):
        # Initialize the app with a name (title will be cleared later)
        self.app = rumps.App("OpenCode Token Meter")
        
        # Use image-based icon with template mode
        if os.path.exists(self.icon_path):
            try:
                # Set icon and template mode via rumps
                self.app.icon = self.icon_path
                self.app.template = True
                
                # IMPORTANT: Clear title to prevent showing text next to icon
                self.app.title = None
                
                # Apply native Cocoa hack to disable highlight inversion on click
                if hasattr(self.app, '_nsstatusitem'):
                    button = self.app._nsstatusitem.button()
                    if button:
                        # setHighlightsBy_(0) disables all highlight states (no inversion)
                        button.cell().setHighlightsBy_(0)
                        print("[INFO] Tray icon highlight disabled via NSButtonCell hack")
            except Exception as e:
                print(f"[WARN] Failed to apply tray icon hack: {e}")
        else:
            print(f"[WARN] Icon path not found: {self.icon_path}")

        today_header = rumps.MenuItem("Today")
        today_row1 = rumps.MenuItem(self._build_row("In:", "--", "Req:", "--"))
        today_row2 = rumps.MenuItem(self._build_row("Out:", "--", "Cost:", "--"))
        today_row3 = rumps.MenuItem("")

        month_header = rumps.MenuItem("This Month")
        month_row1 = rumps.MenuItem(self._build_row("In:", "--", "Req:", "--"))
        month_row2 = rumps.MenuItem(self._build_row("Out:", "--", "Cost:", "--"))
        month_row3 = rumps.MenuItem("")

        show_item = rumps.MenuItem("Open Main Window", callback=self._on_show)
        quit_item = rumps.MenuItem("Quit", callback=self._on_quit)
        
        self.app.menu = [
            today_header,
            today_row1,
            today_row2,
            today_row3,
            None,
            month_header,
            month_row1,
            month_row2,
            month_row3,
            None,
            show_item,
            None,
            quit_item,
        ]

        # Disable the default quit button since we have our own
        self.app.quit_button = None

        self._menu_items = {
            "today_header": today_header,
            "today_row1": today_row1,
            "today_row2": today_row2,
            "today_row3": today_row3,
            "month_header": month_header,
            "month_row1": month_row1,
            "month_row2": month_row2,
            "month_row3": month_row3,
        }
        return self.app

    def _on_show(self, _sender):
        if self.on_show:
            self.on_show()

    def _on_quit(self, _sender):
        if self.on_quit:
            self.on_quit()
        rumps.quit_application()


    def _read_stats_file(self):
        if not self._stats_path or not os.path.exists(self._stats_path):
            return {}
        try:
            with open(self._stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
            
            # Stale check removed to allow slow updates (e.g. 300s in slow mode)
            # if time.time() - file_ts > 20: ...

            return stats
        except Exception:
            return {}

    def _format_tokens(self, num):
        if num is None:
            return "--"
        try:
            n = int(num)
        except (TypeError, ValueError):
            return "--"
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)

    def _format_cost(self, value):
        if value is None:
            return "--"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "--"

    def _tab_units(self, text):
        units = 0
        for ch in text:
            if ch == "\t":
                units += self._tab_size - (units % self._tab_size)
            else:
                units += 1
        return units

    def _tabs_to_target(self, current_units, target_units):
        if current_units < target_units:
            tabs = 0
            units = current_units
            while units < target_units:
                units += self._tab_size - (units % self._tab_size)
                tabs += 1
            return max(1, tabs)
        return 1

    def _append_tabs(self, text, target_units):
        tabs = self._tabs_to_target(self._tab_units(text), target_units)
        return text + ("\t" * tabs)

    def _build_row(self, left_label, left_value, right_label, right_value):
        text = str(left_label)
        text = self._append_tabs(text, self._tab_size * self._left_value_stop)
        text += str(left_value)
        text = self._append_tabs(text, self._tab_size * self._right_label_stop)
        text += str(right_label)
        text = self._append_tabs(text, self._tab_size * self._right_value_stop)
        text += str(right_value)
        return text

    def _build_attributed_row(self, left_label, left_value, right_label, right_value):
        try:
            from AppKit import (
                NSMutableParagraphStyle,
                NSTextTab,
                NSParagraphStyleAttributeName,
                NSForegroundColorAttributeName,
                NSRightTabStopType,
                NSLeftTabStopType,
                NSAttributedString,
                NSColor,
                NSFont,
                NSFontAttributeName,
            )
        except Exception:
            return None

        # Match PyQt layout with tighter label-value spacing
        label_value_spacing = 13  # ~2/3 of previous 8
        column_gap = 12
        left_value_end = 12 + 20 + label_value_spacing + 60
        right_label_start = left_value_end + column_gap
        right_value_end = right_label_start + 20 + label_value_spacing + 72

        paragraph = NSMutableParagraphStyle.alloc().init()
        tabs = [
            NSTextTab.alloc().initWithType_location_(NSRightTabStopType, left_value_end),
            NSTextTab.alloc().initWithType_location_(NSLeftTabStopType, right_label_start),
            NSTextTab.alloc().initWithType_location_(NSRightTabStopType, right_value_end),
        ]
        paragraph.setTabStops_(tabs)

        # Use semantic label color to adapt to light/dark mode
        attrs = {
            NSParagraphStyleAttributeName: paragraph,
            NSForegroundColorAttributeName: NSColor.labelColor(),
            NSFontAttributeName: NSFont.menuFontOfSize_(0),
        }
        text = f"{left_label}\t{left_value}\t{right_label}\t{right_value}"
        return NSAttributedString.alloc().initWithString_attributes_(text, attrs)

    def _set_menu_item_text(self, item, left_label, left_value, right_label, right_value):
        fallback = self._build_row(left_label, left_value, right_label, right_value)
        attributed = self._build_attributed_row(left_label, left_value, right_label, right_value)
        
        try:
            from AppKit import NSTextField, NSColor, NSView, NSMakeRect, NSNoBorder, NSBackingStoreBuffered
            
            menu_item = getattr(item, "_menuitem", None) or getattr(item, "_menuItem", None)
            if menu_item is not None and attributed is not None:
                # Check if view already exists
                view = menu_item.view()
                if view is None:
                    # Create a container view to handle indentation
                    # Standard menu item height is around 19-22pts depending on OS version
                    container_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 250, 19))
                    
                    # Add 19pt margin to match standard menu item indentation
                    left_margin = 12
                    # Create non-editable text field
                    tf = NSTextField.alloc().initWithFrame_(NSMakeRect(left_margin, 0, 250 - left_margin, 19))
                    tf.setBezeled_(False)
                    tf.setDrawsBackground_(False)
                    tf.setEditable_(False)
                    tf.setSelectable_(False)
                    tf.setBordered_(False)
                    
                    # Set the attributed string
                    tf.setAttributedStringValue_(attributed)
                    
                    # Add text field to container
                    container_view.addSubview_(tf)
                    
                    # Set the container view on the menu item
                    menu_item.setView_(container_view)
                else:
                    # View exists, check if it's our container or direct text field
                    target_view = view
                    if not hasattr(view, "setAttributedStringValue_"):
                         # Should be container, get subview
                         if hasattr(view, "subviews") and view.subviews().count() > 0:
                             target_view = view.subviews().objectAtIndex_(0)
                    
                    if hasattr(target_view, "setAttributedStringValue_"):
                        target_view.setAttributedStringValue_(attributed)
                return
        except Exception as e:
            # Fallback
            pass

        item.title = fallback

    def _set_menu_header_text(self, item, title):
        """Set header text using custom view for consistent alignment"""
        try:
            from AppKit import (
                NSTextField, NSColor, NSView, NSMakeRect, 
                NSMutableAttributedString, NSFont, NSForegroundColorAttributeName,
                NSFontAttributeName
            )
            
            menu_item = getattr(item, "_menuitem", None) or getattr(item, "_menuItem", None)
            if menu_item is not None:
                view = menu_item.view()
                if view is None:
                    # Create a container view
                    container_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 250, 19))

                    # Create non-editable text field same as rows
                    # Add 19pt margin to match standard menu item indentation
                    left_margin = 12
                    tf = NSTextField.alloc().initWithFrame_(NSMakeRect(left_margin, 0, 250 - left_margin, 19))
                    tf.setBezeled_(False)
                    tf.setDrawsBackground_(False)
                    tf.setEditable_(False)
                    tf.setSelectable_(False)
                    tf.setBordered_(False)
                    
                    # Create attributed string for color
                    attrs = {
                        NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
                        NSFontAttributeName: NSFont.menuFontOfSize_(0),
                    }
                    attr_str = NSMutableAttributedString.alloc().initWithString_attributes_(title, attrs)
                    tf.setAttributedStringValue_(attr_str)
                    
                    container_view.addSubview_(tf)
                    menu_item.setView_(container_view)
                else:
                    # View exists, find text field
                    target_view = view
                    if not hasattr(view, "setAttributedStringValue_"):
                        if hasattr(view, "subviews") and view.subviews().count() > 0:
                            target_view = view.subviews().objectAtIndex_(0)

                    if hasattr(target_view, "setAttributedStringValue_"):
                         # Update existing
                        attrs = {
                            NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
                            NSFontAttributeName: NSFont.menuFontOfSize_(0),
                        }
                        attr_str = NSMutableAttributedString.alloc().initWithString_attributes_(title, attrs)
                        target_view.setAttributedStringValue_(attr_str)
                return
        except Exception:
            pass
        
        item.title = title

    def _set_row_visible(self, item, visible):
        try:
            item.hidden = not visible
        except Exception:
            if not visible:
                item.title = ""

    def _send_notification(self, title, message):
        """Send notification using AppKit with Delegate for banner support"""
        success = False
        
        # Method 1: AppKit (Native)
        try:
            from Foundation import NSUserNotificationCenter, NSUserNotification, NSObject
            from PyObjCTools import AppHelper

            # Define delegate class if not already defined
            global _notification_delegate
            if '_notification_delegate' not in globals():
                class NotificationDelegate(NSObject):
                    def userNotificationCenter_shouldPresentNotification_(self, center, notification):
                        return True
                _notification_delegate = NotificationDelegate.alloc().init()

            center = NSUserNotificationCenter.defaultUserNotificationCenter()
            # Safety check for center
            if center is not None:
                center.setDelegate_(_notification_delegate)

                notification = NSUserNotification.alloc().init()
                notification.setTitle_(title)
                notification.setInformativeText_(message)
                notification.setSoundName_("NSUserNotificationDefaultSoundName")
                
                center.deliverNotification_(notification)
                success = True
        except Exception:
            pass

        if success:
            return

        # Method 2: rumps (Fallback 1)
        try:
            rumps.notification(title, "", message)
            return
        except Exception:
            pass

        # Method 3: osascript (Fallback 2 - Best for scripts/frozen apps without proper bundle ID)
        try:
            import subprocess
            # Escape quotes
            safe_title = title.replace('"', '\\"')
            safe_msg = message.replace('"', '\\"')
            script = f'display notification "{safe_msg}" with title "{safe_title}"'
            subprocess.run(['osascript', '-e', script], capture_output=True, timeout=2)
        except Exception:
            pass

    def _check_thresholds(self, stats):
        if not self.notifications_enabled:
            return

        today = stats.get("today", {})
        month = stats.get("month", {})
        
        # Check for date changes to reset state
        import time
        current_time = time.localtime()
        current_day = current_time.tm_yday
        current_month = current_time.tm_mon
        
        # Reset daily flags on new day
        if self._notification_state["last_reset_day"] != current_day:
            self._notification_state["daily_tokens"] = False
            self._notification_state["daily_cost"] = False
            self._notification_state["last_reset_day"] = current_day
            
        # Reset monthly flags on new month
        if self._notification_state["last_reset_month"] != current_month:
            self._notification_state["monthly_tokens"] = False
            self._notification_state["monthly_cost"] = False
            self._notification_state["last_reset_month"] = current_month
            
        # 1. Check for pricing changes that AFFECTED cost
        # Stats worker sends a counter that increments ONLY if cost result changed due to settings
        pricing_update_id = stats.get("pricing_update_id", 0)
        if pricing_update_id > self._last_pricing_update_id:
             # Pricing logic changed: Reset COST flags only
            self._notification_state["daily_cost"] = False
            self._notification_state["monthly_cost"] = False
            self._last_pricing_update_id = pricing_update_id
            
        # 2. Check for specific threshold changes
        # Reset ONLY the flag for the threshold that changed
        current_thresholds = stats.get("thresholds", {})
        if self._last_thresholds: # Skip first run
            # Daily Tokens
            if current_thresholds.get("daily_tokens") != self._last_thresholds.get("daily_tokens"):
                self._notification_state["daily_tokens"] = False
            # Daily Cost
            if current_thresholds.get("daily_cost") != self._last_thresholds.get("daily_cost"):
                self._notification_state["daily_cost"] = False
            # Monthly Tokens
            if current_thresholds.get("monthly_tokens") != self._last_thresholds.get("monthly_tokens"):
                self._notification_state["monthly_tokens"] = False
            # Monthly Cost
            if current_thresholds.get("monthly_cost") != self._last_thresholds.get("monthly_cost"):
                self._notification_state["monthly_cost"] = False
        
        self._last_thresholds = current_thresholds
        
        # Key in stats, Pct Key in stats, Label, State Key
        metrics = [
            (today, 'token_pct', "Daily Token Limit", "daily_tokens"),
            (today, 'cost_pct', "Daily Cost Limit", "daily_cost"),
            (month, 'token_pct', "Monthly Token Limit", "monthly_tokens"),
            (month, 'cost_pct', "Monthly Cost Limit", "monthly_cost"),
        ]
        
        for stat_obj, pct_key, label, state_key in metrics:
            try:
                val = float(stat_obj.get(pct_key, 0))
            except (TypeError, ValueError):
                val = 0
            
            # Trigger if >= 100% AND not already notified for this period
            if val >= 100:
                if not self._notification_state[state_key]:
                    self._send_notification(
                        "Threshold Exceeded",
                        f"{label} has been reached ({val:.0f}%)"
                    )
                    self._notification_state[state_key] = True
            else:
                # Optional: specific reset if usage drops (unlikely for cumulative but good for correctness)
                # If usage < 100, we clear the flag so it can fire again if it goes back up?
                # Actually, better to keep it True until day reset to avoid flapping if it hovers at 99-100.
                # For now, let's stick to day/month reset.
                pass

    def _apply_stats(self, stats):
        thresholds_enabled = bool(stats.get("thresholds_enabled", False))
        
        if thresholds_enabled:
            self._check_thresholds(stats)

        today = stats.get("today", {}) if isinstance(stats, dict) else {}

        month = stats.get("month", {}) if isinstance(stats, dict) else {}

        today_in = self._format_tokens(today.get("input", 0))
        today_req = self._format_tokens(today.get("requests", 0))
        today_out = self._format_tokens((today.get("output", 0) or 0) + (today.get("reasoning", 0) or 0))
        today_cost = self._format_cost(today.get("cost", 0.0))

        month_in = self._format_tokens(month.get("input", 0))
        month_req = self._format_tokens(month.get("requests", 0))
        month_out = self._format_tokens((month.get("output", 0) or 0) + (month.get("reasoning", 0) or 0))
        month_cost = self._format_cost(month.get("cost", 0.0))
        month_cost = self._format_cost(month.get("cost", 0.0))

        # Update Headers with custom view for alignment
        self._set_menu_header_text(self._menu_items["today_header"], "Today")
        self._set_menu_header_text(self._menu_items["month_header"], "This Month")

        self._set_menu_item_text(self._menu_items["today_row1"], "In:", today_in, "Req:", today_req)
        self._set_menu_item_text(self._menu_items["today_row2"], "Out:", today_out, "Cost:", f"${today_cost}")
        self._set_menu_item_text(self._menu_items["month_row1"], "In:", month_in, "Req:", month_req)
        self._set_menu_item_text(self._menu_items["month_row2"], "Out:", month_out, "Cost:", f"${month_cost}")

        if thresholds_enabled:
            self._set_menu_item_text(
                self._menu_items["today_row3"],
                "Token:",
                f"{today.get('token_pct', 0)}%",
                "Cost:",
                f"{today.get('cost_pct', 0)}%"
            )
            self._set_menu_item_text(
                self._menu_items["month_row3"],
                "Token:",
                f"{month.get('token_pct', 0)}%",
                "Cost:",
                f"{month.get('cost_pct', 0)}%"
            )
            self._set_row_visible(self._menu_items["today_row3"], True)
            self._set_row_visible(self._menu_items["month_row3"], True)
        else:
            self._menu_items["today_row3"].title = ""
            self._menu_items["month_row3"].title = ""
            self._set_row_visible(self._menu_items["today_row3"], False)
            self._set_row_visible(self._menu_items["month_row3"], False)

    def start_auto_update(self, stats_path, interval=5):
        # State for threshold notifications
        self._notification_state = {
            "last_reset_day": None,
            "last_reset_month": None,
            "daily_tokens": False,
            "daily_cost": False,
            "monthly_tokens": False,
            "monthly_cost": False
        }
        self._last_pricing_update_id = 0
        self._last_thresholds = {}
        self._stats_path = stats_path
        self._interval = max(1, int(interval)) if interval else 5
        if self._timer is None:
            self._timer = rumps.Timer(self._refresh_stats, self._interval)
            self._timer.start()

    def _refresh_stats(self, _=None):
        stats = self._read_stats_file()
        self._apply_stats(stats)
        self._maybe_update_interval(stats)

    def _maybe_update_interval(self, stats):
        try:
            new_interval = int(stats.get("refresh_interval", self._interval))
        except (TypeError, ValueError):
            return
        # Allow fast polling (down to 1s) since we are just reading a local JSON file
        new_interval = max(1, new_interval)
        if new_interval == self._interval:
            return
        self._interval = new_interval
        try:
            if self._timer:
                self._timer.stop()
            self._timer = rumps.Timer(self._refresh_stats, self._interval)
            self._timer.start()
        except Exception:
            pass

    def notify_startup(self):
        if self._notified_startup or not self.notifications_enabled:
            return
        
        self._notified_startup = True
        
        # Try rumps notification first
        try:
            rumps.notification(
                "OpenCode Token Meter", 
                "Launch Success", 
                "The App is running in the menubar."
            )
        except Exception:
            pass
        
        # Fallback to osascript for better compatibility when running as script
        try:
            import subprocess
            script = '''
            display notification "The App is running in the menubar." with title "OpenCode Token Meter" subtitle "Launch Success"
            '''
            subprocess.run(['osascript', '-e', script], capture_output=True, timeout=2)
        except Exception:
            pass

    def run(self):
        if self._running:
            return
        self.create_app()
        if self._stats_path:
            self._refresh_stats()
        self.notify_startup()
        self._running = True
        self.app.run()
