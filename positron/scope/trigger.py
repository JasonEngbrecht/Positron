"""
Trigger configuration module for PicoScope oscilloscopes.

This module handles advanced trigger setup with configurable AND/OR logic
for pulse detection experiments.

Hardware Configuration (FIXED):
- Threshold: -5 mV
- Direction: Falling edge (negative pulses)
- Hysteresis: 10 ADC counts (minimal)

User Configuration:
- Up to 4 trigger conditions (OR logic between conditions)
- Each condition supports multiple channels (AND logic within condition)
- Auto-trigger timeout (enabled/disabled)
"""

import ctypes
from typing import Protocol, List, Tuple
from dataclasses import dataclass

from picosdk.functions import assert_pico_ok, mV2adc
from positron.scope.connection import ScopeInfo
from positron.config import TriggerConfig, TriggerCondition


# Hardware constants
TRIGGER_THRESHOLD_MV = -5.0  # millivolts (negative for falling pulses)
TRIGGER_HYSTERESIS = 10  # ADC counts
AUTO_TRIGGER_MAX_MS = 60000  # 60 seconds maximum auto-trigger timeout


@dataclass
class AppliedTriggerInfo:
    """Information about the applied trigger configuration."""
    num_conditions: int
    conditions_summary: List[str]
    auto_trigger_ms: int
    threshold_mv: float
    direction: str


class TriggerConfigurator(Protocol):
    """
    Protocol defining the interface for trigger configurators.
    
    This allows both PS3000a and PS6000a implementations to follow
    the same interface pattern.
    """
    
    def apply_trigger(self, trigger_config: TriggerConfig) -> AppliedTriggerInfo:
        """
        Apply trigger configuration to the scope.
        
        Args:
            trigger_config: User-configured trigger settings
            
        Returns:
            Information about the applied trigger
            
        Raises:
            Exception: If trigger configuration fails
        """
        ...


