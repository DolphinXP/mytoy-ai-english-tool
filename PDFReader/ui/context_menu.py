"""
Context menu for text selection actions.
"""
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Signal, QObject, QPoint
from PySide6.QtGui import QAction


class TextContextMenu(QObject):
    """Context menu with Mark option for creating annotations."""

    mark_clicked = Signal(str)  # selected_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_text = ""
        self._menu = QMenu(parent)
        self._setup_menu()

    def _setup_menu(self):
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #454545;
                border-radius: 4px;
                padding: 4px 0;
            }
            QMenu::item {
                background-color: transparent;
                color: #ffffff;
                padding: 8px 24px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QMenu::separator {
                height: 1px;
                background-color: #454545;
                margin: 4px 8px;
            }
        """)

        # Mark action - creates annotation with selected text
        self._mark_action = QAction("📌 Mark", self._menu)
        self._mark_action.triggered.connect(self._on_mark)
        self._menu.addAction(self._mark_action)

    def show_at(self, pos: QPoint, text: str):
        """Show context menu at position with selected text."""
        self._selected_text = text
        self._menu.popup(pos)

    def _on_mark(self):
        if self._selected_text:
            self.mark_clicked.emit(self._selected_text)
