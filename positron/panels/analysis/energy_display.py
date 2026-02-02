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
import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QRadioButton, QButtonGroup, QDoubleSpinBox,
    QSpinBox, QPushButton, QSizePolicy, QFileDialog, QMessageBox
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
        self._log_mode = True  # Start with log mode enabled
        
        # Store current histogram data for saving
        self._current_histogram_data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        
        # Setup UI
        self._setup_ui()
        
        # Auto-update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.setInterval(2000)  # 2 seconds
        
        # Connect to acquisition state signals to enable/disable save button
        self.app.acquisition_paused.connect(self._update_save_button_state)
        self.app.acquisition_stopped.connect(self._update_save_button_state)
        self.app.acquisition_started.connect(self._update_save_button_state)
        self.app.acquisition_resumed.connect(self._update_save_button_state)
        
        # Initial save button state
        self._update_save_button_state()
    
    def _setup_ui(self) -> None:
        """Create and layout all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        title = QLabel("Energy Display - Calibrated Energy Histograms")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
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
        plot.setMinimumHeight(140)
        
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
        
        # Update and Save buttons
        button_layout = QHBoxLayout()
        self.update_button = QPushButton("Update Histogram")
        self.update_button.clicked.connect(self._update_display)
        button_layout.addWidget(self.update_button)
        
        self.save_button = QPushButton("Save Histogram")
        self.save_button.clicked.connect(self._save_histogram)
        self.save_button.setStyleSheet("QPushButton { font-weight: bold; }")
        button_layout.addWidget(self.save_button)
        
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
        self._channel_enabled[channel] = (state == 2)  # Qt.CheckState.Checked = 2
        self._update_display()
    
    def _on_log_scale_changed(self, state: int) -> None:
        """Handle log scale checkbox change."""
        self._log_mode = (state == 2)  # Qt.CheckState.Checked = 2
        
        # Use native PyQtGraph log mode
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setLogMode(y=self._log_mode)
        
        # Trigger a full redraw with updated log mode
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
        """Update the histogram display with current data."""
        # Get events from storage
        event_count = self.app.event_storage.get_count()
        
        if event_count == 0:
            self.status_label.setText("No events in storage. Acquire data in Home panel first.")
            self._current_histogram_data = {}
            return
        
        events = self.app.event_storage.get_all_events()
        
        # Update channel status (in case calibration changed)
        self._update_channel_status()
        
        # Track event counts per channel
        channel_counts = {}
        
        # Clear old plot items and histogram data
        for channel, plot_item_to_remove in self._plot_items.items():
            if plot_item_to_remove is not None:
                self.plot_widget.removeItem(plot_item_to_remove)
                self._plot_items[channel] = None
        
        self._current_histogram_data = {}
        
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
            
            # Store histogram data for saving (bin centers and original counts)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            self._current_histogram_data[channel] = (bin_centers, counts)
            
            # Use original count values (setLogMode handles the log display)
            plot_counts = counts.astype(float)
            
            # For log mode, replace zeros with small value to avoid log(0) issues
            if self._log_mode:
                plot_counts = np.where(plot_counts > 0, plot_counts, 0.5)
            
            # For stepMode=True, use bin_edges (N+1) for X and counts (N) for Y
            color = CHANNEL_COLORS[channel]
            pen = pg.mkPen(color=color, width=2)
            
            plot_item_new = self.plot_widget.plot(
                bin_edges,
                plot_counts,
                stepMode=True,
                fillLevel=0,
                brush=None,
                pen=pen,
                name=f"Channel {channel}"
            )
            
            self._plot_items[channel] = plot_item_new
        
        # Update status label
        status_parts = [f"Total events: {event_count:,}"]
        for channel in ['A', 'B', 'C', 'D']:
            if channel in channel_counts:
                status_parts.append(f"Ch {channel}: {channel_counts[channel]:,}")
        
        self.status_label.setText(" | ".join(status_parts))
        
        # Update save button state
        self._update_save_button_state()
    
    def _update_save_button_state(self) -> None:
        """Update the save button enabled state based on acquisition state."""
        # Save button is only enabled when acquisition is paused or stopped
        is_paused_or_stopped = self.app.acquisition_state in ("paused", "stopped")
        has_data = len(self._current_histogram_data) > 0
        self.save_button.setEnabled(is_paused_or_stopped and has_data)
    
    def _save_histogram(self) -> None:
        """Save the current histogram data to CSV file."""
        if len(self._current_histogram_data) == 0:
            QMessageBox.warning(
                self,
                "No Data",
                "No histogram data available to save. Please update the histogram first."
            )
            return
        
        # Open file dialog
        default_filename = f"energy_histogram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Energy Histogram",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write metadata as comments
                writer.writerow(['# Energy Display - Saved: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([f'# Total Events: {self.app.event_storage.get_count():,}'])
                
                # Binning information
                if self._binning_mode == 'automatic':
                    writer.writerow([f'# Binning: Automatic, 1000 bins'])
                else:
                    writer.writerow([f'# Binning: Manual, {self.bins_spin.value()} bins, {self.min_energy_spin.value()}-{self.max_energy_spin.value()} keV'])
                
                # Channel information
                channels_info = []
                for channel in ['A', 'B', 'C', 'D']:
                    if channel in self._current_histogram_data:
                        channels_info.append(f"{channel} (calibrated)")
                    else:
                        info = get_channel_info(self.app, channel)
                        if info['calibrated']:
                            channels_info.append(f"{channel} (not enabled)")
                        else:
                            channels_info.append(f"{channel} (not calibrated)")
                
                writer.writerow(['# Channels: ' + ', '.join(channels_info)])
                writer.writerow([])  # Blank line
                
                # Prepare column headers and data
                headers = ['Energy_keV']
                data_columns = []
                
                # Get all channels that have data
                channels_with_data = sorted(self._current_histogram_data.keys())
                
                for channel in channels_with_data:
                    headers.append(f'Channel_{channel}_Counts')
                    bin_centers, counts = self._current_histogram_data[channel]
                    data_columns.append((bin_centers, counts))
                
                # Write headers
                writer.writerow(headers)
                
                # Write data rows
                # All channels should have the same number of bins
                if data_columns:
                    num_rows = len(data_columns[0][0])
                    for i in range(num_rows):
                        row = [f"{data_columns[0][0][i]:.2f}"]  # Energy from first channel
                        for bin_centers, counts in data_columns:
                            row.append(f"{int(counts[i])}")
                        writer.writerow(row)
            
            QMessageBox.information(
                self,
                "Save Successful",
                f"Histogram data saved successfully to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save histogram data:\n{str(e)}"
            )
    
    def showEvent(self, event):
        """Override showEvent to start auto-update when panel becomes visible."""
        super().showEvent(event)
        self._update_display()
        self._update_timer.start()
    
    def hideEvent(self, event):
        """Override hideEvent to stop auto-update when panel is hidden."""
        super().hideEvent(event)
        self._update_timer.stop()

