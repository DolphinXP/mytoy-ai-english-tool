"""
Streaming audio player for real-time audio playback.
"""
import queue
import threading


class StreamingAudioPlayer:
    """Real-time audio streaming player using pyaudio."""

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
        """Start the streaming playback."""
        if self.is_playing:
            return

        self.stop_event.clear()
        self.is_playing = True
        self.total_bytes_played = 0
        self.playback_thread = threading.Thread(
            target=self._playback_loop, daemon=True)
        self.playback_thread.start()

    def add_audio_chunk(self, audio_bytes):
        """Add an audio chunk to the playback queue."""
        if self.is_playing:
            self.audio_queue.put(audio_bytes)

    def stop(self):
        """Stop the streaming playback."""
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
        """Main playback loop running in a separate thread."""
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
        """Get current playback position in seconds."""
        bytes_per_sample = self.sample_width * self.channels
        samples_played = self.total_bytes_played / bytes_per_sample
        return samples_played / self.sample_rate
