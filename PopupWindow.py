import os
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QProgressBar, QLabel, QSystemTrayIcon, QMenu, QApplication
)
from PySide6.QtCore import QTimer, QSettings, Qt as _Qt
from PySide6.QtGui import QFont, QIcon
import pygame


class PopupWindow(QWidget):
    def __init__(self, original_text, parent=None):
        super().__init__(parent)
        self.original_text = original_text
        self.corrected_text = ""
        self.translated_text = ""
        self.english_text = ""

        self.is_playing = False
        self.audio_file_path = None
        self.audio_length = 0
        self.current_position = 0

        # Settings for position memory
        self.settings = QSettings('AI-TTS-App', 'PopupWindow')

        # Initialize pygame mixer
        try:
            pygame.mixer.init()
        except:
            pygame.mixer.quit()
            pygame.mixer.init()

        self.init_ui()
        self.restore_position()
        self.setup_auto_close_timer()

    def init_ui(self):
        self.setWindowTitle("AI-TTS - Text Correction, Translation & TTS")
        self.setMinimumSize(500, 600)

        # Make window stay on top
        self.setWindowFlags(self.windowFlags() | _Qt.WindowStaysOnTopHint)

        # Main layout
        layout = QVBoxLayout()

        # Title font
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)

        # Original text section
        original_label = QLabel("Original Text:")
        original_label.setFont(title_font)
        layout.addWidget(original_label)

        self.original_text_display = QTextEdit()
        self.original_text_display.setFont(QFont("Microsoft YaHei", 10))
        self.original_text_display.setPlainText(self.original_text)
        self.original_text_display.setReadOnly(True)
        self.original_text_display.setMaximumHeight(100)
        layout.addWidget(self.original_text_display)

        # Corrected text section
        corrected_label = QLabel("AI Corrected Text (fixes PDF formatting issues):")
        corrected_label.setFont(title_font)
        layout.addWidget(corrected_label)

        self.corrected_text_display = QTextEdit()
        self.corrected_text_display.setFont(QFont("Microsoft YaHei", 10))
        self.corrected_text_display.setPlainText("Correcting...")
        self.corrected_text_display.setReadOnly(True)
        self.corrected_text_display.setMaximumHeight(100)
        layout.addWidget(self.corrected_text_display)

        # Translated text section
        translated_label = QLabel("Translated Text:")
        translated_label.setFont(title_font)
        layout.addWidget(translated_label)

        self.translated_text_display = QTextEdit()
        self.translated_text_display.setFont(QFont("Microsoft YaHei", 10))
        self.translated_text_display.setPlainText("Translating...")
        self.translated_text_display.setReadOnly(True)
        self.translated_text_display.setMaximumHeight(100)
        layout.addWidget(self.translated_text_display)

        # English text for TTS section
        english_label = QLabel("English Text (for TTS):")
        english_label.setFont(title_font)
        layout.addWidget(english_label)

        self.english_text_display = QTextEdit()
        self.english_text_display.setFont(QFont("Microsoft YaHei", 10))
        self.english_text_display.setPlainText("Processing...")
        self.english_text_display.setReadOnly(True)
        layout.addWidget(self.english_text_display)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Audio controls layout
        controls_layout = QHBoxLayout()

        # Play/Stop button
        self.play_stop_btn = QPushButton("▶ Play English Audio")
        self.play_stop_btn.setEnabled(False)
        self.play_stop_btn.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_stop_btn)

        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.time_label)

        controls_layout.addStretch()

        # Close button
        self.close_btn = QPushButton("✕ Close")
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)

        layout.addLayout(controls_layout)

        # Auto-close countdown label
        self.countdown_label = QLabel("Auto-close in 360 seconds")
        self.countdown_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.countdown_label)

        self.setLayout(layout)

        # Setup progress timer for real-time updates
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)

    def restore_position(self):
        """Restore the widget to its previous position"""
        pos = self.settings.value('position')
        size = self.settings.value('size')

        if pos is not None:
            self.move(pos)
        else:
            # Default position (center of screen)
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )

        if size is not None:
            self.resize(size)

    def save_position(self):
        """Save the current position and size"""
        self.settings.setValue('position', self.pos())
        self.settings.setValue('size', self.size())

    def moveEvent(self, event):
        """Called when window is moved - save position"""
        super().moveEvent(event)
        self.save_position()

    def resizeEvent(self, event):
        """Called when window is resized - save size"""
        super().resizeEvent(event)
        self.save_position()

    def setup_auto_close_timer(self):
        """Setup timer for auto-close after 360 seconds"""
        self.auto_close_countdown = 360
        self.auto_close_timer = QTimer()
        self.auto_close_timer.timeout.connect(self.update_countdown)
        self.auto_close_timer.start(1000)

    def update_countdown(self):
        """Update the countdown display and close when it reaches 0"""
        self.auto_close_countdown -= 1
        self.countdown_label.setText(
            f"Auto-close in {self.auto_close_countdown} seconds")

        if self.auto_close_countdown <= 0:
            self.auto_close_timer.stop()
            self.close()

    def update_corrected_text(self, text):
        """Update the corrected text display"""
        self.corrected_text = text
        self.corrected_text_display.setPlainText(text)

    def append_corrected_chunk(self, chunk):
        """Append streaming correction chunk"""
        current_text = self.corrected_text_display.toPlainText()
        if current_text == "Correcting...":
            current_text = ""
        self.corrected_text_display.setPlainText(current_text + chunk)

    def update_translated_text(self, text):
        """Update the translated text display"""
        self.translated_text = text
        self.translated_text_display.setPlainText(text)

    def append_translated_chunk(self, chunk):
        """Append streaming translation chunk"""
        current_text = self.translated_text_display.toPlainText()
        if current_text == "Translating...":
            current_text = ""
        self.translated_text_display.setPlainText(current_text + chunk)

    def update_english_text(self, text):
        """Update the English text for TTS display"""
        self.english_text = text
        self.english_text_display.setPlainText(text)

    def set_status(self, status):
        """Update status label"""
        self.status_label.setText(status)

    def set_audio_ready(self, audio_file_path, duration=None):
        """Called when audio is ready for playback"""
        self.audio_file_path = audio_file_path

        # Get actual audio length
        self.audio_length = self.get_audio_length(audio_file_path)

        print(f"Audio file: {audio_file_path}")
        print(f"Audio length: {self.audio_length} seconds")

        self.status_label.setText("✅ Audio ready")
        self.play_stop_btn.setEnabled(True)
        self.update_time_display()

        # Auto-start playback
        self.start_playback()

    def set_audio_error(self, error_message):
        """Called when audio generation fails"""
        self.status_label.setText(f"❌ Audio error: {error_message}")
        self.play_stop_btn.setEnabled(False)

    def get_audio_length(self, audio_file_path):
        """Get the actual length of the audio file"""
        try:
            sound = pygame.mixer.Sound(audio_file_path)
            length_seconds = sound.get_length()
            return int(length_seconds)
        except Exception as e:
            print(f"Error getting audio length: {e}")
            return 30  # Default fallback

    def toggle_playback(self):
        """Toggle between play and stop"""
        if not self.is_playing:
            self.start_playback()
        else:
            self.stop_playback()

    def start_playback(self):
        """Start actual audio playback"""
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            print("Audio file not found")
            return

        try:
            # Stop any currently playing audio
            pygame.mixer.music.stop()

            # Load and play the audio file
            pygame.mixer.music.load(self.audio_file_path)
            pygame.mixer.music.play()

            self.is_playing = True
            self.play_stop_btn.setText("⏸ Stop")
            self.current_position = 0

            # Start the progress timer
            self.progress_timer.start(100)  # Update every 100ms

            print(f"Audio playback started: {self.audio_file_path}")

        except Exception as e:
            print(f"Error starting playback: {e}")
            self.set_audio_error(f"Playback error: {str(e)}")

    def stop_playback(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
        except:
            pass

        self.is_playing = False
        self.play_stop_btn.setText("▶ Play English Audio")
        self.progress_timer.stop()
        self.current_position = 0
        self.progress_bar.setValue(0)
        self.update_time_display()
        print("Audio playback stopped")

    def update_progress(self):
        """Update progress bar and time display based on actual playback"""
        if self.is_playing and pygame.mixer.music.get_busy():
            # Audio is still playing
            self.current_position += 0.1  # Increment by 100ms

            # Calculate progress percentage
            if self.audio_length > 0:
                progress_percent = min(
                    100, (self.current_position / self.audio_length) * 100)
                self.progress_bar.setValue(int(progress_percent))

            self.update_time_display()

        elif self.is_playing and not pygame.mixer.music.get_busy():
            # Audio finished playing
            print("Audio playback completed")
            self.stop_playback()

    def update_time_display(self):
        """Update time display"""
        current_seconds = int(self.current_position)
        total_seconds = self.audio_length

        current_time = f"{current_seconds//60:02d}:{current_seconds % 60:02d}"
        total_time = f"{total_seconds//60:02d}:{total_seconds % 60:02d}"

        self.time_label.setText(f"{current_time} / {total_time}")

    def closeEvent(self, event):
        """Handle window close event"""
        # Save position before closing
        self.save_position()

        # Stop audio playback
        if self.is_playing:
            self.stop_playback()

        # Stop timers
        if hasattr(self, 'auto_close_timer'):
            self.auto_close_timer.stop()
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()

        # Clean up temporary audio file
        if self.audio_file_path and os.path.exists(self.audio_file_path):
            try:
                pygame.mixer.music.unload()
                pygame.mixer.quit()
                pygame.mixer.init()

                time.sleep(0.2)

                os.unlink(self.audio_file_path)
                print(f"Cleaned up audio file: {self.audio_file_path}")
            except Exception as e:
                print(f"Failed to clean up audio file: {e}")

        event.accept()
