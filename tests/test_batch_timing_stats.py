"""Tests for the acquisition engine's periodic timing summary."""

from positron.scope.acquisition import BatchTimingStats


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_summary_only_when_window_elapses():
    clock = FakeClock()
    stats = BatchTimingStats(interval_s=5.0, clock=clock)

    clock.t += 1.0
    assert stats.record(0.5, 0.1, 0.05, 20) is None
    clock.t += 1.0
    assert stats.record(0.5, 0.1, 0.05, 20) is None


def test_summary_values_and_reset():
    clock = FakeClock()
    stats = BatchTimingStats(interval_s=5.0, clock=clock)

    # Two batches of 20 captures over exactly 5 s of wall time.
    clock.t += 2.5
    assert stats.record(wait_s=1.0, download_s=0.2, process_s=0.1, captures=20) is None
    clock.t += 2.5
    line = stats.record(wait_s=1.0, download_s=0.2, process_s=0.1, captures=20)

    assert line is not None
    assert "8 events/s" in line              # 40 captures / 5 s
    assert "0.4 batches/s" in line
    assert "(20 captures/batch)" in line
    assert "wait 1000.0 ms" in line
    assert "download 200.0 ms" in line
    assert "process 100.0 ms" in line
    # other = (5.0 - 2*(1.0+0.2+0.1)) / 2 batches = 1.2 s per batch
    assert "other 1200.0 ms" in line

    # Window reset: the next record starts a fresh window
    clock.t += 1.0
    assert stats.record(0.1, 0.1, 0.1, 20) is None


def test_other_never_negative():
    clock = FakeClock()
    stats = BatchTimingStats(interval_s=1.0, clock=clock)
    clock.t += 1.0
    # Phases sum to more than wall time (clock skew) -> other clamps to 0
    line = stats.record(wait_s=2.0, download_s=0.0, process_s=0.0, captures=1)
    assert "other 0.0 ms" in line
