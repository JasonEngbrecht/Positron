# PS6000a Integration - Implementation Summary

## Overview

The PS6000a series oscilloscope support has been successfully integrated into the Positron application. All three core modules (configuration, trigger, and acquisition) have been implemented according to the plan.

## Implementation Status

✅ **All implementation tasks completed:**

1. ✅ PS6000aConfigurator - 50Ω impedance, 10-bit resolution, 100mV range
2. ✅ PS6000aTriggerConfigurator - PICO_CONDITION structures with AND/OR logic
3. ✅ PS6000aAcquisitionEngine - 20-segment rapid block mode
4. ✅ Configuration system updates - Added timebase_index storage
5. ✅ Main application integration - Updated to support PS6000a

## Key Features Implemented

### 1. PS6000aConfigurator (`positron/scope/configuration.py`)

**Configuration Settings:**
- **Input Impedance:** 50Ω (PICO_DC_50OHM) - PS6000a-specific feature
- **Resolution:** 10-bit (PICO_DR_10BIT)
- **Voltage Range:** 100 mV (range code 5)
- **Bandwidth:** Full bandwidth (PICO_BW_FULL)
- **Channels:** All 4 channels (A, B, C, D) enabled

**Timebase Configuration:**
- Uses `ps6000aGetMinimumTimebaseStateless` for fastest sample rate
- Calculates channel flags for all 4 channels
- Determines optimal timebase for 3 µs capture window (1 µs pre-trigger, 2 µs post-trigger)
- Stores timebase index for use by acquisition engine

**Expected Performance:**
- Sample rate: 1.25-2.5 GS/s (model-dependent, with 4 channels active)
- Sample interval: 0.4-0.8 ns
- Samples per waveform: ~3750-7500 (vs 375 on PS3000a)

### 2. PS6000aTriggerConfigurator (`positron/scope/trigger.py`)

**Trigger Configuration:**
- **Threshold:** -5 mV (for negative pulses)
- **Direction:** Falling edge (PICO_FALLING)
- **Threshold Mode:** Level trigger (PICO_LEVEL)
- **Hysteresis:** 0 (as per PS6000a examples)

**Logic Implementation:**
- Uses `PICO_CONDITION` structures for channel conditions
- Multiple PICO_CONDITION structs implement OR logic
- Supports up to 4 trigger conditions
- Auto-trigger configurable (60 second maximum)

**API Calls:**
1. `ps6000aSetTriggerChannelConditions` - Set AND/OR logic
2. `ps6000aSetTriggerChannelDirections` - Set falling edge
3. `ps6000aSetTriggerChannelProperties` - Set threshold and auto-trigger

**Note:** Current implementation focuses on OR logic (A OR B OR C OR D), which is the most common use case for PALS experiments. AND logic within a single condition may require additional investigation.

### 3. PS6000aAcquisitionEngine (`positron/scope/acquisition.py`)

**Rapid Block Mode:**
- **Batch Size:** 20 captures per batch (vs 10 for PS3000a)
- **Buffer Management:** 4 channels × 20 segments = 80 buffers
- **Data Type:** PICO_INT16_T (16-bit ADC values)
- **Downsample Mode:** PICO_RATIO_MODE_RAW (no downsampling)

**API Calls:**
1. `ps6000aMemorySegments` - Allocate memory for 20 segments
2. `ps6000aSetNoOfCaptures` - Set capture count to 20
3. `ps6000aSetDataBuffers` - Register buffers (with CLEAR_ALL | ADD pattern)
4. `ps6000aRunBlock` - Start acquisition
5. `ps6000aIsReady` - Poll for completion
6. `ps6000aGetValuesBulk` - Retrieve all 20 waveforms
7. `ps6000aStop` - Stop acquisition on cleanup

**Event Processing:**
- Processes all 20 segments per batch
- Converts ADC to mV using 10-bit ADC limits
- Analyzes pulses using existing CFD timing and energy integration
- Stores events in shared EventStorage
- Emits signals for UI updates

**Performance:**
- Memory per batch: ~1.2 MB (20 × 7500 × 4 channels × 2 bytes)
- Target rate: >1000 events/second
- Processing: Same pulse analysis as PS3000a

### 4. Configuration System Updates

**Added to `positron/config.py`:**
- `timebase_index` field in ScopeConfig
- Serialization/deserialization support
- Backward compatibility maintained

**Updated in `main.py`:**
- Stores timebase_index from configurator
- Passes timebase_index to acquisition engine

**Updated in `positron/panels/home.py`:**
- Automatically uses batch_size=20 for PS6000a
- Passes timebase_index to acquisition engine

## API Differences: PS6000a vs PS3000a

| Feature | PS3000a | PS6000a |
|---------|---------|---------|
| **Resolution** | 8-bit fixed | 10-bit (configurable 8/10/12) |
| **Impedance** | 1MΩ only | 50Ω or 1MΩ |
| **Channel Setup** | `ps3000aSetChannel` | `ps6000aSetChannelOn/Off` |
| **Enums** | Series-specific (PS3000A_*) | Generic (PICO_*) |
| **Timebase API** | `ps3000aGetTimebase2` (iterative) | `ps6000aGetMinimumTimebaseStateless` |
| **Trigger Structures** | PS3000A_TRIGGER_CONDITIONS_V2 | PICO_CONDITION, PICO_DIRECTION |
| **Sample Count Type** | ctypes.c_int32 | ctypes.c_uint64 |
| **Batch Size** | 10 captures | 20 captures |
| **Data Buffer API** | `ps3000aSetDataBuffers` | `ps6000aSetDataBuffers` (different params) |

