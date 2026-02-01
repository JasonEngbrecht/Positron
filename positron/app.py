"""
Application state manager for Positron.

The PositronApp class manages application-wide state including:
- Configuration management (load/save settings)
- Scope connection state and device information
- Qt signals for application-wide events
- Shared access point for UI panels and modules

This is NOT the entry point - see main.py for application startup.
"""

import sys
from pathlib import Path
from typing import Optional, Any

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

from positron.config import AppConfig
from positron.scope.connection import ScopeInfo


class PositronApp(QObject):
    """
    Main application class managing the application lifecycle and configuration.
    """
    
    # Signals for application-wide events
    config_changed = Signal()
    scope_connected_signal = Signal()
    scope_disconnected_signal = Signal()
    
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
        self._scope_info: Optional[ScopeInfo] = None
    
    @property
    def scope_connected(self) -> bool:
        """Check if scope is currently connected."""
        return self._scope_connected
    
    @property
    def scope_info(self) -> Optional[ScopeInfo]:
        """Get information about the connected scope."""
        return self._scope_info
    
    def connect_scope(self, scope_info: ScopeInfo) -> None:
        """
        Register a successful scope connection.
        
        Args:
            scope_info: Information about the connected scope
        """
        self._scope_info = scope_info
        self._scope_handle = scope_info.handle
        self._scope_connected = True
        
        # Update configuration with detected scope
        self.config.scope.scope_series = scope_info.series
        self.save_config()
        
        # Emit connection signal
        self.scope_connected_signal.emit()
    
    def disconnect_scope(self) -> None:
        """Disconnect the scope and update application state."""
        if self._scope_connected:
            # Import here to avoid circular dependency
            from positron.scope.connection import disconnect
            
            disconnect()
            self._scope_connected = False
            self._scope_handle = None
            self._scope_info = None
            self.scope_disconnected_signal.emit()
    
    def save_config(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file."""
        self.config.save(path)
        self.config_changed.emit()
    
    def get_config(self) -> AppConfig:
        """Get the current application configuration."""
        return self.config
    
    def set_scope_connected(self, connected: bool, handle: Optional[Any] = None) -> None:
        """
        Update scope connection state (legacy method, prefer connect_scope).
        
        Args:
            connected: Whether scope is connected
            handle: Optional scope handle object
        """
        self._scope_connected = connected
        self._scope_handle = handle
        if connected:
            self.scope_connected_signal.emit()
        else:
            self.scope_disconnected_signal.emit()


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
