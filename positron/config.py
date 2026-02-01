"""
Configuration management for scope settings and application defaults.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json
from pathlib import Path


@dataclass
class ScopeConfig:
    """Configuration for oscilloscope settings."""
    
    # Scope identification
    scope_series: Optional[str] = None  # "3000a" or "6000a"
    last_variant: Optional[str] = None  # Last connected variant (e.g., "3406D MSO")
    last_serial: Optional[str] = None  # Last connected serial number
    
    # Channel settings (applied to all 4 channels)
    voltage_range: float = 2.0  # Volts, preset same for all channels
    enabled_channels: list = field(default_factory=lambda: [True, True, True, True])  # 4 channels
    
    # Acquisition settings
    waveform_length: int = 1500  # Number of samples (1000-2000, configurable)
    pre_trigger_samples: int = 500  # Pre-trigger sample capture
    sample_rate: Optional[float] = None  # Will be set to maximum based on scope model
    
    # Trigger settings
    trigger_enabled: bool = True
    trigger_channels: list = field(default_factory=list)  # List of channel indices
    trigger_logic: str = "OR"  # "AND" or "OR"
    trigger_threshold: float = 0.5  # Volts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "scope_series": self.scope_series,
            "last_variant": self.last_variant,
            "last_serial": self.last_serial,
            "voltage_range": self.voltage_range,
            "enabled_channels": self.enabled_channels,
            "waveform_length": self.waveform_length,
            "pre_trigger_samples": self.pre_trigger_samples,
            "sample_rate": self.sample_rate,
            "trigger_enabled": self.trigger_enabled,
            "trigger_channels": self.trigger_channels,
            "trigger_logic": self.trigger_logic,
            "trigger_threshold": self.trigger_threshold,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScopeConfig":
        """Create configuration from dictionary."""
        return cls(**data)


@dataclass
class AppConfig:
    """Application-wide configuration."""
    
    # Default scope configuration
    scope: ScopeConfig = field(default_factory=ScopeConfig)
    
    # Display settings
    waveform_display_rate: float = 3.0  # Hz, max update rate for waveform display
    
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
            "default_save_directory": str(self.default_save_directory),
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
            "voltage_range": 2.0,
            "waveform_length": 1500,
            "pre_trigger_samples": 500,
            "trigger_logic": "OR",
            "trigger_threshold": 0.5,
        }
