"""
Main entry point for the Positron application.

This is the application entry point that initializes the GUI application
and starts the main event loop.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from positron.app import PositronApp, create_application


def main():
    """Main application entry point."""
    try:
        # Create Qt application
        app = create_application()
        
        # Create Positron application instance
        positron_app = PositronApp()
        
        # TODO: Phase 1.2 - Initialize and show main window
        # For now, just show a message that the application started
        # This will be replaced with actual UI in Phase 2
        
        print("Positron application initialized successfully.")
        print(f"Configuration loaded from: {positron_app.config.config_file}")
        print(f"Scope series: {positron_app.config.scope.scope_series}")
        
        # Show a simple message box for now
        msg = QMessageBox()
        msg.setWindowTitle("Positron")
        msg.setText("Positron application started successfully.\n\nPhase 1.1 complete: Project structure and configuration management.")
        msg.setInformativeText("Scope connection and UI will be implemented in subsequent phases.")
        msg.exec()
        
        # Run application event loop
        # sys.exit(app.exec())
        # For Phase 1.1, we'll just exit after showing the message
        # The actual event loop will be started in Phase 2 when the main window is created
        
        return 0
        
    except Exception as e:
        print(f"Error starting application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
