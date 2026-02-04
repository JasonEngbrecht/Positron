# How to Create a GitHub Release for Positron

This guide explains how to distribute the compiled Positron executable via GitHub Releases.

## Why Use GitHub Releases?

- ✅ Keeps large binaries separate from source code
- ✅ Easy for users to download
- ✅ Version tracking
- ✅ Release notes and changelogs
- ✅ No large files clogging up the repository

## Steps to Create a Release

### 1. Build the Application

```powershell
cd C:\Users\engbrech\Python\Positron
.\build.bat
```

This creates `dist\Positron\` with all files.

### 2. Create a ZIP File

Right-click the `dist\Positron` folder and select "Send to > Compressed (zipped) folder"

Rename it to: `Positron_v1.0_Windows.zip`

### 3. Commit and Push Your Code

**Important**: Don't commit the `dist/` or `build/` folders!

```bash
git add .
git commit -m "Release v1.0 - Initial stable release"
git push origin main
```

### 4. Create a Release on GitHub

1. **Go to your repository** on GitHub
2. **Click "Releases"** (right sidebar)
3. **Click "Draft a new release"**
4. **Fill in the details**:

   **Tag version**: `v1.0`
   
   **Release title**: `Positron v1.0 - Initial Release`
   
   **Description**:
   ```markdown
   # Positron v1.0 - Initial Stable Release
   
   🎉 First stable release of Positron data acquisition system!
   
   ## What's Included
   
   - Full 4-channel waveform acquisition
   - Energy calibration with Na-22 sources
   - Real-time analysis panels
   - Complete user manual (PDF)
   
   ## System Requirements
   
   - Windows 10 or later (64-bit)
   - PicoScope 3000a or 6000a series
   - PicoScope drivers (PicoSDK) - [Download here](https://www.picotech.com/downloads)
   
   ## Installation
   
   1. Download `Positron_v1.0_Windows.zip` below
   2. Extract to your desired location
   3. Install PicoScope drivers if not already installed
   4. Run `Positron.exe`
   5. Read `Positron_User_Manual.pdf` for complete instructions
   
   ## What's New
   
   - ✅ Phase 1-5 complete
   - ✅ Full acquisition and analysis pipeline
   - ✅ Professional packaging
   - ✅ Comprehensive documentation
   
   ## Known Issues
   
   - PS6000a support framework in place but not fully tested
   
   ## Support
   
   For issues, please use the [Issues tab](https://github.com/YOUR_USERNAME/Positron/issues)
   
   ---
   
   **File Size**: ~200 MB (includes all dependencies)
   **No Python installation required!**
   ```

5. **Upload the ZIP file**: Drag `Positron_v1.0_Windows.zip` to the "Attach binaries" section

6. **Click "Publish release"**

### 5. Update Your README

In your main README.md, update the download link:

```markdown
👉 **[Download Latest Release (Windows)](https://github.com/YOUR_USERNAME/Positron/releases/latest)**
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Future Releases (v1.1, v1.2, etc.)

When you make updates:

1. Update version numbers in code
2. Rebuild: `.\build.bat`
3. Create new ZIP: `Positron_v1.1_Windows.zip`
4. Create new GitHub release with:
   - New tag: `v1.1`
   - Changelog describing what changed
   - Upload new ZIP file

## Release Checklist

Before creating a release, verify:

- [ ] Application builds successfully
- [ ] Executable runs on a clean machine
- [ ] User manual PDF is included
- [ ] All features work as expected
- [ ] README.md is up to date
- [ ] CHANGELOG.md is updated (if you have one)
- [ ] Version numbers are correct
- [ ] LICENSE file is present

## Best Practices

### Version Numbering

Use semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Examples:
- `v1.0.0` - Initial release
- `v1.1.0` - Added new analysis panel
- `v1.1.1` - Fixed bug in calibration

### Release Notes

Always include:
- What's new
- Bug fixes
- Known issues
- Installation instructions
- System requirements

### File Naming

Use clear, descriptive names:
- ✅ `Positron_v1.0_Windows.zip`
- ✅ `Positron_v1.0_Windows_x64.zip`
- ❌ `positron.zip`
- ❌ `dist.zip`

## Troubleshooting

**ZIP file too large?**
- This is normal (~200 MB with all dependencies)
- GitHub allows files up to 2 GB

**Release not showing up?**
- Make sure you clicked "Publish release", not "Save draft"
- Check that the release is not marked as "pre-release"

**Users can't download?**
- Verify the repository is public
- Check that the ZIP file uploaded correctly
- Test the download link yourself

## Additional Tips

### Create a CHANGELOG.md

Track changes between versions:

```markdown
# Changelog

## [1.0.0] - 2026-02-04

### Added
- Initial stable release
- Full acquisition pipeline
- Energy calibration
- Analysis panels
- User manual

### Known Issues
- PS6000a implementation incomplete
```

### Add Release Automation (Optional)

For advanced users, you can automate releases using GitHub Actions, but manual releases are fine for now.

---

**Remember**: Source code stays in Git, compiled executables go in Releases!
