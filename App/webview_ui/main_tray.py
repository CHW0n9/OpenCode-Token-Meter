"""Main entry point for OpenCode Token Meter - Tray version with subprocess webview

This version runs the system tray on the main thread and spawns a subprocess
for the webview window, solving the macOS threading conflict.
"""

import os
import sys
import subprocess
import argparse
import atexit
import signal
import platform
import time
import json
import socket
import threading
import asyncio

# Add paths for imports
# 1. Agent path (App/agent)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
# 2. App root path (App/) to allow imports like 'webview_ui.stats_worker'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# 3. Webview UI path (App/webview_ui) to allow imports like 'backend'
sys.path.insert(0, os.path.dirname(__file__))

# Import agent config and logger BEFORE tray imports (needed in except blocks)
from agent.config import BASE_DIR, SOCKET_PATH, TCP_HOST, TCP_PORT, USE_TCP
from agent.logger import log_info, log_warn, log_error
from backend.settings import Settings

# Import TrayManager based on platform
TrayManager = None
_system = platform.system()
if _system == "Darwin":
    try:
        from .backend.tray_rumps import TrayManager
    except ImportError:
        from backend.tray_rumps import TrayManager
elif _system == "Linux":
    # Linux: see LinuxTrayManager class defined below (inline D-Bus SNI)
    pass
else:
    try:
        from .backend.tray import TrayManager
    except ImportError:
        from backend.tray import TrayManager

# Import modules for threading
try:
    import agent.__main__ as agent_main

    # Try different import paths for stats_worker
    try:
        # If running from App/, this works
        import webview_ui.stats_worker as stats_worker
    except ImportError:
        # If running from App/webview_ui/, this works
        import stats_worker
except ImportError as e:
    raise RuntimeError(f"Failed to import required runtime modules: {e}") from e

# PID file to track webview process
WEBVIEW_PID_FILE = os.path.join(BASE_DIR, "webview.pid")
STATS_FILE = os.path.join(BASE_DIR, "tray_stats.json")
NAV_FILE = os.path.join(BASE_DIR, "nav.json")


