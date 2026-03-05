"""
Context menu for text selection actions.
"""
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Signal, QObject, QPoint
from PySide6.QtGui import QAction


class TextContextMenu(QObject):
    """Context menu with Mark option for creating annotations."""

    mark_clicked = Signal(str)  # selected_text
    add_bookmark_clicked = Signal(str)  # selected_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_text = ""
        self._menu = QMenu(parent)
        self._setup_menu()

    def _setup_menu(self):
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px 0;
                color: #d4d4d4;
            }
            QMenu::item {
                background-color: transparent;
                color: #d4d4d4;
                padding: 8px 24px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #0e639c;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3c3c3c;
                margin: 4px 8px;
            }
        """)

        # Mark action - creates annotation with selected text
        self._mark_action = QAction("Mark Selection", self._menu)
        self._mark_action.triggered.connect(self._on_mark)
        self._menu.addAction(self._mark_action)

        # Add Bookmark submenu
        self._add_bookmark_menu = self._menu.addMenu("Add Bookmark")
        self._add_bookmark_from_selection_action = QAction(
            "Use Selected Text", self._add_bookmark_menu
        )
        self._add_bookmark_from_selection_action.triggered.connect(
            self._on_add_bookmark
        )
        self._add_bookmark_menu.addAction(self._add_bookmark_from_selection_action)

    def show_at(self, pos: QPoint, text: str):
        """Show context menu at position with selected text."""
        self._selected_text = text
        has_text = bool(text and text.strip())
        self._mark_action.setEnabled(has_text)
        self._add_bookmark_menu.setEnabled(has_text)
        self._menu.popup(pos)

    def _on_mark(self):
        if self._selected_text:
            self.mark_clicked.emit(self._selected_text)

    def _on_add_bookmark(self):
        if self._selected_text:
            self.add_bookmark_clicked.emit(self._selected_text)
