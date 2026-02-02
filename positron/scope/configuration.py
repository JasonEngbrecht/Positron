"""
Scope configuration module for applying hardware settings to PicoScope devices.

This module provides a unified interface for configuring PicoScope oscilloscopes
with hardcoded settings optimized for pulse detection experiments.

Hardware Configuration (FIXED):
- Voltage range: 100 mV on all channels
- Channels: All 4 channels enabled
- Coupling: DC
- Timebase: Maximum (fastest) rate
- Capture time: 1 µs pre-trigger, 2 µs post-trigger (3 µs total)
"""

import ctypes
from typing import Protocol, Tuple, Any
from dataclasses import dataclass

from picosdk.functions import assert_pico_ok
from positron.scope.connection import ScopeInfo


# Hardware configuration constants
VOLTAGE_RANGE_MV = 100  # millivolts
PRE_TRIGGER_TIME_US = 1.0  # microseconds
POST_TRIGGER_TIME_US = 2.0  # microseconds
TOTAL_CAPTURE_TIME_US = PRE_TRIGGER_TIME_US + POST_TRIGGER_TIME_US


class ScopeConfigurator(Protocol):
    """
    Protocol defining the interface for scope configurators.
    
    This allows both PS3000a and PS6000a implementations to follow
    the same interface pattern.
    """
    
    def apply_configuration(self) -> None:
        """
        Apply all hardware configuration settings to the scope.
        
        This configures:
        - All 4 channels with 100mV range, DC coupling
        - Maximum sample rate (fastest timebase)
        - Sample counts based on 3 µs capture time
        
        Raises:
            Exception: If configuration fails
        """
        ...
    
    def get_actual_sample_rate(self) -> float:
        """
        Get the actual achieved sample rate in samples per second.
        
        Returns:
            Sample rate in Hz
        """
        ...
    
    def get_sample_counts(self) -> Tuple[int, int]:
        """
        Get the calculated sample counts.
        
        Returns:
            Tuple of (total_samples, pre_trigger_samples)
        """
        ...


@dataclass
class TimebaseInfo:
    """Information about the configured timebase."""
    timebase_index: int
    sample_interval_ns: float
    sample_rate_hz: float
    total_samples: int
    pre_trigger_samples: int
    post_trigger_samples: int
    voltage_range_code: int  # PS3000A_RANGE code used for channels


