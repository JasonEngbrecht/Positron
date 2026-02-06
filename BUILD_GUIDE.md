# Building a Standalone Executable for Positron

This guide explains how to create a standalone Windows executable for the Positron data acquisition system.

## Prerequisites

Before building, ensure you have:

1. **All dependencies installed**:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Verified the application runs** from source:
   ```bash
   python main.py
   ```

3. **A working PicoScope connection** for testing

## Quick Build

### Method 1: Using the Build Script (Recommended)

Simply double-click `build.bat` or run from command line:

```bash
build.bat
```

This script will:
- Check for PyInstaller installation
- Clean previous build artifacts
- Build the executable
- Report success/failure

### Method 2: Manual PyInstaller Command

If you prefer manual control:

```bash
pyinstaller positron.spec
```

## Build Output

After a successful build, you'll find:

```
dist/
└── Positron/
    ├── Positron.exe          # Main executable
    ├── PySide6/              # Qt libraries
    ├── numpy/                # NumPy libraries
    ├── pyqtgraph/            # Plotting libraries
    ├── picosdk/              # PicoScope SDK wrapper
    ├── positron/             # Your application code
    └── [many other DLLs]     # Dependencies
```

**Total size**: Approximately 150-250 MB (depends on dependencies)

## Testing the Executable

1. **Test on your development machine**:
   ```bash
   cd dist\Positron
   Positron.exe
   ```

2. **Test on a clean machine**:
   - Copy the entire `dist\Positron` folder to another computer
   - Ensure PicoScope drivers are installed
   - Run `Positron.exe`

## Distribution

### What to Distribute

**Option 1: Distribute the folder**
- Zip the entire `dist\Positron` folder
- Users unzip and run `Positron.exe`

**Option 2: Create an installer** (future enhancement)
- Use tools like Inno Setup or NSIS
- Create a professional installer

### System Requirements for End Users

The target computer must have:

1. **Windows 10 or later** (64-bit)
2. **PicoScope drivers installed** (PicoSDK):
   - Download from: https://www.picotech.com/downloads
   - Install the appropriate driver for PS3000a or PS6000a series
3. **Compatible PicoScope device**:
   - PS3000a series (tested: PS3406D MSO)
   - PS6000a series (framework in place)

**Note**: Python is NOT required on the target machine - everything is bundled!

## Customization Options

### 1. Console Window

By default, the executable shows a console window (useful for debugging). To hide it:

Edit `positron.spec`, change:
```python
console=True,  # Shows console
```
to:
```python
console=False,  # Hides console (production)
```

Then rebuild.

### 2. Application Icon

To add a custom icon:

1. Create or obtain a `.ico` file
2. Place it in the project root (e.g., `positron.ico`)
3. Edit `positron.spec`, change:
   ```python
   icon=None,
   ```
   to:
   ```python
   icon='positron.ico',
   ```
4. Rebuild

### 3. Reduce File Size

Current spec file uses `upx=True` for compression. Additional size reduction:

1. **Exclude unused modules** - Already configured in spec file
2. **Use `--onefile` mode** - Creates single .exe but slower startup:
   ```bash
   pyinstaller --onefile main.py
   ```
   (Not recommended for this application due to startup time)

## Troubleshooting

### Build Errors

**"Module not found" errors**:
- Add the missing module to `hiddenimports` in `positron.spec`
- Rebuild

**DLL errors**:
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Try cleaning build artifacts: delete `build/` and `dist/` folders

### Runtime Errors

**"PicoScope drivers not found"**:
- Install PicoSDK on the target machine
- Ensure the correct driver version for your scope series

**"Failed to connect to scope"**:
- Verify scope is connected via USB
- Check scope is powered on
- Ensure drivers are properly installed

**Application crashes immediately**:
- Run from command line to see error messages:
  ```bash
  cd dist\Positron
  Positron.exe
  ```
- Check for missing DLLs or configuration issues

### Testing Recommendations

1. **Test on development machine first**
2. **Test on a VM or clean machine** without Python installed
3. **Test with different PicoScope models** if available
4. **Verify all panels work**: Home, Calibration, Energy Display, Timing Display
5. **Test complete workflow**: Connect → Acquire → Calibrate → Analyze

## Build Time

- **First build**: 5-10 minutes (compiles everything)
- **Subsequent builds**: 2-5 minutes (reuses cached files)
- **Clean build**: 5-10 minutes (after deleting build artifacts)

## Advanced: One-File Executable

For a single executable file (instead of a folder), modify the spec file or use:

```bash
pyinstaller --onefile --windowed main.py
```

**Pros**: Single file is easier to distribute
**Cons**: 
- Slower startup (extracts files to temp folder)
- Larger file size
- More complex debugging

Not recommended for scientific applications like Positron where startup time matters.

## Version Control

Add to `.gitignore`:
```
build/
dist/
*.spec.bak
```

The spec file (`positron.spec`) should be version controlled.

## Future Enhancements

For Phase 6, consider:

1. **Professional installer** using Inno Setup
2. **Auto-update mechanism**
3. **Crash reporting**
4. **Usage analytics** (with user consent)
5. **Configuration wizard** for first-time setup
6. **Comprehensive user manual** (PDF)

## Support

If users encounter issues with the executable:

1. Check system requirements
2. Verify PicoScope drivers are installed
3. Test with source code: `python main.py`
4. Report issues with:
   - Windows version
   - PicoScope model
   - Error messages (from console or logs)

---

**Last Updated**: February 2026  
**Application Version**: v1.1.0  
**PyInstaller Version**: 6.0+
