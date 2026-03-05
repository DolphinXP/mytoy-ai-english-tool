"""Side panel for PDF bookmarks."""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal


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
                color: #ffffff;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self._empty_label = QLabel("No bookmarks in this PDF")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #888888; padding: 20px;")
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

        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
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
            self._collapse_btn.setText("▶")
            self.setFixedWidth(40)
        else:
            self._bookmark_panel.show()
            self._collapse_btn.setText("◀")
            self.setMinimumWidth(160)
            self.setMaximumWidth(500)
        self.collapse_toggled.emit(self._collapsed)

    def set_bookmarks(self, bookmarks: List[tuple]):
        self._bookmark_panel.set_bookmarks(bookmarks)

    def is_collapsed(self) -> bool:
        return self._collapsed
