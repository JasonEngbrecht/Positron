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
from positron.scope.configuration import create_configurator
from positron.scope.trigger import create_trigger_configurator
from positron.ui.main_window import MainWindow
from picosdk.errors import DeviceNotFoundError


def main():
    """Main application entry point."""
    try:
        # Create Qt application
        app = create_application()
        app.setStyle('Fusion')  # Apply modern Qt style
        
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
                    return 1
        
        # Create Positron application instance
        positron_app = PositronApp()
        
        # Register the scope connection
        positron_app.connect_scope(scope_info)
        
        # Phase 1.3: Apply scope configuration
        try:
            configurator = create_configurator(scope_info)
            configurator.apply_configuration()
            
            # Store achieved values in config
            sample_rate = configurator.get_actual_sample_rate()
            total_samples, pre_samples = configurator.get_sample_counts()
            voltage_range_code = configurator.get_voltage_range_code()
            timebase_info = configurator.get_timebase_info()
            
            positron_app.config.scope.sample_rate = sample_rate
            positron_app.config.scope.waveform_length = total_samples
            positron_app.config.scope.pre_trigger_samples = pre_samples
            positron_app.config.scope.voltage_range_code = voltage_range_code
            positron_app.config.scope.timebase_index = timebase_info.timebase_index
            positron_app.save_config()
            
        except Exception as e:
            # Configuration failed
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("Configuration Error")
            error_msg.setText("Failed to configure the oscilloscope.")
            error_msg.setInformativeText(str(e))
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec()
            
            # Clean up and exit
            positron_app.disconnect_scope()
            return 1
        
        # Phase 1.4: Apply saved trigger configuration
        try:
            
            # Apply saved trigger configuration to scope
            trigger_configurator = create_trigger_configurator(scope_info)
            trigger_info = trigger_configurator.apply_trigger(positron_app.config.scope.trigger)
            
        except Exception as e:
            # Trigger configuration failed
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("Trigger Configuration Error")
            error_msg.setText("Failed to configure the trigger.")
            error_msg.setInformativeText(str(e))
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec()
            
            # Clean up and exit
            positron_app.disconnect_scope()
            return 1
        
        # Phase 2: Create and show main window
        main_window = MainWindow(positron_app)
        main_window.show()
        
        # Start Qt event loop
        return app.exec()
        
    except Exception as e:
        print(f"Error starting application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
