"""
Main popup window for AI-TTS text processing, translation, and audio playback.
Modern UI design with extracted components.
"""
import os
import time
import queue
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton,
    QLabel, QApplication, QMenu
)
from PySide6.QtCore import QTimer, QSettings, Qt as _Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QAction, QCursor

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("Warning: markdown library not installed. Dictionary will show plain text.")

from ui.styles.theme import Theme
from ui.styles.icons import get_icon_manager
from ui.widgets.translatable_text_edit import TranslatableTextEdit, TranslatableTextBrowser
from ui.widgets.text_section import TextSection
from ui.widgets.audio_controls import AudioControls
from services.audio.streaming_player import StreamingAudioPlayer
from services.audio.file_player import FileAudioPlayer


class PopupWindow(QWidget):
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

        # Dictionary state
        self.dictionary_thread = None
        self._orphan_dictionary_threads = []
        self._dictionary_markdown = ""

        # Audio state
        self.file_player = FileAudioPlayer()
        self.streaming_player = None
        self.is_streaming = False
        self.is_playing = False
        self.streaming_chunks_received = 0
        self.streaming_position_at_end = 0
        self._streaming_done = False
        self._drain_idle_ticks = 0
        self._last_stream_chunk_time = None

        # Icon manager
        self.icon_mgr = get_icon_manager()

        # Settings for position memory
        self.settings = QSettings('AI-TTS-App', 'PopupWindow')

        # Edit mode state
        self.original_corrected_text = ""
        self.is_edit_mode = False

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
        self.dictionary_display.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {Theme.Colors.BG_SECONDARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.MD}px;
                padding: {Theme.Spacing.SM}px;
            }}
        """)
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

    # ── Streaming audio ────────────────────────────────────────────────

    def start_streaming_playback(self):
        """Initialize streaming audio playback."""
        if self.streaming_player is not None:
            print("Stopping existing streaming player before starting new one")
            self.streaming_player.stop()
            if self.streaming_player.playback_thread and self.streaming_player.playback_thread.is_alive():
                self.streaming_player.playback_thread.join(timeout=2.0)
            self.streaming_player = None
            time.sleep(0.2)

        self.is_streaming = True
        self.streaming_chunks_received = 0
        self._streaming_done = False
        self._drain_idle_ticks = 0
        self._last_stream_chunk_time = None
        self.streaming_player = StreamingAudioPlayer(sample_rate=24000)
        self.streaming_player.start()
        self.is_playing = True

        self.audio_controls.set_playing(True)
        self.audio_controls.set_enabled(True)
        self.progress_timer.start(100)
        self.set_status(self.icon_mgr.get_icon_label("audio", "Streaming audio..."))
        print("Streaming playback started")

    def on_audio_chunk_ready(self, audio_bytes, sample_rate):
        """Handle incoming audio chunk for streaming playback."""
        sender = self.sender()
        if hasattr(self, 'retranslate_tts_thread') and sender != self.retranslate_tts_thread:
            return

        if not self.is_streaming:
            self.start_streaming_playback()

        self.streaming_chunks_received += 1
        self._last_stream_chunk_time = time.time()
        self._drain_idle_ticks = 0

        if self.streaming_player:
            self.streaming_player.add_audio_chunk(audio_bytes)

        self.set_status(self.icon_mgr.get_icon_label(
            "audio", f"Streaming audio... ({self.streaming_chunks_received} chunks)"))

    def stop_streaming_playback(self, wait_for_completion=False):
        """Stop streaming audio playback."""
        if self.streaming_player:
            if wait_for_completion:
                timeout_time = time.time() + 5
                while not self.streaming_player.audio_queue.empty():
                    if time.time() > timeout_time:
                        break
                    time.sleep(0.1)

            self.streaming_position_at_end = self.streaming_player.get_current_position()
            print(f"Streaming ended at position: {self.streaming_position_at_end:.2f}s")
            self.streaming_player.stop()
            if self.streaming_player.playback_thread and self.streaming_player.playback_thread.is_alive():
                self.streaming_player.playback_thread.join(timeout=2.0)
            self.streaming_player = None

        self.is_streaming = False
        self.is_playing = False
        self.audio_controls.set_playing(False)
        self.progress_timer.stop()
        self._streaming_done = False
        self._drain_idle_ticks = 0
        self.audio_controls.set_progress_range(0, 100)
        self.audio_controls.set_progress(0)
        self.audio_controls.set_time(0, self.file_player.audio_length)
        print("Streaming playback stopped")

    # ── File audio ─────────────────────────────────────────────────────

    def set_audio_ready(self, audio_file_path):
        """Called when audio file is ready for playback."""
        self.file_player.load_audio(audio_file_path)
        print(f"Audio file: {audio_file_path}, length: {self.file_player.audio_length}s")

        if self.is_streaming:
            self.set_status("Draining audio buffer...")
            self._streaming_done = True
        else:
            self.set_status(self.icon_mgr.get_icon_label("ready", "Audio ready"))

        self.audio_controls.set_enabled(True)
        self.audio_controls.set_time(0, self.file_player.audio_length)

    def set_audio_error(self, error_message):
        """Called when audio generation fails."""
        self.set_status(self.icon_mgr.get_icon_label("error", f"Audio error: {error_message}"))
        self.audio_controls.set_enabled(False)
        if self.is_streaming:
            self.stop_streaming_playback()

    # ── Playback controls ──────────────────────────────────────────────

    def _on_play(self):
        if self.is_streaming:
            self.stop_streaming_playback()
        elif not self.is_playing:
            self._start_file_playback()

    def _on_stop(self):
        if self.is_streaming:
            self.stop_streaming_playback()
        elif self.is_playing:
            self._stop_file_playback()

    def _start_file_playback(self):
        if self.file_player.play():
            self.is_playing = True
            self.audio_controls.set_playing(True)
            self.progress_timer.start(100)

    def _stop_file_playback(self):
        self.file_player.stop()
        self.is_playing = False
        self.streaming_position_at_end = 0
        self.audio_controls.set_playing(False)
        self.audio_controls.set_progress(0)
        self.audio_controls.set_time(0, self.file_player.audio_length)
        self.progress_timer.stop()
        print("Audio playback stopped")

    # ── Progress timer ─────────────────────────────────────────────────

    def _update_progress(self):
        if self.is_streaming and self.streaming_player:
            pos = self.streaming_player.get_current_position()
            secs = int(pos)
            self.audio_controls.set_time_text(f"{secs // 60:02d}:{secs % 60:02d} / --:--")
            self.audio_controls.set_progress_range(0, 0)  # indeterminate

            if self._streaming_done:
                if self.streaming_player.audio_queue.empty():
                    last = self._last_stream_chunk_time or time.time()
                    if time.time() - last >= 0.5:
                        self._drain_idle_ticks += 1
                else:
                    self._drain_idle_ticks = 0

                if self._drain_idle_ticks >= 2:
                    print("Streaming playback completed")
                    self.stop_streaming_playback(wait_for_completion=False)
                    self._streaming_done = False
                    self._drain_idle_ticks = 0
                    self.set_status(self.icon_mgr.get_icon_label("ready", "Audio ready"))
                    return

        elif self.is_playing:
            self.file_player.update_position()
            pos = self.file_player.current_position
            length = self.file_player.audio_length

            self.audio_controls.set_progress_range(0, 100)
            if length > 0:
                self.audio_controls.set_progress(min(100, (pos / length) * 100))
            self.audio_controls.set_time(pos, length)

            if self.file_player.is_finished() if hasattr(self.file_player, 'is_finished') else not self.file_player.is_busy():
                print("Audio playback completed")
                self._stop_file_playback()

    # ── Context menu & dictionary ──────────────────────────────────────

    def _copy_text(self, text_widget):
        text = text_widget.toPlainText()
        placeholder = {"Correcting...", "Translating..."}
        if text and text not in placeholder:
            QApplication.clipboard().setText(text)

    def _show_context_menu(self, text_edit, pos):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.menu_style())

        cursor = text_edit.textCursor()

        copy_action = QAction("Copy", self)
        icon = self.icon_mgr.make_menu_icon("copy")
        if not icon.isNull():
            copy_action.setIcon(icon)
        copy_action.triggered.connect(text_edit.copy)
        copy_action.setEnabled(cursor.hasSelection())
        menu.addAction(copy_action)

        sel_all_action = QAction("Select All", self)
        icon = self.icon_mgr.make_menu_icon("select_all")
        if not icon.isNull():
            sel_all_action.setIcon(icon)
        sel_all_action.triggered.connect(text_edit.selectAll)
        menu.addAction(sel_all_action)

        menu.addSeparator()

        translate_action = QAction(
            self.icon_mgr.get_icon_label("search", "Translate to Dictionary"), self)
        icon = self.icon_mgr.make_menu_icon("translate")
        if not icon.isNull():
            translate_action.setIcon(icon)
        translate_action.triggered.connect(lambda: self._translate_selected(text_edit))
        translate_action.setEnabled(cursor.hasSelection())
        menu.addAction(translate_action)

        menu.exec(text_edit.mapToGlobal(pos))

    def _show_translate_menu(self, text_edit):
        cursor = text_edit.textCursor()
        if not cursor.hasSelection():
            return

        gpos = QCursor.pos()
        gpos.setX(gpos.x() - 20)
        gpos.setY(gpos.y() - 10)

        menu = QMenu(self)
        menu.setStyleSheet(Theme.menu_style())
        action = QAction(self.icon_mgr.get_icon_label("search", "Translate to Dictionary"), self)
        icon = self.icon_mgr.make_menu_icon("translate")
        if not icon.isNull():
            action.setIcon(icon)
        action.triggered.connect(lambda: self._translate_selected(text_edit))
        menu.addAction(action)
        menu.exec(gpos)

    def _translate_selected(self, text_edit):
        cursor = text_edit.textCursor()
        selected = cursor.selectedText().strip()
        if not selected:
            return

        full_text = text_edit.toPlainText()
        self._dictionary_markdown = ""
        translating_prefix = self.icon_mgr.get_icon_label("translating", "Translating:")
        self.dictionary_display.setPlainText(f"{translating_prefix} {selected}...")

        if self.dictionary_thread and self.dictionary_thread.isRunning():
            self._stop_dictionary_thread(immediate=True)

        from services.api.dictionary import DictionaryThread
        self.dictionary_thread = DictionaryThread(selected, full_text)
        self.dictionary_thread.translation_chunk.connect(self._on_dict_chunk)
        self.dictionary_thread.translation_done.connect(self._on_dict_done)
        self.dictionary_thread.start()

    def _stop_dictionary_thread(self, immediate=False):
        if not self.dictionary_thread or not self.dictionary_thread.isRunning():
            return
        try:
            self.dictionary_thread.translation_chunk.disconnect()
            self.dictionary_thread.translation_done.disconnect()
        except:
            pass
        self.dictionary_thread.stop()
        if immediate:
            if not self.dictionary_thread.wait(150):
                self.dictionary_thread.terminate()
                self.dictionary_thread.wait(150)
        else:
            self.dictionary_thread.finished.connect(self._cleanup_orphan_threads)
            self._orphan_dictionary_threads.append(self.dictionary_thread)
        self.dictionary_thread = None

    def _cleanup_orphan_threads(self):
        self._orphan_dictionary_threads = [t for t in self._orphan_dictionary_threads if t.isRunning()]

    def _on_dict_chunk(self, chunk):
        self._dictionary_markdown += chunk
        self._render_dictionary()

    def _on_dict_done(self, result):
        if self._dictionary_markdown:
            self._render_dictionary()

    def _render_dictionary(self):
        scrollbar = self.dictionary_display.verticalScrollBar()
        scroll_pos = scrollbar.value()

        if HAS_MARKDOWN:
            html = markdown.markdown(self._dictionary_markdown, extensions=['extra', 'nl2br', 'sane_lists'])
            styled = f"""
            <style>
                body {{ font-family: '{Theme.Fonts.FAMILY_SECONDARY}', sans-serif; line-height: 1.6; }}
                h1, h2, h3 {{ color: {Theme.Colors.GRAY_800}; margin-top: 10px; }}
                strong {{ color: {Theme.Colors.PRIMARY}; }}
                code {{ background-color: {Theme.Colors.GRAY_100}; padding: 2px 5px; border-radius: 3px; }}
                ul, ol {{ margin-left: 20px; }}
                p {{ margin: 5px 0; }}
            </style>
            {html}
            """
            self.dictionary_display.setHtml(styled)
        else:
            self.dictionary_display.setPlainText(self._dictionary_markdown)

        scrollbar.setValue(scroll_pos)

    # ── Edit / Retranslate ─────────────────────────────────────────────

    def _toggle_edit_restore(self):
        if self.is_edit_mode:
            self.corrected_text_display.setPlainText(self.original_corrected_text)
            self.corrected_text = self.original_corrected_text
            self.corrected_text_display.setReadOnly(True)
            self.edit_restore_btn.setText("Edit")
            self.edit_restore_btn.setStyleSheet(Theme.button_style("primary"))
            self.is_edit_mode = False
        else:
            self.corrected_text_display.setPlainText(self.original_corrected_text)
            self.corrected_text_display.setReadOnly(False)
            self.edit_restore_btn.setText("Restore")
            self.edit_restore_btn.setStyleSheet(Theme.button_style("danger"))
            self.is_edit_mode = True
            self.corrected_text_display.setFocus()

    def _retranslate_text(self):
        current_time = time.time()
        if hasattr(self, '_last_retranslate_time') and (current_time - self._last_retranslate_time) < 1.0:
            return
        self._last_retranslate_time = current_time

        text = self.corrected_text_display.toPlainText().strip()
        if not text:
            return

        self.corrected_text = text
        self.translated_text_display.setPlainText("Translating...")
        self.set_status("Retranslating and regenerating audio...")

        if self.is_streaming:
            self.stop_streaming_playback()
            time.sleep(0.1)
        elif self.is_playing:
            self._stop_file_playback()

        self.audio_controls.set_enabled(False)

        # Start translation
        from services.api.translation import TranslationThread
        if hasattr(self, 'retranslation_thread') and self.retranslation_thread and self.retranslation_thread.isRunning():
            self.retranslation_thread.terminate()
            self.retranslation_thread.wait(1000)

        self.retranslation_thread = TranslationThread(text, 'deepseek')
        self.retranslation_thread.translation_done.connect(self._on_retranslation_done)
        self.retranslation_thread.translation_chunk.connect(self._on_retranslation_chunk)
        self.retranslation_thread.translation_error.connect(self._on_retranslation_error)
        self.retranslation_thread.start()

        # Start TTS
        self._start_retranslate_tts(text)

    def _on_retranslation_chunk(self, chunk):
        cur = self.translated_text_display.toPlainText()
        if cur == "Translating...":
            cur = ""
        self.translated_text_display.setPlainText(cur + chunk)

    def _on_retranslation_done(self, text):
        self.translated_text = text
        self.translated_text_display.setPlainText(text)
        if hasattr(self, 'retranslate_tts_thread') and self.retranslate_tts_thread and self.retranslate_tts_thread.isRunning():
            self.set_status("Retranslation done. Generating audio...")
        self.retranslation_thread = None

    def _on_retranslation_error(self, msg):
        self.translated_text_display.setPlainText(f"Translation failed: {msg}\n\nPlease try again.")
        self.set_status("Translation failed")
        self.retranslation_thread = None

    def _start_retranslate_tts(self, tts_text):
        try:
            from services.tts.remote_tts import RemoteTTSManager
            remote_manager = RemoteTTSManager()

            if hasattr(self, 'retranslate_tts_thread') and self.retranslate_tts_thread:
                try:
                    self.retranslate_tts_thread.tts_completed.disconnect()
                    self.retranslate_tts_thread.tts_error.disconnect()
                    self.retranslate_tts_thread.progress_update.disconnect()
                    self.retranslate_tts_thread.audio_chunk_ready.disconnect()
                except:
                    pass
                if self.retranslate_tts_thread.isRunning():
                    self.retranslate_tts_thread.stop()
                    if not self.retranslate_tts_thread.wait(3000):
                        self.retranslate_tts_thread.terminate()
                        self.retranslate_tts_thread.wait(1000)
                self.retranslate_tts_thread = None

            time.sleep(1.0)

            self.retranslate_tts_thread = remote_manager.create_tts_thread(
                text=tts_text,
                server_url="ws://10.110.31.157:3000/stream",
                streaming=True
            )
            self.retranslate_tts_thread.tts_completed.connect(lambda p: self.set_audio_ready(p))
            self.retranslate_tts_thread.tts_error.connect(lambda m: self.set_audio_error(m))
            self.retranslate_tts_thread.progress_update.connect(lambda m: self.set_status(m))
            self.retranslate_tts_thread.audio_chunk_ready.connect(self.on_audio_chunk_ready)
            self.retranslate_tts_thread.start()

        except Exception as e:
            print(f"Failed to start retranslate TTS: {e}")
            self.set_audio_error(f"Failed to start TTS: {str(e)}")

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

    def closeEvent(self, event):
        self.popup_destroyed.emit()
        self._save_position()

        if self.is_streaming:
            self.stop_streaming_playback()
        if self.is_playing:
            self._stop_file_playback()

        if hasattr(self, 'auto_close_timer'):
            self.auto_close_timer.stop()
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()

        # Stop dictionary thread
        if self.dictionary_thread and self.dictionary_thread.isRunning():
            try:
                self.dictionary_thread.translation_chunk.disconnect()
                self.dictionary_thread.translation_done.disconnect()
            except:
                pass
            self.dictionary_thread.stop()
            if not self.dictionary_thread.wait(1000):
                self.dictionary_thread.terminate()
                self.dictionary_thread.wait(500)
            self.dictionary_thread = None

        # Stop retranslation thread
        if hasattr(self, 'retranslation_thread') and self.retranslation_thread and self.retranslation_thread.isRunning():
            try:
                self.retranslation_thread.translation_chunk.disconnect()
                self.retranslation_thread.translation_done.disconnect()
                self.retranslation_thread.translation_error.disconnect()
            except:
                pass
            self.retranslation_thread.terminate()
            self.retranslation_thread.wait(1000)
            self.retranslation_thread = None

        # Stop retranslate TTS thread
        if hasattr(self, 'retranslate_tts_thread') and self.retranslate_tts_thread and self.retranslate_tts_thread.isRunning():
            try:
                self.retranslate_tts_thread.tts_completed.disconnect()
                self.retranslate_tts_thread.tts_error.disconnect()
                self.retranslate_tts_thread.progress_update.disconnect()
                self.retranslate_tts_thread.audio_chunk_ready.disconnect()
            except:
                pass
            self.retranslate_tts_thread.stop()
            if not self.retranslate_tts_thread.wait(5000):
                self.retranslate_tts_thread.terminate()
                self.retranslate_tts_thread.wait(1000)
            self.retranslate_tts_thread = None

        # Clean up audio file
        self.file_player.cleanup()

        event.accept()