class PS3000aConfigurator:
    """
    Configurator for PS3000a series oscilloscopes.
    
    Applies hardcoded configuration optimized for pulse detection.
    """
    
    # PS3000a specific constants
    PS3000A_CHANNELS = [0, 1, 2, 3]  # Channel A, B, C, D indices
    
    def __init__(self, scope_info: ScopeInfo):
        """
        Initialize PS3000a configurator.
        
        Args:
            scope_info: Information about the connected scope
        """
        if scope_info.series != "3000a":
            raise ValueError(f"PS3000aConfigurator requires 3000a series, got {scope_info.series}")
        
        self.scope_info = scope_info
        self.handle = scope_info.handle
        self.ps = scope_info.api_module
        
        # Configuration state
        self._timebase_info: TimebaseInfo | None = None
        self._voltage_range_code: int | None = None
    
    def apply_configuration(self) -> None:
        """Apply all hardware configuration settings."""
        # Configure all 4 channels
        self._configure_channels()
        
        # Configure timebase and calculate sample counts
        self._configure_timebase()
    
    def _configure_channels(self) -> None:
        """Configure all 4 analog channels with hardcoded settings."""
        # Get the range enum value for 100mV
        self._voltage_range_code = self.ps.PS3000A_RANGE['PS3000A_100MV']
        coupling = self.ps.PS3000A_COUPLING['PS3000A_DC']
        analog_offset = 0.0
        
        status = {}
        
        for channel_idx in self.PS3000A_CHANNELS:
            status[f"setCh{channel_idx}"] = self.ps.ps3000aSetChannel(
                self.handle,
                channel_idx,  # channel
                1,  # enabled
                coupling,  # DC coupling
                self._voltage_range_code,  # 100mV range
                analog_offset  # 0V offset
            )
            
            try:
                assert_pico_ok(status[f"setCh{channel_idx}"])
            except Exception as e:
                raise RuntimeError(
                    f"Failed to configure channel {channel_idx}: {e}\n"
                    f"Status code: {status[f'setCh{channel_idx}']}"
                )
    
    def _configure_timebase(self) -> None:
        """
        Configure timebase to maximum rate and calculate sample counts.
        
        Calculates the required number of samples to achieve:
        - 1 µs pre-trigger capture
        - 2 µs post-trigger capture
        - 3 µs total capture time
        """
        # Start with timebase 0 (fastest rate)
        timebase = 0
        max_attempts = 100
        
        # We need to iterate to find a timebase that:
        # 1. Achieves a fast sample rate
        # 2. Can support enough samples for our time window
        
        for attempt in range(max_attempts):
            # Calculate required samples for 3 µs at this timebase
            # First, we need to query what the timebase gives us
            time_interval_ns = ctypes.c_float()
            max_samples = ctypes.c_int32()
            
            # Query with a trial sample count (we'll refine this)
            trial_samples = 500  # Start with a reasonable estimate
            
            status = self.ps.ps3000aGetTimebase2(
                self.handle,
                timebase,
                trial_samples,
                ctypes.byref(time_interval_ns),
                1,  # oversample (not used in this mode)
                ctypes.byref(max_samples),
                0  # segment index
            )
            
            # Check if this timebase is valid
            if status == 0:  # PICO_OK
                # Calculate sample rate from interval
                sample_interval_s = time_interval_ns.value * 1e-9
                sample_rate_hz = 1.0 / sample_interval_s
                
                # Calculate required samples for our time window
                total_time_s = TOTAL_CAPTURE_TIME_US * 1e-6
                pre_trigger_time_s = PRE_TRIGGER_TIME_US * 1e-6
                
                total_samples_needed = int(total_time_s * sample_rate_hz)
                pre_trigger_samples = int(pre_trigger_time_s * sample_rate_hz)
                post_trigger_samples = total_samples_needed - pre_trigger_samples
                
                # Verify we can collect this many samples
                if total_samples_needed <= max_samples.value:
                    # Success! Store the configuration
                    self._timebase_info = TimebaseInfo(
                        timebase_index=timebase,
                        sample_interval_ns=time_interval_ns.value,
                        sample_rate_hz=sample_rate_hz,
                        total_samples=total_samples_needed,
                        pre_trigger_samples=pre_trigger_samples,
                        post_trigger_samples=post_trigger_samples,
                        voltage_range_code=self._voltage_range_code
                    )
                    return
                else:
                    # Need slower timebase to support more samples
                    timebase += 1
            else:
                # This timebase didn't work, try the next one
                timebase += 1
        
        # If we get here, we couldn't find a valid timebase
        raise RuntimeError(
            f"Failed to configure timebase after {max_attempts} attempts. "
            f"Cannot achieve {TOTAL_CAPTURE_TIME_US} µs capture time."
        )
    
    def get_actual_sample_rate(self) -> float:
        """Get the actual achieved sample rate in Hz."""
        if self._timebase_info is None:
            raise RuntimeError("Timebase not configured. Call apply_configuration() first.")
        return self._timebase_info.sample_rate_hz
    
    def get_sample_counts(self) -> Tuple[int, int]:
        """Get the calculated sample counts as (total_samples, pre_trigger_samples)."""
        if self._timebase_info is None:
            raise RuntimeError("Timebase not configured. Call apply_configuration() first.")
        return (self._timebase_info.total_samples, self._timebase_info.pre_trigger_samples)
    
    def get_timebase_info(self) -> TimebaseInfo:
        """
        Get detailed timebase information.
        
        Returns:
            TimebaseInfo with all calculated values
            
        Raises:
            RuntimeError: If timebase not yet configured
        """
        if self._timebase_info is None:
            raise RuntimeError("Timebase not configured. Call apply_configuration() first.")
        return self._timebase_info
    
    def get_voltage_range_code(self) -> int:
        """
        Get the voltage range code used for channel configuration.
        
        Returns:
            Voltage range code (e.g., 3 for PS3000A_100MV)
            
        Raises:
            RuntimeError: If channels not yet configured
        """
        if self._voltage_range_code is None:
            raise RuntimeError("Channels not configured. Call apply_configuration() first.")
        return self._voltage_range_code


class PS6000aConfigurator:
    """
    Stub configurator for PS6000a series oscilloscopes.
    
    To be implemented in future phases.
    """
    
    def __init__(self, scope_info: ScopeInfo):
        """Initialize PS6000a configurator."""
        if scope_info.series != "6000a":
            raise ValueError(f"PS6000aConfigurator requires 6000a series, got {scope_info.series}")
        
        self.scope_info = scope_info
    
    def apply_configuration(self) -> None:
        """Not yet implemented."""
        raise NotImplementedError(
            "PS6000a configuration is not yet implemented. "
            "This will be added in a future phase. "
            "Currently only PS3000a series is supported."
        )
    
    def get_actual_sample_rate(self) -> float:
        """Not yet implemented."""
        raise NotImplementedError("PS6000a configuration not yet implemented")
    
    def get_sample_counts(self) -> Tuple[int, int]:
        """Not yet implemented."""
        raise NotImplementedError("PS6000a configuration not yet implemented")


def create_configurator(scope_info: ScopeInfo) -> ScopeConfigurator:
    """
    Factory function to create the appropriate configurator for a scope.
    
    Args:
        scope_info: Information about the connected scope
        
    Returns:
        Appropriate configurator instance for the scope series
        
    Raises:
        ValueError: If scope series is not supported
    """
    if scope_info.series == "3000a":
        return PS3000aConfigurator(scope_info)
    elif scope_info.series == "6000a":
        return PS6000aConfigurator(scope_info)
    else:
        raise ValueError(
            f"Unsupported scope series: {scope_info.series}. "
            f"Supported series: 3000a, 6000a"
        )
