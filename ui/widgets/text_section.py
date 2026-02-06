"""
Reusable text section widget with label, text display, and action buttons.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from ui.widgets.translatable_text_edit import TranslatableTextEdit
from ui.styles.theme import Theme


class TextSection(QWidget):
    """
    Reusable text section with label, text display, and optional action buttons.
    """

    copy_clicked = Signal()
    edit_clicked = Signal()
    action_clicked = Signal(str)  # Generic action signal with action name

    def __init__(self, title, read_only=True, show_copy=True, show_edit=False,
                 show_action=False, action_label="", parent=None):
        super().__init__(parent)
        self.title = title
        self._read_only = read_only
        self._show_copy = show_copy
        self._show_edit = show_edit
        self._show_action = show_action
        self._action_label = action_label

        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Theme.Spacing.SM)

        # Header layout with title and buttons
        header_layout = QHBoxLayout()
        header_layout.setSpacing(Theme.Spacing.SM)

        # Title label
        self.title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(Theme.Fonts.SIZE_MEDIUM)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)

        # Copy button
        if self._show_copy:
            self.copy_btn = QPushButton("Copy")
            self.copy_btn.setMaximumWidth(60)
            self.copy_btn.setStyleSheet(Theme.button_style("secondary"))
            self.copy_btn.clicked.connect(self._on_copy_clicked)
            header_layout.addWidget(self.copy_btn)

        # Edit button
        if self._show_edit:
            self.edit_btn = QPushButton("Edit")
            self.edit_btn.setMaximumWidth(60)
            self.edit_btn.setStyleSheet(Theme.button_style("primary"))
            self.edit_btn.clicked.connect(self._on_edit_clicked)
            header_layout.addWidget(self.edit_btn)

        # Custom action button
        if self._show_action and self._action_label:
            self.action_btn = QPushButton(self._action_label)
            self.action_btn.setMaximumWidth(80)
            self.action_btn.setStyleSheet(Theme.button_style("success"))
            self.action_btn.clicked.connect(self._on_action_clicked)
            header_layout.addWidget(self.action_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Text display
        self.text_display = TranslatableTextEdit()
        self.text_display.setFont(QFont("Microsoft YaHei", Theme.Fonts.SIZE_NORMAL))
        self.text_display.setReadOnly(self._read_only)
        self.text_display.setStyleSheet(Theme.text_edit_style())
        layout.addWidget(self.text_display)

        self.setLayout(layout)

    def set_text(self, text):
        """Set the text content."""
        self.text_display.setPlainText(text)

    def get_text(self):
        """Get the text content."""
        return self.text_display.toPlainText()

    def append_text(self, text):
        """Append text to the current content."""
        current = self.text_display.toPlainText()
        self.text_display.setPlainText(current + text)

    def set_read_only(self, read_only):
        """Set read-only state."""
        self._read_only = read_only
        self.text_display.setReadOnly(read_only)

    def is_read_only(self):
        """Check if text is read-only."""
        return self._read_only

    def set_max_height(self, height):
        """Set maximum height for text display."""
        self.text_display.setMaximumHeight(height)

    def _on_copy_clicked(self):
        """Handle copy button click."""
        text = self.get_text()
        if text and text != "Processing...":
            QApplication.clipboard().setText(text)
        self.copy_clicked.emit()

    def _on_edit_clicked(self):
        """Handle edit button click."""
        self.edit_clicked.emit()

    def _on_action_clicked(self):
        """Handle custom action button click."""
        self.action_clicked.emit(self._action_label)

    def get_text_widget(self):
        """Get the underlying text widget."""
        return self.text_display
