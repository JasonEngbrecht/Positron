# Positron

A Python-based data acquisition and analysis system for pulse detection experiments using Picoscope oscilloscopes (3000 or 6000 series). The system operates in event mode, capturing timing and energy information from 4-channel waveforms triggered by configurable hardware logic. Designed for experiments including positron annihilation lifetime spectroscopy (PALS) and related techniques.

## Requirements

- Python 3.9+
- Picoscope oscilloscope hardware (3000 or 6000 series)
- Picoscope SDK installed on the system

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the Picoscope SDK is installed on your system (required by the `picosdk` package).

## Running the Application

```bash
python main.py
```

## Project Status

Currently implementing Phase 1: Foundation & Scope Communication.

- ✅ Phase 1.1: Project Structure - Complete
- ✅ Phase 1.2: Scope Connection - Complete
  - Automatic detection of PS3000a/PS6000a series
  - Device information retrieval
  - Power state handling
  - Configuration persistence
- ⏳ Phase 1.3: Basic Scope Configuration - Pending
- ⏳ Phase 1.4: Trigger Configuration - Pending

## Development

See `DEVELOPMENT_PLAN.md` for detailed development phases and architecture decisions.

## License

This project uses the following open-source libraries:
- PySide6 (LGPL)
- PyQtGraph (MIT)
- NumPy (BSD)
- picosdk-python-wrappers (ISC)

All dependencies use permissive licenses that allow free use in closed-source and commercial applications.
