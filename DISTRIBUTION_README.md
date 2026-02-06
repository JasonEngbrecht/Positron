# Positron - Data Acquisition System
**User Guide for Students and Researchers**

## What is Positron?

Positron is a data acquisition and analysis system for pulse detection experiments using PicoScope oscilloscopes. It is designed specifically for positron annihilation lifetime spectroscopy (PALS) and related nuclear physics experiments.

## System Requirements

- **Operating System**: Windows 10 or later (64-bit)
- **Hardware**: PicoScope oscilloscope (3000 or 6000 series)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Storage**: 500 MB for application
- **Required Software**: PicoScope SDK drivers (see installation below)

## Installation

### Step 1: Install PicoScope Drivers

**IMPORTANT**: You must install the PicoScope drivers before running Positron.

1. Visit: https://www.picotech.com/downloads
2. Select your PicoScope model (e.g., 3406D MSO or 6402D)
3. Download and install the PicoSDK package
4. **Restart your computer** after installation

### Step 2: Extract Positron

1. Unzip the Positron folder to your desired location
2. Recommended: `C:\Program Files\Positron\` or `C:\Users\YourName\Documents\Positron\`
3. Keep all files in the extracted folder together

### Step 3: Connect Hardware

1. Connect your PicoScope to a USB port (USB 3.0 recommended for best performance)
2. Wait for Windows to recognize the device
3. Ensure your detectors are connected to the oscilloscope channels

### Step 4: Launch Positron

1. Navigate to the extracted Positron folder
2. Double-click **`Positron.exe`**
3. The application will automatically detect and connect to your PicoScope
4. You should see the model and serial number displayed in the window title

## First Time Setup

When you first launch Positron, you'll see four main tabs:

1. **Home** - Control data acquisition and view live waveforms
2. **Calibration** - Calibrate your detectors for energy measurements
3. **Energy Display** - View energy spectra
4. **Timing Display** - Analyze timing differences between channels

## Getting Help

**Positron has comprehensive built-in help documentation.**

### Access Help:
- Press **F1** at any time for Getting Started guide
- Use the **Help menu** at the top of the window:
  - Getting Started (F1)
  - Home Panel
  - Energy Display Panel
  - Timing Display Panel
  - Calibration Panel

**The in-app help provides detailed instructions for:**
- Configuring triggers
- Acquiring data
- Performing energy calibration
- Analyzing results
- Troubleshooting common issues

## Quick Start Workflow

1. **Launch Positron** and verify your PicoScope is detected
2. **Press F1** to open the Getting Started guide
3. Follow the in-app instructions for your specific experiment
4. Use the Help menu for detailed guidance on each panel

## Troubleshooting Installation

### PicoScope Not Detected

If Positron reports "No PicoScope device detected":

1. Check the USB connection (try a different port)
2. Verify the scope is powered on
3. Confirm PicoScope drivers are installed:
   - Go to Windows Device Manager
   - Look for "Pico Technology" devices
   - If missing or showing errors, reinstall drivers
4. Close PicoScope software if it's running (only one program can connect at a time)
5. Restart Positron

### Application Won't Start

If Positron.exe won't launch:

1. Ensure all files from the zip are extracted together
2. Check Windows antivirus hasn't quarantined files
3. Right-click Positron.exe → Properties → Unblock (if option appears)
4. Try running as Administrator (right-click → Run as administrator)

### Missing DLL Errors

If you see errors about missing DLL files:
- Reinstall PicoScope drivers (PicoSDK)
- Ensure you extracted the entire Positron folder, not just the .exe file

## Technical Support

For help with Positron:

1. **First**: Check the in-app Help menu (press F1)
2. **Installation issues**: Verify drivers are installed and PicoScope is detected
3. **Usage questions**: Consult your lab instructor or supervisor
4. **Bug reports**: Provide:
   - PicoScope model (shown in window title)
   - Windows version
   - Error messages (take screenshots)
   - Steps to reproduce the issue

## Hardware Configuration

Positron automatically configures your PicoScope with optimized settings for pulse detection:

- **Voltage Range**: 100 mV (all 4 channels)
- **Sample Rate**: Maximum available (typically 250 MS/s to 1.25 GS/s)
- **Capture Window**: 3 µs (1 µs pre-trigger, 2 µs post-trigger)
- **Trigger**: -5 mV threshold, falling edge, configurable logic

These settings are optimized for typical PALS experiments and do not require adjustment.

### IMPORTANT: Input Impedance Configuration

**Input impedance must be 50 Ω for proper signal termination.** The setup differs between PicoScope models:

#### 6000 Series (e.g., 6402D)
✅ **Software-Controlled**: Positron automatically configures the input impedance to 50 Ω in software. No external termination needed.

#### 3000 Series (e.g., 3406D MSO)
⚠️ **External Termination Required**: The 3000 series has fixed 1 MΩ input impedance. You MUST add external 50 Ω terminators to each active channel.

**Recommended Setup: BNC T-Connector with 50 Ω Terminator**

```
Signal Source (Detector)
         |
         | (BNC cable)
         |
    ┌────▼────┐
    │  BNC T  │  (T-connector on scope input)
    └─┬─────┬─┘
      │     │
      │     └─────── 50 Ω Terminator (BNC plug with 50 Ω resistor)
      │
      └─────────────► PicoScope Channel Input (A, B, C, or D)
```

**Parts Needed (for 3000 series):**
- 4× BNC T-connectors (one per channel)
- 4× 50 Ω BNC terminators (standard coaxial terminators)
- Available from electronics suppliers (e.g., Pomona Electronics, Amphenol)

**Why 50 Ω Termination Matters:**
- Prevents signal reflections and ringing
- Matches the cable impedance (RG-58 coax is 50 Ω)
- Provides correct signal amplitude
- Essential for accurate timing measurements

**Verification:**
- With proper termination, your baseline should be stable near 0 mV
- Without termination, you may see reflections, overshoot, and incorrect pulse shapes

## About Positron

**Version**: 1.1.0  
**Compatible Hardware**: PicoScope 3000a and 6000 series  
**License**: Educational and research use

Positron was developed for nuclear physics laboratory experiments, providing:
- Real-time 4-channel waveform display
- Event-mode acquisition (up to 10,000 events/second)
- Constant Fraction Discrimination (CFD) timing analysis
- Energy calibration with standard sources
- Interactive histogram displays

**Technology Stack**: Python, PySide6 (Qt), PyQtGraph, NumPy, PicoSDK

---

**Remember**: Press **F1** or use the **Help menu** for complete documentation on using Positron!
