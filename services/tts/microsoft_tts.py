"""
Microsoft Edge Read Aloud (online) TTS service.
"""
import asyncio
import tempfile

from PySide6.QtCore import Signal, QThread

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False


class MicrosoftEdgeTTSThread(QThread):
    """Generate TTS audio using Microsoft Edge Read Aloud online voices."""

    tts_completed = Signal(str)  # Signal to emit generated audio file path
    tts_error = Signal(str)  # Signal for error messages
    progress_update = Signal(str)  # Signal for progress updates
    audio_chunk_ready = Signal(bytes, int)  # Kept for interface compatibility

    def __init__(
        self,
        text: str,
        voice: str = "en-US-EmmaMultilingualNeural",
        rate: str = "+0%",
        streaming: bool = False,
    ):
        super().__init__()
        self.text = text or ""
        self.voice = voice or "en-US-EmmaMultilingualNeural"
        self.rate = rate or "+0%"
        self.streaming = streaming
        self._stop_requested = False

    async def _generate_audio(self):
        """Generate MP3 audio and return its temp file path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name

        communicate = edge_tts.Communicate(
            text=self.text,
            voice=self.voice,
            rate=self.rate,
        )

        bytes_written = 0
        with open(temp_path, "wb") as out_file:
            async for chunk in communicate.stream():
                if self._stop_requested:
                    return None
                if chunk.get("type") == "audio":
                    data = chunk.get("data", b"")
                    out_file.write(data)
                    bytes_written += len(data)

        if bytes_written <= 0:
            raise RuntimeError("No audio data received from Microsoft TTS service.")

        return temp_path

    def run(self):
        """Run TTS generation."""
        if not HAS_EDGE_TTS:
            self.tts_error.emit(
                "edge-tts is not installed. Install it with: pip install edge-tts"
            )
            return

        if not self.text.strip():
            self.tts_error.emit("TTS text is empty.")
            return

        try:
            self.progress_update.emit("Generating TTS with Microsoft Read Aloud...")
            if self.streaming:
                self.progress_update.emit(
                    "Microsoft mode is generating a full audio file before playback."
                )

            audio_file_path = asyncio.run(self._generate_audio())
            if self._stop_requested or not audio_file_path:
                return
            self.tts_completed.emit(audio_file_path)
        except Exception as e:
            self.tts_error.emit(f"Microsoft TTS error: {e}")

    def stop(self):
        """Request to stop TTS generation."""
        self._stop_requested = True
