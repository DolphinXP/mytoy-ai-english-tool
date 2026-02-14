"""
Main popup window for AI-TTS text processing, translation, and audio playback.
Modern UI design with extracted components.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QApplication
)
from PySide6.QtCore import QTimer, QSettings, Qt as _Qt, Signal
from PySide6.QtGui import QFont

from ui.styles.theme import Theme
from ui.styles.icons import get_icon_manager
from ui.widgets.translatable_text_edit import TranslatableTextEdit, TranslatableTextBrowser
from ui.widgets.audio_controls import AudioControls
from ui.mixins import AudioMixin, DictionaryMixin, RetranslateMixin


class PopupWindow(AudioMixin, DictionaryMixin, RetranslateMixin, QWidget):
    """Main popup window for text correction, translation, and TTS."""

    exit_app_requested = Signal()
    popup_destroyed = Signal()

    def __init__(self, original_text, thread_manager=None, text_processor=None, parent=None):
        super().__init__(parent)
        self.original_text = original_text
        self.corrected_text = ""
        self.translated_text = ""
        self.thread_manager = thread_manager
        self.text_processor = text_processor

        # Icon manager
        self.icon_mgr = get_icon_manager()

        # Settings for position memory
        self.settings = QSettings('AI-TTS-App', 'PopupWindow')

        # Initialize mixin states
        self._init_audio_state()
        self._init_dictionary_state()
        self._init_retranslate_state()

        self._init_ui()
        self._restore_position()
        self._setup_auto_close_timer()

    # ── UI Construction ────────────────────────────────────────────────

    def _init_ui(self):
        """Initialize the modern UI layout."""
        self.setWindowTitle("AI-TTS - Text Correction, Translation & TTS")
        self.setMinimumSize(380, 640)
        self.setWindowFlags(self.windowFlags() | _Qt.WindowStaysOnTopHint)

        # Global window style
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.Colors.BG_PRIMARY};
                font-family: '{Theme.Fonts.FAMILY_PRIMARY}', '{Theme.Fonts.FAMILY_SECONDARY}';
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(Theme.Spacing.MD, Theme.Spacing.MD,
                                  Theme.Spacing.MD, Theme.Spacing.SM)
        layout.setSpacing(Theme.Spacing.SM)

        # ── Original Text ──
        self._build_original_section(layout)

        # ── Corrected Text ──
        self._build_corrected_section(layout)

        # ── Translated Text ──
        self._build_translated_section(layout)

        # ── Quick Dictionary ──
        self._build_dictionary_section(layout)

        # ── Status & Progress ──
        self._build_status_section(layout)

        # ── Audio Controls ──
        self._build_audio_section(layout)

        # ── Footer ──
        self._build_footer(layout)

        self.setLayout(layout)

        # Setup progress timer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)

    def _section_title(self, text, bold=True, icon_key=None):
        """Create a styled section title label."""
        display = self.icon_mgr.get_icon_label(icon_key, text) if icon_key else text
        label = QLabel(display)
        font = QFont(Theme.Fonts.FAMILY_PRIMARY, Theme.Fonts.SIZE_MEDIUM)
        font.setBold(bold)
        label.setFont(font)
        label.setStyleSheet(f"color: {Theme.Colors.TEXT_PRIMARY}; padding: 2px 0;")
        return label

    def _small_btn(self, text, style_type="secondary", max_w=60):
        """Create a small styled button."""
        btn = QPushButton(text)
        btn.setMaximumWidth(max_w)
        btn.setStyleSheet(Theme.button_style(style_type))
        return btn

    # ── Section builders ───────────────────────────────────────────────

    def _build_original_section(self, layout):
        layout.addWidget(self._section_title("Original Text"))
        self.original_text_display = TranslatableTextEdit()
        self.original_text_display.setFont(QFont(Theme.Fonts.FAMILY_SECONDARY, Theme.Fonts.SIZE_LARGE))
        self.original_text_display.setPlainText(self.original_text)
        self.original_text_display.setReadOnly(True)
        self.original_text_display.setMaximumHeight(56)
        self.original_text_display.setStyleSheet(Theme.text_edit_style())
        layout.addWidget(self.original_text_display)

    def _build_corrected_section(self, layout):
        hdr = QHBoxLayout()
        hdr.setSpacing(Theme.Spacing.SM)
        hdr.addWidget(self._section_title("AI Corrected Text"))

        self.copy_corrected_btn = self._small_btn("Copy")
        self.copy_corrected_btn.clicked.connect(lambda: self._copy_text(self.corrected_text_display))
        hdr.addWidget(self.copy_corrected_btn)

        self.edit_restore_btn = self._small_btn("Edit", "primary", 60)
        self.edit_restore_btn.clicked.connect(self._toggle_edit_restore)
        hdr.addWidget(self.edit_restore_btn)

        self.retranslate_btn = self._small_btn("Retranslate", "success", 90)
        self.retranslate_btn.clicked.connect(self._retranslate_text)
        hdr.addWidget(self.retranslate_btn)

        hdr.addStretch()
        layout.addLayout(hdr)

        self.corrected_text_display = TranslatableTextEdit()
        self.corrected_text_display.setFont(QFont(Theme.Fonts.FAMILY_SECONDARY, Theme.Fonts.SIZE_LARGE))
        self.corrected_text_display.setPlainText("Correcting...")
        self.corrected_text_display.setReadOnly(True)
        self.corrected_text_display.setStyleSheet(Theme.text_edit_style())
        self.corrected_text_display.setContextMenuPolicy(_Qt.CustomContextMenu)
        self.corrected_text_display.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.corrected_text_display, pos))
        self.corrected_text_display.text_selected.connect(
            lambda: self._show_translate_menu(self.corrected_text_display))
        layout.addWidget(self.corrected_text_display)

    def _build_translated_section(self, layout):
        hdr = QHBoxLayout()
        hdr.setSpacing(Theme.Spacing.SM)
        hdr.addWidget(self._section_title("Translated Text"))

        self.copy_translated_btn = self._small_btn("Copy")
        self.copy_translated_btn.clicked.connect(lambda: self._copy_text(self.translated_text_display))
        hdr.addWidget(self.copy_translated_btn)

        self.explain_btn = self._small_btn("Explain", "primary", 70)
        self.explain_btn.clicked.connect(self._open_explain_dialog)
        hdr.addWidget(self.explain_btn)

        hdr.addStretch()
        layout.addLayout(hdr)

        self.translated_text_display = TranslatableTextEdit()
        self.translated_text_display.setFont(QFont(Theme.Fonts.FAMILY_SECONDARY, Theme.Fonts.SIZE_LARGE))
        self.translated_text_display.setPlainText("Translating...")
        self.translated_text_display.setReadOnly(True)
        self.translated_text_display.setStyleSheet(Theme.text_edit_style())
        self.translated_text_display.setContextMenuPolicy(_Qt.CustomContextMenu)
        self.translated_text_display.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.translated_text_display, pos))
        self.translated_text_display.text_selected.connect(
            lambda: self._show_translate_menu(self.translated_text_display))
        layout.addWidget(self.translated_text_display)

    def _build_dictionary_section(self, layout):
        layout.addWidget(self._section_title("Quick Dictionary", icon_key="dictionary"))

        self.dictionary_display = TranslatableTextBrowser()
        self.dictionary_display.setFont(QFont(Theme.Fonts.FAMILY_SECONDARY, Theme.Fonts.SIZE_LARGE))
        self.dictionary_display.setPlainText(
            "Select text in Corrected/Translated sections, then right-click 'Translate' to look up here.")
        self.dictionary_display.setOpenExternalLinks(True)
        self.dictionary_display.setStyleSheet(Theme.text_edit_style())
        self.dictionary_display.setContextMenuPolicy(_Qt.CustomContextMenu)
        self.dictionary_display.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.dictionary_display, pos))
        self.dictionary_display.text_selected.connect(
            lambda: self._show_translate_menu(self.dictionary_display))
        layout.addWidget(self.dictionary_display)

    def _build_status_section(self, layout):
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.Colors.TEXT_SECONDARY};
                font-size: {Theme.Fonts.SIZE_NORMAL}px;
                padding: 4px 8px;
                background-color: {Theme.Colors.BG_SECONDARY};
                border-radius: {Theme.Radius.SM}px;
            }}
        """)
        layout.addWidget(self.status_label)

    def _build_audio_section(self, layout):
        self.audio_controls = AudioControls()
        self.audio_controls.play_clicked.connect(self._on_play)
        self.audio_controls.stop_clicked.connect(self._on_stop)
        layout.addWidget(self.audio_controls)

    def _build_footer(self, layout):
        footer = QHBoxLayout()
        footer.setSpacing(Theme.Spacing.SM)

        self.countdown_label = QLabel("Auto-close in 720s")
        self.countdown_label.setStyleSheet(f"color: {Theme.Colors.TEXT_TERTIARY}; font-size: {Theme.Fonts.SIZE_SMALL}px;")
        footer.addWidget(self.countdown_label)

        footer.addStretch()

        self.exit_app_btn = QPushButton("Exit Program")
        self.exit_app_btn.setStyleSheet(Theme.button_style("danger"))
        self.icon_mgr.set_button_icon(self.exit_app_btn, "power")
        self.exit_app_btn.clicked.connect(self._request_exit)
        footer.addWidget(self.exit_app_btn)

        layout.addLayout(footer)

    # ── Public API (called by MainApp) ─────────────────────────────────

    def set_status(self, status):
        self.status_label.setText(status)

    def update_corrected_text(self, text):
        self.corrected_text = text
        self.original_corrected_text = text
        self.corrected_text_display.setPlainText(text)

    def append_corrected_chunk(self, chunk):
        cur = self.corrected_text_display.toPlainText()
        if cur == "Correcting...":
            cur = ""
            self.original_corrected_text = ""
        new = cur + chunk
        self.corrected_text_display.setPlainText(new)
        self.original_corrected_text = new

    def update_translated_text(self, text):
        self.translated_text = text
        self.translated_text_display.setPlainText(text)

    def append_translated_chunk(self, chunk):
        cur = self.translated_text_display.toPlainText()
        if cur == "Translating...":
            cur = ""
        self.translated_text_display.setPlainText(cur + chunk)

    def set_translation_error(self, error_message):
        self.translated_text_display.setPlainText(
            f"Translation failed: {error_message}\n\nPlease try again.")
        self.set_status("Translation failed")

    # ── Window position persistence ────────────────────────────────────

    def _restore_position(self):
        pos = self.settings.value('position')
        size = self.settings.value('size')
        if pos is not None:
            self.move(pos)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
        if size is not None:
            self.resize(size)

    def _save_position(self):
        self.settings.setValue('position', self.pos())
        self.settings.setValue('size', self.size())

    def moveEvent(self, event):
        super().moveEvent(event)
        self._save_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._save_position()

    # ── Auto-close timer ───────────────────────────────────────────────

    def _setup_auto_close_timer(self):
        self.auto_close_countdown = 720
        self.auto_close_timer = QTimer()
        self.auto_close_timer.timeout.connect(self._update_countdown)
        self.auto_close_timer.start(1000)

    def _update_countdown(self):
        self.auto_close_countdown -= 1
        self.countdown_label.setText(f"Auto-close in {self.auto_close_countdown}s")
        if self.auto_close_countdown <= 0:
            self.auto_close_timer.stop()
            self.close()

    # ── Close / Exit ───────────────────────────────────────────────────

    def _request_exit(self):
        self.exit_app_requested.emit()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == _Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.popup_destroyed.emit()
        self._save_position()

        # Cleanup from mixins
        self._cleanup_audio()
        self._cleanup_dictionary()
        self._cleanup_retranslate()

        if hasattr(self, 'auto_close_timer'):
            self.auto_close_timer.stop()
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()

        event.accept()
