import sys
import time
import re

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon, QPixmap

from PopupWindow import PopupWindow
from GlobalShortcutHandler import GlobalShortcutHandler
from ClipboardCapture import ClipboardCapture
from TextCorrectionThread import TextCorrectionThread
from TranslationThread import TranslationThread
from VibeVoiceTTS import VibeVoiceModelManager


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

        # VibeVoice model manager (singleton for reuse)
        self.vibevoice_manager = None

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

        tray_menu.addSeparator()

        # Exit
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

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
        latin_chars = sum(1 for c in text if ('\u0020' <= c <= '\u007F') or ('\u0080' <= c <= '\u00FF'))
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
        self.popup_window.show()

        # Initialize model manager if not already done
        if self.vibevoice_manager is None:
            self.vibevoice_manager = VibeVoiceModelManager()

        # Wait for any previous threads to finish
        if self.correction_thread is not None:
            self.correction_thread.wait()
        if self.translation_thread is not None:
            self.translation_thread.wait()
        if self.tts_thread is not None:
            self.tts_thread.wait()

        # Start correction thread
        self.popup_window.set_status("Correcting text...")
        self.correction_thread = TextCorrectionThread(original_text, 'deepseek')
        self.correction_thread.correction_done.connect(self.on_correction_done)
        self.correction_thread.correction_chunk.connect(self.on_correction_chunk)
        self.correction_thread.correction_error.connect(self.on_correction_error)
        self.correction_thread.start()

    def on_correction_chunk(self, chunk):
        """Handle streaming correction chunk"""
        if self.popup_window:
            self.popup_window.append_corrected_chunk(chunk)

    def on_correction_error(self, error_message):
        """Handle correction error"""
        print(f"Correction error: {error_message}")
        if self.popup_window:
            self.popup_window.set_status(f"Correction failed: {error_message[:50]}... (using original text)")

    def on_correction_done(self, corrected_text):
        """Handle correction completion"""
        print(f"Correction completed: {corrected_text[:50]}...")

        # Update popup with corrected text
        if self.popup_window:
            self.popup_window.update_corrected_text(corrected_text)
            self.popup_window.set_status("Translating text...")

        self.correction_thread = None

        # Start translation thread
        self.translation_thread = TranslationThread(corrected_text, 'deepseek')
        self.translation_thread.translation_done.connect(self.on_translation_done)
        self.translation_thread.translation_chunk.connect(self.on_translation_chunk)
        self.translation_thread.start()

    def on_translation_chunk(self, chunk):
        """Handle streaming translation chunk"""
        if self.popup_window:
            self.popup_window.append_translated_chunk(chunk)

    def on_translation_done(self, translated_text):
        """Handle translation completion"""
        print(f"Translation completed: {translated_text[:50]}...")

        # Update popup with translated text
        if self.popup_window:
            self.popup_window.update_translated_text(translated_text)
            self.popup_window.set_status("Generating audio...")

        self.translation_thread = None

        # Always use the corrected text for TTS (it's the AI-corrected English text)
        tts_text = self.popup_window.corrected_text if self.popup_window else ""

        # Start TTS thread with streaming enabled
        try:
            self.tts_thread = self.vibevoice_manager.create_tts_thread(
                text=tts_text,
                model_path="microsoft/VibeVoice-Realtime-0.5B",
                device="cuda",
                streaming=True  # Enable streaming for real-time playback
            )
            self.tts_thread.tts_completed.connect(self.on_tts_completed)
            self.tts_thread.tts_error.connect(self.on_tts_error)
            self.tts_thread.progress_update.connect(self.on_tts_progress)
            # Connect audio chunk signal for real-time streaming playback
            self.tts_thread.audio_chunk_ready.connect(self.on_audio_chunk_ready)
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

    def exit_app(self):
        print("Exiting application...")

        # Close popup window
        if self.popup_window is not None:
            self.popup_window.close()

        # Wait for threads to finish
        if self.correction_thread is not None:
            self.correction_thread.wait()
        if self.translation_thread is not None:
            self.translation_thread.wait()
        if self.tts_thread is not None:
            self.tts_thread.wait()

        # Cleanup
        self.shortcut_handler.stop()
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        return self.app.exec()


if __name__ == "__main__":
    main_app = MainApp()
    sys.exit(main_app.run())
