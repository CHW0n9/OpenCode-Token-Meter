"""System tray icon implementation using pystray (Windows/Linux)"""
import json
import os
import platform
import threading
import time

from PIL import Image
import pystray
from pystray import Menu, MenuItem


class TrayManager:
    """Manages system tray icon and menu"""

    def __init__(self, on_show=None, on_quit=None, notifications_enabled=True):
        self.on_show = on_show
        self.on_quit = on_quit
        self.notifications_enabled = notifications_enabled
        self.icon = None
        self._running = False
        self._stats_path = None
        self._interval = 5
        self._notified_startup = False
        self._tab_size = 8
        self._left_value_stop = 2
        self._right_label_stop = 4
        self._right_value_stop = 6
        
        # Track threshold notification state: 0=OK, 1=80% warned, 2=100% warned
        self._threshold_state = {
            'today_token': 0, 'today_cost': 0,
            'month_token': 0, 'month_cost': 0
        }
        self._lines = {
            "today_header": "Today",
            "today_row1": self._build_row("In:", "--", "Req:", "--"),
            "today_row2": self._build_row("Out:", "--", "Cost:", "--"),
            "today_row3": "",
            "month_header": "This Month",
            "month_row1": self._build_row("In:", "--", "Req:", "--"),
            "month_row2": self._build_row("Out:", "--", "Cost:", "--"),
            "month_row3": "",
        }

    def get_icon_path(self):
        import sys
        system = platform.system()
        
        if getattr(sys, 'frozen', False):
            # Frozen mode
            if system == "Darwin":
                # macOS .app bundle
                resources_dir = os.path.join(os.path.dirname(sys.executable), "..", "Resources", "resources")
            else:
                # Windows/Linux PyInstaller one-dir
                # resources are usually in _internal/resources or just resources next to exe?
                # Based on file lists: dist/OpenCode Token Meter/_internal/resources/AppIcon.ico
                # sys.executable is inside dist/OpenCode Token Meter/
                # _internal is adjacent to exe?
                # Actually, standard PyInstaller behaviour:
                # sys._MEIPASS for onefile, or sys.executable dir for onedir
                # Let's try to locate 'resources' dir relative to internal directory
                base_path = os.path.dirname(os.path.abspath(__file__)) # This should be in _internal/webview_ui/backend
                # Go up to _internal root?
                # Safer to look relative to sys.executable for onedir
                exe_dir = os.path.dirname(sys.executable)
                resources_dir = os.path.join(exe_dir, "_internal", "resources")
                if not os.path.exists(resources_dir):
                     resources_dir = os.path.join(exe_dir, "resources")
        else:
            # Dev mode
            base_dir = os.path.dirname(os.path.dirname(__file__))
            resources_dir = os.path.join(base_dir, "web", "assets")

        if system == "Darwin":
             # Use template icon for macOS
            path = os.path.join(resources_dir, "icon_template@2x.png")
            if not os.path.exists(path):
                path = os.path.join(resources_dir, "icon_template.png")
            return path
            
        if system == "Windows":
            return os.path.join(resources_dir, "AppIcon.ico")
            
        return os.path.join(resources_dir, "AppIcon.png")

    def create_icon(self):
        icon_path = self.get_icon_path()
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        return Image.new("RGB", (64, 64), color="blue")

    def _item_text(self, key):
        return lambda _item: self._lines.get(key, "")

    def get_menu(self):
        return Menu(
            MenuItem(self._item_text("today_header"), None, enabled=False),
            MenuItem(self._item_text("today_row1"), None, enabled=False),
            MenuItem(self._item_text("today_row2"), None, enabled=False),
            MenuItem(self._item_text("today_row3"), None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(self._item_text("month_header"), None, enabled=False),
            MenuItem(self._item_text("month_row1"), None, enabled=False),
            MenuItem(self._item_text("month_row2"), None, enabled=False),
            MenuItem(self._item_text("month_row3"), None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Open Main Window", self._on_show_window),
            MenuItem("Quit", self._on_quit)
        )

    def _on_show_window(self, _icon, _item):
        if self.on_show:
            self.on_show()

    def _on_quit(self, _icon, _item):
        if self.on_quit:
            self.on_quit()
        if self.icon:
            self.icon.stop()
        os._exit(0)

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

    def _read_stats_file(self):
        if not self._stats_path or not os.path.exists(self._stats_path):
            return {}
        try:
            with open(self._stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _check_thresholds(self, stats):
        if not self.notifications_enabled:
            return

        today = stats.get("today", {})
        month = stats.get("month", {})
        
        # Key, Pct, Label
        metrics = [
            ('today_token', today.get('token_pct', 0), "Daily Token Limit"),
            ('today_cost', today.get('cost_pct', 0), "Daily Cost Limit"),
            ('month_token', month.get('token_pct', 0), "Monthly Token Limit"),
            ('month_cost', month.get('cost_pct', 0), "Monthly Cost Limit"),
        ]
        
        alerts = []
        
        for key, pct, label in metrics:
            try:
                val = float(pct)
            except (TypeError, ValueError):
                val = 0
            
            current_level = 0
            if val >= 100:
                current_level = 2
            elif val >= 80:
                current_level = 1
            
            last_level = self._threshold_state.get(key, 0)
            
            if current_level > last_level:
                # Upgrade: New threshold reached
                self._threshold_state[key] = current_level
                if current_level == 2:
                    alerts.append(f"{label} reached 100%!")
                else:
                    alerts.append(f"{label} reached 80%!")
            elif current_level < last_level:
                # Downgrade: Reset state (e.g. new day/month or limit increased)
                self._threshold_state[key] = current_level

        if alerts:
            msg = "\n".join(alerts)
            if self.icon and hasattr(self.icon, "notify"):
                self.icon.notify(msg, "Threshold Alert")

    def _apply_stats(self, stats):
        display = stats.get("display", {}) if isinstance(stats, dict) else {}
        thresholds_enabled = bool(stats.get("thresholds_enabled", False))

        if thresholds_enabled:
            self._check_thresholds(stats)

        if display:
            fallback_row1 = self._build_row("In:", "--", "Req:", "--")
            fallback_row2 = self._build_row("Out:", "--", "Cost:", "--")
            self._lines["today_row1"] = display.get("today_row1", fallback_row1)
            self._lines["today_row2"] = display.get("today_row2", fallback_row2)
            self._lines["month_row1"] = display.get("month_row1", fallback_row1)
            self._lines["month_row2"] = display.get("month_row2", fallback_row2)
        else:
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

            self._lines["today_row1"] = self._build_row("In:", today_in, "Req:", today_req)
            self._lines["today_row2"] = self._build_row("Out:", today_out, "Cost:", f"${today_cost}")
            self._lines["month_row1"] = self._build_row("In:", month_in, "Req:", month_req)
            self._lines["month_row2"] = self._build_row("Out:", month_out, "Cost:", f"${month_cost}")

        if thresholds_enabled:
            today_row3 = display.get("today_row3") if display else None
            month_row3 = display.get("month_row3") if display else None
            if not today_row3:
                today = stats.get("today", {}) if isinstance(stats, dict) else {}
                today_row3 = self._build_row("Token:", f"{today.get('token_pct', 0)}%", "Cost:", f"{today.get('cost_pct', 0)}%")
            if not month_row3:
                month = stats.get("month", {}) if isinstance(stats, dict) else {}
                month_row3 = self._build_row("Token:", f"{month.get('token_pct', 0)}%", "Cost:", f"{month.get('cost_pct', 0)}%")
            self._lines["today_row3"] = today_row3
            self._lines["month_row3"] = month_row3
        else:
            self._lines["today_row3"] = ""
            self._lines["month_row3"] = ""

        try:
            if self.icon:
                self.icon.update_menu()
        except Exception:
            pass

        try:
            new_interval = int(stats.get("refresh_interval", self._interval))
            new_interval = max(5, new_interval)
            self._interval = new_interval
        except (TypeError, ValueError):
            pass

    def start_auto_update(self, stats_path, interval=5):
        self._stats_path = stats_path
        self._interval = max(5, int(interval)) if interval else 5

        def loop():
            while True:
                stats = self._read_stats_file()
                self._apply_stats(stats)
                time.sleep(self._interval)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _notify_startup(self):
        if self._notified_startup or not self.notifications_enabled:
            return
        self._notified_startup = True
        try:
            if self.icon and hasattr(self.icon, "notify"):
                self.icon.notify("The App is running in the tray.", "OpenCode Token Meter")
        except Exception:
            pass

    def run(self):
        if self._running:
            return
        try:
            self.icon = pystray.Icon(
                "opencode_token_meter",
                self.create_icon(),
                "OpenCode Token Meter",
                self.get_menu()
            )
            self._running = True
            # notify after icon is ready
            threading.Timer(0.5, self._notify_startup).start()
            self.icon.run()
        except Exception as e:
            print(f"[Tray] Failed to start: {e}")
