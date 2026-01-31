import sys
import time
import re

from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox,
                               QDialog, QVBoxLayout, QRadioButton, QPushButton,
                               QLineEdit, QLabel, QDialogButtonBox)
from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon, QPixmap

from PopupWindow import PopupWindow
from GlobalShortcutHandler import GlobalShortcutHandler
from ClipboardCapture import ClipboardCapture
from TextCorrectionThread import TextCorrectionThread
from TranslationThread import TranslationThread
from VibeVoiceTTS import VibeVoiceModelManager
from VibeVoiceTTSRemote import VibeVoiceTTSRemoteManager


class TTSServerSelectionDialog(QDialog):
    """Dialog for selecting TTS server (local or remote)"""

    def __init__(self, current_server_type="remote", current_remote_url="ws://10.110.31.157:3000/stream", parent=None):
        super().__init__(parent)
        self.current_server_type = current_server_type
        self.current_remote_url = current_remote_url
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("TTS Server Selection")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Select TTS Server:")
        title_font = title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Remote server radio button (default)
        self.remote_radio = QRadioButton("Remote Server (recommended)")
        self.remote_radio.setChecked(self.current_server_type == "remote")
        self.remote_radio.toggled.connect(self.on_server_type_changed)
        layout.addWidget(self.remote_radio)

        # Remote server URL input
        url_layout = QVBoxLayout()
        url_label = QLabel("Remote Server URL:")
        url_layout.addWidget(url_label)

        self.remote_url_input = QLineEdit(self.current_remote_url)
        self.remote_url_input.setEnabled(self.current_server_type == "remote")
        url_layout.addWidget(self.remote_url_input)

        # Add indent for URL input
        from PySide6.QtWidgets import QSpacerItem
        url_layout.addSpacerItem(QSpacerItem(20, 10))
        layout.addLayout(url_layout)

        # Local server radio button
        self.local_radio = QRadioButton("Local Server (requires GPU)")
        self.local_radio.setChecked(self.current_server_type == "local")
        self.local_radio.toggled.connect(self.on_server_type_changed)
        layout.addWidget(self.local_radio)

        # Info text
        info_label = QLabel("\nInfo:")
        info_font = info_label.font()
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)

        info_text = QLabel()
        info_text.setWordWrap(True)
        info_text.setText(
            "• Remote: Uses a remote WebSocket server for TTS (faster, no GPU required)\n"
            "• Local: Runs TTS locally on your machine (requires GPU with CUDA support)"
        )
        info_text.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_text)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def on_server_type_changed(self):
        """Handle server type radio button change"""
        is_remote = self.remote_radio.isChecked()
        self.remote_url_input.setEnabled(is_remote)

    def get_server_config(self):
        """Get the selected server configuration"""
        server_type = "remote" if self.remote_radio.isChecked() else "local"
        remote_url = self.remote_url_input.text().strip()
        return server_type, remote_url


