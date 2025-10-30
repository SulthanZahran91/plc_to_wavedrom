"""Help dialog showing comprehensive application documentation."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QScrollArea,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtGui import QFont


class HelpDialog(QDialog):
    """Dialog displaying comprehensive application documentation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("PLC Log Visualizer - Help")
        self.setMinimumSize(800, 700)
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different help sections
        tabs = QTabWidget()
        tabs.addTab(self._create_getting_started_tab(), "🚀 Getting Started")
        tabs.addTab(self._create_file_management_tab(), "📁 File Management")
        tabs.addTab(self._create_home_view_tab(), "🏠 Home View")
        tabs.addTab(self._create_timing_diagram_tab(), "⚙️ Timing Diagram")
        tabs.addTab(self._create_log_table_tab(), "📋 Log Table")
        tabs.addTab(self._create_map_viewer_tab(), "🗺️ Map Viewer")
        tabs.addTab(self._create_signal_intervals_tab(), "📈 Signal Intervals")
        tabs.addTab(self._create_multi_view_tab(), "🔀 Multi-View System")
        tabs.addTab(self._create_shortcuts_tab(), "⌨️ Shortcuts")
        tabs.addTab(self._create_tips_tab(), "💡 Tips & Troubleshooting")
        
        layout.addWidget(tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _create_getting_started_tab(self) -> QWidget:
        """Create the Getting Started tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Welcome to PLC Log Visualizer!")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        intro = QLabel(
            "PLC Log Visualizer is a powerful tool for analyzing and visualizing Programmable Logic Controller (PLC) log data. "
            "Whether you're debugging control systems, analyzing timing issues, or understanding system behavior, "
            "this application provides multiple synchronized views to help you gain insights quickly."
        )
        intro.setWordWrap(True)
        content_layout.addWidget(intro)
        
        content_layout.addSpacing(10)
        
        purpose = QLabel(
            "<b>What Can You Do?</b><br><br>"
            "• <b>Visualize Signal Changes:</b> See waveforms and timing relationships<br><br>"
            "• <b>Search Log Entries:</b> Filter and find specific events quickly<br><br>"
            "• <b>Analyze Intervals:</b> Understand signal state durations and patterns<br><br>"
            "• <b>Map States:</b> Visualize PLC states on custom diagrams<br><br>"
            "• <b>Compare Views:</b> Work with multiple synchronized perspectives"
        )
        purpose.setWordWrap(True)
        purpose.setTextFormat(Qt.RichText)
        content_layout.addWidget(purpose)
        
        content_layout.addSpacing(10)
        
        workflow = QLabel(
            "<b>Quick Start Workflow:</b><br><br>"
            "<b>1. Load Data</b><br>"
            "   • Drag and drop log files onto the <b>Home</b> tab<br>"
            "   • Or click to browse for files<br>"
            "   • The app will parse and display statistics<br><br>"
            
            "<b>2. Open Views</b><br>"
            "   • Click the <b>⚙️ Timing Diagram</b> button to see waveforms<br>"
            "   • Click the <b>📋 Log Table</b> button to see entries<br>"
            "   • Click the <b>🗺️ Map Viewer</b> button to visualize states<br>"
            "   • Or use keyboard shortcuts: <b>Ctrl+T</b>, <b>Ctrl+L</b>, <b>Ctrl+M</b><br><br>"
            
            "<b>3. Analyze</b><br>"
            "   • Pan and zoom in the timing diagram<br>"
            "   • Click signals to see interval histograms<br>"
            "   • Filter and search in the log table<br>"
            "   • Use bookmarks to mark important moments<br><br>"
            
            "<b>4. Compare</b><br>"
            "   • Split views by dragging tabs to screen edges<br>"
            "   • Use the <b>🔗 Sync Views</b> button to align times<br>"
            "   • Work with up to 4 panes simultaneously"
        )
        workflow.setWordWrap(True)
        workflow.setTextFormat(Qt.RichText)
        content_layout.addWidget(workflow)
        
        content_layout.addSpacing(10)
        
        requirements = QLabel(
            "<b>System Requirements:</b><br>"
            "• Python 3.8 or higher<br>"
            "• PySide6 (Qt for Python)<br>"
            "• Supported on Windows, macOS, and Linux<br>"
            "• Wayland-compatible for modern Linux desktops"
        )
        requirements.setWordWrap(True)
        requirements.setTextFormat(Qt.RichText)
        content_layout.addWidget(requirements)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_file_management_tab(self) -> QWidget:
        """Create the File Management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("File Management")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>How to Upload Files:</b><br><br>"
            
            "<b>Method 1: Drag and Drop</b><br>"
            "1. Open the <b>🏠 Home</b> tab<br>"
            "2. Drag one or more log files from your file manager<br>"
            "3. Drop them onto the upload widget<br>"
            "4. Parsing begins automatically<br><br>"
            
            "<b>Method 2: Browse</b><br>"
            "1. Click anywhere in the upload widget<br>"
            "2. A file browser dialog will open<br>"
            "3. Select one or more log files<br>"
            "4. Click <b>Open</b> to start parsing<br><br>"
            
            "<b>Supported File Formats:</b><br>"
            "• Plain text log files (.log, .txt)<br>"
            "• CSV files with timestamp columns<br>"
            "• Custom PLC log formats<br>"
            "• Multiple files can be loaded together for combined analysis<br><br>"
            
            "<b>Multiple File Handling:</b><br>"
            "• Load multiple files at once—they'll be merged chronologically<br>"
            "• Each file is parsed independently and then aggregated<br>"
            "• Failed files won't block successful ones<br>"
            "• All loaded files appear in the file list widget<br><br>"
            
            "<b>Parsing Process:</b><br>"
            "1. Files are validated and checked for readability<br>"
            "2. A progress bar shows parsing status<br>"
            "3. Each file is parsed for timestamp and signal data<br>"
            "4. Statistics are computed and displayed<br>"
            "5. Views are automatically updated with new data<br><br>"
            
            "<b>File List Widget:</b><br>"
            "The right side of the Home tab shows all loaded files:<br>"
            "• <b>File name</b> with full path in tooltip<br>"
            "• <b>Parse status</b> (success/failure)<br>"
            "• <b>Progress indicators</b> during parsing<br>"
            "• <b>🗑️ Remove button</b> to unload individual files<br><br>"
            
            "<b>Statistics Panel:</b><br>"
            "After successful parsing, the statistics widget displays:<br>"
            "• <b>Total log entries</b> parsed<br>"
            "• <b>Number of signals</b> detected<br>"
            "• <b>Time range</b> of the data<br>"
            "• <b>Error count</b> if parsing issues occurred<br><br>"
            
            "<b>Clearing Data:</b><br>"
            "• Click the <b>Clear</b> button in the header to reset everything<br>"
            "• Or use the 🗑️ button on individual files in the file list<br>"
            "• Clearing closes all open views and frees memory"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_home_view_tab(self) -> QWidget:
        """Create the Home View tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Home View")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>What is the Home View?</b><br>"
            "The Home View is the main landing page of the application, displayed as the first tab. "
            "It's your starting point for loading data and opening different analysis views.<br><br>"
            
            "<b>Layout Overview:</b><br>"
            "The Home tab is divided into sections:<br><br>"
            
            "<b>1. Upload Widget (Top Left)</b><br>"
            "• Large drop zone for drag-and-drop files<br>"
            "• Click to browse for files<br>"
            "• Shows current status (idle, parsing, loaded)<br>"
            "• Visual feedback during file operations<br><br>"
            
            "<b>2. Statistics Widget (Middle Left)</b><br>"
            "Displays key metrics after parsing:<br>"
            "• Total entries in the log<br>"
            "• Number of unique signals<br>"
            "• Time range (start to end)<br>"
            "• Parse errors (if any)<br><br>"
            
            "<b>3. File List Widget (Right Side)</b><br>"
            "Shows all loaded files with:<br>"
            "• File names and paths<br>"
            "• Status indicators (✓ success, ✗ error)<br>"
            "• Progress bars during parsing<br>"
            "• Individual remove buttons<br><br>"
            
            "<b>4. Progress Bar (Center)</b><br>"
            "• Appears during file parsing<br>"
            "• Shows which file is currently being processed<br>"
            "• Displays overall progress percentage<br>"
            "• Automatically hidden when complete<br><br>"
            
            "<b>5. View Buttons (Bottom)</b><br>"
            "Four large buttons to open different views:<br>"
            "• <b>⚙️ Timing Diagram</b> - See signal waveforms<br>"
            "• <b>📋 Log Table</b> - Browse log entries<br>"
            "• <b>🗺️ Map Viewer</b> - Visualize states<br>"
            "• <b>📈 Signal Intervals</b> - Analyze signal changes<br><br>"
            
            "<b>Working with Home View:</b><br>"
            "• The Home View stays open—it's always your first tab<br>"
            "• You can split it alongside other views if needed<br>"
            "• Use it to check stats while analyzing in other views<br>"
            "• Return to it to load additional files<br><br>"
            
            "<b>Tips:</b><br>"
            "• Keep the Home tab visible to monitor overall stats<br>"
            "• Reload files by clicking Clear and re-uploading<br>"
            "• The view buttons create new tabs in the active pane"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_timing_diagram_tab(self) -> QWidget:
        """Create the Timing Diagram View tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Timing Diagram View")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>What Does It Show?</b><br>"
            "The Timing Diagram displays signal waveforms over time, showing when signals change state. "
            "This view is ideal for understanding timing relationships and debugging sequence issues.<br><br>"
            
            "<b>Visual Elements:</b><br>"
            "• <b>Signal Names</b> - Listed on the left side<br>"
            "• <b>Waveforms</b> - Horizontal lines showing signal states over time<br>"
            "• <b>Time Axis</b> - Shows timestamps along the bottom<br>"
            "• <b>State Changes</b> - Vertical transitions between HIGH/LOW<br>"
            "• <b>Grid Lines</b> - Optional time reference markers<br><br>"
            
            "<b>Navigation:</b><br><br>"
            
            "<b>Pan:</b><br>"
            "• Click and drag horizontally to scroll through time<br>"
            "• Click and drag vertically to scroll through signals<br>"
            "• Use scrollbars for precise positioning<br><br>"
            
            "<b>Zoom:</b><br>"
            "• Mouse wheel to zoom in/out on time axis<br>"
            "• Ctrl+Mouse wheel for vertical zooming<br>"
            "• Double-click to fit view<br>"
            "• Zoom controls in the toolbar<br><br>"
            
            "<b>Signal Management:</b><br><br>"
            
            "<b>Filtering:</b><br>"
            "• Type in the filter box to search signals by name<br>"
            "• Only matching signals are displayed<br>"
            "• Clear filter to show all signals again<br><br>"
            
            "<b>Selection:</b><br>"
            "• Click any signal name to select it<br>"
            "• Click the waveform to see details<br>"
            "• Double-click a signal to open interval analysis<br><br>"
            
            "<b>Interval Analysis:</b><br>"
            "• Click or double-click a signal to view its interval histogram<br>"
            "• Shows how long the signal stayed in each state<br>"
            "• Helps identify patterns and anomalies<br><br>"
            
            "<b>Time Range Selection:</b><br>"
            "• The visible time range can be manually adjusted<br>"
            "• Limited to 5 minutes of data at once for performance<br>"
            "• Pan to different time ranges as needed<br><br>"
            
            "<b>Integration with Other Views:</b><br>"
            "• Use <b>🔗 Sync Views</b> button to align with other views<br>"
            "• Changes to viewport propagate to synchronized views<br>"
            "• Bookmarks jump to specific times in this view<br><br>"
            
            "<b>Tips:</b><br>"
            "• Look for timing relationships between related signals<br>"
            "• Use zoom to see rapid transitions clearly<br>"
            "• Filter to focus on specific subsystems<br>"
            "• Combine with Log Table for detailed investigation"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_log_table_tab(self) -> QWidget:
        """Create the Log Table View tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Log Table View")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>What Does It Show?</b><br>"
            "The Log Table displays chronological log entries in a spreadsheet-like format. "
            "Each row represents one log entry with its timestamp, signal name, value, and any additional metadata.<br><br>"
            
            "<b>Column Structure:</b><br>"
            "• <b>Timestamp</b> - When the entry was logged<br>"
            "• <b>Signal</b> - The signal or variable name<br>"
            "• <b>Value</b> - The recorded value or state<br>"
            "• <b>Type</b> - Signal type (digital, analog, etc.)<br>"
            "• <b>Additional Columns</b> - Any extra metadata from the log<br><br>"
            
            "<b>Sorting:</b><br>"
            "• Click any column header to sort by that column<br>"
            "• Click again to reverse sort order<br>"
            "• Default sort is by timestamp (chronological)<br>"
            "• Sort by signal name to group related entries<br><br>"
            
            "<b>Filtering Signals:</b><br><br>"
            
            "<b>Filter Box:</b><br>"
            "• Type in the filter/search box at the top<br>"
            "• Entries matching the search term are shown<br>"
            "• Filters apply to signal names<br>"
            "• Clear to show all entries<br><br>"
            
            "<b>Signal Selection:</b><br>"
            "• Use the signal dropdown/list if available<br>"
            "• Select specific signals to display<br>"
            "• Deselect to hide signals you're not interested in<br><br>"
            
            "<b>Searching Entries:</b><br>"
            "• Use the search function to find specific values<br>"
            "• Search across all columns simultaneously<br>"
            "• Results highlight matching entries<br>"
            "• Navigate between results with next/previous buttons<br><br>"
            
            "<b>Interval Analysis:</b><br>"
            "• Click or right-click on a signal name in the table<br>"
            "• Select <b>Show Intervals</b> from the context menu<br>"
            "• Opens a histogram showing state change intervals<br>"
            "• Same functionality as in the Timing Diagram<br><br>"
            
            "<b>Navigation:</b><br>"
            "• Scroll vertically through entries<br>"
            "• Page Up/Down for faster navigation<br>"
            "• Home/End to jump to first/last entry<br>"
            "• Click entries to select and inspect details<br><br>"
            
            "<b>Selection and Copy:</b><br>"
            "• Click to select a single entry<br>"
            "• Shift+Click to select a range<br>"
            "• Ctrl+Click (Cmd+Click on Mac) for multiple selection<br>"
            "• Ctrl+C to copy selected entries<br><br>"
            
            "<b>Integration with Other Views:</b><br>"
            "• When views are synced, table scrolls to matching time<br>"
            "• Selecting an entry can update time in other views<br>"
            "• Use with Timing Diagram to see events in context<br><br>"
            
            "<b>Tips:</b><br>"
            "• Sort by signal to see all changes for one signal<br>"
            "• Filter to focus on specific subsystems<br>"
            "• Copy entries for further analysis in spreadsheets<br>"
            "• Use search to find error conditions or specific values"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_map_viewer_tab(self) -> QWidget:
        """Create the Map Viewer tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Map Viewer")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>What Is the Map Viewer?</b><br>"
            "The Map Viewer visualizes PLC states on custom diagrams or schematics. "
            "It shows a graphical representation of your system with elements changing color "
            "or appearance based on signal values at specific times.<br><br>"
            
            "<b>Purpose:</b><br>"
            "• See the physical or logical layout of your system<br>"
            "• Understand which components are active at any moment<br>"
            "• Visualize state transitions in a spatial context<br>"
            "• Correlate signal data with system topology<br><br>"
            
            "<b>Configuration:</b><br><br>"
            
            "<b>XML File:</b><br>"
            "• Defines the visual elements (shapes, positions, sizes)<br>"
            "• Specifies the diagram structure and layout<br>"
            "• Can include multiple layers or pages<br>"
            "• Located in <code>tools/map_viewer/test.xml</code> by default<br><br>"
            
            "<b>YAML Configuration:</b><br>"
            "• Maps signal names to visual elements<br>"
            "• Defines rules for how signals affect appearance<br>"
            "• Specifies colors, states, and transitions<br>"
            "• Located in <code>tools/map_viewer/mappings_and_rules.yaml</code> by default<br><br>"
            
            "<b>Time-Based Playback:</b><br>"
            "• The map updates to show system state at the current time<br>"
            "• Use the time controls to navigate through logged data<br>"
            "• See how the system evolved over time<br>"
            "• Correlate with events in Timing Diagram and Log Table<br><br>"
            
            "<b>Media Controls:</b><br>"
            "• <b>Play/Pause</b> - Animate through time automatically<br>"
            "• <b>Speed Control</b> - Adjust playback rate<br>"
            "• <b>Time Slider</b> - Jump to specific times<br>"
            "• <b>Step Forward/Back</b> - Move one frame at a time<br><br>"
            
            "<b>State Visualization:</b><br>"
            "• Elements change color based on signal states<br>"
            "• Active components highlighted<br>"
            "• Transitions shown in real-time during playback<br>"
            "• Legend shows color meanings (if configured)<br><br>"
            
            "<b>Interaction:</b><br>"
            "• Pan the view by clicking and dragging<br>"
            "• Zoom in/out with mouse wheel<br>"
            "• Click elements to see associated signals<br>"
            "• Tooltip shows element names and current states<br><br>"
            
            "<b>Integration:</b><br>"
            "• Syncs with other views via the <b>🔗 Sync Views</b> button<br>"
            "• Time changes in Timing Diagram update the map<br>"
            "• Bookmarks work across all views including map<br><br>"
            
            "<b>Customization:</b><br>"
            "• Edit XML and YAML files to match your system<br>"
            "• Add your own diagrams and schematics<br>"
            "• Define custom color rules and mappings<br>"
            "• Create multiple maps for different subsystems<br><br>"
            
            "<b>Tips:</b><br>"
            "• Use Map Viewer to understand spatial relationships<br>"
            "• Combine with Timing Diagram for comprehensive view<br>"
            "• Animate playback to see event sequences<br>"
            "• Create maps for critical control scenarios"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_signal_intervals_tab(self) -> QWidget:
        """Create the Signal Intervals tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Signal Intervals")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>What Are Signal Intervals?</b><br>"
            "Signal intervals show how long a signal stayed in each state between changes. "
            "This analysis helps identify patterns, find anomalies, and understand signal behavior.<br><br>"
            
            "<b>What the Analysis Shows:</b><br>"
            "• <b>State Duration Histogram</b> - Visual distribution of how long states lasted<br>"
            "• <b>Frequency Count</b> - How many times each duration occurred<br>"
            "• <b>Statistics</b> - Min, max, average, median state durations<br>"
            "• <b>Patterns</b> - Regular vs. irregular behavior<br><br>"
            
            "<b>How to Open Interval Analysis:</b><br><br>"
            
            "<b>From Timing Diagram:</b><br>"
            "1. Click or double-click any signal in the timing diagram<br>"
            "2. An interval window opens for that signal<br>"
            "3. Shows histogram of state change intervals<br><br>"
            
            "<b>From Log Table:</b><br>"
            "1. Right-click a signal name in the table<br>"
            "2. Select <b>Show Intervals</b> from context menu<br>"
            "3. Same histogram display opens<br><br>"
            
            "<b>From Home View:</b><br>"
            "1. Click the <b>📈 Signal Intervals</b> button<br>"
            "2. Choose which signal to analyze<br>"
            "3. Interval window opens for selected signal<br><br>"
            
            "<b>From Menu:</b><br>"
            "1. Go to <b>View → Plot Signal Intervals</b><br>"
            "2. Select signal from dialog<br>"
            "3. Analysis window opens<br><br>"
            
            "<b>Histogram Interpretation:</b><br><br>"
            
            "<b>X-Axis (Duration):</b><br>"
            "• Shows time intervals (milliseconds, seconds, etc.)<br>"
            "• Bins represent duration ranges<br>"
            "• Wider bins for coarse overview<br>"
            "• Narrow bins for detailed analysis<br><br>"
            
            "<b>Y-Axis (Frequency):</b><br>"
            "• Shows how many times each duration occurred<br>"
            "• Taller bars = more common durations<br>"
            "• Look for peaks indicating typical behavior<br>"
            "• Look for outliers indicating anomalies<br><br>"
            
            "<b>Statistics Displayed:</b><br>"
            "• <b>Total Transitions</b> - Number of state changes<br>"
            "• <b>Minimum Duration</b> - Shortest interval<br>"
            "• <b>Maximum Duration</b> - Longest interval<br>"
            "• <b>Average Duration</b> - Mean of all intervals<br>"
            "• <b>Median Duration</b> - Middle value when sorted<br>"
            "• <b>Standard Deviation</b> - Variability measure<br><br>"
            
            "<b>Use Cases:</b><br><br>"
            
            "<b>Finding Patterns:</b><br>"
            "• Regular peaks indicate periodic behavior<br>"
            "• Tight distribution suggests consistent timing<br>"
            "• Multiple peaks might indicate different modes<br><br>"
            
            "<b>Detecting Anomalies:</b><br>"
            "• Outliers far from main distribution<br>"
            "• Unusually long or short durations<br>"
            "• Irregular patterns during errors<br><br>"
            
            "<b>Performance Analysis:</b><br>"
            "• Check if cycle times meet requirements<br>"
            "• Identify timing variations<br>"
            "• Compare expected vs. actual durations<br><br>"
            
            "<b>Debugging:</b><br>"
            "• Verify signal timing relationships<br>"
            "• Find race conditions (very short intervals)<br>"
            "• Detect stuck signals (very long intervals)<br><br>"
            
            "<b>Tips:</b><br>"
            "• Compare intervals for related signals<br>"
            "• Look for changes in patterns over time<br>"
            "• Use statistics to quantify timing requirements<br>"
            "• Export data for further statistical analysis"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_multi_view_tab(self) -> QWidget:
        """Create the Multi-View System tab (combining split panes, sync, bookmarks)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Multi-View System")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b>Overview:</b><br>"
            "The Multi-View System lets you work with multiple perspectives simultaneously "
            "in a flexible, tabbed interface. Split views, synchronize times, and bookmark "
            "important moments for efficient analysis.<br><br>"
            
            "<!-- SPLIT PANES -->"
            "<b style='font-size: 11pt;'>Split Panes</b><br><br>"
            
            "<b>What are Split Panes?</b><br>"
            "Split panes let you view multiple tabs side-by-side or top-and-bottom. "
            "You can have up to 4 panes visible at once.<br><br>"
            
            "<b>How to Create a Split:</b><br>"
            "1. Click and hold on any tab<br>"
            "2. Drag toward the edge of the pane (left, right, top, or bottom)<br>"
            "3. When you get within 20 pixels of the edge, you'll see a <span style='color: #4285F4;'>blue drop zone</span><br>"
            "4. Release to create the split<br><br>"
            
            "<b>Split Directions:</b><br>"
            "• <b>Drag Left/Right:</b> Creates vertical split (side-by-side panes)<br>"
            "• <b>Drag Top/Bottom:</b> Creates horizontal split (top/bottom panes)<br><br>"
            
            "<b>Managing Panes:</b><br>"
            "• Close all tabs in a pane to automatically merge it back<br>"
            "• Right-click on tabs for quick close options<br>"
            "• Drag the splitter between panes to resize them<br>"
            "• Maximum of 4 panes can be active at once<br><br>"
            
            "<!-- TIME SYNC -->"
            "<b style='font-size: 11pt;'>Time Synchronization</b><br><br>"
            
            "<b>What is Time Sync?</b><br>"
            "Time synchronization keeps all your views at the same timestamp, making it easy "
            "to compare data across different view types.<br><br>"
            
            "<b>How to Use:</b><br>"
            "1. Navigate to an interesting time in any Timing Diagram view<br>"
            "2. Click the <span style='color: #4285F4;'><b>🔗 Sync Views</b></span> button in the header<br>"
            "3. All open views will jump to the same time<br><br>"
            
            "<b>What Gets Synchronized:</b><br>"
            "• <b>Timing Diagrams:</b> Pan to the synced time<br>"
            "• <b>Log Tables:</b> Scroll to show entries at that time<br>"
            "• <b>Map Viewer:</b> Update to show state at that time<br><br>"
            
            "<!-- BOOKMARKS -->"
            "<b style='font-size: 11pt;'>Bookmark System</b><br><br>"
            
            "<b>What are Bookmarks?</b><br>"
            "Bookmarks let you mark important moments in your log data and quickly jump "
            "back to them later. Perfect for comparing events or revisiting interesting patterns.<br><br>"
            
            "<b>Creating Bookmarks:</b><br>"
            "1. Navigate to the time you want to bookmark<br>"
            "2. Press <b>Ctrl+B</b><br>"
            "3. Enter a descriptive label (e.g., 'Fault Start', 'Peak Load')<br>"
            "4. Press Enter to save<br><br>"
            
            "<b>Using Bookmarks:</b><br>"
            "• <b>Ctrl+]</b> - Jump to next bookmark<br>"
            "• <b>Ctrl+[</b> - Jump to previous bookmark<br>"
            "• <b>Ctrl+Shift+B</b> - Open bookmark browser dialog<br><br>"
            
            "<b>Bookmark Browser:</b><br>"
            "The bookmark dialog shows all your bookmarks with:<br>"
            "• Timestamp - When the event occurred<br>"
            "• Label - Your custom name<br>"
            "• Description - Optional details<br><br>"
            
            "Actions in the dialog:<br>"
            "• Double-click to jump to a bookmark<br>"
            "• Click 'Add' to create a new bookmark<br>"
            "• Select and click 'Delete' to remove one<br><br>"
            
            "<b>Tips:</b><br>"
            "• Use split panes to compare timing diagram with log table<br>"
            "• Sync views after opening multiple perspectives<br>"
            "• Bookmark before investigating to mark your place<br>"
            "• Create workflow: split → open views → sync → bookmark key moments"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_shortcuts_tab(self) -> QWidget:
        """Create the complete keyboard shortcuts reference tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Keyboard Shortcuts")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        intro = QLabel(
            "Keyboard shortcuts provide quick access to common operations. "
            "All shortcuts work globally within the application."
        )
        intro.setWordWrap(True)
        content_layout.addWidget(intro)
        
        content_layout.addSpacing(10)
        
        shortcuts = QLabel(
            "<b>View Management:</b><br>"
            "• <b>Ctrl+T</b> - Open new Timing Diagram view<br>"
            "• <b>Ctrl+L</b> - Open new Log Table view<br>"
            "• <b>Ctrl+M</b> - Open new Map Viewer<br><br>"
            
            "<b>Bookmarks:</b><br>"
            "• <b>Ctrl+B</b> - Add bookmark at current time<br>"
            "• <b>Ctrl+Shift+B</b> - Show bookmark browser dialog<br>"
            "• <b>Ctrl+]</b> - Jump to next bookmark<br>"
            "• <b>Ctrl+[</b> - Jump to previous bookmark<br><br>"
            
            "<b>Help:</b><br>"
            "• <b>F1</b> - Open this help dialog<br><br>"
            
            "<b>General Navigation:</b><br>"
            "• <b>Mouse Wheel</b> - Scroll/zoom in views<br>"
            "• <b>Ctrl+Mouse Wheel</b> - Alternative zoom (view-dependent)<br>"
            "• <b>Click + Drag</b> - Pan/scroll in timing diagram<br>"
            "• <b>Double-Click</b> - Fit to view or open details<br><br>"
            
            "<b>Selection and Copy:</b><br>"
            "• <b>Ctrl+C</b> (Cmd+C on Mac) - Copy selected entries in log table<br>"
            "• <b>Shift+Click</b> - Select range in tables<br>"
            "• <b>Ctrl+Click</b> (Cmd+Click on Mac) - Multi-select in tables<br><br>"
            
            "<b>Table Navigation:</b><br>"
            "• <b>Page Up/Down</b> - Scroll one page in tables<br>"
            "• <b>Home</b> - Jump to first entry<br>"
            "• <b>End</b> - Jump to last entry<br>"
            "• <b>Arrow Keys</b> - Navigate entries<br><br>"
            
            "<b>Context Menus:</b><br>"
            "• <b>Right-Click</b> - Open context menu (tabs, signals, entries)<br>"
            "• Provides quick access to actions like close, intervals, etc."
        )
        shortcuts.setWordWrap(True)
        shortcuts.setTextFormat(Qt.RichText)
        content_layout.addWidget(shortcuts)
        
        content_layout.addSpacing(20)
        
        # Quick reference table
        reference_title = QLabel("<b>Quick Reference Card:</b>")
        reference_title.setTextFormat(Qt.RichText)
        content_layout.addWidget(reference_title)
        
        table = QLabel(
            "<table style='border: 1px solid #ccc; border-collapse: collapse; width: 100%;' cellpadding='8'>"
            "<tr style='background-color: #f5f5f5;'>"
            "<th style='border: 1px solid #ccc; text-align: left;'>Action</th>"
            "<th style='border: 1px solid #ccc; text-align: left;'>Shortcut</th>"
            "</tr>"
            "<tr><td style='border: 1px solid #ccc;'>New Timing Diagram</td><td style='border: 1px solid #ccc;'><b>Ctrl+T</b></td></tr>"
            "<tr><td style='border: 1px solid #ccc;'>New Log Table</td><td style='border: 1px solid #ccc;'><b>Ctrl+L</b></td></tr>"
            "<tr><td style='border: 1px solid #ccc;'>New Map Viewer</td><td style='border: 1px solid #ccc;'><b>Ctrl+M</b></td></tr>"
            "<tr style='background-color: #f9f9f9;'><td style='border: 1px solid #ccc;'>Add Bookmark</td><td style='border: 1px solid #ccc;'><b>Ctrl+B</b></td></tr>"
            "<tr style='background-color: #f9f9f9;'><td style='border: 1px solid #ccc;'>Show Bookmarks</td><td style='border: 1px solid #ccc;'><b>Ctrl+Shift+B</b></td></tr>"
            "<tr style='background-color: #f9f9f9;'><td style='border: 1px solid #ccc;'>Next Bookmark</td><td style='border: 1px solid #ccc;'><b>Ctrl+]</b></td></tr>"
            "<tr style='background-color: #f9f9f9;'><td style='border: 1px solid #ccc;'>Previous Bookmark</td><td style='border: 1px solid #ccc;'><b>Ctrl+[</b></td></tr>"
            "<tr><td style='border: 1px solid #ccc;'>Open Help</td><td style='border: 1px solid #ccc;'><b>F1</b></td></tr>"
            "</table>"
        )
        table.setTextFormat(Qt.RichText)
        content_layout.addWidget(table)
        
        content_layout.addSpacing(10)
        
        tips = QLabel(
            "<b>Tips:</b><br>"
            "• Shortcuts are shown in menus next to their actions<br>"
            "• Hover over buttons to see tooltips with shortcuts<br>"
            "• Mac users: Cmd key instead of Ctrl for most shortcuts<br>"
            "• View-specific shortcuts may vary depending on the active view"
        )
        tips.setWordWrap(True)
        tips.setTextFormat(Qt.RichText)
        content_layout.addWidget(tips)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _create_tips_tab(self) -> QWidget:
        """Create the Tips & Troubleshooting tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        title = QLabel("Tips & Troubleshooting")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        content_layout.addWidget(title)
        
        help_text = QLabel(
            "<b style='font-size: 11pt;'>Performance Tips</b><br><br>"
            
            "<b>Large File Handling:</b><br>"
            "• The app is optimized for files up to several GB<br>"
            "• Parsing may take time for very large files—be patient<br>"
            "• Progress bar shows real-time parsing status<br>"
            "• Consider splitting extremely large logs into smaller files<br><br>"
            
            "<b>View Performance:</b><br>"
            "• Timing diagram limits to 5-minute visible ranges for performance<br>"
            "• Pan to different time ranges rather than zooming out too far<br>"
            "• Filter signals to reduce the number displayed<br>"
            "• Close unused views to free memory<br><br>"
            
            "<b>Memory Management:</b><br>"
            "• Use the <b>Clear</b> button to free memory after analysis<br>"
            "• Close interval windows when done with them<br>"
            "• Signal data is cached intelligently<br>"
            "• Only visible time ranges are kept in memory<br><br>"
            
            "<!-- BEST PRACTICES -->"
            "<b style='font-size: 11pt;'>Best Practices for Analysis</b><br><br>"
            
            "<b>Effective Workflow:</b><br>"
            "1. <b>Load and verify</b> - Check stats widget for completeness<br>"
            "2. <b>Overview first</b> - Open timing diagram to get the big picture<br>"
            "3. <b>Focus in</b> - Filter to relevant signals and time ranges<br>"
            "4. <b>Correlate</b> - Use split panes to compare views<br>"
            "5. <b>Bookmark key moments</b> - Mark events of interest<br>"
            "6. <b>Deep dive</b> - Use interval analysis and log table details<br><br>"
            
            "<b>Investigation Strategies:</b><br>"
            "• <b>For timing issues:</b> Use timing diagram + interval analysis<br>"
            "• <b>For error events:</b> Use log table filtering + bookmarks<br>"
            "• <b>For sequence verification:</b> Use map viewer + timing diagram<br>"
            "• <b>For pattern analysis:</b> Use signal intervals across multiple signals<br><br>"
            
            "<b>View Combinations:</b><br>"
            "• <b>Timing + Log Table:</b> See waveforms and detailed entries side-by-side<br>"
            "• <b>Timing + Map Viewer:</b> Connect timing with physical layout<br>"
            "• <b>Log Table + Intervals:</b> Find patterns in specific signal groups<br>"
            "• <b>All three:</b> Comprehensive view for complex debugging<br><br>"
            
            "<!-- COMMON ISSUES -->"
            "<b style='font-size: 11pt;'>Common Issues & Solutions</b><br><br>"
            
            "<b>\"No data appears after parsing\"</b><br>"
            "• Check the statistics widget—was parsing successful?<br>"
            "• Look for error messages in the stats panel<br>"
            "• Verify file format is supported<br>"
            "• Try opening views manually (buttons or menu)<br><br>"
            
            "<b>\"Views are not synchronized\"</b><br>"
            "• Click the <span style='color: #4285F4;'><b>🔗 Sync Views</b></span> button in the header<br>"
            "• Ensure a timing diagram view is open and active<br>"
            "• Sync works from the active view's current time<br>"
            "• Only timing-aware views can be synced<br><br>"
            
            "<b>\"Timing diagram shows only part of my data\"</b><br>"
            "• This is intentional—5 minute limit for performance<br>"
            "• Pan horizontally to see different time ranges<br>"
            "• Use bookmarks to mark regions of interest<br>"
            "• Use log table to see all entries chronologically<br><br>"
            
            "<b>\"Can't create more split panes\"</b><br>"
            "• Maximum of 4 panes allowed to maintain usability<br>"
            "• Close some panes first (close all tabs in a pane)<br>"
            "• Consider using tabs within panes instead<br>"
            "• Use Alt+Tab to switch between tab groups<br><br>"
            
            "<b>\"Signal intervals show no data\"</b><br>"
            "• Signal must have at least 2 state changes<br>"
            "• Check if signal is static in your log<br>"
            "• Verify signal data was parsed correctly<br>"
            "• Try a different signal to confirm functionality<br><br>"
            
            "<b>\"Map viewer not showing anything\"</b><br>"
            "• XML and YAML configuration files must be present<br>"
            "• Check that files exist in <code>tools/map_viewer/</code><br>"
            "• Verify signal mappings in YAML match your log signals<br>"
            "• Customize configuration for your system<br><br>"
            
            "<b>\"Application is slow or freezing\"</b><br>"
            "• Close unused views and interval windows<br>"
            "• Reduce visible time range in timing diagram<br>"
            "• Filter to fewer signals<br>"
            "• Clear and reload data if memory is an issue<br>"
            "• Consider processing files in smaller chunks<br><br>"
            
            "<!-- WORKFLOW RECOMMENDATIONS -->"
            "<b style='font-size: 11pt;'>Workflow Recommendations</b><br><br>"
            
            "<b>For Debugging PLC Issues:</b><br>"
            "1. Load log from the problem period<br>"
            "2. Check overall stats for anomalies<br>"
            "3. Open timing diagram, identify suspect signals<br>"
            "4. Bookmark the problem time<br>"
            "5. Split and add log table for details<br>"
            "6. Use interval analysis to compare normal vs. problem behavior<br>"
            "7. Document findings with bookmarks and notes<br><br>"
            
            "<b>For Performance Analysis:</b><br>"
            "1. Load representative log data<br>"
            "2. Identify cycle/timing signals<br>"
            "3. Use signal intervals to get timing statistics<br>"
            "4. Compare intervals across different operational modes<br>"
            "5. Look for outliers and variability<br>"
            "6. Export data if quantitative analysis is needed<br><br>"
            
            "<b>For System Verification:</b><br>"
            "1. Load logs from test runs<br>"
            "2. Configure map viewer for your system<br>"
            "3. Use playback to verify sequences<br>"
            "4. Bookmark expected vs. actual transitions<br>"
            "5. Compare timing diagram with requirements<br>"
            "6. Document discrepancies with bookmarks<br><br>"
            
            "<b>Tips:</b><br>"
            "• Press <b>F1</b> anytime to reopen this help<br>"
            "• Check menu items for additional features<br>"
            "• Experiment with view combinations<br>"
            "• Use bookmarks liberally—they're searchable and sortable"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        content_layout.addWidget(help_text)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

