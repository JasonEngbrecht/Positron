"""Tests for the analysis-level pile-up event removal."""

import pytest

from positron.config import ChannelCalibration
from positron.processing.pulse import ChannelPulse, EventData
from positron.panels.analysis.utils import remove_pileup_events, MAX_EVENT_ENERGY_KEV


def cal(gain=0.04, offset=-20.0, calibrated=True):
    return ChannelCalibration(gain=gain, offset=offset, calibrated=calibrated)


def pulse(raw, has_pulse=True):
    return ChannelPulse(timing_ns=0.0, energy=raw, peak_mv=50.0, has_pulse=has_pulse)


def event(i, **raw_by_channel):
    return EventData(event_id=i, timestamp=float(i),
                     channels={ch: pulse(raw) for ch, raw in raw_by_channel.items()})


CALS = {'A': cal(), 'B': cal(), 'C': cal(), 'D': cal()}
RAW_511 = (511 + 20) / 0.04       # 13275 mV*ns
RAW_PILEUP = (3500 + 20) / 0.04   # 88000 mV*ns


def test_normal_events_kept():
    events = [event(1, A=RAW_511, B=RAW_511), event(2, C=RAW_511)]
    kept, removed = remove_pileup_events(events, CALS)
    assert removed == 0
    assert kept == events


def test_pileup_on_one_channel_removes_whole_event():
    events = [event(1, A=RAW_511, D=RAW_PILEUP), event(2, B=RAW_511)]
    kept, removed = remove_pileup_events(events, CALS)
    assert removed == 1
    assert [e.event_id for e in kept] == [2]


def test_threshold_is_exclusive_at_limit():
    raw_at_limit = (MAX_EVENT_ENERGY_KEV + 20) / 0.04
    kept, removed = remove_pileup_events([event(1, A=raw_at_limit)], CALS)
    assert removed == 0 and len(kept) == 1
    kept, removed = remove_pileup_events([event(1, A=raw_at_limit * 1.001)], CALS)
    assert removed == 1 and kept == []


def test_uncalibrated_channel_ignored():
    cals = dict(CALS, D=cal(calibrated=False))
    kept, removed = remove_pileup_events([event(1, A=RAW_511, D=RAW_PILEUP)], cals)
    assert removed == 0 and len(kept) == 1


def test_no_calibration_at_all_keeps_everything():
    cals = {ch: cal(calibrated=False) for ch in 'ABCD'}
    events = [event(1, A=RAW_PILEUP)]
    kept, removed = remove_pileup_events(events, cals)
    assert removed == 0 and kept == events


def test_rejected_pulse_not_judged():
    ev = EventData(event_id=1, timestamp=0.0, channels={'A': pulse(RAW_PILEUP, has_pulse=False)})
    kept, removed = remove_pileup_events([ev], CALS)
    assert removed == 0 and len(kept) == 1


def test_custom_threshold():
    kept, removed = remove_pileup_events([event(1, A=RAW_511)], CALS, max_kev=500.0)
    assert removed == 1
