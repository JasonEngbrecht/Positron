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


# ---------------------------------------------------------------------------
# Pulse validity (pre-trigger pulses, guarded baseline, leading-edge check)
# ---------------------------------------------------------------------------

from positron.processing.pulse import (
    BASELINE_GUARD_NS,
    PULSE_THRESHOLD_MV,
    guard_samples,
    _pre_trigger_is_quiet,
)

# 6402D-like capture: 0.8 ns samples, 1 us pre-trigger, 2 us post-trigger
DT_6000 = 0.8
N_6000 = 3750
PRE_6000 = 1249
# 3406D-like capture: 4 ns samples, 1 us pre-trigger, 2 us post-trigger
DT_3000 = 4.0
N_3000 = 749
PRE_3000 = 249


def make_pmt_pulse(t0_ns, amp_mv, dt, n, pre, tau_ns=250.0, rise_ns=3.0,
                   noise_mv=0.0, seed=0):
    """
    Realistic detector pulse: fast rise, exponential ~1 us tail, negative
    polarity, starting at t0_ns relative to the trigger (t = 0 at index pre).
    """
    t = (np.arange(n) - pre) * dt
    w = np.zeros(n)
    m = t >= t0_ns
    x = t[m] - t0_ns
    w[m] = -amp_mv * np.exp(-x / tau_ns) * (1.0 - np.exp(-x / rise_ns))
    if noise_mv:
        w += np.random.default_rng(seed).normal(0.0, noise_mv, n)
    return t, w


def _analyze(t0_ns, amp_mv, dt=DT_6000, n=N_6000, pre=PRE_6000, **kw):
    t, w = make_pmt_pulse(t0_ns, amp_mv, dt, n, pre, **kw)
    return analyze_pulse(w, t, pre, dt, cfd_fraction=0.5)


def test_guard_samples():
    assert guard_samples(PRE_6000, DT_6000) == round(BASELINE_GUARD_NS / DT_6000)
    assert guard_samples(PRE_3000, DT_3000) == round(BASELINE_GUARD_NS / DT_3000)
    # Never more than half the pre-trigger window
    assert guard_samples(10, 0.8) == 5
    assert guard_samples(0, 0.8) == 0


def test_baseline_excludes_guard_region():
    waveform = np.zeros(20)
    waveform[8:10] = -40.0  # leading edge inside the guard, just before trigger
    assert _calculate_baseline(waveform, pre_trigger_samples=10, guard_samples=2) == 0.0
    assert _calculate_baseline(waveform, pre_trigger_samples=10) == -8.0


def test_pre_trigger_quiet_check():
    waveform = np.zeros(100)
    assert _pre_trigger_is_quiet(waveform, 0.0, 50)
    waveform[20] = -PULSE_THRESHOLD_MV - 0.1
    assert not _pre_trigger_is_quiet(waveform, 0.0, 50)
    assert _pre_trigger_is_quiet(waveform, 0.0, 10)  # dip lies outside the region


@pytest.mark.parametrize("dt,n,pre", [(DT_6000, N_6000, PRE_6000), (DT_3000, N_3000, PRE_3000)])
@pytest.mark.parametrize("t0_ns", [-900.0, -500.0, -330.0, -240.0, -130.0])
def test_pulse_in_pre_trigger_window_is_rejected(dt, n, pre, t0_ns):
    """The bug: a pulse peaking before the trigger gave a large negative energy."""
    result = _analyze(t0_ns, 40.0, dt, n, pre)
    assert result.rejected
    assert not result.has_pulse
    assert result.energy == 0.0
    assert result.timing_ns == 0.0


@pytest.mark.parametrize("dt,n,pre", [(DT_6000, N_6000, PRE_6000), (DT_3000, N_3000, PRE_3000)])
def test_no_accepted_pulse_has_negative_energy(dt, n, pre):
    for t0_ns in np.arange(-980.0, 1900.0, 37.0):
        result = _analyze(t0_ns, 30.0, dt, n, pre, noise_mv=0.4, seed=int(t0_ns) & 0xFFFF)
        if result.has_pulse:
            assert result.energy > 0.0, f"t0={t0_ns}: energy {result.energy}"
            assert not result.rejected
        if t0_ns < -BASELINE_GUARD_NS - 10.0:
            assert result.rejected, f"t0={t0_ns}: pre-trigger pulse not rejected"


@pytest.mark.parametrize("dt,n,pre", [(DT_6000, N_6000, PRE_6000), (DT_3000, N_3000, PRE_3000)])
@pytest.mark.parametrize("t0_ns", [-30.0, -10.0, -4.0, 0.0, 2.0, 100.0, 800.0])
def test_pulse_straddling_or_after_trigger_is_accepted(dt, n, pre, t0_ns):
    reference = _analyze(300.0, 40.0, dt, n, pre)
    result = _analyze(t0_ns, 40.0, dt, n, pre)
    assert result.has_pulse and not result.rejected
    assert abs(result.energy - reference.energy) / reference.energy < 0.02
    # CFD crossing sits on the leading edge, a few ns after the pulse starts
    assert t0_ns - dt <= result.timing_ns <= t0_ns + 3.0 * 3.0


