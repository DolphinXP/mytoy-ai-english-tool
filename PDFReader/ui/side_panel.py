"""
Side panel with bookmark and history tabs.
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListWidget, QListWidgetItem, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from PDFReader.models.annotation import Annotation


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


class HistoryPanel(QWidget):
    """Panel for displaying reading history."""

    history_clicked = Signal(str, int)  # document_path, page_number

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
                padding: 10px 12px;
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

        self._empty_label = QLabel("No reading history yet")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #888888; padding: 20px;")
        layout.addWidget(self._empty_label)

    def add_history(self, doc_path: str, page: int, title: str):
        """Add a history entry."""
        self._empty_label.hide()
        self._list.show()

        # Check if already exists and remove
        for i in range(self._list.count()):
            item = self._list.item(i)
            data = item.data(Qt.UserRole)
            if data and data[0] == doc_path and data[1] == page:
                self._list.takeItem(i)
                break

        # Add to top
        item = QListWidgetItem()
        item.setText(f"{title} - Page {page + 1}")
        item.setData(Qt.UserRole, (doc_path, page))
        self._list.insertItem(0, item)

        # Limit history
        while self._list.count() > 50:
            self._list.takeItem(self._list.count() - 1)

    def clear_history(self):
        self._list.clear()
        self._empty_label.show()
        self._list.hide()

    def _on_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            self.history_clicked.emit(data[0], data[1])


class SidePanel(QWidget):
    """Collapsible side panel with bookmark and history tabs."""

    bookmark_clicked = Signal(int)
    history_clicked = Signal(str, int)
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

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 8px 16px;
                border: none;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3c3c3c;
            }
        """)

        # Bookmark tab
        self._bookmark_panel = BookmarkPanel()
        self._bookmark_panel.bookmark_clicked.connect(self.bookmark_clicked.emit)
        self._tabs.addTab(self._bookmark_panel, "Bookmarks")

        # History tab
        self._history_panel = HistoryPanel()
        self._history_panel.history_clicked.connect(self.history_clicked.emit)
        self._tabs.addTab(self._history_panel, "History")

        layout.addWidget(self._tabs)

        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._tabs.hide()
            self._collapse_btn.setText("▶")
            self.setFixedWidth(40)
        else:
            self._tabs.show()
            self._collapse_btn.setText("◀")
            self.setMinimumWidth(200)
            self.setMaximumWidth(300)
        self.collapse_toggled.emit(self._collapsed)

    def set_bookmarks(self, bookmarks: List[tuple]):
        self._bookmark_panel.set_bookmarks(bookmarks)

    def add_history(self, doc_path: str, page: int, title: str):
        self._history_panel.add_history(doc_path, page, title)

    def is_collapsed(self) -> bool:
        return self._collapsed
