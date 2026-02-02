"""
Histogram display widget for energy calibration.

Provides interactive histogram plot with:
- Region selection for peak identification
- Logarithmic/linear y-axis
- Adjustable binning
"""

from typing import Optional, Dict, Tuple
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor


class HistogramPlot(pg.PlotWidget):
    """
    PyQtGraph-based histogram plot for energy calibration.
    
    Features:
    - Histogram display with adjustable binning
    - Two selectable regions for peak identification
    - Linear or logarithmic y-axis
    - Auto-ranging
    """
    
    # Signals
    region_1_changed = Signal(float, float)  # (min, max)
    region_2_changed = Signal(float, float)  # (min, max)
    
    # Region colors
    REGION_1_COLOR = QColor(100, 255, 100, 100)  # Green, semi-transparent
    REGION_2_COLOR = QColor(100, 150, 255, 100)  # Blue, semi-transparent
    
    def __init__(self, parent=None):
        """
        Initialize the histogram plot.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Plot items
        self._histogram_item: Optional[pg.PlotDataItem] = None
        self._region_1: Optional[pg.LinearRegionItem] = None
        self._region_2: Optional[pg.LinearRegionItem] = None
        
        # Data
        self._current_data: Optional[np.ndarray] = None
        self._num_bins = 100
        self._log_scale = False
        
        # Setup the plot
        self._setup_plot()
    
    def _setup_plot(self) -> None:
        """Configure the plot appearance."""
        plot_item = self.getPlotItem()
        
        # Disable SI prefix on axes
        left_axis = plot_item.getAxis('left')
        left_axis.enableAutoSIPrefix(False)
        bottom_axis = plot_item.getAxis('bottom')
        bottom_axis.enableAutoSIPrefix(False)
        
        # Set labels
        plot_item.setLabel('left', 'Counts')
        plot_item.setLabel('bottom', 'Energy (mV·ns)')
        plot_item.setTitle('Energy Histogram')
        
        # Enable grid
        self.showGrid(x=True, y=True, alpha=0.3)
        
        # Create regions (initially hidden)
        self._region_1 = pg.LinearRegionItem(
            values=[0, 100],
            brush=self.REGION_1_COLOR,
            movable=True
        )
        self._region_1.setZValue(-10)  # Behind histogram
        self._region_1.sigRegionChanged.connect(self._on_region_1_changed)
        self._region_1.hide()
        self.addItem(self._region_1)
        
        self._region_2 = pg.LinearRegionItem(
            values=[200, 300],
            brush=self.REGION_2_COLOR,
            movable=True
        )
        self._region_2.setZValue(-10)  # Behind histogram
        self._region_2.sigRegionChanged.connect(self._on_region_2_changed)
        self._region_2.hide()
        self.addItem(self._region_2)
    
    def update_histogram(
        self,
        data: np.ndarray,
        num_bins: Optional[int] = None,
        energy_range: Optional[Tuple[float, float]] = None
    ) -> None:
        """
        Update the histogram display with new data.
        
        Args:
            data: Array of energy values (mV·ns)
            num_bins: Number of bins (if None, uses current setting)
            energy_range: (min, max) energy range (if None, auto-range)
        """
        if len(data) == 0:
            self.clear_histogram()
            return
        
        self._current_data = data
        
        if num_bins is not None:
            self._num_bins = num_bins
        
        # Calculate histogram
        if energy_range is None:
            energy_range = (np.min(data), np.max(data))
        
        hist, bin_edges = np.histogram(data, bins=self._num_bins, range=energy_range)
        
        # Calculate bin centers and widths
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_width = bin_edges[1] - bin_edges[0]
        
        # Remove old histogram
        if self._histogram_item is not None:
            self.removeItem(self._histogram_item)
        
        # Use original count values (setLogMode handles the log display)
        plot_counts = hist.astype(float)
        
        # For log mode, replace zeros with small value to avoid log(0) issues
        if self._log_scale:
            plot_counts = np.where(plot_counts > 0, plot_counts, 0.5)
        
        # Use stepMode plot like energy and timing displays (works with setLogMode)
        pen = pg.mkPen(color='steelblue', width=2)
        self._histogram_item = self.plot(
            bin_edges,
            plot_counts,
            stepMode=True,
            fillLevel=0,
            brush=(70, 130, 180, 100),  # steelblue with transparency
            pen=pen
        )
        
        # Auto-range
        self.enableAutoRange()
    
    def set_log_scale(self, enabled: bool) -> None:
        """
        Enable or disable logarithmic y-axis.
        
        Args:
            enabled: True for log scale, False for linear
        """
        self._log_scale = enabled
        
        # Clear old histogram before changing log mode (BarGraphItem needs this)
        if self._histogram_item is not None:
            self.removeItem(self._histogram_item)
            self._histogram_item = None
        
        # Use native PyQtGraph log mode
        plot_item = self.getPlotItem()
        plot_item.setLogMode(y=enabled)
        
        # Keep axis label as 'Counts' in both modes
        plot_item.setLabel('left', 'Counts')
        
        # Redraw histogram if data exists
        if self._current_data is not None:
            self.update_histogram(self._current_data)
    
    def set_num_bins(self, num_bins: int) -> None:
        """
        Set the number of histogram bins.
        
        Args:
            num_bins: Number of bins
        """
        if num_bins < 10:
            num_bins = 10
        if num_bins > 1000:
            num_bins = 1000
        
        self._num_bins = num_bins
        
        # Redraw histogram if data exists
        if self._current_data is not None:
            self.update_histogram(self._current_data)
    
    def show_region_1(self, show: bool = True) -> None:
        """
        Show or hide region 1.
        
        Args:
            show: True to show, False to hide
        """
        if show:
            self._region_1.show()
        else:
            self._region_1.hide()
    
    def show_region_2(self, show: bool = True) -> None:
        """
        Show or hide region 2.
        
        Args:
            show: True to show, False to hide
        """
        if show:
            self._region_2.show()
        else:
            self._region_2.hide()
    
    def set_region_1(self, min_val: float, max_val: float) -> None:
        """
        Set the bounds of region 1.
        
        Args:
            min_val: Minimum energy value
            max_val: Maximum energy value
        """
        self._region_1.setRegion([min_val, max_val])
        self._region_1.show()
    
    def set_region_2(self, min_val: float, max_val: float) -> None:
        """
        Set the bounds of region 2.
        
        Args:
            min_val: Minimum energy value
            max_val: Maximum energy value
        """
        self._region_2.setRegion([min_val, max_val])
        self._region_2.show()
    
    def get_region_1(self) -> Tuple[float, float]:
        """
        Get the current bounds of region 1.
        
        Returns:
            Tuple of (min, max)
        """
        return tuple(self._region_1.getRegion())
    
    def get_region_2(self) -> Tuple[float, float]:
        """
        Get the current bounds of region 2.
        
        Returns:
            Tuple of (min, max)
        """
        return tuple(self._region_2.getRegion())
    
    def auto_position_regions(self, data: np.ndarray) -> None:
        """
        Automatically position regions based on data distribution.
        
        This is a simple heuristic that places regions around
        likely peak locations. Users can adjust manually.
        
        Args:
            data: Energy values to analyze
        """
        if len(data) == 0:
            return
        
        # Get data range
        min_energy = np.min(data)
        max_energy = np.max(data)
        energy_range = max_energy - min_energy
        
        if energy_range < 0.01:
            return  # Data too narrow
        
        # Position region 1 at lower 1/3 of range
        r1_center = min_energy + energy_range * 0.33
        r1_width = energy_range * 0.15
        self.set_region_1(r1_center - r1_width/2, r1_center + r1_width/2)
        
        # Position region 2 at upper 2/3 of range
        r2_center = min_energy + energy_range * 0.67
        r2_width = energy_range * 0.15
        self.set_region_2(r2_center - r2_width/2, r2_center + r2_width/2)
    
    def _on_region_1_changed(self) -> None:
        """Handle region 1 boundary changes."""
        min_val, max_val = self.get_region_1()
        self.region_1_changed.emit(min_val, max_val)
    
    def _on_region_2_changed(self) -> None:
        """Handle region 2 boundary changes."""
        min_val, max_val = self.get_region_2()
        self.region_2_changed.emit(min_val, max_val)
    
    def clear_histogram(self) -> None:
        """Clear the histogram display."""
        if self._histogram_item is not None:
            self.removeItem(self._histogram_item)
            self._histogram_item = None
        
        self._current_data = None
        self._region_1.hide()
        self._region_2.hide()
    
    def get_current_data(self) -> Optional[np.ndarray]:
        """
        Get the current histogram data.
        
        Returns:
            Current energy data array, or None if no data
        """
        return self._current_data