# ---------------------------------------------------------------------------
# Linux Tray — pure D-Bus StatusNotifierItem (no pystray / GI introspection)
# ---------------------------------------------------------------------------
if _system == "Linux":
    import struct
    from PIL import Image
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    def _icon_to_pixmap(icon_path):
        """Load image and convert to SNI IconPixmap (ARGB32)."""
        if not icon_path or not os.path.exists(icon_path):
            return dbus.Array([], signature="(iiay)")
        try:
            img = Image.open(icon_path).convert("RGBA")
            img = img.resize((22, 22), Image.LANCZOS)
            w, h = img.size
            pixels = img.tobytes()
            argb_data = bytearray()
            for i in range(0, len(pixels), 4):
                r, g, b, a = pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]
                argb_data.extend(struct.pack(">BBBB", a, r, g, b))
            return dbus.Array(
                [
                    dbus.Struct(
                        (
                            dbus.Int32(w),
                            dbus.Int32(h),
                            dbus.ByteArray(bytes(argb_data)),
                        ),
                        signature="iiay",
                    )
                ],
                signature="(iiay)",
            )
        except Exception:
            return dbus.Array([], signature="(iiay)")

    class _StatusNotifierItem(dbus.service.Object):
        """org.kde.StatusNotifierItem D-Bus object with Properties support."""

        IFACE = "org.kde.StatusNotifierItem"
        PROP_IFACE = "org.freedesktop.DBus.Properties"

        def __init__(self, bus_name, object_path, icon_path, menu_path):
            super().__init__(bus_name, object_path)
            self._menu_path = menu_path
            self._title = "OpenCode Token Meter"
            self._status = "Active"
            self._icon_pixmap = _icon_to_pixmap(icon_path)
            self._tooltip = ("", dbus.Array([], signature="(ii)"), "", "")
            self._empty_pixmap = dbus.Array(
                [
                    dbus.Struct(
                        (dbus.Int32(0), dbus.Int32(0), dbus.ByteArray(b"")),
                        signature="iiay",
                    )
                ],
                signature="(iiay)",
            )

        # -- D-Bus Properties interface (required by GNOME AppIndicator) --

        def _get_property(self, iface, name):
            if iface != self.IFACE:
                return None
            props = {
                "Id": dbus.String("OpenCodeTokenMeter"),
                "Title": dbus.String(self._title),
                "Status": dbus.String(self._status),
                "IconName": dbus.String(""),
                "IconPixmap": self._icon_pixmap,
                "IconThemePath": dbus.String(""),
                "ToolTip": self._tooltip,
                "Menu": dbus.ObjectPath(self._menu_path),
                "Category": dbus.String("ApplicationStatus"),
                "AttentionIconName": dbus.String(""),
                "AttentionIconPixmap": self._empty_pixmap,
                "OverlayIconName": dbus.String(""),
                "OverlayIconPixmap": self._empty_pixmap,
                "WindowId": dbus.Int32(0),
                "ItemIsMenu": dbus.Boolean(False),
            }
            return props.get(name)

        @dbus.service.method(PROP_IFACE, in_signature="ss", out_signature="v")
        def Get(self, iface, name):
            val = self._get_property(iface, name)
            return val if val is not None else dbus.String("")

        @dbus.service.method(PROP_IFACE, in_signature="s", out_signature="a{sv}")
        def GetAll(self, iface):
            if iface != self.IFACE:
                return dbus.Dictionary({}, signature="sv")
            return dbus.Dictionary(
                {
                    "Id": dbus.String("OpenCodeTokenMeter"),
                    "Title": dbus.String(self._title),
                    "Status": dbus.String(self._status),
                    "IconName": dbus.String(""),
                    "IconPixmap": self._icon_pixmap,
                    "IconThemePath": dbus.String(""),
                    "ToolTip": self._tooltip,
                    "Menu": dbus.ObjectPath(self._menu_path),
                    "Category": dbus.String("ApplicationStatus"),
                    "AttentionIconName": dbus.String(""),
                    "AttentionIconPixmap": self._empty_pixmap,
                    "OverlayIconName": dbus.String(""),
                    "OverlayIconPixmap": self._empty_pixmap,
                    "WindowId": dbus.Int32(0),
                    "ItemIsMenu": dbus.Boolean(False),
                },
                signature="sv",
            )

        # -- SNI signals --

        @dbus.service.signal(IFACE, signature="")
        def NewTitle(self):
            pass

        @dbus.service.signal(IFACE, signature="")
        def NewIcon(self):
            pass

        @dbus.service.signal(IFACE, signature="")
        def NewStatus(self):
            pass

        @dbus.service.signal(IFACE, signature="")
        def NewToolTip(self):
            pass

        def update_tooltip(self, title, desc):
            self._tooltip = ("", dbus.Array([], signature="(ii)"), title, desc)
            self.NewToolTip()

    class _DBusMenu(dbus.service.Object):
        """com.canonical.dbusmenu D-Bus object."""

        IFACE = "com.canonical.dbusmenu"

        def __init__(self, bus_name, object_path):
            super().__init__(bus_name, object_path)
            self._revision = 0
            self._items = []
            self._id_counter = 0

        def add_item(self, label, callback=None, enabled=True, item_type="standard"):
            self._id_counter += 1
            item = {
                "id": self._id_counter,
                "label": label,
                "enabled": enabled,
                "type": item_type,
                "callback": callback,
            }
            self._items.append(item)
            return item

        def add_separator(self):
            self._id_counter += 1
            item = {
                "id": self._id_counter,
                "label": "",
                "enabled": False,
                "type": "separator",
                "callback": None,
            }
            self._items.append(item)
            return item

        def update_label(self, item, label):
            if item:
                item["label"] = label

        def emit_updated(self):
            self._revision += 1
            self.LayoutUpdated(self._revision, 0)

        @dbus.service.method(IFACE, in_signature="iias", out_signature="u(ia{sv}av)")
        def GetLayout(self, parent_id, recursion_depth, property_names):
            children = []
            for it in self._items:
                props = {
                    "label": dbus.String(it["label"]),
                    "enabled": dbus.Boolean(it["enabled"]),
                }
                if it["type"] == "separator":
                    props["type"] = dbus.String("separator")
                children.append(
                    dbus.Struct(
                        (
                            dbus.Int32(it["id"]),
                            dbus.Dictionary(props, signature="sv"),
                            dbus.Array([], signature="v"),
                        ),
                        signature="ia{sv}av",
                    )
                )
            return (
                dbus.UInt32(self._revision),
                dbus.Struct(
                    (
                        dbus.Int32(0),
                        dbus.Dictionary(
                            {"children-display": dbus.String("submenu")}, signature="sv"
                        ),
                        dbus.Array(children, signature="(ia{sv}av)"),
                    ),
                    signature="ia{sv}av",
                ),
            )

        @dbus.service.method(IFACE, in_signature="auas", out_signature="u(ia{sv}av)")
        def GetGroupProperties(self, ids, property_names):
            return (
                dbus.UInt32(self._revision),
                dbus.Struct(
                    (
                        dbus.Int32(0),
                        dbus.Dictionary(
                            {"children-display": dbus.String("submenu")}, signature="sv"
                        ),
                        dbus.Array([], signature="(ia{sv}av)"),
                    ),
                    signature="ia{sv}av",
                ),
            )

        @dbus.service.method(IFACE, in_signature="is", out_signature="v")
        def GetProperty(self, item_id, name):
            for it in self._items:
                if it["id"] == item_id:
                    return dbus.String(it.get(name, ""))
            return dbus.String("")

        @dbus.service.method(IFACE, in_signature="isvu", out_signature="b")
        def Event(self, item_id, event_id, data, timestamp):
            if event_id == "clicked":
                for it in self._items:
                    if it["id"] == item_id and it.get("callback"):
                        it["callback"]()
                        return dbus.Boolean(True)
            return dbus.Boolean(False)

        @dbus.service.signal(IFACE, signature="ui")
        def LayoutUpdated(self, revision, parent):
            pass

    class LinuxTrayManager:
        """Linux tray via pure D-Bus StatusNotifierItem."""

        def __init__(self, on_show=None, on_quit=None, notifications_enabled=True):
            self.on_show = on_show
            self.on_quit = on_quit
            self.notifications_enabled = notifications_enabled
            self._running = False
            self._stats_path = None
            self._interval = 5
            self._notified_startup = False
            self._loop = None
            self._sni_obj = None
            self._menu_obj = None
            self._menu_items = {}
            self._threshold_state = {
                "today_token": 0,
                "today_cost": 0,
                "month_token": 0,
                "month_cost": 0,
            }
            self._tab_size = 8
            self._left_value_stop = 2
            self._right_label_stop = 4
            self._right_value_stop = 6
            self._icon_path = self._get_icon_path()

        def _get_icon_path(self):
            if getattr(sys, "frozen", False):
                meipass = getattr(sys, "_MEIPASS", None)
                if meipass:
                    return os.path.join(meipass, "resources", "AppIcon.png")
                exe_dir = os.path.dirname(sys.executable)
                for sub in ("_internal/resources", "resources"):
                    p = os.path.join(exe_dir, sub, "AppIcon.png")
                    if os.path.exists(p):
                        return p
            base = os.path.dirname(__file__)
            return os.path.join(base, "web", "assets", "AppIcon.png")

        # -- layout helpers (shared with tray.py) --------------------------

        def _format_tokens(self, num):
            if num is None:
                return "--"
            try:
                n = int(num)
            except (TypeError, ValueError):
                return "--"
            if n >= 1_000_000:
                return f"{n / 1_000_000:.1f}M"
            if n >= 1000:
                return f"{n / 1000:.1f}K"
            return str(n)

        def _format_cost(self, value):
            if value is None:
                return "--"
            try:
                return f"{float(value):.2f}"
            except (TypeError, ValueError):
                return "--"

        def _pad_to_col(self, text, col):
            if len(text) < col:
                return text + (" " * (col - len(text)))
            return text + " "

        def _default_columns(self):
            return (
                self._tab_size * self._left_value_stop,
                self._tab_size * self._right_label_stop,
                self._tab_size * self._right_value_stop,
            )

        def _compute_columns(
            self, left_labels, left_values, right_labels, right_values
        ):
            base_l, base_rl, base_rv = self._default_columns()
            max_ll = max((len(str(v)) for v in left_labels), default=0)
            max_lv = max((len(str(v)) for v in left_values), default=0)
            max_rl = max((len(str(v)) for v in right_labels), default=0)
            max_rv = max((len(str(v)) for v in right_values), default=0)
            lv = max(base_l, max_ll + 1)
            rl = max(base_rl, lv + max_lv + 2)
            rv = max(base_rv, rl + max_rl + 2)
            rv = max(rv, rl + max_rl + 1 + max_rv)
            return lv, rl, rv

        def _build_row(self, ll, lv, rl, rv, cols=None):
            # Keep label/value spacing with tabs only.
            # Normal rows: 2 tabs after label, 1 tab between columns.
            # In: row: 3 tabs after label.
            if ll == "In:":
                return f"{ll}\t\t\t{str(lv)}\t\t{rl}\t\t{str(rv)}"
            return f"{ll}\t\t{str(lv)}\t\t{rl}\t\t{str(rv)}"

        # -- D-Bus setup ---------------------------------------------------

        def _setup_dbus(self):
            DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()
            svc = dbus.service.BusName(
                f"org.kde.StatusNotifierItem-pid{os.getpid()}", bus
            )
            self._menu_obj = _DBusMenu(svc, "/MenuBar")
            self._build_menu()
            self._sni_obj = _StatusNotifierItem(
                svc, "/StatusNotifierItem", self._icon_path, "/MenuBar"
            )
            try:
                watcher = dbus.Interface(
                    bus.get_object(
                        "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher"
                    ),
                    "org.kde.StatusNotifierWatcher",
                )
                watcher.RegisterStatusNotifierItem(svc.get_name())
            except dbus.exceptions.DBusException as e:
                log_warn("Tray", f"Failed to register SNI: {e}")

        def _build_menu(self):
            m = self._menu_obj
            self._menu_items["today_header"] = m.add_item("— Today —", enabled=True)
            self._menu_items["today_row1"] = m.add_item(
                self._build_row("In:", "--", "Req:", "--"), enabled=True
            )
            self._menu_items["today_row2"] = m.add_item(
                self._build_row("Out:", "--", "Cost:", "--"), enabled=True
            )
            self._menu_items["today_row3"] = m.add_item("", enabled=True)
            m.add_separator()
            self._menu_items["month_header"] = m.add_item(
                "— This Month —", enabled=True
            )
            self._menu_items["month_row1"] = m.add_item(
                self._build_row("In:", "--", "Req:", "--"), enabled=True
            )
            self._menu_items["month_row2"] = m.add_item(
                self._build_row("Out:", "--", "Cost:", "--"), enabled=True
            )
            self._menu_items["month_row3"] = m.add_item("", enabled=True)
            m.add_separator()
            self._menu_items["show"] = m.add_item(
                "Open Main Window", callback=self._cb_show
            )
            self._menu_items["quit"] = m.add_item("Quit", callback=self._cb_quit)

        def _cb_show(self):
            if self.on_show:
                self.on_show()

        def _cb_quit(self):
            if self.on_quit:
                self.on_quit()
            if self._loop:
                self._loop.quit()

        # -- stats ---------------------------------------------------------

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
            metrics = [
                ("today_token", today.get("token_pct", 0), "Daily Token Limit"),
                ("today_cost", today.get("cost_pct", 0), "Daily Cost Limit"),
                ("month_token", month.get("token_pct", 0), "Monthly Token Limit"),
                ("month_cost", month.get("cost_pct", 0), "Monthly Cost Limit"),
            ]
            alerts = []
            for key, pct, label in metrics:
                try:
                    val = float(pct)
                except (TypeError, ValueError):
                    val = 0
                level = 2 if val >= 100 else (1 if val >= 80 else 0)
                if level > self._threshold_state.get(key, 0):
                    self._threshold_state[key] = level
                    alerts.append(f"{label} reached {100 if level == 2 else 80}%!")
                elif level < self._threshold_state.get(key, 0):
                    self._threshold_state[key] = level
            if alerts:
                try:
                    subprocess.run(
                        [
                            "notify-send",
                            "-a",
                            "OpenCode Token Meter",
                            "-u",
                            "critical",
                            "Threshold Alert",
                            "\n".join(alerts),
                        ],
                        capture_output=True,
                    )
                except Exception:
                    pass

        def _apply_stats(self, stats):
            if self._menu_obj is None:
                return
            thresholds_enabled = bool(stats.get("thresholds_enabled", False))
            if thresholds_enabled:
                self._check_thresholds(stats)
            today = stats.get("today", {}) if isinstance(stats, dict) else {}
            month = stats.get("month", {}) if isinstance(stats, dict) else {}
            t_in = self._format_tokens(today.get("input", 0))
            t_req = self._format_tokens(today.get("requests", 0))
            t_out = self._format_tokens(
                (today.get("output", 0) or 0) + (today.get("reasoning", 0) or 0)
            )
            t_cost = self._format_cost(today.get("cost", 0.0))
            m_in = self._format_tokens(month.get("input", 0))
            m_req = self._format_tokens(month.get("requests", 0))
            m_out = self._format_tokens(
                (month.get("output", 0) or 0) + (month.get("reasoning", 0) or 0)
            )
            m_cost = self._format_cost(month.get("cost", 0.0))
            cols = self._compute_columns(
                ["In:", "Out:"],
                [t_in, t_out, m_in, m_out],
                ["Req:", "Cost:"],
                [t_req, f"${t_cost}", m_req, f"${m_cost}"],
            )
            mi = self._menu_items
            mu = self._menu_obj.update_label
            mu(mi.get("today_header"), "Today")
            mu(mi.get("today_row1"), self._build_row("In:", t_in, "Req:", t_req, cols))
            mu(
                mi.get("today_row2"),
                self._build_row("Out:", t_out, "Cost:", f"${t_cost}", cols),
            )
            mu(mi.get("month_header"), "This Month")
            mu(mi.get("month_row1"), self._build_row("In:", m_in, "Req:", m_req, cols))
            mu(
                mi.get("month_row2"),
                self._build_row("Out:", m_out, "Cost:", f"${m_cost}", cols),
            )
            if thresholds_enabled:
                tp = f"{today.get('token_pct', 0)}%"
                cp = f"{today.get('cost_pct', 0)}%"
                mp = f"{month.get('token_pct', 0)}%"
                mc = f"{month.get('cost_pct', 0)}%"
                mu(mi.get("today_row3"), self._build_row("Token:", tp, "Cost:", cp))
                mu(mi.get("month_row3"), self._build_row("Token:", mp, "Cost:", mc))
            else:
                mu(mi.get("today_row3"), "")
                mu(mi.get("month_row3"), "")
            if self._sni_obj:
                self._sni_obj.update_tooltip(
                    "OpenCode Token Meter",
                    f"In: {t_in}  Out: {t_out}\nCost: ${t_cost}  Req: {t_req}",
                )
            self._menu_obj.emit_updated()
            try:
                self._interval = max(
                    5, int(stats.get("refresh_interval", self._interval))
                )
            except (TypeError, ValueError):
                pass

        def start_auto_update(self, stats_path, interval=5):
            self._stats_path = stats_path
            self._interval = max(5, int(interval)) if interval else 5

            def loop():
                while True:
                    self._apply_stats(self._read_stats_file())
                    time.sleep(self._interval)

            threading.Thread(target=loop, daemon=True).start()

        def _notify_startup(self):
            if self._notified_startup or not self.notifications_enabled:
                return
            self._notified_startup = True
            try:
                subprocess.run(
                    [
                        "notify-send",
                        "-a",
                        "OpenCode Token Meter",
                        "OpenCode Token Meter",
                        "The App is running in the tray.",
                    ],
                    capture_output=True,
                )
            except Exception:
                pass

        def run(self):
            if self._running:
                return
            try:
                self._setup_dbus()
                # Apply initial stats immediately after menu is created
                self._apply_stats(self._read_stats_file())
                self._running = True
                threading.Timer(0.5, self._notify_startup).start()
                self._loop = GLib.MainLoop()
                self._loop.run()
            except Exception as e:
                log_error("Tray", f"Linux tray failed: {e}")

    # Assign as the TrayManager for Linux
    TrayManager = LinuxTrayManager


