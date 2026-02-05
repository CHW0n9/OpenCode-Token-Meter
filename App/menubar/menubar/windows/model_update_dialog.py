from typing import TYPE_CHECKING, List, Dict, Any, Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QCheckBox, QHeaderView, QGroupBox, QScrollArea,
                               QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from menubar.settings import DEFAULT_SETTINGS, Settings
from menubar.utils.ui_helpers import get_icon_path

if TYPE_CHECKING:
    from menubar.app import OpenCodeTokenMeter

class ModelUpdateDialog(QDialog):
    """Dialog to show model pricing updates and let user choose what to update"""
    
    def __init__(self, settings: Settings, new_models: List[str], customized_models: List[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings = settings
        self.new_models = new_models
        self.customized_models = customized_models
        self.selected_models_to_update: List[str] = []
        self.user_choice: Optional[str] = None  # 'update_all', 'keep_all', 'selective'
        self.DEFAULT_SETTINGS = DEFAULT_SETTINGS
        
        # Make dialog non-modal
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)
        
        # Set window icon
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Model Pricing Update")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        # Title and description
        title_label = QLabel("<h2>New Model Pricing Available</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        desc_text = f"""
        <p>A new version of model pricing is available.</p>
        <p><b>New models added:</b> {len(self.new_models)}<br>
        <b>Your customized models:</b> {len(self.customized_models)}</p>
        <p>Please review the changes below and select which models to update.</p>
        """
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # New Models Section
        if self.new_models:
            new_group = QGroupBox("New Models (Will be added automatically)")
            new_layout = QVBoxLayout()
            
            new_table = QTableWidget(len(self.new_models), 4)
            new_table.setHorizontalHeaderLabels(["Model", "Provider", "Request Price", "Status"])
            new_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            
            for i, model_id in enumerate(sorted(self.new_models)):
                default_price = self.DEFAULT_SETTINGS['prices']['models'].get(model_id, {})
                provider = default_price.get('provider', 'unknown')
                request_price = default_price.get('request', 0.0)
                
                new_table.setItem(i, 0, QTableWidgetItem(model_id.split('/')[-1]))
                new_table.setItem(i, 1, QTableWidgetItem(provider))
                new_table.setItem(i, 2, QTableWidgetItem(f"${request_price}"))
                new_table.setItem(i, 3, QTableWidgetItem("Will be added"))
            
            new_layout.addWidget(new_table)
            new_group.setLayout(new_layout)
            layout.addWidget(new_group)
        
        # Customized Models Section
        if self.customized_models:
            cust_group = QGroupBox("Your Customized Models (Select which to update)")
            cust_layout = QVBoxLayout()
            
            cust_table = QTableWidget(len(self.customized_models), 6)
            cust_table.setHorizontalHeaderLabels(["Update", "Model", "Provider", "Your Price", "New Price", "Diff"])
            cust_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            
            self.cust_checkboxes = []
            for i, model_id in enumerate(sorted(self.customized_models)):
                # Checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(False)
                checkbox.stateChanged.connect(lambda state, m=model_id: self.on_model_checkbox_changed(m, state))
                self.cust_checkboxes.append((model_id, checkbox))
                cust_table.setCellWidget(i, 0, checkbox)
                
                # Model info
                user_price = self.settings.get_model_price(model_id) or {}
                default_price = self.DEFAULT_SETTINGS['prices']['models'].get(model_id, {})
                provider = default_price.get('provider', 'unknown')
                user_request = user_price.get('request', 0.0)
                default_request = default_price.get('request', 0.0)
                diff = default_request - user_request
                
                cust_table.setItem(i, 1, QTableWidgetItem(model_id.split('/')[-1]))
                cust_table.setItem(i, 2, QTableWidgetItem(provider))
                cust_table.setItem(i, 3, QTableWidgetItem(f"${user_request}"))
                cust_table.setItem(i, 4, QTableWidgetItem(f"${default_request}"))
                
                diff_text = f"{'+' if diff > 0 else ''}${diff:.4f}" if diff != 0 else "No change"
                diff_item = QTableWidgetItem(diff_text)
                if diff > 0:
                    diff_item.setForeground(Qt.GlobalColor.red)
                elif diff < 0:
                    diff_item.setForeground(Qt.GlobalColor.green)
                cust_table.setItem(i, 5, diff_item)
            
            cust_layout.addWidget(cust_table)
            
            # Select All / Deselect All buttons
            btn_layout = QHBoxLayout()
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(self.select_all_models)
            deselect_all_btn = QPushButton("Deselect All")
            deselect_all_btn.clicked.connect(self.deselect_all_models)
            btn_layout.addWidget(select_all_btn)
            btn_layout.addWidget(deselect_all_btn)
            btn_layout.addStretch()
            cust_layout.addLayout(btn_layout)
            
            cust_group.setLayout(cust_layout)
            layout.addWidget(cust_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.update_all_btn = QPushButton("Update All Models")
        self.update_all_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        self.update_all_btn.clicked.connect(self.on_update_all)
        
        self.update_selected_btn = QPushButton("Update Selected Only")
        self.update_selected_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        self.update_selected_btn.clicked.connect(self.on_update_selected)
        
        self.keep_all_btn = QPushButton("Keep My Custom Prices")
        self.keep_all_btn.setStyleSheet("padding: 10px;")
        self.keep_all_btn.clicked.connect(self.on_keep_all)
        
        button_layout.addWidget(self.update_all_btn)
        button_layout.addWidget(self.update_selected_btn)
        button_layout.addWidget(self.keep_all_btn)
        
        layout.addLayout(button_layout)
        
        # Note
        note_label = QLabel("<i>Note: New models will always be added. Only customized models can be kept or updated.</i>")
        note_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(note_label)
        
        self.setLayout(layout)
    
    def on_model_checkbox_changed(self, model_id, state):
        """Track which customized models user wants to update"""
        if state == Qt.CheckState.Checked.value:
            if model_id not in self.selected_models_to_update:
                self.selected_models_to_update.append(model_id)
        else:
            if model_id in self.selected_models_to_update:
                self.selected_models_to_update.remove(model_id)
    
    def select_all_models(self):
        """Select all customized models"""
        for model_id, checkbox in self.cust_checkboxes:
            checkbox.setChecked(True)
    
    def deselect_all_models(self):
        """Deselect all customized models"""
        for model_id, checkbox in self.cust_checkboxes:
            checkbox.setChecked(False)
    
    def on_update_all(self):
        """User chose to update all models to default pricing"""
        self.user_choice = 'update_all'
        self.accept()
    
    def on_update_selected(self):
        """User chose to update only selected customized models"""
        self.user_choice = 'selective'
        self.accept()
    
    def on_keep_all(self):
        """User chose to keep all custom prices"""
        self.user_choice = 'keep_all'
        self.selected_models_to_update = []
        self.accept()
    
    def get_result(self):
        """Get the user's choice and selected models"""
        return {
            'choice': self.user_choice,
            'selected_models': self.selected_models_to_update
        }
