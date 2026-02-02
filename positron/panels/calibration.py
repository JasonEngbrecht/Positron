"""
Calibration panel for energy calibration workflow.

Provides:
- Single acquisition for all 4 channels simultaneously
- Tabbed histograms for individual channel viewing
- Interactive histogram with peak region selection per channel
- Individual calibration calculation and application per channel
"""

import time
from datetime import datetime
from typing import Optional, Dict
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QTabWidget,
    QCheckBox, QLineEdit, QTextEdit, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QShowEvent

from positron.app import PositronApp
from positron.ui.histogram_plot import HistogramPlot
from positron.scope.acquisition import create_acquisition_engine
from positron.calibration.energy import (
    find_peak_center_weighted_mean,
    calculate_two_point_calibration,
    validate_calibration_data,
    get_calibration_summary,
    CalibrationError,
    PEAK_1_KEV,
    PEAK_2_KEV
)


class CalibrationPanel(QWidget):
    """
    Calibration panel for performing energy calibration.
    
    Workflow:
    1. Acquire calibration data for all 4 channels simultaneously using Na-22 source
    2. View each channel's histogram in separate tabs
    3. Select regions around 511 keV and 1275 keV peaks per channel
    4. Calculate calibration parameters individually per channel
    5. Apply and save calibration per channel
    """
    
    # Signals
    calibration_applied = Signal(str)  # channel name
    
    def __init__(self, app: PositronApp, parent=None):
        """
        Initialize the calibration panel.
        
        Args:
            app: Positron application instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.app = app
        
        # Per-channel calibration data
        self._peak_1_raw: Dict[str, Optional[float]] = {'A': None, 'B': None, 'C': None, 'D': None}
        self._peak_2_raw: Dict[str, Optional[float]] = {'A': None, 'B': None, 'C': None, 'D': None}
        self._calculated_gain: Dict[str, Optional[float]] = {'A': None, 'B': None, 'C': None, 'D': None}
        self._calculated_offset: Dict[str, Optional[float]] = {'A': None, 'B': None, 'C': None, 'D': None}
        
        # Setup UI
        self._setup_ui()
        
        # Timer for automatic updates (event count and histograms)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._auto_update)
        self._update_timer.setInterval(2000)  # Update every 2 seconds
    
    def _setup_ui(self) -> None:
        """Create and layout all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        title = QLabel("Energy Calibration - All Channels")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Configure trigger (A OR B OR C OR D) in Home panel, acquire 1000+ events with Na-22, then update histograms below."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("QLabel { color: #666; padding: 2px; }")
        layout.addWidget(instructions)
        
        # Data status group
        status_group = self._create_data_status_group()
        layout.addWidget(status_group)
        
        # Tabbed interface for each channel
        self.channel_tabs = QTabWidget()
        self.channel_tabs.setMinimumHeight(200)
        
        # Create a tab for each channel
        self.channel_widgets = {}
        for channel in ['A', 'B', 'C', 'D']:
            channel_widget = self._create_channel_widget(channel)
            self.channel_widgets[channel] = channel_widget
            self.channel_tabs.addTab(channel_widget, f"Channel {channel}")
        
        layout.addWidget(self.channel_tabs)
        
        # Update initial event count
        self._update_event_count_display()
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def showEvent(self, event):
        """Override showEvent to refresh data when panel becomes visible."""
        super().showEvent(event)
        # Trigger immediate update when panel is shown
        self._auto_update()
        # Start periodic updates
        self._update_timer.start()
    
    def hideEvent(self, event):
        """Override hideEvent to stop updates when panel is hidden."""
        super().hideEvent(event)
        # Stop periodic updates to save resources
        self._update_timer.stop()
    
    def _auto_update(self) -> None:
        """Automatically update event count and histograms."""
        # Update event count display
        self._update_event_count_display()
        
        # Update histograms for all channels if we have data
        count = self.app.event_storage.get_count()
        if count > 0:
            for channel in ['A', 'B', 'C', 'D']:
                self._update_histogram_display(channel)
    
    def _create_data_status_group(self) -> QGroupBox:
        """Create data status display."""
        group = QGroupBox("Calibration Data")
        layout = QHBoxLayout()
        
        # Event count display
        layout.addWidget(QLabel("Events in Storage:"))
        self.event_count_label = QLabel("0")
        self.event_count_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14pt; }")
        layout.addWidget(self.event_count_label)
        
        layout.addWidget(QLabel("(Auto-updates every 2 seconds)"))
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    
    def _update_event_count_display(self) -> None:
        """Update the event count display."""
        count = self.app.event_storage.get_count()
        self.event_count_label.setText(f"{count:,}")
    
    
    def _create_channel_widget(self, channel: str) -> QWidget:
        """
        Create widget for a single channel with histogram and calibration controls.
        
        Args:
            channel: Channel name ('A', 'B', 'C', or 'D')
            
        Returns:
            QWidget containing histogram and controls for this channel
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Calibration status
        status_layout = QHBoxLayout()
        status_label = QLabel(f"Channel {channel} Status:")
        status_layout.addWidget(status_label)
        
        status_value = QLabel()
        status_value.setObjectName(f"status_{channel}")
        status_layout.addWidget(status_value)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Update status
        self._update_channel_status(channel, status_value)
        
        # Histogram
        histogram = HistogramPlot()
        histogram.setMinimumHeight(120)
        histogram.setObjectName(f"histogram_{channel}")
        histogram.set_log_scale(True)  # Default to log scale
        layout.addWidget(histogram)
        
        # Histogram controls
        controls_layout = QHBoxLayout()
        
        log_scale_check = QCheckBox("Log Scale")
        log_scale_check.setObjectName(f"log_{channel}")
        log_scale_check.setChecked(True)  # Default to log scale
        log_scale_check.stateChanged.connect(lambda state, ch=channel: self._on_log_scale_changed(ch, state))
        controls_layout.addWidget(log_scale_check)
        
        controls_layout.addWidget(QLabel("Bins:"))
        bins_spin = QSpinBox()
        bins_spin.setObjectName(f"bins_{channel}")
        bins_spin.setRange(20, 2000)
        bins_spin.setValue(1000)
        bins_spin.valueChanged.connect(lambda value, ch=channel: self._on_bins_changed(ch, value))
        controls_layout.addWidget(bins_spin)
        
        auto_button = QPushButton("Auto-Position Regions")
        auto_button.setObjectName(f"auto_{channel}")
        auto_button.clicked.connect(lambda checked, ch=channel: self._auto_position_regions(ch))
        controls_layout.addWidget(auto_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Peak values and find button
        peak_group = QGroupBox("Step 2: Identify Peaks")
        peak_layout = QHBoxLayout()
        
        peak_layout.addWidget(QLabel(f"Peak 1 ({PEAK_1_KEV:.0f} keV):"))
        peak_1_value = QLineEdit()
        peak_1_value.setObjectName(f"peak1_{channel}")
        peak_1_value.setReadOnly(True)
        peak_1_value.setPlaceholderText("Select region and find peak")
        peak_1_value.setFixedWidth(120)
        peak_layout.addWidget(peak_1_value)
        
        peak_layout.addWidget(QLabel(f"Peak 2 ({PEAK_2_KEV:.0f} keV):"))
        peak_2_value = QLineEdit()
        peak_2_value.setObjectName(f"peak2_{channel}")
        peak_2_value.setReadOnly(True)
        peak_2_value.setPlaceholderText("Select region and find peak")
        peak_2_value.setFixedWidth(120)
        peak_layout.addWidget(peak_2_value)
        
        find_button = QPushButton("Find Peaks from Regions")
        find_button.setObjectName(f"find_{channel}")
        find_button.clicked.connect(lambda checked, ch=channel: self._find_peaks(ch))
        find_button.setEnabled(False)
        peak_layout.addWidget(find_button)
        
        peak_layout.addStretch()
        
        peak_group.setLayout(peak_layout)
        layout.addWidget(peak_group)
        
        # Calibration calculation
        calib_group = QGroupBox("Step 3: Calculate and Apply Calibration")
        calib_layout = QVBoxLayout()
        
        # Parameters
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("Gain:"))
        gain_value = QLineEdit()
        gain_value.setObjectName(f"gain_{channel}")
        gain_value.setReadOnly(True)
        gain_value.setPlaceholderText("keV/(mV·ns)")
        gain_value.setFixedWidth(120)
        params_layout.addWidget(gain_value)
        
        params_layout.addWidget(QLabel("Offset:"))
        offset_value = QLineEdit()
        offset_value.setObjectName(f"offset_{channel}")
        offset_value.setReadOnly(True)
        offset_value.setPlaceholderText("keV")
        offset_value.setFixedWidth(120)
        params_layout.addWidget(offset_value)
        
        params_layout.addStretch()
        
        calib_layout.addLayout(params_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        calc_button = QPushButton(f"Calculate Calibration")
        calc_button.setObjectName(f"calc_{channel}")
        calc_button.clicked.connect(lambda checked, ch=channel: self._calculate_calibration(ch))
        calc_button.setEnabled(False)
        button_layout.addWidget(calc_button)
        
        apply_button = QPushButton(f"Apply Calibration")
        apply_button.setObjectName(f"apply_{channel}")
        apply_button.clicked.connect(lambda checked, ch=channel: self._apply_calibration(ch))
        apply_button.setEnabled(False)
        button_layout.addWidget(apply_button)
        
        reset_button = QPushButton("Reset")
        reset_button.setObjectName(f"reset_{channel}")
        reset_button.clicked.connect(lambda checked, ch=channel: self._reset_calibration(ch))
        button_layout.addWidget(reset_button)
        
        button_layout.addStretch()
        calib_layout.addLayout(button_layout)
        
        # Status text
        status_text = QTextEdit()
        status_text.setObjectName(f"status_text_{channel}")
        status_text.setReadOnly(True)
        status_text.setMaximumHeight(50)
        status_text.setPlaceholderText(f"Channel {channel} calibration summary will appear here...")
        calib_layout.addWidget(status_text)
        
        calib_group.setLayout(calib_layout)
        layout.addWidget(calib_group)
        
        return widget
    
    def _update_channel_status(self, channel: str, label: QLabel) -> None:
        """Update the calibration status label for a channel."""
        calibration = self.app.config.scope.get_calibration(channel)
        
        if calibration.calibrated:
            status = f"✓ Calibrated on {calibration.calibration_date}"
            label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
        else:
            status = "Not calibrated"
            label.setStyleSheet("QLabel { color: gray; }")
        
        label.setText(status)
    
    
    def _get_channel_widget(self, channel: str, widget_name: str) -> Optional[QWidget]:
        """
        Helper to get a widget from a channel's tab.
        
        Args:
            channel: Channel name ('A', 'B', 'C', or 'D')
            widget_name: Object name of the widget
            
        Returns:
            Widget or None if not found
        """
        channel_widget = self.channel_widgets.get(channel)
        if channel_widget:
            return channel_widget.findChild(QWidget, widget_name)
        return None
    
    
    
    def _update_histogram_display(self, channel: str) -> None:
        """Update the histogram with specified channel data."""
        count = self.app.event_storage.get_count()
        if count == 0:
            return
        
        # Get histogram widget
        histogram = self._get_channel_widget(channel, f"histogram_{channel}")
        if not histogram:
            return
        
        # Get all events
        events = self.app.event_storage.get_all_events()
        
        # Extract energies for this channel
        energies = []
        for event in events:
            pulse = event.channels.get(channel)
            if pulse and pulse.has_pulse:
                energies.append(pulse.energy)
        
        if len(energies) == 0:
            status_text = self._get_channel_widget(channel, f"status_text_{channel}")
            if status_text:
                status_text.setPlainText(
                    f"No valid pulses found on channel {channel}.\n\n"
                    f"This could mean:\n"
                    f"- No detector connected to this channel\n"
                    f"- Trigger not configured for this channel\n"
                    f"- No signals detected"
                )
            return
        
        energies = np.array(energies)
        
        # Get bins setting
        bins_spin = self._get_channel_widget(channel, f"bins_{channel}")
        num_bins = bins_spin.value() if bins_spin else 1000
        
        # Update histogram
        histogram.update_histogram(energies, num_bins=num_bins)
        
        # Show regions
        histogram.show_region_1(True)
        histogram.show_region_2(True)
        
        # Enable find peaks button
        find_button = self._get_channel_widget(channel, f"find_{channel}")
        if find_button:
            find_button.setEnabled(True)
        
        status_text = self._get_channel_widget(channel, f"status_text_{channel}")
        if status_text:
            status_text.setPlainText(
                f"Histogram updated with {len(energies):,} pulses from channel {channel}\n"
                f"({len(energies)/count*100:.1f}% of total events)"
            )
    
    def _on_log_scale_changed(self, channel: str, state: int) -> None:
        """Handle log scale checkbox change for a channel."""
        histogram = self._get_channel_widget(channel, f"histogram_{channel}")
        if histogram:
            histogram.set_log_scale(state == Qt.Checked)
    
    def _on_bins_changed(self, channel: str, value: int) -> None:
        """Handle bins spinbox change for a channel."""
        # Auto-update if we have data
        event_count = self.app.event_storage.get_count()
        if event_count > 0:
            self._update_histogram_display(channel)
    
    def _auto_position_regions(self, channel: str) -> None:
        """Automatically position regions on histogram for a channel."""
        histogram = self._get_channel_widget(channel, f"histogram_{channel}")
        if not histogram:
            return
        
        data = histogram.get_current_data()
        if data is None or len(data) == 0:
            QMessageBox.warning(self, "No Data", f"No histogram data for channel {channel}.")
            return
        
        histogram.auto_position_regions(data)
        
        status_text = self._get_channel_widget(channel, f"status_text_{channel}")
        if status_text:
            status_text.setPlainText(
                f"Regions auto-positioned for channel {channel}. Adjust as needed, then find peaks."
            )
    
    
    def _find_peaks(self, channel: str) -> None:
        """Find peak centers in selected regions for a channel."""
        histogram = self._get_channel_widget(channel, f"histogram_{channel}")
        if not histogram:
            return
        
        data = histogram.get_current_data()
        if data is None or len(data) == 0:
            QMessageBox.warning(self, "No Data", f"No histogram data for channel {channel}.")
            return
        
        try:
            # Get region bounds
            r1_min, r1_max = histogram.get_region_1()
            r2_min, r2_max = histogram.get_region_2()
            
            # Find peak centers
            peak_1 = find_peak_center_weighted_mean(data, r1_min, r1_max)
            peak_2 = find_peak_center_weighted_mean(data, r2_min, r2_max)
            
            # Store values
            self._peak_1_raw[channel] = peak_1
            self._peak_2_raw[channel] = peak_2
            
            # Display
            peak_1_widget = self._get_channel_widget(channel, f"peak1_{channel}")
            peak_2_widget = self._get_channel_widget(channel, f"peak2_{channel}")
            if peak_1_widget:
                peak_1_widget.setText(f"{peak_1:.2f}")
            if peak_2_widget:
                peak_2_widget.setText(f"{peak_2:.2f}")
            
            # Enable calculation
            calc_button = self._get_channel_widget(channel, f"calc_{channel}")
            if calc_button:
                calc_button.setEnabled(True)
            
            status_text = self._get_channel_widget(channel, f"status_text_{channel}")
            if status_text:
                status_text.setPlainText(
                    f"Peaks found:\n"
                    f"  Peak 1 ({PEAK_1_KEV:.0f} keV): {peak_1:.2f} mV·ns\n"
                    f"  Peak 2 ({PEAK_2_KEV:.0f} keV): {peak_2:.2f} mV·ns"
                )
            
        except CalibrationError as e:
            QMessageBox.warning(self, "Peak Finding Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error finding peaks:\n{e}")
    
    
    def _calculate_calibration(self, channel: str) -> None:
        """Calculate calibration parameters from peaks for a channel."""
        if self._peak_1_raw[channel] is None or self._peak_2_raw[channel] is None:
            QMessageBox.warning(self, "No Peaks", f"Find peaks for channel {channel} first.")
            return
        
        try:
            # Validate data
            event_count = self.app.event_storage.get_count()
            is_valid, error_msg = validate_calibration_data(
                event_count,
                self._peak_1_raw[channel],
                self._peak_2_raw[channel]
            )
            
            if not is_valid:
                QMessageBox.warning(self, "Validation Error", error_msg)
                return
            
            # Calculate calibration
            gain, offset = calculate_two_point_calibration(
                self._peak_1_raw[channel],
                self._peak_2_raw[channel]
            )
            
            # Store values
            self._calculated_gain[channel] = gain
            self._calculated_offset[channel] = offset
            
            # Display
            gain_widget = self._get_channel_widget(channel, f"gain_{channel}")
            offset_widget = self._get_channel_widget(channel, f"offset_{channel}")
            if gain_widget:
                gain_widget.setText(f"{gain:.6f}")
            if offset_widget:
                offset_widget.setText(f"{offset:.3f}")
            
            # Enable apply button
            apply_button = self._get_channel_widget(channel, f"apply_{channel}")
            if apply_button:
                apply_button.setEnabled(True)
            
            # Show summary
            summary = get_calibration_summary(
                gain, offset,
                self._peak_1_raw[channel], self._peak_2_raw[channel]
            )
            status_text = self._get_channel_widget(channel, f"status_text_{channel}")
            if status_text:
                status_text.setPlainText(summary)
            
        except CalibrationError as e:
            QMessageBox.warning(self, "Calibration Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error calculating calibration:\n{e}")
    
    def _apply_calibration(self, channel: str) -> None:
        """Apply and save calibration for a channel."""
        if self._calculated_gain[channel] is None or self._calculated_offset[channel] is None:
            QMessageBox.warning(self, "No Calibration", f"Calculate calibration for channel {channel} first.")
            return
        
        # Update configuration
        calibration = self.app.config.scope.get_calibration(channel)
        calibration.gain = self._calculated_gain[channel]
        calibration.offset = self._calculated_offset[channel]
        calibration.calibrated = True
        calibration.calibration_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        calibration.peak_1_raw = self._peak_1_raw[channel]
        calibration.peak_2_raw = self._peak_2_raw[channel]
        
        # Save configuration
        self.app.save_config()
        
        # Update UI status
        status_label = self._get_channel_widget(channel, f"status_{channel}")
        if status_label:
            self._update_channel_status(channel, status_label)
        
        # Emit signal
        self.calibration_applied.emit(channel)
        
        QMessageBox.information(
            self,
            "Calibration Applied",
            f"Calibration for channel {channel} has been applied and saved."
        )
    
    def _reset_calibration(self, channel: str) -> None:
        """Reset calibration calculations for a channel."""
        self._reset_peaks(channel)
        self._calculated_gain[channel] = None
        self._calculated_offset[channel] = None
        
        # Clear UI
        gain_widget = self._get_channel_widget(channel, f"gain_{channel}")
        offset_widget = self._get_channel_widget(channel, f"offset_{channel}")
        calc_button = self._get_channel_widget(channel, f"calc_{channel}")
        apply_button = self._get_channel_widget(channel, f"apply_{channel}")
        status_text = self._get_channel_widget(channel, f"status_text_{channel}")
        
        if gain_widget:
            gain_widget.clear()
        if offset_widget:
            offset_widget.clear()
        if calc_button:
            calc_button.setEnabled(False)
        if apply_button:
            apply_button.setEnabled(False)
        if status_text:
            status_text.clear()
    
    def _reset_peaks(self, channel: str) -> None:
        """Reset peak values for a channel."""
        self._peak_1_raw[channel] = None
        self._peak_2_raw[channel] = None
        
        peak_1_widget = self._get_channel_widget(channel, f"peak1_{channel}")
        peak_2_widget = self._get_channel_widget(channel, f"peak2_{channel}")
        
        if peak_1_widget:
            peak_1_widget.clear()
        if peak_2_widget:
            peak_2_widget.clear()

