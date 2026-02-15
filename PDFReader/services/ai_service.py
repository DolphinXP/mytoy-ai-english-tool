"""
AI service for text processing operations.

Provides text correction, translation, and explanation using AI models.
"""
import sys
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QThread

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class AIResult:
    """Result from AI operation."""
    success: bool
    result: str
    error: str = ""


class AIWorker(QThread):
    """Worker thread for AI operations."""

    finished = Signal(AIResult)

    def __init__(self, operation: Callable, text: str, **kwargs):
        """Initialize worker."""
        super().__init__()
        self._operation = operation
        self._text = text
        self._kwargs = kwargs

    def run(self):
        """Execute AI operation."""
        try:
            result = self._operation(self._text, **self._kwargs)
            self.finished.emit(AIResult(success=True, result=result))
        except Exception as e:
            self.finished.emit(AIResult(success=False, result="", error=str(e)))


class AIService(QObject):
    """
    Service for AI-powered text operations.

    Provides async methods for text correction, translation, and explanation.
    """

    # Signals
    operation_started = Signal(str)  # operation_name
    operation_completed = Signal(str, AIResult)  # operation_name, result
    operation_failed = Signal(str, str)  # operation_name, error

    def __init__(self, parent=None):
        """Initialize AI service."""
        super().__init__(parent)
        self._current_worker: Optional[AIWorker] = None
        self._api_client = None
        self._init_api_client()

    def _init_api_client(self):
        """Initialize API client from parent project if available."""
        try:
            # Try to import from parent AI-TTS project
            from AI_TTS.services.ai_service import AIService as ParentAIService
            self._api_client = ParentAIService()
        except ImportError:
            # Fallback - will use mock implementations
            self._api_client = None

    def correct_text(self, text: str, callback: Optional[Callable] = None) -> None:
        """
        Correct text using AI.

        Args:
            text: Text to correct
            callback: Optional callback(AIResult)
        """
        self._run_operation("correct", self._do_correct, text, callback)

    def translate_text(self, text: str, target_language: str = "Chinese",
                       callback: Optional[Callable] = None) -> None:
        """
        Translate text using AI.

        Args:
            text: Text to translate
            target_language: Target language
            callback: Optional callback(AIResult)
        """
        self._run_operation("translate", self._do_translate, text, callback,
                           target_language=target_language)

    def explain_text(self, text: str, callback: Optional[Callable] = None) -> None:
        """
        Explain text using AI.

        Args:
            text: Text to explain
            callback: Optional callback(AIResult)
        """
        self._run_operation("explain", self._do_explain, text, callback)

    def _run_operation(self, name: str, operation: Callable, text: str,
                       callback: Optional[Callable], **kwargs):
        """Run an AI operation in background thread."""
        # Cancel any existing operation
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.terminate()
            self._current_worker.wait()

        self.operation_started.emit(name)

        self._current_worker = AIWorker(operation, text, **kwargs)

        def on_finished(result: AIResult):
            if result.success:
                self.operation_completed.emit(name, result)
            else:
                self.operation_failed.emit(name, result.error)
            if callback:
                callback(result)

        self._current_worker.finished.connect(on_finished)
        self._current_worker.start()

    def _do_correct(self, text: str, **kwargs) -> str:
        """Perform text correction."""
        if self._api_client:
            return self._api_client.correct_text(text)

        # Mock implementation for standalone use
        # In production, this would call an actual AI API
        return text  # Return original text as placeholder

    def _do_translate(self, text: str, target_language: str = "Chinese", **kwargs) -> str:
        """Perform translation."""
        if self._api_client:
            return self._api_client.translate_text(text, target_language)

        # Mock implementation
        return f"[Translation to {target_language}]: {text}"

    def _do_explain(self, text: str, **kwargs) -> str:
        """Perform explanation."""
        if self._api_client:
            return self._api_client.explain_text(text)

        # Mock implementation
        return f"[Explanation]: This text discusses: {text[:100]}..."

    def cancel(self):
        """Cancel current operation."""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.terminate()
            self._current_worker.wait()
            self._current_worker = None
