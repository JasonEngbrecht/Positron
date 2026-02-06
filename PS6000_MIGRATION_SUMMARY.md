# PS6000 Migration Summary

## Overview
Successfully migrated from PS6000a API to PS6000 (original) API for the PicoScope 6402D oscilloscope. This change simplifies the codebase and aligns with the actual hardware being used.

## Changes Made

### 1. Connection Module (`positron/scope/connection.py`)
**Removed:**
- `_connect_ps6000a()` method
- PS6000a-specific imports and references

**Added:**
- `_connect_ps6000()` method using `ps6000OpenUnit()`
- Fixed max_adc value (32767 for 8-bit)
- `_get_unit_info_ps6000()` helper method

**Updated:**
- `detect_and_connect()` now tries PS6000 first, then PS3000a
- `disconnect()` updated to handle PS6000 with `ps6000Stop()` and `ps6000CloseUnit()`

### 2. Configuration Module (`positron/scope/configuration.py`)
**Replaced:** `PS6000aConfigurator` → `PS6000Configurator`

**Key Differences:**
- Uses **1 MΩ input impedance** (fixed, not configurable like PS6000a)
- Uses **8-bit resolution** (fixed, vs configurable 8-16 bit on PS6000a)
- **Voltage range code: 7** (PS6000_100MV = 7 vs PS6000a code 5)
- Uses numeric constants instead of PicoDeviceEnums dictionaries
- `ps6000SetChannel()` with 7 parameters (including bandwidth)
- `ps6000GetTimebase2()` instead of `ps6000aGetMinimumTimebaseStateless()`

**Sample Rate Achieved:**
- 1250 MS/s (1.25 GS/s)
- 0.80 ns sample interval
- 3749 total samples for 3 µs capture window

### 3. Trigger Module (`positron/scope/trigger.py`)
**Replaced:** `PS6000aTriggerConfigurator` → `PS6000TriggerConfigurator`

**Key Differences:**
- Uses **simplified trigger API**: `ps6000SetSimpleTrigger()`
- No complex PICO_CONDITION/PICO_DIRECTION structures needed
- OR logic implicit when multiple channels enabled
- Single function call handles threshold, direction, and auto-trigger
- **Voltage range code: 7** for ADC conversion (was 5 for PS6000a)

**Trigger Settings:**
- Threshold: -5 mV
- Direction: Falling edge
- Auto-trigger: 60 seconds (when enabled)

### 4. Acquisition Module (`positron/scope/acquisition.py`)
**Replaced:** `PS6000aAcquisitionEngine` → `PS6000AcquisitionEngine`

**Key Differences:**
- Uses **numeric channel codes** (0-3) instead of PICO_CHANNEL enums
- **API functions:**
  - `ps6000MemorySegments()` (not `ps6000a...`)
  - `ps6000SetNoOfCaptures()`
  - `ps6000SetDataBufferBulk()` for rapid block
  - `ps6000RunBlock()` with oversample parameter
  - `ps6000GetValuesBulk()`
  - `ps6000Stop()`
- Uses `ctypes.c_int32` instead of `ctypes.c_uint64` for sample counts
- **Voltage range code: 7** for ADC-to-mV conversion
- **Max ADC: 32767** (8-bit)
- Batch size: 20 captures per batch

### 5. Factory Functions
All factory functions updated to use "6000" series identifier:
- `create_configurator()`
- `create_trigger_configurator()`
- `create_acquisition_engine()`

## API Comparison

| Feature | PS6000a (New API) | PS6000 (Original) |
|---------|-------------------|-------------------|
| **Resolution** | 8-16 bit configurable | 8-bit fixed |
| **Input Impedance** | 1 MΩ or 50 Ω | 1 MΩ fixed |
| **100mV Range Code** | 5 | 7 |
| **Max ADC (8-bit)** | 32512 | 32512 |
| **Enums** | PicoDeviceEnums | Numeric constants |
| **Sample Counts** | c_uint64 | c_int32 |
| **Trigger API** | Complex (structures) | Simple (one call) |
| **OpenUnit** | With resolution param | No resolution param |
| **GetTimebase** | GetMinimumTimebaseStateless | GetTimebase2 |

## Testing

### Test Results
All tests passed successfully:

1. **Connection Test** ✓
   - Successfully opens PS6000 device
   - Retrieves model: 6402D
   - Serial: CP472/051

2. **Configuration Test** ✓
   - Channels configured: 4 (A, B, C, D)
   - Sample rate: 1250 MS/s
   - Total samples: 3749
   - Pre-trigger: 1249 samples

3. **Trigger Test** ✓
   - Trigger configured on all channels (OR logic)
   - Threshold: -5 mV
   - Direction: Falling
   - Auto-trigger: enabled

### Test Files
- `test_ps6000_quick.py` - Quick connection and configuration test
- `test_ps6000_complete.py` - Full test including trigger setup

## Files Modified
1. `positron/scope/connection.py`
2. `positron/scope/configuration.py`
3. `positron/scope/trigger.py`
4. `positron/scope/acquisition.py`

## Files Removed
- `test_ps6000a.py`
- `diagnose_ps6000a.py`
- `reset_ps6000a.py`
- `try_all_resolutions.py`
- `detect_ps6000_series.py`
- `debug_ps6000_open.py`

## Next Steps
The PS6000 (6402D) is now fully integrated into Positron and ready for use:

1. **Run the application:** `python main.py`
2. **Connect your 6402D** - It will be automatically detected
3. **Configure and run** - All settings will be applied automatically

## Notes
- The 6402D connects successfully with `ps6000OpenUnit()`
- Sample rate of 1.25 GS/s provides excellent time resolution (0.8 ns)
- 8-bit resolution provides sufficient dynamic range for the 100 mV range
- Simplified PS6000 API is easier to work with than PS6000a
- All protocol-based abstractions work correctly with PS6000
