"""Side panel for PDF bookmarks."""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStyle
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont


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


def _light_icon(widget: QWidget, standard_pixmap: QStyle.StandardPixmap, size: int = 18) -> QIcon:
    """Create a light-tinted icon from Qt standard pixmaps for dark theme."""
    # Try to get the standard icon directly - it may already be styled correctly
    icon = widget.style().standardIcon(standard_pixmap)
    if not icon.isNull():
        return icon
    
    # Fallback: get pixmap and try to tint it
    source = widget.style().standardPixmap(standard_pixmap)
    if source.isNull():
        return QIcon()

    # Scale to desired size
    scaled = source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return QIcon(scaled)


class BookmarkPanel(QWidget):
    """Panel for displaying PDF bookmarks/outline."""

    bookmark_clicked = Signal(int)  # page_number

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #d4d4d4;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QListWidget::item:selected {
                background-color: #0e639c;
            }
        """)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self._empty_label = QLabel("No bookmarks in this PDF")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #7f7f7f; padding: 20px;")
        layout.addWidget(self._empty_label)

    def set_bookmarks(self, bookmarks: List[tuple]):
        """Set bookmarks list. Each tuple: (title, page_number, level)."""
        self._list.clear()
        if not bookmarks:
            self._empty_label.show()
            self._list.hide()
            return

        self._empty_label.hide()
        self._list.show()

        for title, page, level in bookmarks:
            item = QListWidgetItem()
            indent = "  " * level
            item.setText(f"{indent}{title}")
            item.setData(Qt.UserRole, page)
            self._list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        page = item.data(Qt.UserRole)
        if page is not None:
            self.bookmark_clicked.emit(page)


class SidePanel(QWidget):
    """Collapsible side panel with bookmarks."""

    bookmark_clicked = Signal(int)
    collapse_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with collapse button
        header = QWidget()
        header.setStyleSheet("background-color: #252526;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self._collapse_btn = QPushButton("Hide")
        self._collapse_btn.setFixedSize(76, 24)
        self._collapse_btn.setToolTip("Hide bookmarks panel")
        self._collapse_btn.setIcon(_create_text_icon("◀", 20, "#d4d4d4"))
        self._collapse_btn.setIconSize(QSize(20, 20))
        self._collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #d4d4d4;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-radius: 4px;
            }
        """)
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self._collapse_btn)
        header_layout.addStretch()

        layout.addWidget(header)

        self._bookmark_panel = BookmarkPanel()
        self._bookmark_panel.bookmark_clicked.connect(self.bookmark_clicked.emit)
        layout.addWidget(self._bookmark_panel)

        self.setMinimumWidth(160)
        self.setMaximumWidth(500)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._bookmark_panel.hide()
            self._collapse_btn.setText("Show")
            self._collapse_btn.setToolTip("Show bookmarks panel")
            self._collapse_btn.setIcon(_create_text_icon("▶", 20, "#d4d4d4"))
            self.setFixedWidth(72)
        else:
            self._bookmark_panel.show()
            self._collapse_btn.setText("Hide")
            self._collapse_btn.setToolTip("Hide bookmarks panel")
            self._collapse_btn.setIcon(_create_text_icon("◀", 20, "#d4d4d4"))
            self.setMinimumWidth(160)
            self.setMaximumWidth(500)
        self.collapse_toggled.emit(self._collapsed)

    def set_bookmarks(self, bookmarks: List[tuple]):
        self._bookmark_panel.set_bookmarks(bookmarks)

    def is_collapsed(self) -> bool:
        return self._collapsed
