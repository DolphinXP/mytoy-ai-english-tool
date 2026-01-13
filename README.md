# AI-TTS - Text Correction, Translation & TTS

A Windows application that captures selected text via double Ctrl+C, corrects PDF formatting issues, translates text (Chinese <-> English), and converts English text to speech using VibeVoice.

## Features

- **Double Ctrl+C Capture**: Press Ctrl+C twice within 1 second to capture selected text from any application
- **AI Text Correction**: Fixes common PDF copying issues like word breaks, line breaks, and OCR errors
- **AI Translation**: Translates Chinese to English and English to Chinese
- **VibeVoice TTS**: High-quality text-to-speech for English text using Microsoft's VibeVoice model

## Requirements

```bash
pip install PySide6 pynput pygame win32clipboard openai httpx torch numpy
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python main.py
```

2. The application will minimize to system tray

3. Select text anywhere (browser, PDF reader, document, etc.)

4. Press **Ctrl+C** to copy the text

5. Press **Ctrl+C** again within 1 second to trigger processing

6. A popup window will appear showing:
   - Original Text
   - AI Corrected Text (fixes PDF formatting)
   - Translated Text
   - English Text (for TTS)
   - Audio playback controls

7. The English audio will play automatically

## Configuration

### API Keys

Edit `TextCorrectionThread.py` and `TranslationThread.py` to configure your preferred AI API:

```python
default_configs = {
    'deepseek': {
        'endpoint': "https://api.deepseek.com",
        'key': "YOUR_API_KEY",
        'model': "deepseek-chat",
        'proxy': None
    },
    # ... other configs
}
```

### VibeVoice Model

The VibeVoice model (`microsoft/VibeVoice-Realtime-0.5B`) will be downloaded automatically on first use.

To use a different device, modify `main.py`:
```python
device="cpu"  # or "cuda", "mps"
```

## File Structure

```
AI-TTS/
├── main.py                      # Main application
├── ClipboardCapture.py          # Clipboard access
├── GlobalShortcutHandler.py     # Double Ctrl+C detection
├── TextCorrectionThread.py      # AI text correction
├── TranslationThread.py         # AI translation
├── VibeVoiceTTS.py              # VibeVoice TTS integration
├── PopupWindow.py               # Popup UI
└── VibeVoice/                   # VibeVoice submodule
```

## Troubleshooting

### Model Loading Issues

If you encounter issues loading the VibeVoice model:
1. Ensure you have enough RAM/VRAM (at least 4GB for CPU, 8GB for GPU)
2. Try using CPU mode: change `device="cuda"` to `device="cpu"`
3. Preload the model via system tray menu before first use

### CUDA Out of Memory

If you get CUDA OOM errors:
1. Reduce batch size in VibeVoiceTTS.py
2. Use CPU mode instead
3. Close other GPU-intensive applications

### Clipboard Not Working

If clipboard capture doesn't work:
1. Run the application as Administrator
2. Check if the application has proper permissions
3. Test with the "Show Current Clipboard" option in system tray

## License

This project uses VibeVoice by Microsoft. Please refer to the VibeVoice license for usage terms.
