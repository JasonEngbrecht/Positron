"""
Data acquisition engine for PicoScope oscilloscopes using rapid block mode.

This module handles high-speed batch acquisition of triggered waveforms,
designed for event-mode data collection at rates up to 10,000 events/second.
"""

import logging
import time
from typing import Callable, Optional, Dict, List, Tuple
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from positron.scope.connection import ScopeInfo
from positron.scope.driver import ScopeDriver, create_driver, CHANNEL_MAP
from positron.processing.pulse import analyze_event, EventData
from positron.processing.events import EventStorage


logger = logging.getLogger(__name__)

# Sleep between is_ready() polls. time.sleep() uses a high-resolution timer
# on Windows (measured ~0.6 ms actual for 0.2 ms requested). Do NOT use
# QThread.msleep(1) here: it rounds up to the 15.6 ms scheduler tick and
# cost ~24 ms of dead time per batch (scope disarmed) at 600 events/s.
POLL_INTERVAL_S = 0.0002
TRIGGER_TIMEOUT_S = 10.0


@dataclass
class WaveformBatch:
    """A batch of captured waveforms from rapid block acquisition."""
    time_ns: np.ndarray  # Time array in nanoseconds (relative to trigger)
    waveforms: Dict[str, np.ndarray]  # Channel name -> voltage array (mV)
    num_captures: int  # Number of captures in this batch
    segment_index: int  # Index of the segment shown (for display)


# Full-scale millivolts for each PicoScope range code. Same table (and
# indexing) as picosdk.functions.adc2mV; index 3 = 100 mV on both PS3000a
# and PS6000.
CHANNEL_INPUT_RANGES_MV = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000,
                           10000, 20000, 50000, 100000, 200000]


def adc_to_mv(buffer_adc: np.ndarray, voltage_range_code: int, max_adc: int) -> np.ndarray:
    """
    Convert raw ADC counts to millivolts (vectorized, float64).

    Replaces picosdk.functions.adc2mV, which multiplies each int16 sample by
    the range in a Python loop. Under NumPy >= 2 (NEP 50 promotion) that
    product stays int16 and wraps for any sample beyond ~1 mV, silently
    corrupting every waveform. Widening to float64 first makes the result
    independent of NumPy's promotion rules, and is ~100x faster.

    Args:
        buffer_adc: Raw ADC samples (any integer dtype)
        voltage_range_code: PicoScope range code (index into CHANNEL_INPUT_RANGES_MV)
        max_adc: Full-scale ADC count for this scope (e.g. 32512 on PS6000)

    Returns:
        float64 array of the same shape, in millivolts
    """
    range_mv = CHANNEL_INPUT_RANGES_MV[voltage_range_code]
    return np.asarray(buffer_adc, dtype=np.float64) * (range_mv / max_adc)


class BatchTimingStats:
    """
    Accumulates per-batch phase timings and emits a one-line summary every
    `interval_s` seconds of wall time.

    Phases per batch:
      wait     - run_block issued -> scope reports ready (trigger wait, plus
                 any ready-detection latency from the poll loop's sleep)
      download - get_values_bulk
      process  - ADC->mV, pulse analysis, storage append
      other    - everything else in the loop (signal emission, post-batch
                 sleep, Python overhead); derived as wall - sum(phases)
    """

    def __init__(self, interval_s: float = 5.0,
                 clock: Callable[[], float] = time.perf_counter):
        self.interval_s = interval_s
        self._clock = clock
        self._reset(self._clock())

    def _reset(self, now: float) -> None:
        self._window_start = now
        self._batches = 0
        self._captures = 0
        self._wait = 0.0
        self._download = 0.0
        self._process = 0.0

    def record(self, wait_s: float, download_s: float, process_s: float,
               captures: int) -> Optional[str]:
        """Record one batch. Returns a summary string when a window closes, else None."""
        self._batches += 1
        self._captures += captures
        self._wait += wait_s
        self._download += download_s
        self._process += process_s

        now = self._clock()
        elapsed = now - self._window_start
        if elapsed < self.interval_s:
            return None
        summary = self._format(elapsed)
        self._reset(now)
        return summary

    def _format(self, elapsed: float) -> str:
        n = self._batches
        busy = self._wait + self._download + self._process
        other = max(elapsed - busy, 0.0)
        return (
            f"acq: {self._captures / elapsed:.0f} events/s, "
            f"{n / elapsed:.1f} batches/s ({self._captures / n:.0f} captures/batch) | "
            f"per batch: wait {self._wait / n * 1e3:.1f} ms, "
            f"download {self._download / n * 1e3:.1f} ms, "
            f"process {self._process / n * 1e3:.1f} ms, "
            f"other {other / n * 1e3:.1f} ms"
        )


