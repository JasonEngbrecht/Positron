"""
Timing Display panel for visualizing time differences between channel pairs.

Shows up to 4 timing difference histograms on a single plot with:
- User-selectable channel pairs
- Energy filtering for each channel
- Automatic and manual binning
- Auto-update every 2 seconds when visible
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QRadioButton, QComboBox, QDoubleSpinBox,
    QSpinBox, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
import pyqtgraph as pg

from positron.app import PositronApp
from positron.panels.analysis.utils import (
    calculate_timing_differences,
    get_channel_info
)


# Slot colors for different timing curves
SLOT_COLORS = [
    QColor(31, 119, 180),   # Blue
    QColor(255, 127, 14),   # Orange
    QColor(44, 160, 44),    # Green
    QColor(214, 39, 40),    # Red
]


class TimingSlotWidget(QWidget):
    """Widget for configuring a single timing histogram slot (no plot)."""
    
    # Signal emitted when configuration changes
    config_changed = Signal()
    
    def __init__(self, slot_number: int, parent=None):
        """
        Initialize timing slot widget.
        
        Args:
            slot_number: Slot number (1-4)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.slot_number = slot_number
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Create UI elements."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with enable checkbox
        header_layout = QHBoxLayout()
        self.enable_check = QCheckBox(f"Slot {self.slot_number}")
        self.enable_check.setChecked(False)
        self.enable_check.stateChanged.connect(self._on_config_changed)
        header_font = QFont()
        header_font.setBold(True)
        self.enable_check.setFont(header_font)
        header_layout.addWidget(self.enable_check)
        
        # Color indicator
        color = SLOT_COLORS[self.slot_number - 1]
        color_label = QLabel("●")
        color_label.setStyleSheet(f"QLabel {{ color: rgb({color.red()}, {color.green()}, {color.blue()}); font-size: 20pt; }}")
        header_layout.addWidget(color_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Channel selectors
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Ch1:"))
        self.ch1_combo = QComboBox()
        self.ch1_combo.addItems(['None', 'A', 'B', 'C', 'D'])
        self.ch1_combo.currentTextChanged.connect(self._on_config_changed)
        selector_layout.addWidget(self.ch1_combo)
        
        selector_layout.addWidget(QLabel("Ch2:"))
        self.ch2_combo = QComboBox()
        self.ch2_combo.addItems(['None', 'A', 'B', 'C', 'D'])
        self.ch2_combo.currentTextChanged.connect(self._on_config_changed)
        selector_layout.addWidget(self.ch2_combo)
        
        layout.addLayout(selector_layout)
        
        # Energy filters
        filter_grid = QGridLayout()
        
        # Channel 1 energy filter
        filter_grid.addWidget(QLabel("Ch1 (keV):"), 0, 0)
        self.ch1_min_spin = QDoubleSpinBox()
        self.ch1_min_spin.setRange(0.0, 10000.0)
        self.ch1_min_spin.setValue(0.0)
        self.ch1_min_spin.setDecimals(1)
        self.ch1_min_spin.setPrefix("min:")
        self.ch1_min_spin.setMaximumWidth(100)
        self.ch1_min_spin.valueChanged.connect(self._on_config_changed)
        filter_grid.addWidget(self.ch1_min_spin, 0, 1)
        
        self.ch1_max_spin = QDoubleSpinBox()
        self.ch1_max_spin.setRange(0.0, 10000.0)
        self.ch1_max_spin.setValue(2000.0)
        self.ch1_max_spin.setDecimals(1)
        self.ch1_max_spin.setPrefix("max:")
        self.ch1_max_spin.setMaximumWidth(100)
        self.ch1_max_spin.valueChanged.connect(self._on_config_changed)
        filter_grid.addWidget(self.ch1_max_spin, 0, 2)
        
        # Channel 2 energy filter
        filter_grid.addWidget(QLabel("Ch2 (keV):"), 1, 0)
        self.ch2_min_spin = QDoubleSpinBox()
        self.ch2_min_spin.setRange(0.0, 10000.0)
        self.ch2_min_spin.setValue(0.0)
        self.ch2_min_spin.setDecimals(1)
        self.ch2_min_spin.setPrefix("min:")
        self.ch2_min_spin.setMaximumWidth(100)
        self.ch2_min_spin.valueChanged.connect(self._on_config_changed)
        filter_grid.addWidget(self.ch2_min_spin, 1, 1)
        
        self.ch2_max_spin = QDoubleSpinBox()
        self.ch2_max_spin.setRange(0.0, 10000.0)
        self.ch2_max_spin.setValue(2000.0)
        self.ch2_max_spin.setDecimals(1)
        self.ch2_max_spin.setPrefix("max:")
        self.ch2_max_spin.setMaximumWidth(100)
        self.ch2_max_spin.valueChanged.connect(self._on_config_changed)
        filter_grid.addWidget(self.ch2_max_spin, 1, 2)
        
        layout.addLayout(filter_grid)
        
        # Status label
        self.status_label = QLabel("Not configured")
        self.status_label.setStyleSheet("QLabel { font-size: 9pt; color: #666; }")
        layout.addWidget(self.status_label)
    
    def _on_config_changed(self) -> None:
        """Handle configuration change."""
        self.config_changed.emit()
    
    def get_config(self) -> Dict:
        """Get current slot configuration."""
        ch1 = self.ch1_combo.currentText()
        ch2 = self.ch2_combo.currentText()
        
        return {
            'enabled': self.enable_check.isChecked(),
            'channel_1': ch1 if ch1 != 'None' else None,
            'channel_2': ch2 if ch2 != 'None' else None,
            'ch1_energy_min': self.ch1_min_spin.value(),
            'ch1_energy_max': self.ch1_max_spin.value(),
            'ch2_energy_min': self.ch2_min_spin.value(),
            'ch2_energy_max': self.ch2_max_spin.value()
        }
    
    def set_status(self, status: str) -> None:
        """Set the status label text."""
        self.status_label.setText(status)


class TimingDisplayPanel(QWidget):
    """
    Timing Display panel showing time differences between channel pairs.
    
    Displays up to 4 timing difference histograms with energy filtering.
    """
    
    def __init__(self, app: PositronApp, parent=None):
        """
        Initialize the Timing Display panel.
        
        Args:
            app: Positron application instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.app = app
        
        # Binning settings
        self._binning_mode = 'automatic'  # 'automatic' or 'manual'
        self._num_bins = 1000
        self._manual_min_time = -100.0
        self._manual_max_time = 100.0
        self._log_scale = False
        
        # Setup UI
        self._setup_ui()
        
        # Auto-update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.setInterval(2000)  # 2 seconds
    
    def _setup_ui(self) -> None:
        """Create and layout all UI elements."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Timing Display - Time Differences Between Channels")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Configure up to 4 timing difference histograms (all shown on one plot). "
            "Shows (Channel 1 time - Channel 2 time) with energy filtering."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("QLabel { color: #666; padding: 5px; }")
        layout.addWidget(instructions)
        
        # Main plot
        self.plot_widget = self._create_plot_widget()
        layout.addWidget(self.plot_widget, stretch=2)
        
        # Timing slots in horizontal layout
        slots_group = QGroupBox("Slot Configuration")
        slots_layout = QGridLayout()
        
        self.timing_slots = []
        for i in range(4):
            slot = TimingSlotWidget(i + 1)
            slot.config_changed.connect(self._update_display)
            self.timing_slots.append(slot)
            slots_layout.addWidget(slot, i // 2, i % 2)
        
        slots_group.setLayout(slots_layout)
        layout.addWidget(slots_group)
        
        # Global controls
        controls = self._create_controls()
        layout.addWidget(controls)
        
        # Status label
        self.status_label = QLabel("No data available")
        self.status_label.setStyleSheet("QLabel { padding: 5px; }")
        layout.addWidget(self.status_label)
        
        # Store plot items for each slot
        self._plot_items: Dict[int, Optional[pg.PlotDataItem]] = {
            0: None, 1: None, 2: None, 3: None
        }
    
    def _create_plot_widget(self) -> pg.PlotWidget:
        """Create the main PyQtGraph plot widget."""
        plot = pg.PlotWidget()
        plot.setMinimumHeight(400)
        
        # Configure plot
        plot_item = plot.getPlotItem()
        plot_item.setLabel('left', 'Counts')
        plot_item.setLabel('bottom', 'Time Difference', units='ns')
        plot_item.setTitle('Timing Differences')
        plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Disable SI prefix on axes (prevent kns, μns, etc.)
        left_axis = plot_item.getAxis('left')
        left_axis.enableAutoSIPrefix(False)
        bottom_axis = plot_item.getAxis('bottom')
        bottom_axis.enableAutoSIPrefix(False)
        
        # Add legend
        plot.addLegend()
        
        return plot
    
    def _create_controls(self) -> QGroupBox:
        """Create global control widgets."""
        group = QGroupBox("Global Controls")
        layout = QVBoxLayout()
        
        # Log scale checkbox
        log_layout = QHBoxLayout()
        self.log_scale_check = QCheckBox("Logarithmic Y-axis")
        self.log_scale_check.setChecked(False)
        self.log_scale_check.stateChanged.connect(self._on_log_scale_changed)
        log_layout.addWidget(self.log_scale_check)
        log_layout.addStretch()
        layout.addLayout(log_layout)
        
        # Binning mode
        binning_layout = QHBoxLayout()
        binning_layout.addWidget(QLabel("Binning Mode:"))
        
        self.auto_radio = QRadioButton("Automatic (1000 bins)")
        self.auto_radio.setChecked(True)
        self.auto_radio.toggled.connect(self._on_binning_mode_changed)
        binning_layout.addWidget(self.auto_radio)
        
        self.manual_radio = QRadioButton("Manual")
        binning_layout.addWidget(self.manual_radio)
        binning_layout.addStretch()
        layout.addLayout(binning_layout)
        
        # Manual binning controls
        manual_group = QGroupBox("Manual Binning Settings")
        manual_layout = QGridLayout()
        
        manual_layout.addWidget(QLabel("Min Time (ns):"), 0, 0)
        self.min_time_spin = QDoubleSpinBox()
        self.min_time_spin.setRange(-10000.0, 10000.0)
        self.min_time_spin.setValue(-100.0)
        self.min_time_spin.setDecimals(1)
        self.min_time_spin.setSuffix(" ns")
        manual_layout.addWidget(self.min_time_spin, 0, 1)
        
        manual_layout.addWidget(QLabel("Max Time (ns):"), 0, 2)
        self.max_time_spin = QDoubleSpinBox()
        self.max_time_spin.setRange(-10000.0, 10000.0)
        self.max_time_spin.setValue(100.0)
        self.max_time_spin.setDecimals(1)
        self.max_time_spin.setSuffix(" ns")
        manual_layout.addWidget(self.max_time_spin, 0, 3)
        
        manual_layout.addWidget(QLabel("Number of Bins:"), 1, 0)
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(20, 2000)
        self.bins_spin.setValue(1000)
        manual_layout.addWidget(self.bins_spin, 1, 1)
        
        manual_group.setLayout(manual_layout)
        manual_group.setEnabled(False)  # Disabled by default (automatic mode)
        self.manual_controls_group = manual_group
        layout.addWidget(manual_group)
        
        # Update button
        button_layout = QHBoxLayout()
        self.update_button = QPushButton("Update All Histograms")
        self.update_button.clicked.connect(self._update_display)
        button_layout.addWidget(self.update_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
    
    def _on_log_scale_changed(self, state: int) -> None:
        """Handle log scale checkbox change."""
        self._log_scale = (state == Qt.Checked)
        self._update_display()
    
    def _on_binning_mode_changed(self, checked: bool) -> None:
        """Handle binning mode radio button change."""
        if checked:  # Auto radio is checked
            self._binning_mode = 'automatic'
            self.manual_controls_group.setEnabled(False)
        else:
            self._binning_mode = 'manual'
            self.manual_controls_group.setEnabled(True)
        
        self._update_display()
    
    def _update_display(self) -> None:
        """Update all timing histogram displays."""
        # Get events from storage
        event_count = self.app.event_storage.get_count()
        
        if event_count == 0:
            self.status_label.setText("No events in storage. Acquire data in Home panel first.")
            for i, slot in enumerate(self.timing_slots):
                slot.set_status("No data")
                # Clear old plot items
                if self._plot_items[i] is not None:
                    self.plot_widget.removeItem(self._plot_items[i])
                    self._plot_items[i] = None
            return
        
        events = self.app.event_storage.get_all_events()
        
        # Get binning parameters
        if self._binning_mode == 'automatic':
            num_bins = 1000
            time_range = None  # Auto-range
        else:
            num_bins = self.bins_spin.value()
            time_range = (self.min_time_spin.value(), self.max_time_spin.value())
        
        # Update each slot
        active_slots = 0
        status_parts = [f"Total events: {event_count:,}"]
        
        for i, slot in enumerate(self.timing_slots):
            config = slot.get_config()
            
            # Clear old plot item
            if self._plot_items[i] is not None:
                self.plot_widget.removeItem(self._plot_items[i])
                self._plot_items[i] = None
            
            if not config['enabled']:
                slot.set_status("Disabled")
                continue
            
            # Validate configuration
            if config['channel_1'] is None or config['channel_2'] is None:
                slot.set_status("Select both channels")
                continue
            
            if config['channel_1'] == config['channel_2']:
                slot.set_status("⚠ Same channel selected")
                continue
            
            # Check calibration
            ch1_info = get_channel_info(self.app, config['channel_1'])
            ch2_info = get_channel_info(self.app, config['channel_2'])
            
            if not ch1_info['calibrated'] or not ch2_info['calibrated']:
                slot.set_status("⚠ Not calibrated")
                continue
            
            # Calculate timing differences
            time_diffs = calculate_timing_differences(
                events,
                config['channel_1'],
                config['channel_2'],
                ch1_info['calibration'],
                ch2_info['calibration'],
                (config['ch1_energy_min'], config['ch1_energy_max']),
                (config['ch2_energy_min'], config['ch2_energy_max'])
            )
            
            if len(time_diffs) == 0:
                slot.set_status("No events match filters")
                continue
            
            # Calculate histogram
            if time_range is None:
                hist_range = (np.min(time_diffs), np.max(time_diffs))
            else:
                hist_range = time_range
            
            counts, bin_edges = np.histogram(time_diffs, bins=num_bins, range=hist_range)
            
            # Plot on shared plot widget
            color = SLOT_COLORS[i]
            pen = pg.mkPen(color=color, width=2)
            
            label = f"Slot {i+1}: {config['channel_1']}-{config['channel_2']}"
            self._plot_items[i] = self.plot_widget.plot(
                bin_edges,
                counts,
                stepMode=True,
                fillLevel=0,
                brush=None,
                pen=pen,
                name=label
            )
            
            # Update slot status
            slot.set_status(f"Events: {len(time_diffs):,}")
            active_slots += 1
            status_parts.append(f"Slot {i+1}: {len(time_diffs):,}")
        
        # Set log mode
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setLogMode(x=False, y=self._log_scale)
        
        # Update status
        self.status_label.setText(" | ".join(status_parts) + f" | Active: {active_slots}/4")
    
    def showEvent(self, event):
        """Override showEvent to start auto-update when panel becomes visible."""
        super().showEvent(event)
        self._update_display()
        self._update_timer.start()
    
    def hideEvent(self, event):
        """Override hideEvent to stop auto-update when panel is hidden."""
        super().hideEvent(event)
        self._update_timer.stop()
