@echo off
REM Run Positron from source with the anomaly waveform dump enabled.
REM Writes .npz files for anomalous events to %USERPROFILE%\.positron\debug\<timestamp>\
REM Plot them afterwards with:  py tools\plot_anomalies.py
set POSITRON_DUMP_ANOMALIES=1
call run.bat
