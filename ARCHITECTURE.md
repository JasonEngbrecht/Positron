# Positron Architecture Documentation

**Technical reference for developers and contributors**

This document explains the architectural decisions, design patterns, and key algorithms used in Positron. For user-facing documentation, see the in-app Help menu (F1) or `DISTRIBUTION_README.md`.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Threading Model](#threading-model)
3. [Data Flow](#data-flow)
4. [Key Algorithms](#key-algorithms)
5. [Hardware Abstraction](#hardware-abstraction)
6. [File Organization](#file-organization)
7. [Configuration System](#configuration-system)
8. [Design Rationale](#design-rationale)

---

## Architecture Overview

Positron uses a **multi-threaded event-driven architecture** with Qt as the foundation:

- **Main Thread**: UI rendering and user interaction (Qt event loop)
- **Acquisition Thread**: Hardware communication and data processing (QThread)
- **Shared Storage**: Thread-safe event storage with mutex protection

### Core Principles

1. **Separation of Concerns**: Hardware abstraction (scope), processing logic (pulse analysis), UI (panels)
2. **Protocol-Based Design**: Common interfaces for different PicoScope series (3000a vs 6000)
3. **Signal-Slot Communication**: Qt signals for thread-safe inter-component messaging
4. **Synchronous Processing**: Events processed immediately after acquisition (no queue backlog)

---

## Threading Model

### Main Thread (Qt Event Loop)
**Responsibilities:**
- UI rendering and updates (PyQtGraph plots, controls)
- User input handling (button clicks, configuration dialogs)
- Timer-based updates (waveform display at 3 Hz, analysis panels at 0.5 Hz)

**Key Point**: Never block the main thread with I/O or heavy computation

### Acquisition Thread (QThread)
**Responsibilities:**
- PicoScope API calls (`ps3000aRunBlock`, `ps6000RunBlock`, etc.)
- Batch waveform download (10-20 captures per batch)
- Pulse analysis (CFD timing, energy integration) - synchronous
- Event storage (thread-safe append to shared EventStorage)

**Why Synchronous Processing?** 
- Processing time (~32 µs/event) is much faster than acquisition time
- Eliminates queue management complexity
- Prevents memory buildup from unprocessed waveforms
- Target rate (10,000 events/sec) easily achieved

### Thread Communication
Uses Qt **signals** exclusively (thread-safe):
```
Acquisition Thread                Main Thread
─────────────────────            ───────────────
emit waveform_ready()     ─────> Update live plot
emit batch_complete()     ─────> Update statistics
emit acquisition_error()  ─────> Show error dialog
emit acquisition_finished() ───> Enable buttons
```

No shared mutable state except `EventStorage` (protected by QMutex).

---

## Data Flow

```
Hardware → Acquisition → Processing → Storage → Analysis/Display
```

### 1. Hardware Capture (Acquisition Thread)
- PicoScope captures batch of N waveforms (rapid block mode)
- N = 10 for PS3000a, N = 20 for PS6000
- Returns raw ADC values (16-bit integers)

### 2. Conversion (Acquisition Thread)
```python
voltage_mv = (adc_value / max_adc) * voltage_range_mv
```
- Converts ADC counts to millivolts for each sample
- Applied to all 4 channels

### 3. Pulse Analysis (Acquisition Thread)
For each channel in each waveform:
- **Baseline**: Mean of 125 pre-trigger samples
- **CFD Timing**: Zero-crossing of 50% threshold (see Algorithms)
- **Energy**: Integration of baseline-corrected waveform (mV·ns)
- **Pulse Detection**: Minimum 5 mV amplitude

### 4. Event Storage (Acquisition Thread)
```python
event = EventData(
    event_id=counter,
    timestamp=time.time(),
    channels={
        'A': ChannelPulse(timing_ns, energy, peak_mv, has_pulse),
        'B': ChannelPulse(...),
        'C': ChannelPulse(...),
        'D': ChannelPulse(...)
    }
)
get_event_storage().add_event(event)  # Thread-safe
```

### 5. UI Updates (Main Thread)
- **Waveform Display**: 3 Hz via QTimer, reads last waveform from signal
- **Statistics**: Updated on each `batch_complete` signal
- **Analysis Panels**: 0.5 Hz via QTimer, reads from EventStorage

**Key Design Choice**: Analysis panels read directly from storage (no copies). Memory efficient but requires thread-safe access.

---

## Key Algorithms

### Constant Fraction Discrimination (CFD)

**Purpose**: Sub-nanosecond timing resolution, eliminates amplitude walk

**Method**: Digital CFD at 50% threshold
1. Find peak amplitude after trigger: `peak_mv = min(waveform[trigger:])`
2. Calculate threshold: `threshold = baseline + 0.5 * (peak - baseline)`
3. Find zero-crossing: Linear interpolation between samples
4. Return time in nanoseconds relative to trigger

**Why 50%?**
- Industry standard for timing measurements
- Balances noise immunity (higher %) vs time walk compensation (lower %)
- Tested with typical PMT pulse shapes (1-2 ns rise time)

**Code**: `positron/processing/pulse.py::calculate_cfd_timing()`

### Energy Integration

**Purpose**: Pulse energy proportional to deposited particle energy

**Method**: Baseline-corrected trapezoidal integration
```python
energy = -sum(waveform - baseline) * sample_interval_ns
```
- Negative sign: Pulses go negative (falling edge trigger)
- Units: mV·ns (converted to keV via calibration)
- Trapezoidal rule: `np.trapz()` for numerical integration

**Design Choice**: Full waveform integration (not gated)
- Simple and robust
- Pileup rejection not needed at target rates (<10 kHz)
- Future: Add integration window if needed

**Code**: `positron/processing/pulse.py::calculate_energy()`

### Energy Calibration

**Purpose**: Convert raw energy (mV·ns) to physical units (keV)

**Method**: Two-point linear calibration
```python
E_keV = gain * E_raw + offset
```
Given two known peaks (Na-22: 511 keV, 1275 keV):
```python
gain = (E2_keV - E1_keV) / (E2_raw - E1_raw)
offset = E1_keV - gain * E1_raw
```

**Validation**:
- Minimum 100 events
- Peak separation >10%
- Energy ratio 1.5-4.0 (sanity check for Na-22)
- Positive gain

**Peak Finding**: Weighted mean (center-of-mass) within user-selected region
- Fast, no external dependencies
- Works well for symmetric peaks
- User adjusts regions if peaks are asymmetric

**Code**: `positron/calibration/energy.py`

---

## Hardware Abstraction

### Driver-Adapter Design

Different PicoScope series have different APIs. All series-specific SDK calls
are concentrated in one place: `positron/scope/driver.py`. Each driver wraps
an open scope handle plus its picosdk module and exposes a unified interface
(`ScopeDriver` Protocol):

```python
class ScopeDriver(Protocol):
    series: str
    voltage_range_code_100mv: int
    default_batch_size: int

    def set_channel(self, channel_idx) -> None: ...          # coupling/bandwidth differences live here
    def get_timebase2(self, timebase) -> Optional[Tuple]: ...
    def run_block(self, pre, post, timebase) -> None: ...
    def register_buffer(self, ...) -> None: ...              # SetDataBuffers vs SetDataBufferBulk
    def set_trigger_properties(self, ...) -> None: ...       # different struct field names per series
    # ... plus is_ready, get_values_bulk, stop, close, etc.
```

The configurator (`configuration.py`), trigger configurator (`trigger.py`),
and acquisition engine (`acquisition.py`) are each a SINGLE class consuming a
driver — the shared logic (timebase search, capture loop, pulse processing)
exists exactly once.

**Factory Pattern**: `create_driver(scope_info)` returns `PS3000aDriver` or
`PS6000Driver`; the `create_configurator` / `create_trigger_configurator` /
`create_acquisition_engine` factories build the right driver internally.

### PicoScope 3000a vs 6000 Series

| Feature | PS3000a | PS6000 |
|---------|---------|--------|
| **Input Coupling** | DC, 1 MΩ (external 50 Ω terminators needed) | DC, 50 Ω (set in software) |
| **Resolution** | 8-bit fixed | 8-bit fixed |
| **Sample Rate** | 250 MS/s (4ch) | 1.25 GS/s (4ch) |
| **Batch Size** | 10 captures | 20 captures |
| **Max ADC** | Queried via `MaximumValue` | Fixed 32512 (no API call) |
| **Buffer Registration** | max/min pair per (channel, segment) | single buffer per (channel, waveform) |
| **Trigger Structs** | `thresholdUpperHysteresis` fields, ConditionsV2 with `digital` | `hysteresisUpper` fields, plain Conditions |

**Deliberately NOT unified** (each driver owns its own structs, enums, and
magic numbers): trigger struct population, channel coupling/bandwidth,
buffer registration, and connection/power handling. The "NONE" trigger
direction value even differs between the series' enums. Verify struct
layouts against `docs/picosdk-python-wrappers-master/picosdk/` before
touching driver code — ctypes structs silently accept typo'd field names.

**Code**:
- `positron/scope/driver.py` - ScopeDriver Protocol, PS3000aDriver, PS6000Driver
- `positron/scope/configuration.py` - ScopeConfigurator (shared logic)
- `positron/scope/trigger.py` - TriggerConfigurator (shared logic)
- `positron/scope/acquisition.py` - AcquisitionEngine (shared logic)

---

## File Organization

```
positron/
├── app.py              # Application state manager (singleton)
├── config.py           # Configuration persistence (JSON)
│
├── scope/              # Hardware abstraction layer
│   ├── connection.py   # Auto-detection, open/close
│   ├── driver.py       # Series-specific SDK adapters (PS3000a / PS6000)
│   ├── configuration.py # Channel setup, sample rate (series-agnostic)
│   ├── trigger.py      # Trigger logic configuration (series-agnostic)
│   └── acquisition.py  # Rapid block capture engine (series-agnostic)
│
├── processing/         # Signal processing
│   ├── pulse.py        # CFD, energy, baseline algorithms
│   └── events.py       # Thread-safe event storage
│
├── calibration/        # Energy calibration
│   └── energy.py       # Two-point calibration, peak finding
│
├── panels/             # UI panels (tabs)
│   ├── home.py         # Acquisition control + live waveforms
│   ├── calibration.py  # Energy calibration workflow
│   └── analysis/
│       ├── utils.py            # Shared analysis functions
│       ├── energy_display.py   # Energy histograms
│       └── timing_display.py   # Timing differences
│
└── ui/                 # Reusable UI components
    ├── main_window.py      # Main window + menu bar
    ├── waveform_plot.py    # PyQtGraph 4-channel display
    ├── histogram_plot.py   # PyQtGraph histogram widget
    ├── trigger_dialog.py   # Trigger configuration dialog
    └── help_dialogs.py     # In-app help system
```

**Design Principle**: Each module has a single responsibility. Hardware-specific code isolated in `scope/` implementations.

---

## Configuration System

### User Configuration (Persistent)
**File**: `~/.positron/config.json` (Windows: `C:\Users\{user}\.positron\config.json`)

**Contents**:
```json
{
  "last_scope_series": "3000a",
  "trigger_conditions": [...],
  "calibration_a": {"gain": 0.0026, "offset": 10.0, ...},
  "calibration_b": {...},
  "calibration_c": {...},
  "calibration_d": {...}
}
```

**Managed By**: `positron.config.ScopeConfig` (dataclass with JSON serialization)

### Hardware Configuration (Fixed)
**Rationale**: Optimize for PALS experiments, eliminate configuration complexity

**Fixed Settings**:
- Voltage range: 100 mV (optimized for PMT pulses)
- Coupling: DC (standard for PMT signals)
- Capture window: 3 µs (1 µs pre, 2 µs post) - sufficient for typical pulse widths
- Trigger: -5 mV threshold, falling edge (negative pulses)

**User-Configurable**:
- Trigger logic (OR/AND combinations of channels)
- Auto-stop conditions (time/event limits)
- Calibration parameters (per-channel)

**Why Fixed?** Testing showed these settings work for 95% of PALS setups. Advanced users can modify code if needed.

---

## Design Rationale

### Why Python?
- **Pros**: Rapid development, rich scientific ecosystem (NumPy, Qt), picosdk wrappers available
- **Cons**: Lower performance than C++
- **Verdict**: Performance sufficient (>10k events/sec achieved), development speed prioritized

### Why Qt (PySide6)?
- **Alternatives**: Tkinter (limited), wxPython (outdated), web-based (complexity)
- **Chosen**: Industry-standard, excellent PyQtGraph integration, native look, good threading support

### Why PyQtGraph?
- **Alternatives**: Matplotlib (too slow for real-time), Plotly (web-based)
- **Chosen**: OpenGL-accelerated, designed for real-time data, native Qt integration

### Why In-Memory Storage?
- **Capacity**: 1 million events (~750 MB RAM)
- **Rationale**: Typical runs are 10k-100k events, fast access for analysis panels
- **Future**: Add CSV/ROOT export for archival and external analysis
- **Tradeoff**: Lose data on crash (acceptable for lab use, acquire new data quickly)

### Why Synchronous Processing?
- **Alternative**: Queue-based pipeline (acquisition → queue → processing thread)
- **Chosen**: Simpler, no queue management, processing faster than acquisition
- **Tradeoff**: If processing becomes bottleneck, queue-based can be added

### Why Driver-Adapter Hardware Abstraction?
- **Alternatives**: Parallel per-series classes for configurator/trigger/engine
  (the original design — drifted apart in practice); base-class hierarchies
  (awkward combined with QThread inheritance)
- **Chosen**: One thin driver per series holding every SDK difference; a single
  shared implementation of each higher-level component consumes it
- **Payoff**: The capture loop, timebase search, and trigger orchestration are
  written once — a fix applies to all series; adding a series means writing
  one driver class

### Why JSON for Configuration?
- **Alternatives**: INI (no nested structures), YAML (external dependency), pickle (not human-readable)
- **Chosen**: Built-in, human-readable, sufficient for simple config needs

---

## Performance Considerations

### Target Performance
- **Event Rate**: >10,000 events/second
- **Waveform Display**: 3 Hz update (responsive but not overwhelming)
- **Analysis Updates**: 0.5 Hz (balance between responsiveness and CPU)
- **Latency**: <100 ms from trigger to display

### Bottlenecks
1. **USB Transfer**: ~10-20 ms per batch (hardware limited)
2. **Pulse Processing**: ~32 µs per event (fast enough)
3. **Plot Rendering**: ~50 ms for histogram (PyQtGraph is efficient)

**Design for Performance**:
- Batch capture (10-20 waveforms at once) reduces USB overhead
- NumPy vectorized operations for pulse analysis
- Plot updates throttled by QTimer (don't overwhelm rendering)
- EventStorage uses Python list (fast append, adequate for 1M events)

### Memory Usage
- **Per Event**: ~750 bytes (4 channels × ~180 bytes + overhead)
- **1M Events**: ~750 MB
- **Total Application**: ~1 GB typical (includes Qt, NumPy, plots)

---

## Testing Strategy

### Unit Tests
- **Location**: `tests/test_pulse_analysis.py`
- **Coverage**: Pulse analysis algorithms (CFD, energy, baseline)
- **Approach**: Synthetic waveforms with known properties

### Integration Testing
- **Manual**: Test scripts (now deleted, functionality in main app)
- **Hardware**: Requires physical PicoScope
- **Approach**: Acquire real data, verify processing pipeline

### Future: Automated Testing
- Mock PicoScope API for CI/CD
- Property-based testing for pulse algorithms (hypothesis library)
- UI testing (pytest-qt)

---

## Extension Points

### Adding New Analysis Panels
1. Create new panel class inheriting `QWidget`
2. Implement `showEvent()` / `hideEvent()` for auto-update timer
3. Read from `get_event_storage()` with mutex lock
4. Add to `MainWindow._create_panels()` as new tab

**Example**: Coincidence rate monitor, 2D energy-timing plots

### Adding New PicoScope Series
1. Add a connect path in `positron/scope/connection.py` (open unit, read
   variant/serial/max ADC)
2. Implement a new driver class in `positron/scope/driver.py` following the
   `ScopeDriver` protocol (verify struct layouts against
   `docs/picosdk-python-wrappers-master/picosdk/`)
3. Add the series case to `create_driver()`
4. Add the new module names to `positron.spec` hiddenimports if any files
   are added
5. Test with physical hardware

The configurator, trigger configurator, and acquisition engine need no
changes — they only talk to the driver.

**Example**: PS5000 series, PS4000 series, PS6000a (newer API)

### Adding Data Export
- Implement in `positron/processing/events.py`
- Add menu item in `MainWindow`
- Export formats: CSV (pandas), ROOT (uproot), HDF5 (h5py)

---

## Troubleshooting Guide (for Developers)

### Adding Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Message here")
```

### Common Issues
- **Scope not detected**: Check series detection order in `connection.py`
- **Acquisition timeout**: Verify trigger conditions actually fire
- **Memory leak**: Check event storage isn't growing unbounded
- **UI freeze**: Ensure no blocking operations in main thread

### Performance Profiling
```python
import cProfile
cProfile.run('your_function()', 'output.prof')
# Analyze with snakeviz: pip install snakeviz && snakeviz output.prof
```

---

## References

- **PicoScope API**: See `docs/picoscope-*-api-programmers-guide.pdf`
- **Qt Documentation**: https://doc.qt.io/qtforpython/
- **PyQtGraph**: https://pyqtgraph.readthedocs.io/
- **CFD Algorithm**: Knoll, "Radiation Detection and Measurement", 4th ed.

---

**Last Updated**: August 2026  
**Version**: 1.2.0  
**Contributors**: See commit history