class TrayAppWithSubprocess:
    """Main application that runs tray and manages webview subprocess"""

    def __init__(self, debug=False, show_window=False):
        self.debug = debug
        self.show_window = show_window
        self.webview_process = None
        self.platform = platform.system()
        self.agent_client = None
        self._cleanup_called = False

        # Threading controls
        self.agent_thread = None
        self.agent_stop_event = threading.Event()
        self.stats_thread = None
        self.stats_stop_event = threading.Event()

    def _start_agent_thread(self):
        """Start the agent in a background thread"""
        log_info("Tray", "Starting Agent thread...")

        def agent_runner():
            try:
                # asyncio.run() creates a new event loop for this thread
                asyncio.run(agent_main.main(threading_stop_event=self.agent_stop_event))
            except Exception as e:
                log_error("Tray", f"Agent thread failed: {e}")

        self.agent_thread = threading.Thread(
            target=agent_runner, name="AgentThread", daemon=True
        )
        self.agent_thread.start()

    def _start_stats_thread(self):
        """Start the stats worker in a background thread"""
        log_info("Tray", "Starting Stats Worker thread...")

        def stats_runner():
            try:
                stats_worker.main(stop_event=self.stats_stop_event)
            except Exception as e:
                log_error("Tray", f"Stats worker thread failed: {e}")

        self.stats_thread = threading.Thread(
            target=stats_runner, name="StatsThread", daemon=True
        )
        self.stats_thread.start()

    def _get_webview_pid(self):
        """Get stored webview PID"""
        try:
            if os.path.exists(WEBVIEW_PID_FILE):
                with open(WEBVIEW_PID_FILE, "r") as f:
                    return int(f.read().strip())
        except:
            pass
        return None

    def _save_webview_pid(self, pid):
        """Store webview PID"""
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(WEBVIEW_PID_FILE, "w") as f:
            f.write(str(pid))

    def _clear_webview_pid(self):
        """Clear stored webview PID"""
        try:
            if os.path.exists(WEBVIEW_PID_FILE):
                os.remove(WEBVIEW_PID_FILE)
        except:
            pass

    def _is_webview_running(self):
        """Check if webview process is still running with robust verification"""
        pid = self._get_webview_pid()
        if pid is None:
            return False

        # Basic existence check - works on all platforms
        try:
            os.kill(pid, 0)
        except OSError:
            self._clear_webview_pid()
            return False

        # Advanced check: Verify the process is actually ours
        # This prevents PID reuse conflicts (stale PID file pointing to a new unrelated process)
        try:
            import platform

            if platform.system() == "Windows":
                # Windows: use tasklist to check process existence
                # Output format: "imagename PID sessionname session# mem usage"
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and str(pid) in result.stdout:
                    return True
                else:
                    log_info("Tray", f"PID {pid} not found in tasklist")
                    self._clear_webview_pid()
                    return False
            else:
                # Unix/macOS: use ps to get command line for the pid
                # Output format: "command_args"
                cmd = ["ps", "-p", str(pid), "-o", "command="]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    output = result.stdout.strip()
                    # Check keywords that should be in our webview process
                    # Frozen: "OpenCode Token Meter" or similar
                    # Dev: "python" and "main.py"
                    if (
                        "main.py" in output
                        or "OpenCode Token Meter" in output
                        or "webview" in output
                    ):
                        return True
                    else:
                        log_info(
                            "Tray",
                            f"PID {pid} exists but seems to be a different process: {output[:50]}...",
                        )
                        self._clear_webview_pid()
                        return False
                else:
                    # ps failed? Assume running if kill changed nothing, but maybe not?
                    # If ps failed, satisfy with kill check
                    return True
        except Exception as e:
            log_warn("Tray", f"Failed to verify process args: {e}")
            return True  # Fallback to trusting os.kill logic if ps fails

        return True

    def _write_nav_file(self, page):
        """Write navigation command to file for webview to read"""
        nav_data = {"target": page, "timestamp": time.time()}
        try:
            os.makedirs(BASE_DIR, exist_ok=True)
            with open(NAV_FILE, "w") as f:
                json.dump(nav_data, f)
        except Exception as e:
            log_warn("Tray", f"Failed to write nav file: {e}")

    def start_webview_subprocess(self, page="dashboard"):
        """Start webview in a separate subprocess (only if not already running)"""
        # Check if already running
        if self._is_webview_running():
            log_info(
                "Tray",
                f"Webview already running (PID: {self._get_webview_pid()}), navigating to {page}",
            )
            self._write_nav_file(page)
            return

        if self.webview_process is not None:
            if self.webview_process.poll() is None:
                log_info(
                    "Tray",
                    f"Webview subprocess already running (PID: {self.webview_process.pid})",
                )
                self._write_nav_file(page)
                return
            else:
                self.webview_process = None

        # Build command with page parameter
        if getattr(sys, "frozen", False):
            # In frozen mode, call the executable with --webview flag
            cmd = [sys.executable, "--webview", "--page", page]
        else:
            # Get the current script path
            # Use main.py instead of webview_runner.py
            webview_script = os.path.join(os.path.dirname(__file__), "main.py")
            if not os.path.exists(webview_script):
                log_error("Tray", f"Webview script not found: {webview_script}")
                return
            cmd = [sys.executable, webview_script, "--no-tray", "--page", page]

        if self.debug:
            cmd.append("--debug")

        log_info("Tray", f"Starting webview subprocess with command: {cmd}")

        # Start subprocess - capture output for debugging
        stdout_dest = None if self.debug else subprocess.DEVNULL
        stderr_dest = None if self.debug else subprocess.DEVNULL

        if getattr(sys, "frozen", False):
            # In frozen mode, log subprocess output to a file if needed, or let it go to system log
            self.webview_process = subprocess.Popen(
                cmd, stdout=stdout_dest, stderr=stderr_dest, start_new_session=True
            )
        else:
            # In dev mode, inherit stdout/stderr so we can see it in terminal
            self.webview_process = subprocess.Popen(
                cmd, stdout=stdout_dest, stderr=stderr_dest, start_new_session=True
            )

        # Store PID
        self._save_webview_pid(self.webview_process.pid)
        log_info("Tray", f"Webview started (PID: {self.webview_process.pid})")

        # Register cleanup
        atexit.register(self.cleanup_webview)

    def cleanup_webview(self):
        """Clean up webview subprocess"""
        pid = None
        if self.webview_process is not None:
            try:
                pid = self.webview_process.pid
                self.webview_process.terminate()
                self.webview_process.wait(timeout=5)
            except Exception as e:
                log_warn("Tray", f"Error cleaning up webview process: {e}")
            self.webview_process = None

        if pid is None:
            pid = self._get_webview_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        self._clear_webview_pid()

    def on_show_window(self, page="dashboard"):
        """Called when user requests to show window"""
        log_info("Tray", f"Show window requested with page: {page}")
        self.start_webview_subprocess(page=page)

    def on_refresh(self):
        """Called when user requests refresh"""
        log_info("Tray", "Refresh requested")
        # Since agent is running in this process (different thread), we could technically call it directly?
        # But for thread safety, using the IPC mechanism is still safest and simplest without refactoring everything.
        try:
            msg = json.dumps({"cmd": "refresh"}) + "\n"
            if USE_TCP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((TCP_HOST, TCP_PORT))
                sock.sendall(msg.encode())
                sock.close()
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(SOCKET_PATH)
                sock.sendall(msg.encode())
                sock.close()
            log_info("Tray", "Refresh command sent to agent")
        except Exception as e:
            log_warn("Tray", f"Failed to send refresh command: {e}")

    def on_details(self):
        """Called when user requests details view"""
        log_info("Tray", "Show details requested")
        self.on_show_window(page="details")

    def on_export(self, scope):
        """Called when user requests export"""
        log_info("Tray", f"Export requested: {scope}")
        self.on_show_window(page="details")

    def on_settings(self):
        """Called when user requests settings"""
        log_info("Tray", "Settings requested")
        self.on_show_window(page="settings")

    def on_reconnect(self):
        """Called when user requests agent reconnect"""
        log_info("Tray", "Reconnect requested - Restarting Agent Thread")

        # Stop existing
        self.agent_stop_event.set()
        if self.agent_thread and self.agent_thread.is_alive():
            self.agent_thread.join(timeout=2)

        # Restart
        self.agent_stop_event.clear()
        self._start_agent_thread()

    def on_quit(self):
        """Called when user requests quit"""
        log_info("Tray", "Quit requested")
        self._cleanup_on_exit()
        # Do NOT call sys.exit(0) here - let rumps handle the exit loop
        # The TrayManager will call rumps.quit_application() after this callback returns

    def _cleanup_on_exit(self):
        if self._cleanup_called:
            return
        self._cleanup_called = True

        log_info("Tray", "Cleaning up threads and processes...")

        # Signal threads to stop
        self.agent_stop_event.set()
        self.stats_stop_event.set()

        # Cleanup webview
        self.cleanup_webview()

        # Wait for threads? (Optional, daemon threads will be killed anyway on exit)
        # But better to be explicit if possible.

    def run(self):
        """Run the application"""
        log_info(
            "Tray", f"Starting OpenCode Token Meter (Tray Mode) on {self.platform}"
        )

        # Ensure BASE_DIR exists
        os.makedirs(BASE_DIR, exist_ok=True)

        # Start background threads
        self._start_agent_thread()
        self._start_stats_thread()

        atexit.register(self._cleanup_on_exit)

        # Create and run tray with all callbacks
        if TrayManager is None:
            raise RuntimeError("TrayManager is unavailable on this platform")

        settings = Settings()

        refresh_interval = settings.get("refresh_interval", 5)
        notifications_enabled = settings.get("notifications_enabled", True)
        tray = TrayManager(
            on_show=self.on_show_window,
            on_quit=self.on_quit,
            notifications_enabled=notifications_enabled,
        )
        try:
            refresh_interval = max(1, int(refresh_interval))
        except (TypeError, ValueError):
            refresh_interval = 5
        tray.start_auto_update(STATS_FILE, interval=refresh_interval)

        # Auto-show window if requested
        if self.show_window:
            log_info("Tray", "Auto-showing window on startup")
            # We need to defer this slightly to ensure tray is ready?
            # Or just call it directly. subprocess call is non-blocking to tray loop.
            self.start_webview_subprocess(page="dashboard")

        tray.run()


def main(debug=False, show_window=False):
    """Main entry point"""
    app = TrayAppWithSubprocess(debug=debug, show_window=show_window)
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode Token Meter - Tray Mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--window", action="store_true", help="Show window on startup")
    args = parser.parse_args()

    main(debug=args.debug, show_window=args.window)
