# Positron - Data Acquisition System

**Version**: 1.0 (Phase 5 Complete)  
**For**: Nuclear and Particle Physics Experiments

## Overview

Positron is a data acquisition and analysis system for pulse detection experiments using PicoScope oscilloscopes. Designed for positron annihilation lifetime spectroscopy (PALS) and related nuclear physics experiments.

## Quick Start

### System Requirements

- **Operating System**: Windows 10 or later (64-bit)
- **Hardware**: PicoScope oscilloscope (3000 or 6000 series)
- **Drivers**: PicoScope SDK must be installed (see Installation below)

### Installation

1. **Install PicoScope Drivers**:
   - Download from: https://www.picotech.com/downloads
   - Select your PicoScope model
   - Install the PicoSDK package
   - Restart your computer

2. **Extract Positron Application**:
   - Unzip the provided folder to your desired location
   - Example: `C:\Program Files\Positron\`

3. **Connect Your PicoScope**:
   - Connect the oscilloscope to a USB port
   - Wait for Windows to recognize the device

4. **Launch Positron**:
   - Double-click `Positron.exe`
   - The application will automatically detect your scope
   - If no scope is detected, check connections and drivers

## Using Positron

### Main Panels

The application has four main tabs:

1. **Home** - Acquisition control and live waveform display
2. **Calibration** - Energy calibration using Na-22 source
3. **Energy Display** - Calibrated energy histograms
4. **Timing Display** - Timing difference analysis

### Typical Workflow

#### 1. Configure Trigger (Home Panel)

- Click "Configure Trigger" button
- Set up logic: A OR B OR C OR D (for coincidence detection)
- Or use specific channel combinations for your experiment
- Click "Apply" to save

#### 2. Acquire Data (Home Panel)

- Set optional limits:
  - Time limit (hours:minutes:seconds)
  - Event count limit
- Click "Start Acquisition"
- Monitor:
  - Live waveforms (4 channels: Red=A, Green=B, Blue=C, Orange=D)
  - Event count
  - Acquisition rate (events/second)
  - Elapsed time
- Use "Pause/Resume" to temporarily stop
- Use "Restart" to clear counters and start fresh

#### 3. Calibrate Energy (Calibration Panel)

**Prerequisites**: Na-22 radioactive source (511 keV and 1275 keV gamma peaks)

For each channel (A, B, C, D):

1. Click "Update All Histograms" to view energy spectrum
2. Adjust bins (1000 recommended) and toggle log scale as needed
3. Drag the **green region** over the 511 keV peak
4. Drag the **blue region** over the 1275 keV peak
5. Click "Find Peaks" - values appear in text boxes
6. Click "Calculate Calibration"
7. Click "Apply to [Channel]"
8. Repeat for all channels you want to calibrate

**Tips**:
- Collect 1000+ events before calibrating
- Use log scale to see peaks clearly
- Peaks should be well-separated
- Save configuration when done (automatic on exit)

#### 4. Analyze Data

**Energy Display Panel**:
- View calibrated energy histograms for all channels
- Toggle individual channels on/off
- Switch between linear and log Y-axis
- Auto-update every 2 seconds during acquisition
- Manual binning control available

**Timing Display Panel**:
- Analyze timing differences between channel pairs
- Up to 4 slots for different pair comparisons
- Energy filtering (requires calibrated channels):
  - Set energy windows for each channel
  - Only events within windows are included
- Auto-update every 2 seconds during acquisition

### Tips and Best Practices

1. **Acquisition Rate**:
   - System supports up to 10,000 events/second
   - Typical rates: 100-1000 events/second
   - Lower rates → better signal quality

2. **Trigger Configuration**:
   - Use "OR" logic for maximum event capture
   - Use "AND" logic for coincidence requirements
   - Adjust based on your experimental needs

3. **Calibration**:
   - Calibrate with good statistics (1000+ events)
   - Recalibrate if detector conditions change
   - Save configuration before closing

4. **Data Management**:
   - Currently stores up to 1 million events in memory
   - Close and restart for new experiments
   - Export functionality (coming in future updates)

5. **Performance**:
   - Close other applications during acquisition
   - Keep acquisition window visible for best performance
   - Pause if you need to do lengthy analysis

## Hardware Configuration

The system is optimized for pulse detection with fixed settings:

- **Voltage Range**: 100 mV (all channels)
- **Coupling**: DC
- **Channels**: 4 (A, B, C, D)
- **Sample Rate**: Maximum available (typically 250 MS/s for PS3000a)
- **Capture Window**: 
  - Pre-trigger: 1 µs
  - Post-trigger: 2 µs
  - Total: 3 µs

**Trigger Settings**:
- Threshold: -5 mV
- Edge: Falling
- Hysteresis: 10 ADC counts
- Logic: User-configurable (OR/AND combinations)

## Troubleshooting

### Scope Not Detected

1. Check USB connection
2. Verify scope is powered on
3. Install/reinstall PicoScope drivers
4. Try a different USB port
5. Restart the application

### No Events Detected

1. Check signal connections
2. Verify trigger configuration
3. Adjust trigger threshold if needed
4. Check that signals exceed 5 mV threshold

### Application Crashes or Errors

1. Check console output for error messages
2. Verify all cables are connected properly
3. Restart the scope and application
4. Reinstall PicoScope drivers if persistent

### Low Acquisition Rate

1. Close other applications
2. Reduce number of active analysis panels
3. Check USB connection quality
4. Verify scope temperature (cooling)

## Technical Support

For issues or questions:

1. Check the troubleshooting section above
2. Review console output for error messages
3. Contact your lab instructor or supervisor
4. Provide detailed information:
   - PicoScope model
   - Windows version
   - Error messages
   - Steps to reproduce the issue

## About

**Positron** was developed for nuclear physics laboratory experiments, specifically designed for positron annihilation lifetime spectroscopy (PALS) and related particle detection experiments.

### Key Features

- Real-time waveform display (4 channels)
- Event-mode acquisition (up to 10,000 events/s)
- Pulse analysis (CFD timing, energy integration)
- Energy calibration using standard sources
- Multiple analysis panels for visualization
- Thread-safe data management

### Technology

- **Framework**: PySide6 (Qt)
- **Plotting**: PyQtGraph
- **Processing**: NumPy
- **Hardware Interface**: PicoSDK Python wrappers

### License

Educational and research use.

---

**Development**: Phase 5 Complete  
**Last Updated**: February 2026  
**Compatible**: PicoScope 3000a, 6000a series

## Acknowledgments

Developed for student laboratory experiments in nuclear and particle physics.

---

For updates and documentation, contact your lab supervisor.
