"""
Pulse analysis module for event-mode data processing.

Implements digital constant fraction discrimination (CFD) for timing
and waveform integration for energy measurement.

Pulse validity
--------------
The scope's trigger is disarmed while it refills the pre-trigger buffer
between rapid-block segments. A pulse arriving in that window is recorded
but does not trigger; the scope then fires as soon as the trigger re-arms,
because the pulse's ~1 us tail is still below the -5 mV threshold (noise on
the recovering tail counts as a fresh falling crossing). The result is a
capture whose pulse peaks in the pre-trigger region. Averaging the whole
pre-trigger window for the baseline then drags the baseline down and the
full-window integral comes out negative (down to about -2x the pulse area).

analyze_pulse therefore
  1. computes the baseline from the pre-trigger window minus a short guard
     interval before the trigger (a legitimate leading edge can start a few
     ns before t = 0),
  2. rejects the channel if that baseline region is not quiet (any sample
     more than PULSE_THRESHOLD_MV below the baseline), whatever the
     post-trigger amplitude,
  3. rejects the channel if the CFD threshold crossing is not found between
     the guard start and the peak, i.e. the pulse's leading edge is not
     inside the captured window, and
  4. rejects the channel if the pulse is too narrow to be scintillation
     light: energy / peak amplitude (an effective width) below
     MIN_EFFECTIVE_WIDTH_NS. Single-photoelectron dark pulses from the PMT
     are 3-5 ns wide with ~zero area; real pulses from these detectors have
     an effective width of 240-280 ns. The cut is gain-independent, so one
     constant serves every detector.
Rejected channels have has_pulse=False and a non-empty reject_reason, so
every consumer that filters on has_pulse ignores them; peak_mv is kept for
diagnostics.

analyze_event additionally re-evaluates the trigger logic: if the trigger
condition was met only with the help of a dark pulse (a width-rejected
channel at t ~ 0), the whole event is marked for discard, because it exists
only because of PMT noise and the other channels hold random content.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence
import numpy as np


# Minimum amplitude below baseline for a channel to count as having a pulse
# (mV). Matches the -5 mV hardware trigger threshold.
PULSE_THRESHOLD_MV = 5.0

# Pre-trigger samples closer than this to the trigger are excluded from the
# baseline and are searched for the CFD crossing. The leading edge of a pulse
# that fired the trigger at -5 mV begins a few ns before t = 0; 50 ns is far
# longer than any leading edge yet short against the 1 us pre-trigger window.
BASELINE_GUARD_NS = 50.0

# Minimum effective width (energy / peak amplitude, in ns) for a pulse to be
# scintillation light rather than a PMT dark pulse. Dark pulses measured on
# both scopes: 3-20 ns. Real pulses: 40 ns minimum, 240-280 ns typical.
MIN_EFFECTIVE_WIDTH_NS = 30.0

# A pulse whose CFD time is within this window of t = 0 is taken to be one of
# the channels that fired the trigger. Real pulses that fired the trigger sit
# at 1-5 ns on the 6000 series and -3 to +2 ns on the 3000a.
TRIGGER_WINDOW_NS = 20.0

REJECT_PRE_TRIGGER = "pre_trigger"  # pulse in the pre-trigger window
REJECT_NO_EDGE = "no_edge"          # leading edge not inside the window
REJECT_WIDTH = "width"              # too narrow: PMT dark pulse / noise spike
DISCARD_DARK_PULSE_TRIGGER = "dark_pulse_trigger"


@dataclass
class ChannelPulse:
    """Analysis results for a single channel."""
    timing_ns: float  # Relative to trigger (CFD zero crossing)
    energy: float     # Integrated signal (arbitrary units, positive)
    peak_mv: float    # Peak amplitude below baseline for diagnostics
    has_pulse: bool   # Whether a valid pulse was detected
    energy_kev: Optional[float] = None  # Calibrated energy in keV (None if not calibrated)
    reject_reason: str = ""  # One of the REJECT_* constants when a validity check failed

    @property
    def rejected(self) -> bool:
        return bool(self.reject_reason)


@dataclass
class EventData:
    """Complete event with 4-channel data."""
    event_id: int
    timestamp: float  # Acquisition time (seconds since start)
    channels: Dict[str, ChannelPulse]  # 'A', 'B', 'C', 'D'
    discard_reason: str = ""  # Non-empty if the whole event should not be stored

    @property
    def discarded(self) -> bool:
        return bool(self.discard_reason)


def guard_samples(pre_trigger_samples: int, sample_interval_ns: float) -> int:
    """
    Number of pre-trigger samples covered by BASELINE_GUARD_NS.

    Capped at half the pre-trigger window so the baseline always keeps a
    reasonable number of samples, whatever the timebase.
    """
    if sample_interval_ns <= 0:
        return 0
    guard = int(round(BASELINE_GUARD_NS / sample_interval_ns))
    return max(0, min(guard, pre_trigger_samples // 2))


def _calculate_baseline(
    waveform: np.ndarray,
    pre_trigger_samples: int,
    guard_samples: int = 0
) -> float:
    """
    Calculate baseline as the mean of the pre-trigger samples, excluding the
    last `guard_samples` before the trigger.

    Args:
        waveform: Voltage waveform in mV
        pre_trigger_samples: Number of samples before trigger
        guard_samples: Samples immediately before the trigger to exclude

    Returns:
        Baseline voltage in mV (0.0 if no usable pre-trigger samples)
    """
    n_baseline = pre_trigger_samples - guard_samples
    if n_baseline <= 0 or pre_trigger_samples > len(waveform):
        return 0.0

    return float(np.mean(waveform[:n_baseline]))


def _pre_trigger_is_quiet(
    waveform: np.ndarray,
    baseline: float,
    n_baseline_samples: int,
    threshold_mv: float = PULSE_THRESHOLD_MV
) -> bool:
    """
    True if no sample in the baseline region dips more than threshold_mv
    below the baseline, i.e. there is no pulse in the pre-trigger window.
    """
    if n_baseline_samples <= 0:
        return True
    return float(np.min(waveform[:n_baseline_samples])) > baseline - threshold_mv


def _find_cfd_timing(
    waveform: np.ndarray,
    baseline: float,
    time_ns: np.ndarray,
    pre_trigger_samples: int,
    fraction: float,
    guard_samples: int = 0
) -> tuple[float, float, bool]:
    """
    Find pulse timing using digital constant fraction discrimination.

    Algorithm:
    1. Find peak (minimum value) in the post-trigger region
    2. Calculate CFD threshold = baseline - fraction * peak_amplitude
    3. Find the first falling crossing of that threshold between
       (trigger - guard_samples) and the peak, with linear interpolation

    Args:
        waveform: Voltage waveform in mV
        baseline: Baseline voltage in mV
        time_ns: Time array in nanoseconds
        pre_trigger_samples: Number of pre-trigger samples
        fraction: CFD fraction (0-1, typically 0.5)
        guard_samples: How far before the trigger the crossing search starts

    Returns:
        Tuple of (timing_ns, peak_mv, has_pulse)
        - timing_ns: Time of CFD crossing relative to trigger (0.0 if none)
        - peak_mv: Peak amplitude below baseline (always returned, even
          when has_pulse is False, so callers can tell a small pulse from a
          pulse whose leading edge is not in the window)
        - has_pulse: True only if the amplitude exceeds PULSE_THRESHOLD_MV
          AND a threshold crossing was found in the search range
    """
    post_trigger_waveform = waveform[pre_trigger_samples:]

    if len(post_trigger_waveform) == 0:
        return 0.0, 0.0, False

    # Peak (minimum for negative pulses) in the post-trigger region
    peak_idx = int(np.argmin(post_trigger_waveform)) + pre_trigger_samples
    peak_amplitude = float(baseline - waveform[peak_idx])  # Positive for negative pulses

    if peak_amplitude < PULSE_THRESHOLD_MV:
        return 0.0, peak_amplitude, False

    threshold = baseline - fraction * peak_amplitude

    # Falling crossing of the threshold on the leading edge, searched from
    # the guard start up to the peak. w[i] >= thr and w[i+1] < thr.
    search_start = max(pre_trigger_samples - guard_samples, 0)
    search_end = peak_idx
    if search_end <= search_start:
        # Peak at the very start of the search range: no leading edge here
        return 0.0, peak_amplitude, False

    segment = waveform[search_start:search_end + 1]
    crossings = np.nonzero((segment[:-1] >= threshold) & (segment[1:] < threshold))[0]
    if crossings.size == 0:
        # Already below threshold when the search range starts: the leading
        # edge lies before the window we trust
        return 0.0, peak_amplitude, False

    i = search_start + int(crossings[0])
    v1, v2 = waveform[i], waveform[i + 1]
    t1, t2 = time_ns[i], time_ns[i + 1]
    if v2 != v1:
        t_cross = t1 + (threshold - v1) * (t2 - t1) / (v2 - v1)
    else:
        t_cross = t1

    return float(t_cross), peak_amplitude, True


def _calculate_energy(
    waveform: np.ndarray,
    baseline: float,
    sample_interval_ns: float
) -> float:
    """
    Calculate pulse energy via integration.

    Energy = -sum(waveform - baseline) * sample_interval
    Negative sign inverts negative pulses to positive values.

    Args:
        waveform: Voltage waveform in mV
        baseline: Baseline voltage in mV
        sample_interval_ns: Sample interval in nanoseconds

    Returns:
        Energy in mV·ns (arbitrary units, positive)
    """
    # Subtract baseline
    baseline_corrected = waveform - baseline

    # Integrate (sum all samples)
    # Negative sign to make negative pulses positive
    energy = -np.sum(baseline_corrected) * sample_interval_ns

    return float(energy)


def analyze_pulse(
    waveform_mv: np.ndarray,
    time_ns: np.ndarray,
    pre_trigger_samples: int,
    sample_interval_ns: float,
    cfd_fraction: float = 0.5
) -> ChannelPulse:
    """
    Analyze a single channel waveform to extract timing and energy.

    See the module docstring for the validity checks. A channel that fails
    a check is returned with has_pulse=False, a reject_reason, energy=0.0
    and the measured peak_mv. timing_ns is 0.0 except for width rejections,
    which keep the CFD time so analyze_event can tell whether the dark pulse
    is what fired the trigger.

    Args:
        waveform_mv: Voltage waveform in mV
        time_ns: Time array in nanoseconds (relative to trigger)
        pre_trigger_samples: Number of pre-trigger samples
        sample_interval_ns: Sample interval in nanoseconds
        cfd_fraction: CFD fraction for timing (default: 0.5)

    Returns:
        ChannelPulse with timing, energy, and peak information
    """
    guard = guard_samples(pre_trigger_samples, sample_interval_ns)
    n_baseline = pre_trigger_samples - guard

    baseline = _calculate_baseline(waveform_mv, pre_trigger_samples, guard)

    timing_ns, peak_mv, has_pulse = _find_cfd_timing(
        waveform_mv, baseline, time_ns, pre_trigger_samples, cfd_fraction, guard
    )

    if not _pre_trigger_is_quiet(waveform_mv, baseline, n_baseline):
        # A pulse in the pre-trigger region: whatever follows the trigger is
        # its tail (or piled up on it), so the channel is unusable
        return ChannelPulse(
            timing_ns=0.0, energy=0.0, peak_mv=peak_mv, has_pulse=False,
            reject_reason=REJECT_PRE_TRIGGER
        )

    if peak_mv < PULSE_THRESHOLD_MV:
        # No pulse on this channel
        return ChannelPulse(timing_ns=0.0, energy=0.0, peak_mv=peak_mv, has_pulse=False)

    if not has_pulse:
        # Amplitude is there but the leading edge is not inside the window
        return ChannelPulse(
            timing_ns=0.0, energy=0.0, peak_mv=peak_mv, has_pulse=False,
            reject_reason=REJECT_NO_EDGE
        )

    energy = _calculate_energy(waveform_mv, baseline, sample_interval_ns)

    if energy < MIN_EFFECTIVE_WIDTH_NS * peak_mv:
        # Too narrow for scintillation light: PMT dark pulse or noise spike.
        # Keep the CFD time so the event-level trigger check can use it.
        return ChannelPulse(
            timing_ns=timing_ns, energy=0.0, peak_mv=peak_mv, has_pulse=False,
            reject_reason=REJECT_WIDTH
        )

    return ChannelPulse(
        timing_ns=timing_ns,
        energy=energy,
        peak_mv=peak_mv,
        has_pulse=True
    )


def event_triggered_by_dark_pulse(
    channels: Dict[str, ChannelPulse],
    trigger_conditions: Sequence[Sequence[str]]
) -> bool:
    """
    True if the scope trigger was satisfied only with the help of a dark pulse.

    Channels whose pulse (accepted, or width-rejected) has a CFD time within
    TRIGGER_WINDOW_NS of t = 0 are the ones that fired the trigger. The
    trigger logic (OR of AND-ed channel lists) is re-evaluated:
      - satisfiable with accepted pulses alone -> the event would have
        triggered anyway -> keep;
      - satisfiable only when the dark pulses are included -> discard;
      - not satisfiable either way (trigger source not visible to the
        analysis) -> keep, as before.
    """
    def at_trigger(pulse: ChannelPulse) -> bool:
        return abs(pulse.timing_ns) <= TRIGGER_WINDOW_NS

    dark = {ch for ch, p in channels.items()
            if p.reject_reason == REJECT_WIDTH and at_trigger(p)}
    if not dark:
        return False

    valid = {ch for ch, p in channels.items() if p.has_pulse and at_trigger(p)}
    for condition in trigger_conditions:
        if condition and all(ch in valid for ch in condition):
            return False  # fired legitimately

    both = valid | dark
    for condition in trigger_conditions:
        if (condition and all(ch in both for ch in condition)
                and any(ch in dark for ch in condition)):
            return True
    return False


def analyze_event(
    time_ns: np.ndarray,
    waveforms: Dict[str, np.ndarray],
    segment_waveforms: Dict[str, np.ndarray],
    event_id: int,
    timestamp: float,
    pre_trigger_samples: int,
    sample_interval_ns: float,
    cfd_fraction: float = 0.5,
    trigger_conditions: Optional[Sequence[Sequence[str]]] = None
) -> EventData:
    """
    Analyze a complete 4-channel event.

    If trigger_conditions is given (OR of AND-ed channel lists, as configured
    on the scope) the event is marked discard_reason=DISCARD_DARK_PULSE_TRIGGER
    when the trigger would not have fired without a width-rejected dark pulse;
    see event_triggered_by_dark_pulse.

    Args:
        time_ns: Time array in nanoseconds (shared across channels)
        waveforms: Dict of channel name -> full waveform batch data (not used, for compatibility)
        segment_waveforms: Dict of channel name -> single segment waveform data in mV
        event_id: Unique event identifier
        timestamp: Event timestamp in seconds
        pre_trigger_samples: Number of pre-trigger samples
        sample_interval_ns: Sample interval in nanoseconds
        cfd_fraction: CFD fraction for timing (default: 0.5)
        trigger_conditions: Trigger logic, e.g. [['A'], ['B']] for A OR B,
            [['A', 'B']] for A AND B. None disables the event-level check.

    Returns:
        EventData containing all 4 channels
    """
    channels = {}

    for channel_name in ['A', 'B', 'C', 'D']:
        if channel_name in segment_waveforms:
            waveform_mv = segment_waveforms[channel_name]
            pulse = analyze_pulse(
                waveform_mv=waveform_mv,
                time_ns=time_ns,
                pre_trigger_samples=pre_trigger_samples,
                sample_interval_ns=sample_interval_ns,
                cfd_fraction=cfd_fraction
            )
            channels[channel_name] = pulse
        else:
            # Channel not available - create placeholder
            channels[channel_name] = ChannelPulse(
                timing_ns=0.0,
                energy=0.0,
                peak_mv=0.0,
                has_pulse=False
            )

    discard_reason = ""
    if trigger_conditions and event_triggered_by_dark_pulse(channels, trigger_conditions):
        discard_reason = DISCARD_DARK_PULSE_TRIGGER

    return EventData(
        event_id=event_id,
        timestamp=timestamp,
        channels=channels,
        discard_reason=discard_reason
    )
