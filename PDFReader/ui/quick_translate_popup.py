"""Floating popup for quick translation results."""
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QApplication,
)


class QuickTranslatePopup(QFrame):
    """Non-intrusive popup that shows quick translation text."""

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging = False
        self._drag_offset = QPoint()
        self._user_resized = False
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        # Use a normal tool window so users can resize it with native borders.
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
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
                font-size: 14px;
                font-family: Tahoma, Consolas, "Courier New", monospace;
            }
            QPushButton#closeButton {
                background-color: transparent;
                border: none;
                color: #a0a0a0;
                font-size: 12px;
                padding: 0;
            }
            QPushButton#closeButton:hover {
                color: #ffffff;
            }
            """
        )
        self.setMinimumSize(260, 140)
        self.resize(360, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        self._title = QLabel("Translation")
        header.addWidget(self._title)
        header.addStretch()

        self._close_btn = QPushButton("x")
        self._close_btn.setObjectName("closeButton")
        self._close_btn.setToolTip("Close")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.clicked.connect(self._on_close_clicked)
        header.addWidget(self._close_btn)

        layout.addLayout(header)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

    def show_loading(self, anchor_global: QPoint, avoid_rect: QRect | None = None):
        self._title.setText("Translation")
        self._text.setPlainText("Translating...")
        self._show_near(anchor_global, avoid_rect)

    def start_streaming(self, anchor_global: QPoint, avoid_rect: QRect | None = None):
        """Prepare popup for incremental translation output."""
        self._title.setText("Translation (Chinese)")
        self._text.clear()
        self._show_near(anchor_global, avoid_rect)

    def append_stream_chunk(self, chunk: str):
        """Append one streamed chunk without repositioning the popup."""
        if not chunk:
            return
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(chunk)
        self._text.setTextCursor(cursor)

    def show_correcting(self, anchor_global: QPoint, avoid_rect: QRect | None = None):
        self._title.setText("Translation")
        self._text.setPlainText("Correcting...")
        self._show_near(anchor_global, avoid_rect)

    def set_result(self, anchor_global: QPoint, text: str, avoid_rect: QRect | None = None):
        self._title.setText("Translation (Chinese)")
        self._text.setPlainText(text.strip())
        self._show_near(anchor_global, avoid_rect)

    def set_error(self, anchor_global: QPoint, error: str, avoid_rect: QRect | None = None):
        self._title.setText("Translation Error")
        self._text.setPlainText(error.strip())
        self._show_near(anchor_global, avoid_rect)

    def _show_near(self, anchor_global: QPoint, avoid_rect: QRect | None = None):
        if not self._user_resized:
            self.adjustSize()
            self.resize(max(self.width(), 320), max(self.height(), 170))
        w = self.width()
        h = self.height()
        margin = 8
        gap = 12
        x = int(anchor_global.x() - w / 2)
        y = anchor_global.y() - h - gap

        screen = QApplication.screenAt(anchor_global)
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            min_x = rect.left() + margin
            max_x = rect.right() - w - margin
            min_y = rect.top() + margin
            max_y = rect.bottom() - h - margin

            def _clamp(px: int, py: int) -> tuple[int, int]:
                return (
                    max(min_x, min(px, max_x)),
                    max(min_y, min(py, max_y)),
                )

            x, y = _clamp(x, y)

            valid_avoid = (
                isinstance(avoid_rect, QRect)
                and not avoid_rect.isNull()
                and avoid_rect.width() > 0
                and avoid_rect.height() > 0
            )

            if valid_avoid:
                center_x = avoid_rect.center().x()
                center_y = avoid_rect.center().y()
                candidates = [
                    # Prefer below first to keep prior lines visible.
                    _clamp(center_x - int(w / 2), avoid_rect.bottom() + gap),
                    _clamp(avoid_rect.right() + gap, center_y - int(h / 2)),
                    _clamp(avoid_rect.left() - w - gap, center_y - int(h / 2)),
                    _clamp(center_x - int(w / 2), avoid_rect.top() - h - gap),
                    # Fallback around anchor.
                    _clamp(anchor_global.x() - int(w / 2), anchor_global.y() + gap),
                    _clamp(anchor_global.x() - int(w / 2), anchor_global.y() - h - gap),
                ]

                best_pos = (x, y)
                best_overlap = None
                for cx, cy in candidates:
                    popup_rect = QRect(cx, cy, w, h)
                    if not popup_rect.intersects(avoid_rect):
                        best_pos = (cx, cy)
                        best_overlap = 0
                        break

                    inter = popup_rect.intersected(avoid_rect)
                    overlap = inter.width() * inter.height()
                    if best_overlap is None or overlap < best_overlap:
                        best_overlap = overlap
                        best_pos = (cx, cy)

                x, y = best_pos

        self.move(x, y)
        self.show()
        self.raise_()

    def _on_close_clicked(self):
        self.close_requested.emit()

    def resizeEvent(self, event):
        if self.isVisible():
            self._user_resized = True
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)
