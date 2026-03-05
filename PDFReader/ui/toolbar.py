"""
Toolbar widget for PDFReader.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox,
    QComboBox, QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont


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
                padding: 6px 12px;
                font-size: 13px;
                color: #cccccc;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #3c3c3c;
                border-color: #555555;
            }
            QPushButton:pressed, QToolButton:pressed {
                background-color: #4a4a4a;
            }
            QPushButton:disabled, QToolButton:disabled {
                color: #666666;
            }
            QSpinBox {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                padding: 2px;
            }
            QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QLabel {
                color: #cccccc;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Open file button
        self._open_btn = QPushButton("📂 Open")
        self._open_btn.setToolTip("Open PDF file (Ctrl+O)")
        self._open_btn.clicked.connect(self.open_file_clicked.emit)
        layout.addWidget(self._open_btn)

        layout.addSpacing(16)

        # Navigation buttons
        self._first_btn = QPushButton("⏮")
        self._first_btn.setToolTip("First page (Home)")
        self._first_btn.setFixedWidth(36)
        self._first_btn.clicked.connect(self.first_page_clicked.emit)
        layout.addWidget(self._first_btn)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setToolTip("Previous page (←)")
        self._prev_btn.setFixedWidth(36)
        self._prev_btn.clicked.connect(self.prev_page_clicked.emit)
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

        self._next_btn = QPushButton("▶")
        self._next_btn.setToolTip("Next page (→)")
        self._next_btn.setFixedWidth(36)
        self._next_btn.clicked.connect(self.next_page_clicked.emit)
        layout.addWidget(self._next_btn)

        self._last_btn = QPushButton("⏭")
        self._last_btn.setToolTip("Last page (End)")
        self._last_btn.setFixedWidth(36)
        self._last_btn.clicked.connect(self.last_page_clicked.emit)
        layout.addWidget(self._last_btn)

        layout.addSpacing(16)

        # Zoom controls
        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setToolTip("Zoom out (Ctrl+-)")
        self._zoom_out_btn.setFixedWidth(36)
        self._zoom_out_btn.clicked.connect(self.zoom_out_clicked.emit)
        layout.addWidget(self._zoom_out_btn)

        self._zoom_combo = QComboBox()
        self._zoom_combo.setEditable(True)
        self._zoom_combo.setFixedWidth(80)
        self._zoom_combo.addItems(
            ["50%", "75%", "100%", "125%", "150%", "200%", "300%"])
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_text_changed)
        layout.addWidget(self._zoom_combo)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setToolTip("Zoom in (Ctrl++)")
        self._zoom_in_btn.setFixedWidth(36)
        self._zoom_in_btn.clicked.connect(self.zoom_in_clicked.emit)
        layout.addWidget(self._zoom_in_btn)

        self._zoom_reset_btn = QPushButton("Reset")
        self._zoom_reset_btn.setToolTip("Reset zoom (Ctrl+0)")
        self._zoom_reset_btn.clicked.connect(self.zoom_reset_clicked.emit)
        layout.addWidget(self._zoom_reset_btn)

        layout.addStretch()

        # Toggle annotation panel button
        self._toggle_annotations_btn = QPushButton("📝 Annotations")
        self._toggle_annotations_btn.setToolTip("Toggle annotation panel")
        self._toggle_annotations_btn.setCheckable(True)
        self._toggle_annotations_btn.setChecked(True)
        self._toggle_annotations_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
                color: #cccccc;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                border-color: #555555;
            }
            QPushButton:checked {
                background-color: #0078d4;
                color: #ffffff;
            }
        """)
        self._toggle_annotations_btn.clicked.connect(
            self.toggle_annotations_clicked.emit)
        layout.addWidget(self._toggle_annotations_btn)

        # Initially disable navigation
        self._set_navigation_enabled(False)

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
