"""
AI processing controller for text correction, translation, and explanation.
"""
from typing import Optional
from PySide6.QtCore import QObject, Signal

from core.thread_manager import ThreadManager
from services.api.text_correction import TextCorrectionThread
from services.api.translation import TranslationThread
from services.api.explain import ExplainThread
from services.tts.remote_tts import RemoteTTSThread


class AIProcessor(QObject):
    """Handles AI processing pipeline: correction -> translation -> TTS."""

    correction_chunk = Signal(str)
    correction_done = Signal(str)
    correction_error = Signal(str)
    translation_chunk = Signal(str)
    translation_done = Signal(str)
    translation_error = Signal(str)
    explain_chunk = Signal(str)
    explain_done = Signal(str)
    tts_started = Signal()
    tts_completed = Signal(str)  # audio file path
    tts_finished = Signal()
    tts_error = Signal(str)

    def __init__(self, thread_manager: ThreadManager, parent=None):
        super().__init__(parent)
        self._thread_manager = thread_manager
        self._explain_thread: Optional[ExplainThread] = None

    def start_correction(self, text: str):
        """Start text correction processing."""
        thread = TextCorrectionThread(text)
        thread.correction_chunk.connect(self.correction_chunk.emit)
        thread.correction_done.connect(self.correction_done.emit)
        thread.correction_error.connect(self.correction_error.emit)
        self._thread_manager.set_correction_thread(thread)
        thread.start()

    def start_translation(self, text: str):
        """Start translation processing."""
        thread = TranslationThread(text)
        thread.translation_chunk.connect(self.translation_chunk.emit)
        thread.translation_done.connect(self.translation_done.emit)
        thread.translation_error.connect(self.translation_error.emit)
        self._thread_manager.set_translation_thread(thread)
        thread.start()

    def start_explanation(self, corrected_text: str, translated_text: str = ""):
        """Start AI explanation processing."""
        thread = ExplainThread(
            question="Please explain this text, including vocabulary, grammar, and meaning.",
            corrected_text=corrected_text,
            translated_text=translated_text
        )
        thread.explain_chunk.connect(self.explain_chunk.emit)
        thread.explain_done.connect(self._on_explain_done)
        self._explain_thread = thread
        thread.start()

    def _on_explain_done(self, explanation: str):
        """Handle explanation completion."""
        self.explain_done.emit(explanation)
        self._explain_thread = None  # Allow garbage collection

    def start_tts(self, text: str):
        """Start text-to-speech generation."""
        try:
            self.tts_started.emit()
            thread = RemoteTTSThread(text)
            thread.tts_completed.connect(self.tts_completed.emit)
            thread.tts_error.connect(self.tts_error.emit)
            thread.finished.connect(self.tts_finished.emit)
            self._thread_manager.set_tts_thread(thread)
            thread.start()
        except Exception as e:
            self.tts_error.emit(str(e))

    def stop_all(self):
        """Stop all running threads."""
        self._thread_manager.stop_all_threads()
        self._explain_thread = None
