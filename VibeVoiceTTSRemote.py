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


class VibeVoiceTTSRemote(QThread):
    """Remote VibeVoice TTS client that connects to a WebSocket server for streaming TTS"""

    tts_completed = Signal(str)  # Signal to emit audio file path
    tts_error = Signal(str)  # Signal for error messages
    progress_update = Signal(str)  # Signal for progress updates
    audio_chunk_ready = Signal(bytes, int)  # Signal for streaming: (audio_bytes, sample_rate)

    def __init__(self, text, server_url="ws://10.110.31.157:3000/stream", streaming=False, voice_preset="en-Carter_man"):
        super().__init__()
        self.text = text
        self.server_url = server_url
        self.streaming = streaming
        self.voice_preset = voice_preset  # Voice preset to use (e.g., "en-Carter_man")
        self.sample_rate = 24000  # Standard sample rate for VibeVoice

        # Audio storage
        self.audio_chunks = []
        self.all_audio_data = bytearray()

        # Control flags
        self._stop_requested = False
        self._connection_completed = False  # Track if connection completed successfully

    def _build_url(self):
        """Build the WebSocket URL with encoded text parameter and voice preset"""
        from urllib.parse import urlencode
        params = {
            "text": self.text,
            "voice": self.voice_preset,
            "cfg": "1.5",  # Default CFG scale
            "steps": "5",  # Default inference steps
        }
        return f"{self.server_url}?{urlencode(params)}"

    def _parse_audio_chunk(self, data):
        """Parse incoming audio data and convert to 16-bit PCM bytes

        The VibeVoice server sends int16 PCM audio data (little-endian).
        Each sample is a 16-bit signed integer that needs to be converted.
        """
        # Convert string to bytes if needed (shouldn't happen with on_data callback)
        if isinstance(data, str):
            try:
                # Try to decode base64 encoded data
                import base64
                data = base64.b64decode(data)
            except:
                # If not base64, encode as latin-1 (preserves byte values)
                data = data.encode('latin-1')

        try:
            # The server sends int16 PCM data directly (little-endian)
            # Just verify it's already int16 and return as-is
            audio_array = np.frombuffer(data, dtype=np.int16)

            # Optional: Verify the data is in valid range
            if len(audio_array) > 0:
                max_val = np.max(np.abs(audio_array))
                if max_val > 32767:
                    print(f"Warning: Audio data exceeds int16 range: {max_val}")

            # Return the bytes directly (already in int16 PCM format)
            return audio_array.tobytes()

        except Exception as e:
            print(f"Error parsing audio chunk: {e}, data length: {len(data) if data else 0}")
            return b''

    def _on_data(self, ws, data, data_type, continue_flag):
        """Handle incoming WebSocket data - this gives us control over frame type"""
        if self._stop_requested:
            return

        # data_type: 1 = text (UTF-8), 2 = binary
        if data_type == 1:
            # Text message (JSON log)
            try:
                import json
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                log_data = json.loads(data)
                event_type = log_data.get("event", "unknown")
                print(f"[WebSocket Log] {event_type}: {log_data.get('data', {})}")
            except:
                print(f"[WebSocket] Received text: {str(data)[:100]}")
            return

        elif data_type == 2:
            # Binary message (audio data)
            if isinstance(data, str):
                data = data.encode('latin-1')
            print(f"[WebSocket] Received binary audio chunk: {len(data)} bytes")

            # Parse and emit audio chunk
            audio_bytes = self._parse_audio_chunk(data)

            if audio_bytes:
                self.all_audio_data.extend(audio_bytes)
                self.audio_chunks.append(audio_bytes)

                # Emit chunk for streaming playback
                if self.streaming:
                    self.audio_chunk_ready.emit(audio_bytes, self.sample_rate)
            else:
                print(f"[WebSocket] Failed to parse audio chunk, length: {len(data)}")

    def _on_message(self, ws, message):
        """Fallback handler for when on_data is not available"""
        if self._stop_requested:
            return

        # Check message type
        if isinstance(message, str):
            # This is a text message (JSON log), skip it
            try:
                import json
                log_data = json.loads(message)
                event_type = log_data.get("event", "unknown")
                print(f"[WebSocket Log] {event_type}: {log_data.get('data', {})}")
            except:
                print(f"[WebSocket] Received text message: {message[:100]}")
            # Don't process text messages as audio
            return

        # This is a binary message (audio data)
        print(f"[WebSocket] Received binary audio chunk: {len(message)} bytes")

        # Parse and emit audio chunk
        audio_bytes = self._parse_audio_chunk(message)

        if audio_bytes:
            self.all_audio_data.extend(audio_bytes)
            self.audio_chunks.append(audio_bytes)

            # Emit chunk for streaming playback
            if self.streaming:
                self.audio_chunk_ready.emit(audio_bytes, self.sample_rate)
        else:
            print(f"[WebSocket] Failed to parse audio chunk, length: {len(message)}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors - only emit for real errors, not normal closure"""
        error_str = str(error)

        # Ignore normal closure errors (opcode 8 is normal close)
        # The websocket-client library reports normal closure as an error
        if "opcode=8" in error_str or "fin=1" in error_str:
            # This is a normal closure, not an error
            print(f"[WebSocket] Connection closed normally by server")
            return

        # Only emit for actual errors
        error_msg = f"WebSocket error: {error_str}"
        print(f"[WebSocket Error] {error_msg}")
        self.tts_error.emit(error_msg)

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        # Normal close codes: 1000 (normal), 1005 (no status)
        # The server may close with various codes after streaming completes
        normal_close_codes = [1000, 1005, 1006, None]

        is_normal_close = (
            close_status_code in normal_close_codes or
            (close_status_code is None and len(self.all_audio_data) > 0)
        )

        if is_normal_close and len(self.all_audio_data) > 0:
            print(f"[WebSocket] Streaming completed normally (code: {close_status_code})")
        elif close_status_code not in normal_close_codes:
            print(f"[WebSocket] Connection closed with code: {close_status_code} - {close_msg}")

        # Save audio to file if we received any data
        if self.all_audio_data:
            audio_file_path = self._save_audio(bytes(self.all_audio_data))
            self.tts_completed.emit(audio_file_path)
        else:
            # Emit error if no audio data was received and it wasn't a normal close
            if not is_normal_close:
                error_msg = f"Connection closed without audio data (code: {close_status_code})"
                print(f"[WebSocket] {error_msg}")
                self.tts_error.emit(error_msg)

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        self._connection_completed = True
        self.progress_update.emit(f"Connected to remote TTS server: {self.server_url}")

    def _save_audio(self, audio_bytes):
        """Save audio to temporary WAV file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            import wave

            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_bytes)

            return temp_file.name

    def run(self):
        """Run TTS generation via remote WebSocket server"""
        if not HAS_WEBSOCKET:
            error_msg = "websocket-client library not installed. Please install it with: pip install websocket-client"
            self.tts_error.emit(error_msg)
            return

        try:
            url = self._build_url()
            self.progress_update.emit(f"Connecting to remote TTS server...")

            # Create WebSocket connection with explicit binary mode
            # Use on_data callback to properly handle both text and binary frames
            ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_data=self._on_data,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # Run WebSocket connection (this blocks until connection closes)
            # Enable ping and suppress close errors
            ws.run_forever(ping_interval=30, ping_timeout=10)

        except Exception as e:
            error_msg = f"Remote TTS error: {str(e)}"
            print(error_msg)
            self.tts_error.emit(error_msg)

    def stop(self):
        """Request to stop TTS generation"""
        self._stop_requested = True


class VibeVoiceTTSRemoteManager:
    """Manager for remote VibeVoice TTS - follows the same pattern as VibeVoiceModelManager"""

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
        self._server_url = "ws://10.110.31.157:3000/stream"  # Default server
        self._voice_preset = "en-Carter_man"  # Default voice preset

    def set_server_url(self, url):
        """Set the remote server URL"""
        self._server_url = url

    def get_server_url(self):
        """Get the current server URL"""
        return self._server_url

    def set_voice_preset(self, voice):
        """Set the voice preset to use"""
        self._voice_preset = voice

    def get_voice_preset(self):
        """Get the current voice preset"""
        return self._voice_preset

    def create_tts_thread(self, text, server_url=None, streaming=False, voice_preset=None):
        """Create a new TTS thread for remote server"""
        if server_url is None:
            server_url = self._server_url
        if voice_preset is None:
            voice_preset = self._voice_preset

        thread = VibeVoiceTTSRemote(text, server_url, streaming, voice_preset)
        return thread
