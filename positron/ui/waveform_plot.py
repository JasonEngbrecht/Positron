"""
Waveform display widget for 4-channel oscilloscope data.

Displays all 4 channels (A, B, C, D) overlaid on a single plot with different colors.
Updates are rate-limited to avoid overwhelming the UI during high-speed acquisition.
"""

from typing import Optional, Dict
import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor


class WaveformPlot(pg.PlotWidget):
    """
    PyQtGraph-based waveform display for 4-channel oscilloscope data.
    
    Features:
    - Overlaid display of 4 channels with distinct colors
    - Time axis in nanoseconds relative to trigger
    - Voltage axis in millivolts
    - Update rate limiting (default 3 Hz)
    - Auto-ranging or fixed scale
    """
    
    # Channel colors (distinct and visible)
    CHANNEL_COLORS = {
        'A': QColor(255, 100, 100),  # Red
        'B': QColor(100, 255, 100),  # Green
        'C': QColor(100, 150, 255),  # Blue
        'D': QColor(255, 200, 100),  # Orange/Yellow
    }
    
    def __init__(self, parent=None, update_rate_hz: float = 3.0):
        """
        Initialize the waveform plot.
        
        Args:
            parent: Parent widget
            update_rate_hz: Maximum display update rate in Hz
        """
        super().__init__(parent)
        
        # Configuration
        self._update_rate_hz = update_rate_hz
        self._min_update_interval = 1.0 / update_rate_hz if update_rate_hz > 0 else 0
        self._last_update_time = 0.0
        
        # Pending data for rate-limited updates
        self._pending_update = False
        self._pending_data: Optional[Dict[str, np.ndarray]] = None
        self._pending_time: Optional[np.ndarray] = None
        
        # Plot curves for each channel
        self._curves: Dict[str, pg.PlotDataItem] = {}
        
        # Setup the plot
        self._setup_plot()
        
        # Timer for pending updates
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._process_pending_update)
        self._update_timer.setInterval(int(self._min_update_interval * 1000))
    
    def _setup_plot(self) -> None:
        """Configure the plot appearance and create curve items."""
        # Get axis items to disable SI prefix
        plot_item = self.getPlotItem()
        
        # Set plot labels without SI prefix scaling
        # Left axis (voltage in mV)
        left_axis = plot_item.getAxis('left')
        left_axis.enableAutoSIPrefix(False)
        plot_item.setLabel('left', 'Voltage (mV)')
        
        # Bottom axis (time in ns)
        bottom_axis = plot_item.getAxis('bottom')
        bottom_axis.enableAutoSIPrefix(False)
        plot_item.setLabel('bottom', 'Time (ns)')
        
        plot_item.setTitle('Live Waveforms')
        
        # Enable grid
        self.showGrid(x=True, y=True, alpha=0.3)
        
        # Add legend
        self.addLegend()
        
        # Create curve items for each channel
        for channel_name in ['A', 'B', 'C', 'D']:
            color = self.CHANNEL_COLORS[channel_name]
            pen = pg.mkPen(color=color, width=1.5)
            curve = self.plot(
                [], [],
                name=f'Channel {channel_name}',
                pen=pen
            )
            self._curves[channel_name] = curve
        
        # Set reasonable default ranges
        self.setXRange(-1000, 2000)  # -1000 to +2000 ns default
        self.setYRange(-50, 50)      # ±50 mV default
        
        # Enable auto-range
        self.enableAutoRange(axis='xy')
    
    def update_waveforms(
        self,
        time_ns: np.ndarray,
        waveforms: Dict[str, np.ndarray],
        force: bool = False
    ) -> None:
        """
        Update the displayed waveforms.
        
        Args:
            time_ns: Time array in nanoseconds (relative to trigger)
            waveforms: Dictionary mapping channel names ('A', 'B', 'C', 'D') to
                      voltage arrays in millivolts
            force: If True, bypass rate limiting and update immediately
        """
        current_time = time.time()
        time_since_last_update = current_time - self._last_update_time
        
        if force or time_since_last_update >= self._min_update_interval:
            # Update immediately
            self._update_plot(time_ns, waveforms)
            self._last_update_time = current_time
            self._pending_update = False
        else:
            # Store for later update
            self._pending_data = waveforms.copy()
            self._pending_time = time_ns.copy()
            
            if not self._pending_update:
                self._pending_update = True
                # Schedule update after minimum interval
                remaining_time = self._min_update_interval - time_since_last_update
                self._update_timer.start(int(remaining_time * 1000))
    
    def _process_pending_update(self) -> None:
        """Process any pending waveform update."""
        self._update_timer.stop()
        
        if self._pending_update and self._pending_data is not None:
            self._update_plot(self._pending_time, self._pending_data)
            self._last_update_time = time.time()
            self._pending_update = False
            self._pending_data = None
            self._pending_time = None
    
    def _update_plot(self, time_ns: np.ndarray, waveforms: Dict[str, np.ndarray]) -> None:
        """
        Actually update the plot curves.
        
        Args:
            time_ns: Time array in nanoseconds
            waveforms: Dictionary of channel waveforms in millivolts
        """
        for channel_name, curve in self._curves.items():
            if channel_name in waveforms:
                voltage_mv = waveforms[channel_name]
                curve.setData(time_ns, voltage_mv)
            else:
                # Clear curve if no data for this channel
                curve.setData([], [])
    
    def clear(self) -> None:
        """Clear all waveform data from the plot."""
        for curve in self._curves.values():
            curve.setData([], [])
    
    def set_update_rate(self, rate_hz: float) -> None:
        """
        Change the maximum update rate.
        
        Args:
            rate_hz: New update rate in Hz (0 = no limit)
        """
        self._update_rate_hz = rate_hz
        self._min_update_interval = 1.0 / rate_hz if rate_hz > 0 else 0
        self._update_timer.setInterval(int(self._min_update_interval * 1000))
