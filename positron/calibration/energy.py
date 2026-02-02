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

from typing import Tuple, Optional
import numpy as np


# Na-22 calibration peak energies (keV)
PEAK_1_KEV = 511.0   # Positron annihilation
PEAK_2_KEV = 1275.0  # Na-22 gamma


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
