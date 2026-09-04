"""
Tests for the temporary AnomalyDumper diagnostic in the acquisition engine.
"""

import numpy as np

from positron.processing.pulse import ChannelPulse, EventData
from positron.scope import acquisition
from positron.scope.acquisition import AnomalyDumper, ANOMALY_DUMP_ENV


def _event(event_id, energy_d=1000.0, timing_d=5.0, has_pulse_d=True):
    quiet = ChannelPulse(timing_ns=0.0, energy=0.0, peak_mv=0.0, has_pulse=False)
    return EventData(
        event_id=event_id,
        timestamp=0.0,
        channels={
            "A": quiet, "B": quiet, "C": quiet,
            "D": ChannelPulse(timing_ns=timing_d, energy=energy_d, peak_mv=30.0, has_pulse=has_pulse_d),
        },
    )


def _waveforms(n, samples=50):
    return [{ch: np.full(samples, float(i)) for ch in "ABCD"} for i in range(n)]


def test_disabled_without_env(monkeypatch):
    monkeypatch.delenv(ANOMALY_DUMP_ENV, raising=False)
    dumper = AnomalyDumper("6402D", 0.8, 10, 0.5)
    assert not dumper.enabled
    assert dumper.directory is None


def test_is_anomalous():
    assert AnomalyDumper.is_anomalous(_event(1, energy_d=-5.0))
    assert AnomalyDumper.is_anomalous(_event(2, timing_d=0.8))
    assert not AnomalyDumper.is_anomalous(_event(3))
    # A no-pulse channel never counts, whatever its numbers say
    assert not AnomalyDumper.is_anomalous(_event(4, energy_d=-5.0, has_pulse_d=False))


def test_dump_writes_anomalies_with_neighbours(monkeypatch, tmp_path):
    monkeypatch.setenv(ANOMALY_DUMP_ENV, "1")
    monkeypatch.setattr(acquisition.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(acquisition, "ANOMALY_NORMAL_FILES", 1)

    dumper = AnomalyDumper("6402D", 0.8, 10, 0.5)
    assert dumper.enabled
    assert dumper.directory.parent == tmp_path / ".positron" / "debug"

    time_ns = (np.arange(50) - 10) * 0.8
    events = [_event(100), _event(101, energy_d=-300.0), _event(102)]
    dumper.process_batch(time_ns, _waveforms(3), events)

    assert dumper.n_events == 3
    assert dumper.n_anomalies == 1
    assert dumper.n_saved == 1
    assert dumper.n_normal_saved == 1

    files = sorted(p.name for p in dumper.directory.glob("*.npz"))
    assert files == ["anomaly_0000101.npz", "normal_0000100.npz"]

    d = np.load(dumper.directory / "anomaly_0000101.npz")
    assert int(d["event_id"]) == 101
    assert int(d["prev_event_id"]) == 100 and int(d["next_event_id"]) == 102
    assert np.all(d["D"] == 1.0) and np.all(d["prev_D"] == 0.0) and np.all(d["next_D"] == 2.0)
    assert float(d["D_energy"]) == -300.0
    assert bool(d["D_has_pulse"]) is True
    assert int(d["pre_trigger_samples"]) == 10
    np.testing.assert_allclose(d["time_ns"], time_ns)

    # The first (normal) event has no previous neighbour
    n = np.load(dumper.directory / "normal_0000100.npz")
    assert "prev_event_id" not in n.files and "next_event_id" in n.files


def test_file_cap_keeps_counting(monkeypatch, tmp_path):
    monkeypatch.setenv(ANOMALY_DUMP_ENV, "1")
    monkeypatch.setattr(acquisition.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(acquisition, "ANOMALY_MAX_FILES", 2)
    monkeypatch.setattr(acquisition, "ANOMALY_NORMAL_FILES", 0)
    monkeypatch.setattr(acquisition, "ANOMALY_MIN_SPACING_S", 0.0)

    dumper = AnomalyDumper("3406D", 8.0, 125, 0.5)
    events = [_event(i, energy_d=-1.0) for i in range(5)]
    dumper.process_batch(np.arange(50) * 8.0, _waveforms(5), events)

    assert dumper.n_anomalies == 5
    assert dumper.n_saved == 2
    assert len(list(dumper.directory.glob("anomaly_*.npz"))) == 2
    dumper.close()  # just logs


def test_saved_anomalies_are_time_spaced(monkeypatch, tmp_path):
    monkeypatch.setenv(ANOMALY_DUMP_ENV, "1")
    monkeypatch.setattr(acquisition.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(acquisition, "ANOMALY_NORMAL_FILES", 0)
    monkeypatch.setattr(acquisition, "ANOMALY_MIN_SPACING_S", 10.0)

    dumper = AnomalyDumper("6402D", 0.8, 10, 0.5)
    events = [_event(i, energy_d=-1.0) for i in range(5)]
    dumper.process_batch(np.arange(50) * 0.8, _waveforms(5), events)

    # All counted, only the first saved: the rest arrived within the spacing
    assert dumper.n_anomalies == 5
    assert dumper.n_saved == 1
