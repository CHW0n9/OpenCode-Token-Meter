from typing import TYPE_CHECKING, Tuple, Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDateEdit, 
                               QTimeEdit, QHBoxLayout, QPushButton, QWidget)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QIcon
from menubar.utils.ui_helpers import get_icon_path

if TYPE_CHECKING:
    from menubar.app import OpenCodeTokenMeter

class CustomRangeDialog(QDialog):
    def __init__(self, app_instance: Optional["OpenCodeTokenMeter"] = None):
        super().__init__()
        self.app_instance = app_instance
        
        # Make dialog non-modal
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)
        
        # Set window icon
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        self.setWindowTitle("Export Custom Range")
        self.setFixedWidth(450)
        self.setFixedHeight(150)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 15, 30, 15)
        layout.setSpacing(10)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # Start Time Row
        start_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.setMinimumWidth(120)
        
        self.start_time = QTimeEdit()
        self.start_time.setTime(QTime(0, 0))
        self.start_time.setMinimumWidth(100)
        
        start_layout.addWidget(self.start_date)
        start_layout.addSpacing(10)
        start_layout.addWidget(self.start_time)
        form.addRow("Start Time:", start_layout)
        
        # End Time Row
        end_layout = QHBoxLayout()
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setMinimumWidth(120)
        
        self.end_time = QTimeEdit()
        self.end_time.setTime(QTime.currentTime())
        self.end_time.setMinimumWidth(100)
        
        end_layout.addWidget(self.end_date)
        end_layout.addSpacing(10)
        end_layout.addWidget(self.end_time)
        form.addRow("End Time:", end_layout)
        
        layout.addLayout(form)
        
        button_layout = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.setMinimumHeight(30)
        export_btn.clicked.connect(self.accept)
        button_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(30)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_timestamps(self):
        """Get Unix timestamps for selected range (in UTC)"""
        start_dt = QDateTime(self.start_date.date(), self.start_time.time())
        end_dt = QDateTime(self.end_date.date(), self.end_time.time())
        
        # Convert to Unix timestamp
        start_ts = int(start_dt.toSecsSinceEpoch())
        end_ts = int(end_dt.toSecsSinceEpoch())
        
        return start_ts, end_ts
