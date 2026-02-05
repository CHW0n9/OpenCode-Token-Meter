"""
OpenCode Token Meter - PyQt6 Menubar Application
"""
import os
import sys
import threading
import time
import subprocess
import json
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QDialog, 
                              QVBoxLayout, QTableWidget, QTableWidgetItem, 
                              QPushButton, QLabel, QMessageBox, QWidget,
                              QFormLayout, QLineEdit, QComboBox, QCheckBox,
                              QHBoxLayout, QFileDialog, QWidgetAction, QDateTimeEdit,
                              QTabWidget)
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, Qt, QDateTime
from PyQt6.QtGui import QIcon, QPixmap, QAction, QFont

from menubar.uds_client import AgentClient
from menubar.settings import Settings

# Path for tracking last agent start time to prevent infinite loops
LAST_START_FILE = os.path.join(
    os.path.expanduser("~"),
    "Library/Application Support/OpenCode Token Meter/last_agent_start.json"
)


class StatsUpdateSignal(QObject):
    """Signal emitter for stats updates"""
    update = pyqtSignal()


class OpenCodeTokenMeter:
    """Main application with system tray icon"""
    
    def __init__(self):
        self.client = AgentClient()
        self.settings = Settings()
        
        # Track threshold notification state to prevent spam
        self.last_threshold_state = {
            'daily_tokens': False,
            'daily_cost': False,
            'monthly_tokens': False,
            'monthly_cost': False
        }
        
        # Track agent loading state
        self.agent_online = False
        
        # Cache for stats
        self.stats_cache = {
            'current_session': None,
            'today': None,
            '7days': None,
            'month': None
        }
        
        # Cache for model-specific cost calculations
        self.cost_cache = {
            'current_session': None,
            'today': None,
            '7days': None,
            'month': None
        }
        
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
        agent_thread = threading.Thread(target=self._manage_agent_background, daemon=True)
        agent_thread.start()
        
        # Start agent status check timer (check every 2 seconds)
        self.agent_check_retries = 0
        self.agent_check_timer = QTimer()
        self.agent_check_timer.timeout.connect(self._check_agent_status)
        self.agent_check_timer.start(2000)  # 2 seconds
    
    def _manage_agent_background(self):
        """Start agent in background thread (non-blocking)"""
        self._manage_agent()
        # Don't wait for agent to come online - let the timer handle it
        print("Agent started in background, status check timer running")
    
    def _manage_agent(self):
        """
        Manage agent process with infinite loop protection:
        - If agent is running: shutdown and restart
        - If agent is not running: start it
        - Prevent starting too frequently (min 10 seconds between starts)
        - Use lockfile mechanism
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
        
        # Check if agent is online
        if self.client.is_online():
            print("Agent is online, restarting...")
            # Shutdown existing agent
            self.client.shutdown()
            time.sleep(2)  # Wait for shutdown
        
        # Find agent executable
        print(f"DEBUG: sys.executable = {sys.executable}")
        print(f"DEBUG: __file__ = {__file__}")
        
        agent_paths = [
            # When bundled
            os.path.join(os.path.dirname(sys.executable), "..", "Resources", "bin", "opencode-agent"),
            # When running from source
            os.path.join(os.path.dirname(__file__), "..", "..", "agent"),
            # When installed
            "/Applications/OpenCode Token Meter.app/Contents/Resources/bin/opencode-agent",
            # Development path
            os.path.expanduser("~/Desktop/OpenCode Token Meter/App/agent"),
        ]
        
        print(f"DEBUG: Searching for agent in these paths:")
        for i, path in enumerate(agent_paths):
            exists = os.path.exists(path)
            is_file = os.path.isfile(path) if exists else False
            print(f"  [{i}] {path}")
            print(f"      exists={exists}, is_file={is_file}")
        
        for agent_path in agent_paths:
            # Check if it's a bundled executable
            if os.path.exists(agent_path) and os.path.isfile(agent_path):
                try:
                    print(f"Starting agent from: {agent_path}")
                    # Don't suppress output for debugging
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
                    time.sleep(3)  # Give agent time to do quick scan
                    
                    # Check if process is still running
                    if proc.poll() is None:
                        print("Agent process is still running")
                    else:
                        stdout, stderr = proc.communicate()
                        print(f"Agent process exited with code {proc.returncode}")
                        print(f"STDOUT: {stdout.decode()}")
                        print(f"STDERR: {stderr.decode()}")
                    
                    if self.client.is_online():
                        print("Agent started successfully and is online")
                        return
                    else:
                        print("Agent process started but not responding to client yet")
                        print("Will retry connection in background...")
                        # Don't continue trying other paths since we already started an agent
                        return
                except Exception as e:
                    print(f"Failed to start agent: {e}")
                    import traceback
                    traceback.print_exc()
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
                    # Wait for agent to initialize
                    time.sleep(1)
                    if self.client.is_online():
                        print("Agent started successfully")
                        return
                except Exception as e:
                    print(f"Failed to start agent: {e}")
        
        print("WARNING: Could not start agent - no valid agent path found")
    
    def _check_agent_status(self):
        """Check agent status and update UI (called by QTimer every 2 seconds)"""
        if self.client.is_online():
            if not self.agent_online:
                # Agent just came online
                self.agent_online = True
                print("Agent is now online")
                # Update UI
                self.signal.update.emit()
                # Check thresholds on startup
                self._check_thresholds(is_startup=True)
                # Stop checking after agent is online (refresh loop will keep it updated)
                self.agent_check_timer.stop()
                self.agent_check_timer.deleteLater()
        else:
            self.agent_check_retries += 1
            if self.agent_check_retries >= 15:  # 15 * 2 = 30 seconds max wait
                # Give up waiting, update UI to show offline
                print(f"Agent still offline after {self.agent_check_retries * 2} seconds")
                self.signal.update.emit()
                self.agent_check_timer.stop()
                self.agent_check_timer.deleteLater()

    def create_tray_icon(self):
        """Create the system tray icon"""
        # Load template icon for dark/light mode support
        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            icon = QIcon(icon_path)
            # Mark as template to support macOS dark/light mode
            icon.setIsMask(True)
            self.tray_icon = QSystemTrayIcon(icon)
        else:
            # Create a simple colored square as fallback
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.blue)
            self.tray_icon = QSystemTrayIcon(QIcon(pixmap))
        
        # Main window reference (will be created on first click)
        self.main_window = None
        
        # Create context menu with stats embedded
        self.build_menu()
        
        self.tray_icon.show()
    
    def build_menu(self):
        """Build context menu with embedded stats"""
        self.menu = QMenu()
        
        # Status indicator (no emoji)
        self.status_action = QAction("Status: Checking...", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        
        # Today section header (bold, gray)
        today_header = QAction("Today", self.menu)
        today_header.setEnabled(False)  # Gray color
        font = QFont()
        font.setBold(True)
        today_header.setFont(font)
        self.menu.addAction(today_header)
        
        # Today stats - two fields per row (3 rows)
        # Row 1: In, Req
        self.today_row1_action, self.today_in_label, self.today_req_label = self._create_two_stat_widget("In:", "--", "Req:", "--")
        self.menu.addAction(self.today_row1_action)
        
        # Row 2: Out, Cost ($)
        self.today_row2_action, self.today_out_label, self.today_cost_label = self._create_two_stat_widget("Out:", "--", "Cost:", "--")
        self.menu.addAction(self.today_row2_action)
        
        # Row 3: Token %, Cost % (no progress bar graphics, just percentage)
        self.today_row3_action, self.today_token_pct_label, self.today_cost_pct_label = self._create_two_stat_widget("Token:", "--", "Cost:", "--")
        self.menu.addAction(self.today_row3_action)
        self.today_row3_action.setVisible(False)  # Hidden by default (shown when thresholds enabled)
        
        self.menu.addSeparator()
        
        # Month section header (bold, gray)
        month_header = QAction("This Month", self.menu)
        month_header.setEnabled(False)  # Gray color
        month_header.setFont(font)
        self.menu.addAction(month_header)
        
        # Month stats - two fields per row (3 rows)
        # Row 1: In, Req
        self.month_row1_action, self.month_in_label, self.month_req_label = self._create_two_stat_widget("In:", "--", "Req:", "--")
        self.menu.addAction(self.month_row1_action)
        
        # Row 2: Out, Cost ($)
        self.month_row2_action, self.month_out_label, self.month_cost_label = self._create_two_stat_widget("Out:", "--", "Cost:", "--")
        self.menu.addAction(self.month_row2_action)
        
        # Row 3: Token %, Cost % (no progress bar graphics, just percentage)
        self.month_row3_action, self.month_token_pct_label, self.month_cost_pct_label = self._create_two_stat_widget("Token:", "--", "Cost:", "--")
        self.menu.addAction(self.month_row3_action)
        self.month_row3_action.setVisible(False)  # Hidden by default (shown when thresholds enabled)
        
        self.menu.addSeparator()
        
        # Refresh button (separate group)
        refresh_action = QAction("Refresh Now", self.menu)
        refresh_action.triggered.connect(self.refresh_now)
        self.menu.addAction(refresh_action)
        
        self.menu.addSeparator()
        
        # Window actions group
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
        
        # Settings (separate group)
        settings_action = QAction("Settings", self.menu)
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)
        
        self.menu.addSeparator()
        
        # Quit (separate group)
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
    
    def _format_tokens_k(self, num):
        """
        Format token number in K/M units with adaptive display.
        < 1M: display as K (e.g., 123.5K)
        >= 1M: display as M (e.g., 1.23M)
        """
        if num is None or num == 0:
            return "0"
        
        # Convert to millions first
        m = num / 1_000_000.0
        
        if m >= 1.0:
            # Display as M
            if m >= 100:
                return f"{m:,.0f}M"
            elif m >= 10:
                return f"{m:,.1f}M"
            else:
                return f"{m:,.2f}M"
        else:
            # Display as K
            k = num / 1000.0
            if k >= 100:
                return f"{k:,.0f}K"
            elif k >= 10:
                return f"{k:,.1f}K"
            else:
                return f"{k:,.2f}K"
    
    def _create_two_stat_widget(self, label1, value1_text, label2, value2_text):
        """
        Create a widget action with two fields per row.
        Layout: Label1 | Value1 | Label2 | Value2
        Returns tuple of (QWidgetAction, value1_label, value2_label)
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 2, 20, 2)
        layout.setSpacing(8)
        
        # First field - label gray, value normal
        label1_widget = QLabel(label1)
        label1_widget.setMinimumWidth(40)
        label1_widget.setMaximumWidth(40)
        label1_widget.setStyleSheet("color: #999;")  # Gray for labels
        
        value1 = QLabel(value1_text)
        value1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value1.setMinimumWidth(80)
        value1.setMaximumWidth(80)
        # Value uses normal color (no gray)
        
        # Second field - label gray, value normal
        label2_widget = QLabel(label2)
        label2_widget.setMinimumWidth(40)
        label2_widget.setMaximumWidth(40)
        label2_widget.setStyleSheet("color: #999;")  # Gray for labels
        
        value2 = QLabel(value2_text)
        value2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value2.setMinimumWidth(80)
        value2.setMaximumWidth(80)
        # Value uses normal color (no gray)
        
        layout.addWidget(label1_widget)
        layout.addWidget(value1)
        layout.addWidget(label2_widget)
        layout.addWidget(value2)
        layout.addStretch()
        
        action = QWidgetAction(self.menu)
        action.setDefaultWidget(widget)
        
        return action, value1, value2
    
    def _calculate_cost_by_model(self, scope):
        """
        Calculate cost using model-specific pricing by aggregating cost from each model.
        scope: 'today', 'month', '7days', 'current_session'
        Returns total cost (float)
        """
        # Check cache first
        cached_cost = self.cost_cache.get(scope)
        if cached_cost is not None:
            return cached_cost
        
        # Not cached, calculate from model stats
        model_stats = self.client.get_stats_by_model(scope)
        if not model_stats:
            # Fallback to default pricing if model stats not available
            stats = self.stats_cache.get(scope)
            cost = self.settings.calculate_cost(stats) if stats else 0.0
        else:
            total_cost = 0.0
            for provider_id, models in model_stats.items():
                for model_id, stats in models.items():
                    cost = self.settings.calculate_cost(
                        stats, 
                        model_id=model_id, 
                        provider_id=provider_id
                    )
                    total_cost += cost
            cost = total_cost
        
        # Cache the result
        self.cost_cache[scope] = cost
        return cost
    
    def _update_menu_stats(self):
        """Update menu items with current stats in separate sections"""
        # Update status (no emoji)
        if not self.agent_online:
            self.status_action.setText("Status: Agent Loading...")
        elif self.client.is_online():
            self.status_action.setText("Status: Online")
        else:
            self.status_action.setText("Status: Offline")
        
        # Check if thresholds are enabled
        thresholds_enabled = self.settings.get('thresholds.enabled', False)
        
        # Update today stats
        today_stats = self.stats_cache.get('today')
        if today_stats and self.agent_online:
            input_tok = today_stats.get('input', 0)
            output_tok = today_stats.get('output', 0)
            reasoning_tok = today_stats.get('reasoning', 0)
            total_output = output_tok + reasoning_tok
            total_tokens = input_tok + total_output
            requests = today_stats.get('requests', 0)
            
            # Calculate cost using model-specific pricing
            cost = self._calculate_cost_by_model('today')
            
            # Row 1: In, Req
            self.today_in_label.setText(self._format_tokens_k(input_tok))
            self.today_req_label.setText(f"{requests:,}")
            
            # Row 2: Out, Cost ($)
            self.today_out_label.setText(self._format_tokens_k(total_output))
            self.today_cost_label.setText(f"${cost:.2f}")
            
            # Row 3: Token %, Cost % (only show if thresholds enabled)
            if thresholds_enabled:
                self.today_row3_action.setVisible(True)
                token_pct = self._calculate_percentage(today_stats, 'daily', 'token')
                cost_pct = self._calculate_percentage(today_stats, 'daily', 'cost', cost_value=cost)
                self.today_token_pct_label.setText(f"{token_pct}%")
                self.today_cost_pct_label.setText(f"{cost_pct}%")
            else:
                self.today_row3_action.setVisible(False)
        else:
            self.today_in_label.setText("--")
            self.today_req_label.setText("--")
            self.today_out_label.setText("--")
            self.today_cost_label.setText("--")
            self.today_row3_action.setVisible(False)
        
        # Update month stats
        month_stats = self.stats_cache.get('month')
        if month_stats and self.agent_online:
            input_tok = month_stats.get('input', 0)
            output_tok = month_stats.get('output', 0)
            reasoning_tok = month_stats.get('reasoning', 0)
            total_output = output_tok + reasoning_tok
            total_tokens = input_tok + total_output
            requests = month_stats.get('requests', 0)
            
            # Calculate cost using model-specific pricing
            cost = self._calculate_cost_by_model('month')
            
            # Row 1: In, Req
            self.month_in_label.setText(self._format_tokens_k(input_tok))
            self.month_req_label.setText(f"{requests:,}")
            
            # Row 2: Out, Cost ($)
            self.month_out_label.setText(self._format_tokens_k(total_output))
            self.month_cost_label.setText(f"${cost:.2f}")
            
            # Row 3: Token %, Cost % (only show if thresholds enabled)
            if thresholds_enabled:
                self.month_row3_action.setVisible(True)
                token_pct = self._calculate_percentage(month_stats, 'monthly', 'token')
                cost_pct = self._calculate_percentage(month_stats, 'monthly', 'cost', cost_value=cost)
                self.month_token_pct_label.setText(f"{token_pct}%")
                self.month_cost_pct_label.setText(f"{cost_pct}%")
            else:
                self.month_row3_action.setVisible(False)
        else:
            self.month_in_label.setText("--")
            self.month_req_label.setText("--")
            self.month_out_label.setText("--")
            self.month_cost_label.setText("--")
            self.month_row3_action.setVisible(False)
    
    def _calculate_percentage(self, stats, period, metric, cost_value=None):
        """
        Calculate percentage for token or cost (without progress bar).
        period: 'daily' or 'monthly'
        metric: 'token' or 'cost'
        cost_value: pre-calculated model-specific cost (required when metric='cost')
        Returns percentage as integer (e.g., 65 for 65%)
        """
        if period == 'daily':
            token_threshold = self.settings.get('thresholds.daily_tokens', 1000000)
            cost_threshold = self.settings.get('thresholds.daily_cost', 20.0)
        else:  # monthly
            token_threshold = self.settings.get('thresholds.monthly_tokens', 10000000)
            cost_threshold = self.settings.get('thresholds.monthly_cost', 1000.0)
        
        if metric == 'token':
            # Calculate total tokens
            total_tokens = (
                stats.get('input', 0) +
                stats.get('output', 0) +
                stats.get('reasoning', 0)
            )
            threshold = token_threshold
            value = total_tokens
        else:  # cost
            value = cost_value if cost_value is not None else 0.0
            threshold = cost_threshold
        
        # Calculate percentage
        pct = min(int((value / threshold) * 100), 999) if threshold > 0 else 0
        return pct
    
    def get_icon_path(self):
        """Get path to template icon file for menubar"""
        if getattr(sys, 'frozen', False):
            # Frozen bundle
            bundled_resources = os.path.abspath(
                os.path.join(os.path.dirname(sys.executable), "..", "Resources")
            )
            # Try template icon first (for menubar dark/light mode)
            template_path = os.path.join(bundled_resources, "resources", "icon_template@2x.png")
            if os.path.exists(template_path):
                return template_path
            template_path = os.path.join(bundled_resources, "resources", "icon_template.png")
            if os.path.exists(template_path):
                return template_path
        else:
            # Development
            dev_template = os.path.join(
                os.path.dirname(__file__), "..", "resources", "icon_template@2x.png"
            )
            if os.path.exists(dev_template):
                return dev_template
            dev_template = os.path.join(
                os.path.dirname(__file__), "..", "resources", "icon_template.png"
            )
            if os.path.exists(dev_template):
                return dev_template
        return None
    
    def _format_tokens(self, num):
        """Format token number with commas"""
        if num is None:
            return "N/A"
        return f"{num:,}"
    
    def _format_cost(self, cost):
        """Format cost in dollars"""
        if cost is None:
            return "N/A"
        return f"${cost:.2f}"
    
    def _update_all_stats(self):
        """Update all statistics from agent"""
        # Fetch stats for each scope
        self.stats_cache['current_session'] = self.client.get_stats('current_session')
        self.stats_cache['today'] = self.client.get_stats('today')
        self.stats_cache['7days'] = self.client.get_stats('7days')
        self.stats_cache['month'] = self.client.get_stats('month')
        
        # Clear cost cache when stats are updated
        self.cost_cache = {
            'current_session': None,
            'today': None,
            '7days': None,
            'month': None
        }
        
        # Update menu stats
        self._update_menu_stats()
        
        # Update main window if it exists
        if self.main_window:
            self.main_window.update_display()
        
        # Check thresholds (not on startup, only on refresh)
        self._check_thresholds(is_startup=False)
    
    def _check_thresholds(self, is_startup=False):
        """
        Check if any thresholds are exceeded and notify.
        Only notifies on:
        1. Startup if already exceeded
        2. State change from not-exceeded to exceeded
        """
        if not self.settings.get('thresholds.enabled'):
            return
        
        today_stats = self.stats_cache.get('today')
        month_stats = self.stats_cache.get('month')
        
        if not today_stats:
            return
        
        # Check daily token threshold
        daily_threshold = self.settings.get('thresholds.daily_tokens', 1000000)
        total_tokens = (
            today_stats.get('input', 0) +
            today_stats.get('output', 0) +
            today_stats.get('reasoning', 0)
        )
        
        daily_tokens_exceeded = total_tokens > daily_threshold
        if daily_tokens_exceeded and (is_startup or not self.last_threshold_state['daily_tokens']):
            self.tray_icon.showMessage(
                "OpenCode Token Meter",
                f"Daily Token Threshold Exceeded\nUsed {self._format_tokens(total_tokens)} tokens today",
                QSystemTrayIcon.MessageIcon.Warning
            )
        self.last_threshold_state['daily_tokens'] = daily_tokens_exceeded
        
        # Check daily cost threshold
        cost_threshold = self.settings.get('thresholds.daily_cost', 20.0)
        daily_cost = self.settings.calculate_cost(today_stats)
        
        daily_cost_exceeded = daily_cost > cost_threshold
        if daily_cost_exceeded and (is_startup or not self.last_threshold_state['daily_cost']):
            self.tray_icon.showMessage(
                "OpenCode Token Meter",
                f"Daily Cost Threshold Exceeded\nSpent {self._format_cost(daily_cost)} today",
                QSystemTrayIcon.MessageIcon.Warning
            )
        self.last_threshold_state['daily_cost'] = daily_cost_exceeded
        
        # Check monthly thresholds
        if month_stats:
            monthly_token_threshold = self.settings.get('thresholds.monthly_tokens', 10000000)
            monthly_total_tokens = (
                month_stats.get('input', 0) +
                month_stats.get('output', 0) +
                month_stats.get('reasoning', 0)
            )
            
            monthly_tokens_exceeded = monthly_total_tokens > monthly_token_threshold
            if monthly_tokens_exceeded and (is_startup or not self.last_threshold_state['monthly_tokens']):
                self.tray_icon.showMessage(
                    "OpenCode Token Meter",
                    f"Monthly Token Threshold Exceeded\nUsed {self._format_tokens(monthly_total_tokens)} tokens this month",
                    QSystemTrayIcon.MessageIcon.Warning
                )
            self.last_threshold_state['monthly_tokens'] = monthly_tokens_exceeded
            
            # Check monthly cost threshold
            monthly_cost_threshold = self.settings.get('thresholds.monthly_cost', 1000.0)
            monthly_cost = self.settings.calculate_cost(month_stats)
            
            monthly_cost_exceeded = monthly_cost > monthly_cost_threshold
            if monthly_cost_exceeded and (is_startup or not self.last_threshold_state['monthly_cost']):
                self.tray_icon.showMessage(
                    "OpenCode Token Meter",
                    f"Monthly Cost Threshold Exceeded\nSpent {self._format_cost(monthly_cost)} this month",
                    QSystemTrayIcon.MessageIcon.Warning
                )
            self.last_threshold_state['monthly_cost'] = monthly_cost_exceeded
    
    def _auto_refresh_loop(self):
        """Background thread for auto-refresh"""
        while self.auto_refresh_enabled:
            interval = self.settings.get('refresh_interval', 300)
            time.sleep(max(10, int(interval)))
            # Use signal to update from main thread
            self.signal.update.emit()
    
    def refresh_now(self):
        """Manually refresh stats"""
        self.tray_icon.showMessage(
            "OpenCode Token Meter",
            "Refreshing...\nTriggering agent scan",
            QSystemTrayIcon.MessageIcon.Information
        )
        
        success = self.client.refresh()
        
        if success:
            time.sleep(1)
            self._update_all_stats()
            self.tray_icon.showMessage(
                "OpenCode Token Meter",
                "Refresh Complete\nStatistics updated",
                QSystemTrayIcon.MessageIcon.Information
            )
        else:
            self.tray_icon.showMessage(
                "OpenCode Token Meter",
                "Refresh Failed\nCould not connect to agent",
                QSystemTrayIcon.MessageIcon.Critical
            )
    
    def export_csv_scope(self, scope='this_month'):
        """Export data to CSV for a specific scope"""
        scope_names = {
            'current_session': 'session',
            'today': 'today',
            '7days': '7days',
            'this_month': 'month'
        }
        scope_name = scope_names.get(scope, 'export')
        
        filename, _ = QFileDialog.getSaveFileName(
            None,
            "Export to CSV",
            os.path.join(os.path.expanduser("~"), "Desktop", 
                        f"opencode_tokens_{scope_name}_{int(time.time())}.csv"),
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        result = self.client.export_csv(filename, scope=scope)
        
        if result:
            self.tray_icon.showMessage(
                "OpenCode Token Meter",
                f"Export Complete\nSaved to {os.path.basename(result)}",
                QSystemTrayIcon.MessageIcon.Information
            )
            # Open in Finder (macOS)
            os.system(f'open -R "{result}"')
        else:
            self.tray_icon.showMessage(
                "OpenCode Token Meter",
                "Export Failed\nCould not export data",
                QSystemTrayIcon.MessageIcon.Critical
            )
    
    def export_csv_custom(self):
        """Export data for custom date range with stats dialog"""
        dialog = CustomRangeDialog(None)
        if dialog.exec():
            start_ts, end_ts = dialog.get_timestamps()
            
            # Get filename
            filename, _ = QFileDialog.getSaveFileName(
                None,
                "Export to CSV",
                os.path.join(os.path.expanduser("~"), "Desktop", 
                            f"opencode_tokens_custom_{int(time.time())}.csv"),
                "CSV Files (*.csv)"
            )
            
            if not filename:
                return
            
            # Export via agent
            result = self.client.export_csv_range(filename, start_ts, end_ts)
            
            if result:
                # Get stats for this range
                stats = self.client.get_stats_range(start_ts, end_ts)
                
                # Show success and stats
                self.tray_icon.showMessage(
                    "OpenCode Token Meter",
                    f"Export Complete\nSaved to {os.path.basename(result)}",
                    QSystemTrayIcon.MessageIcon.Information
                )
                
                # Show detailed stats dialog
                if stats:
                    stats_dialog = CustomRangeStatsDialog(stats, self.settings, self.client, start_ts, end_ts)
                    stats_dialog.exec()
                
                # Open in Finder (macOS)
                os.system(f'open -R "{result}"')
            else:
                self.tray_icon.showMessage(
                    "OpenCode Token Meter",
                    "Export Failed\nCould not export data",
                    QSystemTrayIcon.MessageIcon.Critical
                )
    
    def show_details(self):
        """Show detailed stats table for all time scopes"""
        dialog = DetailsDialog(self.stats_cache, self.settings, self)
        dialog.exec()
    
    def show_main_window(self):
        """Show or create the main stats window"""
        if self.main_window is None:
            self.main_window = MainStatsWindow(self)
        
        # Update stats before showing
        self._update_all_stats()
        self.main_window.update_display()
        
        # Show and bring to front
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            # Settings were saved, refresh stats
            self._update_all_stats()
    
    def quit_app(self):
        """Quit the application"""
        self.auto_refresh_enabled = False
        
        # Always shutdown agent on quit
        self.client.shutdown()
        
        QApplication.quit()


class MainStatsWindow(QWidget):
    """Main window showing stats table (shown when clicking tray icon)"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        
        self.setWindowTitle("OpenCode Token Meter")
        self.setMinimumWidth(700)
        self.setMinimumHeight(250)
        
        # Set window flags to keep it always on top but not a popup
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        layout = QVBoxLayout()
        
        # Title and status
        header_layout = QHBoxLayout()
        title = QLabel("OpenCode Token Meter")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        self.status_label = QLabel()
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)
        
        # Table (without Actions column)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Scope", "Input", "Output+Reasoning", "Requests", "Cost"
        ])
        self.table.setRowCount(4)
        
        # Make table read-only
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        layout.addWidget(self.table)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.on_refresh)
        button_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(lambda: self.app_instance.export_csv_scope('this_month'))
        button_layout.addWidget(export_btn)
        
        details_btn = QPushButton("Show Details")
        details_btn.clicked.connect(self.app_instance.show_details)
        button_layout.addWidget(details_btn)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.app_instance.show_settings)
        button_layout.addWidget(settings_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_refresh(self):
        """Handle refresh button"""
        self.app_instance.refresh_now()
    
    def update_display(self):
        """Update the display with current stats"""
        # Update status
        if self.app_instance.client.is_online():
            self.status_label.setText("✅ Agent Online")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("⚠️  Agent Offline")
            self.status_label.setStyleSheet("color: red;")
        
        # Update table with right-aligned columns
        scopes = [
            ('current_session', 'Current Session'),
            ('today', 'Today'),
            ('7days', 'Last 7 Days'),
            ('month', 'This Month')
        ]
        
        for i, (scope_key, scope_name) in enumerate(scopes):
            stats = self.app_instance.stats_cache.get(scope_key)
            
            # Scope column (left aligned)
            scope_item = QTableWidgetItem(scope_name)
            self.table.setItem(i, 0, scope_item)
            
            if not stats:
                for col in range(1, 5):
                    item = QTableWidgetItem("N/A")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(i, col, item)
                continue
            
            input_tok = stats.get('input', 0)
            output_tok = stats.get('output', 0)
            reasoning_tok = stats.get('reasoning', 0)
            requests = stats.get('requests', 0)
            total_output = output_tok + reasoning_tok
            cost = self.app_instance._calculate_cost_by_model(scope_key)
            
            # All numeric columns right-aligned
            input_item = QTableWidgetItem(f"{input_tok:,}")
            input_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, input_item)
            
            output_item = QTableWidgetItem(f"{total_output:,}")
            output_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 2, output_item)
            
            req_item = QTableWidgetItem(f"{requests:,}")
            req_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 3, req_item)
            
            cost_item = QTableWidgetItem(f"${cost:.2f}")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 4, cost_item)
        
        self.table.resizeColumnsToContents()


class DetailsDialog(QDialog):
    """Dialog showing detailed statistics table"""
    
    def __init__(self, stats_cache, settings, app_instance=None):
        super().__init__()
        self.stats_cache = stats_cache
        self.settings = settings
        self.app_instance = app_instance
        self.current_view = 'all'
        
        self.setWindowTitle("OpenCode Token Meter - Detailed Statistics")
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Title and view toggle buttons
        header_layout = QHBoxLayout()
        
        title = QLabel("Detailed Statistics")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # View toggle buttons
        self.btn_all = QPushButton("All Providers")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self.switch_view('all'))
        header_layout.addWidget(self.btn_all)
        
        self.btn_provider = QPushButton("By Provider")
        self.btn_provider.setCheckable(True)
        self.btn_provider.clicked.connect(lambda: self.switch_view('provider'))
        header_layout.addWidget(self.btn_provider)
        
        self.btn_model = QPushButton("By Model")
        self.btn_model.setCheckable(True)
        self.btn_model.clicked.connect(lambda: self.switch_view('model'))
        header_layout.addWidget(self.btn_model)
        
        layout.addLayout(header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setRowCount(1)
        self.table.setColumnCount(1)
        loading_item = QTableWidgetItem("Loading...")
        loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(0, 0, loading_item)
        layout.addWidget(self.table)
        
        # Populate initial view after dialog is shown (delayed to avoid blocking)
        QTimer.singleShot(50, self._populate_table_all)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        export_button = QPushButton("Export CSV")
        export_button.clicked.connect(self.export_current_view)
        button_layout.addWidget(export_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def switch_view(self, view_type):
        """Switch between All/Provider/Model views"""
        self.current_view = view_type
        
        # Update button states
        self.btn_all.setChecked(view_type == 'all')
        self.btn_provider.setChecked(view_type == 'provider')
        self.btn_model.setChecked(view_type == 'model')
        
        # Repopulate table
        if view_type == 'all':
            self._populate_table_all()
        elif view_type == 'provider':
            self._populate_table_by_provider()
        elif view_type == 'model':
            self._populate_table_by_model()
    
    def _populate_table_all(self):
        """Populate table with aggregated stats across all providers"""
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Scope", "Input", "Output+Reasoning", "Cache Read", 
            "Cache Write", "Messages", "Requests", "Cost"
        ])
        
        # Populate table
        scopes = [
            ('current_session', 'Current Session'),
            ('today', 'Today'),
            ('7days', 'Last 7 Days'),
            ('month', 'This Month')
        ]
        
        self.table.setRowCount(len(scopes))
        
        for i, (scope_key, scope_name) in enumerate(scopes):
            stats = self.stats_cache.get(scope_key)
            
            # Scope column (left aligned)
            scope_item = QTableWidgetItem(scope_name)
            self.table.setItem(i, 0, scope_item)
            
            if not stats:
                for col in range(1, 8):
                    item = QTableWidgetItem("N/A")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(i, col, item)
                continue
            
            input_tok = stats.get('input', 0)
            output_tok = stats.get('output', 0)
            reasoning_tok = stats.get('reasoning', 0)
            cache_read = stats.get('cache_read', 0)
            cache_write = stats.get('cache_write', 0)
            messages = stats.get('messages', 0)
            requests = stats.get('requests', 0)
            total_output_tok = output_tok + reasoning_tok
            
            # Calculate cost using model-specific pricing
            cost = self._calculate_cost_by_model(scope_key)
            
            # All numeric columns right-aligned
            input_item = QTableWidgetItem(f"{input_tok:,}")
            input_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, input_item)
            
            output_item = QTableWidgetItem(f"{total_output_tok:,}")
            output_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 2, output_item)
            
            cache_read_item = QTableWidgetItem(f"{cache_read:,}")
            cache_read_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 3, cache_read_item)
            
            cache_write_item = QTableWidgetItem(f"{cache_write:,}")
            cache_write_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 4, cache_write_item)
            
            messages_item = QTableWidgetItem(f"{messages:,}")
            messages_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 5, messages_item)
            
            requests_item = QTableWidgetItem(f"{requests:,}")
            requests_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 6, requests_item)
            
            cost_item = QTableWidgetItem(f"${cost:.2f}")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 7, cost_item)
        
        self.table.resizeColumnsToContents()
    
    def _populate_table_by_provider(self):
        """Populate table with stats grouped by provider"""
        if not self.app_instance:
            QMessageBox.warning(self, "Error", "Cannot fetch provider stats")
            return
        
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Provider / Scope", "Input", "Output+Reasoning", 
            "Cache Read", "Cache Write", "Messages", "Requests", "Cost"
        ])
        
        scopes = [
            ('current_session', 'Current Session'),
            ('today', 'Today'),
            ('7days', 'Last 7 Days'),
            ('month', 'This Month')
        ]
        
        # Collect all data
        rows = []
        for scope_key, scope_name in scopes:
            provider_stats = self.app_instance.client.get_stats_by_provider(scope_key)
            if provider_stats:
                # Get scope totals from app_instance
                scope_totals = self.stats_cache.get(scope_key)
                if scope_totals:
                    # Add scope_key to totals for later use
                    scope_totals = scope_totals.copy()
                    scope_totals['_scope_key'] = scope_key
                
                # Add section header with totals
                rows.append(('header', scope_name, scope_totals))
                
                # Add provider rows
                for provider_id in sorted(provider_stats.keys()):
                    stats = provider_stats[provider_id]
                    # Add scope_key to stats for cost calculation
                    stats = stats.copy()
                    stats['_scope_key'] = scope_key
                    stats['_provider_id'] = provider_id
                    rows.append(('data', f"  {provider_id}", stats, provider_id, None))
                
                # Add empty separator row
                rows.append(('empty', '', None, None, None))
        
        self.table.setRowCount(len(rows))
        
        for i, row_data in enumerate(rows):
            if row_data[0] == 'header':
                # Section header with totals
                scope_name = row_data[1]
                scope_totals = row_data[2]
                
                item = QTableWidgetItem(scope_name)
                font = QFont()
                font.setBold(True)
                item.setFont(font)
                self.table.setItem(i, 0, item)
                
                if scope_totals:
                    # Display scope totals
                    input_tok = scope_totals.get('input', 0)
                    output_tok = scope_totals.get('output', 0)
                    reasoning_tok = scope_totals.get('reasoning', 0)
                    cache_read = scope_totals.get('cache_read', 0)
                    cache_write = scope_totals.get('cache_write', 0)
                    messages = scope_totals.get('messages', 0)
                    requests = scope_totals.get('requests', 0)
                    total_output = output_tok + reasoning_tok
                    
                    # Calculate cost using model-specific pricing
                    cost = self._calculate_cost_by_model(scope_totals.get('_scope_key', 'today'))
                    
                    values = [input_tok, total_output, cache_read, cache_write, messages, requests]
                    for col, value in enumerate(values, start=1):
                        item = QTableWidgetItem(f"{value:,}")
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                        self.table.setItem(i, col, item)
                    
                    cost_item = QTableWidgetItem(f"${cost:.2f}")
                    cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    font = QFont()
                    font.setBold(True)
                    cost_item.setFont(font)
                    self.table.setItem(i, 7, cost_item)
                else:
                    for col in range(1, 8):
                        self.table.setItem(i, col, QTableWidgetItem(""))
            elif row_data[0] == 'empty':
                # Empty separator row
                for col in range(8):
                    self.table.setItem(i, col, QTableWidgetItem(""))
            else:  # data row
                # Data row
                provider_name = row_data[1]
                stats = row_data[2]
                provider_id = row_data[3]
                
                self.table.setItem(i, 0, QTableWidgetItem(provider_name))
                
                input_tok = stats.get('input', 0)
                output_tok = stats.get('output', 0)
                reasoning_tok = stats.get('reasoning', 0)
                cache_read = stats.get('cache_read', 0)
                cache_write = stats.get('cache_write', 0)
                messages = stats.get('messages', 0)
                requests = stats.get('requests', 0)
                total_output = output_tok + reasoning_tok
                
                # Calculate cost for this provider using model-specific pricing
                # Get the scope_key from stats if available, otherwise use 'today' as default
                scope_key = stats.get('_scope_key', 'today')
                cost = 0.0
                # Get model stats for this provider and calculate cost per model
                model_stats_response = self.app_instance.client.get_stats_by_model(scope_key)
                if model_stats_response and provider_id in model_stats_response:
                    for model_id, model_stats in model_stats_response[provider_id].items():
                        cost += self.settings.calculate_cost(model_stats, model_id=model_id, provider_id=provider_id)
                else:
                    # Fallback to generic calculation (won't have model-specific pricing)
                    cost = self.settings.calculate_cost(stats)
                
                # Display values
                values = [input_tok, total_output, cache_read, cache_write, messages, requests]
                for col, value in enumerate(values, start=1):
                    item = QTableWidgetItem(f"{value:,}")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(i, col, item)
                
                cost_item = QTableWidgetItem(f"${cost:.2f}")
                cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 7, cost_item)
        
        self.table.resizeColumnsToContents()
    
    def _populate_table_by_model(self):
        """Populate table with stats grouped by provider and model"""
        if not self.app_instance:
            QMessageBox.warning(self, "Error", "Cannot fetch model stats")
            return
        
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Provider / Model / Scope", "Input", "Output+Reasoning",
            "Cache Read", "Cache Write", "Messages", "Requests", "Cost"
        ])
        
        scopes = [
            ('current_session', 'Current Session'),
            ('today', 'Today'),
            ('7days', 'Last 7 Days'),
            ('month', 'This Month')
        ]
        
        # Collect all data
        rows = []
        for scope_key, scope_name in scopes:
            model_stats = self.app_instance.client.get_stats_by_model(scope_key)
            if model_stats:
                # Get scope totals from app_instance
                scope_totals = self.stats_cache.get(scope_key)
                if scope_totals:
                    # Add scope_key to totals for later use
                    scope_totals = scope_totals.copy()
                    scope_totals['_scope_key'] = scope_key
                
                # Add scope header with totals
                rows.append(('header', scope_name, scope_totals, None, None))
                
                # Add provider and model rows
                for provider_id in sorted(model_stats.keys()):
                    rows.append(('subheader', f"  {provider_id}", None, None, None))
                    for model_id in sorted(model_stats[provider_id].keys()):
                        stats = model_stats[provider_id][model_id]
                        rows.append(('data', f"    {model_id}", stats, provider_id, model_id))
                
                # Add empty separator row
                rows.append(('empty', '', None, None, None))
        
        self.table.setRowCount(len(rows))
        
        for i, row_data in enumerate(rows):
            if row_data[0] == 'header':
                # Scope header with totals
                scope_name = row_data[1]
                scope_totals = row_data[2]
                
                item = QTableWidgetItem(scope_name)
                font = QFont()
                font.setBold(True)
                font.setPointSize(14)
                item.setFont(font)
                self.table.setItem(i, 0, item)
                
                if scope_totals:
                    # Display scope totals
                    input_tok = scope_totals.get('input', 0)
                    output_tok = scope_totals.get('output', 0)
                    reasoning_tok = scope_totals.get('reasoning', 0)
                    cache_read = scope_totals.get('cache_read', 0)
                    cache_write = scope_totals.get('cache_write', 0)
                    messages = scope_totals.get('messages', 0)
                    requests = scope_totals.get('requests', 0)
                    total_output = output_tok + reasoning_tok
                    
                    # Calculate cost using model-specific pricing
                    cost = self._calculate_cost_by_model(scope_totals.get('_scope_key', 'today'))
                    
                    values = [input_tok, total_output, cache_read, cache_write, messages, requests]
                    for col, value in enumerate(values, start=1):
                        item = QTableWidgetItem(f"{value:,}")
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        font = QFont()
                        font.setBold(True)
                        font.setPointSize(14)
                        item.setFont(font)
                        self.table.setItem(i, col, item)
                    
                    cost_item = QTableWidgetItem(f"${cost:.2f}")
                    cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    font = QFont()
                    font.setBold(True)
                    font.setPointSize(14)
                    cost_item.setFont(font)
                    self.table.setItem(i, 7, cost_item)
                else:
                    for col in range(1, 8):
                        self.table.setItem(i, col, QTableWidgetItem(""))
            elif row_data[0] == 'subheader':
                # Provider subheader
                item = QTableWidgetItem(row_data[1])
                font = QFont()
                font.setBold(True)
                item.setFont(font)
                self.table.setItem(i, 0, item)
                for col in range(1, 8):
                    self.table.setItem(i, col, QTableWidgetItem(""))
            elif row_data[0] == 'empty':
                # Empty separator row
                for col in range(8):
                    self.table.setItem(i, col, QTableWidgetItem(""))
            else:  # data row
                # Data row
                model_name = row_data[1]
                stats = row_data[2]
                provider_id = row_data[3]
                model_id = row_data[4]
                
                self.table.setItem(i, 0, QTableWidgetItem(model_name))
                
                input_tok = stats.get('input', 0)
                output_tok = stats.get('output', 0)
                reasoning_tok = stats.get('reasoning', 0)
                cache_read = stats.get('cache_read', 0)
                cache_write = stats.get('cache_write', 0)
                messages = stats.get('messages', 0)
                requests = stats.get('requests', 0)
                total_output = output_tok + reasoning_tok
                cost = self.settings.calculate_cost(stats, model_id=model_id, provider_id=provider_id)
                
                values = [input_tok, total_output, cache_read, cache_write, messages, requests]
                for col, value in enumerate(values, start=1):
                    item = QTableWidgetItem(f"{value:,}")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(i, col, item)
                
                cost_item = QTableWidgetItem(f"${cost:.2f}")
                cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 7, cost_item)
        
        self.table.resizeColumnsToContents()
    
    def _calculate_cost_by_model(self, scope):
        """
        Calculate cost using model-specific pricing by aggregating cost from each model.
        scope: 'today', 'month', '7days', 'current_session'
        Returns total cost (float)
        """
        if not self.app_instance:
            # Fallback to default pricing if app_instance not available
            stats = self.stats_cache.get(scope)
            return self.settings.calculate_cost(stats) if stats else 0.0
        
        model_stats = self.app_instance.client.get_stats_by_model(scope)
        if not model_stats:
            # Fallback to default pricing if model stats not available
            stats = self.stats_cache.get(scope)
            return self.settings.calculate_cost(stats) if stats else 0.0
        
        total_cost = 0.0
        for provider_id, models in model_stats.items():
            for model_id, stats in models.items():
                cost = self.settings.calculate_cost(
                    stats, 
                    model_id=model_id, 
                    provider_id=provider_id
                )
                total_cost += cost
        
        return total_cost
    
    def export_current_view(self):
        """Export current view to CSV"""
        import csv
        
        # Get filename
        view_name = self.current_view
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            os.path.join(os.path.expanduser("~"), "Desktop", 
                        f"opencode_tokens_{view_name}_{int(time.time())}.csv"),
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write headers
                headers = []
                for col in range(self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(col)
                    headers.append(header_item.text() if header_item else f"Column {col}")
                writer.writerow(headers)
                
                # Write rows
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Export Complete", 
                                   f"Data exported to:\n{os.path.basename(filename)}")
            # Open in Finder
            os.system(f'open -R "{filename}"')
        
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export data:\n{str(e)}")


class SettingsDialog(QDialog):
    """Dialog for editing settings with tabbed interface"""
    
    def __init__(self, settings, app_instance):
        super().__init__()
        self.settings = settings
        self.app_instance = app_instance
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(550)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("OpenCode Token Meter Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: Cost Meter
        cost_tab = QWidget()
        cost_layout = QVBoxLayout()
        cost_form = QFormLayout()
        
        # ==================== DEFAULT PRICING SECTION ====================
        default_section_label = QLabel("Default Pricing")
        default_section_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        cost_form.addRow(default_section_label)
        
        # Default price settings
        self.input_price = QLineEdit(str(settings.get('prices.default.input', 0.5)))
        cost_form.addRow("Input Price ($/1M tokens):", self.input_price)
        
        self.output_price = QLineEdit(str(settings.get('prices.default.output', 3.0)))
        cost_form.addRow("Output Price ($/1M tokens):", self.output_price)
        
        self.caching_price = QLineEdit(str(settings.get('prices.default.caching', 0.05)))
        cost_form.addRow("Caching Price ($/1M tokens):", self.caching_price)
        
        self.request_price = QLineEdit(str(settings.get('prices.default.request', 0.0)))
        cost_form.addRow("Request Price ($):", self.request_price)
        
        # Add spacing + separator
        spacer_default = QLabel("")
        spacer_default.setMinimumHeight(10)
        cost_form.addRow(spacer_default)
        separator_default = QLabel()
        separator_default.setStyleSheet("border-top: 1px solid #ccc;")
        separator_default.setMaximumHeight(1)
        cost_form.addRow(separator_default)
        spacer_default2 = QLabel("")
        spacer_default2.setMinimumHeight(10)
        cost_form.addRow(spacer_default2)
        
        # ==================== MODEL-SPECIFIC PRICING SECTION ====================
        model_section_label = QLabel("Model-Specific Pricing")
        model_section_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        cost_form.addRow(model_section_label)
        
        # Model selector dropdown
        self.model_selector = QComboBox()
        
        # Populate with existing models from settings (user's models only)
        models_dict = settings.get('prices.models', {})
        for model_key in sorted(models_dict.keys()):
            self.model_selector.addItem(model_key, model_key)
        
        # Add "Custom model" at the bottom
        self.model_selector.addItem("Custom model", "custom")
        
        self.model_selector.currentIndexChanged.connect(self._on_model_selected)
        cost_form.addRow("Select Model:", self.model_selector)
        
        # Provider input
        self.provider_input = QLineEdit()
        self.provider_input.setPlaceholderText("e.g., github-copilot, google, opencode")
        cost_form.addRow("Provider:", self.provider_input)
        
        # Model input
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g., claude-sonnet-4.5, gpt-5-mini")
        cost_form.addRow("Model:", self.model_input)
        
        # Model-specific prices
        self.model_input_price = QLineEdit()
        self.model_input_price.setPlaceholderText("0.0")
        cost_form.addRow("Input Price ($/1M tokens):", self.model_input_price)
        
        self.model_output_price = QLineEdit()
        self.model_output_price.setPlaceholderText("0.0")
        cost_form.addRow("Output Price ($/1M tokens):", self.model_output_price)
        
        self.model_caching_price = QLineEdit()
        self.model_caching_price.setPlaceholderText("0.0")
        cost_form.addRow("Caching Price ($/1M tokens):", self.model_caching_price)
        
        self.model_request_price = QLineEdit()
        self.model_request_price.setPlaceholderText("0.0")
        cost_form.addRow("Request Price ($):", self.model_request_price)
        
        # Save/Delete model buttons
        model_buttons = QHBoxLayout()
        self.save_model_button = QPushButton("Save Model Pricing")
        self.save_model_button.clicked.connect(self._save_model_pricing)
        model_buttons.addWidget(self.save_model_button)
        
        self.delete_model_button = QPushButton("Delete Model Pricing")
        self.delete_model_button.clicked.connect(self._delete_model_pricing)
        model_buttons.addWidget(self.delete_model_button)
        cost_form.addRow(model_buttons)
        
        cost_layout.addLayout(cost_form)
        cost_layout.addStretch()
        cost_tab.setLayout(cost_layout)
        
        # Tab 2: Notification
        notif_tab = QWidget()
        notif_layout = QVBoxLayout()
        notif_form = QFormLayout()
        
        notification_label = QLabel("Notification Settings")
        notification_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        notif_form.addRow(notification_label)
        
        # Notifications enabled checkbox
        self.notifications_enabled = QCheckBox()
        self.notifications_enabled.setChecked(settings.get('notifications_enabled', True))
        notif_form.addRow("Enable Notifications:", self.notifications_enabled)
        
        # Add spacing
        spacer_notif = QLabel("")
        spacer_notif.setMinimumHeight(10)
        notif_form.addRow(spacer_notif)
        separator_notif = QLabel()
        separator_notif.setStyleSheet("border-top: 1px solid #ccc;")
        separator_notif.setMaximumHeight(1)
        notif_form.addRow(separator_notif)
        spacer_notif2 = QLabel("")
        spacer_notif2.setMinimumHeight(10)
        notif_form.addRow(spacer_notif2)
        
        threshold_label = QLabel("Threshold Settings")
        threshold_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        notif_form.addRow(threshold_label)
        
        # Threshold settings (enable = show notifications when exceeded)
        self.thresholds_enabled = QCheckBox()
        self.thresholds_enabled.setChecked(settings.get('thresholds.enabled', False))
        self.thresholds_enabled.stateChanged.connect(self._on_threshold_enabled_changed)
        notif_form.addRow("Enable Thresholds:", self.thresholds_enabled)
        
        # Convert from raw tokens to K (thousands)
        daily_tokens_raw = settings.get('thresholds.daily_tokens', 1000000)
        daily_tokens_k = int(daily_tokens_raw / 1000)
        self.daily_tokens = QLineEdit(f"{daily_tokens_k}")
        notif_form.addRow("Daily Token Limit (K):", self.daily_tokens)
        
        self.daily_cost = QLineEdit(str(settings.get('thresholds.daily_cost', 20.0)))
        notif_form.addRow("Daily Cost Limit ($):", self.daily_cost)
        
        # Monthly threshold settings
        monthly_tokens_raw = settings.get('thresholds.monthly_tokens', 10000000)
        monthly_tokens_k = int(monthly_tokens_raw / 1000)
        self.monthly_tokens = QLineEdit(f"{monthly_tokens_k}")
        notif_form.addRow("Monthly Token Limit (K):", self.monthly_tokens)
        
        self.monthly_cost = QLineEdit(str(settings.get('thresholds.monthly_cost', 1000.0)))
        notif_form.addRow("Monthly Cost Limit ($):", self.monthly_cost)
        
        # Monthly reset day (1-31)
        self.monthly_reset_day = QLineEdit(str(settings.get('thresholds.monthly_reset_day', 1)))
        notif_form.addRow("Monthly Reset Day (1-31):", self.monthly_reset_day)
        
        # Add spacing
        spacer_refresh = QLabel("")
        spacer_refresh.setMinimumHeight(10)
        notif_form.addRow(spacer_refresh)
        separator_refresh = QLabel()
        separator_refresh.setStyleSheet("border-top: 1px solid #ccc;")
        separator_refresh.setMaximumHeight(1)
        notif_form.addRow(separator_refresh)
        spacer_refresh2 = QLabel("")
        spacer_refresh2.setMinimumHeight(10)
        notif_form.addRow(spacer_refresh2)
        
        refresh_label = QLabel("Auto-refresh Interval")
        refresh_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        notif_form.addRow(refresh_label)
        
        # Refresh interval
        self.refresh_interval = QLineEdit(str(settings.get('refresh_interval', 300)))
        notif_form.addRow("Refresh Interval (seconds):", self.refresh_interval)
        
        notif_layout.addLayout(notif_form)
        notif_layout.addStretch()
        notif_tab.setLayout(notif_layout)
        
        # Add tabs to tab widget
        self.tabs.addTab(cost_tab, "Cost Meter")
        self.tabs.addTab(notif_tab, "Notification")
        
        layout.addWidget(self.tabs)
        
        # Initial enable/disable state
        self._on_threshold_enabled_changed()
        
        # Initial load of first model (if exists)
        if self.model_selector.count() > 1:
            self.model_selector.setCurrentIndex(0)  # Select first preset model
        else:
            self.model_selector.setCurrentIndex(0)  # "Custom model" (only option)
        self._on_model_selected()
        
        # Buttons (shared for all tabs)
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_model_selected(self):
        """Load selected model's pricing into input fields"""
        model_key = self.model_selector.currentData()
        
        if model_key == "custom":
            # Clear all fields for custom entry
            self.provider_input.clear()
            self.model_input.clear()
            self.model_input_price.clear()
            self.model_output_price.clear()
            self.model_caching_price.clear()
            self.model_request_price.clear()
            self.provider_input.setEnabled(True)
            self.model_input.setEnabled(True)
            self.delete_model_button.setEnabled(False)
        else:
            # Load model pricing - use dict access instead of dot notation
            # because model_key contains '/' which breaks settings.get() parsing
            models_dict = self.settings.get('prices.models', {})
            model_prices = models_dict.get(model_key)
            if model_prices:
                # Parse provider/model from key
                if '/' in model_key:
                    provider, model = model_key.split('/', 1)
                    self.provider_input.setText(provider)
                    self.model_input.setText(model)
                else:
                    self.provider_input.setText(model_prices.get('provider', ''))
                    self.model_input.setText(model_key)
                
                self.model_input_price.setText(str(model_prices.get('input', 0.0)))
                self.model_output_price.setText(str(model_prices.get('output', 0.0)))
                self.model_caching_price.setText(str(model_prices.get('caching', 0.0)))
                self.model_request_price.setText(str(model_prices.get('request', 0.0)))
                
                self.provider_input.setEnabled(False)
                self.model_input.setEnabled(False)
                self.delete_model_button.setEnabled(True)
    
    def _save_model_pricing(self):
        """Save current model pricing to settings"""
        try:
            provider = self.provider_input.text().strip()
            model = self.model_input.text().strip()
            
            if not provider or not model:
                QMessageBox.warning(self, "Error", "Provider and Model are required")
                return
            
            # Create combined key
            model_key = f"{provider}/{model}"
            
            # Get prices
            prices = {
                'input': float(self.model_input_price.text() or 0.0),
                'output': float(self.model_output_price.text() or 0.0),
                'caching': float(self.model_caching_price.text() or 0.0),
                'request': float(self.model_request_price.text() or 0.0),
                'provider': provider
            }
            
            # Save to settings
            self.settings.add_model_price(model_key, prices)
            
            # Update dropdown (if new model)
            existing_index = self.model_selector.findData(model_key)
            if existing_index == -1:
                self.model_selector.addItem(model_key, model_key)
                self.model_selector.setCurrentIndex(self.model_selector.count() - 1)
            else:
                self.model_selector.setCurrentIndex(existing_index)
            
            QMessageBox.information(self, "Success", f"Pricing saved for {model_key}")
            self._on_model_selected()  # Reload to lock fields
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save model pricing: {str(e)}")
    
    def _delete_model_pricing(self):
        """Delete current model pricing from settings"""
        model_key = self.model_selector.currentData()
        
        if model_key == "custom":
            QMessageBox.warning(self, "Error", "No model selected to delete")
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Delete pricing for {model_key}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings.delete_model_price(model_key)
                
                # Remove from dropdown
                current_index = self.model_selector.currentIndex()
                self.model_selector.removeItem(current_index)
                
                # Select "Custom model"
                self.model_selector.setCurrentIndex(0)
                self._on_model_selected()
                
                QMessageBox.information(self, "Success", f"Deleted pricing for {model_key}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete model pricing: {str(e)}")
    
    def _on_threshold_enabled_changed(self):
        """Enable/disable threshold fields based on checkbox state"""
        enabled = self.thresholds_enabled.isChecked()
        self.daily_tokens.setEnabled(enabled)
        self.daily_cost.setEnabled(enabled)
        self.monthly_tokens.setEnabled(enabled)
        self.monthly_cost.setEnabled(enabled)
        self.monthly_reset_day.setEnabled(enabled)
    
    def save_settings(self):
        """Save all settings"""
        try:
            # Default Prices
            self.settings.set('prices.default.input', float(self.input_price.text()))
            self.settings.set('prices.default.output', float(self.output_price.text()))
            self.settings.set('prices.default.caching', float(self.caching_price.text()))
            self.settings.set('prices.default.request', float(self.request_price.text()))
            
            # Notifications
            self.settings.set('notifications_enabled', self.notifications_enabled.isChecked())
            
            # Thresholds - convert from K to raw tokens
            self.settings.set('thresholds.enabled', self.thresholds_enabled.isChecked())
            daily_tokens_k = int(self.daily_tokens.text())
            daily_tokens_raw = daily_tokens_k * 1000
            self.settings.set('thresholds.daily_tokens', daily_tokens_raw)
            self.settings.set('thresholds.daily_cost', float(self.daily_cost.text()))
            
            # Monthly thresholds
            monthly_tokens_k = int(self.monthly_tokens.text())
            monthly_tokens_raw = monthly_tokens_k * 1000
            self.settings.set('thresholds.monthly_tokens', monthly_tokens_raw)
            self.settings.set('thresholds.monthly_cost', float(self.monthly_cost.text()))
            
            # Monthly reset day (validate 1-31)
            reset_day = int(self.monthly_reset_day.text())
            if reset_day < 1 or reset_day > 31:
                raise ValueError("Monthly reset day must be between 1 and 31")
            self.settings.set('thresholds.monthly_reset_day', reset_day)
            
            # Refresh interval
            refresh_interval = int(self.refresh_interval.text())
            if refresh_interval < 10:
                raise ValueError("Refresh interval must be at least 10 seconds")
            self.settings.set('refresh_interval', refresh_interval)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")


class CustomRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("Export Custom Range")
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.start_dt = QDateTimeEdit()
        self.start_dt.setCalendarPopup(True)
        self.start_dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        default_start = QDateTime.currentDateTime().addDays(-7)
        self.start_dt.setDateTime(default_start)
        form.addRow("Start Time:", self.start_dt)
        
        self.end_dt = QDateTimeEdit()
        self.end_dt.setCalendarPopup(True)
        self.end_dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_dt.setDateTime(QDateTime.currentDateTime())
        form.addRow("End Time:", self.end_dt)
        
        layout.addLayout(form)
        
        button_layout = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.accept)
        button_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _calculate_cost_by_model(self):
        """
        Calculate cost using model-specific pricing by querying agent for model stats.
        Falls back to default pricing if agent_client is not available.
        Returns total cost (float)
        """
        if self.agent_client:
            # Try to get model-specific stats from agent
            # Use the stats we already have as a fallback
            # Note: get_stats_range returns aggregate stats, not by model
            # So we'll use default pricing for custom range unless we query differently
            cost = self.settings.calculate_cost(self.stats)
        else:
            # No agent client, use default pricing
            cost = self.settings.calculate_cost(self.stats)
        
        return cost
    
    def get_timestamps(self):
        """Get Unix timestamps for selected range (in UTC)"""
        start_dt = self.start_dt.dateTime()
        end_dt = self.end_dt.dateTime()
        
        # Convert to Unix timestamp (automatically handles local to UTC)
        start_ts = int(start_dt.toSecsSinceEpoch())
        end_ts = int(end_dt.toSecsSinceEpoch())
        
        return start_ts, end_ts


