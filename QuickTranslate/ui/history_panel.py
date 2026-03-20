"""
History panel for Quick Translation app.
"""
from typing import Optional

from PySide6.QtCore import Signal, Slot, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QApplication, QMessageBox
)
from PySide6.QtGui import QFont

from config import config
from core.history_manager import HistoryManager


class HistoryPanel(QWidget):
    """
    Panel for viewing and managing translation history.
    """

    # Signals
    translation_selected = Signal(str, str)  # original, translation

    def __init__(self, history_manager: HistoryManager, parent=None):
        """
        Initialize history panel.

        Args:
            history_manager: History manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self._history_manager = history_manager

        # Window flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Set window opacity
        self.setWindowOpacity(config.get_ui_opacity())

        # Setup UI
        self._setup_ui()

        # Connect signals
        self._history_manager.history_updated.connect(self._refresh_history)

        # Initial refresh
        self._refresh_history()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Title label
        title_label = QLabel("📚 Translation History")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        # Search box
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search history...")
        self._search_box.setFont(QFont("Arial", 11))
        self._search_box.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 8px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.6);
            }
        """)
        self._search_box.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self._search_box)

        # History list
        self._history_list = QListWidget()
        self._history_list.setFont(QFont("Arial", 11))
        self._history_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(66, 133, 244, 0.3);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self._history_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._history_list)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Clear history button
        clear_button = QPushButton("Clear History")
        clear_button.setFont(QFont("Arial", 11))
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(234, 67, 53, 0.8);
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(234, 67, 53, 1.0);
            }
        """)
        clear_button.clicked.connect(self._on_clear_clicked)
        button_layout.addWidget(clear_button)

        # Close button
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Arial", 11))
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 8px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        close_button.clicked.connect(self.hide_panel)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # Set stylesheet for the widget
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
            }
        """)

        # Set fixed size
        self.setFixedSize(500, 400)

    def _refresh_history(self) -> None:
        """Refresh the history list."""
        self._history_list.clear()

        history = self._history_manager.get_history()
        for item in history:
            # Create list item text
            original = item['original']
            translation = item['translation']
            timestamp = item.get('timestamp', '')

            # Truncate long text
            if len(original) > 50:
                original = original[:50] + "..."
            if len(translation) > 50:
                translation = translation[:50] + "..."

            # Format timestamp
            if timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    timestamp = ""

            # Create display text
            display_text = f"{original}\n→ {translation}"
            if timestamp:
                display_text += f"\n[{timestamp}]"

            # Create list item
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._history_list.addItem(list_item)

    @Slot(str)
    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text change."""
        if not text:
            self._refresh_history()
            return

        # Search history
        results = self._history_manager.search(text)

        # Update list
        self._history_list.clear()
        for item in results:
            original = item['original']
            translation = item['translation']

            # Truncate long text
            if len(original) > 50:
                original = original[:50] + "..."
            if len(translation) > 50:
                translation = translation[:50] + "..."

            display_text = f"{original}\n→ {translation}"

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._history_list.addItem(list_item)

    @Slot(QListWidgetItem)
    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle item double click."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            original = data['original']
            translation = data['translation']
            self.translation_selected.emit(original, translation)
            self.hide_panel()

    @Slot()
    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._history_manager.clear()

    def show_panel(self) -> None:
        """Show the history panel."""
        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

        # Show the window
        self.show()
        self.activateWindow()
        self._search_box.setFocus()

    def hide_panel(self) -> None:
        """Hide the history panel."""
        self.hide()
