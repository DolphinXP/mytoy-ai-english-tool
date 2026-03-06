"""
TTS server selection dialog.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QLineEdit,
                               QLabel, QDialogButtonBox, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QFont

from ui.styles.theme import Theme


class TTSServerSelectionDialog(QDialog):
    """Dialog for selecting TTS server (local or remote)."""

    def __init__(
        self,
        current_server_type="microsoft",
        current_remote_url="ws://10.110.31.157:3000/stream",
        current_microsoft_voice="en-US-EmmaMultilingualNeural",
        current_microsoft_rate="+0%",
        parent=None,
    ):
        super().__init__(parent)
        self.current_server_type = current_server_type
        self.current_remote_url = current_remote_url
        self.current_microsoft_voice = current_microsoft_voice
        self.current_microsoft_rate = current_microsoft_rate
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("TTS Server Selection")
        self.setMinimumWidth(400)

        # Apply dark theme to dialog
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.Colors.BG_PRIMARY};
            }}
            QLabel {{
                color: {Theme.Colors.TEXT_PRIMARY};
            }}
            QRadioButton {{
                color: {Theme.Colors.TEXT_PRIMARY};
                spacing: {Theme.Spacing.SM}px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(Theme.Spacing.MD)

        # Title
        title_label = QLabel("Select TTS Server:")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(Theme.Fonts.SIZE_MEDIUM)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Microsoft server radio button (default)
        self.microsoft_radio = QRadioButton("Microsoft Read Aloud (recommended)")
        self.microsoft_radio.setChecked(self.current_server_type == "microsoft")
        self.microsoft_radio.toggled.connect(self.on_server_type_changed)
        layout.addWidget(self.microsoft_radio)

        ms_layout = QVBoxLayout()
        ms_layout.setSpacing(Theme.Spacing.SM)

        ms_voice_label = QLabel("Microsoft Voice:")
        ms_voice_label.setStyleSheet(f"margin-left: {Theme.Spacing.LG}px;")
        ms_layout.addWidget(ms_voice_label)

        self.microsoft_voice_input = QLineEdit(self.current_microsoft_voice)
        self.microsoft_voice_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {Theme.Spacing.SM}px;
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.SM}px;
                background-color: {Theme.Colors.BG_PRIMARY};
                color: {Theme.Colors.TEXT_PRIMARY};
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
        ms_layout.addWidget(self.microsoft_voice_input)

        ms_rate_label = QLabel("Microsoft Rate:")
        ms_rate_label.setStyleSheet(f"margin-left: {Theme.Spacing.LG}px;")
        ms_layout.addWidget(ms_rate_label)

        self.microsoft_rate_input = QLineEdit(self.current_microsoft_rate)
        self.microsoft_rate_input.setPlaceholderText("Example: +0%, +20%, -15%")
        self.microsoft_rate_input.setStyleSheet(self.microsoft_voice_input.styleSheet())
        ms_layout.addWidget(self.microsoft_rate_input)

        layout.addLayout(ms_layout)
        layout.addSpacing(Theme.Spacing.SM)

        # Remote server radio button
        self.remote_radio = QRadioButton("Remote Server")
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
                color: {Theme.Colors.TEXT_PRIMARY};
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
            "• Microsoft: Uses Microsoft Edge Read Aloud online service (no GPU required)\n"
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
        self.on_server_type_changed()

    def on_server_type_changed(self):
        """Handle server type radio button change."""
        is_remote = self.remote_radio.isChecked()
        is_microsoft = self.microsoft_radio.isChecked()
        self.remote_url_input.setEnabled(is_remote)
        self.microsoft_voice_input.setEnabled(is_microsoft)
        self.microsoft_rate_input.setEnabled(is_microsoft)

    def get_server_config(self):
        """
        Get the selected server configuration.

        Returns:
            Tuple of (server_type, remote_url, microsoft_voice, microsoft_rate)
        """
        if self.microsoft_radio.isChecked():
            server_type = "microsoft"
        elif self.remote_radio.isChecked():
            server_type = "remote"
        else:
            server_type = "local"
        remote_url = self.remote_url_input.text().strip()
        microsoft_voice = self.microsoft_voice_input.text().strip()
        microsoft_rate = self.microsoft_rate_input.text().strip()
        return server_type, remote_url, microsoft_voice, microsoft_rate
