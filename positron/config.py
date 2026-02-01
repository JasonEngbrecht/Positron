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
    
    # Achieved acquisition settings (read-only, set by configurator)
    # These are stored for reference but not used to configure the scope
    # Hardware settings are hardcoded: 100mV range, 4 channels enabled, DC coupling
    waveform_length: int = 375  # Total number of samples (calculated from sample rate and 3 µs)
    pre_trigger_samples: int = 125  # Pre-trigger sample count (calculated from sample rate and 1 µs)
    sample_rate: Optional[float] = None  # Achieved sample rate in Hz (e.g., 125000000.0 for 125 MS/s)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "scope_series": self.scope_series,
            "last_variant": self.last_variant,
            "last_serial": self.last_serial,
            "waveform_length": self.waveform_length,
            "pre_trigger_samples": self.pre_trigger_samples,
            "sample_rate": self.sample_rate,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScopeConfig":
        """Create configuration from dictionary."""
        # Filter out old/unknown fields for backward compatibility
        valid_fields = {
            "scope_series", "last_variant", "last_serial",
            "waveform_length", "pre_trigger_samples", "sample_rate"
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


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
            "waveform_length": 375,
            "pre_trigger_samples": 125,
            "sample_rate": None,
        }
