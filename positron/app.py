"""
Main application class for Positron.
"""

import sys
from pathlib import Path
from typing import Optional, Any

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

from positron.config import AppConfig


class PositronApp(QObject):
    """
    Main application class managing the application lifecycle and configuration.
    """
    
    # Signals for application-wide events
    config_changed = Signal()
    scope_connected = Signal()
    scope_disconnected = Signal()
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the Positron application.
        
        Args:
            config_path: Optional path to configuration file. If None, uses default.
        """
        super().__init__()
        
        # Load configuration
        self.config = AppConfig.load(config_path)
        
        # Application state
        self._scope_connected = False
        self._scope_handle = None
    
    @property
    def scope_connected(self) -> bool:
        """Check if scope is currently connected."""
        return self._scope_connected
    
    def save_config(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file."""
        self.config.save(path)
        self.config_changed.emit()
    
    def get_config(self) -> AppConfig:
        """Get the current application configuration."""
        return self.config
    
    def set_scope_connected(self, connected: bool, handle: Optional[Any] = None) -> None:
        """
        Update scope connection state.
        
        Args:
            connected: Whether scope is connected
            handle: Optional scope handle object
        """
        self._scope_connected = connected
        self._scope_handle = handle
        if connected:
            self.scope_connected.emit()
        else:
            self.scope_disconnected.emit()


def create_application() -> QApplication:
    """
    Create and configure the QApplication instance.
    
    Returns:
        Configured QApplication instance
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("Positron")
        app.setOrganizationName("Positron")
        app.setApplicationVersion("0.1.0")
    
    return app
