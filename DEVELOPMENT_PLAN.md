# Positron Development Plan

## Project Overview

A Python-based data acquisition and analysis system for pulse detection experiments using Picoscope oscilloscopes (3000 or 6000 series). The system operates in event mode, capturing timing and energy information from 4-channel waveforms triggered by configurable hardware logic. Designed for experiments including positron annihilation lifetime spectroscopy (PALS) and related techniques.

---

## Technology Stack

### GUI Framework: PySide6
PySide6 provides the core application framework, offering a robust Qt-based interface with support for tabbed layouts, responsive widgets, and cross-platform compatibility (Windows, macOS, Linux). Licensed under LGPL, allowing free use in closed-source applications.

### Data Visualization: PyQtGraph
PyQtGraph handles all plotting including XY scatter plots, waveform displays, and histograms. It offers fast rendering performance optimized for real-time data display, making it ideal for live oscilloscope data streaming and high-rate event visualization. Integrates seamlessly with PySide6. Licensed under MIT.

### Numerical Processing: NumPy
NumPy provides efficient array operations essential for batch waveform processing, pulse analysis, and histogram calculations. Required for achieving target throughput of 10,000 events/second. Licensed under BSD.

### Oscilloscope Interface: picosdk-python-wrappers
The official Python wrapper library from Pico Technology enables communication with Picoscope oscilloscope hardware. Supports streaming mode, block mode capture, rapid block mode for batch acquisition, and advanced trigger configuration (AND/OR logic) across the 3000 and 6000 series. Licensed under ISC.

### Application Packaging: PyInstaller
PyInstaller packages the complete application into a standalone executable that can be distributed and installed on other machines without requiring a Python environment.

### Licensing Summary

All libraries in this stack use permissive open-source licenses (LGPL, MIT, BSD, ISC) that allow free use in closed-source and commercial applications. The only requirement is to include the respective license notices in the distribution.

| Library | License |
|---------|---------|
| PySide6 | LGPL |
| PyQtGraph | MIT |
| NumPy | BSD |
| picosdk-python-wrappers | ISC |
| PyInstaller | GPL (build tool only, does not affect your code) |

### Requirements

- Python 3.9+
- Picoscope oscilloscope hardware (3000 or 6000 series)
- Picoscope SDK installed on the system

### Installation

```bash
pip install PySide6 pyqtgraph numpy picosdk
```

---

## Phase 1: Foundation & Scope Communication ✅ COMPLETE

**Goal**: Establish basic application structure and reliable oscilloscope communication.

**Status**: Fully implemented for PS3000a series. PS6000a stubs in place for future implementation.

### 1.1 Project Structure ✅
- Python package structure with proper module organization
- Main application entry point (`main.py`)
- Configuration management system with JSON persistence
- Application state manager (`positron/app.py`)

### 1.2 Scope Connection ✅
**Files**: `positron/scope/connection.py`

**Implemented**:
- Automatic scope discovery (tries PS3000a first, then PS6000a)
- Power state handling (status codes 282, 286)
- Device information retrieval (variant, serial, max ADC)
- Connection error handling with retry/cancel dialogs
- Proper cleanup and disconnection
- Configuration persistence

**Series Support**:
- ✅ PS3000a: Fully implemented and tested (PicoScope 3406D MSO)
- ⏳ PS6000a: Framework in place, full implementation pending

### 1.3 Basic Scope Configuration ✅
**Files**: `positron/scope/configuration.py`

**Hardcoded Settings** (optimized for pulse detection):
- Voltage range: 100 mV on all 4 channels
- Coupling: DC
- Channels: All 4 enabled (A, B, C, D)
- Sample rate: Maximum available (250 MS/s on PS3406D)
- Capture window: 1 µs pre-trigger, 2 µs post-trigger (3 µs total)

**Implementation**:
- Protocol-based design (`ScopeConfigurator`)
- Automatic timebase calculation for time-based sampling
- Sample count calculation based on achieved sample rate
- Factory function for series-specific instantiation

**Series Support**:
- ✅ PS3000a: `PS3000aConfigurator` fully implemented
- ⏳ PS6000a: `PS6000aConfigurator` stub ready for implementation