class AcquisitionEngine(QThread):
    """
    Rapid-block acquisition engine for any driver-supported scope series.

    Captures batches of triggered waveforms, converts ADC counts to mV,
    analyzes pulses synchronously, and appends events to shared storage.
    Runs in a separate thread to avoid blocking the UI; all series-specific
    SDK calls go through a ScopeDriver.
    """

    # Signals
    waveform_ready = Signal(WaveformBatch)  # Emitted when new waveforms available
    batch_complete = Signal(int)  # Emitted after each batch (with capture count)
    acquisition_error = Signal(str)  # Emitted on error
    acquisition_finished = Signal()  # Emitted when acquisition stops
    storage_warning = Signal(str)  # Emitted when storage approaching limit

    def __init__(
        self,
        scope_info: ScopeInfo,
        event_storage: EventStorage,
        batch_size: int,
        sample_count: int,
        pre_trigger_samples: int,
        sample_interval_ns: float,
        voltage_range_code: int,
        max_adc: int,
        cfd_fraction: float = 0.5,
        timebase_index: int = 0,
        driver: Optional[ScopeDriver] = None
    ):
        """
        Initialize the acquisition engine.

        Args:
            scope_info: Information about the connected scope
            event_storage: Global event storage for processed events
            batch_size: Number of captures per batch (rapid block segments)
            sample_count: Total samples per capture
            pre_trigger_samples: Number of pre-trigger samples
            sample_interval_ns: Sample interval in nanoseconds
            voltage_range_code: Voltage range code (MUST match channel config)
            max_adc: Maximum ADC count for voltage conversion (from ScopeInfo)
            cfd_fraction: Constant fraction for CFD timing (0-1)
            timebase_index: Timebase index from configurator
            driver: Scope driver to use (created from scope_info if omitted)
        """
        super().__init__()

        self.scope_info = scope_info
        self.driver = driver if driver is not None else create_driver(scope_info)

        # Event storage
        self.event_storage = event_storage

        # Acquisition parameters
        self.batch_size = batch_size
        self.sample_count = sample_count
        self.pre_trigger_samples = pre_trigger_samples
        self.post_trigger_samples = sample_count - pre_trigger_samples
        self.sample_interval_ns = sample_interval_ns
        self.voltage_range_code = voltage_range_code
        self.max_adc = max_adc
        self.cfd_fraction = cfd_fraction

        # State management
        self._mutex = QMutex()
        self._running = False
        self._stop_requested = False

        # Buffers (allocated once, reused for all batches)
        self._buffers: Optional[Dict[str, List[Tuple[np.ndarray, np.ndarray]]]] = None

        # Channel configuration (all 4 channels)
        self._channels = dict(CHANNEL_MAP)

        # Timebase validated by the configurator (must match sample_interval_ns)
        self._timebase = timebase_index

        # Statistics
        self.total_captures = 0
        self._timing = BatchTimingStats()

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

        except Exception as e:
            import traceback
            error_details = f"Acquisition error: {str(e)}\n{traceback.format_exc()}"
            self.acquisition_error.emit(error_details)

        finally:
            # Cleanup
            self._cleanup()
            with QMutexLocker(self._mutex):
                self._running = False
            self.acquisition_finished.emit()

    def _setup_rapid_block(self) -> None:
        """Configure the scope for rapid block mode."""
        self.driver.memory_segments(self.batch_size, self.sample_count)
        self.driver.set_no_of_captures(self.batch_size)

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
        for channel_name, channel_code in self._channels.items():
            for segment in range(self.batch_size):
                buffer_max, buffer_min = self._buffers[channel_name][segment]
                self.driver.register_buffer(
                    channel_code, segment, buffer_max, buffer_min, self.sample_count
                )

    def _capture_batch(self) -> bool:
        """
        Capture one batch of waveforms.

        Returns:
            True if successful, False if error or stop requested
        """
        try:
            t_armed = time.perf_counter()

            # Start the block capture
            self.driver.run_block(
                self.pre_trigger_samples, self.post_trigger_samples, self._timebase
            )

            # Poll until all captures complete (with timeout)
            while not self.driver.is_ready():
                # Check for stop request
                with QMutexLocker(self._mutex):
                    if self._stop_requested:
                        return False

                if time.perf_counter() - t_armed > TRIGGER_TIMEOUT_S:
                    self.acquisition_error.emit("Timeout waiting for triggers")
                    return False

                time.sleep(POLL_INTERVAL_S)

            t_ready = time.perf_counter()

            # Retrieve data from all segments
            self.driver.get_values_bulk(self.sample_count, self.batch_size)
            t_downloaded = time.perf_counter()

            # Create time array in nanoseconds (relative to trigger)
            time_ns = np.arange(self.sample_count) * self.sample_interval_ns
            time_ns -= self.pre_trigger_samples * self.sample_interval_ns  # Trigger at t=0

            # Process each segment in the batch
            events_to_store: List[EventData] = []
            display_waveforms: Dict[str, np.ndarray] = {}

            for segment_idx in range(self.batch_size):
                # Convert ADC to mV for this segment
                segment_waveforms = {}
                for channel_name in self._channels.keys():
                    buffer_max, _ = self._buffers[channel_name][segment_idx]
                    segment_waveforms[channel_name] = adc_to_mv(
                        buffer_max, self.voltage_range_code, self.max_adc
                    )
                if segment_idx == 0:
                    display_waveforms = segment_waveforms

                # Analyze this event
                event_id = self.event_storage.get_next_event_id()
                timestamp = time.time()

                event_data = analyze_event(
                    time_ns=time_ns,
                    waveforms={},  # Not used by analyze_event
                    segment_waveforms=segment_waveforms,
                    event_id=event_id,
                    timestamp=timestamp,
                    pre_trigger_samples=self.pre_trigger_samples,
                    sample_interval_ns=self.sample_interval_ns,
                    cfd_fraction=self.cfd_fraction
                )

                events_to_store.append(event_data)

            # Store all events from this batch
            num_added = self.event_storage.add_events(events_to_store)

            # Check storage capacity
            if num_added < len(events_to_store):
                self.storage_warning.emit(
                    f"Event storage full! Only {num_added} of {len(events_to_store)} events stored."
                )
                return False  # Stop acquisition if storage is full

            # Warn if approaching capacity (>90%)
            fill_pct = self.event_storage.get_fill_percentage()
            if fill_pct > 90.0 and fill_pct < 95.0:
                self.storage_warning.emit(
                    f"Event storage {fill_pct:.1f}% full ({self.event_storage.get_count():,} events)"
                )

            # Update statistics
            self.total_captures += self.batch_size
            summary = self._timing.record(
                wait_s=t_ready - t_armed,
                download_s=t_downloaded - t_ready,
                process_s=time.perf_counter() - t_downloaded,
                captures=self.batch_size,
            )
            if summary:
                logger.info(summary)

            # Emit signals
            batch = WaveformBatch(
                time_ns=time_ns,
                waveforms=display_waveforms,  # First segment of the batch
                num_captures=self.batch_size,
                segment_index=0
            )
            self.waveform_ready.emit(batch)
            self.batch_complete.emit(num_added)  # Emit actual number of events stored

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
            self.driver.stop()
        except Exception:
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


