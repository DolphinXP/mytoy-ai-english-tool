"""
Result panel for displaying AI processing results with streaming support.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class PdfTheme:
    class Colors:
        BG_PRIMARY = "#252526"
        BG_SECONDARY = "#1e1e1e"
        BORDER = "#3c3c3c"
        TEXT_PRIMARY = "#d4d4d4"
        TEXT_SECONDARY = "#a0a0a0"
        ACCENT = "#0e639c"
        ACCENT_HOVER = "#1177bb"

    @staticmethod
    def button_style(style_type="primary"):
        if style_type == "primary":
            return """
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border-radius: 4px;
                    padding: 6px 12px;
                    border: none;
                }
                QPushButton:hover { background-color: #1177bb; }
                QPushButton:disabled { background-color: #2d2d2d; color: #7f7f7f; }
            """
        return """
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border-radius: 4px;
                padding: 6px 12px;
                border: 1px solid #3f3f46;
            }
            QPushButton:hover { background-color: #414141; }
            QPushButton:disabled { background-color: #2d2d2d; color: #7f7f7f; }
        """


class ResultPanel(QFrame):
    """Panel displaying AI processing results with streaming support."""

    # Signals
    copy_clicked = Signal(str)  # text_type: 'corrected' or 'translated'
    retranslate_clicked = Signal()
    explain_clicked = Signal()
    tts_clicked = Signal()
    regenerate_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        """Initialize result panel."""
        super().__init__(parent)
        self._selected_text = ""
        self._corrected_text = ""
        self._translated_text = ""
        self._explanation = ""
        self._is_processing = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the panel UI."""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            ResultPanel {{
                background-color: {PdfTheme.Colors.BG_PRIMARY};
                border: 1px solid {PdfTheme.Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header with close button
        header = QHBoxLayout()
        title = QLabel("AI Results")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {PdfTheme.Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 12px; color: #a0a0a0; }
            QPushButton:hover { background-color: #333333; border-radius: 12px; color: #ffffff; }
        """)
        close_btn.clicked.connect(self.close_clicked.emit)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # Original text section
        content_layout.addWidget(self._section_label("Original Text"))
        self._original_display = self._create_text_display(60)
        content_layout.addWidget(self._original_display)

        # Corrected text section
        corrected_header = QHBoxLayout()
        corrected_header.addWidget(self._section_label("Corrected Text"))
        self._copy_corrected_btn = self._small_btn("Copy")
        self._copy_corrected_btn.clicked.connect(lambda: self.copy_clicked.emit("corrected"))
        corrected_header.addWidget(self._copy_corrected_btn)
        corrected_header.addStretch()
        content_layout.addLayout(corrected_header)

        self._corrected_display = self._create_text_display(80)
        content_layout.addWidget(self._corrected_display)

        # Translated text section
        trans_header = QHBoxLayout()
        trans_header.addWidget(self._section_label("Translation"))
        self._copy_trans_btn = self._small_btn("Copy")
        self._copy_trans_btn.clicked.connect(lambda: self.copy_clicked.emit("translated"))
        trans_header.addWidget(self._copy_trans_btn)
        self._retranslate_btn = self._small_btn("Retranslate")
        self._retranslate_btn.clicked.connect(self.retranslate_clicked.emit)
        trans_header.addWidget(self._retranslate_btn)
        trans_header.addStretch()
        content_layout.addLayout(trans_header)

        self._translated_display = self._create_text_display(100)
        content_layout.addWidget(self._translated_display)

        # Explanation section (collapsible)
        explain_header = QHBoxLayout()
        explain_header.addWidget(self._section_label("Explanation"))
        self._explain_btn = self._small_btn("Explain")
        self._explain_btn.clicked.connect(self.explain_clicked.emit)
        explain_header.addWidget(self._explain_btn)
        explain_header.addStretch()
        content_layout.addLayout(explain_header)

        self._explain_display = self._create_text_display(120)
        self._explain_display.hide()
        content_layout.addWidget(self._explain_display)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Status label
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {PdfTheme.Colors.TEXT_SECONDARY};
                font-size: 11px;
                padding: 4px 8px;
                background-color: {PdfTheme.Colors.BG_SECONDARY};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._status_label)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._tts_btn = QPushButton("Play TTS")
        self._tts_btn.setStyleSheet(PdfTheme.button_style("primary"))
        self._tts_btn.clicked.connect(self.tts_clicked.emit)
        btn_layout.addWidget(self._tts_btn)

        self._regenerate_btn = QPushButton("Regenerate")
        self._regenerate_btn.setStyleSheet(PdfTheme.button_style("secondary"))
        self._regenerate_btn.clicked.connect(self.regenerate_clicked.emit)
        btn_layout.addWidget(self._regenerate_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _section_label(self, text: str) -> QLabel:
        """Create a section label."""
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        label.setStyleSheet(f"color: {PdfTheme.Colors.TEXT_SECONDARY};")
        return label

    def _small_btn(self, text: str) -> QPushButton:
        """Create a small button."""
        btn = QPushButton(text)
        btn.setMaximumWidth(90)
        btn.setStyleSheet(PdfTheme.button_style("secondary"))
        return btn

    def _create_text_display(self, max_height: int) -> QTextEdit:
        """Create a text display widget."""
        display = QTextEdit()
        display.setReadOnly(True)
        display.setMaximumHeight(max_height)
        display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {PdfTheme.Colors.BG_SECONDARY};
                border: 1px solid {PdfTheme.Colors.BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                color: {PdfTheme.Colors.TEXT_PRIMARY};
            }}
        """)
        return display

    def set_original_text(self, text: str):
        """Set original selected text."""
        self._selected_text = text
        self._original_display.setPlainText(text)

    def set_corrected_text(self, text: str):
        """Set corrected text."""
        self._corrected_text = text
        self._corrected_display.setPlainText(text)

    def append_corrected_chunk(self, chunk: str):
        """Append streaming chunk to corrected text."""
        current = self._corrected_display.toPlainText()
        if current == "Correcting...":
            current = ""
        self._corrected_display.setPlainText(current + chunk)
        self._corrected_text = current + chunk

    def set_translated_text(self, text: str):
        """Set translated text."""
        self._translated_text = text
        self._translated_display.setPlainText(text)

    def append_translated_chunk(self, chunk: str):
        """Append streaming chunk to translated text."""
        current = self._translated_display.toPlainText()
        if current == "Translating...":
            current = ""
        self._translated_display.setPlainText(current + chunk)
        self._translated_text = current + chunk

    def set_explanation(self, text: str):
        """Set explanation text."""
        self._explanation = text
        self._explain_display.setPlainText(text)
        self._explain_display.show()

    def append_explain_chunk(self, chunk: str):
        """Append streaming chunk to explanation."""
        current = self._explain_display.toPlainText()
        if current == "Explaining...":
            current = ""
        self._explain_display.setPlainText(current + chunk)
        self._explanation = current + chunk
        self._explain_display.show()

    def set_status(self, status: str):
        """Set status message."""
        self._status_label.setText(status)

    def set_processing(self, processing: bool):
        """Set processing state."""
        self._is_processing = processing
        self._retranslate_btn.setEnabled(not processing)
        self._explain_btn.setEnabled(not processing)
        self._tts_btn.setEnabled(not processing)
        self._regenerate_btn.setEnabled(not processing)

    def start_correction(self):
        """Start correction display."""
        self._corrected_display.setPlainText("Correcting...")
        self.set_status("Correcting text...")
        self.set_processing(True)

    def start_translation(self):
        """Start translation display."""
        self._translated_display.setPlainText("Translating...")
        self.set_status("Translating...")

    def start_explanation(self):
        """Start explanation display."""
        self._explain_display.setPlainText("Explaining...")
        self._explain_display.show()
        self.set_status("Generating explanation...")

    def finish_processing(self):
        """Finish processing."""
        self.set_status("Ready")
        self.set_processing(False)

    def get_corrected_text(self) -> str:
        """Get corrected text."""
        return self._corrected_text

    def get_translated_text(self) -> str:
        """Get translated text."""
        return self._translated_text

    def get_explanation(self) -> str:
        """Get explanation text."""
        return self._explanation

    def clear(self):
        """Clear all displays."""
        self._selected_text = ""
        self._corrected_text = ""
        self._translated_text = ""
        self._explanation = ""
        self._original_display.clear()
        self._corrected_display.clear()
        self._translated_display.clear()
        self._explain_display.clear()
        self._explain_display.hide()
        self.set_status("Ready")
