# Energy Calibration Quick Start Guide

## Prerequisites
- Connected PicoScope 3000a series oscilloscope
- Na-22 radioactive source
- Detector connected to one or more channels (A, B, C, D)
- Positron application running

## Calibration Workflow

### 1. Open Calibration Panel
- Launch Positron application
- Click on **"Calibration"** tab (Tab 2)

### 2. Select Channel
- Use the dropdown to select which channel to calibrate (A, B, C, or D)
- Status indicator shows if channel is already calibrated

### 3. Acquire Calibration Data
1. **Place Na-22 source** near the detector for the selected channel
2. Click **"Start Acquisition"**
3. Watch event counter increase
4. Collect **at least 1000 events** (more is better, 3000-5000 recommended)
5. Click **"Stop"** when sufficient data collected

### 4. Identify Peaks
1. Histogram will automatically display when acquisition stops
2. You should see **two distinct peaks**:
   - Lower peak: 511 keV (positron annihilation)
   - Higher peak: 1275 keV (Na-22 gamma)
3. Click **"Auto-Position Regions"** for initial placement
4. **Drag the green region** (Region 1) to cover the 511 keV peak
5. **Drag the blue region** (Region 2) to cover the 1275 keV peak
6. Adjust region widths to encompass peak but not too much background

### 5. Find Peak Centers
- Click **"Find Peaks from Regions"**
- Peak values will appear in the text fields
- Verify the values look reasonable:
  - Peak 2 should be ~2.5× Peak 1 (ratio of 1275/511)
  - Both peaks should be positive

### 6. Calculate Calibration
- Click **"Calculate Calibration"**
- Gain and Offset will be calculated and displayed
- Summary text shows:
  - Calibration parameters
  - Peak verification (should show ~511 and ~1275 keV)
  - Any warnings or errors

### 7. Apply Calibration
- Review the calculated values
- Click **"Apply Calibration"** to save
- Status indicator updates to show calibration date
- Calibration is automatically saved to config file

### 8. Repeat for Other Channels
- Select next channel from dropdown
- Repeat steps 3-7
- Each channel calibrates independently

## Tips for Best Results

### Histogram Display
- **Log Scale**: Check this if one peak is much taller than the other
- **Bins**: Adjust if peaks look too coarse or too noisy
  - Fewer bins (50-75): Smoother, better for low statistics
  - More bins (150-200): More detail, better for high statistics
- **Update Histogram**: Use if you change bin count

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
- **Clear Data**: Use "Clear Data" button if you need to start over

### Troubleshooting

**Problem**: "No valid pulses found"
- **Cause**: Selected channel has no signals
- **Solution**: Check detector connection, try different channel

**Problem**: "Peaks are too close together"
- **Cause**: Regions overlap or both on same peak
- **Solution**: Check region positions, ensure one on each peak

**Problem**: "Peak ratio outside expected range"
- **Cause**: Regions on wrong peaks or incorrect source
- **Solution**: Verify Na-22 source, check region positions

**Problem**: "Too few events in region"
- **Cause**: Region positioned in valley between peaks
- **Solution**: Move region to peak, collect more data

**Problem**: Histogram looks flat or noisy
- **Cause**: Insufficient data or incorrect trigger settings
- **Solution**: 
  - Acquire more events
  - Check Home panel trigger configuration
  - Verify detector producing signals

**Problem**: Only one peak visible
- **Cause**: Energy range issue or low statistics
- **Solution**:
  - Acquire more events
  - Try log scale
  - Check detector/source positioning

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

Example:
- Gain = 0.0026 keV/(mV·ns)
- Offset = 10 keV
- Raw energy = 192,000 mV·ns
- Calibrated = 0.0026 × 192,000 + 10 = 509 keV ≈ 511 keV ✓

## Verification

### After Calibration:
1. Check the summary text shows peaks near 511 and 1275 keV
2. Note the calibration date in the status indicator
3. Restart the application
4. Verify calibration persists (status shows date)

### Re-Calibration:
- Calibrations are permanent until overwritten
- To re-calibrate: Simply repeat the process
- Old calibration is replaced with new one
- Consider re-calibrating if:
  - Detector settings changed
  - Different PMT voltage
  - Long time since last calibration
  - Switching to different detector on same channel

## File Location

Calibration data is stored in:
- **Windows**: `C:\Users\<username>\.positron\config.json`
- **Linux/Mac**: `~/.positron/config.json`

## Next Steps

After calibration:
- Use Home panel for data acquisition
- (Future) Analysis panels will show calibrated energies
- (Future) Energy histograms will display in keV

## Advanced

### Manual Peak Entry:
Currently not supported via UI, but peaks are displayed in text fields after finding. In future, these could be made editable.

### Exporting Calibration:
Calibration is in JSON config file. Can manually copy calibration section to backup or share.

### Multiple Scopes:
Each scope can have its own calibration. Calibrations are tied to the connected scope series (PS3000a or PS6000a).

---

**Need Help?**
- Check error messages in the status text area
- Verify Na-22 source is present and detector is working
- Ensure sufficient events collected (1000+)
- Try log scale if histogram is hard to see
- Use Auto-Position Regions for initial placement
