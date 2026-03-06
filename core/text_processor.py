"""
Text processing pipeline for correction, translation, and TTS.
"""
import time
import threading

from services.api.text_correction import TextCorrectionThread
from services.api.translation import TranslationThread
from services.tts.remote_tts import RemoteTTSManager


class TextProcessor:
    """Handles the text processing pipeline: correction -> translation + TTS."""

    def __init__(
        self,
        thread_manager,
        tts_server_type="microsoft",
        tts_remote_url="ws://10.110.31.157:3000/stream",
        tts_microsoft_voice="en-US-EmmaMultilingualNeural",
        tts_microsoft_rate="+0%",
    ):
        self.thread_manager = thread_manager
        self.tts_server_type = tts_server_type
        self.tts_remote_url = tts_remote_url
        self.tts_microsoft_voice = tts_microsoft_voice
        self.tts_microsoft_rate = tts_microsoft_rate

        # TTS managers
        self.vibevoice_manager = None  # Local model manager
        self.vibevoice_remote_manager = RemoteTTSManager()
        self.vibevoice_remote_manager.set_source(tts_server_type)
        self.vibevoice_remote_manager.set_server_url(tts_remote_url)
        self.vibevoice_remote_manager.set_microsoft_voice(tts_microsoft_voice)
        self.vibevoice_remote_manager.set_microsoft_rate(tts_microsoft_rate)

        # Callbacks
        self.on_correction_chunk = None
        self.on_correction_done = None
        self.on_correction_error = None
        self.on_translation_chunk = None
        self.on_translation_done = None
        self.on_translation_error = None
        self.on_tts_completed = None
        self.on_tts_error = None
        self.on_tts_progress = None
        self.on_audio_chunk_ready = None

    def set_tts_config(
        self,
        server_type,
        remote_url,
        microsoft_voice=None,
        microsoft_rate=None,
    ):
        """Update TTS configuration."""
        self.tts_server_type = server_type
        self.tts_remote_url = remote_url
        if microsoft_voice is not None:
            self.tts_microsoft_voice = microsoft_voice
        if microsoft_rate is not None:
            self.tts_microsoft_rate = microsoft_rate

        self.vibevoice_remote_manager.set_source(server_type)
        self.vibevoice_remote_manager.set_server_url(remote_url)
        self.vibevoice_remote_manager.set_microsoft_voice(self.tts_microsoft_voice)
        self.vibevoice_remote_manager.set_microsoft_rate(self.tts_microsoft_rate)

    def process_text(self, text):
        """
        Start the text processing pipeline.

        Args:
            text: Text to process
        """
        # Stop any existing threads
        self.thread_manager.stop_all_threads()

        # Start correction thread
        correction_thread = TextCorrectionThread(text, 'deepseek')

        if self.on_correction_chunk:
            correction_thread.correction_chunk.connect(self.on_correction_chunk)
        if self.on_correction_done:
            correction_thread.correction_done.connect(self._handle_correction_done)
        if self.on_correction_error:
            correction_thread.correction_error.connect(self.on_correction_error)

        self.thread_manager.set_correction_thread(correction_thread)
        correction_thread.start()

    def _handle_correction_done(self, corrected_text):
        """Handle correction completion - start translation and TTS in parallel."""
        print(f"Correction completed: {corrected_text[:50]}...")

        # Call user callback
        if self.on_correction_done:
            self.on_correction_done(corrected_text)

        # Start translation thread
        translation_thread = TranslationThread(corrected_text, 'deepseek')

        if self.on_translation_chunk:
            translation_thread.translation_chunk.connect(self.on_translation_chunk)
        if self.on_translation_done:
            translation_thread.translation_done.connect(self.on_translation_done)
        if self.on_translation_error:
            translation_thread.translation_error.connect(self.on_translation_error)

        self.thread_manager.set_translation_thread(translation_thread)
        translation_thread.start()

        # Start TTS in a separate thread to avoid blocking translation
        tts_starter = threading.Thread(
            target=self._start_tts, args=(corrected_text,), daemon=True)
        tts_starter.start()

    def _start_tts(self, text):
        """Start TTS thread with the given text."""
        try:
            # Use local TTS only when explicitly selected; otherwise use manager providers.
            if self.tts_server_type in ("remote", "microsoft"):
                use_streaming = self.tts_server_type == "remote"
                tts_thread = self.vibevoice_remote_manager.create_tts_thread(
                    text=text,
                    server_url=self.tts_remote_url,
                    source=self.tts_server_type,
                    microsoft_voice=self.tts_microsoft_voice,
                    microsoft_rate=self.tts_microsoft_rate,
                    streaming=use_streaming
                )
                if self.tts_server_type == "microsoft":
                    print(
                        f"Using Microsoft Read Aloud: voice={self.tts_microsoft_voice}, "
                        f"rate={self.tts_microsoft_rate}"
                    )
                else:
                    print(f"Using remote TTS server: {self.tts_remote_url}")
            else:
                # Use local TTS model
                if self.vibevoice_manager is None:
                    from VibeVoiceTTS import VibeVoiceModelManager
                    self.vibevoice_manager = VibeVoiceModelManager()

                tts_thread = self.vibevoice_manager.create_tts_thread(
                    text=text,
                    model_path="microsoft/VibeVoice-Realtime-0.5B",
                    device="cuda",
                    streaming=True
                )
                print("Using local TTS model")

            if self.on_tts_completed:
                tts_thread.tts_completed.connect(self.on_tts_completed)
            if self.on_tts_error:
                tts_thread.tts_error.connect(self.on_tts_error)
            if self.on_tts_progress:
                tts_thread.progress_update.connect(self.on_tts_progress)
            if self.on_audio_chunk_ready:
                tts_thread.audio_chunk_ready.connect(self.on_audio_chunk_ready)

            self.thread_manager.set_tts_thread(tts_thread)
            tts_thread.start()

        except Exception as e:
            print(f"Failed to start TTS: {e}")
            if self.on_tts_error:
                self.on_tts_error(f"Failed to start TTS: {str(e)}")

    def preload_local_model(self):
        """Preload the local VibeVoice model in background."""
        def load_model():
            from VibeVoiceTTS import VibeVoiceModelManager
            self.vibevoice_manager = VibeVoiceModelManager()
            self.vibevoice_manager.get_tts_instance(
                model_path="microsoft/VibeVoice-Realtime-0.5B",
                device="cuda"
            )
            print("VibeVoice model loaded successfully!")

        thread = threading.Thread(target=load_model, daemon=True)
        thread.start()
