# Quick Reference: Building Positron Distribution

## To Build the Distribution

Simply run:
```powershell
.\build.bat
```

This will automatically:
1. ✅ Generate the PDF user manual from DISTRIBUTION_README.md
2. ✅ Clean previous build artifacts
3. ✅ Build the standalone executable with PyInstaller
4. ✅ Include the PDF in the distribution folder
5. ✅ Report success/failure

## Distribution Package Contents

After building, `dist\Positron\` will contain:
- `Positron.exe` - The standalone application
- `Positron_User_Manual.pdf` - User guide for students
- [Many DLLs and folders] - Required libraries

## To Distribute to Students

1. **Zip the entire folder**:
   - Right-click `dist\Positron` → Send to → Compressed folder
   - Rename to: `Positron_v1.0.zip`

2. **Provide to students** with these instructions:
   - Install PicoScope drivers from https://www.picotech.com/downloads
   - Unzip the Positron folder
   - Read `Positron_User_Manual.pdf`
   - Run `Positron.exe`

## Files Overview

| File | Purpose | Include in Distribution? |
|------|---------|-------------------------|
| `Positron.exe` | Main application | ✅ Yes |
| `Positron_User_Manual.pdf` | User guide | ✅ Yes |
| `build.bat` | Build script | ❌ No (developer only) |
| `positron.spec` | PyInstaller config | ❌ No (developer only) |
| `DEVELOPMENT_PLAN.md` | Dev documentation | ❌ No (developer only) |
| `BUILD_GUIDE.md` | Build instructions | ❌ No (developer only) |
| `generate_readme_pdf.py` | PDF generator | ❌ No (developer only) |

## Updating the User Manual

If you edit `DISTRIBUTION_README.md`:
1. Save your changes
2. Run `.\build.bat` - it will automatically regenerate the PDF
3. The new PDF will be included in the build

## Troubleshooting

**PDF not generated?**
- Manually run: `python generate_readme_pdf.py`
- Check if reportlab is installed: `pip install reportlab`

**Build fails?**
- See BUILD_GUIDE.md for detailed troubleshooting

**Want to test without rebuilding?**
- The executable is at: `dist\Positron\Positron.exe`
- Just run it directly

---

**Last Updated**: February 2026
