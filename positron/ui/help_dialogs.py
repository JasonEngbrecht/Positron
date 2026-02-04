"""
Help dialog system for Positron application.

Provides comprehensive help documentation for the application and each panel.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt


class HelpDialog(QDialog):
    """Base help dialog with HTML content display and navigation."""
    
    def __init__(self, parent=None, title: str = "Help", content: str = "", 
                 current_topic: str = "getting_started"):
        """
        Initialize help dialog.
        
        Args:
            parent: Parent widget
            title: Dialog window title
            content: HTML content to display
            current_topic: Current help topic identifier
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(750, 650)
        self.current_topic = current_topic
        
        # Layout
        layout = QVBoxLayout()
        
        # Navigation buttons at top
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self._create_nav_label())
        
        # Create navigation buttons
        self.nav_buttons = {}
        topics = [
            ("getting_started", "Getting Started"),
            ("home", "Home Panel"),
            ("energy", "Energy Display"),
            ("timing", "Timing Display"),
            ("calibration", "Calibration")
        ]
        
        for topic_id, topic_name in topics:
            btn = QPushButton(topic_name)
            btn.clicked.connect(lambda checked, t=topic_id: self._navigate_to(t))
            # Highlight current topic
            if topic_id == current_topic:
                btn.setStyleSheet("font-weight: bold;")
            nav_layout.addWidget(btn)
        
        layout.addLayout(nav_layout)
        
        # Text browser for HTML content
        self.browser = QTextBrowser()
        self.browser.setHtml(content)
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)
        
        # Close button at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_nav_label(self):
        """Create navigation label."""
        from PySide6.QtWidgets import QLabel
        label = QLabel("Navigate:")
        label.setStyleSheet("font-weight: bold;")
        return label
    
    def _navigate_to(self, topic: str):
        """Navigate to a different help topic."""
        # Map topics to their show functions
        topic_functions = {
            "getting_started": show_getting_started,
            "home": show_home_help,
            "energy": show_energy_display_help,
            "timing": show_timing_display_help,
            "calibration": show_calibration_help
        }
        
        if topic in topic_functions:
            # Close current dialog
            self.accept()
            # Show new help topic
            topic_functions[topic](self.parent())