### 1.4 Trigger Configuration ✅
**Files**: `positron/scope/trigger.py`, `positron/ui/trigger_dialog.py`, `positron/config.py`

**Hardcoded Settings** (optimized for negative pulses):
- Threshold: -5 mV
- Direction: Falling edge
- Hysteresis: 10 ADC counts
- Auto-trigger: Disabled or 60s maximum

**User-Configurable**:
- Up to 4 trigger conditions (OR logic between conditions)
- Channel selection per condition: A, B, C, D (AND logic within condition)
- Auto-trigger timeout on/off

**Implementation**:
- Protocol-based design (`TriggerConfigurator`)
- Advanced AND/OR logic using multiple condition structures
- PySide6 dialog with intuitive UI for configuration
- Configuration persistence and defaults
- Complete PS3000a API integration:
  - `ps3000aSetTriggerChannelProperties` for threshold levels
  - `ps3000aSetTriggerChannelConditionsV2` for AND/OR logic
  - `ps3000aSetTriggerChannelDirections` for edge direction

**Series Support**:
- ✅ PS3000a: `PS3000aTriggerConfigurator` fully implemented
- ⏳ PS6000a: `PS6000aTriggerConfigurator` stub ready for implementation

### Phase 1 Summary

**Completed Components**:
- ✅ Application framework and configuration system
- ✅ PS3000a scope detection and connection
- ✅ PS3000a channel configuration (100mV, DC, 4 channels, max rate)
- ✅ PS3000a trigger configuration with AND/OR logic
- ✅ User interface for trigger setup
- ✅ Configuration persistence to disk

**Tested Hardware**: PicoScope 3406D MSO (PS3000a series)

**Future Work** (PS6000a series):
- Implement `PS6000aConfigurator` in `configuration.py`
- Implement `PS6000aTriggerConfigurator` in `trigger.py`
- Test with PS6000a hardware
- Note: Data structures and UI are already series-agnostic

**Deliverable**: ✅ Application successfully connects to PS3000a scopes and configures all acquisition parameters (channels, sample rate, trigger logic). Ready for Phase 2 acquisition implementation.

---

## Phase 2: Home Panel & Basic Acquisition

**Goal**: Create the main control interface with live waveform display.

### 2.1 Main Window Framework
- Implement tabbed interface using PySide6
- Create Home Panel as the default/startup tab
- Establish panel navigation

### 2.2 Waveform Display
- Create 4-channel waveform display using PyQtGraph
- Implement display update rate limiting (3 Hz max or acquisition rate, whichever is slower)
- Show representative waveforms for verification (not every acquisition)

### 2.3 Acquisition Controls
- Start/Stop buttons for manual control
- Preset time duration stop
- Preset event count stop
- Display current event count and elapsed time

### 2.4 Home Panel Save Features
- Define what data the home panel saves (event data CSV, run metadata, etc.)
- Implement save functionality (disabled during acquisition)

**Deliverable**: Functional home panel showing live waveforms with acquisition control.

---

## Phase 3: Backend Processing Engine

**Goal**: Implement high-performance event-mode data processing.

### 3.1 Acquisition Architecture
- Implement batch acquisition from Picoscope (rapid block mode)
- Design producer-consumer pattern for acquisition → processing pipeline
- Use threading/multiprocessing appropriately for performance

### 3.2 Pulse Analysis
- Detect pulse presence in each channel (0 or 1 pulse expected; use first if multiple)
- Extract pulse timing relative to trigger
- Extract pulse energy (area under peak)
- Handle baseline determination (details TBD)
- Handle integration method (details TBD)

### 3.3 Event Storage
- Define event data structure: timestamp + (timing, energy) × 4 channels
- Implement efficient in-memory event storage
- Support for high event rates (up to 10,000 events/second)

### 3.4 Performance Optimization
- Profile and optimize for target throughput
- Implement batch processing for pulse analysis
- Minimize memory allocations in hot paths

**Deliverable**: Backend capable of acquiring and processing events at up to 10,000/second.

---

## Phase 4: Calibration Panel

**Goal**: Implement energy calibration using Na-22 source.

### 4.1 Calibration UI
- Create calibration panel tab
- Display energy histogram for calibration data
- Allow channel selection for calibration

