# Energy Calibration Quick Start Guide

## Prerequisites
- Connected PicoScope 3000a series oscilloscope
- Na-22 radioactive source
- Detector connected to one or more channels (A, B, C, D)
- Positron application running

## Calibration Workflow

### Step 1: Configure Trigger (Home Panel)
1. Launch Positron application
2. Go to **Home** panel
3. Click **"Configure Trigger"**
4. Set up OR logic for all channels you want to calibrate:
   - **Condition 1**: Channel A (enabled)
   - **Condition 2**: Channel B (enabled)
   - **Condition 3**: Channel C (enabled)
   - **Condition 4**: Channel D (enabled)
5. This creates **A OR B OR C OR D** trigger logic
6. Click **OK** to save

### Step 2: Acquire Calibration Data (Home Panel)
1. **Place Na-22 source** near all detectors
2. Click **"Start"** in Home panel
3. Watch event counter increase
4. Collect **at least 1000 events** (more is better, 3000-5000 recommended)
5. Optional: Use auto-stop feature (set event limit to desired count)
6. Click **"Pause"** when sufficient data collected (or let auto-stop handle it)

### Step 3: Open Calibration Panel
1. Click on **"Calibration"** tab (Tab 2)
2. You'll see tabs for each channel (A | B | C | D)
3. Status indicators show if channels are already calibrated

### Step 4: Load Data into Histograms
1. Click **"Update All Histograms"** button
2. All 4 channel histograms will populate from the acquired data
3. If a channel shows "No valid pulses found", that detector may not be connected

### Step 5: Identify Peaks (Per Channel)
For each channel tab (A, B, C, D):

1. **View the histogram** - you should see **two distinct peaks**:
   - Lower peak: 511 keV (positron annihilation)
   - Higher peak: 1275 keV (Na-22 gamma)
2. **Adjust display if needed**:
   - Check "Log Scale" if peaks are hard to see
   - Adjust bin count (default 1000 is usually good)
3. **Position regions**:
   - **Drag the green region** (Region 1) to cover the 511 keV peak
   - **Drag the blue region** (Region 2) to cover the 1275 keV peak
   - Adjust widths to encompass each peak but not too much background

### Step 6: Find Peak Centers (Per Channel)
1. Click **"Find Peaks from Regions"**
2. Peak values will appear in the text fields
3. Verify the values look reasonable:
   - Peak 2 should be ~2.5× Peak 1 (ratio of 1275/511)
   - Both peaks should be positive

### Step 7: Calculate Calibration (Per Channel)
1. Click **"Calculate Calibration"**
2. Gain and Offset will be calculated and displayed
3. Summary text shows:
   - Calibration parameters (gain, offset)
   - Peak verification (should show ~511 and ~1275 keV)
   - Any warnings or errors

### Step 8: Apply Calibration (Per Channel)
1. Review the calculated values
2. Click **"Apply Calibration"** to save
3. Status indicator updates to show calibration date
4. Calibration is automatically saved to config file

### Step 9: Repeat for Other Channels
1. Click next channel tab (B, C, or D)
2. Repeat steps 5-8 for each channel
3. Each channel calibrates independently
4. **Advantage**: All channels use the same acquired data!

## Tips for Best Results

### Data Collection (Home Panel)
- **Trigger Configuration**: Use (A OR B OR C OR D) to collect data from all channels simultaneously
- **Event Count**: 1000 minimum, 3000-5000 recommended
- **Source Placement**: Position Na-22 where all detectors can see it
- **Auto-Stop**: Set event count limit for automatic stop

### Histogram Display (Calibration Panel)
- **Log Scale**: Check this if one peak is much taller than the other (usually recommended)
- **Bins**: Adjust if peaks look too coarse or too noisy
  - Fewer bins (200-500): Smoother, better for low statistics
  - More bins (1000-2000): More detail, better for high statistics
  - Default (1000): Good for most cases

### Peak Selection
- **Region Width**: 
  - Too narrow: May miss part of the peak
  - Too wide: Includes background, biases peak center
  - Good width: Covers full peak width but minimal background
- **Peak Position**: 
  - Center the region on the peak maximum
  - The weighted mean algorithm is forgiving of small misalignment

### Data Quality
- **Minimum Events**: 1000 events (system minimum: 100)
- **Recommended**: 3000-5000 events for stable calibration
- **Too Few Events**: Peaks will be noisy, calibration unreliable
- **Clear Storage**: Use "Clear Storage" button if you need to start over

## Troubleshooting

### Acquisition Issues

**Problem**: No events being collected
- **Cause**: Trigger not configured or no signals present
- **Solution**: 
  - Verify trigger is configured (A OR B OR C OR D)
  - Check detector connections
  - Verify Na-22 source is present