class PS3000aTriggerConfigurator:
    """
    Trigger configurator for PS3000a series oscilloscopes.
    
    Implements advanced trigger configuration with AND/OR logic.
    """
    
    # Channel name to index mapping
    CHANNEL_MAP = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    
    def __init__(self, scope_info: ScopeInfo):
        """
        Initialize PS3000a trigger configurator.
        
        Args:
            scope_info: Information about the connected scope
        """
        if scope_info.series != "3000a":
            raise ValueError(f"PS3000aTriggerConfigurator requires 3000a series, got {scope_info.series}")
        
        self.scope_info = scope_info
        self.handle = scope_info.handle
        self.ps = scope_info.api_module
        self.max_adc = scope_info.max_adc
    
    def apply_trigger(self, trigger_config: TriggerConfig) -> AppliedTriggerInfo:
        """
        Apply trigger configuration to PS3000a scope.
        
        Sets up:
        1. Trigger properties (threshold, hysteresis) for each participating channel
        2. Trigger conditions (AND/OR logic) using multiple condition structs
        3. Trigger directions (falling edge for all channels)
        """
        # Validate that at least one condition is valid
        valid_conditions = trigger_config.get_valid_conditions()
        if not valid_conditions:
            raise ValueError("At least one trigger condition must be enabled with channels selected")
        
        # Get all unique channels that participate in any trigger condition
        participating_channels = self._get_participating_channels(valid_conditions)
        
        # Step 1: Set trigger properties for all participating channels
        self._set_trigger_properties(participating_channels, trigger_config.auto_trigger_enabled)
        
        # Step 2: Set trigger conditions (AND/OR logic)
        self._set_trigger_conditions(valid_conditions)
        
        # Step 3: Set trigger directions (falling edge)
        self._set_trigger_directions(participating_channels)
        
        # Create summary
        conditions_summary = []
        for i, condition in enumerate(valid_conditions):
            channels_str = " AND ".join(f"Ch{ch}" for ch in condition.channels)
            conditions_summary.append(f"Condition {i+1}: {channels_str}")
        
        auto_trigger_ms = AUTO_TRIGGER_MAX_MS if trigger_config.auto_trigger_enabled else 0
        
        return AppliedTriggerInfo(
            num_conditions=len(valid_conditions),
            conditions_summary=conditions_summary,
            auto_trigger_ms=auto_trigger_ms,
            threshold_mv=TRIGGER_THRESHOLD_MV,
            direction="Falling"
        )
    
    def _get_participating_channels(self, conditions: List[TriggerCondition]) -> List[str]:
        """Get list of unique channels that participate in any condition."""
        channels_set = set()
        for condition in conditions:
            channels_set.update(condition.channels)
        return sorted(list(channels_set))
    
    def _set_trigger_properties(self, channels: List[str], auto_trigger_enabled: bool) -> None:
        """
        Set trigger properties (threshold, hysteresis) for participating channels.
        
        Args:
            channels: List of channel names ('A', 'B', 'C', 'D')
            auto_trigger_enabled: Whether auto-trigger is enabled
        """
        # Convert threshold from mV to ADC counts
        # We use the 100mV range that was configured in Phase 1.3
        voltage_range = self.ps.PS3000A_RANGE['PS3000A_100MV']
        # mV2adc expects a ctypes object for max_adc
        max_adc_ctypes = ctypes.c_int16(self.max_adc)
        threshold_adc = mV2adc(TRIGGER_THRESHOLD_MV, voltage_range, max_adc_ctypes)
        
        # Auto-trigger timeout
        auto_trigger_ms = AUTO_TRIGGER_MAX_MS if auto_trigger_enabled else 0
        
        # Create trigger channel properties array
        # We need one property struct per participating channel
        properties_array = (self.ps.PS3000A_TRIGGER_CHANNEL_PROPERTIES * len(channels))()
        
        for i, channel_name in enumerate(channels):
            channel_idx = self.CHANNEL_MAP[channel_name]
            
            properties_array[i].thresholdUpper = threshold_adc
            properties_array[i].thresholdUpperHysteresis = TRIGGER_HYSTERESIS
            properties_array[i].thresholdLower = threshold_adc
            properties_array[i].thresholdLowerHysteresis = TRIGGER_HYSTERESIS
            properties_array[i].channel = self.ps.PS3000A_CHANNEL[f"PS3000A_CHANNEL_{channel_name}"]
            properties_array[i].thresholdMode = self.ps.PS3000A_THRESHOLD_MODE["PS3000A_LEVEL"]
        
        # Apply trigger properties
        status = self.ps.ps3000aSetTriggerChannelProperties(
            self.handle,
            ctypes.byref(properties_array),
            len(channels),
            0,  # auxOutputEnabled (not used)
            auto_trigger_ms
        )
        
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger properties: {e}\nStatus code: {status}")
    
    def _set_trigger_conditions(self, conditions: List[TriggerCondition]) -> None:
        """
        Set trigger conditions with AND/OR logic.
        
        Multiple condition structs implement OR logic between them.
        Within each struct, channels set to CONDITION_TRUE implement AND logic.
        
        Args:
            conditions: List of valid trigger conditions
        """
        # Create one condition struct per trigger condition (implements OR logic)
        conditions_array = (self.ps.PS3000A_TRIGGER_CONDITIONS_V2 * len(conditions))()
        
        for i, condition in enumerate(conditions):
            # Initialize all channels to DONT_CARE
            conditions_array[i].channelA = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].channelB = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].channelC = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].channelD = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].external = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].aux = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].pulseWidthQualifier = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            conditions_array[i].digital = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
            
            # Set participating channels to CONDITION_TRUE (implements AND logic)
            for channel_name in condition.channels:
                channel_field = f"channel{channel_name}"
                setattr(
                    conditions_array[i],
                    channel_field,
                    self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_TRUE"]
                )
        
        # Apply trigger conditions
        status = self.ps.ps3000aSetTriggerChannelConditionsV2(
            self.handle,
            ctypes.byref(conditions_array),
            len(conditions)
        )
        
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger conditions: {e}\nStatus code: {status}")
    
    def _set_trigger_directions(self, channels: List[str]) -> None:
        """
        Set trigger directions (falling edge) for all participating channels.
        
        Args:
            channels: List of channel names ('A', 'B', 'C', 'D')
        """
        # Initialize all directions to NONE
        direction_a = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]
        direction_b = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]
        direction_c = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]
        direction_d = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]
        
        # Set falling edge for participating channels
        falling = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_FALLING"]
        if 'A' in channels:
            direction_a = falling
        if 'B' in channels:
            direction_b = falling
        if 'C' in channels:
            direction_c = falling
        if 'D' in channels:
            direction_d = falling
        
        # Apply trigger directions
        # Note: External must be set to a valid direction (not NONE) even if not used
        status = self.ps.ps3000aSetTriggerChannelDirections(
            self.handle,
            direction_a,
            direction_b,
            direction_c,
            direction_d,
            self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_RISING"],  # external (required even if not used)
            self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]      # aux
        )
        
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger directions: {e}\nStatus code: {status}")


class PS6000aTriggerConfigurator:
    """
    Stub configurator for PS6000a series oscilloscopes.
    
    To be implemented in future phases.
    """
    
    def __init__(self, scope_info: ScopeInfo):
        """Initialize PS6000a trigger configurator."""
        if scope_info.series != "6000a":
            raise ValueError(f"PS6000aTriggerConfigurator requires 6000a series, got {scope_info.series}")
        
        self.scope_info = scope_info
    
    def apply_trigger(self, trigger_config: TriggerConfig) -> AppliedTriggerInfo:
        """Not yet implemented."""
        raise NotImplementedError(
            "PS6000a trigger configuration is not yet implemented. "
            "This will be added in a future phase. "
            "Currently only PS3000a series is supported."
        )


def create_trigger_configurator(scope_info: ScopeInfo) -> TriggerConfigurator:
    """
    Factory function to create the appropriate trigger configurator for a scope.
    
    Args:
        scope_info: Information about the connected scope
        
    Returns:
        Appropriate trigger configurator instance for the scope series
        
    Raises:
        ValueError: If scope series is not supported
    """
    if scope_info.series == "3000a":
        return PS3000aTriggerConfigurator(scope_info)
    elif scope_info.series == "6000a":
        return PS6000aTriggerConfigurator(scope_info)
    else:
        raise ValueError(
            f"Unsupported scope series: {scope_info.series}. "
            f"Supported series: 3000a, 6000a"
        )
