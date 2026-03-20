"""
Translation service for Quick Translation app.
"""
import sys
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal, QThread

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.api.translation import TranslationThread


class TranslationService(QObject):
    """
    Service for AI-powered translation.
    Wraps the parent project's TranslationThread for use in Quick Translation.
    """

    # Signals
    translation_started = Signal()
    translation_chunk = Signal(str)  # Streaming chunk
    translation_completed = Signal(str)  # Full translation
    translation_error = Signal(str)  # Error message

    def __init__(self, parent=None):
        """Initialize translation service."""
        super().__init__(parent)
        self._current_thread: Optional[TranslationThread] = None
        self._full_translation = ""

    def translate(self, text: str, service_name: Optional[str] = None) -> None:
        """
        Translate text to Chinese.

        Args:
            text: Text to translate
            service_name: Optional service name (uses config default if not specified)
        """
        # Cancel any existing translation
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.stop()
            self._current_thread.wait()

        self._full_translation = ""
        self.translation_started.emit()

        # Create and start translation thread
        self._current_thread = TranslationThread(
            text_to_translate=text,
            api_config=service_name
        )

        # Connect signals
        self._current_thread.translation_chunk.connect(self._on_chunk)
        self._current_thread.translation_done.connect(self._on_done)
        self._current_thread.translation_error.connect(self._on_error)

        # Start translation
        self._current_thread.start()

    def _on_chunk(self, chunk: str) -> None:
        """Handle streaming chunk."""
        self._full_translation += chunk
        self.translation_chunk.emit(chunk)

    def _on_done(self, translation: str) -> None:
        """Handle translation completion."""
        self._full_translation = translation
        self.translation_completed.emit(translation)

    def _on_error(self, error: str) -> None:
        """Handle translation error."""
        self.translation_error.emit(error)

    def cancel(self) -> None:
        """Cancel current translation."""
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.stop()
            self._current_thread.wait()
            self._current_thread = None

    def is_translating(self) -> bool:
        """Check if translation is in progress."""
        return self._current_thread is not None and self._current_thread.isRunning()
