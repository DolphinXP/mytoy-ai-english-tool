"""
History manager for Quick Translation app.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtCore import QObject, Signal


class HistoryManager(QObject):
    """
    Manages translation history.
    Stores recent translations for quick access.
    """

    # Signals
    history_updated = Signal()

    def __init__(self, parent=None, max_items: int = 20):
        """
        Initialize history manager.

        Args:
            parent: Parent QObject
            max_items: Maximum number of history items to keep
        """
        super().__init__(parent)

        self._max_items = max_items
        self._history_file = Path(__file__).parent.parent / "history.json"
        self._history: List[Dict[str, Any]] = []

        # Load existing history
        self._load_history()

    def _load_history(self) -> None:
        """Load history from file."""
        if self._history_file.exists():
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading history: {e}")
                self._history = []
        else:
            self._history = []

    def _save_history(self) -> None:
        """Save history to file."""
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving history: {e}")

    def add_translation(self, original: str, translation: str) -> None:
        """
        Add a translation to history.

        Args:
            original: Original English text
            translation: Chinese translation
        """
        # Create history item
        item = {
            "original": original,
            "translation": translation,
            "timestamp": datetime.now().isoformat()
        }

        # Add to beginning of list
        self._history.insert(0, item)

        # Trim to max items
        if len(self._history) > self._max_items:
            self._history = self._history[:self._max_items]

        # Save to file
        self._save_history()

        # Emit signal
        self.history_updated.emit()

    def get_history(self) -> List[Dict[str, Any]]:
        """Get all history items."""
        return self._history.copy()

    def get_recent(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent history items."""
        return self._history[:count]

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search history for matching text.

        Args:
            query: Search query

        Returns:
            List of matching history items
        """
        query_lower = query.lower()
        results = []

        for item in self._history:
            if (query_lower in item['original'].lower() or
                    query_lower in item['translation'].lower()):
                results.append(item)

        return results

    def clear(self) -> None:
        """Clear all history."""
        self._history = []
        self._save_history()
        self.history_updated.emit()

    def remove_item(self, index: int) -> None:
        """
        Remove a history item by index.

        Args:
            index: Index of item to remove
        """
        if 0 <= index < len(self._history):
            self._history.pop(index)
            self._save_history()
            self.history_updated.emit()

    def get_item(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Get a history item by index.

        Args:
            index: Index of item to get

        Returns:
            History item or None if index is invalid
        """
        if 0 <= index < len(self._history):
            return self._history[index]
        return None

    def count(self) -> int:
        """Get number of history items."""
        return len(self._history)

    def set_max_items(self, max_items: int) -> None:
        """
        Set maximum number of history items.

        Args:
            max_items: Maximum number of items to keep
        """
        self._max_items = max_items
        if len(self._history) > max_items:
            self._history = self._history[:max_items]
            self._save_history()
