"""
Retranslate mixin for PopupWindow.
Handles edit mode and retranslation functionality.
"""
import time

from ui.styles.theme import Theme


class RetranslateMixin:
    """Mixin providing edit and retranslate functionality."""

    def _init_retranslate_state(self):
        """Initialize retranslate-related state variables."""
        self.original_corrected_text = ""
        self.is_edit_mode = False
        self.retranslation_thread = None
        self.retranslate_tts_thread = None
        self._last_retranslate_time = 0

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
        if (current_time - self._last_retranslate_time) < 1.0:
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
        if self.retranslation_thread and self.retranslation_thread.isRunning():
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
        if self.retranslate_tts_thread and self.retranslate_tts_thread.isRunning():
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

            if self.retranslate_tts_thread:
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

    def _cleanup_retranslate(self):
        """Clean up retranslate threads on close."""
        # Stop retranslation thread
        if self.retranslation_thread and self.retranslation_thread.isRunning():
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
        if self.retranslate_tts_thread and self.retranslate_tts_thread.isRunning():
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
