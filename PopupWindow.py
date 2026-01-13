import os
import tempfile
import time
import queue
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QTextBrowser,
    QPushButton, QProgressBar, QLabel, QSystemTrayIcon, QMenu, QApplication
)
from PySide6.QtCore import QTimer, QSettings, Qt as _Qt, Signal, QEvent
from PySide6.QtGui import QFont, QIcon, QAction, QMouseEvent, QTextCursor
import pygame

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("Warning: markdown library not installed. Dictionary will show plain text.")


class TranslatableTextEdit(QTextEdit):
    """Custom QTextEdit that shows translate popup when text is selected and mouse is released"""
    text_selected = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_selection = ""
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - show translate popup if text is selected"""
        # Let the parent handle the event first
        super().mouseReleaseEvent(event)
        
        # Check if there's a selection after mouse release
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()
        
        # Only emit if there's a new non-empty selection
        if selected_text and selected_text != self._last_selection:
            self._last_selection = selected_text
            # Small delay to ensure UI is stable
            QTimer.singleShot(50, self._emit_if_still_selected)
        elif not selected_text:
            self._last_selection = ""
    
    def _emit_if_still_selected(self):
        """Emit signal if text is still selected"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            self.text_selected.emit()


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
    # Signal emitted when popup is being destroyed
    popup_destroyed = Signal()
    
    def __init__(self, original_text, parent=None):
        super().__init__(parent)
        self.original_text = original_text
        self.corrected_text = ""
        self.translated_text = ""
        self.dictionary_thread = None  # For quick dictionary translation

        self.is_playing = False
        self.audio_file_path = None
        self.audio_length = 0
        self.current_position = 0

        # Streaming audio player
        self.streaming_player = None
        self.is_streaming = False
        self.streaming_chunks_received = 0
        self.streaming_position_at_end = 0  # Track position when streaming ends

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

        self.corrected_text_display = TranslatableTextEdit()
        self.corrected_text_display.setFont(QFont("Microsoft YaHei", 10))
        self.corrected_text_display.setPlainText("Correcting...")
        self.corrected_text_display.setReadOnly(True)
        self.corrected_text_display.setMaximumHeight(100)
        # Enable custom context menu
        self.corrected_text_display.setContextMenuPolicy(_Qt.CustomContextMenu)
        self.corrected_text_display.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(self.corrected_text_display, pos))
        # Connect text selection signal for translation popup
        self.corrected_text_display.text_selected.connect(
            lambda: self.show_translate_menu_for_selection(self.corrected_text_display))
        layout.addWidget(self.corrected_text_display)

        # Translated text section
        translated_label = QLabel("Translated Text:")
        translated_label.setFont(title_font)
        layout.addWidget(translated_label)

        self.translated_text_display = TranslatableTextEdit()
        self.translated_text_display.setFont(QFont("Microsoft YaHei", 10))
        self.translated_text_display.setPlainText("Translating...")
        self.translated_text_display.setReadOnly(True)
        self.translated_text_display.setMaximumHeight(100)
        # Enable custom context menu
        self.translated_text_display.setContextMenuPolicy(_Qt.CustomContextMenu)
        self.translated_text_display.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(self.translated_text_display, pos))
        # Connect text selection signal for translation popup
        self.translated_text_display.text_selected.connect(
            lambda: self.show_translate_menu_for_selection(self.translated_text_display))
        layout.addWidget(self.translated_text_display)

        # Quick Dictionary section (replaces English Text for TTS)
        dictionary_label = QLabel("📖 Quick Dictionary (select text above → popup menu → Translate):")
        dictionary_label.setFont(title_font)
        layout.addWidget(dictionary_label)

        # Use QTextBrowser for markdown rendering
        self.dictionary_display = QTextBrowser()
        self.dictionary_display.setFont(QFont("Microsoft YaHei", 10))
        self.dictionary_display.setPlainText("Double-click a word, or select text in Corrected/Translated sections, then right-click and choose 'Translate' to see the definition here.")
        self.dictionary_display.setOpenExternalLinks(True)
        self.dictionary_display.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                color: black;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        # Store raw markdown for updates
        self._dictionary_markdown = ""
        layout.addWidget(self.dictionary_display)

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

    def show_translate_menu_for_selection(self, text_edit):
        """Show translate menu at cursor position for the selected word"""
        cursor = text_edit.textCursor()
        if cursor.hasSelection():
            # Get cursor position in global coordinates
            cursor_rect = text_edit.cursorRect(cursor)
            global_pos = text_edit.mapToGlobal(cursor_rect.bottomRight())
            
            # Create a mini menu with just translate option
            menu = QMenu(self)
            translate_action = QAction("🔍 Translate to Dictionary", self)
            translate_action.triggered.connect(lambda: self.translate_selected(text_edit))
            menu.addAction(translate_action)
            menu.exec(global_pos)

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

    def show_context_menu(self, text_edit, pos):
        """Show custom context menu with Translate option"""
        menu = QMenu(self)
        
        # Get selected text
        cursor = text_edit.textCursor()
        selected_text = cursor.selectedText()
        
        # Add Copy action
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(text_edit.copy)
        copy_action.setEnabled(cursor.hasSelection())
        menu.addAction(copy_action)
        
        # Add Select All action
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(text_edit.selectAll)
        menu.addAction(select_all_action)
        
        menu.addSeparator()
        
        # Add Translate action
        translate_action = QAction("🔍 Translate to Dictionary", self)
        translate_action.triggered.connect(lambda: self.translate_selected(text_edit))
        translate_action.setEnabled(cursor.hasSelection())
        menu.addAction(translate_action)
        
        # Show menu at cursor position
        menu.exec(text_edit.mapToGlobal(pos))

    def translate_selected(self, text_edit):
        """Translate selected text and show in dictionary display"""
        cursor = text_edit.textCursor()
        selected_text = cursor.selectedText().strip()
        
        if not selected_text:
            return
        
        # Get context from the full text
        full_text = text_edit.toPlainText()
        
        # Show loading state
        self._dictionary_markdown = ""
        self.dictionary_display.setPlainText(f"🔄 Translating: {selected_text}...")
        
        # Start dictionary translation thread
        from DictionaryThread import DictionaryThread
        self.dictionary_thread = DictionaryThread(selected_text, full_text)
        self.dictionary_thread.translation_chunk.connect(self.on_dictionary_chunk)
        self.dictionary_thread.translation_done.connect(self.on_dictionary_done)
        self.dictionary_thread.start()

    def on_dictionary_chunk(self, chunk):
        """Handle streaming dictionary chunk"""
        # Accumulate markdown
        if self._dictionary_markdown == "" and self.dictionary_display.toPlainText().startswith("🔄 Translating:"):
            self._dictionary_markdown = ""
        
        self._dictionary_markdown += chunk
        
        # Render markdown to HTML
        self.update_dictionary_display()

    def update_dictionary_display(self):
        """Update dictionary display with rendered markdown"""
        if HAS_MARKDOWN:
            # Convert markdown to HTML with extensions
            html_content = markdown.markdown(
                self._dictionary_markdown,
                extensions=['extra', 'nl2br', 'sane_lists']
            )
            # Add some base styling
            styled_html = f"""
            <style>
                body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; }}
                h1, h2, h3 {{ color: #333; margin-top: 10px; }}
                strong {{ color: #0066cc; }}
                code {{ background-color: #e9ecef; padding: 2px 5px; border-radius: 3px; }}
                ul, ol {{ margin-left: 20px; }}
                p {{ margin: 5px 0; }}
            </style>
            {html_content}
            """
            self.dictionary_display.setHtml(styled_html)
        else:
            # Fallback to plain text
            self.dictionary_display.setPlainText(self._dictionary_markdown)

    def on_dictionary_done(self, result):
        """Handle dictionary translation completion"""
        # Final update with complete markdown
        if self._dictionary_markdown:
            self.update_dictionary_display()

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
        
    def stop_streaming_playback(self, wait_for_completion=False):
        """Stop streaming audio playback and save final position

        Args:
            wait_for_completion: If True, wait for queued audio to finish playing
        """
        if self.streaming_player:
            if wait_for_completion:
                # Wait for the audio queue to empty (play all queued audio)
                import time
                timeout = 5  # Maximum wait time in seconds
                start_time = time.time()
                while not self.streaming_player.audio_queue.empty():
                    if time.time() - start_time > timeout:
                        print(f"Timeout waiting for audio queue to empty")
                        break
                    time.sleep(0.1)

            # Save the position where streaming ended
            # Get position before stopping to ensure we capture the actual played position
            self.streaming_position_at_end = self.streaming_player.get_current_position()
            print(f"Streaming ended at position: {self.streaming_position_at_end:.2f} seconds")
            print(f"Total bytes played by streaming player: {self.streaming_player.total_bytes_played}")
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

        # Stop streaming if it was active (this saves streaming_position_at_end)
        # Wait for all queued audio to finish playing before stopping
        if self.is_streaming:
            print("Waiting for streaming playback to complete...")
            self.stop_streaming_playback(wait_for_completion=True)

        # Get actual audio length
        self.audio_length = self.get_audio_length(audio_file_path)

        print(f"Audio file: {audio_file_path}")
        print(f"Audio length: {self.audio_length} seconds")

        self.status_label.setText("✅ Audio ready")
        self.play_stop_btn.setEnabled(True)
        self.update_time_display()

        # Auto-start playback from streaming position if we have one
        print(f"Checking resume conditions: is_playing={self.is_playing}, streaming_position_at_end={self.streaming_position_at_end:.2f}")
        if not self.is_playing and self.streaming_position_at_end >= 0.1:
            print(f"Resuming playback from {self.streaming_position_at_end:.2f} seconds")
            self.start_playback_from_position(self.streaming_position_at_end)
        elif not self.is_playing:
            print("Starting playback from beginning")
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

    def start_playback_from_position(self, start_seconds):
        """Start audio playback from a specific position (for resuming after streaming)"""
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            print("Audio file not found")
            return

        try:
            # Stop any currently playing audio
            pygame.mixer.music.stop()

            # Load the WAV file and extract audio data
            import wave
            with wave.open(self.audio_file_path, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                channels = wav_file.getnchannels()
                sampwidth = wav_file.getsampwidth()

                # Calculate starting frame
                start_frame = int(start_seconds * sample_rate)

                if start_frame >= frames:
                    # Start position is beyond file length
                    print(f"Start position {start_seconds}s exceeds file length {frames/sample_rate:.2f}s")
                    self.start_playback()
                    return

                # Read audio data from the starting position
                wav_file.setpos(start_frame)
                audio_data = wav_file.readframes(frames - start_frame)

            # Create a temporary WAV file in memory with the trimmed audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                with wave.open(temp_file.name, 'wb') as out_wav:
                    out_wav.setnchannels(channels)
                    out_wav.setsampwidth(sampwidth)
                    out_wav.setframerate(sample_rate)
                    out_wav.writeframes(audio_data)

                # Load and play the trimmed audio file
                pygame.mixer.music.load(temp_file.name)
                pygame.mixer.music.play()

                # Store the temp file path for cleanup
                self._temp_audio_file = temp_file.name

            self.is_playing = True
            self.play_stop_btn.setText("⏸ Stop")
            self.current_position = start_seconds

            # Store offset for progress tracking
            self._playback_start_offset = start_seconds
            self._playback_start_time = time.time()

            # Start the progress timer
            self.progress_timer.start(100)  # Update every 100ms

            print(f"Audio playback started from {start_seconds:.2f}s: {self.audio_file_path}")

        except Exception as e:
            print(f"Error starting playback from position: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to regular playback if seeking fails
            self.start_playback()

    def stop_playback(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
        except:
            pass

        # Clean up temp audio file if it exists
        if hasattr(self, '_temp_audio_file') and self._temp_audio_file:
            try:
                if os.path.exists(self._temp_audio_file):
                    os.unlink(self._temp_audio_file)
                self._temp_audio_file = None
            except:
                pass

        # Stop Sound object if it was used for seeking
        if hasattr(self, '_sound_channel') and self._sound_channel:
            try:
                self._sound_channel.stop()
            except:
                pass
            self._sound_channel = None
            self._sound = None

        self.is_playing = False
        self.play_stop_btn.setText("▶ Play English Audio")
        self.progress_timer.stop()
        self.current_position = 0
        self.streaming_position_at_end = 0  # Reset streaming position
        self._playback_start_offset = 0
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

        elif self.is_playing:
            # Check if we have a playback offset (resumed from specific position)
            if hasattr(self, '_playback_start_offset') and self._playback_start_offset > 0:
                # Calculate position based on elapsed time since start plus offset
                elapsed = time.time() - self._playback_start_time
                self.current_position = self._playback_start_offset + elapsed

                # Calculate progress percentage
                if self.audio_length > 0:
                    self.progress_bar.setMaximum(100)
                    progress_percent = min(
                        100, (self.current_position / self.audio_length) * 100)
                    self.progress_bar.setValue(int(progress_percent))

                self.update_time_display()

                # Check if we've reached the end
                if self.current_position >= self.audio_length:
                    print("Audio playback completed")
                    self.stop_playback()

            elif pygame.mixer.music.get_busy():
                # Regular music playback from beginning
                self.current_position += 0.1  # Increment by 100ms

                # Calculate progress percentage
                if self.audio_length > 0:
                    self.progress_bar.setMaximum(100)
                    progress_percent = min(
                        100, (self.current_position / self.audio_length) * 100)
                    self.progress_bar.setValue(int(progress_percent))

                self.update_time_display()

            elif not pygame.mixer.music.get_busy():
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
        # Emit destroyed signal before cleanup
        self.popup_destroyed.emit()

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

        # Stop and wait for dictionary thread to finish
        if self.dictionary_thread and self.dictionary_thread.isRunning():
            print("Waiting for dictionary thread to finish...")
            # Disconnect signals to prevent updates after close
            try:
                self.dictionary_thread.translation_chunk.disconnect()
                self.dictionary_thread.translation_done.disconnect()
            except:
                pass
            # Request thread to stop gracefully
            self.dictionary_thread.stop()
            # Wait for thread to finish (with timeout)
            if not self.dictionary_thread.wait(1000):  # 1 second timeout
                print("Dictionary thread did not finish in time, terminating...")
                self.dictionary_thread.terminate()
                self.dictionary_thread.wait(500)
            self.dictionary_thread = None

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
