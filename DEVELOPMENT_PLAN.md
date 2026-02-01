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

## Phase 1: Foundation & Scope Communication

**Goal**: Establish basic application structure and reliable oscilloscope communication.

### 1.1 Project Structure
- Set up Python project with proper package structure
- Create main application entry point
- Establish configuration management (scope settings, defaults)

### 1.2 Scope Connection
- Implement scope discovery and connection for 3000 and 6000 series
- Create startup dialog for scope series selection
- Handle connection errors gracefully
- Implement scope disconnection/cleanup

### 1.3 Basic Scope Configuration
- Configure maximum sample rate (automatic based on scope model)
- Set voltage range (preset, same for all channels)
- Configure pre-trigger sample capture
- Set waveform length (1000-2000 samples, configurable)

### 1.4 Trigger Configuration
- Implement advanced trigger setup using Picoscope's AND/OR logic
- Create UI for selecting trigger channels and logic combinations
- Store/recall trigger configurations

**Deliverable**: Application that connects to a Picoscope and configures basic acquisition parameters.

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
├── main.py
├── positron/
│   ├── __init__.py
│   ├── app.py                 # Main application class
│   ├── config.py              # Configuration management
│   ├── scope/
│   │   ├── __init__.py
│   │   ├── connection.py      # Scope discovery and connection
│   │   ├── acquisition.py     # Data acquisition engine
│   │   └── trigger.py         # Trigger configuration
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
