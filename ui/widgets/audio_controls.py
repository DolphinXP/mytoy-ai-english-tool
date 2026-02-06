"""
Audio controls widget with play/stop button, progress bar, and time display.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QProgressBar, QLabel
from PySide6.QtCore import Signal, QSize

from ui.styles.theme import Theme
from ui.styles.icons import get_icon_manager


class AudioControls(QWidget):
    """
    Audio control panel with play/stop button, progress bar, and time display.
    """

    play_clicked = Signal()
    stop_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.icon_manager = get_icon_manager()
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Theme.Spacing.SM)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(Theme.progress_bar_style())
        layout.addWidget(self.progress_bar)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(Theme.Spacing.MD)

        # Play/Stop button
        self.play_stop_btn = QPushButton("Play")
        self.play_stop_btn.setEnabled(False)
        self.play_stop_btn.setStyleSheet(Theme.button_style("primary"))
        self.play_stop_btn.clicked.connect(self._on_play_stop_clicked)
        self._update_play_button_icon()
        controls_layout.addWidget(self.play_stop_btn)

        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet(Theme.label_style())
        controls_layout.addWidget(self.time_label)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)
        self.setLayout(layout)

    def _update_play_button_icon(self):
        """Update play/stop button icon and text."""
        if self.is_playing:
            self.play_stop_btn.setText("Stop")
            self.icon_manager.set_button_icon(self.play_stop_btn, "stop")
        else:
            self.play_stop_btn.setText("Play")
            self.icon_manager.set_button_icon(self.play_stop_btn, "play")

    def _on_play_stop_clicked(self):
        """Handle play/stop button click."""
        if self.is_playing:
            self.stop_clicked.emit()
        else:
            self.play_clicked.emit()

    def set_playing(self, playing):
        """
        Set playing state.

        Args:
            playing: True if playing, False if stopped
        """
        self.is_playing = playing
        self._update_play_button_icon()

    def set_enabled(self, enabled):
        """Enable or disable the play button."""
        self.play_stop_btn.setEnabled(enabled)

    def set_progress(self, value):
        """
        Set progress bar value.

        Args:
            value: Progress value (0-100)
        """
        self.progress_bar.setValue(int(value))

    def set_progress_range(self, minimum, maximum):
        """
        Set progress bar range.

        Args:
            minimum: Minimum value
            maximum: Maximum value
        """
        self.progress_bar.setMinimum(minimum)
        self.progress_bar.setMaximum(maximum)

    def set_time(self, current_seconds, total_seconds):
        """
        Set time display.

        Args:
            current_seconds: Current position in seconds
            total_seconds: Total duration in seconds
        """
        current_time = self._format_time(current_seconds)
        total_time = self._format_time(total_seconds)
        self.time_label.setText(f"{current_time} / {total_time}")

    def set_time_text(self, text):
        """Set time display text directly."""
        self.time_label.setText(text)

    def _format_time(self, seconds):
        """Format seconds into MM:SS format."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def reset(self):
        """Reset the audio controls to initial state."""
        self.is_playing = False
        self._update_play_button_icon()
        self.progress_bar.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        self.play_stop_btn.setEnabled(False)
