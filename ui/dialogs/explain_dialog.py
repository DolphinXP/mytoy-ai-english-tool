"""
Explain dialog for AI-powered Q&A about text content.
"""
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QTextBrowser, QPushButton, QSplitter, QWidget
)
from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from ui.styles.theme import Theme
from ui.styles.icons import get_icon_manager
from services.api.explain import ExplainThread


class ExplainDialog(QDialog):
    """Dialog for asking AI questions about the text content."""

    def __init__(self, corrected_text, translated_text, initial_question="", parent=None):
        super().__init__(parent)
        self.corrected_text = corrected_text
        self.translated_text = translated_text
        self.initial_question = initial_question
        self.explain_thread = None
        self._response_markdown = ""
        self.icon_mgr = get_icon_manager()
        self.settings = QSettings('AI-TTS-App', 'ExplainDialog')

        self._init_ui()
        self._restore_geometry()

        # Auto-run if initial question provided
        if self.initial_question:
            self.question_input.setPlainText(self.initial_question)
            # Use QTimer to run after dialog is shown
            QTimer.singleShot(100, self._on_ask)

    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Explain - Ask AI")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Apply dark theme
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.Colors.BG_PRIMARY};
            }}
            QLabel {{
                color: {Theme.Colors.TEXT_PRIMARY};
            }}
            QSplitter::handle {{
                background-color: {Theme.Colors.BORDER_LIGHT};
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(Theme.Spacing.MD, Theme.Spacing.MD,
                                  Theme.Spacing.MD, Theme.Spacing.MD)
        layout.setSpacing(Theme.Spacing.SM)

        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # ── Question Input Section ──
        question_widget = QWidget()
        question_layout = QVBoxLayout(question_widget)
        question_layout.setContentsMargins(0, 0, 0, 0)
        question_layout.setSpacing(Theme.Spacing.XS)

        question_label = QLabel("Your Question:")
        question_label.setFont(QFont(Theme.Fonts.FAMILY_PRIMARY, Theme.Fonts.SIZE_MEDIUM))
        question_label.setStyleSheet(f"color: {Theme.Colors.TEXT_PRIMARY}; font-weight: bold;")
        question_layout.addWidget(question_label)

        self.question_input = QTextEdit()
        self.question_input.setFont(QFont(Theme.Fonts.FAMILY_SECONDARY, Theme.Fonts.SIZE_LARGE))
        self.question_input.setPlaceholderText(
            "Ask any question about the text...\n"
            "Examples:\n"
            "- What does 'xxx' mean in this context?\n"
            "- Explain the grammar of this sentence\n"
            "- Why is this word used here?"
        )
        self.question_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.Colors.BG_PRIMARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.MD}px;
                padding: {Theme.Spacing.SM}px;
            }}
            QTextEdit:focus {{
                border: 1px solid {Theme.Colors.PRIMARY};
            }}
        """)
        self.question_input.setMinimumHeight(60)
        question_layout.addWidget(self.question_input, 1)  # stretch factor 1 to fill space

        # Ctrl+Enter shortcut to submit
        self.submit_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.submit_shortcut.activated.connect(self._on_ask)

        # Ask button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Theme.Spacing.SM)
        btn_layout.setContentsMargins(0, Theme.Spacing.SM, 0, Theme.Spacing.SM)

        btn_layout.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(Theme.button_style("secondary"))
        self.clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.clear_btn)

        self.ask_btn = QPushButton("Ask AI")
        self.ask_btn.setStyleSheet(Theme.button_style("primary"))
        self.icon_mgr.set_button_icon(self.ask_btn, "search")
        self.ask_btn.clicked.connect(self._on_ask)
        btn_layout.addWidget(self.ask_btn)

        question_layout.addLayout(btn_layout)
        splitter.addWidget(question_widget)

        # ── Response Section ──
        response_widget = QWidget()
        response_layout = QVBoxLayout(response_widget)
        response_layout.setContentsMargins(0, Theme.Spacing.SM, 0, 0)
        response_layout.setSpacing(Theme.Spacing.XS)

        response_header = QHBoxLayout()
        response_label = QLabel("AI Response:")
        response_label.setFont(QFont(Theme.Fonts.FAMILY_PRIMARY, Theme.Fonts.SIZE_MEDIUM))
        response_label.setStyleSheet(f"color: {Theme.Colors.TEXT_PRIMARY}; font-weight: bold;")
        response_header.addWidget(response_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {Theme.Colors.TEXT_SECONDARY}; font-size: {Theme.Fonts.SIZE_SMALL}px;")
        response_header.addWidget(self.status_label)

        response_header.addStretch()

        self.copy_response_btn = QPushButton("Copy")
        self.copy_response_btn.setMaximumWidth(60)
        self.copy_response_btn.setStyleSheet(Theme.button_style("secondary"))
        self.copy_response_btn.clicked.connect(self._copy_response)
        response_header.addWidget(self.copy_response_btn)

        response_layout.addLayout(response_header)

        self.response_display = QTextBrowser()
        self.response_display.setFont(QFont(Theme.Fonts.FAMILY_SECONDARY, Theme.Fonts.SIZE_LARGE))
        self.response_display.setPlainText("Ask a question to get AI explanation...")
        self.response_display.setOpenExternalLinks(True)
        self.response_display.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {Theme.Colors.BG_SECONDARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.MD}px;
                padding: {Theme.Spacing.SM}px;
            }}
        """)
        response_layout.addWidget(self.response_display)

        splitter.addWidget(response_widget)

        # Set initial splitter sizes (30% question, 70% response)
        splitter.setSizes([150, 350])

        layout.addWidget(splitter)

        # ── Footer ──
        footer = QHBoxLayout()
        footer.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet(Theme.button_style("secondary"))
        self.close_btn.clicked.connect(self.close)
        footer.addWidget(self.close_btn)

        layout.addLayout(footer)

        self.setLayout(layout)

    def _on_ask(self):
        """Handle ask button click."""
        question = self.question_input.toPlainText().strip()
        if not question:
            return

        # Stop any existing thread
        self._stop_explain_thread()

        # Reset response
        self._response_markdown = ""
        self.response_display.setPlainText("Thinking...")
        self.status_label.setText("Generating...")
        self.ask_btn.setEnabled(False)

        # Start explain thread
        self.explain_thread = ExplainThread(
            question=question,
            corrected_text=self.corrected_text,
            translated_text=self.translated_text
        )
        self.explain_thread.explain_chunk.connect(self._on_chunk)
        self.explain_thread.explain_done.connect(self._on_done)
        self.explain_thread.start()

    def _on_chunk(self, chunk):
        """Handle streaming chunk."""
        self._response_markdown += chunk
        self._render_response()

    def _on_done(self, result):
        """Handle completion."""
        self.status_label.setText("Done")
        self.ask_btn.setEnabled(True)
        if self._response_markdown:
            self._render_response()

    def _render_response(self):
        """Render markdown response."""
        scrollbar = self.response_display.verticalScrollBar()
        scroll_pos = scrollbar.value()

        if HAS_MARKDOWN:
            html = markdown.markdown(
                self._response_markdown,
                extensions=['extra', 'nl2br', 'sane_lists']
            )
            styled = f"""
            <style>
                body {{ font-family: '{Theme.Fonts.FAMILY_SECONDARY}', sans-serif; line-height: 1.6; }}
                h1, h2, h3 {{ color: {Theme.Colors.GRAY_300}; margin-top: 10px; }}
                strong {{ color: {Theme.Colors.PRIMARY_LIGHT}; }}
                code {{ background-color: {Theme.Colors.GRAY_600}; color: {Theme.Colors.GRAY_100}; padding: 2px 5px; border-radius: 3px; }}
                pre {{ background-color: {Theme.Colors.GRAY_700}; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                ul, ol {{ margin-left: 20px; }}
                p {{ margin: 5px 0; }}
            </style>
            {html}
            """
            self.response_display.setHtml(styled)
        else:
            self.response_display.setPlainText(self._response_markdown)

        scrollbar.setValue(scroll_pos)

    def _copy_response(self):
        """Copy response to clipboard."""
        from PySide6.QtWidgets import QApplication
        text = self._response_markdown or self.response_display.toPlainText()
        if text and text != "Ask a question to get AI explanation...":
            QApplication.clipboard().setText(text)

    def _clear_all(self):
        """Clear question and response."""
        self._stop_explain_thread()
        self.question_input.clear()
        self._response_markdown = ""
        self.response_display.setPlainText("Ask a question to get AI explanation...")
        self.status_label.setText("")

    def _stop_explain_thread(self):
        """Stop the explain thread if running."""
        if self.explain_thread and self.explain_thread.isRunning():
            try:
                self.explain_thread.explain_chunk.disconnect()
                self.explain_thread.explain_done.disconnect()
            except:
                pass
            self.explain_thread.stop()
            if not self.explain_thread.wait(1000):
                self.explain_thread.terminate()
                self.explain_thread.wait(500)
            self.explain_thread = None
        self.ask_btn.setEnabled(True)

    def _restore_geometry(self):
        """Restore window geometry from settings."""
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def _save_geometry(self):
        """Save window geometry to settings."""
        self.settings.setValue('geometry', self.saveGeometry())

    def closeEvent(self, event):
        """Handle close event."""
        self._stop_explain_thread()
        self._save_geometry()
        event.accept()