### 4.2 Peak Identification
- Display histogram of uncalibrated energy values
- Allow user to identify 511 keV and 1275 keV peaks
- Support peak selection via UI interaction (click or region selection)

### 4.3 Calibration Calculation
- Perform two-point linear calibration (gain and offset)
- Apply calibration to convert raw energy to keV
- Store calibration parameters per channel

### 4.4 Calibration Save Features
- Save calibration parameters
- Load previously saved calibration (if needed)

**Deliverable**: Working energy calibration workflow using Na-22 two-point calibration.

---

## Phase 5: Analysis Panels Framework

**Goal**: Create extensible framework for analysis panels with initial implementations.

### 5.1 Analysis Panel Architecture
- Design base class/pattern for analysis panels
- Implement panel registration system
- Support both live updates during acquisition and post-acquisition analysis

### 5.2 Data Access Layer
- Provide analysis panels access to event data
- Implement data filtering interface (energy windows, timing windows, coincidence requirements)
- Support efficient querying of large event datasets

### 5.3 Initial Analysis Panels (specifics TBD)
- Energy histogram panel
- Timing histogram panel
- Additional panels as requirements are defined

### 5.4 Analysis Panel Save Features
- Each panel implements its own save functionality
- Save filtered data, histogram data, analysis results as appropriate

**Deliverable**: Extensible analysis framework with initial panel implementations.

---

## Phase 6: Polish & Packaging

**Goal**: Prepare for distribution and student use.

### 6.1 Error Handling & Robustness
- Comprehensive error handling throughout
- Graceful handling of scope disconnection
- User-friendly error messages

### 6.2 UI Polish
- Consistent styling across panels
- Responsive layout
- Helpful tooltips and labels

### 6.3 Packaging
- PyInstaller configuration for standalone executable
- Include necessary Picoscope SDK dependencies
- Test on clean Windows installation

### 6.4 Documentation
- User guide for students
- Installation instructions
- Troubleshooting guide

**Deliverable**: Distributable standalone application ready for student use.

---

## Technical Decisions & Notes

### Architecture Decisions
- **Threading model**: Separate threads for acquisition, processing, and UI
- **Data flow**: Acquisition → Processing Queue → Event Storage → UI/Analysis
- **Event storage**: In-memory only; CSV export between runs
- **Hardware configuration**: Fixed optimal settings (100mV, 4 channels, DC coupling, max rate)
- **Sample timing**: Time-based (1 µs pre-trigger, 2 µs post-trigger) with automatic sample count calculation

### Open Questions (to be resolved during development)
- Baseline determination method
- Pulse integration method  
- Specific analysis panel requirements
- Exact save formats for each panel type

### Performance Targets
- Support up to 10,000 events/second
- Waveform display at 3 Hz (or slower if acquisition rate is lower)
- Responsive UI during high-rate acquisition

---

## File Structure (Proposed)

```
Positron/
├── README.md
├── DEVELOPMENT_PLAN.md
├── requirements.txt
├── main.py                    # Application entry point (startup script)
├── positron/
│   ├── __init__.py
│   ├── app.py                 # Application state manager (PositronApp class)
│   ├── config.py              # Configuration management (simplified - stores achieved values only)
│   ├── scope/
│   │   ├── __init__.py
│   │   ├── connection.py      # Scope discovery and connection (Phase 1.2 ✅)
│   │   ├── configuration.py   # Scope hardware configuration (Phase 1.3 ✅)
│   │   ├── acquisition.py     # Data acquisition engine (Phase 2/3)
│   │   └── trigger.py         # Trigger configuration (Phase 1.4)
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── pulse.py           # Pulse detection and analysis
│   │   └── events.py          # Event storage and management
│   ├── calibration/
│   │   ├── __init__.py
│   │   └── energy.py          # Energy calibration
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── base.py            # Base panel class
│   │   ├── home.py            # Home panel
│   │   ├── calibration.py     # Calibration panel
│   │   └── analysis/          # Analysis panels
│   │       ├── __init__.py
│   │       └── ...
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py     # Main window with tabs
│       ├── waveform_plot.py   # Waveform display widget
│       └── widgets/           # Reusable UI components
└── tests/
    └── ...
```