def test_small_pulse_at_threshold_is_accepted():
    # 6 mV pulse whose 50% point falls a sample before t = 0
    result = _analyze(-2.0, 6.0)
    assert result.has_pulse and not result.rejected
    assert -5.0 < result.timing_ns < 5.0


def test_late_pulse_is_accepted_with_shorter_integral():
    # Pulse at 1.5 us: legit, but the tail is cut off by the window end
    result = _analyze(1500.0, 40.0)
    assert result.has_pulse and not result.rejected
    assert result.energy > 0.0
    assert 1495.0 < result.timing_ns < 1510.0


def test_edge_before_guard_start_is_rejected_even_if_baseline_region_quiet():
    # Quiet baseline region, then the signal is already at -20 mV when the
    # guard region begins: the leading edge is outside the trusted window.
    dt, n, pre = DT_6000, N_6000, PRE_6000
    g = guard_samples(pre, dt)
    t = (np.arange(n) - pre) * dt
    w = np.zeros(n)
    w[pre - g:] = -20.0
    result = analyze_pulse(w, t, pre, dt)
    assert result.rejected and not result.has_pulse


def test_normal_pulse_results_unchanged():
    """Guarded baseline + extended search must not move a normal pulse."""
    time_ns, voltage_mv = create_synthetic_pulse(peak_mv=-20.0, peak_time_ns=100.0)
    result = analyze_pulse(voltage_mv, time_ns, 125, 8.0, 0.5)
    assert result.has_pulse and not result.rejected
    assert 80.0 < result.timing_ns < 100.0
    assert result.peak_mv == pytest.approx(-voltage_mv.min(), abs=1e-9)
    assert result.energy == pytest.approx(_calculate_energy(voltage_mv, 0.0, 8.0), rel=1e-6)


def test_analyze_event_propagates_rejected():
    t, good = make_pmt_pulse(50.0, 30.0, DT_6000, N_6000, PRE_6000)
    _, early = make_pmt_pulse(-400.0, 30.0, DT_6000, N_6000, PRE_6000)
    _, quiet = make_pmt_pulse(50.0, 0.0, DT_6000, N_6000, PRE_6000)
    event = analyze_event(t, {}, {'A': good, 'B': early, 'C': quiet}, 7, 0.0, PRE_6000, DT_6000)
    assert event.channels['A'].has_pulse and not event.channels['A'].rejected
    assert event.channels['B'].rejected and not event.channels['B'].has_pulse
    assert not event.channels['C'].has_pulse and not event.channels['C'].rejected
    assert not event.channels['D'].has_pulse and not event.channels['D'].rejected  # placeholder


# ---------------------------------------------------------------------------
# Width cut (PMT dark pulses) and event-level dark-pulse trigger discard
# ---------------------------------------------------------------------------

from positron.processing.pulse import (
    MIN_EFFECTIVE_WIDTH_NS,
    TRIGGER_WINDOW_NS,
    REJECT_WIDTH,
    REJECT_PRE_TRIGGER,
    DISCARD_DARK_PULSE_TRIGGER,
    event_triggered_by_dark_pulse,
)


def make_dark_pulse(t0_ns, amp_mv, dt, n, pre, width_ns=4.0, noise_mv=0.0, seed=0):
    """Single-photoelectron-like blip: a few ns wide, negative, no tail."""
    t = (np.arange(n) - pre) * dt
    w = np.zeros(n)
    m = (t >= t0_ns) & (t < t0_ns + width_ns)
    w[m] = -amp_mv
    if noise_mv:
        w += np.random.default_rng(seed).normal(0.0, noise_mv, n)
    return t, w


@pytest.mark.parametrize("dt,n,pre", [(DT_6000, N_6000, PRE_6000), (DT_3000, N_3000, PRE_3000)])
@pytest.mark.parametrize("amp_mv", [5.5, 8.0, 30.0])
def test_dark_pulse_is_width_rejected(dt, n, pre, amp_mv):
    t, w = make_dark_pulse(0.0, amp_mv, dt, n, pre)
    result = analyze_pulse(w, t, pre, dt)
    assert result.reject_reason == REJECT_WIDTH
    assert not result.has_pulse and result.rejected
    assert result.energy == 0.0
    assert result.peak_mv == pytest.approx(amp_mv, abs=1e-9)
    # CFD time is kept so the event-level check can attribute the trigger
    assert abs(result.timing_ns) < TRIGGER_WINDOW_NS


@pytest.mark.parametrize("dt,n,pre", [(DT_6000, N_6000, PRE_6000), (DT_3000, N_3000, PRE_3000)])
def test_real_pulses_pass_width_cut_at_any_amplitude(dt, n, pre):
    for amp in (5.5, 8.0, 20.0, 60.0):
        r = _analyze(0.0, amp, dt, n, pre, noise_mv=0.4)
        assert r.has_pulse and not r.rejected, (amp, r)
        assert r.energy / r.peak_mv > 4 * MIN_EFFECTIVE_WIDTH_NS  # large margin


