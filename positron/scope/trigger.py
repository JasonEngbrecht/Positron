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

Series-specific SDK calls and trigger structs live in positron.scope.driver;
this module contains only the shared orchestration logic.
"""

from typing import List, Optional
from dataclasses import dataclass

from positron.scope.connection import ScopeInfo
from positron.scope.driver import ScopeDriver, create_driver
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


class TriggerConfigurator:
    """
    Applies user trigger configuration to a connected scope.

    Works for any series supported by the driver layer: all series-specific
    struct population goes through a ScopeDriver.
    """

    def __init__(self, scope_info: ScopeInfo, driver: Optional[ScopeDriver] = None):
        """
        Initialize the trigger configurator.

        Args:
            scope_info: Information about the connected scope
            driver: Scope driver to use (created from scope_info if omitted)
        """
        self.scope_info = scope_info
        self.driver = driver if driver is not None else create_driver(scope_info)

    def apply_trigger(self, trigger_config: TriggerConfig) -> AppliedTriggerInfo:
        """
        Apply trigger configuration to the scope.

        Sets up:
        1. Trigger properties (threshold, hysteresis) for each participating channel
        2. Trigger conditions (AND/OR logic) using multiple condition structs
        3. Trigger directions (falling edge for all participating channels)

        Args:
            trigger_config: User-configured trigger settings

        Returns:
            Information about the applied trigger

        Raises:
            ValueError: If no valid trigger condition is enabled
            RuntimeError: If a hardware call fails
        """
        # Validate that at least one condition is valid
        valid_conditions = trigger_config.get_valid_conditions()
        if not valid_conditions:
            raise ValueError("At least one trigger condition must be enabled with channels selected")

        # Get all unique channels that participate in any trigger condition
        participating_channels = self._get_participating_channels(valid_conditions)

        auto_trigger_ms = AUTO_TRIGGER_MAX_MS if trigger_config.auto_trigger_enabled else 0

        # Step 1: Set trigger properties for all participating channels
        self.driver.set_trigger_properties(
            participating_channels, TRIGGER_THRESHOLD_MV, TRIGGER_HYSTERESIS, auto_trigger_ms
        )

        # Step 2: Set trigger conditions (AND/OR logic)
        self.driver.set_trigger_conditions(
            [condition.channels for condition in valid_conditions]
        )

        # Step 3: Set trigger directions (falling edge)
        self.driver.set_trigger_directions(participating_channels)

        # Create summary
        conditions_summary = []
        for i, condition in enumerate(valid_conditions):
            channels_str = " AND ".join(f"Ch{ch}" for ch in condition.channels)
            conditions_summary.append(f"Condition {i+1}: {channels_str}")

        return AppliedTriggerInfo(
            num_conditions=len(valid_conditions),
            conditions_summary=conditions_summary,
            auto_trigger_ms=auto_trigger_ms,
            threshold_mv=TRIGGER_THRESHOLD_MV,
            direction="Falling"
        )

    def _get_participating_channels(self, conditions: List[TriggerCondition]) -> List[str]:
        """Get sorted list of unique channels that participate in any condition."""
        channels_set = set()
        for condition in conditions:
            channels_set.update(condition.channels)
        return sorted(channels_set)


def create_trigger_configurator(scope_info: ScopeInfo) -> TriggerConfigurator:
    """
    Factory function to create a trigger configurator for a connected scope.

    Args:
        scope_info: Information about the connected scope

    Returns:
        Trigger configurator using the appropriate driver for the scope series

    Raises:
        ValueError: If scope series is not supported (raised by create_driver)
    """
    return TriggerConfigurator(scope_info)
