"""
Data acquisition engine for PicoScope oscilloscopes using rapid block mode.

This module handles high-speed batch acquisition of triggered waveforms,
designed for event-mode data collection at rates up to 10,000 events/second.
"""

import ctypes
import time
from typing import Optional, Dict, Protocol, Any
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from picosdk.functions import assert_pico_ok, adc2mV
from positron.scope.connection import ScopeInfo


@dataclass
class WaveformBatch:
    """A batch of captured waveforms from rapid block acquisition."""
    time_ns: np.ndarray  # Time array in nanoseconds (relative to trigger)
    waveforms: Dict[str, np.ndarray]  # Channel name -> voltage array (mV)
    num_captures: int  # Number of captures in this batch
    segment_index: int  # Index of the segment shown (for display)


class AcquisitionEngine(Protocol):
    """
    Protocol defining the interface for acquisition engines.
    
    Enables abstraction across PS3000a and PS6000a series.
    """
    
    def start(self) -> None:
        """Start acquisition."""
        ...
    
    def stop(self) -> None:
        """Stop acquisition."""
        ...
    
    def is_running(self) -> bool:
        """Check if acquisition is currently running."""
        ...


class PS3000aAcquisitionEngine(QThread):
    """
    Acquisition engine for PS3000a series oscilloscopes.
    
    Uses rapid block mode to capture batches of triggered waveforms.
    Runs in a separate thread to avoid blocking the UI.
    """
    
    # Signals
    waveform_ready = Signal(WaveformBatch)  # Emitted when new waveforms available
    batch_complete = Signal(int)  # Emitted after each batch (with capture count)
    acquisition_error = Signal(str)  # Emitted on error
    acquisition_finished = Signal()  # Emitted when acquisition stops
    
    def __init__(
        self,
        scope_info: ScopeInfo,
        batch_size: int = 10,
        sample_count: int = 375,
        pre_trigger_samples: int = 125,
        sample_interval_ns: float = 8.0,
        voltage_range_code: int = 7,  # 100 mV range
        max_adc: int = 32512
    ):
        """
        Initialize the acquisition engine.
        
        Args:
            scope_info: Information about the connected scope
            batch_size: Number of captures per batch (rapid block segments)
            sample_count: Total samples per capture
            pre_trigger_samples: Number of pre-trigger samples
            sample_interval_ns: Sample interval in nanoseconds
            voltage_range_code: PicoScope voltage range code (7 = 100 mV)
            max_adc: Maximum ADC count for voltage conversion
        """
        super().__init__()
        
        self.scope_info = scope_info
        self.ps = scope_info.api_module
        self.handle = scope_info.handle
        
        # Acquisition parameters
        self.batch_size = batch_size
        self.sample_count = sample_count
        self.pre_trigger_samples = pre_trigger_samples
        self.post_trigger_samples = sample_count - pre_trigger_samples
        self.sample_interval_ns = sample_interval_ns
        self.voltage_range_code = voltage_range_code
        self.max_adc = max_adc
        
        # State management
        self._mutex = QMutex()
        self._running = False
        self._stop_requested = False
        
        # Buffers (allocated once, reused for all batches)
        self._buffers: Optional[Dict[str, np.ndarray]] = None
        
        # Channel configuration (all 4 channels)
        self._channels = {
            'A': 0,  # PS3000A_CHANNEL_A
            'B': 1,  # PS3000A_CHANNEL_B
            'C': 2,  # PS3000A_CHANNEL_C
            'D': 3,  # PS3000A_CHANNEL_D
        }
        
        # Timebase (calculated from sample interval)
        self._timebase = self._calculate_timebase()
        
        # Statistics
        self.total_captures = 0
    
    def _calculate_timebase(self) -> int:
        """
        Calculate timebase index from sample interval.
        
        For PS3000a with sample interval in ns:
        - Timebase 0-2: Special fast timebases
        - Timebase >= 3: interval = (timebase - 2) * sample_period
        
        Returns:
            Timebase index
        """
        # For 8 ns interval (125 MS/s), timebase = 2
        # For 16 ns interval (62.5 MS/s), timebase = 3
        # This is a simplified calculation - actual timebase should come from configurator
        if self.sample_interval_ns <= 8:
            return 2
        else:
            # Approximate for higher timebases
            return int(self.sample_interval_ns / 8) + 2
    
    def run(self) -> None:
        """
        Main acquisition loop (runs in separate thread).
        
        This method is called automatically when the thread starts.
        """
        try:
            # Setup rapid block mode
            self._setup_rapid_block()
            
            # Allocate buffers
            self._allocate_buffers()
            
            # Register buffers with scope
            self._register_buffers()
            
            # Main acquisition loop
            while True:
                with QMutexLocker(self._mutex):
                    if self._stop_requested:
                        break
                
                # Capture a batch
                success = self._capture_batch()
                
                if not success:
                    # Error occurred or stop requested
                    break
                
                # Small delay to prevent CPU thrashing
                self.msleep(1)
            
        except Exception as e:
            self.acquisition_error.emit(f"Acquisition error: {str(e)}")
        
        finally:
            # Cleanup
            self._cleanup()
            with QMutexLocker(self._mutex):
                self._running = False
            self.acquisition_finished.emit()
    
    def _setup_rapid_block(self) -> None:
        """Configure the scope for rapid block mode."""
        status = {}
        
        # Set up memory segments
        max_samples = ctypes.c_int32(self.sample_count)
        status["MemorySegments"] = self.ps.ps3000aMemorySegments(
            self.handle,
            self.batch_size,
            ctypes.byref(max_samples)
        )
        assert_pico_ok(status["MemorySegments"])
        
        # Set number of captures
        status["SetNoOfCaptures"] = self.ps.ps3000aSetNoOfCaptures(
            self.handle,
            self.batch_size
        )
        assert_pico_ok(status["SetNoOfCaptures"])
    
    def _allocate_buffers(self) -> None:
        """Allocate NumPy arrays for waveform data."""
        self._buffers = {}
        
        # Create buffers for each channel and each segment
        for channel_name in self._channels.keys():
            # Each channel needs batch_size separate buffers (one per segment)
            self._buffers[channel_name] = []
            for segment in range(self.batch_size):
                buffer_max = np.empty(self.sample_count, dtype=np.int16)
                buffer_min = np.empty(self.sample_count, dtype=np.int16)
                self._buffers[channel_name].append((buffer_max, buffer_min))
    
    def _register_buffers(self) -> None:
        """Register all buffers with the scope."""
        status = {}
        
        for channel_name, channel_code in self._channels.items():
            for segment in range(self.batch_size):
                buffer_max, buffer_min = self._buffers[channel_name][segment]
                
                status[f"SetDataBuffers_{channel_name}_{segment}"] = self.ps.ps3000aSetDataBuffers(
                    self.handle,
                    channel_code,
                    buffer_max.ctypes.data,
                    buffer_min.ctypes.data,
                    self.sample_count,
                    segment,
                    0  # PS3000A_RATIO_MODE_NONE
                )
                assert_pico_ok(status[f"SetDataBuffers_{channel_name}_{segment}"])
    
    def _capture_batch(self) -> bool:
        """
        Capture one batch of waveforms.
        
        Returns:
            True if successful, False if error or stop requested
        """
        status = {}
        
        try:
            # Start the block capture
            status["RunBlock"] = self.ps.ps3000aRunBlock(
                self.handle,
                ctypes.c_int32(self.pre_trigger_samples),
                ctypes.c_int32(self.post_trigger_samples),
                ctypes.c_uint32(self._timebase),
                ctypes.c_int16(1),  # oversample (not used)
                None,  # time indisposed
                ctypes.c_uint32(0),  # segment index (0 for rapid block)
                None,  # lpReady callback
                None  # pParameter
            )
            assert_pico_ok(status["RunBlock"])
            
            # Wait for all captures to complete
            ready = ctypes.c_int16(0)
            check = ctypes.c_int16(0)
            
            # Poll until ready (with timeout)
            max_polls = 10000  # ~10 second timeout
            polls = 0
            while ready.value == check.value:
                # Check for stop request
                with QMutexLocker(self._mutex):
                    if self._stop_requested:
                        return False
                
                status["IsReady"] = self.ps.ps3000aIsReady(self.handle, ctypes.byref(ready))
                # Note: ps3000aIsReady returns a status code, but we only care about ready.value
                polls += 1
                if polls > max_polls:
                    self.acquisition_error.emit("Timeout waiting for triggers")
                    return False
                
                # Small delay
                self.msleep(1)
            
            # Retrieve data from all segments
            overflow = (ctypes.c_int16 * self.batch_size)()
            num_samples = ctypes.c_int32(self.sample_count)
            
            status["GetValuesBulk"] = self.ps.ps3000aGetValuesBulk(
                self.handle,
                ctypes.byref(num_samples),
                ctypes.c_uint32(0),  # from segment
                ctypes.c_uint32(self.batch_size - 1),  # to segment
                ctypes.c_uint32(1),  # downsample ratio
                ctypes.c_int32(0),  # downsample ratio mode (none)
                ctypes.byref(overflow)
            )
            assert_pico_ok(status["GetValuesBulk"])
            
            # Convert ADC values to millivolts for display
            # Use the first segment for display (others are counted but not shown)
            waveforms_mv = {}
            max_adc_ctypes = ctypes.c_int16(self.max_adc)
            for channel_name, channel_code in self._channels.items():
                buffer_max, _ = self._buffers[channel_name][0]  # First segment
                waveforms_mv[channel_name] = adc2mV(
                    buffer_max,
                    self.voltage_range_code,
                    max_adc_ctypes
                )
            
            # Create time array in nanoseconds (relative to trigger)
            time_ns = np.arange(self.sample_count) * self.sample_interval_ns
            time_ns -= self.pre_trigger_samples * self.sample_interval_ns  # Trigger at t=0
            
            # Update statistics
            self.total_captures += self.batch_size
            
            # Emit signals
            batch = WaveformBatch(
                time_ns=time_ns,
                waveforms=waveforms_mv,
                num_captures=self.batch_size,
                segment_index=0
            )
            self.waveform_ready.emit(batch)
            self.batch_complete.emit(self.batch_size)
            
            return True
            
        except Exception as e:
            import traceback
            error_details = f"Error capturing batch: {str(e)}\n{traceback.format_exc()}"
            self.acquisition_error.emit(error_details)
            return False
    
    def _cleanup(self) -> None:
        """Clean up resources after acquisition stops."""
        # Stop the scope
        try:
            status = self.ps.ps3000aStop(self.handle)
            assert_pico_ok(status)
        except:
            pass  # Ignore errors during cleanup
    
    def start(self) -> None:
        """Start the acquisition thread."""
        with QMutexLocker(self._mutex):
            if self._running:
                return  # Already running
            
            self._running = True
            self._stop_requested = False
            self.total_captures = 0
        
        # Start the thread (calls run())
        super().start()
    
    def stop(self) -> None:
        """Request the acquisition thread to stop."""
        with QMutexLocker(self._mutex):
            self._stop_requested = True
    
    def is_running(self) -> bool:
        """Check if acquisition is currently active."""
        with QMutexLocker(self._mutex):
            return self._running


