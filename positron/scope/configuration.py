"""
Scope configuration module for applying hardware settings to PicoScope devices.

This module provides a unified interface for configuring PicoScope oscilloscopes
with hardcoded settings optimized for pulse detection experiments.

Hardware Configuration (FIXED):
- Voltage range: 100 mV on all channels
- Channels: All 4 channels enabled
- Coupling: DC (1 MOhm on PS3000a, 50 Ohm on PS6000 - see driver.py)
- Timebase: Maximum (fastest) rate
- Capture time: 1 µs pre-trigger, 2 µs post-trigger (3 µs total)

Series-specific SDK calls live in positron.scope.driver; this module contains
only the shared configuration logic.
"""

from typing import Optional, Tuple
from dataclasses import dataclass

from positron.scope.connection import ScopeInfo
from positron.scope.driver import ScopeDriver, create_driver


# Hardware configuration constants
VOLTAGE_RANGE_MV = 100  # millivolts
PRE_TRIGGER_TIME_US = 1.0  # microseconds
POST_TRIGGER_TIME_US = 2.0  # microseconds
TOTAL_CAPTURE_TIME_US = PRE_TRIGGER_TIME_US + POST_TRIGGER_TIME_US


@dataclass
class TimebaseInfo:
    """Information about the configured timebase."""
    timebase_index: int
    sample_interval_ns: float
    sample_rate_hz: float
    total_samples: int
    pre_trigger_samples: int
    post_trigger_samples: int
    voltage_range_code: int  # Series-specific range code used for channels


class ScopeConfigurator:
    """
    Applies the fixed hardware configuration to a connected scope.

    Works for any series supported by the driver layer: all series-specific
    SDK calls go through a ScopeDriver.
    """

    CHANNELS = [0, 1, 2, 3]  # Channel A, B, C, D indices

    def __init__(self, scope_info: ScopeInfo, driver: Optional[ScopeDriver] = None):
        """
        Initialize the configurator.

        Args:
            scope_info: Information about the connected scope
            driver: Scope driver to use (created from scope_info if omitted)
        """
        self.scope_info = scope_info
        self.driver = driver if driver is not None else create_driver(scope_info)

        # Configuration state
        self._timebase_info: Optional[TimebaseInfo] = None
        self._voltage_range_code: Optional[int] = None

    def apply_configuration(self) -> None:
        """
        Apply all hardware configuration settings to the scope.

        This configures:
        - All 4 channels with 100mV range, DC coupling
        - Maximum sample rate (fastest timebase)
        - Sample counts based on 3 µs capture time

        Raises:
            RuntimeError: If configuration fails
        """
        self._configure_channels()
        self._configure_timebase()

    def _configure_channels(self) -> None:
        """Configure all 4 analog channels with the fixed settings."""
        self._voltage_range_code = self.driver.voltage_range_code_100mv

        for channel_idx in self.CHANNELS:
            try:
                self.driver.set_channel(channel_idx)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to configure channel {channel_idx}: {e}"
                )

    def _configure_timebase(self) -> None:
        """
        Configure timebase to maximum rate and calculate sample counts.

        Searches from timebase 0 (fastest) upward for the first timebase that
        is valid with the current channel configuration and can hold enough
        samples for the 3 µs capture window.
        """
        timebase = 0
        max_attempts = 100

        for attempt in range(max_attempts):
            result = self.driver.get_timebase2(timebase)

            if result is None:
                # This timebase isn't valid with the current channel config
                timebase += 1
                continue

            sample_interval_ns, max_samples = result

            # Calculate sample rate from interval
            sample_rate_hz = 1.0 / (sample_interval_ns * 1e-9)

            # Calculate required samples for our time window
            total_samples_needed = int(TOTAL_CAPTURE_TIME_US * 1e-6 * sample_rate_hz)
            pre_trigger_samples = int(PRE_TRIGGER_TIME_US * 1e-6 * sample_rate_hz)
            post_trigger_samples = total_samples_needed - pre_trigger_samples

            if total_samples_needed <= max_samples:
                # Success! Store the configuration
                self._timebase_info = TimebaseInfo(
                    timebase_index=timebase,
                    sample_interval_ns=sample_interval_ns,
                    sample_rate_hz=sample_rate_hz,
                    total_samples=total_samples_needed,
                    pre_trigger_samples=pre_trigger_samples,
                    post_trigger_samples=post_trigger_samples,
                    voltage_range_code=self._voltage_range_code
                )
                return

            # Need slower timebase to support more samples
            timebase += 1

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
            Series-specific voltage range code for 100 mV (3 on both
            PS3000a and PS6000, from their respective range enums)

        Raises:
            RuntimeError: If channels not yet configured
        """
        if self._voltage_range_code is None:
            raise RuntimeError("Channels not configured. Call apply_configuration() first.")
        return self._voltage_range_code


def create_configurator(scope_info: ScopeInfo) -> ScopeConfigurator:
    """
    Factory function to create a configurator for a connected scope.

    Args:
        scope_info: Information about the connected scope

    Returns:
        Configurator using the appropriate driver for the scope series

    Raises:
        ValueError: If scope series is not supported (raised by create_driver)
    """
    return ScopeConfigurator(scope_info)