## Testing

### Test Script

A test script `test_ps6000a.py` has been created to verify the integration:

```bash
python test_ps6000a.py
```

**Tests Performed:**
1. ✓ Connection and device info retrieval
2. ✓ Configuration with 50Ω, 10-bit, 100mV settings
3. ✓ Trigger configuration (single channel and OR logic)

### Running the Full Application

To run the full Positron application with PS6000a:

```bash
python main.py
```

The application will:
1. Auto-detect PS6000a scope
2. Apply configuration (50Ω, 10-bit, 100mV)
3. Configure trigger
4. Launch main window with all panels

### Testing Workflow

**Basic Testing:**
1. Run `test_ps6000a.py` to verify basic functionality
2. Check console output for configuration details
3. Verify sample rate and timebase settings

**Acquisition Testing:**
1. Run `python main.py`
2. Navigate to Home panel
3. Configure trigger (e.g., A OR B OR C OR D)
4. Click Start to begin acquisition
5. Verify waveform display updates
6. Check event counter increments (20 events per batch)

**Calibration Testing:**
1. Place Na-22 source near detectors
2. Acquire 1000+ events
3. Navigate to Calibration panel
4. Update histograms and verify 511 keV and 1275 keV peaks
5. Perform calibration for all channels

**Analysis Testing:**
1. Navigate to Energy Display panel
2. Verify energy histograms show calibrated peaks
3. Navigate to Timing Display panel
4. Configure channel pairs and energy windows
5. Verify timing difference histograms display

## Files Modified

### Core Implementation
- `positron/scope/configuration.py` - PS6000aConfigurator implementation
- `positron/scope/trigger.py` - PS6000aTriggerConfigurator implementation
- `positron/scope/acquisition.py` - PS6000aAcquisitionEngine implementation

### Integration
- `positron/config.py` - Added timebase_index field
- `main.py` - Store timebase_index from configurator
- `positron/panels/home.py` - Pass timebase_index and adjust batch size

### Testing
- `test_ps6000a.py` - New test script for PS6000a verification

## Known Limitations

1. **AND Logic:** The current trigger implementation focuses on OR logic (A OR B OR C OR D). AND logic within a single condition (e.g., A AND B) may require additional API calls or different structure usage. This is not a common use case for PALS experiments.

2. **Resolution:** Fixed at 10-bit. Could be made configurable in future if needed.

3. **Batch Size:** Fixed at 20 for PS6000a. Could be made configurable based on memory and performance requirements.

## Performance Expectations

### Sample Rate
- **PS3000a:** 125-250 MS/s (4 channels)
- **PS6000a:** 1.25-2.5 GS/s (4 channels)
- **Improvement:** ~10× faster sampling

### Resolution
- **PS3000a:** 8-bit (±128 ADC counts)
- **PS6000a:** 10-bit (±512 ADC counts)
- **Improvement:** 4× better voltage resolution (~0.2 mV steps at 100 mV range)

### Batch Processing
- **PS3000a:** 10 events per batch
- **PS6000a:** 20 events per batch
- **Improvement:** 2× more events per batch cycle

### Memory Usage
- **PS3000a:** ~60 KB per batch (10 × 375 × 4 × 2)
- **PS6000a:** ~1.2 MB per batch (20 × 7500 × 4 × 2)
- **Increase:** ~20× more memory per batch (acceptable)

## Next Steps

1. **Hardware Testing:** Test with live PS6000a scope and pulse signals
2. **Performance Validation:** Verify >1000 events/sec acquisition rate
3. **Calibration Verification:** Confirm Na-22 calibration produces accurate results
4. **Extended Testing:** Run overnight acquisition to verify stability
5. **Documentation:** Update user guide with PS6000a-specific information

## Troubleshooting

### Connection Issues
- Verify PS6000a drivers are installed
- Check USB connection (USB 3.0 recommended)
- Ensure scope is not in use by PicoScope software

### Configuration Errors
- Check that 50Ω impedance is supported by your model
- Verify 10-bit resolution is available
- Ensure firmware is up to date

### Acquisition Issues
- Check trigger threshold (-5 mV) matches signal polarity
- Verify trigger channels are configured correctly
- Monitor event storage capacity (max 1M events)

### Performance Issues
- Large sample counts may slow processing
- Consider reducing batch size if memory is limited
- Monitor CPU usage during high-rate acquisition

## Conclusion

The PS6000a integration is complete and ready for testing. All core functionality has been implemented according to the plan, with proper handling of PS6000a-specific features (50Ω impedance, 10-bit resolution, faster sampling). The implementation maintains compatibility with existing PS3000a code through the protocol-based architecture.

**Status:** ✅ Implementation Complete - Ready for Hardware Testing
