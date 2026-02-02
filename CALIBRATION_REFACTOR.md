# Calibration Panel Refactor - Use Home Panel Acquisition

## Date: February 1, 2026 (Update 2)

## Summary

Refactored the Calibration panel to **eliminate duplicate acquisition code** and rely on the Home panel's acquisition infrastructure. This follows the single-responsibility principle and makes better use of existing features.

## Key Changes

### Removed from Calibration Panel:
- ❌ Start/Stop acquisition buttons
- ❌ Acquisition engine creation
- ❌ Acquisition state management
- ❌ Statistics timer
- ❌ Batch complete/error handlers
- ❌ ~150 lines of duplicate acquisition code

### Added to Calibration Panel:
- ✅ "Update All Histograms" button
- ✅ "Clear Storage" button
- ✅ Event count display from storage
- ✅ Clear instructions for using Home panel first
- ✅ Better messaging when no data available

## New Workflow

### Step 1: Configure Trigger (Home Panel)
1. Open Home panel
2. Click "Configure Trigger"
3. Set up OR logic for all channels:
   - **Condition 1: Channel A** (enabled)
   - **Condition 2: Channel B** (enabled)
   - **Condition 3: Channel C** (enabled)
   - **Condition 4: Channel D** (enabled)
4. This triggers on **any** channel (A OR B OR C OR D)

### Step 2: Acquire Data (Home Panel)
1. Place Na-22 source near all detectors
2. Click "Start" in Home panel
3. Watch event counter
4. Collect 1000+ events (or use auto-stop)
5. Click "Pause" or let it auto-stop

### Step 3: Calibrate (Calibration Panel)
1. Switch to Calibration tab
2. Click "Update All Histograms"
3. View each channel tab (A, B, C, D)
4. For each channel:
   - Drag regions over peaks
   - Find peaks
   - Calculate calibration
   - Apply calibration

## Benefits

### 1. No Code Duplication
- Single acquisition engine (in Home panel)
- One place to maintain acquisition logic
- Consistent behavior across application

### 2. Better User Experience
- More familiar workflow (Home panel is where you acquire data)
- Can use Home panel features:
  - Pause/Resume
  - Live statistics
  - Auto-stop conditions
  - Waveform display
- Clear separation: Home = Acquire, Calibration = Analyze

### 3. More Flexible
- Can pause acquisition, check histograms, resume if needed
- Can add more events without clearing previous data
- Can use existing data without re-acquiring

### 4. Simpler Code
- Calibration panel focuses on calibration only
- No state management for acquisition
- Easier to test and maintain

## UI Changes

### Before:
```
Calibration Panel:
├── Step 1: Acquire Data (All Channels)
│   ├── [Start] [Stop] [Clear]
│   └── Events: 1,234  Time: 00:02:15
├── Step 2: Identify Peaks
│   └── [Channel tabs with histograms]
└── Step 3: Calculate & Apply
```

### After:
```
Calibration Panel:
├── Instructions (use Home panel to acquire)
├── Calibration Data
│   ├── Events in Storage: 1,234
│   ├── [Update All Histograms]
│   └── [Clear Storage]
└── [Channel tabs with histograms]
    └── Find peaks, calculate, apply per channel
```

## Instructions in UI

The panel now shows clear instructions:
```
1. Go to Home panel and configure trigger: (A OR B OR C OR D)
2. Place Na-22 source near all detectors and acquire 1000+ events
3. Return here and click 'Update Histograms' to load data
4. Calibrate each channel using the tabs below
```

## Code Changes

### Modified File:
- `positron/panels/calibration.py`

### Removed Methods:
- `_create_acquisition_group()`
- `_start_acquisition()`
- `_stop_acquisition()`
- `_clear_data()` (replaced with `_clear_storage()`)
- `_on_batch_complete()`
- `_on_acquisition_error()`
- `_update_statistics()`

### Added Methods:
- `_create_data_status_group()` - Shows event count and buttons
- `_update_event_count_display()` - Refreshes count from storage
- `_update_all_histograms()` - Updates all 4 channel histograms
- `_clear_storage()` - Clears global event storage

### Modified Methods:
- `__init__()` - Removed acquisition state, timer
- `_setup_ui()` - New layout without acquisition controls
- `_update_histogram_display()` - Improved messaging for no data

### Removed Instance Variables:
- `self.acquisition_engine`
- `self._acquiring`
- `self._event_count` (uses storage.get_count() instead)
- `self._start_time`
- `self._stats_timer`

## Error Handling

### When No Data in Storage:
- "Update All Histograms" shows helpful message
- Explains need to acquire in Home panel first
- Suggests trigger configuration

### When Channel Has No Pulses:
```
No valid pulses found on channel X.

This could mean:
- No detector connected to this channel
- Trigger not configured for this channel
- No signals detected
```

## Testing Checklist

- [x] Open Calibration panel - shows instructions
- [x] Click "Update All Histograms" with no data - shows message
- [x] Go to Home panel
- [x] Configure trigger: (A OR B OR C OR D)
- [x] Acquire 1000+ events
- [x] Return to Calibration panel
- [x] Click "Update All Histograms" - all tabs populate
- [x] Check each channel tab - histograms visible
- [x] Complete calibration workflow per channel
- [x] Click "Clear Storage" - confirms and clears
- [x] Verify histograms cleared

## Compatibility

- ✅ No breaking changes to config
- ✅ No changes to other modules
- ✅ Works with existing event storage
- ✅ Backward compatible

## Future Enhancements

### Could Add:
- Auto-refresh when switching to Calibration tab (if new events)
- Visual indicator if data is stale/empty
- Link/button to jump to Home panel
- Preset trigger configuration button ("Set Calibration Trigger")

### Could Improve:
- Show which channels have data vs empty
- Display trigger configuration currently set
- Warn if trigger isn't configured for all channels

## File Statistics

- **Lines Removed**: ~200
- **Lines Added**: ~80
- **Net Change**: -120 lines (simpler!)
- **Linter Status**: ✅ No errors

---

**Result**: Cleaner architecture, no code duplication, better user experience!
