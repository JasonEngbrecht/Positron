# Changelog

All notable changes to Positron are documented here.

## [1.2.0] - 2026-08-07

### Changed
- Scope-layer refactor: series-specific SDK calls consolidated into a new
  driver adapter (`positron/scope/driver.py`); the configurator, trigger
  configurator, and acquisition engine are now single shared classes
  (~1,100 lines of duplicated code removed). No intended behavior changes.
- PS3000a acquisition now uses the configurator-validated timebase instead
  of a local heuristic
- Acquisition thread teardown now waits for the old thread to exit before
  creating a new engine (fixes a latent crash risk on rapid pause/resume)
- Failed scope-connection attempts are logged instead of silently swallowed
- Added `run.bat` for quick launches from source
- Normalized line endings via `.gitattributes`; removed compiled `.pyc` files from version control
- Added `CLAUDE.md` developer context file
- Documentation corrections (roadmap, EventStorage capacity, stale comments)

## [1.1] - 2026-02-06

### Added
- PicoScope 6000 series support (`ps6000` driver): connection, configuration,
  triggering, and rapid-block acquisition alongside the existing 3000a support

### Changed
- Documentation cleanup
- New distribution build

## [1.0] - 2026-02-04

Initial release.

### Added
- PicoScope 3000a series support: auto-detection, fixed hardware profile
  (100 mV, 4 channels, 3 µs capture window), advanced trigger logic (AND/OR)
- Rapid-block acquisition engine (QThread) with live 4-channel waveform display
- Pulse analysis: baseline correction, CFD timing (50%), energy integration
- Thread-safe in-memory event storage (up to 1 million events)
- Energy calibration panel with interactive Na-22 two-point calibration
- Energy Display and Timing Display analysis panels with log-scale histograms
- CSV export from Home and analysis panels
- In-app help system (F1) for each panel
- PyInstaller standalone distribution with bundled PDF user manual
