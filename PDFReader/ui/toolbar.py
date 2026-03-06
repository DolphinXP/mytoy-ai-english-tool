"""
Toolbar widget for PDFReader.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox,
    QComboBox, QToolButton, QMenu, QStyle, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QFontMetrics


def _create_text_icon(text: str, size: int = 20, color: str = "#d4d4d4") -> QIcon:
    """Create an icon from text/symbol."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    
    # Use a clear, readable font
    font = QFont("Segoe UI Symbol", int(size * 0.7))
    painter.setFont(font)
    painter.setPen(QColor(color))
    
    # Center the text
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()
    
    return QIcon(pixmap)


class ToolbarWidget(QWidget):
    """Toolbar with navigation and zoom controls."""

    # Signals
    open_file_clicked = Signal()
    first_page_clicked = Signal()
    prev_page_clicked = Signal()
    next_page_clicked = Signal()
    last_page_clicked = Signal()
    page_number_changed = Signal(int)
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    zoom_reset_clicked = Signal()
    zoom_fit_width_toggled = Signal(bool)
    zoom_fit_window_toggled = Signal(bool)
    zoom_level_changed = Signal(float)
    toggle_annotations_clicked = Signal()

    def __init__(self, parent=None):
        """Initialize toolbar."""
        super().__init__(parent)
        self._page_count = 0
        self._setup_ui()

    def _setup_ui(self):
        """Set up the toolbar UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-bottom: 1px solid #333333;
            }
            QPushButton, QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 13px;
                color: #d4d4d4;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #333333;
                border-color: #3c3c3c;
            }
            QPushButton:pressed, QToolButton:pressed {
                background-color: #2a2d2e;
            }
            QPushButton:checked, QToolButton:checked {
                background-color: #0e639c;
                border-color: #0e639c;
                color: #ffffff;
            }
            QPushButton:disabled, QToolButton:disabled {
                color: #6b6b6b;
            }
            QSpinBox {
                background-color: #3c3c3c;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #d4d4d4;
                padding: 2px;
            }
            QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #d4d4d4;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #d4d4d4;
                selection-background-color: #0e639c;
            }
            QLabel {
                color: #a0a0a0;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # File menu button (menu is attached by MainWindow)
        self._file_menu_btn = QToolButton()
        self._file_menu_btn.setText("File")
        self._file_menu_btn.setPopupMode(QToolButton.InstantPopup)
        self._file_menu_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        layout.addWidget(self._file_menu_btn)

        # Open file button
        layout.addSpacing(16)

        # Navigation buttons
        self._first_btn = QPushButton("First")
        self._first_btn.setToolTip("First page (Home)")
        self._first_btn.setMinimumWidth(72)
        self._first_btn.clicked.connect(self.first_page_clicked.emit)
        self._first_btn.setIcon(_create_text_icon("⏮", 22))
        self._first_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._first_btn)

        self._prev_btn = QPushButton("Prev")
        self._prev_btn.setToolTip("Previous page (Left Arrow)")
        self._prev_btn.setMinimumWidth(72)
        self._prev_btn.clicked.connect(self.prev_page_clicked.emit)
        self._prev_btn.setIcon(_create_text_icon("◀", 22))
        self._prev_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._prev_btn)

        # Page number input
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.setFixedWidth(60)
        self._page_spin.setAlignment(Qt.AlignCenter)
        self._page_spin.valueChanged.connect(
            lambda v: self.page_number_changed.emit(v - 1)
        )
        layout.addWidget(self._page_spin)

        self._page_count_label = QLabel("/ 0")
        self._page_count_label.setStyleSheet(
            "background: transparent; border: none;")
        layout.addWidget(self._page_count_label)

        self._next_btn = QPushButton("Next")
        self._next_btn.setToolTip("Next page (Right Arrow)")
        self._next_btn.setMinimumWidth(72)
        self._next_btn.clicked.connect(self.next_page_clicked.emit)
        self._next_btn.setIcon(_create_text_icon("▶", 22))
        self._next_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._next_btn)

        self._last_btn = QPushButton("Last")
        self._last_btn.setToolTip("Last page (End)")
        self._last_btn.setMinimumWidth(72)
        self._last_btn.clicked.connect(self.last_page_clicked.emit)
        self._last_btn.setIcon(_create_text_icon("⏭", 22))
        self._last_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._last_btn)

        layout.addSpacing(16)

        # Zoom controls
        self._zoom_out_btn = QPushButton("Out")
        self._zoom_out_btn.setToolTip("Zoom out (Ctrl+-)")
        self._zoom_out_btn.setMinimumWidth(68)
        self._zoom_out_btn.clicked.connect(self.zoom_out_clicked.emit)
        self._zoom_out_btn.setIcon(_create_text_icon("−", 22))
        self._zoom_out_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._zoom_out_btn)

        self._zoom_combo = QComboBox()
        self._zoom_combo.setEditable(True)
        self._zoom_combo.setFixedWidth(80)
        self._zoom_combo.addItems(
            ["50%", "75%", "100%", "125%", "150%", "200%", "300%"])
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_text_changed)
        layout.addWidget(self._zoom_combo)

        self._zoom_in_btn = QPushButton("In")
        self._zoom_in_btn.setToolTip("Zoom in (Ctrl++)")
        self._zoom_in_btn.setMinimumWidth(68)
        self._zoom_in_btn.clicked.connect(self.zoom_in_clicked.emit)
        self._zoom_in_btn.setIcon(_create_text_icon("+", 22))
        self._zoom_in_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._zoom_in_btn)

        self._zoom_reset_btn = QPushButton("Reset Zoom")
        self._zoom_reset_btn.setToolTip("Reset zoom (Ctrl+0)")
        self._zoom_reset_btn.clicked.connect(self.zoom_reset_clicked.emit)
        self._zoom_reset_btn.setIcon(_create_text_icon("⟲", 22))
        self._zoom_reset_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._zoom_reset_btn)

        self._fit_width_btn = QPushButton("Fit Width")
        self._fit_width_btn.setToolTip("Fit page width to viewer")
        self._fit_width_btn.setCheckable(True)
        self._fit_width_btn.toggled.connect(self.zoom_fit_width_toggled.emit)
        self._fit_width_btn.setIcon(_create_text_icon("↔", 22))
        self._fit_width_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._fit_width_btn)

        self._fit_window_btn = QPushButton("Fit Page")
        self._fit_window_btn.setToolTip("Fit entire page in viewer")
        self._fit_window_btn.setCheckable(True)
        self._fit_window_btn.toggled.connect(self.zoom_fit_window_toggled.emit)
        self._fit_window_btn.setIcon(_create_text_icon("⛶", 22))
        self._fit_window_btn.setIconSize(QSize(22, 22))
        layout.addWidget(self._fit_window_btn)

        self._fit_group = QButtonGroup(self)
        self._fit_group.setExclusive(False)
        self._fit_group.addButton(self._fit_width_btn)
        self._fit_group.addButton(self._fit_window_btn)

        layout.addStretch()

        # Toggle annotation panel button
        self._toggle_annotations_btn = QPushButton("Annotations")
        self._toggle_annotations_btn.setToolTip("Toggle annotation panel")
        self._toggle_annotations_btn.setCheckable(True)
        self._toggle_annotations_btn.setChecked(True)
        self._toggle_annotations_btn.setIcon(_create_text_icon("☰", 22))
        self._toggle_annotations_btn.setIconSize(QSize(22, 22))
        self._toggle_annotations_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
                color: #d4d4d4;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #3c3c3c;
            }
            QPushButton:checked {
                background-color: #0e639c;
                color: #ffffff;
            }
        """)
        self._toggle_annotations_btn.clicked.connect(
            self.toggle_annotations_clicked.emit)
        layout.addWidget(self._toggle_annotations_btn)

        # Initially disable navigation
        self._set_navigation_enabled(False)

    def set_file_menu(self, menu: QMenu):
        """Attach the File menu to the toolbar button."""
        self._file_menu_btn.setMenu(menu)

    def _on_zoom_text_changed(self, text: str):
        """Handle zoom combo text change."""
        try:
            # Remove % sign and convert to float
            value = float(text.replace("%", "").strip())
            self.zoom_level_changed.emit(value / 100.0)
        except ValueError:
            pass

    def set_page_count(self, count: int):
        """Set total page count."""
        self._page_count = count
        self._page_spin.setMaximum(max(1, count))
        self._page_count_label.setText(f"/ {count}")
        self._set_navigation_enabled(count > 0)

    def set_current_page(self, page: int):
        """Set current page number (0-indexed)."""
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(page + 1)
        self._page_spin.blockSignals(False)

        # Update button states
        self._first_btn.setEnabled(page > 0)
        self._prev_btn.setEnabled(page > 0)
        self._next_btn.setEnabled(page < self._page_count - 1)
        self._last_btn.setEnabled(page < self._page_count - 1)

    def set_zoom_level(self, zoom: float):
        """Set zoom level display."""
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentText(f"{int(zoom * 100)}%")
        self._zoom_combo.blockSignals(False)

    def _set_navigation_enabled(self, enabled: bool):
        """Enable/disable navigation controls."""
        self._first_btn.setEnabled(enabled)
        self._prev_btn.setEnabled(enabled)
        self._next_btn.setEnabled(enabled)
        self._last_btn.setEnabled(enabled)
        self._page_spin.setEnabled(enabled)
        self._zoom_in_btn.setEnabled(enabled)
        self._zoom_out_btn.setEnabled(enabled)
        self._zoom_combo.setEnabled(enabled)
        self._zoom_reset_btn.setEnabled(enabled)
        self._fit_width_btn.setEnabled(enabled)
        self._fit_window_btn.setEnabled(enabled)

    def set_fit_mode(self, mode: str):
        """Set fit mode check state: 'width', 'page', or None."""
        self._fit_width_btn.blockSignals(True)
        self._fit_window_btn.blockSignals(True)
        self._fit_width_btn.setChecked(mode == "width")
        self._fit_window_btn.setChecked(mode == "page")
        self._fit_width_btn.blockSignals(False)
        self._fit_window_btn.blockSignals(False)
