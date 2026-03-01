"""
Context menu for text selection actions.
"""
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Signal, QObject, QPoint
from PySide6.QtGui import QAction


class TextContextMenu(QObject):
    """Context menu with Translation and AI Explain options."""

    translate_clicked = Signal(str)  # selected_text
    explain_clicked = Signal(str)  # selected_text

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

        # Translation action
        self._translate_action = QAction("🌐 Translation", self._menu)
        self._translate_action.triggered.connect(self._on_translate)
        self._menu.addAction(self._translate_action)

        # AI Explain action
        self._explain_action = QAction("💡 AI Explain", self._menu)
        self._explain_action.triggered.connect(self._on_explain)
        self._menu.addAction(self._explain_action)

    def show_at(self, pos: QPoint, text: str):
        """Show context menu at position with selected text."""
        self._selected_text = text
        self._menu.popup(pos)

    def _on_translate(self):
        if self._selected_text:
            self.translate_clicked.emit(self._selected_text)

    def _on_explain(self):
        if self._selected_text:
            self.explain_clicked.emit(self._selected_text)
