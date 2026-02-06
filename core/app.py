"""
Main application class with system tray and text processing coordination.
"""
import sys
import time
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon, QPixmap

from core.thread_manager import ThreadManager
from core.text_processor import TextProcessor
from services.clipboard.clipboard_service import ClipboardService
from utils.shortcuts import GlobalShortcutHandler
from utils.helpers import clean_text
from ui.dialogs.tts_server_dialog import TTSServerSelectionDialog


class MainApp(QObject):
    """Main application class."""

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Services
        self.clipboard_service = ClipboardService()
        self.thread_manager = ThreadManager()

        # Current popup window
        self.popup_window = None

        # TTS configuration
        self.tts_server_type = "remote"
        self.tts_remote_url = "ws://10.110.31.157:3000/stream"

        # Text processor
        self.text_processor = TextProcessor(
            self.thread_manager,
            self.tts_server_type,
            self.tts_remote_url
        )

        # Setup callbacks
        self._setup_text_processor_callbacks()

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

    def _setup_text_processor_callbacks(self):
        """Setup callbacks for text processor."""
        self.text_processor.on_correction_chunk = self.on_correction_chunk
        self.text_processor.on_correction_done = self.on_correction_done
        self.text_processor.on_correction_error = self.on_correction_error
        self.text_processor.on_translation_chunk = self.on_translation_chunk
        self.text_processor.on_translation_done = self.on_translation_done
        self.text_processor.on_translation_error = self.on_translation_error
        self.text_processor.on_tts_completed = self.on_tts_completed
        self.text_processor.on_tts_error = self.on_tts_error
        self.text_processor.on_tts_progress = self.on_tts_progress
        self.text_processor.on_audio_chunk_ready = self.on_audio_chunk_ready

    def create_system_tray(self):
        """Create system tray icon and menu."""
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
        """Show TTS server selection dialog."""
        dialog = TTSServerSelectionDialog(
            current_server_type=self.tts_server_type,
            current_remote_url=self.tts_remote_url
        )

        if dialog.exec() == TTSServerSelectionDialog.Accepted:
            server_type, remote_url = dialog.get_server_config()
            self.tts_server_type = server_type
            self.tts_remote_url = remote_url

            # Update text processor with new config
            self.text_processor.set_tts_config(server_type, remote_url)

            print(f"TTS Server set to: {server_type}")
            if server_type == "remote":
                print(f"Remote URL: {remote_url}")

    def change_tts_server(self):
        """Change TTS server from tray menu."""
        self.show_tts_server_selection()

    def preload_model(self):
        """Preload the VibeVoice model in background."""
        try:
            self.tray_icon.showMessage(
                "AI-TTS",
                "Loading VibeVoice model... This may take a while.",
                QSystemTrayIcon.Information,
                3000
            )

            self.text_processor.preload_local_model()

            self.tray_icon.showMessage(
                "AI-TTS",
                "VibeVoice model loading started!",
                QSystemTrayIcon.Information,
                3000
            )

        except Exception as e:
            self.tray_icon.showMessage(
                "AI-TTS",
                f"Failed to load model: {str(e)}",
                QSystemTrayIcon.Warning,
                5000
            )

    def test_double_ctrl_c(self):
        """Test function to simulate double Ctrl+C."""
        test_text = "This is a sam-ple text with some\nline breaks and for- matting issues from PDF."
        self.process_clipboard_text(test_text)

    def on_double_ctrl_c(self):
        """Called when double Ctrl+C is detected."""
        print("\n" + "=" * 50)
        print("DOUBLE CTRL+C DETECTED - PROCESSING CLIPBOARD")
        print("=" * 50)

        # Small delay to ensure clipboard is updated
        time.sleep(0.1)

        text, format_name = self.clipboard_service.get_text()

        print(f"Clipboard format: {format_name}")
        print(f"Text length: {len(text) if text else 0}")
        if text:
            preview = text.replace('\n', '\\n').replace('\r', '\\r')[:100]
            print(f"Preview: {preview}...")
        print("=" * 50 + "\n")

        if text and text.strip():
            # Clean up the text
            text = clean_text(text)
            self.process_clipboard_text(text)
        else:
            self.show_no_text_warning()

    def process_clipboard_text(self, original_text):
        """Main processing function for clipboard text."""
        # Close existing popup if any
        if self.popup_window is not None:
            self.popup_window.close()

        # Create new popup window (will be imported later to avoid circular import)
        from ui.popup_window import PopupWindow
        self.popup_window = PopupWindow(original_text, self.thread_manager, self.text_processor)
        self.popup_window.exit_app_requested.connect(self.exit_app)
        self.popup_window.popup_destroyed.connect(self.on_popup_destroyed)
        self.popup_window.show()

        # Start text processing
        self.popup_window.set_status("Correcting text...")
        self.text_processor.process_text(original_text)

    # Text processor callbacks
    def on_correction_chunk(self, chunk):
        """Handle streaming correction chunk."""
        if self.popup_window:
            self.popup_window.append_corrected_chunk(chunk)

    def on_correction_done(self, corrected_text):
        """Handle correction completion."""
        if self.popup_window:
            self.popup_window.update_corrected_text(corrected_text)
            self.popup_window.set_status("Generating audio...")

    def on_correction_error(self, error_message):
        """Handle correction error."""
        print(f"Correction error: {error_message}")
        if self.popup_window:
            self.popup_window.set_status(
                f"Correction failed: {error_message[:50]}... (using original text)")

    def on_translation_chunk(self, chunk):
        """Handle streaming translation chunk."""
        if self.popup_window:
            self.popup_window.append_translated_chunk(chunk)

    def on_translation_done(self, translated_text):
        """Handle translation completion."""
        print(f"Translation completed: {translated_text[:50]}...")
        if self.popup_window:
            self.popup_window.update_translated_text(translated_text)

    def on_translation_error(self, error_message):
        """Handle translation error."""
        print(f"Translation error: {error_message}")
        if self.popup_window:
            self.popup_window.set_translation_error(error_message)

    def on_tts_completed(self, audio_file_path):
        """Handle TTS completion."""
        print("TTS audio generation completed")
        if self.popup_window:
            self.popup_window.set_audio_ready(audio_file_path)

    def on_tts_progress(self, message):
        """Handle TTS progress updates."""
        print(f"TTS Progress: {message}")
        if self.popup_window:
            self.popup_window.set_status(message)

    def on_audio_chunk_ready(self, audio_bytes, sample_rate):
        """Handle streaming audio chunk."""
        if self.popup_window:
            self.popup_window.on_audio_chunk_ready(audio_bytes, sample_rate)

    def on_tts_error(self, error_message):
        """Handle TTS error."""
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
        msg_box.exec()

    def show_no_text_warning(self):
        """Show warning when no text found in clipboard."""
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
        msg_box.exec()

    def on_popup_destroyed(self):
        """Handle popup window destruction."""
        print("Popup window destroyed")
        self.popup_window = None

    def exit_app(self):
        """Exit the application."""
        print("Exiting application...")

        # Close popup window
        if self.popup_window is not None:
            self.popup_window.close()

        # Stop all threads
        self.thread_manager.stop_all_threads()

        # Cleanup
        self.shortcut_handler.stop()
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        """Run the application."""
        return self.app.exec()
