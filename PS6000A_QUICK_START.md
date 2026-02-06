# PS6000a Quick Start Guide

## Prerequisites

1. **Hardware:**
   - PS6000a series oscilloscope connected via USB
   - USB 3.0 port recommended for best performance

2. **Software:**
   - PicoScope drivers installed
   - Python 3.9+ with required packages (see `requirements.txt`)

## Quick Test

Run the test script to verify PS6000a integration:

```bash
python test_ps6000a.py
```

**Expected Output:**
```
PS6000a Integration Test
============================================================
This script tests the PS6000a implementation.
Make sure a PS6000a series scope is connected.

============================================================
TEST 1: Connection and Device Info
============================================================
✓ Connected to scope
  Series: 6000a
  Variant: [Your Model]
  Serial: [Your Serial]
  Max ADC: 512

============================================================
TEST 2: Scope Configuration (50Ω, 10-bit, 100mV)
============================================================
✓ Configuration applied successfully

Configuration Details:
  Resolution: 10-bit (enum value: 1)
  Input Impedance: 50Ω
  Voltage Range: 100 mV (code: 5)
  Sample Rate: [X.XX] GS/s ([XXX.X] MS/s)
  Sample Interval: [X.XXX] ns
  Timebase Index: [X]
  Total Samples: [XXXX]
  Pre-trigger Samples: [XXXX]
  Post-trigger Samples: [XXXX]
  Capture Window: 3.00 µs

============================================================
TEST 3: Trigger Configuration
============================================================
✓ Trigger configured successfully

Trigger Details:
  Number of Conditions: 1
  Conditions:
    - Condition 1: ChA
  Threshold: -5.0 mV
  Direction: Falling
  Auto-trigger: 60000 ms

  Testing OR logic (A OR B OR C OR D)...
  ✓ OR logic configured: 4 conditions

============================================================
TEST SUMMARY
============================================================
✓ All tests passed!

The PS6000a integration is working correctly.
You can now run the full application with: python main.py
```

## Running the Application

Start the full Positron application:

```bash
python main.py
```

The application will:
1. Auto-detect your PS6000a scope
2. Apply configuration (50Ω impedance, 10-bit resolution, 100mV range)
3. Configure default trigger (Channel A, -5mV falling edge)
4. Launch the main window

## Key Differences from PS3000a

| Feature | PS3000a | PS6000a |
|---------|---------|---------|
| **Sample Rate** | 125-250 MS/s | 1.25-2.5 GS/s |
| **Resolution** | 8-bit | 10-bit |
| **Input Impedance** | 1MΩ only | **50Ω** |
| **Batch Size** | 10 events | **20 events** |
| **Voltage Resolution** | ~0.8 mV steps | **~0.2 mV steps** |

## Configuration Details

### Hardware Settings (Fixed)
- **Voltage Range:** 100 mV on all channels
- **Input Impedance:** 50Ω (PS6000a-specific)
- **Resolution:** 10-bit
- **Coupling:** DC
- **Bandwidth:** Full
- **Capture Window:** 3 µs (1 µs pre-trigger, 2 µs post-trigger)

### Configurable Settings
- **Trigger Conditions:** Up to 4 conditions with OR logic
- **Trigger Channels:** Any combination of A, B, C, D
- **Auto-trigger:** Enable/disable with 60s timeout

## Basic Workflow

### 1. Start Acquisition
1. Open Positron application
2. Go to **Home** panel
3. Click **Configure Trigger** to set trigger logic
4. Click **Start** to begin acquisition
5. Watch waveforms update in real-time
6. Monitor event count (increments by 20 per batch)

### 2. Energy Calibration
1. Place Na-22 source near detectors
2. Acquire 1000+ events
3. Go to **Calibration** panel
4. Click **Update All Histograms**
5. For each channel:
   - Drag green region over 511 keV peak
   - Drag blue region over 1275 keV peak
   - Click **Find Peaks**
   - Click **Calculate Calibration**
   - Click **Apply**

### 3. Analysis
1. **Energy Display:**
   - View calibrated energy histograms
   - Enable/disable channels
   - Toggle log/linear scale
   - Adjust binning

2. **Timing Display:**
   - Select channel pairs
   - Set energy windows
   - View timing differences
   - Analyze coincidence timing

## Troubleshooting

### "No PicoScope device detected"
- Check USB connection
- Verify drivers are installed
- Close PicoScope software if running
- Try a different USB port (USB 3.0 recommended)

### "Configuration Error"
- Ensure your PS6000a model supports 50Ω impedance
- Check firmware is up to date
- Verify 10-bit resolution is available

### "Timeout waiting for triggers"
- Check signal connections
- Verify trigger threshold (-5 mV) matches signal polarity
- Enable auto-trigger if signals are intermittent
- Check trigger channel configuration

### Slow Performance
- PS6000a captures ~10× more samples per waveform
- This is normal and provides better resolution
- Target rate: >1000 events/second
- Monitor event storage (max 1M events)

## Performance Tips

1. **Batch Processing:** PS6000a processes 20 events per batch (vs 10 for PS3000a)
2. **Memory Usage:** ~1.2 MB per batch (vs ~60 KB for PS3000a)
3. **Sample Rate:** Much faster sampling provides better timing resolution
4. **Resolution:** 10-bit gives 4× better voltage resolution than 8-bit

## Support

For issues or questions:
1. Check `PS6000A_INTEGRATION_SUMMARY.md` for detailed implementation info
2. Review `DEVELOPMENT_PLAN.md` for architecture details
3. Consult PicoScope documentation in `docs/` folder
4. Check linter output: `python -m pylint positron/`

## Next Steps

After successful testing:
1. Run extended acquisition (1000+ events)
2. Perform energy calibration with Na-22
3. Verify timing analysis with coincidence data
4. Compare results with PS3000a (if available)
5. Document any model-specific observations

---

**Status:** ✅ PS6000a integration complete and ready for use!
