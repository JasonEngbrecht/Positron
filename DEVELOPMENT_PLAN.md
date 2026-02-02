# Positron Development Plan

## Project Overview

A Python-based data acquisition and analysis system for pulse detection experiments using Picoscope oscilloscopes (3000 or 6000 series). The system operates in event mode, capturing timing and energy information from 4-channel waveforms triggered by configurable hardware logic. Designed for experiments including positron annihilation lifetime spectroscopy (PALS) and related techniques.

## Technology Stack

- **PySide6**: Qt-based GUI framework
- **PyQtGraph**: Fast plotting for real-time data visualization
- **NumPy**: Array operations for waveform processing
- **picosdk-python-wrappers**: Official Pico Technology oscilloscope interface
- **PyInstaller**: Application packaging (future)

**Requirements**: Python 3.9+, Picoscope hardware (3000 or 6000 series), Picoscope SDK

```bash
pip install PySide6 pyqtgraph numpy picosdk
```

---

## Development Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Foundation & Scope Communication |
| Phase 2 | ✅ Complete | Home Panel & Basic Acquisition |
| Phase 3 | ✅ Complete | Backend Processing Engine |
| Phase 4 | ✅ Complete | Calibration Panel |
| Phase 5 | ✅ Complete | Analysis Panels (Energy & Timing) |
| Phase 6 | ⏳ Pending | Polish & Packaging |

**Hardware Support**: PS3000a fully implemented and tested (PicoScope 3406D MSO). PS6000a framework in place, needs implementation.

---

## Phase 1: Foundation & Scope Communication ✅

**Goal**: Establish basic application structure and reliable oscilloscope communication.

### Key Components

**Scope Connection** (`positron/scope/connection.py`)
- Automatic scope discovery (tries PS3000a first, then PS6000a)
- Power state handling and device information retrieval
- Connection error handling with retry/cancel dialogs
- Proper cleanup and disconnection

**Scope Configuration** (`positron/scope/configuration.py`)
- Hardcoded settings optimized for pulse detection:
  - Voltage range: 100 mV on all 4 channels
  - Coupling: DC
  - Sample rate: Maximum available (250 MS/s on PS3406D)
  - Capture window: 1 µs pre-trigger, 2 µs post-trigger (3 µs total)
- Protocol-based design for series-specific implementations

**Trigger Configuration** (`positron/scope/trigger.py`, `positron/ui/trigger_dialog.py`)
- Hardcoded: -5 mV threshold, falling edge, 10 ADC hysteresis
- User-configurable: Up to 4 trigger conditions with OR logic, channel selection (AND logic within condition)
- PySide6 dialog with configuration persistence

**Configuration System** (`positron/config.py`, `positron/app.py`)
- JSON-based persistence
- Application state manager

---

## Phase 2: Home Panel & Basic Acquisition ✅

**Goal**: Create the main control interface with live waveform display.

### Key Components

**Main Window** (`positron/ui/main_window.py`)
- QTabWidget for multiple panels
- Menu bar with About dialog
- Graceful cleanup on close

**Waveform Display** (`positron/ui/waveform_plot.py`)
- PyQtGraph 4-channel overlay (Red=A, Green=B, Blue=C, Orange=D)
- Time axis in nanoseconds, voltage in millivolts
- 3 Hz update rate, auto-ranging enabled

**Acquisition Controls** (`positron/panels/home.py`, `positron/scope/acquisition.py`)
- Start/Pause/Resume toggle button
- Restart button (resets counters)
- Live statistics: event count, elapsed time (HH:MM:SS), rate (events/sec)
- Preset auto-stop: time limit and/or event count limit
- Trigger reconfiguration when paused

**Acquisition Engine** (`positron/scope/acquisition.py`)
- PS3000a rapid block mode for batch capture (default: 10 captures/batch)
- QThread-based with proper lifecycle management
- Protocol-based design for future PS6000a support
- Signals: `waveform_ready`, `batch_complete`, `acquisition_error`, `acquisition_finished`

### Design Decisions

- Raw waveform capture with event counting (1 event = 1 triggered waveform)
- Acquisition engine emits signals, doesn't store data
- Home panel tracks event count
- Resume adds to existing count, Restart clears and starts fresh
- Elapsed time excludes paused periods

---

## Phase 3: Backend Processing Engine ✅

**Goal**: Implement high-performance event-mode data processing.

### Key Components

**Pulse Analysis** (`positron/processing/pulse.py`)
- **Baseline**: Mean of pre-trigger samples (125 samples = 1 µs)
- **CFD Timing**: Digital Constant Fraction Discrimination (50% fraction)
  - Find peak after trigger, calculate threshold, find zero crossing with linear interpolation
  - Sub-sample resolution, time in ns relative to trigger
