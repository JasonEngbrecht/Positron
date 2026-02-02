"""
Helper utilities for analysis panels.

Provides shared functionality for data extraction, filtering, and channel information
used by Energy Display and Timing Display panels.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from PySide6.QtGui import QColor

from positron.processing.pulse import EventData
from positron.config import ChannelCalibration
from positron.app import PositronApp


# Channel color definitions (matching WaveformPlot)
CHANNEL_COLORS = {
    'A': QColor(255, 0, 0),      # Red
    'B': QColor(0, 255, 0),      # Green
    'C': QColor(0, 0, 255),      # Blue
    'D': QColor(255, 165, 0),    # Orange
}

CHANNEL_NAMES = {
    'A': 'Channel A',
    'B': 'Channel B',
    'C': 'Channel C',
    'D': 'Channel D',
}


def extract_calibrated_energies(
    events: List[EventData],
    channel: str,
    calibration: ChannelCalibration
) -> np.ndarray:
    """
    Extract calibrated energy values for a specific channel.
    
    Args:
        events: List of EventData to process
        channel: Channel name ('A', 'B', 'C', or 'D')
        calibration: ChannelCalibration for the channel
        
    Returns:
        Numpy array of calibrated energies in keV
    """
    energies = []
    
    for event in events:
        pulse = event.channels.get(channel)
        if pulse and pulse.has_pulse:
            # Apply calibration to convert raw energy (mV·ns) to keV
            energy_kev = calibration.apply_calibration(pulse.energy)
            energies.append(energy_kev)
    
    return np.array(energies)


def filter_events_by_energy(
    events: List[EventData],
    channel: str,
    calibration: ChannelCalibration,
    min_kev: float,
    max_kev: float
) -> List[EventData]:
    """
    Filter events where specified channel's energy falls within range.
    
    Args:
        events: List of EventData to filter
        channel: Channel name ('A', 'B', 'C', or 'D')
        calibration: ChannelCalibration for the channel
        min_kev: Minimum energy in keV (inclusive)
        max_kev: Maximum energy in keV (inclusive)
        
    Returns:
        Filtered list of EventData
    """
    if not calibration.calibrated:
        return []
    
    filtered = []
    
    for event in events:
        pulse = event.channels.get(channel)
        if pulse and pulse.has_pulse:
            # Apply calibration
            energy_kev = calibration.apply_calibration(pulse.energy)
            
            # Check if within range
            if min_kev <= energy_kev <= max_kev:
                filtered.append(event)
    
    return filtered


def calculate_timing_differences(
    events: List[EventData],
    ch1: str,
    ch2: str,
    ch1_calib: ChannelCalibration,
    ch2_calib: ChannelCalibration,
    ch1_energy_range: Tuple[float, float],
    ch2_energy_range: Tuple[float, float]
) -> np.ndarray:
    """
    Extract timing differences between two channels with energy filtering.
    
    Args:
        events: List of EventData to process
        ch1: First channel name ('A', 'B', 'C', or 'D')
        ch2: Second channel name ('A', 'B', 'C', or 'D')
        ch1_calib: ChannelCalibration for first channel
        ch2_calib: ChannelCalibration for second channel
        ch1_energy_range: (min_kev, max_kev) for first channel
        ch2_energy_range: (min_kev, max_kev) for second channel
        
    Returns:
        Numpy array of time differences (ch1.timing_ns - ch2.timing_ns) in nanoseconds
    """
    if not ch1_calib.calibrated or not ch2_calib.calibrated:
        return np.array([])
    
    timing_diffs = []
    
    for event in events:
        pulse1 = event.channels.get(ch1)
        pulse2 = event.channels.get(ch2)
        
        # Check both channels have valid pulses
        if not (pulse1 and pulse1.has_pulse and pulse2 and pulse2.has_pulse):
            continue
        
        # Apply calibration to get energies
        energy1_kev = ch1_calib.apply_calibration(pulse1.energy)
        energy2_kev = ch2_calib.apply_calibration(pulse2.energy)
        
        # Check energy filters
        if not (ch1_energy_range[0] <= energy1_kev <= ch1_energy_range[1]):
            continue
        if not (ch2_energy_range[0] <= energy2_kev <= ch2_energy_range[1]):
            continue
        
        # Calculate timing difference
        time_diff = pulse1.timing_ns - pulse2.timing_ns
        timing_diffs.append(time_diff)
    
    return np.array(timing_diffs)


def get_channel_info(app: PositronApp, channel: str) -> Dict[str, Any]:
    """
    Get channel status information.
    
    Args:
        app: Positron application instance
        channel: Channel name ('A', 'B', 'C', or 'D')
        
    Returns:
        Dictionary with channel information:
        - calibrated (bool): Whether channel is calibrated
        - calibration (ChannelCalibration): Calibration object
        - color (QColor): Display color for this channel
        - name (str): Human-readable name
    """
    calibration = app.get_channel_calibration(channel)
    
    return {
        'calibrated': calibration.calibrated,
        'calibration': calibration,
        'color': CHANNEL_COLORS.get(channel, QColor(128, 128, 128)),
        'name': CHANNEL_NAMES.get(channel, f'Channel {channel}')
    }
