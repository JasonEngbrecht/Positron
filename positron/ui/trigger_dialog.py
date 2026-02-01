"""
Trigger configuration dialog for setting up advanced trigger logic.

Allows users to configure up to 4 trigger conditions with AND/OR logic:
- Each condition can include multiple channels (AND logic)
- Multiple conditions use OR logic
- Auto-trigger timeout can be enabled/disabled
"""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QPushButton, QLabel, QRadioButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt

from positron.config import TriggerConfig, TriggerCondition


class TriggerConditionWidget(QGroupBox):
    """Widget for configuring a single trigger condition."""
    
    def __init__(self, condition_number: int, parent=None):
        """
        Initialize trigger condition widget.
        
        Args:
            condition_number: Condition number (1-4)
            parent: Parent widget
        """
        super().__init__(f"Condition {condition_number}", parent)
        self.condition_number = condition_number
        
        # Create widgets
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        
        # Channel checkboxes
        self.channel_checkboxes = {}
        self.channel_checkboxes['A'] = QCheckBox("Channel A")
        self.channel_checkboxes['B'] = QCheckBox("Channel B")
        self.channel_checkboxes['C'] = QCheckBox("Channel C")
        self.channel_checkboxes['D'] = QCheckBox("Channel D")
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.enabled_checkbox)
        
        # Add AND logic label
        and_label = QLabel("Select channels (AND logic):")
        and_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(and_label)
        
        # Channel checkboxes in a horizontal layout
        channels_layout = QHBoxLayout()
        for channel in ['A', 'B', 'C', 'D']:
            channels_layout.addWidget(self.channel_checkboxes[channel])
        layout.addLayout(channels_layout)
        
        self.setLayout(layout)
        
        # Initially disable channel selection
        self._update_enabled_state()
    
    def _on_enabled_changed(self):
        """Handle enabled checkbox state change."""
        self._update_enabled_state()
    
    def _update_enabled_state(self):
        """Update enabled state of channel checkboxes."""
        enabled = self.enabled_checkbox.isChecked()
        for checkbox in self.channel_checkboxes.values():
            checkbox.setEnabled(enabled)
    
    def set_condition(self, condition: TriggerCondition):
        """
        Set the condition from a TriggerCondition object.
        
        Args:
            condition: Trigger condition to display
        """
        self.enabled_checkbox.setChecked(condition.enabled)
        for channel_name, checkbox in self.channel_checkboxes.items():
            checkbox.setChecked(channel_name in condition.channels)
    
    def get_condition(self) -> TriggerCondition:
        """
        Get the current condition as a TriggerCondition object.
        
        Returns:
            Current trigger condition
        """
        enabled = self.enabled_checkbox.isChecked()
        channels = [
            channel_name
            for channel_name, checkbox in self.channel_checkboxes.items()
            if checkbox.isChecked()
        ]
        return TriggerCondition(enabled=enabled, channels=channels)


class TriggerConfigDialog(QDialog):
    """Dialog for configuring trigger conditions."""
    
    def __init__(self, trigger_config: TriggerConfig, parent=None):
        """
        Initialize trigger configuration dialog.
        
        Args:
            trigger_config: Initial trigger configuration
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Configure Trigger Conditions")
        self.setMinimumWidth(500)
        
        # Store initial config
        self.trigger_config = trigger_config
        
        # Create UI
        self._create_ui()
        
        # Load configuration
        self._load_config(trigger_config)
    
    def _create_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout()
        
        # Info section - hardcoded settings
        info_group = QGroupBox("Hardware Settings (Fixed)")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel("Threshold: -5 mV"))
        info_layout.addWidget(QLabel("Direction: Falling edge (negative pulses)"))
        info_layout.addWidget(QLabel("Hysteresis: 10 ADC counts"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Add separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator1)
        
        # OR logic label
        or_label = QLabel("Configure up to 4 trigger conditions (OR logic between conditions):")
        or_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(or_label)
        
        # Condition widgets
        self.condition_widgets = []
        for i in range(1, 5):
            widget = TriggerConditionWidget(i)
            self.condition_widgets.append(widget)
            layout.addWidget(widget)
        
        # Add separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # Auto-trigger section
        auto_trigger_group = QGroupBox("Auto-Trigger Timeout")
        auto_trigger_layout = QVBoxLayout()
        
        self.auto_trigger_button_group = QButtonGroup(self)
        
        self.auto_trigger_disabled = QRadioButton("Disabled (only trigger on valid pulses)")
        self.auto_trigger_enabled = QRadioButton("Maximum timeout (60 seconds)")
        
        self.auto_trigger_button_group.addButton(self.auto_trigger_disabled, 0)
        self.auto_trigger_button_group.addButton(self.auto_trigger_enabled, 1)
        
        auto_trigger_layout.addWidget(self.auto_trigger_disabled)
        auto_trigger_layout.addWidget(self.auto_trigger_enabled)
        
        auto_trigger_group.setLayout(auto_trigger_layout)
        layout.addWidget(auto_trigger_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.load_defaults_button = QPushButton("Load Defaults")
        self.load_defaults_button.clicked.connect(self._load_defaults)
        buttons_layout.addWidget(self.load_defaults_button)
        
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setDefault(True)
        buttons_layout.addWidget(self.ok_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _load_config(self, config: TriggerConfig):
        """
        Load configuration into UI.
        
        Args:
            config: Trigger configuration to load
        """
        # Load conditions
        conditions = config.get_all_conditions()
        for i, condition in enumerate(conditions):
            self.condition_widgets[i].set_condition(condition)
        
        # Load auto-trigger setting
        if config.auto_trigger_enabled:
            self.auto_trigger_enabled.setChecked(True)
        else:
            self.auto_trigger_disabled.setChecked(True)
    
    def _load_defaults(self):
        """Load default trigger configuration."""
        default_config = TriggerConfig.create_default()
        self._load_config(default_config)
    
    def _on_ok_clicked(self):
        """Handle OK button click."""
        # Validate that at least one condition is valid
        config = self.get_config()
        if not config.has_any_valid_condition():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Configuration",
                "At least one condition must be enabled with channels selected."
            )
            return
        
        self.accept()
    
    def get_config(self) -> TriggerConfig:
        """
        Get the current trigger configuration from the UI.
        
        Returns:
            Current trigger configuration
        """
        config = TriggerConfig()
        
        # Get conditions
        conditions = [widget.get_condition() for widget in self.condition_widgets]
        config.condition_1 = conditions[0]
        config.condition_2 = conditions[1]
        config.condition_3 = conditions[2]
        config.condition_4 = conditions[3]
        
        # Get auto-trigger setting
        config.auto_trigger_enabled = self.auto_trigger_enabled.isChecked()
        
        return config


def show_trigger_config_dialog(trigger_config: TriggerConfig, parent=None) -> Optional[TriggerConfig]:
    """
    Show trigger configuration dialog and return the result.
    
    Args:
        trigger_config: Initial trigger configuration
        parent: Parent widget
        
    Returns:
        Updated trigger configuration if accepted, None if cancelled
    """
    dialog = TriggerConfigDialog(trigger_config, parent)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_config()
    return None