class PS6000aAcquisitionEngine(QThread):
    """
    Acquisition engine for PS6000a series oscilloscopes.
    
    Stub implementation for future development.
    """
    
    # Signals
    waveform_ready = Signal(WaveformBatch)
    batch_complete = Signal(int)
    acquisition_error = Signal(str)
    acquisition_finished = Signal()
    
    def __init__(self, scope_info: ScopeInfo, **kwargs):
        """Initialize stub engine."""
        super().__init__()
        self.scope_info = scope_info
        self._running = False
    
    def run(self) -> None:
        """Stub run method."""
        self.acquisition_error.emit("PS6000a acquisition not yet implemented")
        self.acquisition_finished.emit()
    
    def start(self) -> None:
        """Stub start method."""
        self._running = True
        super().start()
    
    def stop(self) -> None:
        """Stub stop method."""
        self._running = False
    
    def is_running(self) -> bool:
        """Check if running."""
        return self._running


def create_acquisition_engine(
    scope_info: ScopeInfo,
    batch_size: int,
    sample_count: int,
    pre_trigger_samples: int,
    sample_interval_ns: float,
    voltage_range_code: int = 7,
    max_adc: Optional[int] = None
) -> AcquisitionEngine:
    """
    Factory function to create the appropriate acquisition engine for the scope series.
    
    Args:
        scope_info: Information about the connected scope
        batch_size: Number of captures per batch
        sample_count: Total samples per capture
        pre_trigger_samples: Number of pre-trigger samples
        sample_interval_ns: Sample interval in nanoseconds
        voltage_range_code: Voltage range code (default: 7 = 100 mV)
        max_adc: Maximum ADC count (uses scope_info.max_adc if None)
    
    Returns:
        Appropriate acquisition engine instance
    
    Raises:
        ValueError: If scope series is not supported
    """
    if max_adc is None:
        max_adc = scope_info.max_adc
    
    if scope_info.series == "3000a":
        return PS3000aAcquisitionEngine(
            scope_info=scope_info,
            batch_size=batch_size,
            sample_count=sample_count,
            pre_trigger_samples=pre_trigger_samples,
            sample_interval_ns=sample_interval_ns,
            voltage_range_code=voltage_range_code,
            max_adc=max_adc
        )
    elif scope_info.series == "6000a":
        return PS6000aAcquisitionEngine(
            scope_info=scope_info,
            batch_size=batch_size,
            sample_count=sample_count,
            pre_trigger_samples=pre_trigger_samples,
            sample_interval_ns=sample_interval_ns,
            voltage_range_code=voltage_range_code,
            max_adc=max_adc
        )
    else:
        raise ValueError(f"Unsupported scope series: {scope_info.series}")
