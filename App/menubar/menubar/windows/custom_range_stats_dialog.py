import sys
import time
from typing import TYPE_CHECKING, Optional, Dict, Any
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QCloseEvent
from menubar.utils.ui_helpers import get_icon_path

if TYPE_CHECKING:
    from menubar.app import OpenCodeTokenMeter
    from menubar.settings import Settings
    from menubar.uds_client import AgentClient

class CustomRangeStatsDialog(QDialog):
    """Dialog showing statistics for custom date range"""
    
    def __init__(self, stats: Dict[str, Any], settings: 'Settings', agent_client: Optional['AgentClient'] = None, 
                 start_ts: Optional[int] = None, end_ts: Optional[int] = None, 
                 app_instance: Optional['OpenCodeTokenMeter'] = None):
        print(f"[DEBUG] CustomRangeStatsDialog.__init__ starting", file=sys.stderr)
        
        super().__init__()
        self.app_instance = app_instance
        
        # Make dialog non-modal (no permanent stay-on-top)
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)
        
        # Set window icon
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        # Defensive: ensure stats is a dict
        self.stats = stats if isinstance(stats, dict) else {}
        self.settings = settings
        self.agent_client = agent_client
        self.start_ts = start_ts
        self.end_ts = end_ts
        
        # Build window title
        try:
            if isinstance(start_ts, (int, float)) and isinstance(end_ts, (int, float)):
                start_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(start_ts))
                end_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(end_ts))
                window_title = f"Statistics: {start_str} to {end_str}"
            else:
                window_title = "Statistics: Custom Range"
        except Exception as e:
            print(f"Error formatting window title: {e}", file=sys.stderr)
            window_title = "Statistics: Custom Range"
        
        self.setWindowTitle(window_title)
        
        layout = QVBoxLayout()
        
        # Title with date range
        title = QLabel(window_title)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])

        self.table.setRowCount(1)
        loading_item = QTableWidgetItem("Loading...")
        loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(0, 0, loading_item)
        layout.addWidget(self.table)
        
        # Close button removed per request
        self.setLayout(layout)
        
        # Populate stats after dialog shows
        QTimer.singleShot(100, self._populate_table)
        
        print(f"[DEBUG] CustomRangeStatsDialog.__init__ completed successfully", file=sys.stderr)

    def _populate_table(self):
        """Populate stats table with comprehensive error handling"""
        print(f"[DEBUG] _populate_table starting", file=sys.stderr)
        try:
            # Defensive checks for stats
            if not isinstance(self.stats, dict):
                self.stats = {}
            
            # Handle None values with 'or 0' fallback
            input_tok = int(self.stats.get('input', 0) or 0)
            output_tok = int(self.stats.get('output', 0) or 0)
            reasoning_tok = int(self.stats.get('reasoning', 0) or 0)
            cache_read = int(self.stats.get('cache_read', 0) or 0)
            cache_write = int(self.stats.get('cache_write', 0) or 0)
            messages = int(self.stats.get('messages', 0) or 0)
            requests = int(self.stats.get('requests', 0) or 0)
            
            # Calculate cost
            cost = 0.0
            try:
                cost = self._calculate_cost_by_model()
            except Exception as e:
                print(f"Error calculating cost: {e}", file=sys.stderr)
                if self.settings:
                    cost = self.settings.calculate_cost(self.stats)

            total_output = output_tok + reasoning_tok

            rows = [
                ("Input Tokens", f"{input_tok:,}"),
                ("Output Tokens", f"{output_tok:,}"),
                ("Reasoning Tokens", f"{reasoning_tok:,}"),
                ("Total Output (Output + Reasoning)", f"{total_output:,}"),
                ("Cache Read Tokens", f"{cache_read:,}"),
                ("Cache Write Tokens", f"{cache_write:,}"),
                ("Messages (Assistant Responses)", f"{messages:,}"),
                ("Requests (User Messages)", f"{requests:,}"),
                ("Estimated Cost", f"${cost:.2f}")
            ]
        except Exception as e:
            print(f"Error preparing stats data: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            rows = [("Error", f"Failed to load statistics: {str(e)}")]

        # Update table
        try:
            self.table.setRowCount(len(rows))

            for i, (metric, value) in enumerate(rows):
                metric_item = QTableWidgetItem(str(metric))
                self.table.setItem(i, 0, metric_item)

                value_item = QTableWidgetItem(str(value))
                value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 1, value_item)

            self.table.resizeColumnsToContents()
        except Exception as e:
            print(f"Error updating table: {e}", file=sys.stderr)

        # Resize dialog
        try:
            # Resize table columns first
            self.table.resizeColumnsToContents()
            
            # Calculate required size
            horizontal_header = self.table.horizontalHeader()
            vertical_header = self.table.verticalHeader()
            
            if horizontal_header and vertical_header:
                table_width = horizontal_header.length() + vertical_header.width() + 40
                table_height = vertical_header.length() + horizontal_header.height() + 120
            else:
                table_width = 450
                table_height = 350
            
            final_width = max(450, table_width)
            final_height = max(350, table_height)
            
            self.resize(final_width, final_height)
        except Exception as e:
            print(f"Error resizing stats dialog: {e}", file=sys.stderr)
            self.resize(500, 400)
        
        print(f"[DEBUG] _populate_table completed", file=sys.stderr)
    
    def _calculate_cost_by_model(self):
        """
        Calculate cost using model-specific pricing by querying agent for model stats in range.
        Falls back to default pricing if agent_client is not available.
        """
        print(f"[CUSTOM_RANGE_DEBUG] _calculate_cost_by_model called", file=sys.stderr)
        print(f"[CUSTOM_RANGE_DEBUG]   agent_client={self.agent_client is not None}", file=sys.stderr)
        print(f"[CUSTOM_RANGE_DEBUG]   start_ts={self.start_ts}, end_ts={self.end_ts}", file=sys.stderr)
        
        if not self.agent_client or not self.start_ts or not self.end_ts:
            print(f"[CUSTOM_RANGE_DEBUG] Falling back to default cost calculation (no agent client or timestamps)", file=sys.stderr)
            fallback_cost = self.settings.calculate_cost(self.stats)
            print(f"[CUSTOM_RANGE_DEBUG] Default fallback cost: ${fallback_cost:.4f}", file=sys.stderr)
            return fallback_cost

        try:
            # Query agent for model-specific stats in this time range
            print(f"[CUSTOM_RANGE_DEBUG] Calling get_stats_by_model_range...", file=sys.stderr)
            model_stats = self.agent_client.get_stats_by_model_range(self.start_ts, self.end_ts)
            
            # Debug logging for model_stats structure
            print(f"[CUSTOM_RANGE_DEBUG]   model_stats type={type(model_stats)}", file=sys.stderr)
            print(f"[CUSTOM_RANGE_DEBUG]   model_stats is None={model_stats is None}", file=sys.stderr)
            print(f"[CUSTOM_RANGE_DEBUG]   model_stats len={len(model_stats) if model_stats else 'N/A'}", file=sys.stderr)
            
            if model_stats:
                for prov_id in model_stats:
                    models_list = list(model_stats[prov_id].keys()) if model_stats[prov_id] else []
                    print(f"[CUSTOM_RANGE_DEBUG]   Provider '{prov_id}' has {len(models_list)} models: {models_list}", file=sys.stderr)
                    # Log stats for each model
                    for m_id in models_list:
                        m_stats = model_stats[prov_id][m_id]
                        print(f"[CUSTOM_RANGE_DEBUG]     Model '{m_id}': input={m_stats.get('input',0)}, output={m_stats.get('output',0)}, requests={m_stats.get('requests',0)}", file=sys.stderr)
            
            if not model_stats:
                print(f"[CUSTOM_RANGE_DEBUG] model_stats is empty/None, falling back to default pricing", file=sys.stderr)
                fallback_cost = self.settings.calculate_cost(self.stats)
                print(f"[CUSTOM_RANGE_DEBUG] Default fallback cost: ${fallback_cost:.4f}", file=sys.stderr)
                return fallback_cost

            print(f"[CUSTOM_RANGE_DEBUG] Calling calculate_total_cost with model_stats...", file=sys.stderr)
            total_cost = self.settings.calculate_total_cost(model_stats)
            print(f"[CUSTOM_RANGE_DEBUG] calculate_total_cost returned: ${total_cost:.4f}", file=sys.stderr)
            return total_cost
        except Exception as e:
            print(f"[CUSTOM_RANGE_DEBUG] Exception in _calculate_cost_by_model: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            fallback_cost = self.settings.calculate_cost(self.stats)
            print(f"[CUSTOM_RANGE_DEBUG] Exception fallback cost: ${fallback_cost:.4f}", file=sys.stderr)
            return fallback_cost
    
    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        """Handle window close - notify app to update Dock visibility"""
        super().closeEvent(a0)
        if self.app_instance:
            self.app_instance.on_window_closed()
