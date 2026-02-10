import os
import sys
from typing import TYPE_CHECKING, Tuple, List, Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QTableWidget, QTableWidgetItem, QPushButton, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from menubar.utils.ui_helpers import get_icon_path

if TYPE_CHECKING:
    from menubar.app import OpenCodeTokenMeter

class MainStatsWindow(QWidget):
    """Main window showing stats table (shown when clicking tray icon)"""
    
    def __init__(self, app_instance: 'OpenCodeTokenMeter'):

        super().__init__()
        self.app_instance = app_instance
        
        # Set window icon
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        self.setWindowTitle("OpenCode Token Meter")
        self.setMinimumWidth(700)
        self.setMinimumHeight(250)
        
        # Standard window (no WindowStaysOnTopHint - all windows equal priority)
        self.setWindowFlags(Qt.WindowType.Window)
        
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
        
        # Export CSV with dropdown menu
        export_btn = QPushButton("Export CSV")
        # Make button 25% wider than default
        export_btn.setMinimumWidth(int(export_btn.sizeHint().width() * 1.25))
        export_menu = QMenu(self)
        
        export_session_action = QAction("Current Session", export_menu)
        export_session_action.triggered.connect(lambda: self.on_export_csv_and_close_with_scope('current_session'))
        export_menu.addAction(export_session_action)
        
        export_today_action = QAction("Today", export_menu)
        export_today_action.triggered.connect(lambda: self.on_export_csv_and_close_with_scope('today'))
        export_menu.addAction(export_today_action)
        
        export_7days_action = QAction("Last 7 Days", export_menu)
        export_7days_action.triggered.connect(lambda: self.on_export_csv_and_close_with_scope('7days'))
        export_menu.addAction(export_7days_action)
        
        export_month_action = QAction("This Month", export_menu)
        export_month_action.triggered.connect(lambda: self.on_export_csv_and_close_with_scope('this_month'))
        export_menu.addAction(export_month_action)
        
        export_menu.addSeparator()
        
        export_custom_action = QAction("Custom Range...", export_menu)
        export_custom_action.triggered.connect(lambda: (self.hide(), self.app_instance.export_csv_custom()))
        export_menu.addAction(export_custom_action)
        
        export_btn.setMenu(export_menu)
        button_layout.addWidget(export_btn)
        
        details_btn = QPushButton("Show Details")
        details_btn.clicked.connect(self.on_show_details_and_close)
        button_layout.addWidget(details_btn)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.on_show_settings_and_close)
        button_layout.addWidget(settings_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_export_csv_and_close_with_scope(self, scope: str) -> None:
        """Export CSV with specific scope and close window"""
        self.hide()
        self.app_instance.export_csv_scope(scope)
    
    def on_show_details_and_close(self) -> None:
        """Show details dialog and close window"""
        self.hide()
        self.app_instance.show_details()
    
    def on_show_settings_and_close(self) -> None:
        """Show settings dialog and close window"""
        self.hide()
        self.app_instance.show_settings()
    
    def on_refresh(self) -> None:
        """Handle refresh button"""
        self.app_instance.refresh_now()
    
    def update_display(self) -> None:
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