def show_getting_started(parent=None):
    """Show Getting Started help dialog."""
    content = """
    <h1>Getting Started with Positron</h1>
    
    <h2>Overview</h2>
    <p>Positron is a data acquisition and analysis system for pulse detection experiments 
    using PicoScope oscilloscopes. It's designed specifically for positron annihilation 
    lifetime spectroscopy (PALS) and related nuclear physics experiments.</p>
    
    <h2>What Each Tab Does</h2>
    
    <h3>🏠 Home Tab</h3>
    <p>Your main control center for data acquisition:</p>
    <ul>
        <li><b>Configure triggers</b> to detect pulses from your detectors</li>
        <li><b>Start/pause/resume acquisition</b> to collect event data</li>
        <li><b>Monitor live waveforms</b> from all 4 channels in real-time</li>
        <li><b>Track statistics</b> including event count, acquisition time, and event rate</li>
        <li><b>Set auto-stop conditions</b> for unattended data collection</li>
    </ul>
    <p>Start here to collect data from your experiment. <i>Click "Home Panel" above for detailed help.</i></p>
    
    <h3>📊 Energy Display Tab</h3>
    <p>Visualize energy spectra from your detectors:</p>
    <ul>
        <li><b>View energy histograms</b> showing the distribution of pulse energies</li>
        <li><b>Compare multiple channels</b> with color-coded overlay plots</li>
        <li><b>Adjust binning</b> for optimal spectrum visualization</li>
        <li><b>Toggle log/linear scale</b> to see peaks clearly</li>
    </ul>
    <p>Use this after calibration to analyze your energy spectra. <i>Click "Energy Display" above for detailed help.</i></p>
    
    <h3>⏱️ Timing Display Tab</h3>
    <p>Analyze timing differences between detector channels:</p>
    <ul>
        <li><b>Plot timing differences</b> between any two channels</li>
        <li><b>Apply energy windows</b> to filter events by pulse energy</li>
        <li><b>Compare up to 4 timing pairs</b> simultaneously</li>
        <li><b>Measure timing resolution</b> for coincidence experiments</li>
    </ul>
    <p>Essential for PALS and coincidence timing measurements. <i>Click "Timing Display" above for detailed help.</i></p>
    
    <h3>🔬 Calibration Tab</h3>
    <p>Calibrate your detectors using known radioactive sources:</p>
    <ul>
        <li><b>View raw energy histograms</b> for each channel</li>
        <li><b>Identify calibration peaks</b> (e.g., Na-22: 511 keV and 1275 keV)</li>
        <li><b>Calculate calibration</b> to convert raw signals to keV</li>
        <li><b>Validate calibration quality</b> with automatic checks</li>
    </ul>
    <p>Perform calibration before analyzing energy spectra or applying energy windows. <i>Click "Calibration" above for detailed help.</i></p>
    
    <h2>Typical Workflow</h2>
    <ol>
        <li><b>Connect your PicoScope</b> and ensure all detectors are connected</li>
        <li><b>Home Tab:</b> Configure trigger conditions and start acquisition</li>
        <li><b>Calibration Tab:</b> Use a calibration source (e.g., Na-22) to calibrate energy scales</li>
        <li><b>Energy Display Tab:</b> Verify your calibration and examine energy spectra</li>
        <li><b>Timing Display Tab:</b> Analyze coincidence timing with optional energy filtering</li>
        <li><b>Home Tab:</b> Collect your experimental data with optimized settings</li>
    </ol>
    
    <h2>Quick Tips</h2>
    <ul>
        <li>Always calibrate your detectors before analyzing data</li>
        <li>Use pause/resume to reconfigure triggers without losing data</li>
        <li>Energy filtering in Timing Display requires calibrated channels</li>
        <li>Set auto-stop conditions for long overnight acquisitions</li>
        <li>All analysis panels update automatically while acquisition is running</li>
    </ul>
    
    <p><b>Use the navigation buttons above to jump to detailed help for each panel.</b></p>
    """
    
    dialog = HelpDialog(parent, "Getting Started - Positron", content, "getting_started")
    dialog.exec()