class MainApp(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.clipboard_capture = ClipboardCapture()

        # Thread references
        self.correction_thread = None
        self.translation_thread = None
        self.tts_thread = None

        # Current popup window
        self.popup_window = None

        # VibeVoice model managers (singleton for reuse)
        self.vibevoice_manager = None  # Local model manager
        self.vibevoice_remote_manager = VibeVoiceTTSRemoteManager()  # Remote model manager

        # TTS server configuration
        self.tts_server_type = "remote"  # Default to remote
        self.tts_remote_url = "ws://10.110.31.157:3000/stream"  # Default remote URL

        # Show TTS server selection dialog on startup
        self.show_tts_server_selection()

        # Create system tray icon
        self.create_system_tray()

        # Setup global shortcut handler
        self.shortcut_handler = GlobalShortcutHandler()
        self.shortcut_handler.double_ctrl_c_triggered.connect(
            self.on_double_ctrl_c)

        print("=== AI-TTS: Double Ctrl+C Text Processor ===")
        print("How to use:")
        print("1. Select text anywhere (browser, document, etc.)")
        print("2. Press Ctrl+C to copy it")
        print("3. Press Ctrl+C again within 1 second")
        print("4. Text will be:")
        print("   - Corrected (fix PDF formatting issues)")
        print("   - Translated (English -> Chinese)")
        print("   - Converted to speech (English text via VibeVoice)")
        print()
        print("This works with any application that supports copy!")
        print("=" * 50)

    def create_system_tray(self):
        # Create icon
        icon = QIcon()
        pixmap = QPixmap(16, 16)
        pixmap.fill()
        icon.addPixmap(pixmap)

        self.tray_icon = QSystemTrayIcon(icon, self.app)

        # Create context menu
        tray_menu = QMenu()

        # Test clipboard
        test_action = tray_menu.addAction("Test Double Ctrl+C")
        test_action.triggered.connect(self.test_double_ctrl_c)

        # Preload model
        preload_action = tray_menu.addAction("Preload VibeVoice Model")
        preload_action.triggered.connect(self.preload_model)

        # Change TTS Server
        change_server_action = tray_menu.addAction("Change TTS Server")
        change_server_action.triggered.connect(self.change_tts_server)

        tray_menu.addSeparator()

        # Exit
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_tts_server_selection(self):
        """Show TTS server selection dialog"""
        dialog = TTSServerSelectionDialog(
            current_server_type=self.tts_server_type,
            current_remote_url=self.tts_remote_url
        )

        if dialog.exec() == QDialog.Accepted:
            server_type, remote_url = dialog.get_server_config()
            self.tts_server_type = server_type
            self.tts_remote_url = remote_url

            # Update remote manager with new URL
            self.vibevoice_remote_manager.set_server_url(remote_url)

            print(f"TTS Server set to: {server_type}")
            if server_type == "remote":
                print(f"Remote URL: {remote_url}")

    def change_tts_server(self):
        """Change TTS server from tray menu"""
        self.show_tts_server_selection()

    def preload_model(self):
        """Preload the VibeVoice model in background"""
        try:
            self.tray_icon.showMessage(
                "AI-TTS",
                "Loading VibeVoice model... This may take a while.",
                QSystemTrayIcon.Information,
                3000
            )

            def load_model():
                self.vibevoice_manager = VibeVoiceModelManager()
                self.vibevoice_manager.get_tts_instance(
                    model_path="microsoft/VibeVoice-Realtime-0.5B",
                    device="cuda"
                )
                self.tray_icon.showMessage(
                    "AI-TTS",
                    "VibeVoice model loaded successfully!",
                    QSystemTrayIcon.Information,
                    3000
                )

            import threading
            thread = threading.Thread(target=load_model, daemon=True)
            thread.start()

        except Exception as e:
            self.tray_icon.showMessage(
                "AI-TTS",
                f"Failed to load model: {str(e)}",
                QSystemTrayIcon.Warning,
                5000
            )

    def test_double_ctrl_c(self):
        """Test function to simulate double Ctrl+C"""
        test_text = "This is a sam-ple text with some\nline breaks and for- matting issues from PDF."
        self.process_clipboard_text(test_text)

    def on_double_ctrl_c(self):
        """Called when double Ctrl+C is detected"""
        print("\n" + "=" * 50)
        print("DOUBLE CTRL+C DETECTED - PROCESSING CLIPBOARD")
        print("=" * 50)

        # Small delay to ensure clipboard is updated
        time.sleep(0.1)

        text, format_name = self.clipboard_capture.get_clipboard_text()

        print(f"Clipboard format: {format_name}")
        print(f"Text length: {len(text) if text else 0}")
        if text:
            preview = text.replace('\n', '\\n').replace('\r', '\\r')[:100]
            print(f"Preview: {preview}...")
        print("=" * 50 + "\n")

        if text and text.strip():
            # Clean up the text
            text = self.clean_text(text)
            self.process_clipboard_text(text)
        else:
            self.show_no_text_warning()

    def clean_text(self, text):
        """Clean up the copied text"""
        # Replace newlines with spaces
        text = text.replace("\n", " ")
        text = text.replace("\r", " ")

        # Remove extra spaces
        while "  " in text:
            text = text.replace("  ", " ")

        # Strip leading/trailing whitespace
        text = text.strip()

        # Add period if missing
        if text and not text.endswith(('.', '!', '?', ';', ':')):
            text += '.'

        return text

    def is_english(self, text):
        """Check if text is primarily English (Latin characters)"""
        if not text:
            return False

        # Count English/Latin letters vs Chinese characters
        latin_chars = sum(1 for c in text if (
            '\u0020' <= c <= '\u007F') or ('\u0080' <= c <= '\u00FF'))
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

        # If there are Chinese characters, it's likely Chinese text
        if chinese_chars > 0:
            return False

        # Check if majority of alphabetic characters are Latin
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return False

        latin_ratio = latin_chars / total_alpha
        return latin_ratio > 0.5

    def process_clipboard_text(self, original_text):
        """Main processing function for clipboard text"""
        # Close existing popup if any
        if self.popup_window is not None:
            self.popup_window.close()

        # Create new popup window
        self.popup_window = PopupWindow(original_text)
        self.popup_window.exit_app_requested.connect(self.exit_app)
        self.popup_window.popup_destroyed.connect(self.on_popup_destroyed)
        self.popup_window.show()

        # Initialize model manager if not already done
        if self.vibevoice_manager is None:
            self.vibevoice_manager = VibeVoiceModelManager()

        # Stop and wait for any previous threads to finish
        # This prevents "QThread: Destroyed while thread is still running" errors
        if self.correction_thread is not None:
            if self.correction_thread.isRunning():
                self.correction_thread.terminate()  # Force terminate since no stop method
                self.correction_thread.wait(1000)  # Wait up to 1 second
            self.correction_thread = None
        if self.translation_thread is not None:
            if self.translation_thread.isRunning():
                self.translation_thread.terminate()  # Force terminate since no stop method
                self.translation_thread.wait(1000)  # Wait up to 1 second
            self.translation_thread = None
        if self.tts_thread is not None:
            if self.tts_thread.isRunning():
                self.tts_thread.stop()  # Request graceful stop (closes WebSocket)
                if not self.tts_thread.wait(5000):  # Wait up to 5 seconds (increased from 2)
                    print("TTS thread did not stop in time, terminating...")
                    self.tts_thread.terminate()
                    self.tts_thread.wait(1000)  # Wait up to 1 second for termination
            self.tts_thread = None

        # Start correction thread
        self.popup_window.set_status("Correcting text...")
        self.correction_thread = TextCorrectionThread(
            original_text, 'deepseek')
        self.correction_thread.correction_done.connect(self.on_correction_done)
        self.correction_thread.correction_chunk.connect(
            self.on_correction_chunk)
        self.correction_thread.correction_error.connect(
            self.on_correction_error)
        self.correction_thread.start()

    def on_correction_chunk(self, chunk):
        """Handle streaming correction chunk"""
        if self.popup_window:
            self.popup_window.append_corrected_chunk(chunk)

    def on_correction_error(self, error_message):
        """Handle correction error"""
        print(f"Correction error: {error_message}")
        if self.popup_window:
            self.popup_window.set_status(
                f"Correction failed: {error_message[:50]}... (using original text)")

    def on_correction_done(self, corrected_text):
        """Handle correction completion - start translation and TTS in parallel"""
        print(f"Correction completed: {corrected_text[:50]}...")

        # Update popup with corrected text
        if self.popup_window:
            self.popup_window.update_corrected_text(corrected_text)
            self.popup_window.set_status("Translating and generating audio...")

        self.correction_thread = None

        # Start translation thread
        self.translation_thread = TranslationThread(corrected_text, 'deepseek')
        self.translation_thread.translation_done.connect(
            self.on_translation_done)
        self.translation_thread.translation_chunk.connect(
            self.on_translation_chunk)
        self.translation_thread.start()

        # Start TTS thread in parallel (using corrected text)
        self._start_tts(corrected_text)

    def on_translation_chunk(self, chunk):
        """Handle streaming translation chunk"""
        if self.popup_window:
            self.popup_window.append_translated_chunk(chunk)

    def on_translation_done(self, translated_text):
        """Handle translation completion (TTS is already running in parallel)"""
        print(f"Translation completed: {translated_text[:50]}...")

        # Update popup with translated text
        if self.popup_window:
            self.popup_window.update_translated_text(translated_text)
            # Only update status if TTS is still running
            if self.tts_thread is not None and self.tts_thread.isRunning():
                self.popup_window.set_status("Translation done. Generating audio...")

        self.translation_thread = None

    def _start_tts(self, tts_text):
        """Start TTS thread with the given text"""
        try:
            # Use remote or local TTS based on user selection
            if self.tts_server_type == "remote":
                # Use remote TTS server
                self.tts_thread = self.vibevoice_remote_manager.create_tts_thread(
                    text=tts_text,
                    server_url=self.tts_remote_url,
                    streaming=True  # Enable streaming for real-time playback
                )
                print(f"Using remote TTS server: {self.tts_remote_url}")
            else:
                # Use local TTS model
                # Initialize local model manager if not already done
                if self.vibevoice_manager is None:
                    self.vibevoice_manager = VibeVoiceModelManager()

                self.tts_thread = self.vibevoice_manager.create_tts_thread(
                    text=tts_text,
                    model_path="microsoft/VibeVoice-Realtime-0.5B",
                    device="cuda",
                    streaming=True  # Enable streaming for real-time playback
                )
                print("Using local TTS model")

            self.tts_thread.tts_completed.connect(self.on_tts_completed)
            self.tts_thread.tts_error.connect(self.on_tts_error)
            self.tts_thread.progress_update.connect(self.on_tts_progress)
            # Connect audio chunk signal for real-time streaming playback
            self.tts_thread.audio_chunk_ready.connect(
                self.on_audio_chunk_ready)
            self.tts_thread.start()
        except Exception as e:
            print(f"Failed to start TTS: {e}")
            self.on_tts_error(f"Failed to start TTS: {str(e)}")

    def on_tts_completed(self, audio_file_path):
        """Handle TTS completion"""
        print("TTS audio generation completed")

        if self.popup_window:
            self.popup_window.set_audio_ready(audio_file_path)

        self.tts_thread = None

    def on_tts_progress(self, message):
        """Handle TTS progress updates"""
        print(f"TTS Progress: {message}")
        if self.popup_window:
            self.popup_window.set_status(message)

    def on_audio_chunk_ready(self, audio_bytes, sample_rate):
        """Handle streaming audio chunk - forward to popup window for real-time playback"""
        if self.popup_window:
            self.popup_window.on_audio_chunk_ready(audio_bytes, sample_rate)

    def on_tts_error(self, error_message):
        """Handle TTS error"""
        print(f"TTS Error: {error_message}")

        if self.popup_window:
            self.popup_window.set_audio_error(error_message)

        # Show error message to user
        msg_box = QMessageBox()
        msg_box.setWindowTitle("TTS Error")
        msg_box.setText("Text-to-Speech generation failed")
        msg_box.setInformativeText(error_message)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setWindowFlags(msg_box.windowFlags() |
                               msg_box.windowFlags().__class__.WindowStaysOnTopHint)
        msg_box.exec()

    def show_no_text_warning(self):
        """Show warning when no text found in clipboard"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("AI-TTS - No Text Found")
        msg_box.setText("No text found in clipboard")
        msg_box.setInformativeText(
            "Possible reasons:\n"
            "• Nothing was selected when you pressed Ctrl+C\n"
            "• The copied content is not text (image, file, etc.)\n\n"
            "Try:\n"
            "1. Select some text\n"
            "2. Press Ctrl+C (first time to copy)\n"
            "3. Press Ctrl+C again (second time to process)"
        )
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setWindowFlags(msg_box.windowFlags() |
                               msg_box.windowFlags().__class__.WindowStaysOnTopHint)
        msg_box.exec()

    def on_popup_destroyed(self):
        """Handle popup window destruction - disconnect TTS signals"""
        print("Popup window destroyed, disconnecting TTS signals")
        # Disconnect TTS thread signals to prevent updates to destroyed widget
        if self.tts_thread is not None:
            try:
                self.tts_thread.tts_completed.disconnect(self.on_tts_completed)
                self.tts_thread.tts_error.disconnect(self.on_tts_error)
                self.tts_thread.progress_update.disconnect(
                    self.on_tts_progress)
                self.tts_thread.audio_chunk_ready.disconnect(
                    self.on_audio_chunk_ready)
            except:
                pass
        # Clear popup reference
        self.popup_window = None

    def exit_app(self):
        print("Exiting application...")

        # Close popup window
        if self.popup_window is not None:
            self.popup_window.close()

        # Stop and wait for threads to finish
        if self.correction_thread is not None:
            if self.correction_thread.isRunning():
                self.correction_thread.terminate()
                self.correction_thread.wait(1000)
            self.correction_thread = None
        if self.translation_thread is not None:
            if self.translation_thread.isRunning():
                self.translation_thread.terminate()
                self.translation_thread.wait(1000)
            self.translation_thread = None
        if self.tts_thread is not None:
            if self.tts_thread.isRunning():
                self.tts_thread.stop()  # Request graceful stop
                if not self.tts_thread.wait(2000):
                    self.tts_thread.terminate()
                    self.tts_thread.wait(500)
            self.tts_thread = None

        # Cleanup
        self.shortcut_handler.stop()
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        return self.app.exec()


if __name__ == "__main__":
    main_app = MainApp()
    sys.exit(main_app.run())
