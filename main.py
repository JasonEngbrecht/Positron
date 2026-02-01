"""
Entry point for the Positron application.

This script handles application startup:
- Creates the Qt application instance
- Detects and connects to PicoScope hardware
- Shows startup dialogs and error messages
- Initializes the PositronApp state manager
- Launches the main window (Phase 2+)

Run this file to start Positron: python main.py
"""

import sys

from PySide6.QtWidgets import QMessageBox

from positron.app import PositronApp, create_application
from positron.scope.connection import detect_and_connect
from picosdk.errors import DeviceNotFoundError


def main():
    """Main application entry point."""
    try:
        # Create Qt application
        _ = create_application()  # Stored in QApplication.instance(), accessed by Qt internally
        
        # Attempt to detect and connect to a PicoScope
        scope_info = None
        while scope_info is None:
            try:
                # Try to detect and connect
                scope_info = detect_and_connect()
                
            except DeviceNotFoundError as e:
                # Show error dialog with retry option
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("PicoScope Not Found")
                msg.setText("No PicoScope device detected.")
                msg.setInformativeText(str(e))
                msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                msg.setDefaultButton(QMessageBox.Retry)
                
                result = msg.exec()
                
                if result == QMessageBox.Cancel:
                    print("User cancelled scope connection. Exiting.")
                    return 0
                # If Retry, loop will continue
                
            except Exception as e:
                # Unexpected error
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Connection Error")
                msg.setText("An unexpected error occurred while connecting to the PicoScope.")
                msg.setInformativeText(str(e))
                msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                msg.setDefaultButton(QMessageBox.Retry)
                
                result = msg.exec()
                
                if result == QMessageBox.Cancel:
                    print(f"Error connecting to scope: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1
        
        # Successfully connected - show success message
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Positron - Scope Connected")
        msg.setText(f"Successfully connected to PicoScope {scope_info.variant}")
        msg.setInformativeText(
            f"Series: {scope_info.series.upper()}\n"
            f"Serial: {scope_info.serial}\n"
            f"Max ADC: {scope_info.max_adc}\n\n"
            "Phase 1.2 complete: Automatic scope detection and connection."
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        
        # Create Positron application instance
        positron_app = PositronApp()
        
        # Register the scope connection
        positron_app.connect_scope(scope_info)
        
        print("Positron application initialized successfully.")
        print(f"Connected to: PicoScope {scope_info.variant} (Serial: {scope_info.serial})")
        print(f"Configuration loaded from: {positron_app.config.config_file}")
        
        # TODO: Phase 2 - Create and show main window here
        # For now, we exit after showing the connection success message
        
        # Clean up scope connection before exit
        positron_app.disconnect_scope()
        
        return 0
        
    except Exception as e:
        print(f"Error starting application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
