"""
Remote TTS service using WebSocket connection.
"""
import tempfile
import threading
from urllib.parse import urlencode

import numpy as np
from PySide6.QtCore import Signal, QThread

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    print("Warning: websocket-client not installed. Remote TTS will not work.")


class RemoteTTSThread(QThread):
    """Remote VibeVoice TTS client that connects to a WebSocket server for streaming TTS."""

    tts_completed = Signal(str)  # Signal to emit audio file path
    tts_error = Signal(str)  # Signal for error messages
    progress_update = Signal(str)  # Signal for progress updates
    # Signal for streaming: (audio_bytes, sample_rate)
    audio_chunk_ready = Signal(bytes, int)

    def __init__(self, text, server_url="ws://10.110.31.157:3000/stream", streaming=False, voice_preset="en-Emma_woman"):
        super().__init__()
        self.text = text
        self.server_url = server_url
        self.streaming = streaming
        self.voice_preset = voice_preset
        self.sample_rate = 24000  # Standard sample rate for VibeVoice

        # Audio storage
        self.audio_chunks = []
        self.all_audio_data = bytearray()

        # Control flags
        self._stop_requested = False
        self._connection_completed = False
        self._backend_busy = False

        # WebSocket reference for proper cleanup
        self._ws = None

    def _build_url(self):
        """Build the WebSocket URL with encoded text parameter and voice preset."""
        import time
        params = {
            "text": self.text,
            "voice": self.voice_preset,
            "cfg": "1.5",
            "steps": "5",
            "_t": str(int(time.time() * 1000)),
        }
        return f"{self.server_url}?{urlencode(params)}"

    def _parse_audio_chunk(self, data):
        """Parse incoming audio data and convert to 16-bit PCM bytes."""
        if isinstance(data, str):
            try:
                import base64
                data = base64.b64decode(data)
            except:
                data = data.encode('latin-1')

        try:
            audio_array = np.frombuffer(data, dtype=np.int16)

            if len(audio_array) > 0:
                max_val = np.max(np.abs(audio_array))
                if max_val > 32767:
                    print(
                        f"Warning: Audio data exceeds int16 range: {max_val}")

            return audio_array.tobytes()

        except Exception as e:
            print(
                f"Error parsing audio chunk: {e}, data length: {len(data) if data else 0}")
            return b''

    def _on_data(self, ws, data, data_type, continue_flag):
        """Handle incoming WebSocket data."""
        if self._stop_requested:
            return

        if data_type == 1:  # Text message
            try:
                import json
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                log_data = json.loads(data)
                event_type = log_data.get("event", "unknown")
                # print(f"[WebSocket Log] {event_type}: {log_data.get('data', {})}")

                if event_type == "backend_busy":
                    self._backend_busy = True
            except:
                print(f"[WebSocket] Received text: {str(data)[:100]}")
            return

        elif data_type == 2:  # Binary message (audio data)
            if isinstance(data, str):
                data = data.encode('latin-1')
            # print(
            #     f"[WebSocket] Received binary audio chunk: {len(data)} bytes")

            audio_bytes = self._parse_audio_chunk(data)

            if audio_bytes:
                self.all_audio_data.extend(audio_bytes)
                self.audio_chunks.append(audio_bytes)

                if self.streaming:
                    self.audio_chunk_ready.emit(audio_bytes, self.sample_rate)

    def _on_message(self, ws, message):
        """Fallback handler for when on_data is not available."""
        if self._stop_requested:
            return

        if isinstance(message, str):
            try:
                import json
                log_data = json.loads(message)
                event_type = log_data.get("event", "unknown")
                # print(f"[WebSocket Log] {event_type}: {log_data.get('data', {})}")
            except:
                print(f"[WebSocket] Received text message: {message[:100]}")
            return

        audio_bytes = self._parse_audio_chunk(message)

        if audio_bytes:
            self.all_audio_data.extend(audio_bytes)
            self.audio_chunks.append(audio_bytes)

            if self.streaming:
                self.audio_chunk_ready.emit(audio_bytes, self.sample_rate)

    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        error_str = str(error)

        if "opcode=8" in error_str or "fin=1" in error_str:
            print(f"[WebSocket] Connection closed normally by server")
            return

        error_msg = f"WebSocket error: {error_str}"
        print(f"[WebSocket Error] {error_msg}")
        self.tts_error.emit(error_msg)

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close."""
        if self._stop_requested:
            print("[WebSocket] Connection closed due to stop request")
            return

        normal_close_codes = [1000, 1005, 1006, None]

        is_normal_close = (
            close_status_code in normal_close_codes or
            (close_status_code is None and len(self.all_audio_data) > 0)
        )

        if is_normal_close and len(self.all_audio_data) > 0:
            print(
                f"[WebSocket] Streaming completed normally (code: {close_status_code})")
        elif close_status_code not in normal_close_codes:
            print(
                f"[WebSocket] Connection closed with code: {close_status_code} - {close_msg}")

        if self.all_audio_data:
            audio_file_path = self._save_audio(bytes(self.all_audio_data))
            self.tts_completed.emit(audio_file_path)
        else:
            if not is_normal_close:
                error_msg = f"Connection closed without audio data (code: {close_status_code})"
                print(f"[WebSocket] {error_msg}")
                self.tts_error.emit(error_msg)

    def _on_open(self, ws):
        """Handle WebSocket connection open."""
        self._connection_completed = True
        self.progress_update.emit(
            f"Connected to remote TTS server: {self.server_url}")

    def _save_audio(self, audio_bytes):
        """Save audio to temporary WAV file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            import wave

            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_bytes)

            return temp_file.name

    def run(self):
        """Run TTS generation via remote WebSocket server with retry on backend_busy."""
        if not HAS_WEBSOCKET:
            error_msg = "websocket-client library not installed. Please install it with: pip install websocket-client"
            self.tts_error.emit(error_msg)
            return

        print(
            f"[TTS Thread] Starting new TTS thread, stop_requested={self._stop_requested}")

        max_retries = 5
        retry_delay = 1.5

        for attempt in range(max_retries):
            if self._stop_requested:
                print("[TTS Thread] Stop requested, aborting")
                return

            # Reset state for each attempt
            self._backend_busy = False
            self.all_audio_data = bytearray()
            self.audio_chunks = []

            try:
                url = self._build_url()
                if attempt == 0:
                    print(f"[TTS Thread] Connecting to: {url[:100]}...")
                    self.progress_update.emit(f"Connecting to TTS server...")
                else:
                    print(
                        f"[TTS Thread] Retry {attempt}/{max_retries}: Connecting to: {url[:100]}...")
                    self.progress_update.emit(
                        f"Waiting for server... ({attempt}/{max_retries})")

                self._ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_data=self._on_data,
                    on_error=self._on_error,
                    on_close=self._on_close
                )

                print("[TTS Thread] Starting run_forever...")
                self._ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                    skip_utf8_validation=True,
                    reconnect=0
                )

                print("[TTS Thread] run_forever exited")
                self._ws = None

                if self._backend_busy:
                    print(
                        f"[TTS Thread] Backend busy, waiting {retry_delay}s before retry...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.3, 4.0)
                    continue

                if len(self.all_audio_data) > 0:
                    print(
                        f"[TTS Thread] Successfully received {len(self.all_audio_data)} bytes of audio")
                    return

                print("[TTS Thread] No audio received and no backend_busy flag")
                return

            except Exception as e:
                error_msg = f"Remote TTS error: {str(e)}"
                print(error_msg)
                self.tts_error.emit(error_msg)
                return
            finally:
                self._ws = None

        error_msg = f"Server busy after {max_retries} retries. Please try again later."
        print(f"[TTS Thread] {error_msg}")
        self.tts_error.emit(error_msg)
        print("[TTS Thread] Thread finished")

    def stop(self):
        """Request to stop TTS generation and close WebSocket connection."""
        self._stop_requested = True

        ws = self._ws
        if ws is not None:
            try:
                ws.close()
            except Exception as e:
                print(f"Error closing WebSocket gracefully: {e}")

            try:
                if ws.sock is not None:
                    ws.sock.close()
            except Exception as e:
                print(f"Error force closing WebSocket socket: {e}")

            self._ws = None


class RemoteTTSManager:
    """Manager for TTS providers."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._source = "remote"
        self._server_url = "ws://10.110.31.157:3000/stream"
        self._voice_preset = "en-Emma_woman"
        self._microsoft_voice = "en-US-EmmaMultilingualNeural"
        self._microsoft_rate = "+0%"

    def set_source(self, source):
        """Set active TTS source."""
        source = (source or "remote").strip().lower()
        self._source = source if source in {"remote", "microsoft"} else "remote"

    def get_source(self):
        """Get active TTS source."""
        return self._source

    def set_server_url(self, url):
        """Set the remote server URL."""
        self._server_url = url

    def get_server_url(self):
        """Get the current server URL."""
        return self._server_url

    def set_voice_preset(self, voice):
        """Set the voice preset to use."""
        self._voice_preset = voice

    def get_voice_preset(self):
        """Get the current voice preset."""
        return self._voice_preset

    def set_microsoft_voice(self, voice):
        """Set Microsoft Edge voice."""
        if voice and voice.strip():
            self._microsoft_voice = voice.strip()

    def get_microsoft_voice(self):
        """Get Microsoft Edge voice."""
        return self._microsoft_voice

    def set_microsoft_rate(self, rate):
        """Set Microsoft Edge speech rate."""
        if rate and rate.strip():
            self._microsoft_rate = rate.strip()

    def get_microsoft_rate(self):
        """Get Microsoft Edge speech rate."""
        return self._microsoft_rate

    def create_tts_thread(
        self,
        text,
        server_url=None,
        streaming=False,
        voice_preset=None,
        source=None,
        microsoft_voice=None,
        microsoft_rate=None,
    ):
        """Create a new TTS thread for the configured source."""
        selected_source = (source or self._source or "remote").strip().lower()

        if selected_source == "microsoft":
            from services.tts.microsoft_tts import MicrosoftEdgeTTSThread

            voice = microsoft_voice or self._microsoft_voice
            rate = microsoft_rate or self._microsoft_rate
            return MicrosoftEdgeTTSThread(
                text=text,
                voice=voice,
                rate=rate,
                streaming=streaming,
            )

        if server_url is None:
            server_url = self._server_url
        if voice_preset is None:
            voice_preset = self._voice_preset

        thread = RemoteTTSThread(text, server_url, streaming, voice_preset)
        return thread
