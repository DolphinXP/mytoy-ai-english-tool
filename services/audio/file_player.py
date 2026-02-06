"""
File-based audio player using pygame.
"""
import os
import time
import tempfile
import wave
import pygame


class FileAudioPlayer:
    """File-based audio player using pygame mixer."""

    def __init__(self):
        self.is_playing = False
        self.audio_file_path = None
        self.audio_length = 0
        self.current_position = 0
        self._playback_start_offset = 0
        self._playback_start_time = 0
        self._temp_audio_file = None
        self._sound_channel = None
        self._sound = None

        # Initialize pygame mixer
        try:
            pygame.mixer.init()
        except:
            pygame.mixer.quit()
            pygame.mixer.init()

    def load_audio(self, audio_file_path):
        """
        Load an audio file for playback.

        Args:
            audio_file_path: Path to the audio file

        Returns:
            Audio length in seconds
        """
        self.audio_file_path = audio_file_path
        self.audio_length = self._get_audio_length(audio_file_path)
        return self.audio_length

    def _get_audio_length(self, audio_file_path):
        """Get the actual length of the audio file."""
        try:
            sound = pygame.mixer.Sound(audio_file_path)
            length_seconds = sound.get_length()
            return int(length_seconds)
        except Exception as e:
            print(f"Error getting audio length: {e}")
            return 30  # Default fallback

    def play(self):
        """Start audio playback from the beginning."""
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            print("Audio file not found")
            return False

        try:
            # Stop any currently playing audio
            pygame.mixer.music.stop()

            # Load and play the audio file
            pygame.mixer.music.load(self.audio_file_path)
            pygame.mixer.music.play()

            self.is_playing = True
            self.current_position = 0
            self._playback_start_offset = 0

            print(f"Audio playback started: {self.audio_file_path}")
            return True

        except Exception as e:
            print(f"Error starting playback: {e}")
            return False

    def play_from_position(self, start_seconds):
        """
        Start audio playback from a specific position.

        Args:
            start_seconds: Starting position in seconds
        """
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            print("Audio file not found")
            return False

        try:
            # Stop any currently playing audio
            pygame.mixer.music.stop()

            # Load the WAV file and extract audio data
            with wave.open(self.audio_file_path, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                channels = wav_file.getnchannels()
                sampwidth = wav_file.getsampwidth()

                # Calculate starting frame
                start_frame = int(start_seconds * sample_rate)

                if start_frame >= frames:
                    print(f"Start position {start_seconds}s exceeds file length {frames/sample_rate:.2f}s")
                    return self.play()

                # Read audio data from the starting position
                wav_file.setpos(start_frame)
                audio_data = wav_file.readframes(frames - start_frame)

            # Create a temporary WAV file with the trimmed audio
            temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
            os.close(temp_fd)
            with wave.open(temp_path, 'wb') as out_wav:
                out_wav.setnchannels(channels)
                out_wav.setsampwidth(sampwidth)
                out_wav.setframerate(sample_rate)
                out_wav.writeframes(audio_data)

            # Load and play the trimmed audio file
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            # Store the temp file path for cleanup
            self._temp_audio_file = temp_path

            self.is_playing = True
            self.current_position = start_seconds
            self._playback_start_offset = start_seconds
            self._playback_start_time = time.time()

            print(f"Audio playback started from {start_seconds:.2f}s: {self.audio_file_path}")
            return True

        except Exception as e:
            print(f"Error starting playback from position: {e}")
            return self.play()

    def stop(self):
        """Stop audio playback."""
        try:
            pygame.mixer.music.stop()
        except:
            pass

        # Clean up temp audio file if it exists
        if self._temp_audio_file:
            try:
                if os.path.exists(self._temp_audio_file):
                    os.unlink(self._temp_audio_file)
                self._temp_audio_file = None
            except:
                pass

        # Stop Sound object if it was used
        if self._sound_channel:
            try:
                self._sound_channel.stop()
            except:
                pass
            self._sound_channel = None
            self._sound = None

        self.is_playing = False
        self.current_position = 0
        self._playback_start_offset = 0

    def update_position(self):
        """
        Update current playback position.

        Returns:
            Current position in seconds
        """
        if not self.is_playing:
            return self.current_position

        # Check if we have a playback offset
        if self._playback_start_offset > 0:
            elapsed = time.time() - self._playback_start_time
            self.current_position = self._playback_start_offset + elapsed
        elif pygame.mixer.music.get_busy():
            self.current_position += 0.1  # Increment by 100ms
        else:
            # Audio finished playing
            self.is_playing = False

        return self.current_position

    def is_busy(self):
        """Check if audio is currently playing."""
        return pygame.mixer.music.get_busy()

    def cleanup(self):
        """Clean up resources."""
        self.stop()
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
