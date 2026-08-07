# Changelog

All notable changes to Positron are documented here.

## [Unreleased]

### Changed
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
