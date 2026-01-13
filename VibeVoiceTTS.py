import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PySide6.QtCore import Signal, QThread

# Add VibeVoice to path
import sys
vibevoice_path = Path(__file__).parent / "VibeVoice"
sys.path.insert(0, str(vibevoice_path))

from vibevoice.modular.modeling_vibevoice_streaming_inference import (
    VibeVoiceStreamingForConditionalGenerationInference,
)
from vibevoice.processor.vibevoice_streaming_processor import (
    VibeVoiceStreamingProcessor,
)
from vibevoice.modular.streamer import AudioStreamer

import copy


class VibeVoiceTTS(QThread):
    tts_completed = Signal(str)  # Signal to emit audio file path
    tts_error = Signal(str)  # Signal for error messages
    progress_update = Signal(str)  # Signal for progress updates

    def __init__(self, text, model_path="microsoft/VibeVoice-Realtime-0.5B", device="cuda", voice_preset="en-Carter_man"):
        super().__init__()
        self.text = text
        self.model_path = model_path
        self.device = device
        self.voice_preset = voice_preset
        self.sample_rate = 24_000
        self.inference_steps = 5

        # Model components (loaded lazily)
        self._processor = None
        self._model = None
        self._voice_cache = {}
        self._default_voice_key = None
        self._voice_presets = {}
        self._model_loaded = False

    def _load_model(self):
        """Load the VibeVoice model and processor"""
        if self._model_loaded:
            return

        try:
            self.progress_update.emit("Loading VibeVoice model...")

            # Load processor
            self._processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_path)

            # Determine device settings
            if self.device == "mps":
                load_dtype = torch.float32
                device_map = None
                attn_impl = "sdpa"
            elif self.device == "cuda":
                load_dtype = torch.bfloat16
                device_map = 'cuda'
                attn_impl = "flash_attention_2"
            else:
                load_dtype = torch.float32
                device_map = 'cpu'
                attn_impl = "sdpa"

            # Load model
            self._model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                self.model_path,
                torch_dtype=load_dtype,
                device_map=device_map,
                attn_implementation=attn_impl,
            )

            if self.device == "mps":
                self._model.to("mps")

            self._model.eval()

            # Configure scheduler
            self._model.model.noise_scheduler = self._model.model.noise_scheduler.from_config(
                self._model.model.noise_scheduler.config,
                algorithm_type="sde-dpmsolver++",
                beta_schedule="squaredcos_cap_v2",
            )
            self._model.set_ddpm_inference_steps(num_steps=self.inference_steps)

            # Load voice presets
            self._load_voice_presets()

            self._model_loaded = True
            self.progress_update.emit("Model loaded successfully")

        except Exception as e:
            self.progress_update.emit(f"Error loading model: {str(e)}")
            raise

    def _load_voice_presets(self):
        """Load available voice presets"""
        voices_dir = Path(__file__).parent / "VibeVoice" / "demo" / "voices" / "streaming_model"
        if not voices_dir.exists():
            print(f"Warning: Voices directory not found: {voices_dir}")
            self._voice_presets = {}
            return

        for pt_path in voices_dir.rglob("*.pt"):
            self._voice_presets[pt_path.stem] = pt_path

        # Set default voice to en-Carter_man
        if self.voice_preset and self.voice_preset in self._voice_presets:
            self._default_voice_key = self.voice_preset
        elif "en-Carter_man" in self._voice_presets:
            self._default_voice_key = "en-Carter_man"
        elif self._voice_presets:
            self._default_voice_key = next(iter(self._voice_presets))
        else:
            self._default_voice_key = None

        print(f"Found {len(self._voice_presets)} voice presets, using: {self._default_voice_key}")

    def _get_voice_resources(self, voice_key=None):
        """Get voice preset resources"""
        key = voice_key if voice_key and voice_key in self._voice_presets else self._default_voice_key
        if not key:
            raise RuntimeError("No voice preset available")

        if key not in self._voice_cache:
            preset_path = self._voice_presets[key]
            torch_device = torch.device(self.device)
            print(f"Loading voice preset {key} from {preset_path}")
            prefilled_outputs = torch.load(
                preset_path,
                map_location=torch_device,
                weights_only=False,
            )
            self._voice_cache[key] = prefilled_outputs

        return self._voice_cache[key]

    def _prepare_inputs(self, text, prefilled_outputs):
        """Prepare model inputs"""
        if not self._processor or not self._model:
            raise RuntimeError("Model not loaded")

        processor_kwargs = {
            "text": text.strip(),
            "cached_prompt": prefilled_outputs,
            "padding": True,
            "return_tensors": "pt",
            "return_attention_mask": True,
        }

        processed = self._processor.process_input_with_cached_prompt(**processor_kwargs)
        torch_device = torch.device(self.device)

        prepared = {
            key: value.to(torch_device) if hasattr(value, "to") else value
            for key, value in processed.items()
        }
        return prepared

    def _generate_audio(self, text, voice_key=None):
        """Generate audio from text"""
        # Get voice resources
        prefilled_outputs = self._get_voice_resources(voice_key)

        # Prepare inputs
        text = text.replace("'", "'")
        inputs = self._prepare_inputs(text, prefilled_outputs)

        # Create audio streamer
        audio_streamer = AudioStreamer(batch_size=1, stop_signal=None, timeout=None)
        errors = []
        stop_event = threading.Event()

        # Generation function for thread
        def run_generation():
            try:
                self._model.generate(
                    **inputs,
                    max_new_tokens=None,
                    cfg_scale=1.5,
                    tokenizer=self._processor.tokenizer,
                    generation_config={
                        "do_sample": False,
                    },
                    audio_streamer=audio_streamer,
                    stop_check_fn=stop_event.is_set,
                    verbose=False,
                    refresh_negative=True,
                    all_prefilled_outputs=copy.deepcopy(prefilled_outputs),
                )
            except Exception as exc:
                errors.append(exc)
                audio_streamer.end()

        # Start generation in background thread
        thread = threading.Thread(target=run_generation, daemon=True)
        thread.start()

        # Collect audio chunks
        audio_chunks = []
        try:
            stream = audio_streamer.get_stream(0)
            for audio_chunk in stream:
                if torch.is_tensor(audio_chunk):
                    audio_chunk = audio_chunk.detach().cpu().to(torch.float32).numpy()
                else:
                    audio_chunk = np.asarray(audio_chunk, dtype=np.float32)

                if audio_chunk.ndim > 1:
                    audio_chunk = audio_chunk.reshape(-1)

                peak = np.max(np.abs(audio_chunk)) if audio_chunk.size else 0.0
                if peak > 1.0:
                    audio_chunk = audio_chunk / peak

                audio_chunks.append(audio_chunk.astype(np.float32))
        finally:
            stop_event.set()
            audio_streamer.end()
            thread.join()

        if errors:
            raise errors[0]

        # Concatenate all chunks
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            return full_audio
        return np.array([], dtype=np.float32)

    def _save_audio(self, audio_data):
        """Save audio to temporary WAV file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            import wave

            # Convert float32 audio to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)

            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())

            return temp_file.name

    def run(self):
        """Run TTS generation"""
        try:
            # Load model if not already loaded
            if not self._model_loaded:
                self._load_model()

            self.progress_update.emit(f"Generating TTS for: {self.text[:50]}...")

            # Generate audio
            audio_data = self._generate_audio(self.text)

            if len(audio_data) == 0:
                self.tts_error.emit("Generated audio is empty")
                return

            # Save to file
            audio_file_path = self._save_audio(audio_data)
            duration = len(audio_data) / self.sample_rate

            self.progress_update.emit(f"TTS completed: {duration:.2f} seconds")
            self.tts_completed.emit(audio_file_path)

        except Exception as e:
            error_msg = f"TTS error: {str(e)}"
            print(error_msg)
            self.tts_error.emit(error_msg)


# Singleton model manager for reuse across TTS calls
class VibeVoiceModelManager:
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
        self._tts_instance = None

    def get_tts_instance(self, model_path="microsoft/VibeVoice-Realtime-0.5B", device="cuda"):
        """Get or create TTS instance with model loaded"""
        if self._tts_instance is None:
            self._tts_instance = VibeVoiceTTS("", model_path, device)
            self._tts_instance._load_model()
        return self._tts_instance

    def create_tts_thread(self, text, model_path="microsoft/VibeVoice-Realtime-0.5B", device="cuda"):
        """Create a new TTS thread that reuses the loaded model"""
        if self._tts_instance is None or not self._tts_instance._model_loaded:
            self.get_tts_instance(model_path, device)

        # Create new thread instance but share model components
        thread = VibeVoiceTTS(text, model_path, device)
        thread._processor = self._tts_instance._processor
        thread._model = self._tts_instance._model
        thread._voice_cache = self._tts_instance._voice_cache
        thread._voice_presets = self._tts_instance._voice_presets
        thread._default_voice_key = self._tts_instance._default_voice_key
        thread._model_loaded = True
        return thread
