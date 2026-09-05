"""
Event-rate estimation for the live statistics readout.

Designed to read sensibly from ~0.01 Hz to several kHz:

- At high rates the estimate is an average over at least `min_window_s`
  seconds of batches (stable, updates every batch).
- At low rates it is `min_events` events divided by the time they spanned,
  so the value changes only when a new event arrives and then holds.
- If the source goes quiet for much longer than the expected interval, the
  estimate decays continuously so a removed source becomes visible.

No Qt dependency; the clock is injectable for tests.
"""

import time
from collections import deque
from typing import Callable, Deque, Optional, Tuple


class RateEstimator:
    """Interval-based rate estimator fed with (timestamp, count) batch records."""

    def __init__(self, min_window_s: float = 5.0, min_events: int = 10,
                 max_window_s: float = 3600.0, max_records: int = 5000,
                 clock: Callable[[], float] = time.monotonic):
        """
        Args:
            min_window_s: at high rates, average over at least this long
            min_events: at low rates, average over at least this many events
            max_window_s: records older than this (relative to the newest
                record) are discarded
            max_records: hard cap on stored records (bounds memory at kHz rates)
            clock: monotonic time source
        """
        self.min_window_s = min_window_s
        self.min_events = min_events
        self.max_window_s = max_window_s
        self._clock = clock
        self._records: Deque[Tuple[float, int]] = deque(maxlen=max_records)

    def reset(self) -> None:
        self._records.clear()

    def add(self, count: int, t: Optional[float] = None) -> None:
        """Record one batch of `count` events arriving at time `t` (default: now)."""
        if count <= 0:
            return
        if t is None:
            t = self._clock()
        self._records.append((t, count))
        cutoff = t - self.max_window_s
        while self._records and self._records[0][0] < cutoff:
            self._records.popleft()

    def rate(self, now: Optional[float] = None) -> Optional[float]:
        """
        Current rate estimate in events/s, or None if fewer than two batches
        have been recorded.
        """
        if len(self._records) < 2:
            return None
        if now is None:
            now = self._clock()

        t_newest = self._records[-1][0]

        # Walk back from the newest record accumulating counts until the
        # window holds enough events AND enough time. The record where the
        # walk stops marks the interval start; its own count is excluded so
        # that n events / span is unbiased.
        n = 0
        t_old = None
        for t_k, c_k in reversed(self._records):
            if n >= self.min_events and t_newest - t_k >= self.min_window_s:
                t_old = t_k
                break
            n += c_k
        if t_old is None:
            # Ran out of records: the oldest one is the interval start
            t_old, c_oldest = self._records[0]
            n -= c_oldest

        span = t_newest - t_old
        if n <= 0 or span <= 0:
            return None

        # Silence guard: only bite once the gap since the last event is
        # implausibly long (3x the expected interval, and at least 1 s), then
        # grow the denominator continuously so the reading decays smoothly.
        expected_interval = span / n
        silence = now - t_newest
        extra = max(0.0, silence - max(3.0 * expected_interval, 1.0))
        return n / (span + extra)


def format_rate(rate: Optional[float]) -> str:
    """Format a rate with precision appropriate to its magnitude."""
    if rate is None:
        return "-- events/s"
    if rate >= 100:
        return f"{rate:.0f} events/s"
    if rate >= 10:
        return f"{rate:.1f} events/s"
    if rate >= 1:
        return f"{rate:.2f} events/s"
    if rate <= 0:
        return "0 events/s"
    return f"{rate:.3g} events/s"
