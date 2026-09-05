@echo off
REM Run Positron from source with a 200 mV input range instead of the
REM production 100 mV (developer switch for energy-linearity / clipping
REM studies: at 100 mV the pulse peak reaches the rail near 1000 keV).
REM Raw energies (mV*ns) are range-independent, so the 511 keV raw centroid
REM should match a 100 mV run; only clipped peaks move. Calibrate afresh
REM at this range before comparing offsets, and re-run run.bat to go back.
set POSITRON_RANGE_MV=200
call run.bat
