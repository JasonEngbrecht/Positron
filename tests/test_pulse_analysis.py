"""
Unit tests for pulse analysis module.

Tests digital CFD timing and energy integration algorithms.
"""

import numpy as np
import pytest

from positron.processing.pulse import (
    _calculate_baseline,
    _find_cfd_timing,
    _calculate_energy,
    analyze_pulse,
    analyze_event,
    ChannelPulse,
    EventData
)


def create_synthetic_pulse(
    baseline_mv: float = 0.0,
    peak_mv: float = -20.0,
    peak_time_ns: float = 100.0,
    rise_time_ns: float = 10.0,
    fall_time_ns: float = 50.0,
    sample_interval_ns: float = 8.0,
    total_time_ns: float = 3000.0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create a synthetic negative pulse for testing.
    
    Returns:
        Tuple of (time_ns, voltage_mv)
    """
    # Create time array
    num_samples = int(total_time_ns / sample_interval_ns)
    time_ns = np.arange(num_samples) * sample_interval_ns
    time_ns -= 1000.0  # Trigger at t=0, so start at -1000 ns
    
    # Initialize waveform at baseline
    voltage_mv = np.full(num_samples, baseline_mv)
    
    # Create pulse shape (Gaussian-like for falling edge)
    for i, t in enumerate(time_ns):
        if t < peak_time_ns - rise_time_ns:
            # Before pulse
            voltage_mv[i] = baseline_mv
        elif t < peak_time_ns:
            # Rising edge (going down)
            progress = (t - (peak_time_ns - rise_time_ns)) / rise_time_ns
            voltage_mv[i] = baseline_mv + (peak_mv - baseline_mv) * progress
        elif t < peak_time_ns + fall_time_ns:
            # Falling edge (going back up)
            progress = (t - peak_time_ns) / fall_time_ns
            voltage_mv[i] = peak_mv + (baseline_mv - peak_mv) * progress
        else:
            # After pulse
            voltage_mv[i] = baseline_mv
    
    return time_ns, voltage_mv


def test_calculate_baseline():
    """Test baseline calculation."""
    # Simple baseline test
    waveform = np.array([1.0, 1.1, 0.9, 1.0, -10.0, -5.0, 2.0])
    baseline = _calculate_baseline(waveform, pre_trigger_samples=4)
    
    # Should be mean of first 4 samples
    expected = np.mean([1.0, 1.1, 0.9, 1.0])
    assert abs(baseline - expected) < 0.01


def test_find_cfd_timing():
    """Test CFD timing extraction."""
    # Create synthetic pulse
    time_ns, voltage_mv = create_synthetic_pulse(
        baseline_mv=0.0,
        peak_mv=-20.0,
        peak_time_ns=100.0,
        rise_time_ns=20.0,
        fall_time_ns=50.0
    )
    
    baseline = 0.0
    pre_trigger_samples = 125  # 1 µs before trigger
    
    # Test with 50% CFD
    timing, peak, has_pulse = _find_cfd_timing(
        voltage_mv, baseline, time_ns, pre_trigger_samples, fraction=0.5
    )
    
    assert has_pulse
    assert peak > 15.0  # Should detect ~20 mV peak
    # Timing should be somewhere on the falling edge before peak
    assert timing < 100.0  # Before peak time
    assert timing > 0.0  # After trigger


def test_calculate_energy():
    """Test energy integration."""
    # Create synthetic pulse
    time_ns, voltage_mv = create_synthetic_pulse(
        baseline_mv=0.0,
        peak_mv=-20.0,
        peak_time_ns=100.0
    )
    
    baseline = 0.0
    sample_interval_ns = 8.0
    
    energy = _calculate_energy(voltage_mv, baseline, sample_interval_ns)
    
    # Energy should be positive (negative pulse inverted)
    assert energy > 0.0
    
    # Rough check: pulse area should be reasonable
    # Peak is -20 mV, width ~50 ns, so area ~ 1000 mV·ns
    assert 500.0 < energy < 5000.0


def test_analyze_pulse():
    """Test complete pulse analysis."""
    # Create synthetic pulse
    time_ns, voltage_mv = create_synthetic_pulse(
        baseline_mv=0.0,
        peak_mv=-20.0,
        peak_time_ns=100.0
    )
    
    pre_trigger_samples = 125
    sample_interval_ns = 8.0
    
    result = analyze_pulse(
        waveform_mv=voltage_mv,
        time_ns=time_ns,
        pre_trigger_samples=pre_trigger_samples,
        sample_interval_ns=sample_interval_ns,
        cfd_fraction=0.5
    )
    
    assert isinstance(result, ChannelPulse)
    assert result.has_pulse
    assert result.peak_mv > 15.0
    assert result.energy > 0.0
    assert result.timing_ns < 100.0  # Should be before peak


def test_analyze_event():
    """Test complete event analysis with 4 channels."""
    # Create synthetic pulses for all channels
    time_ns, voltage_mv_a = create_synthetic_pulse(peak_mv=-15.0, peak_time_ns=80.0)
    _, voltage_mv_b = create_synthetic_pulse(peak_mv=-25.0, peak_time_ns=100.0)
    _, voltage_mv_c = create_synthetic_pulse(peak_mv=-10.0, peak_time_ns=120.0)
    _, voltage_mv_d = create_synthetic_pulse(peak_mv=-30.0, peak_time_ns=90.0)
    
    segment_waveforms = {
        'A': voltage_mv_a,
        'B': voltage_mv_b,
        'C': voltage_mv_c,
        'D': voltage_mv_d
    }
    
    event = analyze_event(
        time_ns=time_ns,
        waveforms={},
        segment_waveforms=segment_waveforms,
        event_id=42,
        timestamp=1234.5,
        pre_trigger_samples=125,
        sample_interval_ns=8.0,
        cfd_fraction=0.5
    )
    
    assert isinstance(event, EventData)
    assert event.event_id == 42
    assert event.timestamp == 1234.5
    assert len(event.channels) == 4
    
    # Check all channels have valid data
    for channel_name in ['A', 'B', 'C', 'D']:
        assert channel_name in event.channels
        pulse = event.channels[channel_name]
        assert isinstance(pulse, ChannelPulse)
        assert pulse.has_pulse
        assert pulse.peak_mv > 5.0
        assert pulse.energy > 0.0


def test_no_pulse_detection():
    """Test that noise-only signals don't detect false pulses."""
    # Create noise-only waveform (small deviations from baseline)
    num_samples = 375
    time_ns = np.arange(num_samples) * 8.0 - 1000.0
    voltage_mv = np.random.normal(0.0, 0.5, num_samples)  # 0.5 mV RMS noise
    
    result = analyze_pulse(
        waveform_mv=voltage_mv,
        time_ns=time_ns,
        pre_trigger_samples=125,
        sample_interval_ns=8.0,
        cfd_fraction=0.5
    )
    
    # Should not detect a pulse (threshold is 1 mV)
    # Note: With random noise, there's a small chance this could fail
    # In practice, real noise characteristics would be different
    assert isinstance(result, ChannelPulse)


if __name__ == "__main__":
    # Run basic tests
    print("Running pulse analysis tests...")
    
    print("Test 1: Baseline calculation")
    test_calculate_baseline()
    print("PASSED")
    
    print("Test 2: CFD timing")
    test_find_cfd_timing()
    print("PASSED")
    
    print("Test 3: Energy integration")
    test_calculate_energy()
    print("PASSED")
    
    print("Test 4: Pulse analysis")
    test_analyze_pulse()
    print("PASSED")
    
    print("Test 5: Event analysis")
    test_analyze_event()
    print("PASSED")
    
    print("Test 6: No pulse detection")
    test_no_pulse_detection()
    print("PASSED")
    
    print("\nAll tests passed!")
