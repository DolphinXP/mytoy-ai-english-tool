"""
Custom text edit widgets with translation support.
"""
from PySide6.QtWidgets import QTextEdit, QTextBrowser
from PySide6.QtCore import Signal, QTimer


class TranslatableTextEdit(QTextEdit):
    """Custom QTextEdit that shows translate popup when text is selected and mouse is released."""

    text_selected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_selection = ""

    def mouseReleaseEvent(self, event):
        """Handle mouse release - show translate popup if text is selected."""
        # Let the parent handle the event first
        super().mouseReleaseEvent(event)

        # Check if there's a selection after mouse release
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()

        # Only emit if there's a new non-empty selection
        if selected_text and selected_text != self._last_selection:
            self._last_selection = selected_text
            # Small delay to ensure UI is stable
            QTimer.singleShot(50, self._emit_if_still_selected)
        elif not selected_text:
            self._last_selection = ""

    def _emit_if_still_selected(self):
        """Emit signal if text is still selected."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            self.text_selected.emit()


class TranslatableTextBrowser(QTextBrowser):
    """Custom QTextBrowser that shows translate popup when text is selected and mouse is released."""

    text_selected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_selection = ""

    def mouseReleaseEvent(self, event):
        """Handle mouse release - show translate popup if text is selected."""
        # Let the parent handle the event first
        super().mouseReleaseEvent(event)

        # Check if there's a selection after mouse release
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()

        # Only emit if there's a new non-empty selection
        if selected_text and selected_text != self._last_selection:
            self._last_selection = selected_text
            # Small delay to ensure UI is stable
            QTimer.singleShot(50, self._emit_if_still_selected)
        elif not selected_text:
            self._last_selection = ""

    def _emit_if_still_selected(self):
        """Emit signal if text is still selected."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            self.text_selected.emit()
