"""
Home panel for Positron application.

Main control interface with:
- Start/Pause toggle button and Restart button
- Live statistics (event count, time, rate)
- Preset stop conditions (time/event limits)
- Trigger configuration access
- Live waveform display
"""

import time
import csv
from datetime import datetime
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QSpinBox, QGroupBox,
    QSizePolicy, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from positron.app import PositronApp
from positron.ui.waveform_plot import WaveformPlot
from positron.scope.acquisition import create_acquisition_engine, WaveformBatch
from positron.ui.trigger_dialog import show_trigger_config_dialog
from positron.scope.trigger import create_trigger_configurator


class HomePanel(QWidget):
    """
    Main control panel for data acquisition.
    
    Provides controls for starting/pausing/restarting acquisition,
    displays live statistics, and shows waveform data.
    """
    
    # Signals
    acquisition_state_changed = Signal(str)  # "stopped", "running", "paused"
    
    def __init__(self, app: PositronApp, parent=None):
        """
        Initialize the home panel.
        
        Args:
            app: Positron application instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.app = app
        self.acquisition_engine: Optional[create_acquisition_engine] = None
        
        # State
        self._state = "stopped"  # "stopped", "running", "paused"
        self._total_events = 0
        self._start_time = 0.0
        self._pause_time = 0.0
        self._total_paused_time = 0.0
        
        # Rate calculation
        self._recent_events = []
        self._rate_window_sec = 5.0
        
        # Setup UI
        self._setup_ui()
        
        # Timers
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_statistics_display)
        self._stats_timer.setInterval(100)  # Update 10 times per second
        
        # Connect to app signals
        self.app.config_changed.connect(self._on_config_changed)
    
    def _setup_ui(self) -> None:
        """Create and layout all UI elements."""
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        title = QLabel("Positron Data Acquisition")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 2)  # Row 0, full width
        
        # Scope information
        scope_info_group = self._create_scope_info_group()
        layout.addWidget(scope_info_group, 1, 0)  # Row 1, left
        
        # Statistics display
        stats_group = self._create_statistics_group()
        layout.addWidget(stats_group, 1, 1)  # Row 1, right
        
        # Trigger configuration
        trigger_group = self._create_trigger_group()
        layout.addWidget(trigger_group, 2, 0)  # Row 2, left
        
        # Preset stop conditions
        presets_group = self._create_presets_group()
        layout.addWidget(presets_group, 2, 1)  # Row 2, right
        
        # Main controls
        controls_group = self._create_controls_group()
        layout.addWidget(controls_group, 3, 0, 1, 2)  # Row 3, full width
        
        # Waveform display
        waveform_group = self._create_waveform_group()
        layout.addWidget(waveform_group, 4, 0, 1, 2)  # Row 4, full width
        layout.setRowStretch(4, 1)  # Make waveform row stretch to fill space
    
    def _create_scope_info_group(self) -> QGroupBox:
        """Create the scope information display."""
        group = QGroupBox("Scope Information")
        layout = QGridLayout()
        
        # Get scope info and config
        scope_info = self.app.scope_info
        config = self.app.config.scope
        
        # Scope model and serial
        layout.addWidget(QLabel("Scope:"), 0, 0)
        scope_model = QLabel(f"{scope_info.variant} (S/N: {scope_info.serial})")
        scope_model.setStyleSheet("font-weight: bold;")
        layout.addWidget(scope_model, 0, 1)
        
        # Sample rate
        layout.addWidget(QLabel("Sample Rate:"), 1, 0)
        sample_rate_label = QLabel(f"{config.sample_rate / 1e6:.2f} MS/s")
        layout.addWidget(sample_rate_label, 1, 1)
        
        # Voltage range
        layout.addWidget(QLabel("Voltage Range:"), 2, 0)
        voltage_label = QLabel("100 mV (all channels)")
        layout.addWidget(voltage_label, 2, 1)
        
        # Enabled channels
        layout.addWidget(QLabel("Channels:"), 3, 0)
        channels_label = QLabel("A, B, C, D enabled (DC coupling)")
        layout.addWidget(channels_label, 3, 1)
        
        # Capture window
        layout.addWidget(QLabel("Capture Window:"), 4, 0)
        total_time_us = config.waveform_length / config.sample_rate * 1e6
        pre_time_us = config.pre_trigger_samples / config.sample_rate * 1e6
        post_time_us = total_time_us - pre_time_us
        capture_label = QLabel(f"{total_time_us:.3f} µs (Pre: {pre_time_us:.3f} µs, Post: {post_time_us:.3f} µs)")
        layout.addWidget(capture_label, 4, 1)
        
        layout.setColumnStretch(1, 1)
        group.setLayout(layout)
        return group
    
    def _create_controls_group(self) -> QGroupBox:
        """Create the acquisition control buttons."""
        group = QGroupBox("Acquisition Control")
        layout = QHBoxLayout()
        
        # Start/Pause button (toggle)
        self.start_pause_btn = QPushButton("Start")
        self.start_pause_btn.setMinimumHeight(40)
        self.start_pause_btn.setStyleSheet("QPushButton { font-size: 14pt; font-weight: bold; }")
        self.start_pause_btn.clicked.connect(self._on_start_pause_clicked)
        self._update_start_pause_button()
        layout.addWidget(self.start_pause_btn)
        
        # Restart button
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setMinimumHeight(40)
        self.restart_btn.setStyleSheet("QPushButton { font-size: 14pt; }")
        self.restart_btn.clicked.connect(self._on_restart_clicked)
        self.restart_btn.setEnabled(False)
        layout.addWidget(self.restart_btn)
        
        # Save button
        self.save_btn = QPushButton("Save Data...")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("QPushButton { font-size: 14pt; }")
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_statistics_group(self) -> QGroupBox:
        """Create the statistics display."""
        group = QGroupBox("Live Statistics")
        layout = QGridLayout()
        
        # Event count
        layout.addWidget(QLabel("Events:"), 0, 0)
        self.event_count_label = QLabel("0")
        count_font = QFont()
        count_font.setPointSize(24)
        count_font.setBold(True)
        self.event_count_label.setFont(count_font)
        self.event_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.event_count_label, 0, 1)
        
        # Elapsed time
        layout.addWidget(QLabel("Time:"), 1, 0)
        self.elapsed_time_label = QLabel("00:00:00")
        time_font = QFont()
        time_font.setPointSize(16)
        self.elapsed_time_label.setFont(time_font)
        self.elapsed_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.elapsed_time_label, 1, 1)
        
        # Acquisition rate
        layout.addWidget(QLabel("Rate:"), 2, 0)
        self.rate_label = QLabel("0.0 events/s")
        rate_font = QFont()
        rate_font.setPointSize(12)
        self.rate_label.setFont(rate_font)
        self.rate_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.rate_label, 2, 1)
        
        layout.setColumnStretch(1, 1)
        group.setLayout(layout)
        return group
    
    def _create_presets_group(self) -> QGroupBox:
        """Create the preset stop conditions."""
        group = QGroupBox("Auto-Stop Conditions")
        layout = QGridLayout()
        
        # Time limit
        self.time_limit_check = QCheckBox("Time Limit:")
        self.time_limit_check.setChecked(self.app.config.time_limit_enabled)
        self.time_limit_check.stateChanged.connect(self._on_preset_changed)
        layout.addWidget(self.time_limit_check, 0, 0)
        
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(1, 86400)  # 1 second to 24 hours
        self.time_limit_spin.setValue(self.app.config.time_limit_seconds)
        self.time_limit_spin.setSuffix(" seconds")
        self.time_limit_spin.valueChanged.connect(self._on_preset_changed)
        layout.addWidget(self.time_limit_spin, 0, 1)
        
        # Event count limit
        self.event_limit_check = QCheckBox("Event Count Limit:")
        self.event_limit_check.setChecked(self.app.config.event_limit_enabled)
        self.event_limit_check.stateChanged.connect(self._on_preset_changed)
        layout.addWidget(self.event_limit_check, 1, 0)
        
        self.event_limit_spin = QSpinBox()
        self.event_limit_spin.setRange(1, 10000000)
        self.event_limit_spin.setValue(self.app.config.event_limit_count)
        self.event_limit_spin.setSuffix(" events")
        self.event_limit_spin.valueChanged.connect(self._on_preset_changed)
        layout.addWidget(self.event_limit_spin, 1, 1)
        
        layout.setColumnStretch(1, 1)
        group.setLayout(layout)
        return group
    
    def _create_trigger_group(self) -> QGroupBox:
        """Create the trigger configuration section."""
        group = QGroupBox("Trigger Configuration")
        self.trigger_group_layout = QVBoxLayout()
        
        # Trigger summary labels will be added dynamically (one per line)
        self.trigger_summary_labels = []
        
        # Configure button (must be created before _update_trigger_summary)
        self.configure_trigger_btn = QPushButton("Configure Trigger...")
        self.configure_trigger_btn.clicked.connect(self._on_configure_trigger_clicked)
        self.trigger_group_layout.addWidget(self.configure_trigger_btn)
        
        # Now add the summary labels (inserted before the button)
        self._update_trigger_summary()
        
        group.setLayout(self.trigger_group_layout)
        return group
    
    def _create_waveform_group(self) -> QGroupBox:
        """Create the waveform display."""
        group = QGroupBox("Live Waveforms")
        layout = QVBoxLayout()
        
        # Create waveform plot widget
        self.waveform_plot = WaveformPlot(
            update_rate_hz=self.app.config.waveform_display_rate
        )
        self.waveform_plot.setMinimumHeight(120)
        self.waveform_plot.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        layout.addWidget(self.waveform_plot)
        
        group.setLayout(layout)
        return group
    
    def _update_start_pause_button(self) -> None:
        """Update the start/pause button appearance based on state."""
        if self._state == "stopped":
            self.start_pause_btn.setText("Start")
            self.start_pause_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; "
                "font-size: 14pt; font-weight: bold; }"
            )
        elif self._state == "running":
            self.start_pause_btn.setText("Pause")
            self.start_pause_btn.setStyleSheet(
                "QPushButton { background-color: #FF9800; color: white; "
                "font-size: 14pt; font-weight: bold; }"
            )
        elif self._state == "paused":
            self.start_pause_btn.setText("Resume")
            self.start_pause_btn.setStyleSheet(
                "QPushButton { background-color: #2196F3; color: white; "
                "font-size: 14pt; font-weight: bold; }"
            )
    
    def _update_trigger_summary(self) -> None:
        """Update the trigger configuration summary display."""
        # Remove old labels
        for label in self.trigger_summary_labels:
            self.trigger_group_layout.removeWidget(label)
            label.deleteLater()
        self.trigger_summary_labels.clear()
        
        trigger_config = self.app.config.scope.trigger
        valid_conditions = trigger_config.get_valid_conditions()
        
        # Build list of lines to display
        lines = []
        if not valid_conditions:
            lines.append("No trigger configured")
        else:
            for i, condition in enumerate(valid_conditions, 1):
                channels = " AND ".join(condition.channels)
                lines.append(f"Condition {i}: {channels}")
        
        # Add auto-trigger status
        if trigger_config.auto_trigger_enabled:
            lines.append("(Auto-trigger: ON)")
        else:
            lines.append("(Auto-trigger: OFF)")
        
        # Create a label for each line and insert before the button
        button_index = self.trigger_group_layout.indexOf(self.configure_trigger_btn)
        for i, line in enumerate(lines):
            label = QLabel(line)
            self.trigger_summary_labels.append(label)
            self.trigger_group_layout.insertWidget(button_index + i, label)
    
    def _on_start_pause_clicked(self) -> None:
        """Handle start/pause button click."""
        if self._state == "stopped":
            self._start_acquisition()
        elif self._state == "running":
            self._pause_acquisition()
        elif self._state == "paused":
            self._resume_acquisition()
    
    def _on_restart_clicked(self) -> None:
        """Handle restart button click - reset counters and start fresh."""
        # Clear event storage
        self.app.event_storage.clear()
        
        # Clear statistics
        self._total_events = 0
        now = time.time()
        self._start_time = now
        self._pause_time = now  # Set to now so pause_duration calculation = 0
        self._total_paused_time = 0.0
        self._recent_events.clear()
        
        # Update display
        self._update_statistics_display()
        # Note: Don't clear waveform plot - new data will overwrite old
        
        # Use the same code path as Resume - if it works for Resume, it works for Restart
        if self._state == "paused":
            self._resume_acquisition()
        elif self._state == "stopped":
            self._start_acquisition()
    
    def _on_save_clicked(self) -> None:
        """Handle save button click - export data to CSV."""
        # Check if there's any data to save
        event_count = self.app.event_storage.get_count()
        if event_count == 0:
            QMessageBox.warning(
                self,
                "No Data",
                "There is no data to save. Please acquire some events first."
            )
            return
        
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"positron_data_{timestamp}.csv"
        
        # Show save dialog
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Data to CSV",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filepath:
            # User cancelled
            return
        
        # Ensure .csv extension
        if not filepath.lower().endswith('.csv'):
            filepath += '.csv'
        
        # Export to CSV
        try:
            self._export_to_csv(filepath)
            QMessageBox.information(
                self,
                "Save Successful",
                f"Successfully saved {event_count:,} events to:\n{filepath}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save data:\n{str(e)}"
            )
    
    def _export_to_csv(self, filepath: str) -> None:
        """
        Export event data to CSV file.
        
        Args:
            filepath: Path to save CSV file
        """
        # Get all events (thread-safe copy)
        events = self.app.event_storage.get_all_events()
        
        # Get configuration for metadata
        config = self.app.config
        scope_info = self.app.scope_info
        scope_config = config.scope
        
        # Open file and write
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            # Write metadata as comments
            f.write(f"# Positron Data Export\n")
            f.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"#\n")
            
            # Scope information
            f.write(f"# Scope Model: {scope_info.variant}\n")
            f.write(f"# Serial Number: {scope_info.serial}\n")
            f.write(f"# Sample Rate: {scope_config.sample_rate / 1e6:.2f} MS/s\n")
            f.write(f"# Voltage Range: 100 mV (all channels)\n")
            
            # Capture window info
            total_time_us = scope_config.waveform_length / scope_config.sample_rate * 1e6
            pre_time_us = scope_config.pre_trigger_samples / scope_config.sample_rate * 1e6
            post_time_us = total_time_us - pre_time_us
            f.write(f"# Capture Window: {total_time_us:.3f} µs (Pre: {pre_time_us:.3f} µs, Post: {post_time_us:.3f} µs)\n")
            f.write(f"#\n")
            
            # Trigger configuration
            trigger_config = scope_config.trigger
            valid_conditions = trigger_config.get_valid_conditions()
            if valid_conditions:
                f.write(f"# Trigger Configuration:\n")
                for i, condition in enumerate(valid_conditions, 1):
                    channels = " AND ".join(condition.channels)
                    f.write(f"#   Condition {i}: {channels}\n")
                if trigger_config.auto_trigger_enabled:
                    f.write(f"#   Auto-trigger: ON\n")
                else:
                    f.write(f"#   Auto-trigger: OFF\n")
            else:
                f.write(f"# Trigger Configuration: None\n")
            f.write(f"#\n")
            
            # Calibration information
            f.write(f"# Calibration Status:\n")
            calibrations = {
                'A': scope_config.calibration_a,
                'B': scope_config.calibration_b,
                'C': scope_config.calibration_c,
                'D': scope_config.calibration_d
            }
            for ch in ['A', 'B', 'C', 'D']:
                calib = calibrations[ch]
                if calib and calib.calibrated:
                    f.write(f"#   Channel {ch}: Calibrated\n")
                    f.write(f"#     Gain: {calib.gain:.6e} keV/(mV·ns)\n")
                    f.write(f"#     Offset: {calib.offset:.6f} keV\n")
                    if calib.calibration_date:
                        f.write(f"#     Date: {calib.calibration_date}\n")
                else:
                    f.write(f"#   Channel {ch}: Not calibrated\n")
            f.write(f"#\n")
            
            # Acquisition statistics
            elapsed = self._get_elapsed_time()
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            avg_rate = len(events) / elapsed if elapsed > 0 else 0
            f.write(f"# Acquisition Statistics:\n")
            f.write(f"#   Total Events: {len(events):,}\n")
            f.write(f"#   Elapsed Time: {hours:02d}:{minutes:02d}:{seconds:02d}\n")
            f.write(f"#   Average Rate: {avg_rate:.1f} events/s\n")
            f.write(f"#\n")
            
            # Create CSV writer
            writer = csv.writer(f)
            
            # Write header row
            header = [
                'A_has_pulse', 'A_timing_ns', 'A_energy_kev',
                'B_has_pulse', 'B_timing_ns', 'B_energy_kev',
                'C_has_pulse', 'C_timing_ns', 'C_energy_kev',
                'D_has_pulse', 'D_timing_ns', 'D_energy_kev'
            ]
            writer.writerow(header)
            
            # Write data rows
            # Create calibration lookup for efficient access
            calibrations = {
                'A': scope_config.calibration_a,
                'B': scope_config.calibration_b,
                'C': scope_config.calibration_c,
                'D': scope_config.calibration_d
            }
            
            for event in events:
                row = []
                for ch in ['A', 'B', 'C', 'D']:
                    pulse = event.channels.get(ch)
                    if pulse:
                        # Has pulse flag
                        row.append('TRUE' if pulse.has_pulse else 'FALSE')
                        
                        # Timing (always write the value)
                        row.append(f"{pulse.timing_ns:.6f}")
                        
                        # Energy (calibrated if available)
                        calib = calibrations[ch]
                        if calib and calib.calibrated:
                            # Apply calibration
                            energy_kev = calib.apply_calibration(pulse.energy)
                            row.append(f"{energy_kev:.6f}")
                        else:
                            # Not calibrated - write N/A
                            row.append('N/A')
                    else:
                        # No pulse data for this channel
                        row.extend(['FALSE', '0.0', 'N/A'])
                
                writer.writerow(row)
    
    def _start_acquisition(self) -> None:
        """Start data acquisition."""
        if not self.app.scope_connected:
            return
        
        # Create acquisition engine if needed or if the old one is stopped
        # (QThread cannot be restarted once finished)
        if self.acquisition_engine is None or not self.acquisition_engine.is_running():
            # Clean up old engine if it exists
            if self.acquisition_engine is not None:
                # Disconnect old signals
                try:
                    self.acquisition_engine.waveform_ready.disconnect()
                    self.acquisition_engine.batch_complete.disconnect()
                    self.acquisition_engine.acquisition_error.disconnect()
                    self.acquisition_engine.acquisition_finished.disconnect()
                except:
                    pass  # Ignore if already disconnected
                self.acquisition_engine = None
            
            # Create fresh acquisition engine
            self._create_acquisition_engine()
        
        # Update state
        self._state = "running"
        self._start_time = time.time()
        self._total_paused_time = 0.0
        self.app.set_acquisition_state("running")
        self._update_start_pause_button()
        self.restart_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.configure_trigger_btn.setEnabled(False)
        self.time_limit_check.setEnabled(False)
        self.time_limit_spin.setEnabled(False)
        self.event_limit_check.setEnabled(False)
        self.event_limit_spin.setEnabled(False)
        
        # Start statistics timer
        self._stats_timer.start()
        
        # Start acquisition
        self.acquisition_engine.start()
        
        # Emit signal
        self.acquisition_state_changed.emit("running")
        self.app.acquisition_started.emit()
    
    def _pause_acquisition(self) -> None:
        """Pause data acquisition."""
        if self.acquisition_engine is None:
            return
        
        # Stop acquisition
        self.acquisition_engine.stop()
        
        # Update state
        self._state = "paused"
        self._pause_time = time.time()
        self.app.set_acquisition_state("paused")
        self._update_start_pause_button()
        self.restart_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.configure_trigger_btn.setEnabled(True)  # Allow trigger changes when paused
        
        # Re-enable preset controls when paused (enable spin boxes regardless of checkbox state)
        self.time_limit_check.setEnabled(True)
        self.time_limit_spin.setEnabled(True)
        self.event_limit_check.setEnabled(True)
        self.event_limit_spin.setEnabled(True)
        
        # Keep statistics timer running (time continues during pause)
        
        # Emit signal
        self.acquisition_state_changed.emit("paused")
        self.app.acquisition_paused.emit()
    
    def _resume_acquisition(self) -> None:
        """Resume data acquisition (adds to previous count)."""
        # Calculate paused duration
        pause_duration = time.time() - self._pause_time
        self._total_paused_time += pause_duration
        
        # Update state
        self._state = "running"
        self.app.set_acquisition_state("running")
        self._update_start_pause_button()
        self.restart_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.configure_trigger_btn.setEnabled(False)  # Disable trigger changes when running
        
        # Disable preset controls during acquisition
        self.time_limit_check.setEnabled(False)
        self.time_limit_spin.setEnabled(False)
        self.event_limit_check.setEnabled(False)
        self.event_limit_spin.setEnabled(False)
        
        # Start statistics timer (in case it was stopped by auto-stop)
        self._stats_timer.start()
        
        # Need to recreate acquisition engine since QThread can't be restarted
        if self.acquisition_engine is not None:
            # Disconnect old signals
            try:
                self.acquisition_engine.waveform_ready.disconnect()
                self.acquisition_engine.batch_complete.disconnect()
                self.acquisition_engine.acquisition_error.disconnect()
                self.acquisition_engine.acquisition_finished.disconnect()
            except:
                pass  # Ignore if already disconnected
            self.acquisition_engine = None
        
        # Create new acquisition engine
        self._create_acquisition_engine()
        
        # Start acquisition
        self.acquisition_engine.start()
        
        # Emit signal
        self.acquisition_state_changed.emit("running")
        self.app.acquisition_resumed.emit()
    
    def _stop_acquisition(self) -> None:
        """Stop acquisition completely (called by auto-stop conditions)."""
        if self.acquisition_engine is not None:
            self.acquisition_engine.stop()
        
        # Update state
        self._state = "paused"  # Go to paused state (not stopped)
        self._pause_time = time.time()
        self.app.set_acquisition_state("paused")
        self._update_start_pause_button()
        self.restart_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.configure_trigger_btn.setEnabled(True)
        
        # Re-enable preset controls (enable spin boxes regardless of checkbox state)
        self.time_limit_check.setEnabled(True)
        self.time_limit_spin.setEnabled(True)
        self.event_limit_check.setEnabled(True)
        self.event_limit_spin.setEnabled(True)
        
        # Stop statistics timer
        self._stats_timer.stop()
        
        # Emit signal
        self.acquisition_state_changed.emit("paused")
        self.app.acquisition_stopped.emit()
    
    def _create_acquisition_engine(self) -> None:
        """Create and configure the acquisition engine."""
        # Get configuration
        config = self.app.config
        scope_info = self.app.scope_info
        
        # Apply trigger configuration to hardware BEFORE creating acquisition engine
        try:
            trigger_configurator = create_trigger_configurator(scope_info)
            trigger_configurator.apply_trigger(config.scope.trigger)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Trigger Configuration Error",
                f"Failed to configure trigger:\n{e}\n\nAcquisition cannot start."
            )
            raise
        
        # Calculate sample interval from sample rate
        sample_rate = config.scope.sample_rate
        sample_interval_ns = 1e9 / sample_rate if sample_rate else 8.0
        
        # Adjust batch size for PS6000 (20 vs 10 for PS3000a)
        batch_size = config.default_batch_size
        if scope_info.series == "6000" and batch_size == 10:
            batch_size = 20  # PS6000 uses larger batches
        
        # Create engine
        self.acquisition_engine = create_acquisition_engine(
            scope_info=scope_info,
            event_storage=self.app.event_storage,
            batch_size=batch_size,
            sample_count=config.scope.waveform_length,
            pre_trigger_samples=config.scope.pre_trigger_samples,
            sample_interval_ns=sample_interval_ns,
            voltage_range_code=config.scope.voltage_range_code,
            max_adc=scope_info.max_adc,
            cfd_fraction=config.cfd_fraction,
            timebase_index=config.scope.timebase_index
        )
        
        # Connect signals
        self.acquisition_engine.waveform_ready.connect(self._on_waveform_ready)
        self.acquisition_engine.batch_complete.connect(self._on_batch_complete)
        self.acquisition_engine.acquisition_error.connect(self._on_acquisition_error)
        self.acquisition_engine.acquisition_finished.connect(self._on_acquisition_finished)
        self.acquisition_engine.storage_warning.connect(self._on_storage_warning)
    
    def _on_waveform_ready(self, batch: WaveformBatch) -> None:
        """Handle new waveform data."""
        # Update waveform display
        self.waveform_plot.update_waveforms(
            time_ns=batch.time_ns,
            waveforms=batch.waveforms,
            force=False
        )
    
    def _on_batch_complete(self, count: int) -> None:
        """Handle completion of a batch."""
        # Update event count
        self._total_events += count
        
        # Track for rate calculation
        self._recent_events.append((time.time(), count))
        
        # Check stop conditions
        self._check_stop_conditions()
    
    def _on_acquisition_error(self, error_msg: str) -> None:
        """Handle acquisition error."""
        print(f"Acquisition error: {error_msg}")
        self._stop_acquisition()
    
    def _on_acquisition_finished(self) -> None:
        """Handle acquisition thread finishing."""
        # This is called when the thread actually stops
        pass
    
    def _on_storage_warning(self, warning_msg: str) -> None:
        """Handle storage warning from acquisition engine."""
        print(f"Storage warning: {warning_msg}")
        # If storage is full, stop acquisition
        if "full" in warning_msg.lower():
            self._stop_acquisition()
    
    def _check_stop_conditions(self) -> None:
        """Check if any auto-stop conditions are met."""
        if self._state != "running":
            return
        
        # Get current event count from storage
        event_count = self.app.event_storage.get_count()
        
        # Check time limit
        if self.time_limit_check.isChecked():
            elapsed = self._get_elapsed_time()
            limit = self.time_limit_spin.value()
            if elapsed >= limit:
                print(f"Time limit reached: {elapsed:.1f}s >= {limit}s")
                self._stop_acquisition()
                return
        
        # Check event count limit
        if self.event_limit_check.isChecked():
            limit = self.event_limit_spin.value()
            if event_count >= limit:
                print(f"Event count limit reached: {event_count} >= {limit}")
                self._stop_acquisition()
                return
    
    def _update_statistics_display(self) -> None:
        """Update the statistics display."""
        # Event count from storage (more accurate than batch counting)
        event_count = self.app.event_storage.get_count()
        self.event_count_label.setText(f"{event_count:,}")
        
        # Elapsed time
        elapsed = self._get_elapsed_time()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        self.elapsed_time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Acquisition rate (calculated from recent batches)
        rate = self._calculate_rate()
        self.rate_label.setText(f"{rate:.1f} events/s")
    
    def _get_elapsed_time(self) -> float:
        """Get total elapsed time in seconds."""
        if self._start_time == 0:
            return 0.0
        
        if self._state == "paused":
            # Frozen at pause time, excluding all previous pauses
            return self._pause_time - self._start_time - self._total_paused_time
        else:
            # Running - subtract paused time
            return time.time() - self._start_time - self._total_paused_time
    
    def _calculate_rate(self) -> float:
        """Calculate recent acquisition rate."""
        # Return 0 when paused
        if self._state != "running":
            return 0.0
        
        if not self._recent_events:
            return 0.0
        
        # Remove old events outside the window
        current_time = time.time()
        cutoff_time = current_time - self._rate_window_sec
        self._recent_events = [
            (t, count) for t, count in self._recent_events
            if t >= cutoff_time
        ]
        
        if not self._recent_events:
            return 0.0
        
        # Calculate rate
        total_events = sum(count for _, count in self._recent_events)
        time_span = current_time - self._recent_events[0][0]
        
        if time_span > 0:
            return total_events / time_span
        else:
            return 0.0
    
    def _on_configure_trigger_clicked(self) -> None:
        """Open trigger configuration dialog."""
        # Show dialog
        new_config = show_trigger_config_dialog(self.app.config.scope.trigger)
        
        if new_config is not None:
            # Update configuration
            self.app.config.scope.trigger = new_config
            
            # Apply to scope
            trigger_configurator = create_trigger_configurator(self.app.scope_info)
            trigger_configurator.apply_trigger(new_config)
            
            # Save configuration
            self.app.save_config()
            
            # Update display
            self._update_trigger_summary()
    
    def _on_preset_changed(self) -> None:
        """Handle changes to preset stop conditions."""
        # Update configuration
        self.app.config.time_limit_enabled = self.time_limit_check.isChecked()
        self.app.config.time_limit_seconds = self.time_limit_spin.value()
        self.app.config.event_limit_enabled = self.event_limit_check.isChecked()
        self.app.config.event_limit_count = self.event_limit_spin.value()
        
        # Save configuration
        self.app.save_config()
    
    def _on_config_changed(self) -> None:
        """Handle configuration changes from other sources."""
        # Update UI to reflect config changes
        self.time_limit_check.setChecked(self.app.config.time_limit_enabled)
        self.time_limit_spin.setValue(self.app.config.time_limit_seconds)
        self.event_limit_check.setChecked(self.app.config.event_limit_enabled)
        self.event_limit_spin.setValue(self.app.config.event_limit_count)
        self._update_trigger_summary()
    
    def cleanup(self) -> None:
        """Clean up resources before closing."""
        # Stop acquisition if running
        if self.acquisition_engine is not None and self.acquisition_engine.is_running():
            self.acquisition_engine.stop()
            self.acquisition_engine.wait(5000)  # Wait up to 5 seconds
        
        # Stop timers
        self._stats_timer.stop()
