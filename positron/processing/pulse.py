"""
Pulse analysis module for event-mode data processing.

Implements digital constant fraction discrimination (CFD) for timing
and waveform integration for energy measurement.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class ChannelPulse:
    """Analysis results for a single channel."""
    timing_ns: float  # Relative to trigger (CFD zero crossing)
    energy: float     # Integrated signal (arbitrary units, positive)
    peak_mv: float    # Peak amplitude for diagnostics
    has_pulse: bool   # Whether a valid pulse was detected
    energy_kev: Optional[float] = None  # Calibrated energy in keV (None if not calibrated)


@dataclass
class EventData:
    """Complete event with 4-channel data."""
    event_id: int
    timestamp: float  # Acquisition time (seconds since start)
    channels: Dict[str, ChannelPulse]  # 'A', 'B', 'C', 'D'


def _calculate_baseline(waveform: np.ndarray, pre_trigger_samples: int) -> float:
    """
    Calculate baseline using mean of pre-trigger samples.
    
    Args:
        waveform: Voltage waveform in mV
        pre_trigger_samples: Number of samples before trigger
        
    Returns:
        Baseline voltage in mV
    """
    if pre_trigger_samples <= 0 or pre_trigger_samples > len(waveform):
        return 0.0
    
    baseline = np.mean(waveform[:pre_trigger_samples])
    return float(baseline)


def _find_cfd_timing(
    waveform: np.ndarray,
    baseline: float,
    time_ns: np.ndarray,
    pre_trigger_samples: int,
    fraction: float
) -> tuple[float, float, bool]:
    """
    Find pulse timing using digital constant fraction discrimination.
    
    Algorithm:
    1. Find peak (minimum value) on falling edge after trigger
    2. Calculate CFD threshold = baseline + fraction * (peak - baseline)
    3. Find zero crossing with linear interpolation
    
    Args:
        waveform: Voltage waveform in mV
        baseline: Baseline voltage in mV
        time_ns: Time array in nanoseconds
        pre_trigger_samples: Number of pre-trigger samples
        fraction: CFD fraction (0-1, typically 0.5)
        
    Returns:
        Tuple of (timing_ns, peak_mv, has_pulse)
        - timing_ns: Time of CFD crossing relative to trigger
        - peak_mv: Peak amplitude relative to baseline
        - has_pulse: Whether a valid pulse was found
    """
    # Look for pulse after trigger point (in post-trigger region)
    post_trigger_waveform = waveform[pre_trigger_samples:]
    
    if len(post_trigger_waveform) == 0:
        return 0.0, 0.0, False
    
    # Find peak (minimum for negative pulses)
    peak_idx_relative = np.argmin(post_trigger_waveform)
    peak_idx = peak_idx_relative + pre_trigger_samples
    peak_value = waveform[peak_idx]
    peak_amplitude = baseline - peak_value  # Positive for negative pulses
    
    # Check if there's a significant pulse (>5 mV from baseline to match trigger threshold)
    if peak_amplitude < 5.0:
        return 0.0, 0.0, False
    
    # Calculate CFD threshold
    # For negative pulses: threshold is between baseline and peak
    threshold = baseline - fraction * peak_amplitude
    
    # Find crossing point on falling edge (before peak)
    # Search from trigger point to peak
    search_start = pre_trigger_samples
    search_end = peak_idx
    
    if search_end <= search_start:
        # Peak is at or before trigger - unusual but possible
        return time_ns[peak_idx], peak_amplitude, True
    
    # Find where waveform crosses threshold (going down)
    for i in range(search_start, search_end):
        if waveform[i] >= threshold and waveform[i + 1] < threshold:
            # Found crossing - use linear interpolation
            v1, v2 = waveform[i], waveform[i + 1]
            t1, t2 = time_ns[i], time_ns[i + 1]
            
            # Linear interpolation to find exact crossing time
            if v2 != v1:
                t_cross = t1 + (threshold - v1) * (t2 - t1) / (v2 - v1)
            else:
                t_cross = t1
            
            return float(t_cross), float(peak_amplitude), True
    
    # No crossing found - return peak time as fallback
    return float(time_ns[peak_idx]), float(peak_amplitude), True


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
    
    Args:
        waveform_mv: Voltage waveform in mV
        time_ns: Time array in nanoseconds (relative to trigger)
        pre_trigger_samples: Number of pre-trigger samples
        sample_interval_ns: Sample interval in nanoseconds
        cfd_fraction: CFD fraction for timing (default: 0.5)
        
    Returns:
        ChannelPulse with timing, energy, and peak information
    """
    # Calculate baseline
    baseline = _calculate_baseline(waveform_mv, pre_trigger_samples)
    
    # Extract timing via CFD
    timing_ns, peak_mv, has_pulse = _find_cfd_timing(
        waveform_mv, baseline, time_ns, pre_trigger_samples, cfd_fraction
    )
    
    # Calculate energy
    energy = _calculate_energy(waveform_mv, baseline, sample_interval_ns)
    
    return ChannelPulse(
        timing_ns=timing_ns,
        energy=energy,
        peak_mv=peak_mv,
        has_pulse=has_pulse
    )


def analyze_event(
    time_ns: np.ndarray,
    waveforms: Dict[str, np.ndarray],
    segment_waveforms: Dict[str, np.ndarray],
    event_id: int,
    timestamp: float,
    pre_trigger_samples: int,
    sample_interval_ns: float,
    cfd_fraction: float = 0.5
) -> EventData:
    """
    Analyze a complete 4-channel event.
    
    Args:
        time_ns: Time array in nanoseconds (shared across channels)
        waveforms: Dict of channel name -> full waveform batch data (not used, for compatibility)
        segment_waveforms: Dict of channel name -> single segment waveform data in mV
        event_id: Unique event identifier
        timestamp: Event timestamp in seconds
        pre_trigger_samples: Number of pre-trigger samples
        sample_interval_ns: Sample interval in nanoseconds
        cfd_fraction: CFD fraction for timing (default: 0.5)
        
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
    
    return EventData(
        event_id=event_id,
        timestamp=timestamp,
        channels=channels
    )