def show_home_help(parent=None):
    """Show Home panel help dialog."""
    content = """
    <h1>Home Panel Help</h1>
    
    <p><i>💡 Tip: Use the navigation buttons above to view help for other panels.</i></p>
    
    <h2>Purpose</h2>
    <p>The Home panel is your primary control center for data acquisition. Use it to 
    configure hardware triggers, control data collection, and monitor live waveforms 
    from all four detector channels.</p>
    
    <h2>Main Features</h2>
    
    <h3>1. Trigger Configuration</h3>
    <p><b>Configure Triggers Button:</b> Opens the trigger configuration dialog where you can:</p>
    <ul>
        <li>Set up to 4 trigger conditions (combined with OR logic)</li>
        <li>Select which channels must fire together (AND logic within each condition)</li>
        <li>Example: "A AND B" OR "C AND D" will trigger when A and B fire together, 
            OR when C and D fire together</li>
    </ul>
    <p><b>Trigger Settings:</b> Hardware settings are pre-optimized:</p>
    <ul>
        <li>Threshold: -5 mV (for negative-going pulses)</li>
        <li>Edge: Falling (pulse goes negative)</li>
        <li>Hysteresis: 10 ADC counts (noise rejection)</li>
    </ul>
    <p><i>Note: You can reconfigure triggers while paused without losing acquired data.</i></p>
    
    <h3>2. Acquisition Control</h3>
    <p><b>Start/Pause/Resume Button:</b></p>
    <ul>
        <li><b>Start:</b> Begin data acquisition with current trigger settings</li>
        <li><b>Pause:</b> Temporarily stop acquisition (data is preserved)</li>
        <li><b>Resume:</b> Continue acquisition, adding to existing event count</li>
    </ul>
    <p><b>Restart Button:</b></p>
    <ul>
        <li>Stop acquisition completely</li>
        <li>Clear all accumulated data and reset counters</li>
        <li>Start fresh with empty event storage</li>
    </ul>
    
    <h3>3. Live Waveform Display</h3>
    <p>Shows the most recent triggered waveforms from all channels:</p>
    <ul>
        <li><b>Red:</b> Channel A</li>
        <li><b>Green:</b> Channel B</li>
        <li><b>Blue:</b> Channel C</li>
        <li><b>Orange:</b> Channel D</li>
    </ul>
    <p><b>Time axis:</b> Nanoseconds (ns), trigger occurs at time = 0</p>
    <p><b>Voltage axis:</b> Millivolts (mV), baseline near 0 mV</p>
    <p><b>Update rate:</b> 3 Hz to maintain responsive UI during high-rate acquisition</p>
    
    <h3>4. Acquisition Statistics</h3>
    <p>Real-time information about your data collection:</p>
    <ul>
        <li><b>Events:</b> Total number of triggered events captured</li>
        <li><b>Time:</b> Elapsed acquisition time (HH:MM:SS), excludes paused periods</li>
        <li><b>Rate:</b> Current event rate (events per second)</li>
    </ul>
    <p><i>Note: Resume adds to existing counts, Restart clears everything.</i></p>
    
    <h3>5. Auto-Stop Presets</h3>
    <p>Set conditions to automatically stop acquisition:</p>
    <ul>
        <li><b>Time Limit:</b> Stop after specified hours:minutes:seconds</li>
        <li><b>Event Count Limit:</b> Stop after collecting specified number of events</li>
        <li><b>Both:</b> Stop when either condition is met</li>
        <li><b>Neither:</b> Manual control only</li>
    </ul>
    <p>Useful for overnight acquisitions or collecting specific dataset sizes.</p>
    
    <h2>Hardware Details</h2>
    <h3>Optimized Settings (Pre-configured)</h3>
    <ul>
        <li><b>Voltage Range:</b> 100 mV on all channels</li>
        <li><b>Coupling:</b> DC</li>
        <li><b>Sample Rate:</b> Maximum available (250 MS/s on PS3406D)</li>
        <li><b>Capture Window:</b> 3 µs total (1 µs pre-trigger, 2 µs post-trigger)</li>
        <li><b>Batch Size:</b> 10 waveforms captured per batch for efficiency</li>
    </ul>
    
    <h2>Data Processing</h2>
    <p>Behind the scenes, each triggered waveform is analyzed in real-time:</p>
    <ul>
        <li><b>Baseline Calculation:</b> Mean of pre-trigger samples</li>
        <li><b>CFD Timing:</b> Constant Fraction Discrimination at 50% threshold</li>
        <li><b>Energy Integration:</b> Baseline-corrected integral (raw units: mV·ns)</li>
        <li><b>Pulse Detection:</b> Amplitude threshold ≥ 5 mV</li>
    </ul>
    <p>Processed event data is stored in memory (up to 1 million events) and available 
    for analysis in other tabs. See the <b>Energy Display</b> and <b>Timing Display</b> help for analysis options.</p>
    
    <h2>Best Practices</h2>
    <ul>
        <li>Test your trigger logic before long acquisitions</li>
        <li>Monitor the event rate to ensure triggers are working correctly</li>
        <li>Use Pause instead of Restart to reconfigure triggers without losing data</li>
        <li>Set realistic auto-stop conditions for unattended operation</li>
        <li>Watch the live waveforms to verify pulse quality and baseline stability</li>
    </ul>
    
    <h2>What's Next?</h2>
    <p>After acquiring data:</p>
    <ul>
        <li>Go to <b>Calibration</b> panel to calibrate your detectors</li>
        <li>View spectra in <b>Energy Display</b> panel</li>
        <li>Analyze timing in <b>Timing Display</b> panel</li>
    </ul>
    """
    
    dialog = HelpDialog(parent, "Home Panel - Help", content, "home")
    dialog.exec()


