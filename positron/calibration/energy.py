"""
Energy calibration module for converting raw pulse energies to keV.

Implements two-point linear calibration using Na-22 source peaks:
- Peak 1: 511 keV (positron annihilation)
- Peak 2: 1275 keV (Na-22 gamma)

Calibration equation:
    E_keV = gain * E_raw + offset

Where:
    gain = (E2_keV - E1_keV) / (E2_raw - E1_raw)
    offset = E1_keV - gain * E1_raw
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np


# Na-22 calibration peak energies (keV)
PEAK_1_KEV = 511.0   # Positron annihilation
PEAK_2_KEV = 1275.0  # Na-22 gamma

# Auto-positioning of the calibration regions (locate_na22_peaks).
# The raw 1275/511 peak ratio measured on the lab's NaI detectors is
# 2.42-2.50 (a linear detector would give 2.495); the 1062 keV Compton edge
# sits near 2.1, so the search window below excludes it.
AUTO_PEAK_RATIO_MIN = 2.2
AUTO_PEAK_RATIO_MAX = 2.7
AUTO_PEAK_RATIO_FALLBACK = 2.45   # used when no 1275 keV peak is found
AUTO_REGION_HALF_WIDTH_SIGMA = 2.5
AUTO_NUM_BINS = 300
AUTO_MIN_EVENTS = 200
AUTO_UPPER_PERCENTILE = 99.5      # coarse-pass axis top: keeps pile-up from stretching it
AUTO_AXIS_FACTOR = 3.2            # fine-pass axis top as a multiple of the 511 keV candidate
AUTO_LOW_CUT_RATIO = 0.5          # ignore below this fraction of the candidate (noise, backscatter)
AUTO_MIN_PEAK_COUNTS = 2.0        # smoothed counts a 1275 keV local maximum must reach
AUTO_FALLBACK_RESOLUTION = 0.08   # FWHM / peak at 511 keV assumed when the width cannot be measured
AUTO_SIGMA_CLAMP = (0.5, 2.0)     # measured sigma is kept within this factor of the assumed one
_FWHM_TO_SIGMA = 1.0 / 2.3548


@dataclass
class AutoRegions:
    """Result of locate_na22_peaks: peak estimates and the regions built from them."""
    peak_1: float            # 511 keV peak position (raw mV·ns)
    sigma_1: float
    peak_2: float            # 1275 keV peak position (raw mV·ns)
    sigma_2: float
    peak_2_found: bool       # False when peak_2 is the ratio-based fallback
    region_1: Tuple[float, float]
    region_2: Tuple[float, float]


def _peak_sigma(smooth: np.ndarray, centers: np.ndarray, idx: int) -> Optional[float]:
    """
    Sigma of the peak at bin idx from its full width at half maximum, walking
    down each side with linear interpolation. None if either side never drops
    to half maximum inside the histogram.
    """
    half = 0.5 * smooth[idx]

    def cross(step: int) -> Optional[float]:
        i = idx
        while 0 <= i + step < len(smooth):
            j = i + step
            if smooth[j] <= half:
                frac = (smooth[i] - half) / (smooth[i] - smooth[j]) if smooth[i] != smooth[j] else 0.0
                return centers[i] + frac * (centers[j] - centers[i])
            i = j
        return None

    left, right = cross(-1), cross(+1)
    if left is None or right is None:
        return None
    return (right - left) * _FWHM_TO_SIGMA


def _clamped_sigma(measured: Optional[float], peak: float, kev: float) -> float:
    """
    Keep a measured peak sigma within AUTO_SIGMA_CLAMP of the value expected
    from AUTO_FALLBACK_RESOLUTION (FWHM/peak at 511 keV, scaling as
    1/sqrt(E)); use the expected value when none was measured. Protects the
    region width against noisy histograms at low statistics.
    """
    expected = AUTO_FALLBACK_RESOLUTION * np.sqrt(PEAK_1_KEV / kev) * peak * _FWHM_TO_SIGMA
    if measured is None or measured <= 0:
        return float(expected)
    lo, hi = AUTO_SIGMA_CLAMP
    return float(min(max(measured, lo * expected), hi * expected))


def locate_na22_peaks(
    energies: np.ndarray,
    num_bins: int = AUTO_NUM_BINS,
    half_width_sigma: float = AUTO_REGION_HALF_WIDTH_SIGMA,
) -> AutoRegions:
    """
    Locate the 511 and 1275 keV photopeaks in a raw Na-22 spectrum and build
    a calibration region around each (peak +- half_width_sigma * sigma).

    The 511 keV photopeak is the tallest feature of a Na-22 spectrum once the
    lowest part of the axis (noise, backscatter hump) is excluded. The
    1275 keV peak is the tallest local maximum between AUTO_PEAK_RATIO_MIN and
    AUTO_PEAK_RATIO_MAX times the 511 position; if none is found the region
    is placed at AUTO_PEAK_RATIO_FALLBACK times the 511 position with a width
    scaled from the 511 peak (resolution ~ 1/sqrt(E)) and peak_2_found is
    False so the caller can warn.

    Args:
        energies: Raw energies (mV·ns) of accepted pulses
        num_bins: Histogram bins (fine pass covers 0 .. 3.2 x the 511 keV peak)
        half_width_sigma: Region half-width in units of the peak sigma

    Returns:
        AutoRegions

    Raises:
        CalibrationError: Too few events, or no 511 keV peak could be located
    """
    energies = np.asarray(energies, dtype=float)
    energies = energies[np.isfinite(energies) & (energies > 0)]
    if len(energies) < AUTO_MIN_EVENTS:
        raise CalibrationError(
            f"Need at least {AUTO_MIN_EVENTS} pulses to locate the peaks (have {len(energies)})"
        )

    # Pass 1 (coarse): tallest bin of the whole spectrum is the 511 keV
    # photopeak candidate. The axis top is a high percentile so pile-up
    # cannot stretch it, and the first bins (trigger-threshold edge) are skipped.
    upper = float(np.percentile(energies, AUTO_UPPER_PERCENTILE))
    if upper <= 0:
        raise CalibrationError("Energy data has no positive range")
    coarse, edges = np.histogram(energies, bins=num_bins, range=(0.0, upper))
    coarse_centers = 0.5 * (edges[:-1] + edges[1:])
    coarse_smooth = np.convolve(coarse.astype(float), np.ones(5) / 5.0, mode="same")
    skip = 3
    candidate = float(coarse_centers[skip + int(np.argmax(coarse_smooth[skip:]))])
    if candidate <= 0 or coarse_smooth[skip:].max() <= 0:
        raise CalibrationError("No 511 keV peak found in the spectrum")

    # Pass 2 (fine): axis 0 .. AUTO_AXIS_FACTOR x candidate so the bin width
    # is a fixed fraction of the peak position regardless of pile-up.
    top = AUTO_AXIS_FACTOR * candidate
    hist, edges = np.histogram(energies, bins=num_bins, range=(0.0, top))
    centers = 0.5 * (edges[:-1] + edges[1:])
    smooth = np.convolve(hist.astype(float), np.ones(5) / 5.0, mode="same")

    # 511 keV: tallest bin above AUTO_LOW_CUT_RATIO x candidate (skips the
    # noise edge and the backscatter hump)
    low_cut = int(np.searchsorted(centers, AUTO_LOW_CUT_RATIO * candidate))
    idx_1 = low_cut + int(np.argmax(smooth[low_cut:]))
    if smooth[idx_1] <= 0:
        raise CalibrationError("No 511 keV peak found in the spectrum")
    peak_1 = float(centers[idx_1])
    sigma_1 = _clamped_sigma(_peak_sigma(smooth, centers, idx_1), peak_1, PEAK_1_KEV)

    # 1275 keV: tallest local maximum inside the ratio window
    lo_idx = int(np.searchsorted(centers, AUTO_PEAK_RATIO_MIN * peak_1))
    hi_idx = min(int(np.searchsorted(centers, AUTO_PEAK_RATIO_MAX * peak_1)), len(smooth) - 1)
    peak_2_found = False
    peak_2 = sigma_2 = None
    if hi_idx - lo_idx >= 5:
        window = smooth[lo_idx:hi_idx]
        idx_2 = lo_idx + int(np.argmax(window))
        interior = lo_idx < idx_2 < hi_idx - 1
        is_local_max = interior and smooth[idx_2] >= smooth[idx_2 - 1] and smooth[idx_2] >= smooth[idx_2 + 1]
        if is_local_max and smooth[idx_2] >= AUTO_MIN_PEAK_COUNTS:
            sigma_2 = _peak_sigma(smooth, centers, idx_2)
            if sigma_2 is not None and sigma_2 > 0:
                peak_2 = float(centers[idx_2])
                sigma_2 = _clamped_sigma(sigma_2, peak_2, PEAK_2_KEV)
                peak_2_found = True
    if not peak_2_found:
        peak_2 = AUTO_PEAK_RATIO_FALLBACK * peak_1
        # Relative resolution scales as 1/sqrt(E)
        sigma_2 = sigma_1 * AUTO_PEAK_RATIO_FALLBACK * np.sqrt(PEAK_1_KEV / PEAK_2_KEV)

    return AutoRegions(
        peak_1=peak_1, sigma_1=float(sigma_1),
        peak_2=float(peak_2), sigma_2=float(sigma_2),
        peak_2_found=peak_2_found,
        region_1=(peak_1 - half_width_sigma * sigma_1, peak_1 + half_width_sigma * sigma_1),
        region_2=(peak_2 - half_width_sigma * sigma_2, peak_2 + half_width_sigma * sigma_2),
    )


class CalibrationError(Exception):
    """Exception raised for calibration-related errors."""
    pass


def calculate_two_point_calibration(
    peak_1_raw: float,
    peak_2_raw: float,
    peak_1_kev: float = PEAK_1_KEV,
    peak_2_kev: float = PEAK_2_KEV
) -> Tuple[float, float]:
    """
    Calculate linear calibration parameters from two peaks.
    
    Args:
        peak_1_raw: Raw energy value of first peak (mV·ns)
        peak_2_raw: Raw energy value of second peak (mV·ns)
        peak_1_kev: Known energy of first peak (keV, default: 511)
        peak_2_kev: Known energy of second peak (keV, default: 1275)
        
    Returns:
        Tuple of (gain, offset) where:
            gain: keV per mV·ns
            offset: keV
            
    Raises:
        CalibrationError: If peaks are too close or invalid
    """
    # Validate inputs
    if peak_2_raw <= peak_1_raw:
        raise CalibrationError(
            f"Peak 2 raw value ({peak_2_raw:.2f}) must be greater than "
            f"peak 1 raw value ({peak_1_raw:.2f})"
        )
    
    # Check minimum separation (at least 10% difference)
    separation = (peak_2_raw - peak_1_raw) / peak_1_raw
    if separation < 0.1:
        raise CalibrationError(
            f"Peaks are too close together (separation: {separation*100:.1f}%). "
            f"Need at least 10% separation for reliable calibration."
        )
    
    # Calculate gain (slope)
    gain = (peak_2_kev - peak_1_kev) / (peak_2_raw - peak_1_raw)
    
    # Calculate offset (intercept)
    offset = peak_1_kev - gain * peak_1_raw
    
    # Validate gain is reasonable (should be positive and not too extreme)
    if gain <= 0:
        raise CalibrationError(
            f"Invalid gain value: {gain:.6f}. Gain must be positive."
        )
    
    if gain < 0.001 or gain > 1000:
        raise CalibrationError(
            f"Gain value {gain:.6f} keV/(mV·ns) is outside reasonable range "
            f"(0.001 to 1000). Check peak values."
        )
    
    return gain, offset


def find_peak_center_weighted_mean(
    energies: np.ndarray,
    region_min: float,
    region_max: float,
    num_bins: int = 100
) -> float:
    """
    Find peak center using weighted mean (centroid) method.
    
    This method calculates the "center of mass" of the histogram
    within the selected region, providing a robust estimate of
    the peak center.
    
    Args:
        energies: Array of raw energy values (mV·ns)
        region_min: Minimum energy of region
        region_max: Maximum energy of region
        num_bins: Number of histogram bins to use
        
    Returns:
        Peak center location in raw energy units (mV·ns)
        
    Raises:
        CalibrationError: If region is empty or invalid
    """
    # Validate region
    if region_max <= region_min:
        raise CalibrationError(
            f"Invalid region: max ({region_max:.2f}) must be greater than "
            f"min ({region_min:.2f})"
        )
    
    # Filter energies to region
    in_region = (energies >= region_min) & (energies <= region_max)
    region_energies = energies[in_region]
    
    if len(region_energies) == 0:
        raise CalibrationError(
            f"No events found in region [{region_min:.2f}, {region_max:.2f}]"
        )
    
    if len(region_energies) < 10:
        raise CalibrationError(
            f"Too few events in region ({len(region_energies)}). "
            f"Need at least 10 events for reliable peak finding."
        )
    
    # Create histogram
    hist, bin_edges = np.histogram(
        region_energies,
        bins=num_bins,
        range=(region_min, region_max)
    )
    
    # Calculate bin centers
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Calculate weighted mean (centroid)
    total_counts = np.sum(hist)
    if total_counts == 0:
        raise CalibrationError("Histogram is empty in selected region")
    
    peak_center = np.sum(bin_centers * hist) / total_counts
    
    return float(peak_center)


def validate_calibration_data(
    events_count: int,
    peak_1_raw: float,
    peak_2_raw: float,
    min_events: int = 100
) -> Tuple[bool, Optional[str]]:
    """
    Validate that calibration data is sufficient and reasonable.
    
    Args:
        events_count: Number of calibration events collected
        peak_1_raw: Raw value of first peak
        peak_2_raw: Raw value of second peak
        min_events: Minimum number of events required
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid
        - error_message: None if valid, error string if invalid
    """
    # Check event count
    if events_count < min_events:
        return False, f"Need at least {min_events} events for calibration (have {events_count})"
    
    # Check peaks are different
    if abs(peak_2_raw - peak_1_raw) < 0.01:
        return False, "Peaks are too similar - check region selection"
    
    # Check peak order
    if peak_2_raw <= peak_1_raw:
        return False, "Peak 2 must have higher energy than Peak 1"
    
    # Check peaks are positive
    if peak_1_raw <= 0 or peak_2_raw <= 0:
        return False, "Peak values must be positive"
    
    # Check separation ratio
    ratio = peak_2_raw / peak_1_raw
    expected_ratio = PEAK_2_KEV / PEAK_1_KEV  # ~2.5
    
    # Allow ratio between 1.5 and 4.0 (reasonable range)
    if ratio < 1.5 or ratio > 4.0:
        return False, (
            f"Peak ratio ({ratio:.2f}) is outside expected range (1.5-4.0). "
            f"Expected ratio is ~{expected_ratio:.2f} for Na-22. "
            f"Check that you selected the correct peaks."
        )
    
    return True, None


def apply_calibration(
    raw_energy: float,
    gain: float,
    offset: float
) -> float:
    """
    Apply calibration to convert raw energy to keV.
    
    Args:
        raw_energy: Raw energy in mV·ns
        gain: Calibration gain (keV per mV·ns)
        offset: Calibration offset (keV)
        
    Returns:
        Calibrated energy in keV
    """
    return gain * raw_energy + offset


def get_calibration_summary(
    gain: float,
    offset: float,
    peak_1_raw: float,
    peak_2_raw: float
) -> str:
    """
    Generate a human-readable calibration summary.
    
    Args:
        gain: Calibration gain
        offset: Calibration offset
        peak_1_raw: Raw value of 511 keV peak
        peak_2_raw: Raw value of 1275 keV peak
        
    Returns:
        Formatted summary string
    """
    peak_1_calib = apply_calibration(peak_1_raw, gain, offset)
    peak_2_calib = apply_calibration(peak_2_raw, gain, offset)
    
    summary = [
        "Calibration Summary:",
        f"  Gain:   {gain:.6f} keV/(mV·ns)",
        f"  Offset: {offset:.3f} keV",
        "",
        "Peak Verification:",
        f"  511 keV peak:  raw={peak_1_raw:.2f} → calibrated={peak_1_calib:.1f} keV",
        f"  1275 keV peak: raw={peak_2_raw:.2f} → calibrated={peak_2_calib:.1f} keV",
    ]
    
    return "\n".join(summary)
