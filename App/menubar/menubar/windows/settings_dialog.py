from typing import TYPE_CHECKING, cast, Optional, Any
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QComboBox, QCheckBox, QTabWidget, 
                               QLabel, QPushButton, QMessageBox, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from menubar.settings import DEFAULT_SETTINGS, Settings
from menubar.utils.ui_helpers import get_icon_path

if TYPE_CHECKING:
    from menubar.app import OpenCodeTokenMeter

class SettingsDialog(QDialog):
    """Dialog for editing settings with tabbed interface (non-modal)"""
    
    # Signal emitted when settings are saved
    settings_saved = pyqtSignal()
    
    def __init__(self, settings: Settings, app_instance: "OpenCodeTokenMeter"):
        super().__init__()
        self.settings = settings
        self.app_instance = app_instance
        self.DEFAULT_SETTINGS = DEFAULT_SETTINGS
        
        # Make dialog non-modal
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)
        
        # Set window icon
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(550)
        self.setMinimumHeight(520)
        
        layout = QVBoxLayout()
        
        # Header: Title (left) and Version (right)
        header_layout = QHBoxLayout()
        title = QLabel("OpenCode Token Meter Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        version_label = QLabel(f"Version: {self.settings.get_version()}")
        version_label.setStyleSheet("color: gray; font-size: 11px;")
        header_layout.addWidget(version_label)
        layout.addLayout(header_layout)
        
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
        
        # Populate models
        self._refresh_model_selector()
        
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
        
        # Save/Delete/Reset model buttons
        model_buttons = QHBoxLayout()
        reset_button = QPushButton("Reset All to Default")
        reset_button.setStyleSheet("color: #666;")
        reset_button.clicked.connect(self._reset_all_to_default)
        model_buttons.addWidget(reset_button)
        model_buttons.addStretch()
        self.save_model_button = QPushButton("Save")
        self.save_model_button.clicked.connect(self._save_model_pricing)
        model_buttons.addWidget(self.save_model_button)
        self.delete_model_button = QPushButton("Delete")
        self.delete_model_button.clicked.connect(self._delete_model_pricing)
        model_buttons.addWidget(self.delete_model_button)
        self.reset_model_button = QPushButton("Reset to Default")
        self.reset_model_button.clicked.connect(self._reset_model_pricing)
        model_buttons.addWidget(self.reset_model_button)
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
        
        self.notifications_enabled = QCheckBox()
        self.notifications_enabled.setChecked(settings.get('notifications_enabled', True))
        notif_form.addRow("Enable Notifications:", self.notifications_enabled)
        
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
        
        self.thresholds_enabled = QCheckBox()
        self.thresholds_enabled.setChecked(settings.get('thresholds.enabled', False))
        self.thresholds_enabled.stateChanged.connect(self._on_threshold_enabled_changed)
        notif_form.addRow("Enable Thresholds:", self.thresholds_enabled)
        
        daily_tokens_raw = float(cast(Any, settings.get('thresholds.daily_tokens', 1000000.0)))
        daily_tokens_k = int(daily_tokens_raw / 1000)
        self.daily_tokens = QLineEdit(f"{daily_tokens_k}")
        notif_form.addRow("Daily Token Limit (K):", self.daily_tokens)
        
        self.daily_cost = QLineEdit(str(settings.get('thresholds.daily_cost', 20.0)))
        notif_form.addRow("Daily Cost Limit ($):", self.daily_cost)
        
        monthly_tokens_raw = float(cast(Any, settings.get('thresholds.monthly_tokens', 10000000.0)))
        monthly_tokens_k = int(monthly_tokens_raw / 1000)
        self.monthly_tokens = QLineEdit(f"{monthly_tokens_k}")
        notif_form.addRow("Monthly Token Limit (K):", self.monthly_tokens)
        
        self.monthly_cost = QLineEdit(str(settings.get('thresholds.monthly_cost', 1000.0)))
        notif_form.addRow("Monthly Cost Limit ($):", self.monthly_cost)
        
        self.monthly_reset_day = QLineEdit(str(settings.get('thresholds.monthly_reset_day', 1)))
        notif_form.addRow("Monthly Reset Day (1-31):", self.monthly_reset_day)
        
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
        
        self.refresh_interval = QLineEdit(str(settings.get('refresh_interval', 300)))
        notif_form.addRow("Refresh Interval (seconds):", self.refresh_interval)
        
        notif_layout.addLayout(notif_form)
        notif_layout.addStretch()
        notif_tab.setLayout(notif_layout)
        
        self.tabs.addTab(cost_tab, "Cost Meter")
        self.tabs.addTab(notif_tab, "Notification")
        layout.addWidget(self.tabs)
        
        self._on_threshold_enabled_changed()
        if self.model_selector.count() > 0:
            self.model_selector.setCurrentIndex(0)
        self._on_model_selected()
        
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save && Close")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_model_selected(self):
        """Load selected model's pricing into input fields"""
        model_key = self.model_selector.currentData()
        
        if model_key == "custom":
            self.provider_input.clear()
            self.model_input.clear()
            self.model_input_price.clear()
            self.model_output_price.clear()
            self.model_caching_price.clear()
            self.model_request_price.clear()
            self.provider_input.setEnabled(True)
            self.model_input.setEnabled(True)
            self.delete_model_button.setEnabled(False)
            self.reset_model_button.setEnabled(False)
        else:
            user_models = cast(dict, self.settings.get('prices.models', {}))
            default_prices = self.DEFAULT_SETTINGS.get('prices')
            default_models = default_prices.get('models', {}) if isinstance(default_prices, dict) else {}
            
            if model_key in user_models:
                model_prices = user_models[model_key]
            elif model_key in default_models:
                model_prices = default_models[model_key]
            else:
                model_prices = None
            
            if model_prices:
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
                is_default_model = model_key in default_models
                self.delete_model_button.setEnabled(True)
                self.reset_model_button.setEnabled(is_default_model)
    
    def _save_model_pricing(self):
        """Save current model pricing to settings"""
        try:
            provider = self.provider_input.text().strip()
            model = self.model_input.text().strip()
            if not provider or not model:
                QMessageBox.warning(self, "Error", "Provider and Model are required")
                return
            
            model_key = f"{provider}/{model}"
            prices = {
                'input': float(self.model_input_price.text() or 0.0),
                'output': float(self.model_output_price.text() or 0.0),
                'caching': float(self.model_caching_price.text() or 0.0),
                'request': float(self.model_request_price.text() or 0.0),
                'provider': provider
            }

            self.settings.add_model_price(model_key, prices)
            
            self._refresh_model_selector()
            for i in range(self.model_selector.count()):
                if self.model_selector.itemData(i) == model_key:
                    self.model_selector.setCurrentIndex(i)
                    break
            
            QMessageBox.information(self, "Success", f"Pricing saved for {model_key}")
            self._on_model_selected()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save model pricing: {str(e)}")
    
    def _delete_model_pricing(self):
        """Delete current model pricing or hide a default model"""
        model_key = self.model_selector.currentData()
        if model_key == "custom":
            QMessageBox.warning(self, "Error", "No model selected to delete")
            return
        
        default_prices = self.DEFAULT_SETTINGS.get('prices')
        default_models = default_prices.get('models', {}) if isinstance(default_prices, dict) else {}
        is_default_model = model_key in default_models
        confirm_text = (
            f"Delete {model_key}? This will hide it from the list until you reset all to default."
            if is_default_model
            else f"Delete pricing for {model_key}?"
        )
        
        reply = QMessageBox.question(self, "Confirm", confirm_text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if is_default_model:
                    self.settings.mark_model_deleted(model_key)
                    msg = f"{model_key} has been deleted"
                else:
                    self.settings.delete_model_price(model_key)
                    msg = f"Deleted pricing for {model_key}"
                
                self._refresh_model_selector()
                self.model_selector.setCurrentIndex(0)
                self._on_model_selected()
                QMessageBox.information(self, "Success", msg)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to perform action: {str(e)}")

    def _reset_model_pricing(self):
        """Reset current model pricing to default"""
        model_key = self.model_selector.currentData()
        if model_key == "custom":
            QMessageBox.warning(self, "Error", "No model selected to reset")
            return

        default_prices = self.DEFAULT_SETTINGS.get('prices')
        default_models = default_prices.get('models', {}) if isinstance(default_prices, dict) else {}
        is_default_model = model_key in default_models
        if not is_default_model:
            QMessageBox.warning(self, "Error", "Only default models can be reset")
            return

        confirm_text = f"Reset pricing for {model_key} to default values?"
        reply = QMessageBox.question(self, "Confirm", confirm_text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings.reset_model_to_default(model_key)
                self._refresh_model_selector()
                self.model_selector.setCurrentIndex(0)
                self._on_model_selected()
                QMessageBox.information(self, "Success", f"Pricing for {model_key} has been reset to default")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset model: {str(e)}")
    
    def _reset_all_to_default(self):
        """Reset all model prices to default"""
        reply = QMessageBox.question(self, "Confirm Reset", "This will reset ALL model prices to their default values. Your custom pricing will be lost. Are you sure?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings.reset_all_models_to_default()
                self._refresh_model_selector()
                if self.model_selector.count() > 0:
                    self.model_selector.setCurrentIndex(0)
                    self._on_model_selected()
                QMessageBox.information(self, "Success", "All model prices have been reset to default values.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset prices: {str(e)}")
    
    def _refresh_model_selector(self):
        """Refresh the model selector dropdown with updated (customized) indicators"""
        current_data = self.model_selector.currentData()
        self.model_selector.clear()
        
        user_models = cast(dict, self.settings.get('prices.models', {}))
        default_prices = self.DEFAULT_SETTINGS.get('prices')
        default_models = cast(dict, default_prices.get('models', {}) if isinstance(default_prices, dict) else {})
        deleted_models_raw = self.settings.get('prices.deleted_models', [])
        deleted_models_list = []
        if isinstance(deleted_models_raw, dict):
            deleted_models_list = list(deleted_models_raw.keys())
        elif isinstance(deleted_models_raw, list):
            deleted_models_list = deleted_models_raw
        deleted_models = set(deleted_models_list)
        
        # 1. Add customized default models and non-customized default models
        for model_key in sorted(default_models.keys()):
            if model_key in deleted_models:
                continue
            user_price = cast(Optional[dict], user_models.get(model_key))

            display_text = f"{model_key} (customized)" if user_price else model_key
            self.model_selector.addItem(display_text, model_key)
        
        # 2. Add purely custom models (those in user_models but not in default_models)
        for model_key in sorted(user_models.keys()):
            if model_key not in default_models:
                display_text = f"{model_key} (customized)"
                self.model_selector.addItem(display_text, model_key)
        
        self.model_selector.addItem("+ Add Custom Model...", "custom")
        if current_data:
            for i in range(self.model_selector.count()):
                if self.model_selector.itemData(i) == current_data:
                    self.model_selector.setCurrentIndex(i)
                    break
    
    def _on_threshold_enabled_changed(self):
        """Enable/disable threshold fields based on checkbox state"""
        enabled = self.thresholds_enabled.isChecked()
        self.daily_tokens.setEnabled(enabled)
        self.daily_cost.setEnabled(enabled)
        self.monthly_tokens.setEnabled(enabled)
        self.monthly_cost.setEnabled(enabled)
        self.monthly_reset_day.setEnabled(enabled)
    
    def _do_save(self):
        """Internal method to perform the actual save. Returns True on success, False on error."""
        try:
            self.settings.set('prices.default.input', float(self.input_price.text()))
            self.settings.set('prices.default.output', float(self.output_price.text()))
            self.settings.set('prices.default.caching', float(self.caching_price.text()))
            self.settings.set('prices.default.request', float(self.request_price.text()))
            self.settings.set('notifications_enabled', self.notifications_enabled.isChecked())
            self.settings.set('thresholds.enabled', self.thresholds_enabled.isChecked())
            self.settings.set('thresholds.daily_tokens', int(self.daily_tokens.text()) * 1000)
            self.settings.set('thresholds.daily_cost', float(self.daily_cost.text()))
            self.settings.set('thresholds.monthly_tokens', int(self.monthly_tokens.text()) * 1000)
            self.settings.set('thresholds.monthly_cost', float(self.monthly_cost.text()))
            
            reset_day = int(self.monthly_reset_day.text())
            if reset_day < 1 or reset_day > 31:
                raise ValueError("Monthly reset day must be between 1 and 31")
            self.settings.set('thresholds.monthly_reset_day', reset_day)
            
            refresh_interval = int(self.refresh_interval.text())
            if refresh_interval < 10:
                raise ValueError("Refresh interval must be at least 10 seconds")
            self.settings.set('refresh_interval', refresh_interval)
            
            # Refresh model selector to update (customized) suffixes
            self._refresh_model_selector()
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            return False
    
    def apply_settings(self):
        """Apply settings without closing dialog"""
        if self._do_save():
            self.settings_saved.emit()
    
    def save_settings(self):
        """Save settings and close dialog"""
        if self._do_save():
            self.settings_saved.emit()
            self.close()
