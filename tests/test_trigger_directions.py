"""
Tests for the trigger direction rule: channels used on their own trigger on
a falling edge; channels combined by AND use the gated BELOW direction so
the AND is an overlap coincidence rather than a same-instant edge match.
"""

import ctypes

import pytest

from positron.config import TriggerCondition, TriggerConfig
from positron.scope.connection import ScopeInfo
from positron.scope.driver import PS6000Driver, PS3000aDriver
from positron.scope.trigger import classify_trigger_directions, TriggerConfigurator


def cond(*channels):
    return TriggerCondition(enabled=True, channels=list(channels))


def test_single_channel_conditions_are_falling():
    falling, gated = classify_trigger_directions([cond("A"), cond("B"), cond("C"), cond("D")])
    assert falling == ["A", "B", "C", "D"]
    assert gated == []


def test_and_conditions_are_gated():
    falling, gated = classify_trigger_directions([cond("A", "D"), cond("B", "C")])
    assert falling == []
    assert gated == ["A", "B", "C", "D"]


def test_mixed_conditions():
    falling, gated = classify_trigger_directions([cond("A"), cond("B", "C")])
    assert falling == ["A"]
    assert gated == ["B", "C"]


def test_channel_in_both_kinds_is_gated():
    falling, gated = classify_trigger_directions([cond("A"), cond("A", "D")])
    assert falling == []
    assert gated == ["A", "D"]


def test_three_way_and():
    falling, gated = classify_trigger_directions([cond("A", "B", "C")])
    assert (falling, gated) == ([], ["A", "B", "C"])


# ---- what reaches the SDK ----

class FakePS6000:
    """Records the direction arguments of ps6000SetTriggerChannelDirections."""

    def __init__(self):
        self.directions = None

    def ps6000SetTriggerChannelDirections(self, handle, a, b, c, d, ext, aux):
        self.directions = (a, b, c, d)
        return 0  # PICO_OK


class FakePS3000a:
    PS3000A_THRESHOLD_DIRECTION = {
        "PS3000A_ABOVE": 0, "PS3000A_BELOW": 1, "PS3000A_NONE": 1,
        "PS3000A_RISING": 2, "PS3000A_FALLING": 3,
    }
    PS3000A_RANGE = {"PS3000A_200MV": 4}

    def __init__(self):
        self.directions = None

    def ps3000aSetTriggerChannelDirections(self, handle, a, b, c, d, ext, aux):
        self.directions = (a, b, c, d)
        return 0


def info(series, api):
    return ScopeInfo(series=series, variant="fake", serial="0", handle=ctypes.c_int16(0),
                     max_adc=32512, api_module=api)


def test_ps6000_directions_falling_and_below():
    api = FakePS6000()
    drv = PS6000Driver(info("6000", api))
    drv.set_trigger_directions(["A", "B", "C", "D"], gated_channels=["B", "C"])
    # FALLING = 3, BELOW = 1
    assert api.directions == (3, 1, 1, 3)


def test_ps6000_non_participating_is_none():
    api = FakePS6000()
    drv = PS6000Driver(info("6000", api))
    drv.set_trigger_directions(["A"])
    assert api.directions == (3, 2, 2, 2)   # NONE = 2 on PS6000


def test_ps3000a_directions_falling_and_below():
    api = FakePS3000a()
    drv = PS3000aDriver(info("3000a", api))
    drv.set_trigger_directions(["A", "D"], gated_channels=["A", "D"])
    assert api.directions == (1, 1, 1, 1)   # BELOW = 1; NONE happens to be 1 too on PS3000a
    drv.set_trigger_directions(["A", "B"], gated_channels=[])
    assert api.directions == (3, 3, 1, 1)


class RecordingDriver:
    """Minimal ScopeDriver stand-in for TriggerConfigurator."""
    series = "fake"

    def __init__(self):
        self.calls = []

    def set_trigger_properties(self, channels, threshold_mv, hysteresis, auto_trigger_ms):
        self.calls.append(("properties", list(channels)))

    def set_trigger_conditions(self, condition_channel_lists):
        self.calls.append(("conditions", [list(c) for c in condition_channel_lists]))

    def set_trigger_directions(self, channels, gated_channels=()):
        self.calls.append(("directions", list(channels), list(gated_channels)))


def test_configurator_passes_gated_channels():
    config = TriggerConfig()
    config.condition_1 = cond("A", "D")
    config.condition_2 = cond("B")
    drv = RecordingDriver()
    tc = TriggerConfigurator(info("6000", None), driver=drv)
    applied = tc.apply_trigger(config)
    assert ("directions", ["A", "B", "D"], ["A", "D"]) in drv.calls
    assert "Below" in applied.direction and "A, D" in applied.direction


def test_configurator_plain_falling_when_no_and():
    config = TriggerConfig()
    config.condition_1 = cond("A")
    drv = RecordingDriver()
    tc = TriggerConfigurator(info("6000", None), driver=drv)
    applied = tc.apply_trigger(config)
    assert ("directions", ["A"], []) in drv.calls
    assert applied.direction == "Falling"
