"""
Text-to-Speech service for Quick Translation app.
"""
import pyttsx3
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread


class TTSWorker(QThread):
    """Worker thread for TTS operations."""

    finished = Signal()
    error = Signal(str)

    def __init__(self, text: str, rate: int = 150, volume: float = 0.8):
        """
        Initialize TTS worker.

        Args:
            text: Text to speak
            rate: Speech rate (words per minute)
            volume: Volume level (0.0 to 1.0)
        """
        super().__init__()
        self._text = text
        self._rate = rate
        self._volume = volume
        self._engine = None
        self._is_running = True

    def run(self) -> None:
        """Execute TTS."""
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self._rate)
            self._engine.setProperty('volume', self._volume)

            # Speak the text
            self._engine.say(self._text)
            self._engine.runAndWait()

            if self._is_running:
                self.finished.emit()
        except Exception as e:
            if self._is_running:
                self.error.emit(str(e))

    def stop(self) -> None:
        """Stop TTS."""
        self._is_running = False
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass


class TTSService(QObject):
    """
    Service for text-to-speech functionality.
    Uses pyttsx3 for offline TTS.
    """

    # Signals
    tts_started = Signal()
    tts_finished = Signal()
    tts_error = Signal(str)

    def __init__(self, parent=None, rate: int = 150, volume: float = 0.8):
        """
        Initialize TTS service.

        Args:
            parent: Parent QObject
            rate: Speech rate (words per minute)
            volume: Volume level (0.0 to 1.0)
        """
        super().__init__(parent)

        self._rate = rate
        self._volume = volume
        self._current_worker: Optional[TTSWorker] = None

    def speak(self, text: str) -> None:
        """
        Speak text.

        Args:
            text: Text to speak
        """
        # Cancel any existing TTS
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.stop()
            self._current_worker.wait()

        self.tts_started.emit()

        # Create and start TTS worker
        self._current_worker = TTSWorker(text, self._rate, self._volume)
        self._current_worker.finished.connect(self._on_finished)
        self._current_worker.error.connect(self._on_error)
        self._current_worker.start()

    def _on_finished(self) -> None:
        """Handle TTS completion."""
        self.tts_finished.emit()

    def _on_error(self, error: str) -> None:
        """Handle TTS error."""
        print(f"TTS error: {error}")
        self.tts_error.emit(error)

    def stop(self) -> None:
        """Stop current TTS."""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.stop()
            self._current_worker.wait()
            self._current_worker = None

    def is_speaking(self) -> bool:
        """Check if TTS is in progress."""
        return self._current_worker is not None and self._current_worker.isRunning()

    def set_rate(self, rate: int) -> None:
        """
        Set speech rate.

        Args:
            rate: Speech rate (words per minute)
        """
        self._rate = rate

    def set_volume(self, volume: float) -> None:
        """
        Set volume level.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self._volume = max(0.0, min(1.0, volume))

    def get_rate(self) -> int:
        """Get current speech rate."""
        return self._rate

    def get_volume(self) -> float:
        """Get current volume level."""
        return self._volume