- **Energy Integration**: -Σ(waveform - baseline) × sample_interval_ns
  - Units: mV·ns (calibrated to keV in Phase 4)
- **Pulse Detection**: Amplitude threshold ≥ 5 mV (matches trigger)

**Event Storage** (`positron/processing/events.py`)
- Thread-safe storage using QMutex
- Python list-based (1M event capacity, ~700 MB memory)
- Global singleton accessible via `get_event_storage()`
- Methods: `add_event()`, `add_events()`, `get_count()`, `get_all_events()`, `clear()`

**Data Structures**
- `ChannelPulse`: timing_ns, energy, peak_mv, has_pulse
- `EventData`: event_id, timestamp, channels (dict with A, B, C, D)

**Processing Pipeline** (integrated in `acquisition.py`)
1. Scope captures batch (10 waveforms)
2. Convert ADC to mV for all 4 channels
3. Calculate baseline, extract CFD timing, calculate energy
4. Create EventData and store in EventStorage
5. Emit waveform for display

**Configuration** (`positron/config.py`)
- `cfd_fraction: 0.5` - Constant fraction for timing
- `max_events: 1,000,000` - Hard limit (~700 MB memory)

### Performance

- Processing: ~32 µs per event (8 µs × 4 channels)
- Supported rate: >1000 events/second
- Memory: ~750 bytes per event

### Design Decisions

- **Synchronous processing**: Events processed immediately after batch download in acquisition thread
- **Storage**: Python list with mutex (simple, sufficient for 1M events; future optimization: NumPy structured arrays for 10M+)

---

## Phase 4: Calibration Panel ✅

**Goal**: Implement energy calibration using Na-22 source (511 keV and 1275 keV peaks).

### Key Components

**Calibration UI** (`positron/panels/calibration.py`, `positron/ui/histogram_plot.py`)
- Tabbed interface for each channel (A | B | C | D)
- Interactive energy histogram with PyQtGraph per channel
- Adjustable binning (20-2000 bins, default: 1000)
- Logarithmic y-axis by default
- Reuses Home panel acquisition (no duplicate controls)

**Peak Identification** (`positron/calibration/energy.py`)
- Two selectable regions using `LinearRegionItem` (green: 511 keV, blue: 1275 keV)
- **Weighted mean peak finding**: Center-of-mass calculation with 100 bins within region
- Fast, robust, no external dependencies

**Calibration Calculation** (`positron/calibration/energy.py`)
- Two-point linear calibration: `E_keV = gain × E_raw + offset`
- Validation checks: minimum events (100+), peak separation (>10%), reasonable gain, peak ratio (1.5-4.0)
- Independent per-channel calibration

**Calibration Persistence** (`positron/config.py`)
- `ChannelCalibration` dataclass: gain, offset, calibrated flag, date, peak values
- JSON serialization in `ScopeConfig`
- Automatic load on startup, save on apply

### Calibration Workflow

1. **Configure Trigger** (Home panel): Set A OR B OR C OR D logic
2. **Acquire Data** (Home panel): Collect 1000+ events with Na-22 source
3. **Calibrate** (Calibration panel):
   - Click "Update All Histograms"
   - For each channel: drag regions over peaks → Find Peaks → Calculate → Apply
   - All 4 channels calibrated from single acquisition

---

## Phase 5: Analysis Panels ✅

**Goal**: Create analysis panels for visualizing acquired event data.

### Completed Components

**Helper Utilities** (`positron/panels/analysis/utils.py`)
- Data extraction and filtering functions
- `extract_calibrated_energies()` - Extract calibrated energies for a channel
- `filter_events_by_energy()` - Filter events by energy window
- `calculate_timing_differences()` - Calculate timing differences with energy filtering
- `get_channel_info()` - Get channel status and calibration information
- Centralized channel color definitions

**Energy Display Panel** (`positron/panels/analysis/energy_display.py`)
- Multi-channel energy histogram with color-coded overlay (Red=A, Green=B, Blue=C, Orange=D)
- Individual channel enable/disable checkboxes
- Only shows calibrated energy in keV (uncalibrated channels disabled)
- Logarithmic/linear Y-axis toggle (default: logarithmic)
- Auto-update every 2 seconds when panel is active
- Binning options:
  - Automatic: 1000 bins with auto-ranging
  - Manual: User-defined min/max energy (keV) and number of bins (20-2000)
- Live event count per channel

