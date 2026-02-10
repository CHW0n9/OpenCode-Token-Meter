"""
OpenCode Token Meter - PyQt6 Menubar Application
"""
import os
import sys
import platform
import threading
import time
import subprocess
import json
from typing import Optional, Dict, Any, Tuple, cast
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox, 
                                QHBoxLayout, QFileDialog, QWidgetAction, QLabel, QWidget)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QPoint, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction, QCursor

from menubar.uds_client import AgentClient

from menubar.settings import Settings
from menubar.utils.ui_helpers import get_resource_path, get_icon_path
from menubar.windows import (MainStatsWindow, DetailsDialog, SettingsDialog, 
                             CustomRangeDialog, CustomRangeStatsDialog, ModelUpdateDialog)

# Import agent config for cross-platform paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
try:
    from agent.config import BASE_DIR # type: ignore
except (ImportError, ModuleNotFoundError):
    # Fallback for development/different structures
    BASE_DIR = os.path.expanduser("~/.opencode_token_meter")

# Path for tracking last agent start time to prevent infinite loops
LAST_START_FILE = os.path.join(BASE_DIR, "last_agent_start.json")


class StatsUpdateSignal(QObject):
    """Signal emitter for stats updates"""
    update = pyqtSignal()


class OpenCodeTokenMeter:
    """Main application with system tray icon"""
    
    def __init__(self):
        self.client: AgentClient = AgentClient()
        self.settings: Settings = Settings()
        
        # Track if tray icon and notifications are ready
        self.tray_icon_ready: bool = False

        # Notification deduplication window (seconds)
        self._notification_history: Dict[Tuple[str, str], float] = {}
        self._notification_dedup_seconds: int = 3
        
        # Track threshold notification state to prevent spam
        self.last_threshold_state: Dict[str, bool] = {
            'daily_tokens': False,
            'daily_cost': False,
            'monthly_tokens': False,
            'monthly_cost': False
        }
        
        # Track agent loading state
        self.agent_online: bool = False
        
        # Cache for stats
        self.stats_cache: Dict[str, Optional[Dict[str, Any]]] = {
            'current_session': None,
            'today': None,
            '7days': None,
            'month': None
        }
        
        # Cache for model-specific cost calculations
        self.cost_cache: Dict[str, Optional[float]] = {
            'current_session': None,
            'today': None,
            '7days': None,
            'month': None
        }
        
        # Window management - track all open dialogs/windows
        self.main_window: Optional[MainStatsWindow] = None
        self.details_dialog: Optional[DetailsDialog] = None
        self.settings_dialog: Optional[SettingsDialog] = None
        self.custom_range_dialog: Optional[CustomRangeDialog] = None
        self.custom_stats_dialog: Optional[CustomRangeStatsDialog] = None
        self.model_update_dialog: Optional[ModelUpdateDialog] = None
        
        # Action for reconnecting agent
        self.reconnect_action: Optional[QAction] = None
        
        # Create system tray icon
        self.create_tray_icon()
        
        # Signal for cross-thread stats updates
        self.signal = StatsUpdateSignal()
        self.signal.update.connect(self._update_all_stats)
        
        # Start auto-refresh thread
        self.auto_refresh_enabled = True
        self.refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self.refresh_thread.start()
        
        # Start agent in background (non-blocking)
        self.agent_start_thread = threading.Thread(target=self._manage_agent_background, daemon=True)
        self.agent_start_thread.start()
        
        # Start agent status check timer (check every 2 seconds)
        self.agent_check_retries = 0
        self.agent_check_timer = QTimer()
        self.agent_check_timer.timeout.connect(self._check_agent_status)
        self.agent_check_timer.start(2000)  # 2 seconds
        
        # Check for version updates after a short delay (to let UI load)
        QTimer.singleShot(3000, self._check_version_update)
    
    def _check_version_update(self):
        """Check if app version has changed and show update dialog if needed (non-modal)"""
        try:
            needs_update, current_ver, app_ver, new_models, customized_models = self.settings.check_version_update()
            
            if needs_update:
                print(f"Version update detected: {current_ver} -> {app_ver}")
                print(f"New models: {new_models}")
                print(f"Customized models: {customized_models}")
                
                # Show update dialog (NON-MODAL)
                self.model_update_dialog = ModelUpdateDialog(self.settings, new_models, customized_models, None)
                self.model_update_dialog.accepted.connect(self._on_model_update_accepted)
                self.model_update_dialog.show()
                self.model_update_dialog.raise_()
                self.model_update_dialog.activateWindow()
        except Exception as e:
            print(f"Error checking version update: {e}")

    def _on_model_update_accepted(self):
        """Handle user choice from ModelUpdateDialog"""
        if not self.model_update_dialog:
            return
        try:
            choice_data = self.model_update_dialog.get_result()
            choice = choice_data['choice']
            selected_models = choice_data['selected_models']
            app_ver = self.settings.get_app_version()
            
            # Process user's choice
            if choice == 'update_all':
                # Reset all models to default
                self.settings.reset_all_models_to_default()
                self._show_notification(
                    "OpenCode Token Meter",
                    f"All model prices updated to version {app_ver}",
                    QSystemTrayIcon.MessageIcon.Information
                )
            elif choice == 'selective':
                # Update only selected customized models
                for model_id in selected_models:
                    self.settings.reset_model_to_default(model_id)
                # Add new models
                added = self.settings.add_new_models()
                msg = f"Updated {len(selected_models)} models and added {len(added)} new models"
                self._show_notification(
                    "OpenCode Token Meter",
                    msg,
                    QSystemTrayIcon.MessageIcon.Information
                )
            else:  # 'keep_all'
                # Just add new models, keep all custom prices
                added = self.settings.add_new_models()
                if added:
                    self._show_notification(
                        "OpenCode Token Meter",
                        f"Added {len(added)} new models. Your custom prices are preserved.",
                        QSystemTrayIcon.MessageIcon.Information
                    )
            
            # Update version
            self.settings.update_version()
            # Refresh stats in case prices changed
            self._update_all_stats()
        except Exception as e:
            print(f"Error processing model update: {e}")
    
    def _manage_agent_background(self):
        """Start agent in background thread (non-blocking)"""
        self._manage_agent()
        # Don't wait for agent to come online - let the timer handle it
        print("Agent started in background, status check timer running")
    
    def _manage_agent(self):
        """
        Manage agent startup with support for:
        1. Embedded agent (PyInstaller bundle with agent module)
        2. External agent executable
        3. Source code mode
        """
        # Check last start time to prevent rapid restarts
        os.makedirs(os.path.dirname(LAST_START_FILE), exist_ok=True)
        
        last_start_time = 0
        try:
            if os.path.exists(LAST_START_FILE):
                with open(LAST_START_FILE, 'r') as f:
                    data = json.load(f)
                    last_start_time = data.get('time', 0)
        except:
            pass
        
        current_time = time.time()
        if current_time - last_start_time < 10:
            print(f"Agent was started {current_time - last_start_time:.1f}s ago, skipping restart to prevent loop")
            return
        
        # Check if agent is already online
        if self.client.is_online():
            print("Agent is already online")
            return
        
        # Check if running in PyInstaller bundle with embedded agent
        if getattr(sys, 'frozen', False):
            print("Detected PyInstaller bundle - checking for embedded agent module")
            try:
                # Try to import agent module (embedded in bundle)
                import agent.uds_server # type: ignore
                print(f"Successfully imported agent.uds_server from: {agent.uds_server.__file__}")
                print("Found embedded agent module - starting in background thread")
                self._start_embedded_agent()
                # Record start time
                with open(LAST_START_FILE, 'w') as f:
                    json.dump({'time': current_time}, f)
                return
            except ImportError as e:
                print(f"No embedded agent module found: {e}")
        
        # Try to find external agent executable or source
        agent_paths = [
            # macOS bundle
            os.path.join(os.path.dirname(sys.executable), "..", "Resources", "bin", "opencode-agent"),
            # When running from source
            os.path.join(os.path.dirname(__file__), "..", "..", "agent"),
            # Installed macOS app
            "/Applications/OpenCode Token Meter.app/Contents/Resources/bin/opencode-agent",
            # Development path
            os.path.expanduser("~/Desktop/OpenCode Token Meter/App/agent"),
        ]
        
        for agent_path in agent_paths:
            # Check if it's a bundled executable
            if os.path.exists(agent_path) and os.path.isfile(agent_path):
                try:
                    print(f"Starting agent from: {agent_path}")
                    proc = subprocess.Popen(
                        [agent_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True
                    )
                    print(f"Agent process started with PID: {proc.pid}")
                    # Record start time
                    with open(LAST_START_FILE, 'w') as f:
                        json.dump({'time': current_time}, f)
                    # Wait for agent to initialize
                    print("Waiting for agent to complete quick scan...")
                    time.sleep(3)
                    
                    if proc.poll() is None:
                        print("Agent process is still running")
                    
                    if self.client.is_online():
                        print("Agent started successfully and is online")
                        return
                    else:
                        print("Agent process started but not responding yet")
                        return
                except Exception as e:
                    print(f"Failed to start agent: {e}")
            # Check if it's a source directory
            elif os.path.exists(os.path.join(agent_path, "agent", "__main__.py")):
                try:
                    print(f"Starting agent from source: {agent_path}")
                    subprocess.Popen(
                        [sys.executable, "-m", "agent"],
                        cwd=agent_path,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    # Record start time
                    with open(LAST_START_FILE, 'w') as f:
                        json.dump({'time': current_time}, f)
                    time.sleep(1)
                    if self.client.is_online():
                        print("Agent started successfully")
                        return
                except Exception as e:
                    print(f"Failed to start agent from source: {e}")
        
        print("WARNING: Could not start agent - no valid agent path or embedded module found")
    
    def _start_embedded_agent(self):
        """Start embedded agent server in background thread"""
        def run_agent_server():
            try:
                print("Starting embedded agent server thread...")
                import agent.uds_server # type: ignore
                # Run the agent server main loop
                agent.uds_server.main()
            except Exception as e:
                print(f"Error in embedded agent server: {e}")
        
        # Start agent in daemon thread
        agent_thread = threading.Thread(
            target=run_agent_server,
            daemon=True,
            name="EmbeddedAgentServer"
        )
        agent_thread.start()
        print("Embedded agent server thread started")
        
        # Give it a moment to start
        time.sleep(1)
    
    def _check_agent_status(self):
        """Check agent status and update UI (called by QTimer every 2 seconds)"""
        is_online = self.client.is_online()
        
        if is_online:
            if not self.agent_online:
                # Agent just came online
                self.agent_online = True
                print("Agent is now online")
                # Update UI - this will also trigger _check_thresholds via _update_all_stats
                self.signal.update.emit()
            
            # Reset retries
            self.agent_check_retries = 0
        else:
            if self.agent_online:
                # Agent just went offline
                self.agent_online = False
                print("Agent went offline")
                self.signal.update.emit()
                
            self.agent_check_retries += 1
            
            # Auto-retry logic (exponential-ish backoff)
            # Retries at: 10s (5*2), 30s (15*2), 1m (30*2), 2m (60*2), 5m (150*2)
            retry_points = [5, 15, 30, 60, 150]
            
            should_retry = False
            if self.agent_check_retries in retry_points:
                should_retry = True
            elif self.agent_check_retries > 150 and self.agent_check_retries % 150 == 0:
                # Every 5 minutes after the initial retries
                should_retry = True
                
            if should_retry:
                print(f"Agent offline (retry count: {self.agent_check_retries}). Attempting auto-reconnect...")
                # Start agent in background thread to avoid blocking UI
                threading.Thread(target=self._manage_agent_background, daemon=True).start()

    def create_tray_icon(self):
        """Create the system tray icon"""
        # Platform-specific icon selection
        is_windows = sys.platform == 'win32'
        is_macos = sys.platform == 'darwin'
        
        icon = None
        icon_path = get_icon_path()
        
        if is_windows:
            # Windows: Use AppIcon.ico for tray
            if icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)
        elif is_macos:
            # macOS: Use template icon for menubar (dark/light mode support)
            # Try to find template icon
            template_path = get_resource_path("resources/icon_template@2x.png")
            if not os.path.exists(template_path):
                template_path = get_resource_path("resources/icon_template.png")
            
            if os.path.exists(template_path):
                icon = QIcon(template_path)
                icon.setIsMask(True)
            elif icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)
        else:
            if icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)
        
        # Fallback to blue square if no icon found
        if icon is None or icon.isNull():
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.blue)
            icon = QIcon(pixmap)
        
        # Windows-specific: ensure high-resolution icon if possible
        if is_windows and icon_path and os.path.exists(icon_path):
            # QIcon(path) on Windows already handles multiple sizes in ICO
            pass
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.setToolTip("OpenCode Token Meter")
        
        # Store the icon for notification use (Windows needs this)
        self._notification_icon = icon
        self._icon_path = icon_path
        
        # Create context menu with stats embedded
        self.build_menu()
        
        # Set context menu for tray icon
        self.tray_icon.setContextMenu(self.menu)
        
        # Connect left click to show menu (for Windows compatibility)
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        self.tray_icon.show()
        
        # Mark tray icon as ready for notifications
        self.tray_icon_ready = True
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation (left/right click)"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            # Show menu with proper positioning
            self._show_menu_at_cursor()
    
    def _show_menu_at_cursor(self):
        """Show menu with proper positioning (bottom-left corner at cursor)"""
        cursor_pos = QCursor.pos()
        menu_size = self.menu.sizeHint()
        
        # Get screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Default: show menu with bottom-left corner at cursor
        menu_x = cursor_pos.x()
        menu_y = cursor_pos.y() - menu_size.height()
        
        # Check if menu would go off-screen on the right
        if menu_x + menu_size.width() > screen.right():
            # Show with bottom-right corner at cursor instead
            menu_x = cursor_pos.x() - menu_size.width()
        
        # Check if menu would go off-screen on the top
        if menu_y < screen.top():
            # Show below cursor instead
            menu_y = cursor_pos.y()
        
        self.menu.popup(QPoint(menu_x, menu_y))
    
    def build_menu(self):
        """Build context menu with embedded stats"""
        self.menu = QMenu()
        
        # Status indicator (no emoji)
        self.status_action = QAction("Status: Checking...", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        reconnect_action = QAction("Reconnect Agent", self.menu)
        reconnect_action.triggered.connect(self.reconnect_agent)
        reconnect_action.setVisible(False)
        self.menu.addAction(reconnect_action)
        self.reconnect_action = reconnect_action
        
        self.menu.addSeparator()
        
        # Today section header (bold, gray)
        today_header = QAction("Today", self.menu)
        today_header.setEnabled(False)  # Gray color
        font = QFont()
        font.setBold(True)
        today_header.setFont(font)
        self.menu.addAction(today_header)
        
        # Today stats
        self.today_row1_action, self.today_in_label, self.today_req_label = self._create_two_stat_widget("In:", "--", "Req:", "--")
        self.menu.addAction(self.today_row1_action)
        
        self.today_row2_action, self.today_out_label, self.today_cost_label = self._create_two_stat_widget("Out:", "--", "Cost:", "--")
        self.menu.addAction(self.today_row2_action)
        
        self.today_row3_action, self.today_token_pct_label, self.today_cost_pct_label = self._create_two_stat_widget("Token:", "--", "Cost:", "--")
        self.menu.addAction(self.today_row3_action)
        self.today_row3_action.setVisible(False)
        
        self.menu.addSeparator()
        
        # Month section header
        month_header = QAction("This Month", self.menu)
        month_header.setEnabled(False)
        month_header.setFont(font)
        self.menu.addAction(month_header)
        
        # Month stats
        self.month_row1_action, self.month_in_label, self.month_req_label = self._create_two_stat_widget("In:", "--", "Req:", "--")
        self.menu.addAction(self.month_row1_action)
        
        self.month_row2_action, self.month_out_label, self.month_cost_label = self._create_two_stat_widget("Out:", "--", "Cost:", "--")
        self.menu.addAction(self.month_row2_action)
        
        self.month_row3_action, self.month_token_pct_label, self.month_cost_pct_label = self._create_two_stat_widget("Token:", "--", "Cost:", "--")
        self.menu.addAction(self.month_row3_action)
        self.month_row3_action.setVisible(False)
        
        self.menu.addSeparator()
        
        # Refresh button
        refresh_action = QAction("Refresh Now", self.menu)
        refresh_action.triggered.connect(self.refresh_now)
        self.menu.addAction(refresh_action)
        
        self.menu.addSeparator()
        
        # Window actions
        show_window_action = QAction("Show Main Window", self.menu)
        show_window_action.triggered.connect(self.show_main_window)
        self.menu.addAction(show_window_action)
        
        details_action = QAction("Show Details", self.menu)
        details_action.triggered.connect(self.show_details)
        self.menu.addAction(details_action)
        
        # Export CSV submenu
        export_menu = QMenu("Export CSV", self.menu)
        
        export_session_action = QAction("Current Session", export_menu)
        export_session_action.triggered.connect(lambda: self.export_csv_scope('current_session'))
        export_menu.addAction(export_session_action)
        
        export_today_action = QAction("Today", export_menu)
        export_today_action.triggered.connect(lambda: self.export_csv_scope('today'))
        export_menu.addAction(export_today_action)
        
        export_7days_action = QAction("Last 7 Days", export_menu)
        export_7days_action.triggered.connect(lambda: self.export_csv_scope('7days'))
        export_menu.addAction(export_7days_action)
        
        export_month_action = QAction("This Month", export_menu)
        export_month_action.triggered.connect(lambda: self.export_csv_scope('this_month'))
        export_menu.addAction(export_month_action)
        
        export_menu.addSeparator()
        
        export_custom_action = QAction("Custom Range...", export_menu)
        export_custom_action.triggered.connect(self.export_csv_custom)
        export_menu.addAction(export_custom_action)
        
        self.menu.addMenu(export_menu)
        
        self.menu.addSeparator()
        
        # Settings
        settings_action = QAction("Settings", self.menu)
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)
        
        self.menu.addSeparator()
        
        # Quit
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
    
    def _format_tokens_k(self, num):
        if num is None or num == 0:
            return "0"
        m = num / 1_000_000.0
        if m >= 1.0:
            if m >= 100: return f"{m:,.0f}M"
            elif m >= 10: return f"{m:,.1f}M"
            else: return f"{m:,.2f}M"
        else:
            k = num / 1000.0
            if k >= 100: return f"{k:,.0f}K"
            elif k >= 10: return f"{k:,.1f}K"
            else: return f"{k:,.2f}K"
    
    def _create_two_stat_widget(self, label1, value1_text, label2, value2_text):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 2, 20, 2)
        layout.setSpacing(8)
        
        label1_widget = QLabel(label1)
        label1_widget.setMinimumWidth(40)
        label1_widget.setMaximumWidth(40)
        label1_widget.setStyleSheet("color: #999;")
        
        value1 = QLabel(value1_text)
        value1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value1.setMinimumWidth(80)
        value1.setMaximumWidth(80)
        
        label2_widget = QLabel(label2)
        label2_widget.setMinimumWidth(40)
        label2_widget.setMaximumWidth(40)
        label2_widget.setStyleSheet("color: #999;")
        
        value2 = QLabel(value2_text)
        value2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value2.setMinimumWidth(80)
        value2.setMaximumWidth(80)
        
        layout.addWidget(label1_widget)
        layout.addWidget(value1)
        layout.addWidget(label2_widget)
        layout.addWidget(value2)
        layout.addStretch()
        
        action = QWidgetAction(self.menu)
        action.setDefaultWidget(widget)
        
        return action, value1, value2
    
    def _calculate_cost_by_model(self, scope):
        cached_cost = self.cost_cache.get(scope)
        if cached_cost is not None:
            return cached_cost
        
        model_stats = self.client.get_stats_by_model(scope)
        if not model_stats:
            stats = self.stats_cache.get(scope)
            cost = self.settings.calculate_cost(stats) if stats else 0.0
        else:
            total_cost = 0.0
            for provider_id, models in model_stats.items():
                for model_id, stats in models.items():
                    cost = self.settings.calculate_cost(stats, model_id=model_id, provider_id=provider_id)
                    total_cost += cost
            cost = total_cost
        
        self.cost_cache[scope] = cost
        return cost
    
    def _update_menu_stats(self):
        if not self.agent_online:
            self.status_action.setText("Status: Agent Loading...")
            if self.reconnect_action: self.reconnect_action.setVisible(False)
        elif self.client.is_online():
            self.status_action.setText("Status: Online")
            if self.reconnect_action: self.reconnect_action.setVisible(False)
        else:
            self.status_action.setText("Status: Offline")
            if self.reconnect_action: self.reconnect_action.setVisible(True)
        
        thresholds_enabled = bool(self.settings.get('thresholds.enabled', False))
        
        for scope in ['today', 'month']:
            stats = self.stats_cache.get(scope)
            if stats and self.agent_online:
                input_tok = stats.get('input', 0)
                total_output = stats.get('output', 0) + stats.get('reasoning', 0)
                requests = stats.get('requests', 0)
                cost = self._calculate_cost_by_model(scope)
                
                if scope == 'today':
                    self.today_in_label.setText(self._format_tokens_k(input_tok))
                    self.today_req_label.setText(f"{requests:,}")
                    self.today_out_label.setText(self._format_tokens_k(total_output))
                    self.today_cost_label.setText(f"${cost:.2f}")
                    if thresholds_enabled:
                        self.today_row3_action.setVisible(True)
                        self.today_token_pct_label.setText(f"{self._calculate_percentage(stats, 'daily', 'token')}%")
                        self.today_cost_pct_label.setText(f"{self._calculate_percentage(stats, 'daily', 'cost', cost_value=cost)}%")
                    else:
                        self.today_row3_action.setVisible(False)
                else:
                    self.month_in_label.setText(self._format_tokens_k(input_tok))
                    self.month_req_label.setText(f"{requests:,}")
                    self.month_out_label.setText(self._format_tokens_k(total_output))
                    self.month_cost_label.setText(f"${cost:.2f}")
                    if thresholds_enabled:
                        self.month_row3_action.setVisible(True)
                        self.month_token_pct_label.setText(f"{self._calculate_percentage(stats, 'monthly', 'token')}%")
                        self.month_cost_pct_label.setText(f"{self._calculate_percentage(stats, 'monthly', 'cost', cost_value=cost)}%")
                    else:
                        self.month_row3_action.setVisible(False)
            else:
                target_labels = [self.today_in_label, self.today_req_label, self.today_out_label, self.today_cost_label] if scope == 'today' else [self.month_in_label, self.month_req_label, self.month_out_label, self.month_cost_label]
                for label in target_labels: label.setText("--")
                if scope == 'today': self.today_row3_action.setVisible(False)
                else: self.month_row3_action.setVisible(False)
    
    def _calculate_percentage(self, stats: Optional[Dict[str, Any]], period: str, metric: str, cost_value: Optional[float] = None) -> int:
        if stats is None:
            return 0
        
        if period == 'daily':
            token_threshold = float(cast(float, self.settings.get('thresholds.daily_tokens', 1000000)))
            cost_threshold = float(cast(float, self.settings.get('thresholds.daily_cost', 20.0)))
        else:
            token_threshold = float(cast(float, self.settings.get('thresholds.monthly_tokens', 10000000)))
            cost_threshold = float(cast(float, self.settings.get('thresholds.monthly_cost', 1000.0)))
        
        if metric == 'token':
            value = float(stats.get('input', 0) or 0) + float(stats.get('output', 0) or 0) + float(stats.get('reasoning', 0) or 0)
            threshold = token_threshold
        else:
            value = float(cost_value) if cost_value is not None else 0.0
            threshold = cost_threshold
        
        if threshold > 0:
            return min(int((value / threshold) * 100), 999)
        return 0

    def _show_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information, duration: int = 5000):
        if not self.tray_icon_ready: return
        now = time.time()
        key = (title, message)
        if self._notification_history.get(key) and now - (self._notification_history.get(key) or 0) < self._notification_dedup_seconds: return
        self._notification_history[key] = now
        
        if sys.platform == 'win32' and hasattr(self, '_notification_icon') and self._notification_icon:
            self.tray_icon.showMessage(title, message, self._notification_icon, duration)
        else:
            self.tray_icon.showMessage(title, message, icon_type, duration)
    
    def _update_all_stats(self):
        for scope in ['current_session', 'today', '7days', 'month']:
            self.stats_cache[scope] = self.client.get_stats(scope)
        
        # Reset cost cache
        for scope in self.stats_cache:
            self.cost_cache[scope] = None
            
        self._update_menu_stats()
        if self.main_window: self.main_window.update_display()
        if self.details_dialog: self.details_dialog.refresh()
        self._check_thresholds(is_startup=False)
    
    def _check_thresholds(self, is_startup: bool = False):
        if not self.settings.get('notifications_enabled', True): return
        
        today_stats = self.stats_cache.get('today') or {}
        month_stats = self.stats_cache.get('month') or {}
        
        notifications = []
        
        # Daily
        daily_tokens = int(today_stats.get('input', 0) or 0) + int(today_stats.get('output', 0) or 0) + int(today_stats.get('reasoning', 0) or 0)
        daily_token_thresh = int(cast(int, self.settings.get('thresholds.daily_tokens', 50000000)))
        daily_tokens_exceeded = bool(daily_tokens > daily_token_thresh)
        
        daily_cost = self._calculate_cost_by_model('today')
        daily_cost_thresh = float(cast(float, self.settings.get('thresholds.daily_cost', 20.0)))
        daily_cost_exceeded = bool(daily_cost > daily_cost_thresh)
        
        if daily_tokens_exceeded and (is_startup or not self.last_threshold_state['daily_tokens']):
            notifications.append(f"Daily Token Threshold Exceeded: {daily_tokens:,}")
        if daily_cost_exceeded and (is_startup or not self.last_threshold_state['daily_cost']):
            notifications.append(f"Daily Cost Threshold Exceeded: ${daily_cost:.2f}")
        
        self.last_threshold_state['daily_tokens'] = daily_tokens_exceeded
        self.last_threshold_state['daily_cost'] = daily_cost_exceeded
        
        # Monthly
        if month_stats:
            monthly_tokens = int(month_stats.get('input', 0) or 0) + int(month_stats.get('output', 0) or 0) + int(month_stats.get('reasoning', 0) or 0)
            monthly_token_thresh = int(cast(int, self.settings.get('thresholds.monthly_tokens', 10000000)))
            monthly_tokens_exceeded = bool(monthly_tokens > monthly_token_thresh)
            
            monthly_cost = self._calculate_cost_by_model('month')
            monthly_cost_thresh = float(cast(float, self.settings.get('thresholds.monthly_cost', 1000.0)))
            monthly_cost_exceeded = bool(monthly_cost > monthly_cost_thresh)
            
            if monthly_tokens_exceeded and (is_startup or not self.last_threshold_state['monthly_tokens']):
                notifications.append(f"Monthly Token Threshold Exceeded: {monthly_tokens:,}")
            if monthly_cost_exceeded and (is_startup or not self.last_threshold_state['monthly_cost']):
                notifications.append(f"Monthly Cost Threshold Exceeded: ${monthly_cost:.2f}")
            
            self.last_threshold_state['monthly_tokens'] = monthly_tokens_exceeded
            self.last_threshold_state['monthly_cost'] = monthly_cost_exceeded

        if notifications:
            self._show_notification("OpenCode Token Meter", "\n".join(notifications), QSystemTrayIcon.MessageIcon.Warning)
    
    def _auto_refresh_loop(self):
        while self.auto_refresh_enabled:
            interval = self.settings.get('refresh_interval', 300)
            try:
                sleep_time = max(10, int(cast(int, interval)))
            except (ValueError, TypeError):
                sleep_time = 300
            time.sleep(sleep_time)
            self.signal.update.emit()
    
    def refresh_now(self):
        self._show_notification("OpenCode Token Meter", "Refreshing...\nTriggering agent scan")
        if self.client.refresh():
            time.sleep(1)
            self._update_all_stats()
            self._show_notification("OpenCode Token Meter", "Refresh Complete")
        else:
            self._show_notification("OpenCode Token Meter", "Refresh Failed", QSystemTrayIcon.MessageIcon.Critical)
    
    def reconnect_agent(self):
        """Manually trigger agent restart/reconnect"""
        self._show_notification("OpenCode Token Meter", "Attempting to reconnect agent...")
        
        # Reset retries and start timer
        self.agent_check_retries = 0
        if hasattr(self, 'agent_check_timer') and self.agent_check_timer:
            self.agent_check_timer.start(2000)
        else:
            self.agent_check_timer = QTimer()
            self.agent_check_timer.timeout.connect(self._check_agent_status)
            self.agent_check_timer.start(2000)
            
        # Try starting agent again
        agent_thread = threading.Thread(target=self._manage_agent_background, daemon=True)
        agent_thread.start()
    
    def _open_file_location(self, filepath):
        system = platform.system()
        try:
            if system == 'Darwin': os.system(f'open -R "{filepath}"')
            elif system == 'Windows': subprocess.Popen(['explorer', '/select,', os.path.normpath(filepath)])
            else: subprocess.Popen(['xdg-open', os.path.dirname(filepath)])
        except: pass
    
    def export_csv_scope(self, scope='this_month'):
        scope_names = {'current_session': 'session', 'today': 'today', '7days': '7days', 'this_month': 'month'}
        scope_name = scope_names.get(scope, 'export')
        default_dir = os.path.join(os.path.expanduser("~"), "Desktop") if platform.system() == 'Windows' else os.path.expanduser("~/Desktop")
        filename, _ = QFileDialog.getSaveFileName(None, "Export to CSV", os.path.join(default_dir, f"opencode_tokens_{scope_name}_{int(time.time())}.csv"), "CSV Files (*.csv)")
        if not filename: return
        filename = os.path.normpath(filename)
        result = self.client.export_csv(filename, scope=scope)
        if result:
            self._show_notification("OpenCode Token Meter", f"Export Complete\nSaved to {os.path.basename(result)}")
            self._open_file_location(result)
        else:
            self._show_notification("OpenCode Token Meter", "Export Failed", QSystemTrayIcon.MessageIcon.Critical)
    
    def export_csv_custom(self):
        if self.custom_range_dialog and self.custom_range_dialog.isVisible():
            self.custom_range_dialog.raise_()
            self.custom_range_dialog.activateWindow()
            return
        self.custom_range_dialog = CustomRangeDialog(self)
        self.custom_range_dialog.accepted.connect(self._on_custom_range_accepted)
        self.custom_range_dialog.show()
    
    def _on_custom_range_accepted(self):
        if not self.custom_range_dialog:
            return
        try:
            start_ts, end_ts = self.custom_range_dialog.get_timestamps()
            default_dir = os.path.join(os.path.expanduser("~"), "Desktop") if platform.system() == 'Windows' else os.path.expanduser("~/Desktop")
            filename, _ = QFileDialog.getSaveFileName(None, "Export to CSV", os.path.join(default_dir, f"opencode_tokens_custom_{int(time.time())}.csv"), "CSV Files (*.csv)")
            if not filename: return
            filename = os.path.normpath(filename)
            result = self.client.export_csv_range(filename, start_ts, end_ts)
            if result:
                stats = self.client.get_stats_range(start_ts, end_ts)
                self._show_notification("OpenCode Token Meter", f"Export Complete")
                if stats:
                    if self.custom_stats_dialog: self.custom_stats_dialog.close()
                    self.custom_stats_dialog = CustomRangeStatsDialog(stats, self.settings, self.client, start_ts, end_ts, self)
                    self.custom_stats_dialog.show()
                QTimer.singleShot(1000, lambda: self._open_file_location(result))
            else:
                self._show_notification("OpenCode Token Meter", "Export Failed", QSystemTrayIcon.MessageIcon.Critical)
        except Exception as e:
            QMessageBox.critical(None, "Export Error", str(e))
    
    def show_details(self):
        if self.details_dialog and self.details_dialog.isVisible():
            self.details_dialog.raise_()
            self.details_dialog.activateWindow()
            return
        self.details_dialog = DetailsDialog(self.stats_cache, self.settings, self)
        self.details_dialog.show()
    
    def show_main_window(self):
        if self.main_window is None:
            self.main_window = MainStatsWindow(self)
        self._update_all_stats()
        self.main_window.update_display()
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
    
    def show_settings(self):
        if self.settings_dialog and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        self.settings_dialog = SettingsDialog(self.settings, self)
        self.settings_dialog.settings_saved.connect(self._update_all_stats)
        self.settings_dialog.show()
    
    def quit_app(self):
        self.auto_refresh_enabled = False
        self._close_all_windows()
        try: self.client.shutdown()
        except: pass
        QApplication.quit()
    
    def _close_all_windows(self):
        for window in [self.main_window, self.details_dialog, self.settings_dialog, self.custom_range_dialog, self.custom_stats_dialog, self.model_update_dialog]:
            if window:
                try: window.close()
                except: pass
