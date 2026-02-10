"""
Floating context menu that appears on middle-click for text operations.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QApplication
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QCursor

from ui.styles.theme import Theme


class FloatingContextMenu(QWidget):
    """
    A floating context menu that appears near the cursor
    and provides quick actions for selected text.
    """
    process_text_requested = Signal(str)  # Emits the text to process
    copy_requested = Signal(str)
    menu_closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_text = ""
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        # Frameless, always on top, tool window (no taskbar entry)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.Popup
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Style the widget
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.Colors.BG_PRIMARY};
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.LG}px;
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(
            Theme.Spacing.SM, Theme.Spacing.SM,
            Theme.Spacing.SM, Theme.Spacing.SM
        )
        layout.setSpacing(Theme.Spacing.XS)

        # Process with AI-TTS button
        self.process_btn = self._create_button(
            "🎯 Process with AI-TTS", "primary")
        self.process_btn.clicked.connect(self._on_process)
        layout.addWidget(self.process_btn)

        # Copy button
        self.copy_btn = self._create_button(
            "📋 Copy", "secondary")
        self.copy_btn.clicked.connect(self._on_copy)
        layout.addWidget(self.copy_btn)

        self.setLayout(layout)
        self.adjustSize()

    def _create_button(self, text: str, style_type: str) -> QPushButton:
        """Create a styled button."""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.Colors.BG_SECONDARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                border: none;
                padding: {Theme.Spacing.SM}px {Theme.Spacing.MD}px;
                border-radius: {Theme.Radius.SM}px;
                font-size: {Theme.Fonts.SIZE_NORMAL}px;
                text-align: left;
                min-width: 160px;
            }}
            QPushButton:hover {{
                background-color: {Theme.Colors.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Theme.Colors.PRIMARY_HOVER};
            }}
        """)
        return btn

    def show_at(self, x: int, y: int, text: str = None):
        """
        Show the menu at the specified screen coordinates.

        Args:
            x: Screen X coordinate (physical pixels from pynput)
            y: Screen Y coordinate (physical pixels from pynput)
            text: Optional text to use. If None, will try to get from clipboard.
        """
        self._selected_text = text or ""

        # If no text provided, try to get selected text via clipboard simulation
        if not self._selected_text:
            self._selected_text = self._get_selected_text()

        if not self._selected_text.strip():
            print("No text selected, not showing menu")
            return

        # Convert physical pixel coordinates (from pynput) to logical pixel
        # coordinates (for Qt). On Windows with DPI scaling (e.g. 125%, 150%),
        # pynput reports raw physical pixels while Qt uses logical pixels.
        screen = QApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        logical_x = int(x / dpr)
        logical_y = int(y / dpr)

        # Position the menu near the cursor but ensure it's on screen
        screen_geo = screen.geometry()
        menu_width = self.sizeHint().width()
        menu_height = self.sizeHint().height()

        # Adjust position to keep menu on screen
        if logical_x + menu_width > screen_geo.right():
            logical_x = screen_geo.right() - menu_width - 10
        if logical_y + menu_height > screen_geo.bottom():
            logical_y = screen_geo.bottom() - menu_height - 10
        if logical_x < screen_geo.left():
            logical_x = screen_geo.left() + 10
        if logical_y < screen_geo.top():
            logical_y = screen_geo.top() + 10

        self.move(logical_x, logical_y)
        self.show()
        self.raise_()
        self.activateWindow()

    def _get_selected_text(self) -> str:
        """
        Try to get the currently selected text.
        This simulates Ctrl+C to copy selected text.
        """
        import time
        from pynput.keyboard import Controller, Key

        clipboard = QApplication.clipboard()

        # Save current clipboard content
        old_clipboard = clipboard.text()

        # Simulate Ctrl+C
        keyboard = Controller()
        try:
            keyboard.press(Key.ctrl)
            keyboard.press('c')
            keyboard.release('c')
            keyboard.release(Key.ctrl)

            # Small delay for clipboard to update
            time.sleep(0.1)

            # Get new clipboard content
            new_text = clipboard.text()

            # Restore old clipboard if we got nothing new
            if new_text == old_clipboard:
                return ""

            return new_text

        except Exception as e:
            print(f"Error getting selected text: {e}")
            return ""

    def _on_process(self):
        """Handle process button click."""
        if self._selected_text.strip():
            self.process_text_requested.emit(self._selected_text)
        self.close()

    def _on_copy(self):
        """Handle copy button click."""
        if self._selected_text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(self._selected_text)
            self.copy_requested.emit(self._selected_text)
        self.close()

    def closeEvent(self, event):
        """Handle close event."""
        self.menu_closed.emit()
        super().closeEvent(event)

    def focusOutEvent(self, event):
        """Close menu when it loses focus."""
        super().focusOutEvent(event)
        # Use timer to allow button clicks to process first
        QTimer.singleShot(100, self._check_close)

    def _check_close(self):
        """Check if we should close the menu."""
        if not self.isActiveWindow():
            self.close()