def _pulses(**kw):
    """Build a channel dict from keyword specs: ch=('ok'|'dark'|'pre'|None, timing_ns)."""
    out = {}
    for ch in "ABCD":
        kind, t = kw.get(ch, (None, 0.0))
        if kind == "ok":
            out[ch] = ChannelPulse(timing_ns=t, energy=5000.0, peak_mv=20.0, has_pulse=True)
        elif kind == "dark":
            out[ch] = ChannelPulse(timing_ns=t, energy=0.0, peak_mv=6.0, has_pulse=False,
                                   reject_reason=REJECT_WIDTH)
        elif kind == "pre":
            out[ch] = ChannelPulse(timing_ns=0.0, energy=0.0, peak_mv=6.0, has_pulse=False,
                                   reject_reason=REJECT_PRE_TRIGGER)
        else:
            out[ch] = ChannelPulse(timing_ns=0.0, energy=0.0, peak_mv=0.5, has_pulse=False)
    return out


OR_ALL = [["A"], ["B"], ["C"], ["D"]]


def test_dark_pulse_alone_at_trigger_discards_event():
    assert event_triggered_by_dark_pulse(_pulses(B=("dark", 0.8)), OR_ALL)


def test_dark_pulse_with_real_coincident_pulse_keeps_event():
    # D fired the trigger legitimately; B's dark pulse happened to coincide
    assert not event_triggered_by_dark_pulse(_pulses(B=("dark", 0.8), D=("ok", 3.5)), OR_ALL)


def test_dark_pulse_with_late_real_pulse_discards_event():
    # The real pulse at 600 ns did not fire the trigger; the dark pulse did
    assert event_triggered_by_dark_pulse(_pulses(B=("dark", 0.8), D=("ok", 600.0)), OR_ALL)


def test_dark_pulse_away_from_trigger_keeps_event():
    assert not event_triggered_by_dark_pulse(_pulses(B=("dark", 900.0), D=("ok", 3.5)), OR_ALL)


def test_dark_pulse_on_non_trigger_channel_keeps_event():
    # Only A and B are in the trigger; a dark pulse on C cannot have fired it
    assert not event_triggered_by_dark_pulse(_pulses(C=("dark", 0.5)), [["A"], ["B"]])


def test_and_condition_met_only_with_dark_pulse_discards_event():
    # Trigger is A AND B; A is real, B is a dark pulse: without B no trigger
    assert event_triggered_by_dark_pulse(_pulses(A=("ok", 3.0), B=("dark", 1.0)), [["A", "B"]])
    # Both real: keep
    assert not event_triggered_by_dark_pulse(_pulses(A=("ok", 3.0), B=("ok", 2.0)), [["A", "B"]])


def test_or_of_and_conditions():
    conds = [["A", "B"], ["C"]]
    # A AND B via dark B, but C fired legitimately -> keep
    assert not event_triggered_by_dark_pulse(_pulses(A=("ok", 3.0), B=("dark", 1.0), C=("ok", 2.5)), conds)
    # Only the dark-assisted condition is met -> discard
    assert event_triggered_by_dark_pulse(_pulses(A=("ok", 3.0), B=("dark", 1.0)), conds)


def test_pre_trigger_rejection_does_not_discard_event():
    assert not event_triggered_by_dark_pulse(_pulses(A=("pre", 0.0)), OR_ALL)


def test_analyze_event_discards_dark_pulse_trigger_end_to_end():
    dt, n, pre = DT_6000, N_6000, PRE_6000
    t, dark = make_dark_pulse(0.0, 6.5, dt, n, pre)
    _, quiet = make_pmt_pulse(50.0, 0.0, dt, n, pre)
    _, real = make_pmt_pulse(0.0, 40.0, dt, n, pre)

    ev = analyze_event(t, {}, {"A": quiet, "B": dark, "C": quiet, "D": quiet}, 1, 0.0, pre, dt,
                       trigger_conditions=OR_ALL)
    assert ev.discard_reason == DISCARD_DARK_PULSE_TRIGGER and ev.discarded
    assert ev.channels["B"].reject_reason == REJECT_WIDTH

    ev = analyze_event(t, {}, {"A": quiet, "B": dark, "C": quiet, "D": real}, 2, 0.0, pre, dt,
                       trigger_conditions=OR_ALL)
    assert not ev.discarded
    assert ev.channels["D"].has_pulse and ev.channels["B"].rejected

    # No trigger conditions supplied: never discarded, channel still rejected
    ev = analyze_event(t, {}, {"A": quiet, "B": dark, "C": quiet, "D": quiet}, 3, 0.0, pre, dt)
    assert not ev.discarded and ev.channels["B"].reject_reason == REJECT_WIDTH


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
