"""
Tests for locate_na22_peaks (calibration region auto-positioning).

Synthetic Na-22 spectra in raw mV*ns: 511 and 1275 keV photopeaks with
~8 % / 5 % FWHM on a Compton continuum, a backscatter hump near 170 keV,
and a pile-up tail. Peak positions and widths mimic the lab's NaI detectors
(511 keV near 13300 mV*ns, raw ratio ~2.45).
"""

import numpy as np
import pytest

from positron.calibration.energy import (
    locate_na22_peaks,
    CalibrationError,
    AUTO_PEAK_RATIO_FALLBACK,
    AUTO_REGION_HALF_WIDTH_SIGMA,
    AUTO_MIN_EVENTS,
)

MVNS_PER_KEV = 26.0
P511 = 511 * MVNS_PER_KEV
P1275 = 1275 * MVNS_PER_KEV * 0.985   # slight nonlinearity, ratio ~2.46


def na22_spectrum(n, rng, with_1275=True, pileup=True):
    parts = [
        rng.normal(P511, 0.034 * P511, int(n * 0.35)),
        rng.uniform(50 * MVNS_PER_KEV, 340 * MVNS_PER_KEV, int(n * 0.30)),   # 511 Compton
        rng.normal(170 * MVNS_PER_KEV, 40 * MVNS_PER_KEV, int(n * 0.12)),    # backscatter hump
        rng.uniform(340 * MVNS_PER_KEV, 1060 * MVNS_PER_KEV, int(n * 0.15)), # 1275 Compton
    ]
    if with_1275:
        parts.append(rng.normal(P1275, 0.022 * P1275, int(n * 0.06)))
    if pileup:
        parts.append(rng.uniform(1400 * MVNS_PER_KEV, 5000 * MVNS_PER_KEV, int(n * 0.02)))
    x = np.concatenate(parts)
    rng.shuffle(x)
    return x


def test_locates_both_peaks():
    x = na22_spectrum(50000, np.random.default_rng(1))
    r = locate_na22_peaks(x)
    assert r.peak_2_found
    assert r.peak_1 == pytest.approx(P511, rel=0.01)
    assert r.peak_2 == pytest.approx(P1275, rel=0.01)
    # widths within a factor 1.5 of the true sigma
    assert 0.034 * P511 / 1.5 < r.sigma_1 < 0.034 * P511 * 1.5
    assert 0.022 * P1275 / 1.5 < r.sigma_2 < 0.022 * P1275 * 1.5


def test_regions_are_symmetric_about_peaks():
    x = na22_spectrum(20000, np.random.default_rng(2))
    r = locate_na22_peaks(x)
    k = AUTO_REGION_HALF_WIDTH_SIGMA
    assert r.region_1 == pytest.approx((r.peak_1 - k * r.sigma_1, r.peak_1 + k * r.sigma_1))
    assert r.region_2 == pytest.approx((r.peak_2 - k * r.sigma_2, r.peak_2 + k * r.sigma_2))
    # regions do not overlap and are ordered
    assert r.region_1[1] < r.region_2[0]


def test_pileup_does_not_move_regions():
    rng = np.random.default_rng(3)
    x_clean = na22_spectrum(30000, rng, pileup=False)
    x_pile = np.concatenate([x_clean, rng.uniform(1400 * MVNS_PER_KEV, 20000 * MVNS_PER_KEV, 900)])
    a, b = locate_na22_peaks(x_clean), locate_na22_peaks(x_pile)
    assert b.peak_1 == pytest.approx(a.peak_1, rel=0.01)
    assert b.peak_2 == pytest.approx(a.peak_2, rel=0.01)


def test_low_statistics_still_close():
    x = na22_spectrum(1500, np.random.default_rng(4))
    r = locate_na22_peaks(x)
    assert r.peak_1 == pytest.approx(P511, rel=0.03)
    assert r.peak_2 == pytest.approx(P1275, rel=0.04)


def test_fallback_when_1275_absent():
    x = na22_spectrum(20000, np.random.default_rng(5), with_1275=False)
    r = locate_na22_peaks(x)
    assert not r.peak_2_found
    assert r.peak_2 == pytest.approx(AUTO_PEAK_RATIO_FALLBACK * r.peak_1)
    assert r.sigma_2 > r.sigma_1
    assert r.region_2[0] < r.peak_2 < r.region_2[1]


def test_too_few_events_raises():
    x = na22_spectrum(AUTO_MIN_EVENTS * 3, np.random.default_rng(6))[: AUTO_MIN_EVENTS - 1]
    with pytest.raises(CalibrationError):
        locate_na22_peaks(x)


def test_ignores_nonpositive_and_nan():
    x = na22_spectrum(20000, np.random.default_rng(7))
    y = np.concatenate([x, np.full(500, -1.0), np.full(100, np.nan)])
    a, b = locate_na22_peaks(x), locate_na22_peaks(y)
    assert b.peak_1 == pytest.approx(a.peak_1, rel=0.005)
    assert b.peak_2 == pytest.approx(a.peak_2, rel=0.005)