class CustomRangeStatsDialog(QDialog):
    """Dialog showing statistics for custom date range"""
    
    def __init__(self, stats, settings, agent_client=None, start_ts=None, end_ts=None):
        super().__init__()
        self.stats = stats
        self.settings = settings
        self.agent_client = agent_client
        self.start_ts = start_ts
        self.end_ts = end_ts
        
        self.setWindowTitle("Custom Range Statistics")
        self.setMinimumWidth(600)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # Title with date range
        import time
        start_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(start_ts))
        end_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(end_ts))
        title = QLabel(f"Statistics: {start_str} to {end_str}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])
        
        # Populate stats with error handling
        try:
            input_tok = self.stats.get('input', 0)
            output_tok = self.stats.get('output', 0)
            reasoning_tok = self.stats.get('reasoning', 0)
            cache_read = self.stats.get('cache_read', 0)
            cache_write = self.stats.get('cache_write', 0)
            messages = self.stats.get('messages', 0)
            requests = self.stats.get('requests', 0)
            
            # Calculate cost with error handling
            try:
                cost = self._calculate_cost_by_model()
            except Exception as e:
                print(f"Error calculating cost: {e}", file=sys.stderr)
                cost = self.settings.calculate_cost(self.stats) if self.stats else 0.0
            
            total_output = output_tok + reasoning_tok
            
            rows = [
                ("Input Tokens", f"{input_tok:,}" if self.stats else "N/A"),
                ("Output Tokens", f"{output_tok:,}" if self.stats else "N/A"),
                ("Reasoning Tokens", f"{reasoning_tok:,}" if self.stats else "N/A"),
                ("Total Output (Output + Reasoning)", f"{total_output:,}" if self.stats else "N/A"),
                ("Cache Read Tokens", f"{cache_read:,}" if self.stats else "N/A"),
                ("Cache Write Tokens", f"{cache_write:,}" if self.stats else "N/A"),
                ("Messages (Assistant Responses)", f"{messages:,}" if self.stats else "N/A"),
                ("Requests (User Messages)", f"{requests:,}" if self.stats else "N/A"),
                ("Estimated Cost", f"${cost:.2f}")
            ]
        except Exception as e:
            print(f"Error populating stats table: {e}", file=sys.stderr)
            rows = [("Error", str(e))]
        
        self.table.setRowCount(len(rows))
        
        for i, (metric, value) in enumerate(rows):
            metric_item = QTableWidgetItem(metric)
            self.table.setItem(i, 0, metric_item)
            
            value_item = QTableWidgetItem(value)
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, value_item)
        
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