**Timing Display Panel** (`positron/panels/analysis/timing_display.py`)
- Single shared plot showing up to 4 timing difference histograms
- Color-coded curves: Blue (Slot 1), Orange (Slot 2), Green (Slot 3), Red (Slot 4)
- User-selectable channel pairs via dropdown (A, B, C, D)
- Shows time difference: (Channel 1 time - Channel 2 time) in nanoseconds
- Energy filtering for each channel (min/max keV)
- Only includes events where both channels have valid pulses within energy windows
- Validates channel calibration before plotting
- Auto-update every 2 seconds when panel is active
- Binning options:
  - Automatic: 1000 bins with auto-ranging
  - Manual: User-defined time range (ns) and number of bins (20-2000)
- Optional logarithmic Y-axis
- Live event count per slot

**Integration**
- Both panels added as new tabs in main window
- Proper package structure and exports
- Thread-safe access to EventStorage
- No performance impact on acquisition

### Design Decisions

**Data Access**: Both panels read directly from shared `EventStorage` using thread-safe methods. No data duplication.

**Auto-Update**: Uses Qt `QTimer` with 2-second intervals. Starts on `showEvent()`, stops on `hideEvent()` to save resources.

**Calibration Dependency**: Energy Display requires calibrated channels. Timing Display requires calibrated channels for energy filtering.

**UI Consistency**: Channel colors match waveform display. Histogram binning controls consistent across both panels.

### Future Enhancements

- Additional analysis panels as needed (coincidence rate, 2D histograms, etc.)
- Data export functionality (CSV, ROOT format)
- Region-of-interest (ROI) selection and statistics
- Peak fitting capabilities
- Advanced coincidence analysis tools

---

## Phase 6: Polish & Packaging ⏳

**Goal**: Prepare for distribution and student use.

### Planned Components

- Comprehensive error handling and robustness
- UI polish (consistent styling, tooltips, responsive layout)
- PyInstaller packaging for standalone executable
- User documentation and troubleshooting guide

---

## Architecture Decisions

### Core Design

- **Threading**: QThread for acquisition, synchronous processing in acquisition thread, UI in main thread
- **Data Flow**: Acquisition → Pulse Analysis → Event Storage → UI/Analysis
- **Storage**: In-memory only (1M events), future CSV export
- **Configuration**: Fixed optimal hardware settings (100mV, 4ch, DC, max rate), user-configurable trigger logic
- **Sample Timing**: Time-based windows (1µs pre, 2µs post) with automatic sample count calculation

### Key Algorithms

- **CFD Timing**: 50% constant fraction with linear interpolation for sub-sample resolution
- **Energy**: Baseline-corrected integration (inverted for negative pulses)
- **Baseline**: Mean of pre-trigger samples
- **Calibration**: Two-point linear fit (Na-22: 511 & 1275 keV)
- **Peak Finding**: Weighted mean (center-of-mass) within user-selected regions

### Performance Targets

- Support up to 10,000 events/second
- Waveform display at 3 Hz
- Responsive UI during high-rate acquisition

---

## File Structure

```
Positron/
├── README.md
├── DEVELOPMENT_PLAN.md
├── PHASE5_SUMMARY.md          # Phase 5 implementation details
├── requirements.txt
├── main.py                    # Application entry point
├── positron/
│   ├── __init__.py
│   ├── app.py                 # Application state manager
│   ├── config.py              # Configuration management
│   ├── scope/
│   │   ├── __init__.py
│   │   ├── connection.py      # Scope discovery and connection
│   │   ├── configuration.py   # Hardware configuration
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
│   │   ├── home.py            # Home panel
│   │   ├── calibration.py     # Calibration panel
│   │   └── analysis/          # Analysis panels (Phase 5)
│   │       ├── __init__.py
│   │       ├── utils.py       # Helper utilities
│   │       ├── energy_display.py  # Energy histogram panel
│   │       └── timing_display.py  # Timing difference panel
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py     # Main window with tabs
│       ├── waveform_plot.py   # Waveform display widget
│       ├── histogram_plot.py  # Histogram display widget
│       ├── trigger_dialog.py  # Trigger configuration dialog
│       └── widgets/           # Reusable UI components
└── tests/
    └── test_pulse_analysis.py
```

---

## Testing Status

- **Phase 1-2**: Tested with PicoScope 3406D MSO (PS3000a)
- **Phase 3**: Unit tests passing with synthetic pulses
- **Phase 4**: Hardware tested with Na-22 source calibration
- **Phase 5**: Code compiles cleanly, imports verified, ready for hardware testing with live acquisition
- **PS6000a**: Framework in place, needs implementation and hardware testing
