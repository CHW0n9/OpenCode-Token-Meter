import sys
import time
from typing import TYPE_CHECKING, Optional, Dict, Any
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon
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
        
        # Make dialog non-modal
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
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
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
            table_width = self.table.horizontalHeader().length() + self.table.verticalHeader().width() + 40
            table_height = self.table.verticalHeader().length() + self.table.horizontalHeader().height() + 120
            
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
        if not self.agent_client or not self.start_ts or not self.end_ts:
            return self.settings.calculate_cost(self.stats)
        
        try:
            # Query agent for model-specific stats in this time range
            model_stats = self.agent_client.get_stats_by_model_range(self.start_ts, self.end_ts)
            
            if not model_stats:
                return self.settings.calculate_cost(self.stats)
            
            # Calculate total cost using model-specific pricing
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
        except Exception as e:
            print(f"[ERROR] _calculate_cost_by_model: {e}", file=sys.stderr)
            return self.settings.calculate_cost(self.stats)
