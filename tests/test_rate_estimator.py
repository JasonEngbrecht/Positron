"""Tests for the live-statistics rate estimator (no Qt, fake clock)."""

import pytest

from positron.processing.rate import RateEstimator, format_rate


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def make(**kw):
    clock = Clock()
    return RateEstimator(clock=clock, **kw), clock


def test_not_enough_data():
    est, clock = make()
    assert est.rate() is None
    est.add(20)
    assert est.rate() is None          # one record is not an interval
    est.reset()
    assert est.rate() is None


def test_interval_start_excluded():
    # Three single events at t=0,10,20 -> two 10 s intervals -> 0.1 Hz (not 3/20)
    est, clock = make()
    for dt in (0.0, 10.0, 20.0):
        clock.t = 1000.0 + dt
        est.add(1)
    assert est.rate() == pytest.approx(0.1)


def test_high_rate_steady_average():
    # 2 kHz as 20-event batches every 10 ms for 8 s
    est, clock = make()
    for i in range(800):
        clock.t = 1000.0 + i * 0.010
        est.add(20)
    r = est.rate()
    assert r == pytest.approx(2000.0, rel=0.01)
    # A few ticks later with no new batch (8 ms silence is normal) -> unchanged
    clock.t += 0.008
    assert est.rate() == pytest.approx(r)


def test_high_rate_uses_at_least_min_window():
    est, clock = make(min_window_s=5.0)
    # Rate steps from 1000 to 2000 events/s; the 5 s window smooths it
    t = 1000.0
    for _ in range(600):              # 6 s at 1 kHz (10-event batches / 10 ms)
        clock.t = t; est.add(10); t += 0.010
    for _ in range(200):              # then 2 s at 2 kHz
        clock.t = t; est.add(20); t += 0.010
    r = est.rate()
    # Window covers ~5 s: 3 s at 1 kHz + 2 s at 2 kHz = 7000 events / 5 s
    assert 1300 < r < 1500


def test_low_rate_holds_between_events_then_decays():
    est, clock = make(min_events=10)
    # 0.05 Hz: one event every 20 s
    for i in range(3):
        clock.t = 1000.0 + i * 20.0
        est.add(1)
    r = est.rate()
    assert r == pytest.approx(0.05)

    # 59 s of silence (< 3x expected 20 s interval): reading unchanged
    clock.t = 1040.0 + 59.0
    assert est.rate() == pytest.approx(0.05)

    # Continuity at the 60 s boundary, then a clear decrease at 100 s
    clock.t = 1040.0 + 60.0
    assert est.rate() == pytest.approx(0.05, rel=1e-9)
    clock.t = 1040.0 + 100.0
    r_late = est.rate()
    assert r_late < 0.04
    assert r_late == pytest.approx(2 / (40.0 + 40.0))


def test_low_rate_updates_only_on_events():
    est, clock = make()
    times = [0, 12, 31, 45, 70]        # irregular arrivals, mean ~17.5 s
    for dt in times:
        clock.t = 1000.0 + dt
        est.add(1)
    r = est.rate()
    assert r == pytest.approx(4 / 70.0)
    clock.t = 1000.0 + 70 + 30        # within the silence tolerance
    assert est.rate() == pytest.approx(r)
    clock.t = 1000.0 + 72
    est.add(1)
    assert est.rate() == pytest.approx(5 / 72.0)


def test_partial_batch_counts_are_weighted():
    est, clock = make(min_events=10)
    # Two partial batches of 7 and 3 events one second apart, then 5 more
    clock.t = 1000.0; est.add(7)
    clock.t = 1001.0; est.add(3)
    clock.t = 1002.0; est.add(5)
    # Interval start = first record (excluded): 8 events over 2 s
    assert est.rate() == pytest.approx(4.0)


def test_format_rate():
    assert format_rate(None) == "-- events/s"
    assert format_rate(2450.3) == "2450 events/s"
    assert format_rate(45.26) == "45.3 events/s"
    assert format_rate(2.345) == "2.35 events/s"
    assert format_rate(0.05) == "0.05 events/s"
    assert format_rate(0.0523) == "0.0523 events/s"
    assert format_rate(0.005) == "0.005 events/s"
    assert format_rate(0.0) == "0 events/s"