def create_acquisition_engine(
    scope_info: ScopeInfo,
    event_storage: EventStorage,
    batch_size: Optional[int],
    sample_count: int,
    pre_trigger_samples: int,
    sample_interval_ns: float,
    voltage_range_code: int = 3,  # PS6000_100MV
    max_adc: Optional[int] = None,
    cfd_fraction: float = 0.5,
    timebase_index: int = 0
) -> AcquisitionEngine:
    """
    Factory function to create the appropriate acquisition engine for the scope series.
    
    Args:
        scope_info: Information about the connected scope
        event_storage: Global event storage for processed events
        batch_size: Number of captures per batch, or None to use the
            driver's per-series default (10 for PS3000a, 20 for PS6000)
        sample_count: Total samples per capture
        pre_trigger_samples: Number of pre-trigger samples
        sample_interval_ns: Sample interval in nanoseconds
        voltage_range_code: Voltage range code (MUST match channel config from configurator)
        max_adc: Maximum ADC count (uses scope_info.max_adc if None)
        cfd_fraction: Constant fraction for CFD timing (default: 0.5)
        timebase_index: Timebase index from configurator (used by both series)
    
    Returns:
        Acquisition engine using the appropriate driver for the scope series

    Raises:
        ValueError: If scope series is not supported (raised by create_driver)
    """
    if max_adc is None:
        max_adc = scope_info.max_adc

    driver = create_driver(scope_info)
    if batch_size is None:
        batch_size = driver.default_batch_size

    return AcquisitionEngine(
        scope_info=scope_info,
        event_storage=event_storage,
        batch_size=batch_size,
        driver=driver,
        sample_count=sample_count,
        pre_trigger_samples=pre_trigger_samples,
        sample_interval_ns=sample_interval_ns,
        voltage_range_code=voltage_range_code,
        max_adc=max_adc,
        cfd_fraction=cfd_fraction,
        timebase_index=timebase_index
    )
