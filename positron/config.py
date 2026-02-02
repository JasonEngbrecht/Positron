"""
Configuration management for scope settings and application defaults.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from pathlib import Path


@dataclass
class ChannelCalibration:
    """
    Energy calibration parameters for a single channel.
    
    Two-point linear calibration:
    calibrated_energy_keV = gain * raw_energy_mV_ns + offset
    """
    gain: float = 1.0  # keV per mV·ns
    offset: float = 0.0  # keV
    calibrated: bool = False  # Whether this channel has been calibrated
    calibration_date: Optional[str] = None  # ISO format timestamp
    peak_1_raw: Optional[float] = None  # 511 keV peak raw value (mV·ns)
    peak_2_raw: Optional[float] = None  # 1275 keV peak raw value (mV·ns)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "gain": self.gain,
            "offset": self.offset,
            "calibrated": self.calibrated,
            "calibration_date": self.calibration_date,
            "peak_1_raw": self.peak_1_raw,
            "peak_2_raw": self.peak_2_raw,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelCalibration":
        """Create from dictionary."""
        return cls(
            gain=data.get("gain", 1.0),
            offset=data.get("offset", 0.0),
            calibrated=data.get("calibrated", False),
            calibration_date=data.get("calibration_date"),
            peak_1_raw=data.get("peak_1_raw"),
            peak_2_raw=data.get("peak_2_raw"),
        )
    
    def apply_calibration(self, raw_energy: float) -> float:
        """
        Apply calibration to convert raw energy to keV.
        
        Args:
            raw_energy: Raw energy in mV·ns
            
        Returns:
            Calibrated energy in keV
        """
        return self.gain * raw_energy + self.offset


@dataclass
class TriggerCondition:
    """
    A single trigger condition with AND logic between selected channels.
    
    Example: enabled=True, channels=['A', 'B'] means "Channel A AND Channel B"
    """
    enabled: bool = False
    channels: List[str] = field(default_factory=list)  # List of channel names: 'A', 'B', 'C', 'D'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "channels": self.channels.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerCondition":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", False),
            channels=data.get("channels", [])
        )
    
    def has_channels(self) -> bool:
        """Check if this condition has any channels selected."""
        return len(self.channels) > 0
    
    def is_valid(self) -> bool:
        """Check if this condition is valid (enabled and has channels)."""
        return self.enabled and self.has_channels()


@dataclass
class TriggerConfig:
    """
    Trigger configuration with up to 4 conditions using OR logic.
    
    Multiple enabled conditions use OR logic: Condition1 OR Condition2 OR ...
    Within each condition, channels use AND logic.
    
    Hardware settings (hardcoded):
    - Threshold: -5 mV
    - Direction: Falling edge
    """
    # Four trigger conditions
    condition_1: TriggerCondition = field(default_factory=TriggerCondition)
    condition_2: TriggerCondition = field(default_factory=TriggerCondition)
    condition_3: TriggerCondition = field(default_factory=TriggerCondition)
    condition_4: TriggerCondition = field(default_factory=TriggerCondition)
    
    # Auto-trigger timeout setting
    auto_trigger_enabled: bool = False  # If False, scope never auto-triggers
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "condition_1": self.condition_1.to_dict(),
            "condition_2": self.condition_2.to_dict(),
            "condition_3": self.condition_3.to_dict(),
            "condition_4": self.condition_4.to_dict(),
            "auto_trigger_enabled": self.auto_trigger_enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerConfig":
        """Create from dictionary."""
        return cls(
            condition_1=TriggerCondition.from_dict(data.get("condition_1", {})),
            condition_2=TriggerCondition.from_dict(data.get("condition_2", {})),
            condition_3=TriggerCondition.from_dict(data.get("condition_3", {})),
            condition_4=TriggerCondition.from_dict(data.get("condition_4", {})),
            auto_trigger_enabled=data.get("auto_trigger_enabled", False),
        )
    
    def get_all_conditions(self) -> List[TriggerCondition]:
        """Get all conditions as a list."""
        return [self.condition_1, self.condition_2, self.condition_3, self.condition_4]
    
    def get_valid_conditions(self) -> List[TriggerCondition]:
        """Get only valid (enabled with channels) conditions."""
        return [cond for cond in self.get_all_conditions() if cond.is_valid()]
    
    def has_any_valid_condition(self) -> bool:
        """Check if at least one valid condition exists."""
        return len(self.get_valid_conditions()) > 0
    
    @classmethod
    def create_default(cls) -> "TriggerConfig":
        """
        Create default trigger configuration for PALS experiments.
        
        Default: Condition 1 with Channel A only (single start detector)
        """
        config = cls()
        config.condition_1.enabled = True
        config.condition_1.channels = ['A']
        return config


@dataclass
class ScopeConfig:
    """Configuration for oscilloscope settings."""
    
    # Scope identification
    scope_series: Optional[str] = None  # "3000a" or "6000a"
    last_variant: Optional[str] = None  # Last connected variant (e.g., "3406D MSO")
    last_serial: Optional[str] = None  # Last connected serial number
    
    # Achieved acquisition settings (read-only, set by configurator)
    # These are stored for reference but not used to configure the scope
    # Hardware settings are hardcoded: 100mV range, 4 channels enabled, DC coupling
    waveform_length: int = 375  # Total number of samples (calculated from sample rate and 3 µs)
    pre_trigger_samples: int = 125  # Pre-trigger sample count (calculated from sample rate and 1 µs)
    sample_rate: Optional[float] = None  # Achieved sample rate in Hz (e.g., 125000000.0 for 125 MS/s)
    voltage_range_code: int = 3  # Voltage range code used (3 = PS3000A_100MV for PS3000a series)
    
    # Trigger configuration
    trigger: TriggerConfig = field(default_factory=TriggerConfig.create_default)
    
    # Energy calibration (Phase 4)
    calibration_a: ChannelCalibration = field(default_factory=ChannelCalibration)
    calibration_b: ChannelCalibration = field(default_factory=ChannelCalibration)
    calibration_c: ChannelCalibration = field(default_factory=ChannelCalibration)
    calibration_d: ChannelCalibration = field(default_factory=ChannelCalibration)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "scope_series": self.scope_series,
            "last_variant": self.last_variant,
            "last_serial": self.last_serial,
            "waveform_length": self.waveform_length,
            "pre_trigger_samples": self.pre_trigger_samples,
            "sample_rate": self.sample_rate,
            "voltage_range_code": self.voltage_range_code,
            "trigger": self.trigger.to_dict(),
            "calibration_a": self.calibration_a.to_dict(),
            "calibration_b": self.calibration_b.to_dict(),
            "calibration_c": self.calibration_c.to_dict(),
            "calibration_d": self.calibration_d.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScopeConfig":
        """Create configuration from dictionary."""
        # Filter out old/unknown fields for backward compatibility
        valid_fields = {
            "scope_series", "last_variant", "last_serial",
            "waveform_length", "pre_trigger_samples", "sample_rate", "voltage_range_code"
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # Handle trigger config separately
        scope_config = cls(**filtered_data)
        if "trigger" in data:
            scope_config.trigger = TriggerConfig.from_dict(data["trigger"])
        
        # Handle calibration configs
        if "calibration_a" in data:
            scope_config.calibration_a = ChannelCalibration.from_dict(data["calibration_a"])
        if "calibration_b" in data:
            scope_config.calibration_b = ChannelCalibration.from_dict(data["calibration_b"])
        if "calibration_c" in data:
            scope_config.calibration_c = ChannelCalibration.from_dict(data["calibration_c"])
        if "calibration_d" in data:
            scope_config.calibration_d = ChannelCalibration.from_dict(data["calibration_d"])
        
        return scope_config
    
    def get_calibration(self, channel: str) -> ChannelCalibration:
        """
        Get calibration for a specific channel.
        
        Args:
            channel: Channel name ('A', 'B', 'C', or 'D')
            
        Returns:
            ChannelCalibration for the specified channel
            
        Raises:
            ValueError: If channel name is invalid
        """
        channel = channel.upper()
        if channel == 'A':
            return self.calibration_a
        elif channel == 'B':
            return self.calibration_b
        elif channel == 'C':
            return self.calibration_c
        elif channel == 'D':
            return self.calibration_d
        else:
            raise ValueError(f"Invalid channel: {channel}. Must be A, B, C, or D.")


@dataclass
class AppConfig:
    """Application-wide configuration."""
    
    # Default scope configuration
    scope: ScopeConfig = field(default_factory=ScopeConfig)
    
    # Display settings
    waveform_display_rate: float = 3.0  # Hz, max update rate for waveform display
    
    # Acquisition settings
    default_batch_size: int = 10  # Number of captures per batch in rapid block mode
    max_event_count: int = 1000000  # Maximum events before auto-stop (safety limit)
    
    # Phase 3: Processing parameters
    cfd_fraction: float = 0.5  # Constant fraction for timing (0-1)
    max_events: int = 1_000_000  # Hard limit on event storage (~700 MB memory)
    # Note: Can be increased if needed, but memory usage is ~750 bytes/event
    # Future optimization to NumPy arrays could enable 10M+ events in <1 GB
    
    # Preset stop conditions
    time_limit_enabled: bool = False  # Enable automatic stop after time limit
    time_limit_seconds: int = 300  # Time limit in seconds (default: 5 minutes)
    event_limit_enabled: bool = False  # Enable automatic stop after event count
    event_limit_count: int = 10000  # Event count limit (default: 10,000 events)
    
    # File paths
    config_file: Path = field(default_factory=lambda: Path.home() / ".positron" / "config.json")
    default_save_directory: Path = field(default_factory=lambda: Path.home() / "Documents" / "Positron")
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to JSON file."""
        if path is None:
            path = self.config_file
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = {
            "scope": self.scope.to_dict(),
            "waveform_display_rate": self.waveform_display_rate,
            "default_batch_size": self.default_batch_size,
            "max_event_count": self.max_event_count,
            "time_limit_enabled": self.time_limit_enabled,
            "time_limit_seconds": self.time_limit_seconds,
            "event_limit_enabled": self.event_limit_enabled,
            "event_limit_count": self.event_limit_count,
            "default_save_directory": str(self.default_save_directory),
            "cfd_fraction": self.cfd_fraction,
            "max_events": self.max_events,
        }
        
        with open(path, "w") as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        """Load configuration from JSON file."""
        if path is None:
            path = cls().config_file
        
        if not path.exists():
            # Return default configuration if file doesn't exist
            return cls()
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            config = cls()
            config.scope = ScopeConfig.from_dict(data.get("scope", {}))
            config.waveform_display_rate = data.get("waveform_display_rate", 3.0)
            config.default_batch_size = data.get("default_batch_size", 10)
            config.max_event_count = data.get("max_event_count", 1000000)
            config.time_limit_enabled = data.get("time_limit_enabled", False)
            config.time_limit_seconds = data.get("time_limit_seconds", 300)
            config.event_limit_enabled = data.get("event_limit_enabled", False)
            config.event_limit_count = data.get("event_limit_count", 10000)
            config.cfd_fraction = data.get("cfd_fraction", 0.5)
            config.max_events = data.get("max_events", 10_000_000)
            
            save_dir = data.get("default_save_directory")
            if save_dir:
                config.default_save_directory = Path(save_dir)
            
            return config
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Return default configuration on error
            print(f"Warning: Failed to load configuration: {e}. Using defaults.")
            return cls()
    
    def get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "scope_series": None,
            "waveform_length": 375,
            "pre_trigger_samples": 125,
            "sample_rate": None,
        }