def show_energy_display_help(parent=None):
    """Show Energy Display panel help dialog."""
    content = """
    <h1>Energy Display Panel Help</h1>
    
    <p><i>💡 Tip: Use the navigation buttons above to view help for other panels.</i></p>
    
    <h2>Purpose</h2>
    <p>The Energy Display panel visualizes energy spectra from your detectors, showing 
    the distribution of pulse energies across all channels. This is essential for 
    identifying radioactive source peaks, analyzing detector response, and verifying 
    energy calibration.</p>
    
    <p><b>⚠️ Important:</b> Channels must be calibrated before they can be displayed. 
    See the <b>Calibration</b> help for details.</p>
    
    <h2>Main Features</h2>
    
    <h3>1. Multi-Channel Energy Histogram</h3>
    <p>Displays overlaid energy spectra from up to 4 channels:</p>
    <ul>
        <li><b>Red:</b> Channel A</li>
        <li><b>Green:</b> Channel B</li>
        <li><b>Blue:</b> Channel C</li>
        <li><b>Orange:</b> Channel D</li>
    </ul>
    <p><b>X-axis:</b> Energy in keV (after calibration)</p>
    <p><b>Y-axis:</b> Counts per bin</p>
    
    <h3>2. Channel Selection</h3>
    <p>Four checkboxes allow you to show/hide individual channels:</p>
    <ul>
        <li>Enable only the channels you want to compare</li>
        <li>Uncalibrated channels are automatically disabled</li>
        <li>Event counts shown for each channel</li>
    </ul>
    
    <h3>3. Y-Axis Scale Toggle</h3>
    <p><b>Logarithmic Scale (Default):</b></p>
    <ul>
        <li>Better for viewing both strong and weak peaks</li>
        <li>Compresses large count variations</li>
        <li>Recommended for initial analysis</li>
    </ul>
    <p><b>Linear Scale:</b></p>
    <ul>
        <li>Shows true count ratios</li>
        <li>Better for quantitative peak analysis</li>
        <li>May hide weak features</li>
    </ul>
    
    <h3>4. Binning Options</h3>
    <p><b>Automatic Mode (Default):</b></p>
    <ul>
        <li>1000 bins with auto-ranging based on data</li>
        <li>Updates automatically as data is acquired</li>
        <li>Good for most applications</li>
    </ul>
    <p><b>Manual Mode:</b></p>
    <ul>
        <li>Specify energy range (Min/Max in keV)</li>
        <li>Set number of bins (20-2000)</li>
        <li>Fine control for detailed peak analysis</li>
        <li>Click "Apply" to update histogram</li>
    </ul>
    
    <h3>5. Auto-Update</h3>
    <p>The histogram automatically refreshes every 2 seconds when:</p>
    <ul>
        <li>This tab is visible (active)</li>
        <li>Data acquisition is running (see <b>Home Panel</b> help)</li>
        <li>New events have been collected</li>
    </ul>
    <p>Updates pause when you switch to another tab to save CPU resources.</p>
    
    <h2>Typical Use Cases</h2>
    
    <h3>Verifying Calibration</h3>
    <ol>
        <li>Acquire data with a known source (e.g., Na-22) - see <b>Home Panel</b></li>
        <li>Perform calibration in <b>Calibration</b> tab</li>
        <li>Return to Energy Display</li>
        <li>Verify peaks appear at correct energies (511 keV, 1275 keV)</li>
    </ol>
    
    <h3>Comparing Detector Response</h3>
    <ol>
        <li>Enable multiple channels</li>
        <li>Observe peak positions and widths</li>
        <li>Identify channels needing recalibration</li>
        <li>Compare energy resolution (FWHM of peaks)</li>
    </ol>
    
    <h3>Spectrum Analysis</h3>
    <ol>
        <li>Use logarithmic scale to identify all peaks</li>
        <li>Switch to linear scale for peak ratio analysis</li>
        <li>Adjust manual binning for detailed peak shapes</li>
        <li>Use narrow energy range to zoom on region of interest</li>
    </ol>
    
    <h2>Tips for Best Results</h2>
    <ul>
        <li><b>Start with automatic binning</b> to see full spectrum</li>
        <li><b>Use logarithmic scale</b> to identify all peaks, including weak ones</li>
        <li><b>Switch to linear scale</b> for quantitative peak comparisons</li>
        <li><b>Use manual binning</b> to zoom in on specific energy regions</li>
        <li><b>Compare multiple channels</b> to verify consistent calibration</li>
        <li><b>Monitor during acquisition</b> to ensure data quality</li>
    </ul>
    
    <h2>Troubleshooting</h2>
    <p><b>Channel checkbox is disabled:</b></p>
    <ul>
        <li>Channel needs calibration in <b>Calibration</b> tab</li>
        <li>No events detected on that channel</li>
    </ul>
    <p><b>No data displayed:</b></p>
    <ul>
        <li>Verify acquisition has been started in <b>Home</b> tab</li>
        <li>Check that events are being collected (Home tab statistics)</li>
        <li>Ensure at least one channel is enabled and calibrated</li>
    </ul>
    <p><b>Peaks at wrong energies:</b></p>
    <ul>
        <li>Return to <b>Calibration</b> tab and recalibrate</li>
        <li>Verify calibration peaks were selected correctly</li>
    </ul>
    """
    
    dialog = HelpDialog(parent, "Energy Display Panel - Help", content, "energy")
    dialog.exec()


