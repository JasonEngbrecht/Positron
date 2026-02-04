"""
Main window for Positron application.

Provides the top-level window with tabbed interface for different panels.
"""

from typing import Optional

from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PySide6.QtCore import Qt

from positron.app import PositronApp
from positron.panels.home import HomePanel
from positron.panels.calibration import CalibrationPanel
from positron.panels.analysis.energy_display import EnergyDisplayPanel
from positron.panels.analysis.timing_display import TimingDisplayPanel
from positron.ui.help_dialogs import (
    show_getting_started,
    show_home_help,
    show_energy_display_help,
    show_timing_display_help,
    show_calibration_help
)


class MainWindow(QMainWindow):
    """
    Main application window with tabbed interface.
    
    Contains:
    - Home panel (default tab)
    - Future: Calibration panel, Analysis panels
    """
    
    def __init__(self, app: PositronApp):
        """
        Initialize the main window.
        
        Args:
            app: Positron application instance
        """
        super().__init__()
        
        self.app = app
        
        # Setup window
        self._setup_window()
        
        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create panels
        self._create_panels()
        
        # Setup menu bar
        self._setup_menubar()
    
    def _setup_window(self) -> None:
        """Configure main window properties."""
        # Window title with scope info
        if self.app.scope_info:
            title = f"Positron - {self.app.scope_info.variant} ({self.app.scope_info.serial})"
        else:
            title = "Positron"
        self.setWindowTitle(title)
        
        # Window size (laptop-friendly default)
        self.resize(1000, 700)
        
        # Center on screen
        screen_geometry = self.screen().availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def _create_panels(self) -> None:
        """Create and add all panels to tabs."""
        # Home panel
        self.home_panel = HomePanel(self.app)
        self.tabs.addTab(self.home_panel, "Home")
        
        # Energy Display panel (Phase 5)
        self.energy_panel = EnergyDisplayPanel(self.app)
        self.tabs.addTab(self.energy_panel, "Energy Display")
        
        # Timing Display panel (Phase 5)
        self.timing_panel = TimingDisplayPanel(self.app)
        self.tabs.addTab(self.timing_panel, "Timing Display")
        
        # Calibration panel (Phase 4) - last tab for workflow
        self.calibration_panel = CalibrationPanel(self.app)
        self.tabs.addTab(self.calibration_panel, "Calibration")
    
    def _setup_menubar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Exit action
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # Getting Started
        getting_started_action = help_menu.addAction("&Getting Started")
        getting_started_action.setShortcut("F1")
        getting_started_action.triggered.connect(lambda: show_getting_started(self))
        
        help_menu.addSeparator()
        
        # Panel-specific help
        home_help_action = help_menu.addAction("&Home Panel")
        home_help_action.triggered.connect(lambda: show_home_help(self))
        
        energy_help_action = help_menu.addAction("&Energy Display Panel")
        energy_help_action.triggered.connect(lambda: show_energy_display_help(self))
        
        timing_help_action = help_menu.addAction("&Timing Display Panel")
        timing_help_action.triggered.connect(lambda: show_timing_display_help(self))
        
        calibration_help_action = help_menu.addAction("&Calibration Panel")
        calibration_help_action.triggered.connect(lambda: show_calibration_help(self))
        
        help_menu.addSeparator()
        
        # About action
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self._show_about)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        scope_info = ""
        if self.app.scope_info:
            scope_info = (
                f"\n\nConnected Scope:\n"
                f"Model: {self.app.scope_info.variant}\n"
                f"Series: {self.app.scope_info.series.upper()}\n"
                f"Serial: {self.app.scope_info.serial}"
            )
        
        QMessageBox.about(
            self,
            "About Positron",
            f"<h2>Positron</h2>"
            f"<p>Version 0.1.0</p>"
            f"<p>Data acquisition and analysis system for pulse detection experiments.</p>"
            f"<p>Designed for positron annihilation lifetime spectroscopy (PALS) "
            f"and related techniques.</p>"
            f"{scope_info}"
        )
    
    def closeEvent(self, event) -> None:
        """
        Handle window close event.
        
        Ensures proper cleanup of acquisition and scope connection.
        """
        # Check if acquisition is running
        if self.home_panel._state == "running":
            reply = QMessageBox.question(
                self,
                "Acquisition Running",
                "Data acquisition is currently running. Do you want to stop and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        # Clean up home panel
        self.home_panel.cleanup()
        
        # Disconnect scope
        self.app.disconnect_scope()
        
        # Accept the close event
        event.accept()
