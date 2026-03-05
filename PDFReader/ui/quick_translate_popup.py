"""Floating popup for quick translation results."""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QTextEdit, QApplication


class QuickTranslatePopup(QFrame):
    """Non-intrusive popup that shows quick translation text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
            QLabel {
                color: #a0a0a0;
                font-size: 10px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 6px;
                color: #d4d4d4;
                font-size: 11px;
            }
            """
        )
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._title = QLabel("Translation")
        layout.addWidget(self._title)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumHeight(150)
        layout.addWidget(self._text)

    def show_loading(self, anchor_global: QPoint):
        self._title.setText("Translation")
        self._text.setPlainText("Translating...")
        self._show_above(anchor_global)

    def set_result(self, anchor_global: QPoint, text: str):
        self._title.setText("Translation (Chinese)")
        self._text.setPlainText(text.strip())
        self._show_above(anchor_global)

    def set_error(self, anchor_global: QPoint, error: str):
        self._title.setText("Translation Error")
        self._text.setPlainText(error.strip())
        self._show_above(anchor_global)

    def _show_above(self, anchor_global: QPoint):
        self.adjustSize()
        w = self.width()
        h = self.height()
        x = int(anchor_global.x() - w / 2)
        y = anchor_global.y() - h - 8

        screen = QApplication.screenAt(anchor_global)
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            x = max(rect.left() + 8, min(x, rect.right() - w - 8))
            y = max(rect.top() + 8, y)

        self.move(x, y)
        self.show()
        self.raise_()
