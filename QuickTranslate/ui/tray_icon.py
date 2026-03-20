"""
System tray icon for Quick Translation app.
"""
from typing import Optional

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from config import config


class TrayIcon(QSystemTrayIcon):
    """
    System tray icon with context menu.
    Provides access to app features and settings.
    """

    # Signals
    show_input_requested = Signal()
    show_history_requested = Signal()
    show_settings_requested = Signal()
    service_changed = Signal(str)
    exit_requested = Signal()

    def __init__(self, parent=None):
        """Initialize tray icon."""
        super().__init__(parent)

        # Set icon (use a simple icon for now)
        self._setup_icon()

        # Create context menu
        self._create_context_menu()

        # Connect signals
        self.activated.connect(self._on_activated)

        # Set tooltip
        self.setToolTip(f"{config.APP_NAME} v{config.APP_VERSION}")

    def _setup_icon(self) -> None:
        """Setup tray icon."""
        # Create a simple icon using text
        # In a real app, you'd use an actual icon file
        from PySide6.QtGui import QPixmap, QPainter, QFont
        from PySide6.QtCore import Qt

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 40, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
        painter.end()

        self.setIcon(QIcon(pixmap))

    def _create_context_menu(self) -> None:
        """Create context menu."""
        menu = QMenu()

        # Show input action
        show_input_action = QAction("Show Translation Window", self)
        show_input_action.triggered.connect(self.show_input_requested.emit)
        menu.addAction(show_input_action)

        # Show history action
        show_history_action = QAction("Translation History", self)
        show_history_action.triggered.connect(self.show_history_requested.emit)
        menu.addAction(show_history_action)

        menu.addSeparator()

        # AI Service submenu
        service_menu = menu.addMenu("AI Service")

        # DeepSeek action
        deepseek_action = QAction("DeepSeek", self)
        deepseek_action.setCheckable(True)
        deepseek_action.setChecked(config.get_current_service() == "deepseek")
        deepseek_action.triggered.connect(lambda: self._on_service_selected("deepseek"))
        service_menu.addAction(deepseek_action)

        # Ollama action
        ollama_action = QAction("Ollama", self)
        ollama_action.setCheckable(True)
        ollama_action.setChecked(config.get_current_service() == "ollama")
        ollama_action.triggered.connect(lambda: self._on_service_selected("ollama"))
        service_menu.addAction(ollama_action)

        menu.addSeparator()

        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_requested.emit)
        menu.addAction(exit_action)

        # Set context menu
        self.setContextMenu(menu)

    @Slot(str)
    def _on_service_selected(self, service_name: str) -> None:
        """Handle service selection."""
        self.service_changed.emit(service_name)

        # Update menu checkmarks
        menu = self.contextMenu()
        if menu:
            for action in menu.actions():
                if action.text() in ["DeepSeek", "Ollama"]:
                    action.setChecked(action.text().lower() == service_name)

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_input_requested.emit()

    def set_translating(self, translating: bool) -> None:
        """
        Set translating state.

        Args:
            translating: Whether translation is in progress
        """
        if translating:
            self.setToolTip(f"{config.APP_NAME} - Translating...")
            # Could change icon to indicate translating state
        else:
            self.setToolTip(f"{config.APP_NAME} v{config.APP_VERSION}")
