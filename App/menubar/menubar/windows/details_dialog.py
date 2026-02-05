import os
import sys
import time
import csv
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Tuple, cast
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                                QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                                QFileDialog, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont
from menubar.utils.ui_helpers import get_icon_path

if TYPE_CHECKING:
    from menubar.app import OpenCodeTokenMeter
    from menubar.settings import Settings

class DetailsDialog(QDialog):
    """Dialog showing detailed statistics table"""
    
    def __init__(self, stats_cache: Dict[str, Optional[Dict[str, Any]]], settings: 'Settings', app_instance: Optional['OpenCodeTokenMeter'] = None):

        super().__init__()
        self.stats_cache = stats_cache
        self.settings = settings
        self.app_instance = app_instance
        self.current_view = 'all'
        
        # Set window icon
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        self.setWindowTitle("OpenCode Token Meter - Detailed Statistics")
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
        
        # Standard window behavior
        self.setWindowFlags(Qt.WindowType.Window)
        self.setModal(False)
        
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
    
    def switch_view(self, view_type: str) -> None:
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

    def refresh(self) -> None:
        """Refresh current view with latest stats"""
        self.switch_view(self.current_view)
    
    def _populate_table_all(self) -> None:
        """Populate table with aggregated stats across all providers"""
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Scope", "Input", "Output+Reasoning", "Cache Read", 
            "Cache Write", "Messages", "Requests", "Cost"
        ])
        
        # Populate table
        scopes: List[Tuple[str, str]] = [
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
            
            input_tok = cast(int, stats.get('input', 0))
            output_tok = cast(int, stats.get('output', 0))
            reasoning_tok = cast(int, stats.get('reasoning', 0))
            cache_read = cast(int, stats.get('cache_read', 0))
            cache_write = cast(int, stats.get('cache_write', 0))
            messages = cast(int, stats.get('messages', 0))
            requests = cast(int, stats.get('requests', 0))
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
        if self.table.columnWidth(0) > 150:
            self.table.setColumnWidth(0, 150)
    
    def _populate_table_by_provider(self) -> None:
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
                scope_key = stats.get('_scope_key', 'today')
                cost = 0.0
                # Get model stats for this provider and calculate cost per model
                model_stats_response = self.app_instance.client.get_stats_by_model(scope_key)
                if model_stats_response and provider_id in model_stats_response:
                    for model_id, model_stats in model_stats_response[provider_id].items():
                        cost += self.settings.calculate_cost(model_stats, model_id=model_id, provider_id=provider_id)
                else:
                    # Fallback to generic calculation
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
        if self.table.columnWidth(0) > 150:
            self.table.setColumnWidth(0, 150)
    
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
        if self.table.columnWidth(0) > 150:
            self.table.setColumnWidth(0, 150)
    
    def _calculate_cost_by_model(self, scope):
        """
        Calculate cost using model-specific pricing by aggregating cost from each model.
        Returns total cost (float)
        """
        if not self.app_instance:
            stats = self.stats_cache.get(scope)
            return self.settings.calculate_cost(stats) if stats else 0.0
        
        model_stats = self.app_instance.client.get_stats_by_model(scope)
        if not model_stats:
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
                
                headers = []
                for col in range(self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(col)
                    headers.append(header_item.text() if header_item else f"Column {col}")
                writer.writerow(headers)
                
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Export Complete", 
                                   f"Data exported to:\n{os.path.basename(filename)}")
            
            # Platform-specific "show in folder"
            if sys.platform == 'win32':
                os.startfile(os.path.dirname(filename))
            elif sys.platform == 'darwin':
                os.system(f'open -R "{filename}"')
            else:
                import subprocess
                subprocess.run(['xdg-open', os.path.dirname(filename)])
        
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export data:\n{str(e)}")
