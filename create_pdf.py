"""
Simple PDF generator for Positron user manual.
Run this before building to create the PDF.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
import os

def create_simple_pdf():
    """Create a simple, clean PDF from the readme content."""
    
    output_file = "Positron_User_Manual.pdf"
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=letter,
                           topMargin=0.75*inch, bottomMargin=0.75*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph("<font size=24 color='#1a5490'><b>Positron - Data Acquisition System</b></font>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3*inch))
    
    # Version info
    story.append(Paragraph("<b>Version:</b> 1.0 (Phase 5 Complete)", styles['Normal']))
    story.append(Paragraph("<b>For:</b> Nuclear and Particle Physics Experiments", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Overview
    story.append(Paragraph("<font size=16 color='#1a5490'><b>Overview</b></font>", styles['Heading1']))
    story.append(Paragraph("Positron is a data acquisition and analysis system for pulse detection experiments using PicoScope oscilloscopes. Designed for positron annihilation lifetime spectroscopy (PALS) and related nuclear physics experiments.", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))
    
    # System Requirements
    story.append(Paragraph("<font size=14 color='#2a6ab0'><b>System Requirements</b></font>", styles['Heading2']))
    story.append(Paragraph("• <b>Operating System:</b> Windows 10 or later (64-bit)", styles['Normal']))
    story.append(Paragraph("• <b>Hardware:</b> PicoScope oscilloscope (3000 or 6000 series)", styles['Normal']))
    story.append(Paragraph("• <b>Drivers:</b> PicoScope SDK must be installed", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))
    
    # Installation
    story.append(Paragraph("<font size=14 color='#2a6ab0'><b>Installation</b></font>", styles['Heading2']))
    story.append(Paragraph("<b>1. Install PicoScope Drivers:</b>", styles['Normal']))
    story.append(Paragraph("   • Download from: https://www.picotech.com/downloads", styles['Normal']))
    story.append(Paragraph("   • Select your PicoScope model", styles['Normal']))
    story.append(Paragraph("   • Install the PicoSDK package", styles['Normal']))
    story.append(Paragraph("   • Restart your computer", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>2. Extract Positron Application:</b>", styles['Normal']))
    story.append(Paragraph("   • Unzip the provided folder to your desired location", styles['Normal']))
    story.append(Paragraph("   • Example: C:\\Program Files\\Positron\\", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>3. Connect Your PicoScope:</b>", styles['Normal']))
    story.append(Paragraph("   • Connect the oscilloscope to a USB port", styles['Normal']))
    story.append(Paragraph("   • Wait for Windows to recognize the device", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>4. Launch Positron:</b>", styles['Normal']))
    story.append(Paragraph("   • Double-click Positron.exe", styles['Normal']))
    story.append(Paragraph("   • The application will automatically detect your scope", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Using Positron
    story.append(Paragraph("<font size=16 color='#1a5490'><b>Using Positron</b></font>", styles['Heading1']))
    story.append(Paragraph("The application has four main tabs:", styles['Normal']))
    story.append(Paragraph("• <b>Home</b> - Acquisition control and live waveform display", styles['Normal']))
    story.append(Paragraph("• <b>Calibration</b> - Energy calibration using Na-22 source", styles['Normal']))
    story.append(Paragraph("• <b>Energy Display</b> - Calibrated energy histograms", styles['Normal']))
    story.append(Paragraph("• <b>Timing Display</b> - Timing difference analysis", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Workflow
    story.append(Paragraph("<font size=14 color='#2a6ab0'><b>Typical Workflow</b></font>", styles['Heading2']))
    
    # Configure Trigger
    story.append(Paragraph("<b>1. Configure Trigger (Home Panel)</b>", styles['Normal']))
    story.append(Paragraph("   • Click 'Configure Trigger' button", styles['Normal']))
    story.append(Paragraph("   • Set up logic: A OR B OR C OR D (for coincidence detection)", styles['Normal']))
    story.append(Paragraph("   • Click 'Apply' to save", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    # Acquire Data
    story.append(Paragraph("<b>2. Acquire Data (Home Panel)</b>", styles['Normal']))
    story.append(Paragraph("   • Set optional limits: time limit and/or event count", styles['Normal']))
    story.append(Paragraph("   • Click 'Start Acquisition'", styles['Normal']))
    story.append(Paragraph("   • Monitor live waveforms (Red=A, Green=B, Blue=C, Orange=D)", styles['Normal']))
    story.append(Paragraph("   • Use 'Pause/Resume' or 'Restart' as needed", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    # Calibrate
    story.append(Paragraph("<b>3. Calibrate Energy (Calibration Panel)</b>", styles['Normal']))
    story.append(Paragraph("   <b>Prerequisites:</b> Na-22 source (511 keV and 1275 keV peaks)", styles['Normal']))
    story.append(Paragraph("   For each channel (A, B, C, D):", styles['Normal']))
    story.append(Paragraph("   1. Click 'Update All Histograms'", styles['Normal']))
    story.append(Paragraph("   2. Drag the <b>green region</b> over the 511 keV peak", styles['Normal']))
    story.append(Paragraph("   3. Drag the <b>blue region</b> over the 1275 keV peak", styles['Normal']))
    story.append(Paragraph("   4. Click 'Find Peaks'", styles['Normal']))
    story.append(Paragraph("   5. Click 'Calculate Calibration'", styles['Normal']))
    story.append(Paragraph("   6. Click 'Apply to [Channel]'", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Calibration Tips:</b>", styles['Normal']))
    story.append(Paragraph("   • Collect 1000+ events before calibrating", styles['Normal']))
    story.append(Paragraph("   • Use log scale to see peaks clearly", styles['Normal']))
    story.append(Paragraph("   • Peaks should be well-separated", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    # Analyze
    story.append(Paragraph("<b>4. Analyze Data</b>", styles['Normal']))
    story.append(Paragraph("   <b>Energy Display Panel:</b> View calibrated energy histograms", styles['Normal']))
    story.append(Paragraph("   <b>Timing Display Panel:</b> Analyze timing differences between channels", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Troubleshooting
    story.append(PageBreak())
    story.append(Paragraph("<font size=16 color='#1a5490'><b>Troubleshooting</b></font>", styles['Heading1']))
    
    story.append(Paragraph("<b>Scope Not Detected:</b>", styles['Normal']))
    story.append(Paragraph("   • Check USB connection", styles['Normal']))
    story.append(Paragraph("   • Verify scope is powered on", styles['Normal']))
    story.append(Paragraph("   • Install/reinstall PicoScope drivers", styles['Normal']))
    story.append(Paragraph("   • Try a different USB port", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>No Events Detected:</b>", styles['Normal']))
    story.append(Paragraph("   • Check signal connections", styles['Normal']))
    story.append(Paragraph("   • Verify trigger configuration", styles['Normal']))
    story.append(Paragraph("   • Check that signals exceed 5 mV threshold", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Application Crashes or Errors:</b>", styles['Normal']))
    story.append(Paragraph("   • Verify all cables are connected properly", styles['Normal']))
    story.append(Paragraph("   • Restart the scope and application", styles['Normal']))
    story.append(Paragraph("   • Reinstall PicoScope drivers if persistent", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Hardware Configuration
    story.append(Paragraph("<font size=16 color='#1a5490'><b>Hardware Configuration</b></font>", styles['Heading1']))
    story.append(Paragraph("The system is optimized for pulse detection with fixed settings:", styles['Normal']))
    story.append(Paragraph("• <b>Voltage Range:</b> 100 mV (all channels)", styles['Normal']))
    story.append(Paragraph("• <b>Coupling:</b> DC", styles['Normal']))
    story.append(Paragraph("• <b>Channels:</b> 4 (A, B, C, D)", styles['Normal']))
    story.append(Paragraph("• <b>Sample Rate:</b> Maximum available (typically 250 MS/s)", styles['Normal']))
    story.append(Paragraph("• <b>Capture Window:</b> 1 µs pre-trigger, 2 µs post-trigger (3 µs total)", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Trigger Settings:</b>", styles['Normal']))
    story.append(Paragraph("• Threshold: -5 mV", styles['Normal']))
    story.append(Paragraph("• Edge: Falling", styles['Normal']))
    story.append(Paragraph("• Logic: User-configurable (OR/AND combinations)", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # About
    story.append(Paragraph("<font size=16 color='#1a5490'><b>About Positron</b></font>", styles['Heading1']))
    story.append(Paragraph("Developed for nuclear physics laboratory experiments, specifically designed for positron annihilation lifetime spectroscopy (PALS) and related particle detection experiments.", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Key Features:</b>", styles['Normal']))
    story.append(Paragraph("• Real-time waveform display (4 channels)", styles['Normal']))
    story.append(Paragraph("• Event-mode acquisition (up to 10,000 events/s)", styles['Normal']))
    story.append(Paragraph("• Pulse analysis (CFD timing, energy integration)", styles['Normal']))
    story.append(Paragraph("• Energy calibration using standard sources", styles['Normal']))
    story.append(Paragraph("• Multiple analysis panels for visualization", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Technology:</b> PySide6 (Qt), PyQtGraph, NumPy, PicoSDK", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Compatible:</b> PicoScope 3000a, 6000a series", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("For updates and support, contact your lab supervisor.", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"✓ PDF created: {output_file}")
    return output_file

if __name__ == '__main__':
    create_simple_pdf()
