"""Home view containing upload, stats, file list, and view buttons."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QGridLayout,
)

from plc_visualizer.app import SessionManager
from ..components.file_upload_widget import FileUploadWidget
from ..components.file_list_widget import FileListWidget
from ..components.stats_widget import StatsWidget


class HomeView(QWidget):
    """Home view containing file upload, stats, and view buttons."""
    
    # Signals emitted when view buttons are clicked
    timing_diagram_requested = Signal()
    log_table_requested = Signal()
    map_viewer_requested = Signal()
    signal_intervals_requested = Signal()
    
    VIEW_TYPE = "Home"
    
    def __init__(self, session_manager: SessionManager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        
        # Child widgets
        self.upload_widget: FileUploadWidget = None
        self.stats_widget: StatsWidget = None
        self.file_list_widget: FileListWidget = None
        self.progress_bar: QProgressBar = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the home view UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # 2-column top section: Upload/Stats (left) and File List (right)
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(16)
        
        # LEFT COLUMN: Upload widget and stats
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        # Upload section label
        upload_label = QLabel("📄 Log File")
        upload_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(upload_label)
        
        # Upload widget
        self.upload_widget = FileUploadWidget()
        left_layout.addWidget(self.upload_widget)
        
        # Stats widget
        stats_container = QWidget()
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(0)
        
        self.stats_widget = StatsWidget(stats_container)
        stats_layout.addWidget(self.stats_widget)
        
        left_layout.addWidget(stats_container)
        top_layout.addWidget(left_column, 40)  # 40% width
        
        # RIGHT COLUMN: File list
        self.file_list_widget = FileListWidget()
        top_layout.addWidget(self.file_list_widget, 60)  # 60% width
        
        main_layout.addWidget(top_section)
        
        # Progress bar (hidden during normal operation)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Parsing files... %p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                text-align: center;
                background-color: #f5f5f5;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #4285F4;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # 4-button grid for opening views
        button_grid_container = QWidget()
        button_grid_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        button_grid_layout = QVBoxLayout(button_grid_container)
        button_grid_layout.setContentsMargins(16, 16, 16, 16)
        button_grid_layout.setSpacing(12)
        
        # Grid title
        grid_title = QLabel("Open Views")
        grid_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #212529;")
        button_grid_layout.addWidget(grid_title)
        
        # 2x2 button grid
        button_grid = QWidget()
        grid_layout = QGridLayout(button_grid)
        grid_layout.setSpacing(12)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the 4 view buttons
        timing_button = self._create_view_button(
            "⚙️ Timing Diagram",
            "#4285F4",  # Blue
            "#1967D2",
            "#0D47A1"
        )
        timing_button.clicked.connect(self.timing_diagram_requested.emit)
        
        log_table_button = self._create_view_button(
            "📋 Log Table",
            "#34A853",  # Green
            "#2D8E47",
            "#1E7735"
        )
        log_table_button.clicked.connect(self.log_table_requested.emit)
        
        map_viewer_button = self._create_view_button(
            "🗺️ Map Viewer",
            "#FBBC04",  # Yellow
            "#F9AB00",
            "#E37400"
        )
        map_viewer_button.clicked.connect(self.map_viewer_requested.emit)
        
        intervals_button = self._create_view_button(
            "📈 Signal Intervals",
            "#EA4335",  # Red
            "#D33B2C",
            "#B31412"
        )
        intervals_button.clicked.connect(self.signal_intervals_requested.emit)
        
        # Add buttons to grid (2x2)
        grid_layout.addWidget(timing_button, 0, 0)
        grid_layout.addWidget(log_table_button, 0, 1)
        grid_layout.addWidget(map_viewer_button, 1, 0)
        grid_layout.addWidget(intervals_button, 1, 1)
        
        button_grid_layout.addWidget(button_grid)
        main_layout.addWidget(button_grid_container)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
    
    def _create_view_button(self, text: str, bg_color: str, hover_color: str, pressed_color: str) -> QPushButton:
        """Create a styled button for opening a view."""
        button = QPushButton(text)
        button.setMinimumHeight(80)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)
        return button

