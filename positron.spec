# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Positron application.

Usage:
    pyinstaller positron.spec

This creates a standalone executable in the 'dist/Positron' directory.
"""

import sys
import os
from pathlib import Path

# Project root directory
project_root = Path('.').resolve()

# Prepare data files list
datas_list = []
# Include user manual PDF if it exists
if os.path.exists('Positron_User_Manual.pdf'):
    datas_list.append(('Positron_User_Manual.pdf', '.'))

# Analysis: Find all source files and dependencies
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        # PySide6 modules
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        
        # PyQtGraph and dependencies
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.exporters',
        
        # NumPy
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        
        # PicoSDK modules - include all potential scope types
        'picosdk',
        'picosdk.ps3000a',
        'picosdk.ps6000a',
        'picosdk.functions',
        'picosdk.constants',
        'picosdk.errors',
        'picosdk.library',
        
        # Positron package modules
        'positron',
        'positron.app',
        'positron.config',
        'positron.scope',
        'positron.scope.connection',
        'positron.scope.configuration',
        'positron.scope.acquisition',
        'positron.scope.trigger',
        'positron.processing',
        'positron.processing.pulse',
        'positron.processing.events',
        'positron.calibration',
        'positron.calibration.energy',
        'positron.panels',
        'positron.panels.home',
        'positron.panels.calibration',
        'positron.panels.analysis',
        'positron.panels.analysis.utils',
        'positron.panels.analysis.energy_display',
        'positron.panels.analysis.timing_display',
        'positron.ui',
        'positron.ui.main_window',
        'positron.ui.waveform_plot',
        'positron.ui.histogram_plot',
        'positron.ui.trigger_dialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'PIL',
        'tkinter',
        'wx',
    ],
    noarchive=False,
    optimize=0,
)

# PYZ: Create the Python archive
pyz = PYZ(a.pure)

# EXE: Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Positron',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Hide console window for production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you create one: icon='positron.ico'
)

# COLLECT: Bundle everything together
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Positron',
)
