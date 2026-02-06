# Positron - Data Acquisition System

**A high-performance data acquisition and analysis system for nuclear physics experiments**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

Positron is a Python-based application designed for pulse detection experiments using PicoScope oscilloscopes. Built specifically for positron annihilation lifetime spectroscopy (PALS) and related nuclear and particle physics experiments.

![Positron Screenshot](docs/screenshot.png) <!-- Add a screenshot if you have one -->

## 🎯 Features

- **Real-time Waveform Display**: 4-channel live visualization at 3 Hz
- **Event-Mode Acquisition**: Capture up to 10,000 events/second
- **Advanced Pulse Analysis**: CFD timing (sub-nanosecond resolution) and energy integration
- **Energy Calibration**: Interactive calibration using Na-22 gamma sources
- **Analysis Panels**: Energy histograms and timing difference analysis
- **Hardware Support**: PicoScope 3000a and 6000a series (tested on PS3406D MSO)

## 📥 Downloads

### For Students/End Users

**Download the standalone executable** - No Python installation required!

👉 **[Download Latest Release (Windows)](https://github.com/JasonEngbrecht/Positron/releases/tag/v1.1.0)**

1. Download `Positron_v1.1.0.zip` from the Releases page
2. Extract to your desired location
3. Install PicoScope drivers (see Requirements below)
4. Run `Positron.exe`
5. Read `Positron_User_Manual.pdf` for instructions

### For Developers

Clone this repository and install from source:

```bash
git clone https://github.com/YOUR_USERNAME/Positron.git
cd Positron
pip install -r requirements.txt
python main.py
```

## 📋 Requirements

### System Requirements
- **OS**: Windows 10 or later (64-bit)
- **Hardware**: PicoScope oscilloscope (3000a or 6000a series)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Storage**: 500 MB for application + data

### Required Drivers
**PicoScope SDK must be installed:**
- Download from: https://www.picotech.com/downloads
- Install the PicoSDK package for your scope model
- Restart your computer after installation

### Python Requirements (Source Only)
- Python 3.9 or later
- See `requirements.txt` for dependencies

## 🚀 Quick Start

### Using the Executable

1. **Connect your PicoScope** via USB
2. **Launch** `Positron.exe`
3. **Configure trigger** in the Home panel
4. **Start acquisition** to collect data
5. **Calibrate** using Na-22 source in Calibration panel
6. **Analyze** results in Energy Display and Timing Display panels

See `Positron_User_Manual.pdf` for detailed instructions.

### Running from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## 📖 Documentation

- **[User Manual](DISTRIBUTION_README.md)** - Complete guide for students
- **[Architecture](ARCHITECTURE.md)** - Technical documentation for developers
- **[Build Guide](BUILD_GUIDE.md)** - Instructions for building from source

## 🏗️ Building from Source

To create your own executable:

```bash
pip install pyinstaller reportlab
.\build.bat           # Build executable (Windows) - automatically generates PDF
```

The executable will be in `dist\Positron\`

## 🔬 Technical Details

### Technology Stack
- **GUI**: PySide6 (Qt 6)
- **Plotting**: PyQtGraph
- **Processing**: NumPy
- **Hardware Interface**: picosdk-python-wrappers
- **Packaging**: PyInstaller

### Hardware Configuration
- **Voltage Range**: 100 mV (all 4 channels)
- **Sample Rate**: Up to 250 MS/s (model dependent)
- **Capture Window**: 3 µs (1 µs pre-trigger, 2 µs post-trigger)
- **Trigger**: Configurable logic (AND/OR combinations)
- **Data Storage**: In-memory (up to 1 million events)

### Pulse Analysis
- **Timing**: Constant Fraction Discrimination (CFD) at 50%
- **Energy**: Baseline-corrected integration
- **Resolution**: Sub-nanosecond timing, keV energy (after calibration)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses
This software uses the following libraries:
- **PySide6**: LGPL v3
- **PyQtGraph**: MIT
- **NumPy**: BSD
- **picosdk-python-wrappers**: ISC
- **PyInstaller**: GPL with bundling exception

## 🙏 Acknowledgments

Developed for nuclear physics laboratory experiments at [Your Institution].

Special thanks to:
- Students and instructors who provided feedback
- Pico Technology for excellent hardware and SDK
- The Python scientific computing community

## 📧 Support

For questions, issues, or contributions:
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/Positron/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/Positron/discussions)
- **Email**: [Your contact email]

## 🗺️ Roadmap

- [ ] Export data to CSV/ROOT formats
- [ ] Additional analysis tools (2D histograms, peak fitting)
- [ ] PicoScope 6000a series implementation
- [ ] macOS/Linux support
- [ ] Automated calibration procedures

## 📊 Project Status

**Current Version**: 1.1.0

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Foundation & Scope Communication |
| Phase 2 | ✅ Complete | Home Panel & Basic Acquisition |
| Phase 3 | ✅ Complete | Backend Processing Engine |
| Phase 4 | ✅ Complete | Calibration Panel |
| Phase 5 | ✅ Complete | Analysis Panels |
| Phase 6 | ✅ Complete | Polish & Packaging |

---

**Developed with ❤️ for nuclear physics education**

*Last Updated: February 2026*
