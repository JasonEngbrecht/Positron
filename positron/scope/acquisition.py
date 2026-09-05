"""
Data acquisition engine for PicoScope oscilloscopes using rapid block mode.

This module handles high-speed batch acquisition of triggered waveforms,
designed for event-mode data collection at rates up to 10,000 events/second.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict, List, Tuple
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from positron.scope.connection import ScopeInfo
from positron.scope.driver import ScopeDriver, create_driver, CHANNEL_MAP, CHANNEL_INPUT_RANGES_MV
from positron.processing.pulse import analyze_event, EventData
from positron.processing.events import EventStorage


logger = logging.getLogger(__name__)

# Sleep between is_ready() polls. time.sleep() uses a high-resolution timer
# on Windows (measured ~0.6 ms actual for 0.2 ms requested). Do NOT use
# QThread.msleep(1) here: it rounds up to the 15.6 ms scheduler tick and
# cost ~24 ms of dead time per batch (scope disarmed) at 600 events/s.
POLL_INTERVAL_S = 0.0002

# If a batch has not filled within this many seconds of arming, stop the
# scope and read the captures that did complete (possibly none) instead of
# waiting for the full batch. This is what makes low count rates work: a
# batch of 20 at 0.1 Hz would otherwise take 200 s. It also bounds display
# latency at low rates. At high rates the batch fills first and this never
# fires.
PARTIAL_READ_AFTER_S = 0.5


@dataclass
class WaveformBatch:
    """A batch of captured waveforms from rapid block acquisition."""
    time_ns: np.ndarray  # Time array in nanoseconds (relative to trigger)
    waveforms: Dict[str, np.ndarray]  # Channel name -> voltage array (mV)
    num_captures: int  # Number of captures in this batch
    segment_index: int  # Index of the segment shown (for display)


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
        self._discarded = 0
        self._wait = 0.0
        self._download = 0.0
        self._process = 0.0

    def record(self, wait_s: float, download_s: float, process_s: float,
               captures: int, discarded: int = 0) -> Optional[str]:
        """Record one batch. Returns a summary string when a window closes, else None."""
        self._batches += 1
        self._captures += captures
        self._discarded += discarded
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
            f"other {other / n * 1e3:.1f} ms | "
            f"discarded {self._discarded} dark-pulse triggers"
        )


# ---------------------------------------------------------------------------
# DIAGNOSTIC: raw-waveform dump of anomalous events (developer tool).
#
# Added for the 2026-09 negative-energy investigation and kept because it is
# the quickest way to see what the analysis is rejecting. Set the environment
# variable POSITRON_DUMP_ANOMALIES=1 (see run_debug.bat) and the engine writes
# .npz files to ~/.positron/debug/<timestamp>/ for events that were discarded
# (dark-pulse trigger), or where any channel was rejected by the pulse
# validity checks or has a pulse with energy < 0, plus the first few normal
# events for pulse-shape reference. Plot them with tools/plot_anomalies.py.
# Zero cost when the variable is unset.
# ---------------------------------------------------------------------------
ANOMALY_DUMP_ENV = "POSITRON_DUMP_ANOMALIES"
ANOMALY_MAX_FILES = 40       # per run
ANOMALY_NORMAL_FILES = 5     # reference events saved unconditionally
ANOMALY_MIN_SPACING_S = 0.5  # spread saved anomalies over the run instead of
                             # filling the cap in the first second at high rates


class AnomalyDumper:
    """Writes anomalous (and a few normal) events to disk as .npz files."""

    def __init__(self, scope_variant: str, sample_interval_ns: float,
                 pre_trigger_samples: int, cfd_fraction: float):
        self.enabled = os.environ.get(ANOMALY_DUMP_ENV, "") not in ("", "0")
        self.scope_variant = scope_variant
        self.sample_interval_ns = sample_interval_ns
        self.pre_trigger_samples = pre_trigger_samples
        self.cfd_fraction = cfd_fraction
        self.n_events = 0
        self.n_anomalies = 0       # all anomalies seen, saved or not
        self.n_saved = 0
        self.n_normal_saved = 0
        self._t_last_saved = -float('inf')
        self.directory: Optional[Path] = None
        if self.enabled:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.directory = Path.home() / ".positron" / "debug" / stamp
            self.directory.mkdir(parents=True, exist_ok=True)
            logger.info("Anomaly dump enabled: writing to %s", self.directory)

    @staticmethod
    def is_anomalous(event: EventData) -> bool:
        if event.discarded:
            return True
        for pulse in event.channels.values():
            if pulse.rejected or (pulse.has_pulse and pulse.energy < 0.0):
                return True
        return False

    def process_batch(self, time_ns: np.ndarray,
                      waveforms: List[Dict[str, np.ndarray]],
                      events: List[EventData]) -> None:
        """Inspect one batch; waveforms[i] and events[i] describe segment i."""
        for idx, event in enumerate(events):
            self.n_events += 1
            if self.n_normal_saved < ANOMALY_NORMAL_FILES:
                self._save("normal", idx, time_ns, waveforms, events)
                self.n_normal_saved += 1
            if self.is_anomalous(event):
                self.n_anomalies += 1
                now = time.perf_counter()
                if (self.n_saved < ANOMALY_MAX_FILES
                        and now - self._t_last_saved >= ANOMALY_MIN_SPACING_S):
                    self._save("anomaly", idx, time_ns, waveforms, events)
                    self.n_saved += 1
                    self._t_last_saved = now
                    if self.n_saved == ANOMALY_MAX_FILES:
                        logger.info("Anomaly dump: file cap (%d) reached; counting only",
                                    ANOMALY_MAX_FILES)

    def _save(self, kind: str, idx: int, time_ns: np.ndarray,
              waveforms: List[Dict[str, np.ndarray]], events: List[EventData]) -> None:
        event = events[idx]
        data: Dict[str, object] = {
            "kind": kind,
            "scope_variant": self.scope_variant,
            "sample_interval_ns": self.sample_interval_ns,
            "pre_trigger_samples": self.pre_trigger_samples,
            "cfd_fraction": self.cfd_fraction,
            "time_ns": time_ns,
            "event_id": event.event_id,
            "segment_index": idx,
            "batch_size": len(events),
        }
        # This segment, plus the neighbours in the batch (segment idx-1 was
        # captured immediately before, idx+1 immediately after).
        for prefix, j in (("", idx), ("prev_", idx - 1), ("next_", idx + 1)):
            if j < 0 or j >= len(events):
                continue
            data[prefix + "event_id"] = events[j].event_id
            data[prefix + "discard_reason"] = events[j].discard_reason
            for ch, wf in waveforms[j].items():
                pulse = events[j].channels[ch]
                data[f"{prefix}{ch}"] = wf
                data[f"{prefix}{ch}_timing_ns"] = pulse.timing_ns
                data[f"{prefix}{ch}_energy"] = pulse.energy
                data[f"{prefix}{ch}_peak_mv"] = pulse.peak_mv
                data[f"{prefix}{ch}_has_pulse"] = pulse.has_pulse
                data[f"{prefix}{ch}_reject_reason"] = pulse.reject_reason
        path = self.directory / f"{kind}_{event.event_id:07d}.npz"
        np.savez(path, **data)

    def close(self) -> None:
        if self.enabled:
            logger.info("Anomaly dump: %d anomalous of %d events (%.2f%%); %d anomaly + %d normal files in %s",
                        self.n_anomalies, self.n_events,
                        100.0 * self.n_anomalies / max(self.n_events, 1),
                        self.n_saved, self.n_normal_saved, self.directory)

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
        driver: Optional[ScopeDriver] = None,
        trigger_conditions: Optional[List[List[str]]] = None
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
            trigger_conditions: Trigger logic applied to the scope (OR of
                AND-ed channel lists); lets the analysis discard events that
                were triggered only by a PMT dark pulse. None disables that.
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
        self.trigger_conditions = trigger_conditions

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

        # Arm state: True while the scope is collecting a batch we have not
        # yet downloaded. Set by _arm(), cleared after get_values_bulk().
        self._armed = False
        self._t_armed = 0.0
        self.partial_read_after_s = PARTIAL_READ_AFTER_S

        # Statistics
        self.total_captures = 0
        self.total_discarded = 0  # events triggered only by a dark pulse
        self._timing = BatchTimingStats()

        # Diagnostic waveform dump (off unless POSITRON_DUMP_ANOMALIES is set)
        self._dumper = AnomalyDumper(
            scope_info.variant, sample_interval_ns, pre_trigger_samples, cfd_fraction
        )

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
            self._dumper.close()
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

    def _arm(self) -> None:
        """Start a rapid-block capture of batch_size segments."""
        self.driver.run_block(
            self.pre_trigger_samples, self.post_trigger_samples, self._timebase
        )
        self._armed = True
        self._t_armed = time.perf_counter()

    def _capture_batch(self) -> bool:
        """
        Capture one batch of waveforms.

        Sequence: (arm if needed) -> wait ready -> download -> RE-ARM ->
        process. Re-arming before processing lets the scope collect the
        next batch while this one is analyzed: the downloaded samples are
        already in our numpy buffers, which the driver only writes during
        get_values_bulk(), so processing after re-arm is safe.

        If the batch has not filled within partial_read_after_s, the scope
        is stopped and only the completed captures are downloaded and
        processed; zero completed captures simply re-arms. Acquisition
        therefore never times out at low count rates.

        Returns:
            True if successful, False if error or stop requested
        """
        try:
            if not self._armed:
                self._arm()
            t_wait_start = time.perf_counter()

            # Poll until all captures complete, or the wait budget expires
            n_captures = self.batch_size
            while not self.driver.is_ready():
                # Check for stop request
                with QMutexLocker(self._mutex):
                    if self._stop_requested:
                        return False

                if time.perf_counter() - self._t_armed > self.partial_read_after_s:
                    # Partial batch: stop and read what completed
                    self.driver.stop()
                    self._armed = False
                    n_captures = self.driver.get_no_of_captures()
                    break

                time.sleep(POLL_INTERVAL_S)

            t_ready = time.perf_counter()

            if n_captures == 0:
                # Nothing triggered during this arm period; re-arm and keep
                # waiting (no data, no signals, no error).
                self._arm()
                return True

            # Retrieve data from the completed segments
            self.driver.get_values_bulk(self.sample_count, n_captures)
            self._armed = False
            t_downloaded = time.perf_counter()

            # Re-arm immediately so the scope is live while we process
            with QMutexLocker(self._mutex):
                stop_requested = self._stop_requested
            if not stop_requested:
                self._arm()

            # Create time array in nanoseconds (relative to trigger)
            time_ns = np.arange(self.sample_count) * self.sample_interval_ns
            time_ns -= self.pre_trigger_samples * self.sample_interval_ns  # Trigger at t=0

            # Process each segment in the batch
            events_to_store: List[EventData] = []
            display_waveforms: Dict[str, np.ndarray] = {}
            n_discarded = 0
            batch_events: List[EventData] = []                  # diagnostic dump only
            batch_waveforms: List[Dict[str, np.ndarray]] = []  # diagnostic dump only

            for segment_idx in range(n_captures):
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
                    cfd_fraction=self.cfd_fraction,
                    trigger_conditions=self.trigger_conditions
                )

                if event_data.discarded:
                    n_discarded += 1
                else:
                    events_to_store.append(event_data)
                if self._dumper.enabled:
                    batch_events.append(event_data)
                    batch_waveforms.append(segment_waveforms)

            if self._dumper.enabled:
                self._dumper.process_batch(time_ns, batch_waveforms, batch_events)
            self.total_discarded += n_discarded

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
            self.total_captures += n_captures
            summary = self._timing.record(
                wait_s=t_ready - t_wait_start,
                download_s=t_downloaded - t_ready,
                process_s=time.perf_counter() - t_downloaded,
                captures=n_captures,
                discarded=n_discarded,
            )
            if summary:
                logger.info(summary)

            # Emit signals
            batch = WaveformBatch(
                time_ns=time_ns,
                waveforms=display_waveforms,  # First segment of the batch
                num_captures=n_captures,
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
    voltage_range_code: int = 4,  # 200 mV on both series
    max_adc: Optional[int] = None,
    cfd_fraction: float = 0.5,
    timebase_index: int = 0,
    trigger_conditions: Optional[List[List[str]]] = None
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
        trigger_conditions: Trigger logic (OR of AND-ed channel lists) for the
            dark-pulse event discard; None disables it

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
        timebase_index=timebase_index,
        trigger_conditions=trigger_conditions
    )
