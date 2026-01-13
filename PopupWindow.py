import os
import time
import queue
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QProgressBar, QLabel, QSystemTrayIcon, QMenu, QApplication
)
from PySide6.QtCore import QTimer, QSettings, Qt as _Qt, Signal
from PySide6.QtGui import QFont, QIcon
import pygame


class StreamingAudioPlayer:
    """Real-time audio streaming player using pyaudio"""
    
    def __init__(self, sample_rate=24000, channels=1, sample_width=2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width  # 2 bytes for 16-bit audio
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.stop_event = threading.Event()
        self.playback_thread = None
        self.total_bytes_played = 0
        self.pyaudio_instance = None
        self.stream = None
        
    def start(self):
        """Start the streaming playback"""
        if self.is_playing:
            return
        
        self.stop_event.clear()
        self.is_playing = True
        self.total_bytes_played = 0
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()
        
    def add_audio_chunk(self, audio_bytes):
        """Add an audio chunk to the playback queue"""
        if self.is_playing:
            self.audio_queue.put(audio_bytes)
            
    def stop(self):
        """Stop the streaming playback"""
        self.stop_event.set()
        self.is_playing = False
        
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
            
    def _playback_loop(self):
        """Main playback loop running in a separate thread"""
        try:
            import pyaudio
            self.pyaudio_instance = pyaudio.PyAudio()
            
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024
            )
            
            while not self.stop_event.is_set():
                try:
                    # Get audio data with timeout
                    audio_data = self.audio_queue.get(timeout=0.1)
                    self.stream.write(audio_data)
                    self.total_bytes_played += len(audio_data)
                except queue.Empty:
                    continue
                    
        except ImportError:
            print("pyaudio not installed, falling back to non-streaming playback")
        except Exception as e:
            print(f"Streaming playback error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
            self.stream = None
            self.pyaudio_instance = None
            
    def get_current_position(self):
        """Get current playback position in seconds"""
        bytes_per_sample = self.sample_width * self.channels
        samples_played = self.total_bytes_played / bytes_per_sample
        return samples_played / self.sample_rate


class PopupWindow(QWidget):
    # Signal to request full application exit
    exit_app_requested = Signal()
    
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
        
        # Streaming audio player
        self.streaming_player = None
        self.is_streaming = False
        self.streaming_chunks_received = 0

        # Settings for position memory
        self.settings = QSettings('AI-TTS-App', 'PopupWindow')

        # Initialize pygame mixer (for file-based playback fallback)
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

        # Top bar with Exit button
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()
        
        # Exit Program button (exits entire application)
        self.exit_app_btn = QPushButton("⏻ Exit Program")
        self.exit_app_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.exit_app_btn.clicked.connect(self.request_exit_app)
        top_bar_layout.addWidget(self.exit_app_btn)
        
        layout.addLayout(top_bar_layout)

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

    def request_exit_app(self):
        """Request full application exit"""
        self.exit_app_requested.emit()
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

    # --- Streaming Audio Methods ---
    
    def start_streaming_playback(self):
        """Initialize streaming audio playback"""
        self.is_streaming = True
        self.streaming_chunks_received = 0
        self.streaming_player = StreamingAudioPlayer(sample_rate=24000)
        self.streaming_player.start()
        self.is_playing = True
        self.play_stop_btn.setText("⏸ Stop")
        self.play_stop_btn.setEnabled(True)
        self.progress_timer.start(100)
        self.set_status("🔊 Streaming audio...")
        print("Streaming playback started")
        
    def on_audio_chunk_ready(self, audio_bytes, sample_rate):
        """Handle incoming audio chunk for streaming playback"""
        if not self.is_streaming:
            self.start_streaming_playback()
            
        self.streaming_chunks_received += 1
        
        if self.streaming_player:
            self.streaming_player.add_audio_chunk(audio_bytes)
            
        # Update status with chunk count
        self.set_status(f"🔊 Streaming audio... ({self.streaming_chunks_received} chunks)")
        
    def stop_streaming_playback(self):
        """Stop streaming audio playback"""
        if self.streaming_player:
            self.streaming_player.stop()
            self.streaming_player = None
        self.is_streaming = False
        self.is_playing = False
        self.play_stop_btn.setText("▶ Play English Audio")
        self.progress_timer.stop()
        print("Streaming playback stopped")

    # --- File-based Audio Methods ---

    def set_audio_ready(self, audio_file_path, duration=None):
        """Called when audio is ready for playback"""
        self.audio_file_path = audio_file_path
        
        # Stop streaming if it was active
        if self.is_streaming:
            self.stop_streaming_playback()

        # Get actual audio length
        self.audio_length = self.get_audio_length(audio_file_path)

        print(f"Audio file: {audio_file_path}")
        print(f"Audio length: {self.audio_length} seconds")

        self.status_label.setText("✅ Audio ready")
        self.play_stop_btn.setEnabled(True)
        self.update_time_display()

        # Auto-start playback if not already playing via streaming
        if not self.is_playing:
            self.start_playback()

    def set_audio_error(self, error_message):
        """Called when audio generation fails"""
        self.status_label.setText(f"❌ Audio error: {error_message}")
        self.play_stop_btn.setEnabled(False)
        
        # Stop streaming if it was active
        if self.is_streaming:
            self.stop_streaming_playback()

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
        if self.is_streaming:
            self.stop_streaming_playback()
        elif not self.is_playing:
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
        if self.is_streaming and self.streaming_player:
            # Update based on streaming position
            self.current_position = self.streaming_player.get_current_position()
            # For streaming, we don't know total length, so just show current time
            current_seconds = int(self.current_position)
            current_time = f"{current_seconds//60:02d}:{current_seconds % 60:02d}"
            self.time_label.setText(f"{current_time} / --:--")
            # Progress bar in indeterminate mode for streaming
            self.progress_bar.setMaximum(0)  # Indeterminate
            
        elif self.is_playing and pygame.mixer.music.get_busy():
            # Audio is still playing
            self.current_position += 0.1  # Increment by 100ms

            # Calculate progress percentage
            if self.audio_length > 0:
                self.progress_bar.setMaximum(100)
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

        # Stop streaming playback
        if self.is_streaming:
            self.stop_streaming_playback()

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
