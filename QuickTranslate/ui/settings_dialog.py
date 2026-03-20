"""
Settings dialog for Quick Translation app.
"""
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtGui import QFont

from config import config


class SettingsDialog(QDialog):
    """
    Dialog for configuring application settings.
    """

    # Signals
    settings_saved = Signal()

    def __init__(self, parent=None):
        """Initialize settings dialog."""
        super().__init__(parent)

        self.setWindowTitle(f"{config.APP_NAME} - Settings")
        self.setFixedSize(500, 400)

        # Setup UI
        self._setup_ui()

        # Load current settings
        self._load_settings()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Settings")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # Hotkey group
        hotkey_group = QGroupBox("Hotkey")
        hotkey_layout = QFormLayout()

        self._hotkey_input = QLineEdit()
        self._hotkey_input.setPlaceholderText("<ctrl>+<alt>+q")
        hotkey_layout.addRow("Hotkey combination:", self._hotkey_input)

        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)

        # AI Service group
        service_group = QGroupBox("AI Service")
        service_layout = QFormLayout()

        self._service_combo = QComboBox()
        self._service_combo.addItems(["deepseek", "ollama"])
        service_layout.addRow("Current service:", self._service_combo)

        service_group.setLayout(service_layout)
        layout.addWidget(service_group)

        # UI group
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()

        self._opacity_spin = QDoubleSpinBox()
        self._opacity_spin.setRange(0.5, 1.0)
        self._opacity_spin.setSingleStep(0.05)
        self._opacity_spin.setDecimals(2)
        ui_layout.addRow("Window opacity:", self._opacity_spin)

        self._animation_spin = QSpinBox()
        self._animation_spin.setRange(100, 1000)
        self._animation_spin.setSingleStep(50)
        self._animation_spin.setSuffix(" ms")
        ui_layout.addRow("Animation duration:", self._animation_spin)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # TTS group
        tts_group = QGroupBox("Text-to-Speech")
        tts_layout = QFormLayout()

        self._tts_rate_spin = QSpinBox()
        self._tts_rate_spin.setRange(50, 300)
        self._tts_rate_spin.setSingleStep(10)
        tts_layout.addRow("Speech rate:", self._tts_rate_spin)

        self._tts_volume_spin = QDoubleSpinBox()
        self._tts_volume_spin.setRange(0.0, 1.0)
        self._tts_volume_spin.setSingleStep(0.1)
        self._tts_volume_spin.setDecimals(1)
        tts_layout.addRow("Volume:", self._tts_volume_spin)

        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)

        # History group
        history_group = QGroupBox("History")
        history_layout = QFormLayout()

        self._history_max_spin = QSpinBox()
        self._history_max_spin.setRange(5, 100)
        self._history_max_spin.setSingleStep(5)
        history_layout.addRow("Max history items:", self._history_max_spin)

        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Save button
        save_button = QPushButton("Save")
        save_button.setFont(QFont("Arial", 11))
        save_button.setStyleSheet("""
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
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)

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
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _load_settings(self) -> None:
        """Load current settings into UI."""
        # Hotkey
        self._hotkey_input.setText(config.get_hotkey())

        # Service
        current_service = config.get_current_service()
        index = self._service_combo.findText(current_service)
        if index >= 0:
            self._service_combo.setCurrentIndex(index)

        # UI
        self._opacity_spin.setValue(config.get_ui_opacity())
        self._animation_spin.setValue(config.get('ui.animation_duration', 300))

        # TTS
        self._tts_rate_spin.setValue(config.get_tts_rate())
        self._tts_volume_spin.setValue(config.get('tts.volume', 0.8))

        # History
        self._history_max_spin.setValue(config.get_history_max_items())

    @Slot()
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        # Validate hotkey
        hotkey = self._hotkey_input.text().strip()
        if not hotkey:
            QMessageBox.warning(self, "Invalid Hotkey", "Please enter a valid hotkey combination.")
            return

        # Save settings
        config.set_hotkey(hotkey)
        config.set_current_service(self._service_combo.currentText())
        config.set_ui_opacity(self._opacity_spin.value())
        config.set('ui.animation_duration', self._animation_spin.value())
        config.set_tts_rate(self._tts_rate_spin.value())
        config.set('tts.volume', self._tts_volume_spin.value())
        config.set_history_max_items(self._history_max_spin.value())

        # Emit signal
        self.settings_saved.emit()

        # Show success message
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")

        # Close dialog
        self.accept()
