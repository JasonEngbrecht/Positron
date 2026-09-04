"""
Regression tests for ADC-count -> millivolt conversion.

picosdk.functions.adc2mV iterates int16 samples and multiplies each by the
range (an int). Under NumPy >= 2 (NEP 50) that product stays int16 and wraps
for |sample| > 327, i.e. for any real pulse. These tests pin the correct
values so the conversion can never silently regress with a NumPy upgrade.
"""

import warnings

import numpy as np
import pytest

from positron.scope.acquisition import adc_to_mv, CHANNEL_INPUT_RANGES_MV


PS6000_MAX_ADC = 32512   # fixed on PS6000
RANGE_100MV = 3          # index into CHANNEL_INPUT_RANGES_MV on both series


def test_range_table_matches_picosdk():
    assert CHANNEL_INPUT_RANGES_MV[RANGE_100MV] == 100


def test_full_scale_maps_to_range():
    buf = np.array([PS6000_MAX_ADC, -PS6000_MAX_ADC, 0], dtype=np.int16)
    mv = adc_to_mv(buf, RANGE_100MV, PS6000_MAX_ADC)
    assert mv.dtype == np.float64
    np.testing.assert_allclose(mv, [100.0, -100.0, 0.0])


def test_typical_pulse_does_not_wrap():
    # -1626 counts ~= -5 mV trigger threshold on PS6000. Under the int16
    # wraparound bug this came out as -0.97 mV.
    buf = np.array([-1626], dtype=np.int16)
    mv = adc_to_mv(buf, RANGE_100MV, PS6000_MAX_ADC)
    np.testing.assert_allclose(mv, [-1626 * 100 / PS6000_MAX_ADC])
    assert mv[0] < -4.9


def test_no_overflow_warning_on_full_waveform():
    rng = np.random.default_rng(0)
    buf = rng.integers(-PS6000_MAX_ADC, PS6000_MAX_ADC, size=3749, dtype=np.int16)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any RuntimeWarning fails the test
        mv = adc_to_mv(buf, RANGE_100MV, PS6000_MAX_ADC)
    # Every sample must equal the exact rational conversion
    expected = buf.astype(np.float64) * 100 / PS6000_MAX_ADC
    np.testing.assert_allclose(mv, expected)
    assert np.all(np.abs(mv) <= 100.0)


def test_ps3000a_max_adc_queried_value():
    # PS3000a reports its own max ADC (32767 on 8-bit 3000a units)
    buf = np.array([32767, -32767], dtype=np.int16)
    mv = adc_to_mv(buf, RANGE_100MV, 32767)
    np.testing.assert_allclose(mv, [100.0, -100.0])
