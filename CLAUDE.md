# CLAUDE.md

Positron is a Windows desktop data-acquisition and analysis app for positron
annihilation lifetime spectroscopy (PALS) teaching labs. It drives a PicoScope
oscilloscope (3000a or 6000 series), captures 4-channel triggered pulse
waveforms, and extracts per-pulse timing (CFD) and energy with live histograms.

## Commands

- **Run**: `run.bat` or `py main.py` — requires a PicoScope attached via USB
- **Test**: `py -m pytest tests/` — pure pulse-math tests, no hardware needed
- **Build**: `build.bat` — PyInstaller one-folder build to `dist\Positron\`
- Python is invoked via the `py` launcher (Python 3.12). Plain `python` is NOT
  on PATH on the dev machine (Microsoft Store stub). No venv — global install.

## Architecture (details in ARCHITECTURE.md)

- `main.py` — startup: detect scope (retry dialog), apply config + trigger, open MainWindow
- `positron/app.py` — app-wide state manager (config, connection, event storage accessor)
- `positron/config.py` — dataclass config persisted to `~/.positron/config.json`
- `positron/scope/` — hardware layer: `connection.py` (auto-detect, tries PS6000
  first then PS3000a), `configuration.py` (channels + timebase), `trigger.py`
  (advanced trigger logic), `acquisition.py` (QThread rapid-block engine)
- `positron/processing/` — `pulse.py` (baseline/CFD/energy math), `events.py`
  (QMutex-protected in-memory EventStorage)
- `positron/calibration/energy.py` — two-point Na-22 calibration (511/1275 keV)
- `positron/panels/` — tab contents: `home.py` (acquisition control + live
  waveforms + CSV export), `calibration.py`, `analysis/` (energy + timing histograms)
- `positron/ui/` — MainWindow, plot widgets, trigger dialog, in-app help (F1)

**Threading**: one QThread acquisition engine talks to the scope, converts
ADC→mV, analyzes pulses synchronously, appends to EventStorage; communicates
with the UI via Qt signals only. Panels poll EventStorage on QTimers
(waveforms 3 Hz, analysis 0.5 Hz). Never block the main thread.

## Gotchas

- `positron.spec` lists every `positron.*` module by hand in `hiddenimports` —
  **adding or renaming a module requires editing positron.spec** or the frozen
  build will miss it.
- Hardware behavior differs deliberately between series (e.g. PS6000 uses
  50 Ω DC coupling, PS3000a 1 MΩ; batch sizes 10 vs 20). Don't "unify" values
  across series without checking the physics/API intent.
- Scope-layer changes can only be fully verified with real hardware. The user
  has both a 3000-series and 6000-series scope — ask them to run a checkpoint
  (acquire ~30 s, check waveforms + histograms on both scopes) after such changes.
- `docs/README.md` indexes the PicoScope programmer's guides (PDFs) and vendored
  picosdk wrapper source in `docs/picosdk-python-wrappers-master/` — the
  authoritative reference for SDK struct layouts and enum values.

## Conventions

- User prefers small incremental steps: each change should leave the app
  runnable, be verified (tests + hardware checkpoint when relevant), and be
  committed on its own.
