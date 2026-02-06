# Quick Start Guide - PS6000 (6402D)

## ✅ Migration Complete!

Your PicoScope 6402D is now fully integrated into Positron using the PS6000 (original) API.

## What Changed

**Before:** Code was written for PS6000a API (newer API with 50Ω option, 10-bit resolution)
**Now:** Code uses PS6000 API (original API that your 6402D actually uses)

## Hardware Configuration

Your 6402D is now configured with:
- **Input Impedance:** 1 MΩ (fixed)
- **Resolution:** 8-bit (fixed)
- **Sample Rate:** 1.25 GS/s (1250 MS/s)
- **Voltage Range:** 100 mV (all 4 channels)
- **Channels:** A, B, C, D (all enabled)
- **Trigger:** -5 mV falling edge with 60s auto-trigger

## Quick Tests

### 1. Run Complete Test
```bash
python test_ps6000_complete.py
```
This tests connection, configuration, and trigger setup. Should show:
- ✓ Connected to 6402D
- ✓ Configuration applied (1250 MS/s)
- ✓ Trigger configured

### 2. Run Quick Test
```bash
python test_ps6000_quick.py
```
Faster test - just connection and configuration.

## Running the Application

### Start Positron
```bash
python main.py
```

The application will:
1. Automatically detect your 6402D
2. Apply optimal configuration for pulse detection
3. Set up triggers
4. Start data acquisition when you press "Start"

## Sample Rate Details

Your 6402D provides excellent time resolution:
- **Sample Rate:** 1250 MS/s (1.25 GS/s)
- **Sample Interval:** 0.80 ns
- **Capture Window:** 3 µs (3749 samples)
  - Pre-trigger: 1 µs (1249 samples)
  - Post-trigger: 2 µs (2500 samples)

This is perfect for the fast pulse detection required by Positron!

## Troubleshooting

### If connection fails:
1. Unplug and replug the 6402D
2. Make sure PicoScope software is closed
3. Wait 5 seconds
4. Run the test again

### If you see errors:
- Check that picosdk is installed: `pip install picosdk`
- Check that PicoScope drivers are installed
- Make sure the device isn't in use by another program

## Technical Details

See `PS6000_MIGRATION_SUMMARY.md` for complete technical details about:
- API differences between PS6000a and PS6000
- Implementation details
- Code changes made
- Testing results

## Next Steps

You're all set! The 6402D is ready for data acquisition. Simply:
1. Connect your experiment to channels A, B, C, D
2. Run `python main.py`
3. Configure your trigger conditions in the UI
4. Click "Start" to begin acquisition

The scope will automatically capture triggered waveforms, analyze them for pulse timing and energy, and save events to disk.
