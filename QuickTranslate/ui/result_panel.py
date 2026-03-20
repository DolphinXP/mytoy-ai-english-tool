"""
Result panel for Quick Translation app.
"""
from typing import Optional
from PySide6.QtCore import Signal, Slot, Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QApplication, QSizePolicy
)
from PySide6.QtGui import QFont, QKeyEvent

from config import config


class ResultPanel(QWidget):
    """
    Panel for displaying translation results.
    Rolls down from input box with smooth animation.
    """

    # Signals
    new_translation_requested = Signal()

    def __init__(self, parent=None):
        """Initialize result panel."""
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

        # Animation
        self._slide_animation = None
        self._fade_animation = None

        # Auto-hide timer
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide_panel)

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

        # Original text section
        original_label = QLabel("Original:")
        original_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        original_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        layout.addWidget(original_label)

        self._original_text = QLabel()
        self._original_text.setFont(QFont("Arial", 12))
        self._original_text.setStyleSheet("color: white;")
        self._original_text.setWordWrap(True)
        self._original_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._original_text)

        # Translation section
        translation_label = QLabel("Translation:")
        translation_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        translation_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        layout.addWidget(translation_label)

        self._translation_text = QLabel()
        self._translation_text.setFont(QFont("Arial", 12))
        self._translation_text.setStyleSheet("color: white;")
        self._translation_text.setWordWrap(True)
        self._translation_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._translation_text)

        # Copied indicator
        self._copied_label = QLabel("📋 Copied to clipboard")
        self._copied_label.setFont(QFont("Arial", 10))
        self._copied_label.setStyleSheet("color: rgba(66, 133, 244, 0.8);")
        self._copied_label.hide()
        layout.addWidget(self._copied_label)

        # New translation button
        new_button = QPushButton("New Translation")
        new_button.setFont(QFont("Arial", 11))
        new_button.setStyleSheet("""
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
        """)
        new_button.clicked.connect(self.new_translation_requested.emit)
        layout.addWidget(new_button)

        # Set stylesheet for the widget
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
            }
        """)

        # Set fixed width
        self.setFixedWidth(400)

    def show_result(self, original: str, translation: str, input_y: Optional[int] = None) -> None:
        """
        Show translation result.

        Args:
            original: Original English text
            translation: Chinese translation
            input_y: Y position of input window (optional)
        """
        # Update text
        self._original_text.setText(original)
        self._translation_text.setText(translation)

        # Show copied indicator
        self._copied_label.show()

        # Position at center of screen
        self._position_center(input_y)

        # Show with slide-down animation
        self._show_with_animation()

        # Start auto-hide timer (10 seconds)
        self._auto_hide_timer.start(10000)

    def update_translation(self, translation: str) -> None:
        """
        Update translation text (for streaming).

        Args:
            translation: Updated translation text
        """
        self._translation_text.setText(translation)

    def show_error(self, error: str, input_y: Optional[int] = None) -> None:
        """
        Show error message.

        Args:
            error: Error message
            input_y: Y position of input window (optional)
        """
        self._original_text.setText("Error")
        self._translation_text.setText(error)
        self._copied_label.hide()

        # Position at center of screen
        self._position_center(input_y)

        # Show with animation
        self._show_with_animation()

        # Start auto-hide timer (5 seconds for errors)
        self._auto_hide_timer.start(5000)

    def _position_center(self, input_y: Optional[int] = None) -> None:
        """Position the panel at the same Y position as input window, centered horizontally."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            # Use same Y position as input window if provided, otherwise center vertically
            if input_y is not None:
                y = input_y
            else:
                y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _show_with_animation(self) -> None:
        """Show the panel with slide-down animation."""
        # Store initial position
        start_pos = self.pos()
        end_pos = start_pos

        # Start from above (hidden)
        self.move(start_pos.x(), start_pos.y() - 50)

        # Show the window
        self.show()
        self.activateWindow()

        # Slide-down animation
        self._slide_animation = QPropertyAnimation(self, b"pos")
        self._slide_animation.setDuration(config.get('ui.animation_duration', 300))
        self._slide_animation.setStartValue(self.pos())
        self._slide_animation.setEndValue(end_pos)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_animation.start()

        # Fade-in animation
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(config.get('ui.animation_duration', 300))
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(config.get_ui_opacity())
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation.start()

    def hide_panel(self) -> None:
        """Hide the panel with slide-up animation."""
        # Stop auto-hide timer
        self._auto_hide_timer.stop()

        # Slide-up animation
        self._slide_animation = QPropertyAnimation(self, b"pos")
        self._slide_animation.setDuration(config.get('ui.animation_duration', 300))
        self._slide_animation.setStartValue(self.pos())
        self._slide_animation.setEndValue(QPoint(self.pos().x(), self.pos().y() - 50))
        self._slide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._slide_animation.finished.connect(self._on_slide_up_finished)
        self._slide_animation.start()

        # Fade-out animation
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(config.get('ui.animation_duration', 300))
        self._fade_animation.setStartValue(config.get_ui_opacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_animation.start()

    @Slot()
    def _on_slide_up_finished(self) -> None:
        """Handle slide-up animation completion."""
        self.hide()

    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        # Reset auto-hide timer on interaction
        self._auto_hide_timer.start(10000)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide_panel()
        else:
            super().keyPressEvent(event)
