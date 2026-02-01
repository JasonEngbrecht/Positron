# Positron Documentation Reference Library

This folder contains offline reference materials for PicoScope hardware and the PicoSDK Python wrappers. These documents are essential for developing the Positron data acquisition system.

## Contents Overview

### API Programmer's Guides (Primary References)

**`picoscope-3000-series-a-api-programmers-guide.pdf`**
- Comprehensive API reference for PS3000a series oscilloscopes
- Essential for understanding function calls, parameters, and return codes
- Key sections:
  - Triggering modes (simple, advanced, AND/OR logic)
  - Block mode vs streaming mode operation
  - Memory segment management
  - Timebase calculations
  - Signal generator control
- **Use when**: Implementing core acquisition logic, configuring triggers, troubleshooting API calls

**`picoscope-6000-series-a-api-programmers-guide.pdf`**
- Comprehensive API reference for PS6000a series oscilloscopes
- Similar structure to PS3000a guide but with hardware-specific differences
- Notable differences: higher resolution, different timebase ranges
- **Use when**: Adding PS6000 series support or comparing API differences between series

### Hardware Data Sheets

**`picoscope-3000d-series-data-sheet.pdf`**
- Hardware specifications for PS3000D series
- Contains: bandwidth, sample rates, resolution, input ranges, trigger specifications
- **Use when**: Understanding hardware limitations, selecting appropriate settings, validating user inputs

**`picoscope-6000e-series-data-sheet.pdf`**
- Hardware specifications for PS6000E series
- Higher performance specifications than 3000 series
- **Use when**: Implementing PS6000 series support, understanding advanced capabilities

### Advanced Topics

**`picosdk-advanced-triggers.pdf`**
- Detailed documentation on advanced triggering capabilities
- Covers: pulse width triggers, window triggers, logic triggers (AND/OR combinations)
- **Use when**: Implementing sophisticated triggering for coincidence detection in PALS experiments

### Python Examples and Code Reference

**`picosdk-python-wrappers-master/`** (Directory)
- Complete GitHub repository clone of official Python wrappers
- Contains working examples for various acquisition modes
- Key subdirectories:
  - `examples/` - Complete working scripts demonstrating different features
  - `picosdk/` - Source code for the wrapper library
- **Use when**: Looking for implementation patterns, understanding best practices, troubleshooting Python-specific issues

## Quick Reference Guide for Common Tasks

### Setting up hardware triggering
→ See PS3000a/PS6000a Programmer's Guide, "Trigger" chapter
→ See `picosdk-advanced-triggers.pdf` for AND/OR logic

### Configuring acquisition modes
→ See PS3000a/PS6000a Programmer's Guide, "Block mode" or "Streaming mode" chapters
→ Check `examples/` folder for working code patterns

### Understanding timebase and sample rate relationships
→ See PS3000a/PS6000a Programmer's Guide, "Timebase" section
→ Cross-reference with data sheet for hardware-specific limits

### Implementing energy calibration
→ Data sheets for input range specifications
→ Programmer's Guide for resolution and voltage conversion formulas

### Error code lookup
→ All programmer's guides have comprehensive appendices listing error codes and meanings

## Notes for LLM Context

**Project Context**: These documents support the Positron project, a Python-based data acquisition system for pulse detection experiments (primarily positron annihilation lifetime spectroscopy - PALS).

**Primary Use Case**: Event-mode acquisition with 4-channel waveforms, hardware triggering with AND/OR logic, energy calibration using Na-22 sources (511 keV and 1275 keV peaks).

**Target Hardware**: PicoScope 3000 or 6000 series oscilloscopes, operating via the `picosdk` Python wrapper library (v1.1 installed).

**Key Requirement**: The system must handle acquisition rates from <1 to 10,000 events per second, requiring careful attention to API performance and buffer management as documented in these guides.

## Document Versions

These PDFs are local snapshots and may not reflect the absolute latest versions. For updates, check:
- https://www.picotech.com/downloads (official documentation)
- https://github.com/picotech/picosdk-python-wrappers (Python wrapper updates)

---

*README created: 2025-01-31*
*Purpose: Provide comprehensive reference guide for LLM-assisted development of Positron project*
