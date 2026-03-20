"""
Input popup window for Quick Translation app.
"""
from PySide6.QtCore import Signal, Slot, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QApplication
)
from PySide6.QtGui import QFont, QKeyEvent

from config import config


class InputPopup(QWidget):
    """
    Popup window for entering text to translate.
    Semi-transparent overlay design with always-on-top behavior.
    """

    # Signals
    translation_requested = Signal(str)
    popup_hidden = Signal()

    def __init__(self, parent=None):
        """Initialize input popup."""
        super().__init__(parent)

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

        # Center on screen
        self._center_on_screen()

        # Animation
        self._fade_animation = None

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Title label
        title_label = QLabel("🔤 Quick Translation")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        # Input field
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Enter English text to translate...")
        self._input_field.setFont(QFont("Arial", 12))
        self._input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 10px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.6);
            }
        """)
        self._input_field.returnPressed.connect(self._on_translate_clicked)
        layout.addWidget(self._input_field)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Translate button
        self._translate_button = QPushButton("Translate")
        self._translate_button.setFont(QFont("Arial", 11))
        self._translate_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(66, 133, 244, 0.8);
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(66, 133, 244, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(66, 133, 244, 0.6);
            }
        """)
        self._translate_button.clicked.connect(self._on_translate_clicked)
        button_layout.addWidget(self._translate_button)

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 11))
        cancel_button.setStyleSheet("""
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
        cancel_button.clicked.connect(self.hide_popup)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # Set stylesheet for the widget
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
            }
        """)

        # Set fixed width
        self.setFixedWidth(400)

    def _center_on_screen(self) -> None:
        """Center the popup on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def show_popup(self) -> None:
        """Show the popup with fade-in animation."""
        # Clear input field
        self._input_field.clear()

        # Show the window
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Set focus to input field - try immediately and with delay as backup
        self._input_field.setFocus()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._input_field.setFocus)

        # Fade-in animation
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(config.get('ui.animation_duration', 300))
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(config.get_ui_opacity())
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation.start()

    def hide_popup(self) -> None:
        """Hide the popup with fade-out animation."""
        # Fade-out animation
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(config.get('ui.animation_duration', 300))
        self._fade_animation.setStartValue(config.get_ui_opacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_animation.finished.connect(self._on_fade_out_finished)
        self._fade_animation.start()

    @Slot()
    def _on_fade_out_finished(self) -> None:
        """Handle fade-out animation completion."""
        self.hide()
        self.popup_hidden.emit()

    @Slot()
    def _on_translate_clicked(self) -> None:
        """Handle translate button click."""
        text = self._input_field.text().strip()
        if text:
            self.translation_requested.emit(text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide_popup()
        else:
            super().keyPressEvent(event)
