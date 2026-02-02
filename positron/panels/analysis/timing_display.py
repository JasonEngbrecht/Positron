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
import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QRadioButton, QComboBox, QDoubleSpinBox,
    QSpinBox, QPushButton, QSizePolicy, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
import pyqtgraph as pg

from positron.app import PositronApp
from positron.panels.analysis.utils import (
    calculate_timing_differences,
    get_channel_info
)


# Plot colors for different timing curves
PLOT_COLORS = [
    QColor(31, 119, 180),   # Blue
    QColor(255, 127, 14),   # Orange
    QColor(44, 160, 44),    # Green
    QColor(214, 39, 40),    # Red
]


class TimingPlotWidget(QWidget):
    """Widget for configuring a single timing histogram plot in a compact single-row layout."""
    
    # Signal emitted when configuration changes
    config_changed = Signal()
    
    def __init__(self, plot_number: int, parent=None):
        """
        Initialize timing plot widget.
        
        Args:
            plot_number: Plot number (1-4)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.plot_number = plot_number
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Create UI elements in a single horizontal row."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # Enable checkbox with plot number
        self.enable_check = QCheckBox(f"Plot {self.plot_number}")
        self.enable_check.setChecked(False)
        self.enable_check.stateChanged.connect(self._on_config_changed)
        header_font = QFont()
        header_font.setBold(True)
        self.enable_check.setFont(header_font)
        layout.addWidget(self.enable_check)
        
        # Color indicator
        color = PLOT_COLORS[self.plot_number - 1]
        color_label = QLabel("●")
        color_label.setStyleSheet(f"QLabel {{ color: rgb({color.red()}, {color.green()}, {color.blue()}); font-size: 16pt; }}")
        layout.addWidget(color_label)
        
        # Start channel selector
        layout.addWidget(QLabel("Start:"))
        self.start_combo = QComboBox()
        self.start_combo.addItems(['None', 'A', 'B', 'C', 'D'])
        self.start_combo.currentTextChanged.connect(self._on_config_changed)
        self.start_combo.setMaximumWidth(70)
        layout.addWidget(self.start_combo)
        
        # Start energy range
        self.start_min_spin = QDoubleSpinBox()
        self.start_min_spin.setRange(0.0, 10000.0)
        self.start_min_spin.setValue(0.0)
        self.start_min_spin.setDecimals(0)
        self.start_min_spin.setSuffix(" keV")
        self.start_min_spin.setMaximumWidth(70)
        self.start_min_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self.start_min_spin)
        
        layout.addWidget(QLabel("-"))
        
        self.start_max_spin = QDoubleSpinBox()
        self.start_max_spin.setRange(0.0, 10000.0)
        self.start_max_spin.setValue(2000.0)
        self.start_max_spin.setDecimals(0)
        self.start_max_spin.setSuffix(" keV")
        self.start_max_spin.setMaximumWidth(70)
        self.start_max_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self.start_max_spin)
        
        # Stop channel selector
        layout.addWidget(QLabel("Stop:"))
        self.stop_combo = QComboBox()
        self.stop_combo.addItems(['None', 'A', 'B', 'C', 'D'])
        self.stop_combo.currentTextChanged.connect(self._on_config_changed)
        self.stop_combo.setMaximumWidth(70)
        layout.addWidget(self.stop_combo)
        
        # Stop energy range
        self.stop_min_spin = QDoubleSpinBox()
        self.stop_min_spin.setRange(0.0, 10000.0)
        self.stop_min_spin.setValue(0.0)
        self.stop_min_spin.setDecimals(0)
        self.stop_min_spin.setSuffix(" keV")
        self.stop_min_spin.setMaximumWidth(70)
        self.stop_min_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self.stop_min_spin)
        
        layout.addWidget(QLabel("-"))
        
        self.stop_max_spin = QDoubleSpinBox()
        self.stop_max_spin.setRange(0.0, 10000.0)
        self.stop_max_spin.setValue(2000.0)
        self.stop_max_spin.setDecimals(0)
        self.stop_max_spin.setSuffix(" keV")
        self.stop_max_spin.setMaximumWidth(70)
        self.stop_max_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self.stop_max_spin)
        
        # Status label at the end
        self.status_label = QLabel("Not configured")
        self.status_label.setStyleSheet("QLabel { font-size: 9pt; color: #666; }")
        self.status_label.setMinimumWidth(100)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _on_config_changed(self) -> None:
        """Handle configuration change."""
        self.config_changed.emit()
    
    def get_config(self) -> Dict:
        """Get current plot configuration."""
        start_ch = self.start_combo.currentText()
        stop_ch = self.stop_combo.currentText()
        
        return {
            'enabled': self.enable_check.isChecked(),
            'start_channel': start_ch if start_ch != 'None' else None,
            'stop_channel': stop_ch if stop_ch != 'None' else None,
            'start_energy_min': self.start_min_spin.value(),
            'start_energy_max': self.start_max_spin.value(),
            'stop_energy_min': self.stop_min_spin.value(),
            'stop_energy_max': self.stop_max_spin.value()
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
        
        # Store current histogram data for saving (plot_index -> (bin_centers, counts, config))
        self._current_histogram_data: Dict[int, Tuple[np.ndarray, np.ndarray, Dict]] = {}
        
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
    
    def _setup_ui(self) -> None:
        """Create and layout all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        title = QLabel("Timing Display")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Main plot
        self.plot_widget = self._create_plot_widget()
        layout.addWidget(self.plot_widget, stretch=2)
        
        # Timing plots in vertical layout (4 rows, compact)
        plots_group = QGroupBox("Plot Configuration")
        plots_layout = QVBoxLayout()
        plots_layout.setSpacing(2)
        plots_layout.setContentsMargins(4, 4, 4, 4)
        
        self.timing_plots = []
        for i in range(4):
            plot = TimingPlotWidget(i + 1)
            plot.config_changed.connect(self._update_display)
            self.timing_plots.append(plot)
            plots_layout.addWidget(plot)
        
        plots_group.setLayout(plots_layout)
        layout.addWidget(plots_group)
        
        # Global controls
        controls = self._create_controls()
        layout.addWidget(controls)
        
        # Status label
        self.status_label = QLabel("No data available")
        self.status_label.setStyleSheet("QLabel { padding: 5px; }")
        layout.addWidget(self.status_label)
        
        # Store plot items for each plot
        self._plot_items: Dict[int, Optional[pg.PlotDataItem]] = {
            0: None, 1: None, 2: None, 3: None
        }
    
    def _create_plot_widget(self) -> pg.PlotWidget:
        """Create the main PyQtGraph plot widget."""
        plot = pg.PlotWidget()
        plot.setMinimumHeight(140)
        
        # Configure plot
        plot_item = plot.getPlotItem()
        plot_item.setLabel('left', 'Counts')
        plot_item.setLabel('bottom', 'Time Difference (Stop - Start)', units='ns')
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
        """Create compact global control widgets."""
        group = QGroupBox("Global Controls")
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # First row: Log scale + Binning mode
        first_row = QHBoxLayout()
        self.log_scale_check = QCheckBox("Log Y-axis")
        self.log_scale_check.setChecked(False)
        self.log_scale_check.stateChanged.connect(self._on_log_scale_changed)
        first_row.addWidget(self.log_scale_check)
        
        first_row.addWidget(QLabel(" | Binning:"))
        
        self.auto_radio = QRadioButton("Auto (1000)")
        self.auto_radio.setChecked(True)
        self.auto_radio.toggled.connect(self._on_binning_mode_changed)
        first_row.addWidget(self.auto_radio)
        
        self.manual_radio = QRadioButton("Manual")
        first_row.addWidget(self.manual_radio)
        first_row.addStretch()
        layout.addLayout(first_row)
        
        # Manual binning controls (compact grid)
        manual_layout = QHBoxLayout()
        manual_layout.setSpacing(4)
        
        manual_layout.addWidget(QLabel("Range (ns):"))
        self.min_time_spin = QDoubleSpinBox()
        self.min_time_spin.setRange(-10000.0, 10000.0)
        self.min_time_spin.setValue(-100.0)
        self.min_time_spin.setDecimals(1)
        self.min_time_spin.setMaximumWidth(80)
        manual_layout.addWidget(self.min_time_spin)
        
        manual_layout.addWidget(QLabel("to"))
        self.max_time_spin = QDoubleSpinBox()
        self.max_time_spin.setRange(-10000.0, 10000.0)
        self.max_time_spin.setValue(100.0)
        self.max_time_spin.setDecimals(1)
        self.max_time_spin.setMaximumWidth(80)
        manual_layout.addWidget(self.max_time_spin)
        
        manual_layout.addWidget(QLabel("Bins:"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(20, 2000)
        self.bins_spin.setValue(1000)
        self.bins_spin.setMaximumWidth(80)
        manual_layout.addWidget(self.bins_spin)
        manual_layout.addStretch()
        
        self.manual_controls_layout = manual_layout
        layout.addLayout(manual_layout)
        
        # Enable/disable manual controls based on mode
        self._enable_manual_controls(False)
        
        # Save button
        save_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Histogram")
        self.save_button.clicked.connect(self._save_histogram)
        self.save_button.setStyleSheet("QPushButton { font-weight: bold; }")
        save_layout.addWidget(self.save_button)
        save_layout.addStretch()
        layout.addLayout(save_layout)
        
        # Initial save button state
        self._update_save_button_state()
        
        group.setLayout(layout)
        return group
    
    def _enable_manual_controls(self, enabled: bool) -> None:
        """Enable or disable manual binning controls."""
        self.min_time_spin.setEnabled(enabled)
        self.max_time_spin.setEnabled(enabled)
        self.bins_spin.setEnabled(enabled)
    
    def _on_log_scale_changed(self, state: int) -> None:
        """Handle log scale checkbox change."""
        self._log_scale = (state == 2)  # Qt.CheckState.Checked = 2
        
        # Use native PyQtGraph log mode
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setLogMode(y=self._log_scale)
        
        # Clear all plots first to ensure clean redraw with new mode
        for i in range(4):
            if self._plot_items[i] is not None:
                self.plot_widget.removeItem(self._plot_items[i])
                self._plot_items[i] = None
        
        self._update_display()
    
    def _on_binning_mode_changed(self, checked: bool) -> None:
        """Handle binning mode radio button change."""
        if checked:  # Auto radio is checked
            self._binning_mode = 'automatic'
            self._enable_manual_controls(False)
        else:
            self._binning_mode = 'manual'
            self._enable_manual_controls(True)
        
        self._update_display()
    
    def _update_display(self) -> None:
        """Update all timing histogram displays."""
        # Get events from storage
        event_count = self.app.event_storage.get_count()
        
        if event_count == 0:
            self.status_label.setText("No events in storage. Acquire data in Home panel first.")
            self._current_histogram_data = {}
            for i, plot in enumerate(self.timing_plots):
                plot.set_status("No data")
                # Clear old plot items
                if self._plot_items[i] is not None:
                    self.plot_widget.removeItem(self._plot_items[i])
                    self._plot_items[i] = None
            self._update_save_button_state()
            return
        
        events = self.app.event_storage.get_all_events()
        
        # Clear histogram data
        self._current_histogram_data = {}
        
        # Get binning parameters
        if self._binning_mode == 'automatic':
            num_bins = 1000
            time_range = None  # Auto-range
        else:
            num_bins = self.bins_spin.value()
            time_range = (self.min_time_spin.value(), self.max_time_spin.value())
        
        # Update each plot
        active_plots = 0
        status_parts = [f"Total events: {event_count:,}"]
        
        for i, plot in enumerate(self.timing_plots):
            config = plot.get_config()
            
            # Clear old plot item
            if self._plot_items[i] is not None:
                self.plot_widget.removeItem(self._plot_items[i])
                self._plot_items[i] = None
            
            if not config['enabled']:
                plot.set_status("Disabled")
                continue
            
            # Validate configuration
            if config['start_channel'] is None or config['stop_channel'] is None:
                plot.set_status("Select both channels")
                continue
            
            if config['start_channel'] == config['stop_channel']:
                plot.set_status("⚠ Same channel")
                continue
            
            # Check calibration
            start_info = get_channel_info(self.app, config['start_channel'])
            stop_info = get_channel_info(self.app, config['stop_channel'])
            
            if not start_info['calibrated'] or not stop_info['calibrated']:
                plot.set_status("⚠ Not calibrated")
                continue
            
            # Calculate timing differences (Stop - Start, so we pass stop as channel_1)
            time_diffs = calculate_timing_differences(
                events,
                config['stop_channel'],  # Stop is channel_1 for calculation
                config['start_channel'],  # Start is channel_2 for calculation
                stop_info['calibration'],
                start_info['calibration'],
                (config['stop_energy_min'], config['stop_energy_max']),
                (config['start_energy_min'], config['start_energy_max'])
            )
            
            if len(time_diffs) == 0:
                plot.set_status("No events match filters")
                continue
            
            # Calculate histogram
            if time_range is None:
                hist_range = (np.min(time_diffs), np.max(time_diffs))
            else:
                hist_range = time_range
            
            counts, bin_edges = np.histogram(time_diffs, bins=num_bins, range=hist_range)
            
            # Store histogram data for saving (bin centers and original counts)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            self._current_histogram_data[i] = (bin_centers, counts, config)
            
            # Use original count values (setLogMode handles the log display)
            plot_counts = counts.astype(float)
            
            # For log mode, replace zeros with small value to avoid log(0) issues
            if self._log_scale:
                plot_counts = np.where(plot_counts > 0, plot_counts, 0.5)
            
            # Plot on shared plot widget
            color = PLOT_COLORS[i]
            pen = pg.mkPen(color=color, width=2)
            
            label = f"Plot {i+1}: {config['stop_channel']}-{config['start_channel']}"
            self._plot_items[i] = self.plot_widget.plot(
                bin_edges,
                plot_counts,
                stepMode=True,
                fillLevel=0,
                brush=None,
                pen=pen,
                name=label
            )
            
            # Update plot status
            plot.set_status(f"Events: {len(time_diffs):,}")
            active_plots += 1
            status_parts.append(f"Plot {i+1}: {len(time_diffs):,}")
        
        # Update status
        self.status_label.setText(" | ".join(status_parts) + f" | Active: {active_plots}/4")
        
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
                "No histogram data available to save. Please configure and update plots first."
            )
            return
        
        # Open file dialog
        default_filename = f"timing_histogram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Timing Histogram",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write metadata as comments
                writer.writerow(['# Timing Display - Saved: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([f'# Total Events: {self.app.event_storage.get_count():,}'])
                
                # Binning information
                if self._binning_mode == 'automatic':
                    writer.writerow([f'# Binning: Automatic, 1000 bins'])
                else:
                    writer.writerow([f'# Binning: Manual, {self.bins_spin.value()} bins, {self.min_time_spin.value()}-{self.max_time_spin.value()} ns'])
                
                # Plot information
                for plot_idx in sorted(self._current_histogram_data.keys()):
                    bin_centers, counts, config = self._current_histogram_data[plot_idx]
                    num_events = len(counts[counts > 0]) if len(counts) > 0 else np.sum(counts)
                    writer.writerow([
                        f"# Plot{plot_idx+1}: {config['stop_channel']}-{config['start_channel']}, "
                        f"Energy filters: {config['start_channel']}({config['start_energy_min']:.0f}-{config['start_energy_max']:.0f} keV), "
                        f"{config['stop_channel']}({config['stop_energy_min']:.0f}-{config['stop_energy_max']:.0f} keV), "
                        f"Events: {int(np.sum(counts))}"
                    ])
                
                writer.writerow([])  # Blank line
                
                # Prepare column headers and data
                headers = ['Time_Difference_ns']
                
                # Get all plots that have data
                plot_indices = sorted(self._current_histogram_data.keys())
                
                for plot_idx in plot_indices:
                    headers.append(f'Plot{plot_idx+1}_Counts')
                
                # Write headers
                writer.writerow(headers)
                
                # Write data rows
                if self._current_histogram_data:
                    # Get bin centers from first plot (all should have same binning)
                    first_plot_idx = plot_indices[0]
                    bin_centers = self._current_histogram_data[first_plot_idx][0]
                    num_rows = len(bin_centers)
                    
                    for i in range(num_rows):
                        row = [f"{bin_centers[i]:.2f}"]  # Time difference
                        for plot_idx in plot_indices:
                            _, counts, _ = self._current_histogram_data[plot_idx]
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