def show_timing_display_help(parent=None):
    """Show Timing Display panel help dialog."""
    content = """
    <h1>Timing Display Panel Help</h1>
    
    <p><i>💡 Tip: Use the navigation buttons above to view help for other panels.</i></p>
    
    <h2>Purpose</h2>
    <p>The Timing Display panel analyzes time differences between detector channels, 
    essential for coincidence experiments like PALS (Positron Annihilation Lifetime 
    Spectroscopy). It shows the time distribution of events where two channels 
    detect pulses, with optional energy filtering.</p>
    
    <p><b>⚠️ Note:</b> Energy filtering requires calibrated channels. See <b>Calibration</b> help for details.</p>
    
    <h2>Main Features</h2>
    
    <h3>1. Multi-Slot Timing Analysis</h3>
    <p>Analyze up to 4 channel pairs simultaneously:</p>
    <ul>
        <li><b>Blue curve:</b> Slot 1 timing difference</li>
        <li><b>Orange curve:</b> Slot 2 timing difference</li>
        <li><b>Green curve:</b> Slot 3 timing difference</li>
        <li><b>Red curve:</b> Slot 4 timing difference</li>
    </ul>
    <p>Each slot independently configures a channel pair and energy windows.</p>
    
    <h3>2. Channel Pair Selection</h3>
    <p>For each slot, select two channels:</p>
    <ul>
        <li><b>Channel 1:</b> Start time reference</li>
        <li><b>Channel 2:</b> Stop time reference</li>
        <li><b>Time difference = Channel 1 time - Channel 2 time</b></li>
    </ul>
    <p>Example: If Channel 1 = A and Channel 2 = B, the histogram shows (A time - B time)</p>
    
    <h3>3. Energy Filtering</h3>
    <p>Filter events by pulse energy for each channel:</p>
    <ul>
        <li><b>Channel 1 Energy Window:</b> Min and Max energy in keV</li>
        <li><b>Channel 2 Energy Window:</b> Min and Max energy in keV</li>
        <li>Only events where BOTH channels have pulses within their windows are included</li>
        <li>Requires calibrated channels (see <b>Calibration</b> panel)</li>
    </ul>
    <p><i>Note: Energy filtering allows you to select specific transitions or reject 
    scattered events.</i></p>
    
    <h3>4. Timing Histogram</h3>
    <p><b>X-axis:</b> Time difference in nanoseconds (ns)</p>
    <p><b>Y-axis:</b> Counts per bin (linear or log scale)</p>
    <p>The histogram shows the distribution of time differences between channel pairs.</p>
    
    <h3>5. Binning Options</h3>
    <p><b>Automatic Mode (Default):</b></p>
    <ul>
        <li>1000 bins with auto-ranging based on data</li>
        <li>Adapts as timing distribution evolves</li>
        <li>Good for initial exploration</li>
    </ul>
    <p><b>Manual Mode:</b></p>
    <ul>
        <li>Specify time range (Min/Max in ns)</li>
        <li>Set number of bins (20-2000)</li>
        <li>Fine control for measuring timing resolution</li>
        <li>Click "Apply" to update histogram</li>
    </ul>
    
    <h3>6. Auto-Update</h3>
    <p>Histograms automatically refresh every 2 seconds when:</p>
    <ul>
        <li>This tab is visible</li>
        <li>Data acquisition is running (see <b>Home Panel</b>)</li>
        <li>Pauses when you switch to another tab</li>
    </ul>
    
    <h2>Typical Use Cases</h2>
    
    <h3>PALS Lifetime Measurement</h3>
    <ol>
        <li>Channel A: Start detector (source/positron pulse)</li>
        <li>Channel B: Stop detector (511 keV annihilation gamma)</li>
        <li>Set Channel B energy window: 480-540 keV (511 keV peak)</li>
        <li>Time histogram shows lifetime spectrum</li>
    </ol>
    
    <h3>Coincidence Timing Resolution</h3>
    <ol>
        <li>Use two detectors viewing same source (e.g., Na-22)</li>
        <li>Set energy windows for 511 keV on both channels</li>
        <li>Timing histogram shows prompt coincidence peak</li>
        <li>Peak width (FWHM) = timing resolution</li>
    </ol>
    
    <h3>Multi-Transition Analysis</h3>
    <ol>
        <li>Slot 1: 511 keV coincidences</li>
        <li>Slot 2: 1275 keV coincidences</li>
        <li>Slot 3: 511-1275 keV coincidences</li>
        <li>Compare timing characteristics of different transitions</li>
    </ol>
    
    <h2>Understanding Time Differences</h2>
    
    <h3>Positive vs Negative Times</h3>
    <p>The time difference (t1 - t2) can be positive or negative:</p>
    <ul>
        <li><b>Positive:</b> Channel 1 pulse occurred AFTER Channel 2</li>
        <li><b>Negative:</b> Channel 1 pulse occurred BEFORE Channel 2</li>
        <li><b>Near zero:</b> Pulses nearly simultaneous (prompt coincidence)</li>
    </ul>
    
    <h2>Best Practices</h2>
    <ul>
        <li><b>Calibrate first:</b> Perform energy calibration before using energy filters</li>
        <li><b>Start with wide windows:</b> Use automatic binning and no energy filtering initially</li>
        <li><b>Refine gradually:</b> Narrow energy windows to select specific transitions</li>
        <li><b>Compare multiple slots:</b> Use different slots to test different filter conditions</li>
        <li><b>Monitor event counts:</b> Check that sufficient events pass your filters</li>
        <li><b>Use manual binning:</b> Zoom in on prompt peak to measure timing resolution</li>
    </ul>
    
    <h2>Troubleshooting</h2>
    <p><b>No data in histogram:</b></p>
    <ul>
        <li>Verify both channels are selected and different</li>
        <li>Check that both channels are calibrated (for energy filtering)</li>
        <li>Widen energy windows or disable filtering</li>
        <li>Ensure sufficient events collected (check <b>Home</b> tab)</li>
    </ul>
    <p><b>Energy windows not available:</b></p>
    <ul>
        <li>One or both channels need calibration (<b>Calibration</b> tab)</li>
        <li>Calibration required for energy filtering</li>
    </ul>
    """
    
    dialog = HelpDialog(parent, "Timing Display Panel - Help", content, "timing")
    dialog.exec()


