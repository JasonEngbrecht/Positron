# Changelog

All notable changes to Positron are documented here.

## [Unreleased]

### Fixed
- A few percent of pulses came out with negative (or near-zero) energy.
  Cause: a pulse arriving while the scope refills the pre-trigger buffer
  between segments (trigger disarmed) is captured with its peak in the
  pre-trigger window, because the scope fires on noise as the pulse tail
  recovers through the -5 mV threshold. The mean-of-pre-trigger baseline was
  dragged down and the full-window integral went negative. The analysis now
  takes the baseline from the pre-trigger window minus a 50 ns guard, and
  marks a channel *rejected* (`has_pulse` FALSE, new `rejected` flag) when
  the pre-trigger window is not quiet or the leading edge is not inside the
  captured window. Rejected channels drop out of all histograms and the
  calibration; the CSV export gains an `X_rejected` column per channel
  holding the reason (`pre_trigger`, `no_edge`, `width`).
- PMT dark pulses (single-photoelectron blips, 3-5 ns wide, ~zero area) no
  longer pile up at zero energy in the spectra, where the calibration offset
  made them appear at -15 to -35 keV with a detector-dependent height. A
  pulse is now rejected (`width`) when energy / peak amplitude is below
  30 ns; real scintillation pulses measure 240-280 ns. An event whose
  trigger condition was satisfied only with the help of such a dark pulse is
  discarded entirely (not stored or counted); the per-5 s acquisition log
  line reports how many.
- CFD crossing search now also covers the 50 ns guard interval before the
  trigger, so pulses whose 50% point falls a sample before t = 0 get an
  interpolated time instead of the peak-time fallback; the search is
  vectorized (late pulses no longer cost a per-sample Python loop).

### Added
- Developer diagnostic: `run_debug.bat` (env `POSITRON_DUMP_ANOMALIES=1`)
  writes raw waveforms of rejected / negative-energy events to
  `~/.positron/debug/`; `tools/plot_anomalies.py` plots them.

## [1.3.0] - 2026-09-04

### Fixed
- ADC-to-mV conversion silently corrupted every waveform when running under
  NumPy >= 2: picosdk's `adc2mV` multiplies int16 samples in a Python loop
  and the product now wraps (a -5 mV pulse read as -0.97 mV). Replaced with
  a vectorized float64 conversion (`adc_to_mv`) plus regression tests. The
  1.2.0 executable was unaffected only because it bundled NumPy 1.x.
- `build.bat` removes PyInstaller's intermediate `build\positron\Positron.exe`
  stub (launching it fails with "Failed to load Python DLL") and prefers the
  `py` launcher so the user manual PDF is regenerated.

### Changed
- Acquisition rate on a PS6402D with the same source: ~600 events/s
  (1.2.0 from source; ~60 events/s for the 1.2.0 executable) -> ~2450 events/s
  - Poll loop uses `time.sleep` (0.6 ms actual) instead of `QThread.msleep(1)`,
    which rounds up to the 15.6 ms Windows scheduler tick; the post-batch
    sleep is removed
  - The scope is re-armed immediately after each download so it captures the
    next batch while the current one is processed

### Added
- Per-batch acquisition timing summary (wait / download / process / other)
  logged every 5 s; INFO console logging when running from source, including
  the reason a scope connection attempt failed (e.g. device busy)

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
