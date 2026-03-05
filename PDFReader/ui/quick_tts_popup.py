"""Floating popup for quick TTS playback controls."""
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QApplication,
)


class QuickTTSPopup(QFrame):
    """Popup that shows quick TTS state and playback controls."""

    close_requested = Signal()
    play_requested = Signal()
    stop_requested = Signal()

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
                font-size: 11px;
            }
            QProgressBar {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                min-height: 12px;
                max-height: 12px;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #d4d4d4;
                font-size: 12px;
                padding: 4px 8px;
                min-width: 48px;
            }
            QPushButton:hover {
                background-color: #414141;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #7f7f7f;
            }
            QPushButton#closeButton {
                background-color: transparent;
                border: none;
                color: #a0a0a0;
                font-size: 12px;
                padding: 0;
                min-width: 16px;
            }
            QPushButton#closeButton:hover {
                color: #ffffff;
            }
            """
        )
        self.setMinimumWidth(240)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        self._title = QLabel("TTS")
        header.addWidget(self._title)
        header.addStretch()

        self._close_btn = QPushButton("x")
        self._close_btn.setObjectName("closeButton")
        self._close_btn.setToolTip("Close")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(self._close_btn)

        layout.addLayout(header)

        self._status = QLabel("Ready")
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)

        self._play_btn = QPushButton("Play")
        self._play_btn.clicked.connect(self.play_requested.emit)
        controls.addWidget(self._play_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        controls.addWidget(self._stop_btn)

        layout.addLayout(controls)

        self.set_playing(False)

    def show_generating(self, anchor_global: QPoint):
        self._title.setText("TTS")
        self._status.setText("Generating TTS audio...")
        self._progress.setRange(0, 0)
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._show_above(anchor_global)

    def show_ready(self, anchor_global: QPoint, duration: int):
        self._title.setText("TTS Ready")
        self._status.setText("Ready")
        max_value = max(1, int(duration))
        self._progress.setRange(0, max_value)
        self._progress.setValue(0)
        self._play_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        self.set_playing(False)
        self._show_above(anchor_global)

    def set_error(self, anchor_global: QPoint, error: str):
        self._title.setText("TTS Error")
        self._status.setText(error.strip())
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._show_above(anchor_global)

    def set_status(self, text: str):
        self._status.setText(text)

    def set_playing(self, playing: bool):
        self._play_btn.setEnabled(not playing)
        self._stop_btn.setEnabled(playing)

    def update_progress(self, value: int, maximum: int = -1):
        if maximum >= 0:
            self._progress.setRange(0, max(1, int(maximum)))
        self._progress.setValue(max(0, int(value)))

    def reset_state(self):
        self._title.setText("TTS")
        self._status.setText("Ready")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)

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
