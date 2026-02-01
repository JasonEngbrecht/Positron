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
        
        # Phase 1.3: Apply scope configuration
        try:
            print("\nApplying scope configuration...")
            configurator = create_configurator(scope_info)
            configurator.apply_configuration()
            
            # Store achieved values in config
            sample_rate = configurator.get_actual_sample_rate()
            total_samples, pre_samples = configurator.get_sample_counts()
            
            positron_app.config.scope.sample_rate = sample_rate
            positron_app.config.scope.waveform_length = total_samples
            positron_app.config.scope.pre_trigger_samples = pre_samples
            positron_app.save_config()
            
            # Get detailed timebase info for display
            timebase_info = configurator.get_timebase_info()
            
            print("Scope configuration applied successfully:")
            print(f"  Voltage range: 100 mV (all 4 channels)")
            print(f"  Coupling: DC")
            print(f"  Channels enabled: A, B, C, D")
            print(f"  Sample rate: {sample_rate / 1e6:.2f} MS/s")
            print(f"  Timebase index: {timebase_info.timebase_index}")
            print(f"  Sample interval: {timebase_info.sample_interval_ns:.2f} ns")
            print(f"  Total samples: {total_samples}")
            print(f"  Pre-trigger samples: {pre_samples} ({pre_samples / sample_rate * 1e6:.3f} µs)")
            print(f"  Post-trigger samples: {timebase_info.post_trigger_samples} ({timebase_info.post_trigger_samples / sample_rate * 1e6:.3f} µs)")
            print(f"  Total capture time: {total_samples / sample_rate * 1e6:.3f} µs")
            
            # Show configuration success message
            config_msg = QMessageBox()
            config_msg.setIcon(QMessageBox.Information)
            config_msg.setWindowTitle("Positron - Configuration Complete")
            config_msg.setText("Scope configured successfully!")
            config_msg.setInformativeText(
                f"Sample Rate: {sample_rate / 1e6:.2f} MS/s\n"
                f"Voltage Range: 100 mV (all channels)\n"
                f"Channels: A, B, C, D enabled\n"
                f"Capture Window: {total_samples / sample_rate * 1e6:.3f} µs\n"
                f"  Pre-trigger: {pre_samples / sample_rate * 1e6:.3f} µs\n"
                f"  Post-trigger: {timebase_info.post_trigger_samples / sample_rate * 1e6:.3f} µs\n\n"
                "Phase 1.3 complete: Basic scope configuration."
            )
            config_msg.setStandardButtons(QMessageBox.Ok)
            config_msg.exec()
            
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
