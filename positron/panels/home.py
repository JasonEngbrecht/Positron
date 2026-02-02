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
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QSpinBox, QGroupBox,
    QSizePolicy
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
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Positron Data Acquisition")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Main controls
        controls_group = self._create_controls_group()
        layout.addWidget(controls_group)
        
        # Statistics display
        stats_group = self._create_statistics_group()
        layout.addWidget(stats_group)
        
        # Preset stop conditions
        presets_group = self._create_presets_group()
        layout.addWidget(presets_group)
        
        # Trigger configuration
        trigger_group = self._create_trigger_group()
        layout.addWidget(trigger_group)
        
        # Waveform display
        waveform_group = self._create_waveform_group()
        layout.addWidget(waveform_group, stretch=1)
    
    def _create_controls_group(self) -> QGroupBox:
        """Create the acquisition control buttons."""
        group = QGroupBox("Acquisition Control")
        layout = QHBoxLayout()
        
        # Start/Pause button (toggle)
        self.start_pause_btn = QPushButton("Start")
        self.start_pause_btn.setMinimumHeight(50)
        self.start_pause_btn.setStyleSheet("QPushButton { font-size: 14pt; font-weight: bold; }")
        self.start_pause_btn.clicked.connect(self._on_start_pause_clicked)
        self._update_start_pause_button()
        layout.addWidget(self.start_pause_btn)
        
        # Restart button
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setMinimumHeight(50)
        self.restart_btn.setStyleSheet("QPushButton { font-size: 14pt; }")
        self.restart_btn.clicked.connect(self._on_restart_clicked)
        self.restart_btn.setEnabled(False)
        layout.addWidget(self.restart_btn)
        
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
        layout = QHBoxLayout()
        
        # Current trigger summary
        self.trigger_summary_label = QLabel()
        self._update_trigger_summary()
        layout.addWidget(self.trigger_summary_label, stretch=1)
        
        # Configure button
        self.configure_trigger_btn = QPushButton("Configure Trigger...")
        self.configure_trigger_btn.clicked.connect(self._on_configure_trigger_clicked)
        layout.addWidget(self.configure_trigger_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_waveform_group(self) -> QGroupBox:
        """Create the waveform display."""
        group = QGroupBox("Live Waveforms")
        layout = QVBoxLayout()
        
        # Create waveform plot widget
        self.waveform_plot = WaveformPlot(
            update_rate_hz=self.app.config.waveform_display_rate
        )
        self.waveform_plot.setMinimumHeight(300)
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
        trigger_config = self.app.config.scope.trigger
        valid_conditions = trigger_config.get_valid_conditions()
        
        if not valid_conditions:
            summary = "No trigger configured"
        else:
            parts = []
            for i, condition in enumerate(valid_conditions, 1):
                channels = " AND ".join(condition.channels)
                parts.append(f"Condition {i}: {channels}")
            summary = " OR ".join(parts)
        
        if trigger_config.auto_trigger_enabled:
            summary += " (Auto-trigger: ON)"
        else:
            summary += " (Auto-trigger: OFF)"
        
        self.trigger_summary_label.setText(summary)
    
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
        self._update_start_pause_button()
        self.restart_btn.setEnabled(False)
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
        self._update_start_pause_button()
        self.restart_btn.setEnabled(True)
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
        self._update_start_pause_button()
        self.restart_btn.setEnabled(False)
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
        self._update_start_pause_button()
        self.restart_btn.setEnabled(True)
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
        
        # Calculate sample interval from sample rate
        sample_rate = config.scope.sample_rate
        sample_interval_ns = 1e9 / sample_rate if sample_rate else 8.0
        
        # Create engine
        self.acquisition_engine = create_acquisition_engine(
            scope_info=scope_info,
            event_storage=self.app.event_storage,
            batch_size=config.default_batch_size,
            sample_count=config.scope.waveform_length,
            pre_trigger_samples=config.scope.pre_trigger_samples,
            sample_interval_ns=sample_interval_ns,
            voltage_range_code=config.scope.voltage_range_code,
            max_adc=scope_info.max_adc,
            cfd_fraction=config.cfd_fraction
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
