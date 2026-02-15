"""
Selection popup widget for AI actions on selected text.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont


class SelectionPopup(QFrame):
    """Popup widget showing selected text and AI action buttons."""

    # Signals
    correct_clicked = Signal(str)  # selected_text
    translate_clicked = Signal(str)  # selected_text
    explain_clicked = Signal(str)  # selected_text
    tts_clicked = Signal(str)  # selected_text
    create_annotation_clicked = Signal(str)  # selected_text
    close_clicked = Signal()

    def __init__(self, parent=None):
        """Initialize selection popup."""
        super().__init__(parent)
        self._selected_text = ""
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        """Set up the popup UI."""
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            SelectionPopup {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)

        self.setMinimumWidth(320)
        self.setMaximumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header with close button
        header_layout = QHBoxLayout()
        title = QLabel("Selected Text")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
        """)
        close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Selected text display
        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setMaximumHeight(100)
        self._text_display.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self._text_display)

        # AI action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._correct_btn = QPushButton("✏️ Correct")
        self._correct_btn.setToolTip("AI text correction")
        self._correct_btn.clicked.connect(lambda: self.correct_clicked.emit(self._selected_text))
        btn_layout.addWidget(self._correct_btn)

        self._translate_btn = QPushButton("🌐 Translate")
        self._translate_btn.setToolTip("Translate text")
        self._translate_btn.clicked.connect(lambda: self.translate_clicked.emit(self._selected_text))
        btn_layout.addWidget(self._translate_btn)

        self._explain_btn = QPushButton("💡 Explain")
        self._explain_btn.setToolTip("AI explanation")
        self._explain_btn.clicked.connect(lambda: self.explain_clicked.emit(self._selected_text))
        btn_layout.addWidget(self._explain_btn)

        layout.addLayout(btn_layout)

        # Second row of buttons
        btn_layout2 = QHBoxLayout()
        btn_layout2.setSpacing(8)

        self._tts_btn = QPushButton("🔊 TTS")
        self._tts_btn.setToolTip("Text to speech")
        self._tts_btn.clicked.connect(lambda: self.tts_clicked.emit(self._selected_text))
        btn_layout2.addWidget(self._tts_btn)

        self._annotate_btn = QPushButton("📝 Save")
        self._annotate_btn.setToolTip("Save as annotation")
        self._annotate_btn.clicked.connect(lambda: self.create_annotation_clicked.emit(self._selected_text))
        btn_layout2.addWidget(self._annotate_btn)

        btn_layout2.addStretch()

        layout.addLayout(btn_layout2)

        # Result display (hidden initially)
        self._result_label = QLabel("Result:")
        self._result_label.setStyleSheet("color: #666666; font-size: 10px; font-weight: bold;")
        self._result_label.hide()
        layout.addWidget(self._result_label)

        self._result_display = QTextEdit()
        self._result_display.setReadOnly(True)
        self._result_display.setMaximumHeight(120)
        self._result_display.setStyleSheet("""
            QTextEdit {
                background-color: #f0f8ff;
                border: 1px solid #cce5ff;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self._result_display.hide()
        layout.addWidget(self._result_display)

    def show_at(self, pos: QPoint, text: str):
        """
        Show popup at position with selected text.

        Args:
            pos: Global position to show popup
            text: Selected text to display
        """
        self._selected_text = text
        self._text_display.setPlainText(text)
        self._result_label.hide()
        self._result_display.hide()

        # Adjust position to stay on screen
        self.adjustSize()
        self.move(pos)
        self.show()
        self.raise_()

    def show_result(self, label: str, result: str):
        """
        Show AI result in the popup.

        Args:
            label: Result label (e.g., "Translation:", "Correction:")
            result: Result text
        """
        self._result_label.setText(label)
        self._result_label.show()
        self._result_display.setPlainText(result)
        self._result_display.show()
        self.adjustSize()

    def set_loading(self, loading: bool):
        """Set loading state for buttons."""
        self._correct_btn.setEnabled(not loading)
        self._translate_btn.setEnabled(not loading)
        self._explain_btn.setEnabled(not loading)
        self._tts_btn.setEnabled(not loading)

        if loading:
            self._result_label.setText("Processing...")
            self._result_label.show()
            self._result_display.hide()

    def _on_close(self):
        """Handle close button click."""
        self.hide()
        self.close_clicked.emit()

    def get_selected_text(self) -> str:
        """Get the currently selected text."""
        return self._selected_text
