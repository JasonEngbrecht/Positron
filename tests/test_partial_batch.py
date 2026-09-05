"""
Engine-level tests of the capture loop using a fake driver (no hardware).

Covers the partial-batch path that makes low count rates work: when the
batch does not fill within the wait budget, the engine stops the scope,
reads however many captures completed, processes exactly those, and
re-arms. Zero completed captures re-arms silently.
"""

import pytest

from positron.processing.events import EventStorage
from positron.scope.acquisition import AcquisitionEngine
from positron.scope.connection import ScopeInfo


SAMPLES = 400
PRE = 100
MAX_ADC = 32512
BATCH = 20


class FakeDriver:
    series = "fake"
    voltage_range_code_100mv = 3
    default_batch_size = BATCH
    timebase_trial_samples = 1

    def __init__(self, ready: bool, completed: int):
        self.ready = ready            # what is_ready() reports
        self.completed = completed    # what get_no_of_captures() reports
        self.buffers = {}             # (channel, segment) -> registered array
        self.calls = []

    def memory_segments(self, n, s):
        self.calls.append("memory_segments")

    def set_no_of_captures(self, n):
        self.calls.append("set_no_of_captures")

    def run_block(self, pre, post, tb):
        self.calls.append("run_block")

    def is_ready(self):
        return self.ready

    def stop(self):
        self.calls.append("stop")

    def close(self):
        pass

    def get_no_of_captures(self):
        self.calls.append("get_no_of_captures")
        return self.completed

    def register_buffer(self, ch, seg, bmax, bmin, n):
        self.buffers[(ch, seg)] = bmax

    def get_values_bulk(self, num_samples, num_segments):
        self.calls.append(f"get_values_bulk:{num_segments}")
        # Segment k gets a negative pulse of pulse_counts(k) on every channel
        for (ch, seg), buf in self.buffers.items():
            buf[:] = 0
            if seg < num_segments:
                # 100 samples wide so it passes the analysis width cut
                buf[PRE + 10:PRE + 110] = -pulse_counts(seg)
        return num_samples


def pulse_counts(segment: int) -> int:
    """Synthetic pulse depth: 3000 counts (~9 mV) rising 1400/segment, max ~29600 (fits int16)."""
    return 3000 + segment * 1400


def make_engine(driver):
    info = ScopeInfo(series="fake", variant="", serial="", handle=None,
                     max_adc=MAX_ADC, api_module=None)
    storage = EventStorage(max_capacity=1000)
    eng = AcquisitionEngine(
        scope_info=info, event_storage=storage, batch_size=BATCH,
        sample_count=SAMPLES, pre_trigger_samples=PRE, sample_interval_ns=0.8,
        voltage_range_code=3, max_adc=MAX_ADC, driver=driver,
    )
    eng._setup_rapid_block()
    eng._allocate_buffers()
    eng._register_buffers()
    eng.partial_read_after_s = 0.0   # expire the wait budget immediately
    # Surface engine errors in test output instead of a bare False
    eng.errors = []
    eng.acquisition_error.connect(eng.errors.append)
    return eng, storage


def capture_ok(eng) -> bool:
    ok = eng._capture_batch()
    assert not eng.errors, eng.errors
    return ok


def test_partial_batch_reads_only_completed_captures():
    drv = FakeDriver(ready=False, completed=3)
    eng, storage = make_engine(drv)

    assert capture_ok(eng) is True
    assert storage.get_count() == 3
    assert eng.total_captures == 3
    assert "stop" in drv.calls
    assert "get_values_bulk:3" in drv.calls
    # Armed once at entry, re-armed once after the download
    assert drv.calls.count("run_block") == 2
    assert drv.calls.index("get_values_bulk:3") < len(drv.calls) - 1

    # Events carry the right per-segment amplitude (segment k -> pulse_counts(k))
    for k, ev in enumerate(storage.get_all_events()):
        expected_mv = pulse_counts(k) * 100 / MAX_ADC
        assert ev.channels["A"].has_pulse
        assert ev.channels["A"].peak_mv == pytest.approx(expected_mv, rel=1e-6)


def test_zero_completed_captures_rearms_without_data():
    drv = FakeDriver(ready=False, completed=0)
    eng, storage = make_engine(drv)

    assert capture_ok(eng) is True
    assert storage.get_count() == 0
    assert eng.total_captures == 0
    assert not any(c.startswith("get_values_bulk") for c in drv.calls)
    assert drv.calls[-1] == "run_block"          # re-armed
    assert eng._armed is True


def test_full_batch_path_unchanged():
    drv = FakeDriver(ready=True, completed=BATCH)
    eng, storage = make_engine(drv)

    assert capture_ok(eng) is True
    assert storage.get_count() == BATCH
    assert "stop" not in drv.calls
    assert "get_no_of_captures" not in drv.calls
    assert f"get_values_bulk:{BATCH}" in drv.calls


def test_stop_request_exits_poll_loop():
    drv = FakeDriver(ready=False, completed=5)
    eng, storage = make_engine(drv)
    eng.partial_read_after_s = 1e9   # never expire: only the stop flag can exit
    eng.stop()

    assert eng._capture_batch() is False
    assert storage.get_count() == 0
