"""
Audio playback mixin for PopupWindow.
Handles streaming and file-based audio playback.
"""
import time


class AudioMixin:
    """Mixin providing audio playback functionality."""

    def _init_audio_state(self):
        """Initialize audio-related state variables."""
        from services.audio.file_player import FileAudioPlayer
        self.file_player = FileAudioPlayer()
        self.streaming_player = None
        self.is_streaming = False
        self.is_playing = False
        self.streaming_chunks_received = 0
        self.streaming_position_at_end = 0
        self._streaming_done = False
        self._drain_idle_ticks = 0
        self._last_stream_chunk_time = None

    # ── Streaming audio ────────────────────────────────────────────────

    def start_streaming_playback(self):
        """Initialize streaming audio playback."""
        from services.audio.streaming_player import StreamingAudioPlayer

        if self.streaming_player is not None:
            print("Stopping existing streaming player before starting new one")
            self.streaming_player.stop()
            if self.streaming_player.playback_thread and self.streaming_player.playback_thread.is_alive():
                self.streaming_player.playback_thread.join(timeout=2.0)
            self.streaming_player = None
            time.sleep(0.2)

        self.is_streaming = True
        self.streaming_chunks_received = 0
        self._streaming_done = False
        self._drain_idle_ticks = 0
        self._last_stream_chunk_time = None
        self.streaming_player = StreamingAudioPlayer(sample_rate=24000)
        self.streaming_player.start()
        self.is_playing = True

        self.audio_controls.set_playing(True)
        self.audio_controls.set_enabled(True)
        self.progress_timer.start(100)
        self.set_status(self.icon_mgr.get_icon_label("audio", "Streaming audio..."))
        print("Streaming playback started")

    def on_audio_chunk_ready(self, audio_bytes, sample_rate):
        """Handle incoming audio chunk for streaming playback."""
        sender = self.sender()
        if hasattr(self, 'retranslate_tts_thread') and sender != self.retranslate_tts_thread:
            return

        if not self.is_streaming:
            self.start_streaming_playback()

        self.streaming_chunks_received += 1
        self._last_stream_chunk_time = time.time()
        self._drain_idle_ticks = 0

        if self.streaming_player:
            self.streaming_player.add_audio_chunk(audio_bytes)

        self.set_status(self.icon_mgr.get_icon_label(
            "audio", f"Streaming audio... ({self.streaming_chunks_received} chunks)"))

    def stop_streaming_playback(self, wait_for_completion=False):
        """Stop streaming audio playback."""
        if self.streaming_player:
            if wait_for_completion:
                timeout_time = time.time() + 5
                while not self.streaming_player.audio_queue.empty():
                    if time.time() > timeout_time:
                        break
                    time.sleep(0.1)

            self.streaming_position_at_end = self.streaming_player.get_current_position()
            print(f"Streaming ended at position: {self.streaming_position_at_end:.2f}s")
            self.streaming_player.stop()
            if self.streaming_player.playback_thread and self.streaming_player.playback_thread.is_alive():
                self.streaming_player.playback_thread.join(timeout=2.0)
            self.streaming_player = None

        self.is_streaming = False
        self.is_playing = False
        self.audio_controls.set_playing(False)
        self.progress_timer.stop()
        self._streaming_done = False
        self._drain_idle_ticks = 0
        self.audio_controls.set_progress_range(0, 100)
        self.audio_controls.set_progress(0)
        self.audio_controls.set_time(0, self.file_player.audio_length)
        print("Streaming playback stopped")

    # ── File audio ─────────────────────────────────────────────────────

    def set_audio_ready(self, audio_file_path):
        """Called when audio file is ready for playback."""
        self.file_player.load_audio(audio_file_path)
        print(f"Audio file: {audio_file_path}, length: {self.file_player.audio_length}s")

        if self.is_streaming:
            self.set_status("Draining audio buffer...")
            self._streaming_done = True
        else:
            self.set_status(self.icon_mgr.get_icon_label("ready", "Audio ready"))

        self.audio_controls.set_enabled(True)
        self.audio_controls.set_time(0, self.file_player.audio_length)

    def set_audio_error(self, error_message):
        """Called when audio generation fails."""
        self.set_status(self.icon_mgr.get_icon_label("error", f"Audio error: {error_message}"))
        self.audio_controls.set_enabled(False)
        if self.is_streaming:
            self.stop_streaming_playback()

    # ── Playback controls ──────────────────────────────────────────────

    def _on_play(self):
        if self.is_streaming:
            self.stop_streaming_playback()
        elif not self.is_playing:
            self._start_file_playback()

    def _on_stop(self):
        if self.is_streaming:
            self.stop_streaming_playback()
        elif self.is_playing:
            self._stop_file_playback()

    def _start_file_playback(self):
        if self.file_player.play():
            self.is_playing = True
            self.audio_controls.set_playing(True)
            self.progress_timer.start(100)

    def _stop_file_playback(self):
        self.file_player.stop()
        self.is_playing = False
        self.streaming_position_at_end = 0
        self.audio_controls.set_playing(False)
        self.audio_controls.set_progress(0)
        self.audio_controls.set_time(0, self.file_player.audio_length)
        self.progress_timer.stop()
        print("Audio playback stopped")

    # ── Progress timer ─────────────────────────────────────────────────

    def _update_progress(self):
        if self.is_streaming and self.streaming_player:
            pos = self.streaming_player.get_current_position()
            secs = int(pos)
            self.audio_controls.set_time_text(f"{secs // 60:02d}:{secs % 60:02d} / --:--")
            self.audio_controls.set_progress_range(0, 0)  # indeterminate

            if self._streaming_done:
                if self.streaming_player.audio_queue.empty():
                    last = self._last_stream_chunk_time or time.time()
                    if time.time() - last >= 0.5:
                        self._drain_idle_ticks += 1
                else:
                    self._drain_idle_ticks = 0

                if self._drain_idle_ticks >= 2:
                    print("Streaming playback completed")
                    self.stop_streaming_playback(wait_for_completion=False)
                    self._streaming_done = False
                    self._drain_idle_ticks = 0
                    self.set_status(self.icon_mgr.get_icon_label("ready", "Audio ready"))
                    return

        elif self.is_playing:
            self.file_player.update_position()
            pos = self.file_player.current_position
            length = self.file_player.audio_length

            self.audio_controls.set_progress_range(0, 100)
            if length > 0:
                self.audio_controls.set_progress(min(100, (pos / length) * 100))
            self.audio_controls.set_time(pos, length)

            if self.file_player.is_finished() if hasattr(self.file_player, 'is_finished') else not self.file_player.is_busy():
                print("Audio playback completed")
                self._stop_file_playback()

    def _cleanup_audio(self):
        """Clean up audio resources on close."""
        if self.is_streaming:
            self.stop_streaming_playback()
        if self.is_playing:
            self._stop_file_playback()
        self.file_player.cleanup()
