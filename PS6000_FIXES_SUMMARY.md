# PS6000 (6402D) Troubleshooting Fixes

## Issues Found and Fixed

### 1. Missing Function Parameters ✅ FIXED
**Problem**: API functions were being called with incorrect number of arguments.

**Fixes**:
- `ps6000SetDataBufferBulk()`: Added missing `downSampleRatioMode` parameter (6th argument)
- `ps6000GetValuesBulk()`: Added missing `downSampleRatio` parameter (5th argument)

**Files Modified**: `positron/scope/acquisition.py`

---

### 2. Incorrect Input Impedance ✅ FIXED
**Problem**: Channels were configured with 1 MΩ impedance instead of 50Ω.

**Fix**: Changed coupling parameter from `1` (PS6000_DC_1M) to `2` (PS6000_DC_50R)

**Files Modified**: `positron/scope/configuration.py`

**Impact**: Signals now properly terminated with 50Ω, preventing reflections and ensuring correct signal levels.

---

### 3. Broken Trigger Configuration ✅ FIXED
**Problem**: Using `ps6000SetSimpleTrigger()` in a loop, where each call replaced the previous trigger setup. Only the last channel would trigger.

**Fix**: Completely rewrote trigger configurator to use advanced trigger API:
- `ps6000SetTriggerChannelProperties()` - Sets threshold/hysteresis for all channels at once
- `ps6000SetTriggerChannelConditions()` - Implements AND/OR logic correctly
- `ps6000SetTriggerChannelDirections()` - Sets falling edge for all channels

**Files Modified**: `positron/scope/trigger.py`

**Impact**: Multi-channel triggering now works correctly with proper AND/OR logic.

---

### 4. Trigger Not Applied on Acquisition Start ✅ FIXED
**Problem**: Trigger configuration was only applied when clicking "Configure Trigger" button, not when starting acquisition.

**Fix**: Added trigger configuration step to `_create_acquisition_engine()` function before creating the acquisition engine.

**Files Modified**: `positron/panels/home.py`

**Impact**: Trigger is now properly configured every time acquisition starts.

---

### 5. Incorrect Max ADC Value ✅ FIXED
**Problem**: Using `max_adc = 32767` (15-bit value) instead of correct 8-bit value.

**Fix**: Changed `max_adc = 32512` (correct value from official PicoSDK examples)

**Files Modified**: `positron/scope/connection.py`

---

### 6. WRONG VOLTAGE RANGE CODE ✅ FIXED
**Problem**: Using voltage_range_code = 7 (PS6000_2V = 2000 mV range) instead of 3 (PS6000_100MV = 100 mV range).

**Symptom**: Voltages scaled 20x too large! Noise appeared as >10 mV steps, causing false triggers.

**Fix**: Changed voltage_range_code from 7 to **3** in all locations:
- `positron/scope/configuration.py` - Channel configuration
- `positron/scope/trigger.py` - Trigger threshold conversion
- `positron/scope/acquisition.py` - ADC-to-voltage conversion

**Impact**: 
- **Before**: ADC 1 → 0.062 mV (20x too large!)
- **After**: ADC 1 → 0.003 mV (correct!)
- **Before**: Your 40 mV pulse → 800 mV (wrong!)
- **After**: Your 40 mV pulse → 40 mV (correct!)
- **Before**: Trigger threshold -5 mV → -100 mV (wrong!)
- **After**: Trigger threshold -5 mV → -5 mV (correct!)

---

## Verification

Run `verify_trigger_hardware.py` to confirm:
- ✅ Trigger is enabled on hardware
- ✅ Threshold: -5 mV (-1625 ADC counts)
- ✅ Direction: Falling edge
- ✅ Channels: A, B, C, D (OR logic)

## Current Configuration

**Hardware Settings**:
- Voltage range: 100 mV on all 4 channels
- Input impedance: 50Ω (DC coupling)
- Sample rate: 1250 MS/s (1.25 GS/s)
- Resolution: 8-bit (32512 max ADC)
- Voltage step: 3.08 µV

**Trigger Settings**:
- Threshold: -5 mV
- Direction: Falling edge (negative pulses)
- Logic: A OR B OR C OR D
- Auto-trigger: OFF (waits for valid trigger)

**Expected Performance**:
- Your 40-50 mV negative pulses should trigger reliably
- No more false triggers on noise
- Proper voltage resolution throughout waveform

---

## Testing

1. Run `python main.py`
2. Click "Start" to begin acquisition
3. Apply your 40-50 mV negative pulses to any channel (A, B, C, or D)
4. Waveforms should appear with correct voltage scaling
5. No more noise triggers!

---

*Fixed: 2026-02-06*