def show_calibration_help(parent=None):
    """Show Calibration panel help dialog."""
    content = """
    <h1>Calibration Panel Help</h1>
    
    <p><i>💡 Tip: Use the navigation buttons above to view help for other panels.</i></p>
    
    <h2>Purpose</h2>
    <p>The Calibration panel converts raw pulse energy measurements (mV·ns) to 
    calibrated energies (keV) using known radioactive source peaks. Accurate calibration 
    is essential for energy spectrum analysis and applying energy windows in timing 
    measurements.</p>
    
    <p><b>Why calibrate?</b> This enables you to use the <b>Energy Display</b> and 
    <b>Timing Display</b> panels with meaningful energy units.</p>
    
    <h2>Why Calibration Is Necessary</h2>
    <p>Each detector has unique characteristics:</p>
    <ul>
        <li>PMT gain variations</li>
        <li>Scintillator light output differences</li>
        <li>Electronic amplification differences</li>
        <li>Cable length effects</li>
    </ul>
    <p>Calibration establishes the relationship between detector output and actual 
    photon energy, enabling quantitative analysis.</p>
    
    <h2>Calibration Process Overview</h2>
    <ol>
        <li><b>Acquire calibration data</b> with known source (<b>Home</b> tab)</li>
        <li><b>Display energy histograms</b> (raw mV·ns units)</li>
        <li><b>Identify calibration peaks</b> in the spectrum</li>
        <li><b>Calculate calibration parameters</b> (gain and offset)</li>
        <li><b>Apply calibration</b> to convert future measurements to keV</li>
    </ol>
    
    <h2>Main Features</h2>
    
    <h3>1. Channel Tabs</h3>
    <p>Independent calibration for each detector channel:</p>
    <ul>
        <li><b>Channel A, B, C, D tabs:</b> Switch between channels</li>
        <li>Each channel has its own histogram and calibration controls</li>
        <li>Calibration status shown at top of each tab</li>
    </ul>
    
    <h3>2. Energy Histogram Display</h3>
    <p>Shows uncalibrated energy spectrum:</p>
    <ul>
        <li><b>X-axis:</b> Raw energy in mV·ns</li>
        <li><b>Y-axis:</b> Counts per bin (logarithmic scale)</li>
        <li>Logarithmic scale helps visualize both strong and weak peaks</li>
    </ul>
    <p><b>Update Histogram Button:</b> Refresh with latest acquired data</p>
    
    <h3>3. Peak Region Selection</h3>
    <p>Interactive green and blue shaded regions for peak identification:</p>
    <ul>
        <li><b>Green region:</b> Lower energy peak (e.g., 511 keV for Na-22)</li>
        <li><b>Blue region:</b> Higher energy peak (e.g., 1275 keV for Na-22)</li>
        <li><b>Drag edges:</b> Adjust region boundaries</li>
        <li><b>Drag center:</b> Move entire region</li>
    </ul>
    <p>Position regions over the peaks you want to use for calibration.</p>
    
    <h3>4. Find Peaks Button</h3>
    <p>Automatically determines peak centers within selected regions:</p>
    <ul>
        <li>Uses weighted mean (center-of-mass) algorithm</li>
        <li>Displays calculated peak positions in controls</li>
        <li>Fast and robust method</li>
    </ul>
    
    <h3>5. Known Energy Inputs</h3>
    <p>Enter the true photon energies for calibration:</p>
    <ul>
        <li><b>Green Peak Energy:</b> Energy in keV of lower peak</li>
        <li><b>Blue Peak Energy:</b> Energy in keV of higher peak</li>
        <li><b>Common values for Na-22:</b> 511 keV and 1275 keV</li>
        <li>Can be edited for other calibration sources</li>
    </ul>
    
    <h3>6. Calculate & Apply Calibration</h3>
    <p><b>Calculate Calibration:</b> Computes linear calibration relationship</p>
    <p><b>Apply Calibration:</b> Saves and activates the calibration</p>
    <ul>
        <li>Enables channel in <b>Energy Display</b> and <b>Timing Display</b></li>
        <li>Calibration persists across sessions</li>
    </ul>
    
    <h2>Quick Start Procedure</h2>
    
    <ol>
        <li><b>Acquire Data:</b> Go to <b>Home</b> tab, configure trigger "A OR B OR C OR D", 
            collect 1000+ events with Na-22 source</li>
        <li><b>Load Histograms:</b> Click "Update All Histograms"</li>
        <li><b>For Each Channel:</b>
            <ul>
                <li>Drag green region over 511 keV peak</li>
                <li>Drag blue region over 1275 keV peak</li>
                <li>Click "Find Peaks"</li>
                <li>Click "Calculate Calibration"</li>
                <li>Click "Apply Calibration"</li>
            </ul>
        </li>
        <li><b>Verify:</b> Check calibration in <b>Energy Display</b> tab</li>
    </ol>
    
    <h2>Validation Checks</h2>
    <p>The calibration system performs automatic quality checks:</p>
    <ul>
        <li><b>Minimum events:</b> At least 100 events required</li>
        <li><b>Peak separation:</b> Peaks must differ by >10%</li>
        <li><b>Peak order:</b> Blue peak must be higher energy than green</li>
        <li><b>Reasonable gain:</b> Gain must be positive</li>
        <li><b>Peak ratio:</b> Energy ratio should be between 1.5 and 4.0</li>
    </ul>
    <p>Warnings indicate potential calibration issues that should be investigated.</p>
    
    <h2>Calibration Sources</h2>
    
    <h3>Na-22 (Recommended)</h3>
    <ul>
        <li><b>Photon energies:</b> 511 keV and 1275 keV</li>
        <li><b>Advantages:</b> Two well-separated peaks</li>
        <li><b>Half-life:</b> 2.6 years</li>
    </ul>
    
    <h3>Alternatives</h3>
    <ul>
        <li><b>Cs-137:</b> 662 keV (single peak)</li>
        <li><b>Co-60:</b> 1173 keV and 1332 keV</li>
    </ul>
    
    <h2>Best Practices</h2>
    <ul>
        <li><b>Collect sufficient statistics:</b> 5000+ events per channel ideal</li>
        <li><b>Use consistent geometry:</b> Keep source position constant</li>
        <li><b>Allow warm-up time:</b> Check detector stability before calibrating</li>
        <li><b>Recalibrate periodically:</b> PMT gain can drift over time</li>
        <li><b>Verify in Energy Display:</b> Check peaks appear at correct energies</li>
    </ul>
    
    <h2>Troubleshooting</h2>
    
    <p><b>Peaks Not Visible:</b></p>
    <ul>
        <li>Acquire more events (need 1000+ per channel)</li>
        <li>Verify source is properly positioned</li>
        <li>Check detector high voltage is on</li>
        <li>Verify trigger settings in <b>Home</b> panel allow channel to trigger</li>
    </ul>
    
    <p><b>Calculate Calibration Fails:</b></p>
    <ul>
        <li>Review validation error messages</li>
        <li>Check peak positions are reasonable and separated</li>
        <li>Verify known energies are correct</li>
        <li>Try adjusting region positions and finding peaks again</li>
    </ul>
    
    <h2>After Calibration</h2>
    <p>Once channels are calibrated:</p>
    <ul>
        <li><b>Energy Display</b> shows spectra in keV</li>
        <li><b>Timing Display</b> allows energy window filtering</li>
        <li>Calibration persists until recalibrated</li>
    </ul>
    """
    
    dialog = HelpDialog(parent, "Calibration Panel - Help", content, "calibration")
    dialog.exec()