**Problem**: Very low event rate
- **Cause**: Source too far away or weak
- **Solution**: Move source closer to detectors

### Histogram Issues

**Problem**: "No valid pulses found" on a channel
- **Cause**: Selected channel has no signals
- **Solution**: 
  - Check detector connection for that channel
  - Verify trigger includes that channel
  - That channel may not have a detector connected (OK to skip)

**Problem**: Histogram looks flat or noisy
- **Cause**: Insufficient data or incorrect trigger settings
- **Solution**: 
  - Acquire more events in Home panel
  - Check trigger configuration
  - Verify detector producing signals
  - Try log scale

**Problem**: Only one peak visible
- **Cause**: Energy range issue or low statistics
- **Solution**:
  - Acquire more events
  - Try log scale (usually reveals hidden peak)
  - Check detector/source positioning
  - Increase bin count

### Peak Selection Issues

**Problem**: "Peaks are too close together"
- **Cause**: Regions overlap or both on same peak
- **Solution**: Check region positions, ensure one on each peak

**Problem**: "Peak ratio outside expected range"
- **Cause**: Regions on wrong peaks or incorrect source
- **Solution**: 
  - Verify Na-22 source (not a different isotope)
  - Check region positions (green on lower peak, blue on higher peak)
  - Peaks should be ~2.5× apart

**Problem**: "Too few events in region"
- **Cause**: Region positioned in valley between peaks
- **Solution**: Move region to peak center, or collect more data

## Understanding the Results

### Typical Values (will vary by detector/setup):
- **Gain**: 0.001 to 0.1 keV/(mV·ns)
  - Higher gain = more sensitive detector or higher PMT voltage
- **Offset**: -50 to +50 keV
  - Usually small, accounts for baseline shifts
- **Peak Ratio**: ~2.5 (1275/511)
  - Should be close to this for Na-22

### Calibration Equation:
```
E_calibrated [keV] = gain × E_raw [mV·ns] + offset
```

**Example:**
- Gain = 0.0026 keV/(mV·ns)
- Offset = 10 keV
- Raw energy = 192,000 mV·ns
- Calibrated = 0.0026 × 192,000 + 10 = 509 keV ≈ 511 keV ✓

## Verification

### After Calibration:
1. Check the summary text shows peaks near 511 and 1275 keV
2. Note the calibration date in the status indicator
3. Restart the application
4. Open Calibration panel and verify status shows calibration dates
5. Calibrations persist between sessions

### Re-Calibration:
- Calibrations are permanent until overwritten
- To re-calibrate: Simply repeat the process
- Old calibration is replaced with new one
- Consider re-calibrating if:
  - Detector settings changed
  - Different PMT voltage
  - Long time since last calibration
  - Switching to different detector on same channel

## Advanced Tips

### Calibrating Only Some Channels
If you only want to calibrate channels A and B:
1. Configure trigger: (A OR B) in Home panel
2. Acquire data
3. In Calibration panel, only tabs A and B will have meaningful histograms
4. Calibrate those channels; leave C and D uncalibrated

### Using Existing Data
If you already have events in storage from previous acquisition:
1. Go directly to Calibration panel
2. Click "Update All Histograms"
3. No need to re-acquire if you have sufficient events

### Clearing Data
- **"Clear Storage"** button in Calibration panel clears all events
- **"Restart"** button in Home panel also clears events and resets counters
- Use when starting a fresh calibration run

## File Locations

**Calibration data is stored in:**
- **Windows**: `C:\Users\<username>\.positron\config.json`
- **Linux/Mac**: `~/.positron/config.json`

**Backing up calibrations:**
- Copy the config.json file to backup
- Calibrations are in the `calibration_a`, `calibration_b`, `calibration_c`, `calibration_d` sections

## Next Steps

After calibration:
- Return to Home panel for normal data acquisition
- (Future) Analysis panels will display calibrated energies in keV
- (Future) Energy histograms will show in keV instead of raw mV·ns units

---

## Quick Reference

**Complete Workflow Summary:**
1. Home → Configure Trigger → (A OR B OR C OR D)
2. Home → Place Na-22 → Start → Collect 3000+ events → Pause
3. Calibration → Update All Histograms
4. For each channel tab: Position regions → Find Peaks → Calculate → Apply
5. Done! All channels calibrated from single acquisition.

**Need Help?**
- Check error messages in the status text area
- Verify Na-22 source is present and detectors are working
- Ensure sufficient events collected (1000+ minimum, 3000+ recommended)
- Use log scale if histogram is hard to see
- Make sure trigger is configured for all channels: (A OR B OR C OR D)
