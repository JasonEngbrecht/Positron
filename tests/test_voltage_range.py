"""
Tests for the input voltage range selection in positron.scope.driver.

The production range is 100 mV; POSITRON_RANGE_MV overrides it for
clipping / linearity studies. The range code must stay consistent with the
ADC-to-mV conversion table.
"""

import pytest

from positron.scope.driver import (
    CHANNEL_INPUT_RANGES_MV,
    DEFAULT_VOLTAGE_RANGE_MV,
    SUPPORTED_VOLTAGE_RANGES_MV,
    VOLTAGE_RANGE_ENV,
    configured_voltage_range_mv,
    voltage_range_code,
)
from positron.scope.acquisition import adc_to_mv

MAX_ADC = 32512


def test_default_is_100mv(monkeypatch):
    monkeypatch.delenv(VOLTAGE_RANGE_ENV, raising=False)
    assert configured_voltage_range_mv() == 100
    assert DEFAULT_VOLTAGE_RANGE_MV == 100
    assert voltage_range_code(100) == 3


def test_empty_env_means_default(monkeypatch):
    monkeypatch.setenv(VOLTAGE_RANGE_ENV, "  ")
    assert configured_voltage_range_mv() == 100


@pytest.mark.parametrize("range_mv", SUPPORTED_VOLTAGE_RANGES_MV)
def test_override_round_trips_through_code(monkeypatch, range_mv):
    monkeypatch.setenv(VOLTAGE_RANGE_ENV, str(range_mv))
    assert configured_voltage_range_mv() == range_mv
    code = voltage_range_code(range_mv)
    assert CHANNEL_INPUT_RANGES_MV[code] == range_mv
    # Full-scale ADC count converts to the range itself
    assert adc_to_mv([-MAX_ADC], code, MAX_ADC)[0] == pytest.approx(-range_mv)


def test_200mv_code_is_4(monkeypatch):
    # PS3000A_RANGE / PS6000_RANGE enum layout: 10, 20, 50, 100, 200, ...
    assert voltage_range_code(200) == 4


@pytest.mark.parametrize("bad", ["abc", "150", "1000", "0"])
def test_invalid_override_rejected(monkeypatch, bad):
    monkeypatch.setenv(VOLTAGE_RANGE_ENV, bad)
    with pytest.raises(ValueError):
        configured_voltage_range_mv()


def test_same_millivolts_regardless_of_range():
    """A -50 mV signal is -50 mV at either range (different ADC counts)."""
    adc_100 = -MAX_ADC // 2
    adc_200 = -MAX_ADC // 4
    assert adc_to_mv([adc_100], voltage_range_code(100), MAX_ADC)[0] == pytest.approx(-50, abs=0.01)
    assert adc_to_mv([adc_200], voltage_range_code(200), MAX_ADC)[0] == pytest.approx(-50, abs=0.01)
