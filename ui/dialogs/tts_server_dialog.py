"""
TTS server selection dialog.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QLineEdit,
                               QLabel, QDialogButtonBox, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QFont

from ui.styles.theme import Theme


class TTSServerSelectionDialog(QDialog):
    """Dialog for selecting TTS server (local or remote)."""

    def __init__(self, current_server_type="remote", current_remote_url="ws://10.110.31.157:3000/stream", parent=None):
        super().__init__(parent)
        self.current_server_type = current_server_type
        self.current_remote_url = current_remote_url
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("TTS Server Selection")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.setSpacing(Theme.Spacing.MD)

        # Title
        title_label = QLabel("Select TTS Server:")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(Theme.Fonts.SIZE_MEDIUM)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Remote server radio button (default)
        self.remote_radio = QRadioButton("Remote Server (recommended)")
        self.remote_radio.setChecked(self.current_server_type == "remote")
        self.remote_radio.toggled.connect(self.on_server_type_changed)
        layout.addWidget(self.remote_radio)

        # Remote server URL input
        url_layout = QVBoxLayout()
        url_layout.setSpacing(Theme.Spacing.SM)

        url_label = QLabel("Remote Server URL:")
        url_label.setStyleSheet(f"margin-left: {Theme.Spacing.LG}px;")
        url_layout.addWidget(url_label)

        self.remote_url_input = QLineEdit(self.current_remote_url)
        self.remote_url_input.setEnabled(self.current_server_type == "remote")
        self.remote_url_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {Theme.Spacing.SM}px;
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.SM}px;
                background-color: {Theme.Colors.BG_PRIMARY};
                margin-left: {Theme.Spacing.LG}px;
                margin-right: {Theme.Spacing.LG}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {Theme.Colors.PRIMARY};
            }}
            QLineEdit:disabled {{
                background-color: {Theme.Colors.BG_SECONDARY};
                color: {Theme.Colors.TEXT_SECONDARY};
            }}
        """)
        url_layout.addWidget(self.remote_url_input)

        layout.addLayout(url_layout)
        layout.addSpacing(Theme.Spacing.SM)

        # Local server radio button
        self.local_radio = QRadioButton("Local Server (requires GPU)")
        self.local_radio.setChecked(self.current_server_type == "local")
        self.local_radio.toggled.connect(self.on_server_type_changed)
        layout.addWidget(self.local_radio)

        layout.addSpacing(Theme.Spacing.MD)

        # Info text
        info_label = QLabel("Info:")
        info_font = QFont()
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)

        info_text = QLabel()
        info_text.setWordWrap(True)
        info_text.setText(
            "• Remote: Uses a remote WebSocket server for TTS (faster, no GPU required)\n"
            "• Local: Runs TTS locally on your machine (requires GPU with CUDA support)"
        )
        info_text.setStyleSheet(f"""
            QLabel {{
                color: {Theme.Colors.TEXT_SECONDARY};
                padding: {Theme.Spacing.SM}px;
                background-color: {Theme.Colors.BG_SECONDARY};
                border-radius: {Theme.Radius.SM}px;
            }}
        """)
        layout.addWidget(info_text)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Style the buttons
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setStyleSheet(Theme.button_style("primary"))
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setStyleSheet(Theme.button_style("secondary"))

        layout.addWidget(button_box)

        self.setLayout(layout)

    def on_server_type_changed(self):
        """Handle server type radio button change."""
        is_remote = self.remote_radio.isChecked()
        self.remote_url_input.setEnabled(is_remote)

    def get_server_config(self):
        """
        Get the selected server configuration.

        Returns:
            Tuple of (server_type, remote_url)
        """
        server_type = "remote" if self.remote_radio.isChecked() else "local"
        remote_url = self.remote_url_input.text().strip()
        return server_type, remote_url
