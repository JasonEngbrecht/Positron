"""
Energy Display panel for visualizing calibrated energy histograms.

Shows calibrated energy histograms for all 4 channels with:
- Individual channel enable/disable controls
- Logarithmic/linear Y-axis
- Automatic and manual binning
- Auto-update every 2 seconds when visible
"""

import numpy as np
from typing import Dict, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QRadioButton, QButtonGroup, QDoubleSpinBox,
    QSpinBox, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
import pyqtgraph as pg

from positron.app import PositronApp
from positron.panels.analysis.utils import (
    extract_calibrated_energies,
    get_channel_info,
    CHANNEL_COLORS
)


class EnergyDisplayPanel(QWidget):
    """
    Energy Display panel showing calibrated energy histograms.
    
    Displays overlaid histograms for all 4 channels with user controls
    for enabling/disabling channels and adjusting binning parameters.
    """
    
    def __init__(self, app: PositronApp, parent=None):
        """
        Initialize the Energy Display panel.
        
        Args:
            app: Positron application instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.app = app
        
        # Channel state tracking
        self._channel_enabled: Dict[str, bool] = {
            'A': True,
            'B': True,
            'C': True,
            'D': True
        }
        
        # Plot items for each channel
        self._plot_items: Dict[str, Optional[pg.PlotDataItem]] = {
            'A': None,
            'B': None,
            'C': None,
            'D': None
        }
        
        # Binning settings
        self._binning_mode = 'automatic'  # 'automatic' or 'manual'
        self._num_bins = 1000
        self._manual_min_energy = 0.0
        self._manual_max_energy = 2000.0
        
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
        title = QLabel("Energy Display - Calibrated Energy Histograms")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Displays calibrated energy (keV) for all channels. "
            "Only calibrated channels can be enabled."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("QLabel { color: #666; padding: 5px; }")
        layout.addWidget(instructions)
        
        # Histogram plot
        self.plot_widget = self._create_plot_widget()
        layout.addWidget(self.plot_widget, stretch=2)
        
        # Channel controls
        channel_controls = self._create_channel_controls()
        layout.addWidget(channel_controls)
        
        # Plot controls
        plot_controls = self._create_plot_controls()
        layout.addWidget(plot_controls)
        
        # Status label
        self.status_label = QLabel("No data available")
        self.status_label.setStyleSheet("QLabel { padding: 5px; }")
        layout.addWidget(self.status_label)
    
    def _create_plot_widget(self) -> pg.PlotWidget:
        """Create the PyQtGraph plot widget."""
        plot = pg.PlotWidget()
        plot.setMinimumHeight(400)
        
        # Configure plot
        plot_item = plot.getPlotItem()
        plot_item.setLabel('left', 'Counts')
        plot_item.setLabel('bottom', 'Energy', units='keV')
        plot_item.setTitle('Energy Histogram')
        plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Disable SI prefix on axes (prevent kkeV, MkeV, etc.)
        left_axis = plot_item.getAxis('left')
        left_axis.enableAutoSIPrefix(False)
        bottom_axis = plot_item.getAxis('bottom')
        bottom_axis.enableAutoSIPrefix(False)
        
        # Add legend
        plot.addLegend()
        
        # Set log mode by default
        plot_item.setLogMode(x=False, y=True)
        
        return plot
    
    def _create_channel_controls(self) -> QGroupBox:
        """Create channel enable/disable controls."""
        group = QGroupBox("Channel Selection")
        layout = QGridLayout()
        
        self.channel_checkboxes = {}
        self.channel_status_labels = {}
        
        for i, channel in enumerate(['A', 'B', 'C', 'D']):
            # Checkbox
            checkbox = QCheckBox(f"Channel {channel}")
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, ch=channel: self._on_channel_toggled(ch, state)
            )
            self.channel_checkboxes[channel] = checkbox
            layout.addWidget(checkbox, i // 2, (i % 2) * 2)
            
            # Status label
            status_label = QLabel()
            self.channel_status_labels[channel] = status_label
            layout.addWidget(status_label, i // 2, (i % 2) * 2 + 1)
        
        # Update channel status
        self._update_channel_status()
        
        group.setLayout(layout)
        return group
    
    def _create_plot_controls(self) -> QGroupBox:
        """Create plot control widgets."""
        group = QGroupBox("Plot Controls")
        layout = QVBoxLayout()
        
        # Log scale checkbox
        log_layout = QHBoxLayout()
        self.log_scale_check = QCheckBox("Logarithmic Y-axis")
        self.log_scale_check.setChecked(True)
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
        
        manual_layout.addWidget(QLabel("Min Energy (keV):"), 0, 0)
        self.min_energy_spin = QDoubleSpinBox()
        self.min_energy_spin.setRange(0.0, 10000.0)
        self.min_energy_spin.setValue(0.0)
        self.min_energy_spin.setDecimals(1)
        self.min_energy_spin.setSuffix(" keV")
        manual_layout.addWidget(self.min_energy_spin, 0, 1)
        
        manual_layout.addWidget(QLabel("Max Energy (keV):"), 0, 2)
        self.max_energy_spin = QDoubleSpinBox()
        self.max_energy_spin.setRange(0.0, 10000.0)
        self.max_energy_spin.setValue(2000.0)
        self.max_energy_spin.setDecimals(1)
        self.max_energy_spin.setSuffix(" keV")
        manual_layout.addWidget(self.max_energy_spin, 0, 3)
        
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
        self.update_button = QPushButton("Update Histogram")
        self.update_button.clicked.connect(self._update_display)
        button_layout.addWidget(self.update_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
    
    def _update_channel_status(self) -> None:
        """Update calibration status for all channels."""
        for channel in ['A', 'B', 'C', 'D']:
            info = get_channel_info(self.app, channel)
            checkbox = self.channel_checkboxes[channel]
            status_label = self.channel_status_labels[channel]
            
            if info['calibrated']:
                status_label.setText("✓ Calibrated")
                status_label.setStyleSheet("QLabel { color: green; }")
                checkbox.setEnabled(True)
            else:
                status_label.setText("⚠ Not Calibrated")
                status_label.setStyleSheet("QLabel { color: orange; }")
                checkbox.setEnabled(False)
                checkbox.setChecked(False)
                self._channel_enabled[channel] = False
    
    def _on_channel_toggled(self, channel: str, state: int) -> None:
        """Handle channel checkbox toggle."""
        self._channel_enabled[channel] = (state == Qt.Checked)
        self._update_display()
    
    def _on_log_scale_changed(self, state: int) -> None:
        """Handle log scale checkbox change."""
        log_mode = (state == Qt.Checked)
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setLogMode(x=False, y=log_mode)
    
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
        """Update the histogram display with current data."""
        # Get events from storage
        event_count = self.app.event_storage.get_count()
        
        if event_count == 0:
            self.status_label.setText("No events in storage. Acquire data in Home panel first.")
            return
        
        events = self.app.event_storage.get_all_events()
        
        # Update channel status (in case calibration changed)
        self._update_channel_status()
        
        # Track event counts per channel
        channel_counts = {}
        
        # Clear old plot items
        for channel, plot_item in self._plot_items.items():
            if plot_item is not None:
                self.plot_widget.removeItem(plot_item)
                self._plot_items[channel] = None
        
        # Get binning parameters
        if self._binning_mode == 'automatic':
            num_bins = 1000
            energy_range = None  # Auto-range
        else:
            num_bins = self.bins_spin.value()
            energy_range = (self.min_energy_spin.value(), self.max_energy_spin.value())
        
        # Plot each enabled channel
        for channel in ['A', 'B', 'C', 'D']:
            if not self._channel_enabled[channel]:
                continue
            
            # Get channel info
            info = get_channel_info(self.app, channel)
            if not info['calibrated']:
                continue
            
            # Extract calibrated energies
            energies = extract_calibrated_energies(
                events,
                channel,
                info['calibration']
            )
            
            if len(energies) == 0:
                channel_counts[channel] = 0
                continue
            
            channel_counts[channel] = len(energies)
            
            # Calculate histogram
            if energy_range is None:
                hist_range = (np.min(energies), np.max(energies))
            else:
                hist_range = energy_range
            
            counts, bin_edges = np.histogram(energies, bins=num_bins, range=hist_range)
            
            # For stepMode=True, use bin_edges (N+1) for X and counts (N) for Y
            color = CHANNEL_COLORS[channel]
            pen = pg.mkPen(color=color, width=2)
            
            plot_item = self.plot_widget.plot(
                bin_edges,
                counts,
                stepMode=True,
                fillLevel=0,
                brush=None,
                pen=pen,
                name=f"Channel {channel}"
            )
            
            self._plot_items[channel] = plot_item
        
        # Update status label
        status_parts = [f"Total events: {event_count:,}"]
        for channel in ['A', 'B', 'C', 'D']:
            if channel in channel_counts:
                status_parts.append(f"Ch {channel}: {channel_counts[channel]:,}")
        
        self.status_label.setText(" | ".join(status_parts))
    
    def showEvent(self, event):
        """Override showEvent to start auto-update when panel becomes visible."""
        super().showEvent(event)
        self._update_display()
        self._update_timer.start()
    
    def hideEvent(self, event):
        """Override hideEvent to stop auto-update when panel is hidden."""
        super().hideEvent(event)
        self._update_timer.stop()
