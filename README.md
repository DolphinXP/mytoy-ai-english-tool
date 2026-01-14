# AI-TTS - Text Correction, Translation & TTS

A Windows application that captures selected text via double Ctrl+C, corrects PDF formatting issues, translates text (Chinese <-> English), and converts English text to speech using VibeVoice.

## Features

- **Double Ctrl+C Capture**: Press Ctrl+C twice within 1 second to capture selected text from any application
- **AI Text Correction**: Fixes common PDF copying issues like word breaks, line breaks, and OCR errors
- **AI Translation**: Translates Chinese to English and English to Chinese
- **Quick Dictionary**: Contextual dictionary-style translations with pronunciation guides (select text and use "Translate to Dictionary")
- **VibeVoice TTS**: High-quality text-to-speech for English text using Microsoft's VibeVoice model
  - **Local TTS**: Run VibeVoice model locally on CPU/GPU
  - **Remote TTS**: Connect to remote TTS server via WebSocket for streaming audio
  - **Streaming Audio**: Real-time audio playback with automatic resume from streaming position when file is ready
  - **Position-aware Playback**: Seamlessly resume playback from where streaming ended

## Requirements

```bash
pip install PySide6 pynput pygame win32clipboard openai httpx torch numpy pyaudio markdown websocket-client
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `PySide6` - GUI framework
- `pynput` - Global hotkey detection
- `pygame` - Audio playback
- `openai` - AI API client (supports DeepSeek, OpenAI, etc.)
- `pyaudio` - Real-time streaming audio playback
- `markdown` - Dictionary rendering
- `websocket-client` - Remote TTS server connection

## Usage

### Main Workflow (Double Ctrl+C)

1. Run the application:
```bash
python main.py
```

2. On startup, select your TTS server preference (Local or Remote)

3. The application will minimize to system tray

4. Select text anywhere (browser, PDF reader, document, etc.)

5. Press **Ctrl+C** to copy the text

6. Press **Ctrl+C** again within 1 second to trigger processing

7. A popup window will appear showing:
   - Original Text
   - AI Corrected Text (fixes PDF formatting)
   - Translated Text
   - English Text (for TTS)
   - Quick Dictionary section (for contextual translations)
   - Audio playback controls with streaming progress

8. The English audio will play automatically (streaming starts immediately, switches to file when ready)

### Quick Dictionary Workflow

1. Select any word or phrase in the popup window

2. Right-click to open context menu

3. Click **"Translate to Dictionary"**

4. A dictionary-style translation will appear with:
   - Contextual definitions
   - Pronunciation guides
   - Example sentences
   - Rich markdown formatting

### System Tray Features

Right-click the system tray icon to access:
- **Change TTS Server**: Switch between local and remote TTS
- **Preload TTS Model**: Load the model before first use (local TTS only)
- **Show Current Clipboard**: View current clipboard content
- **Test API Connectivity**: Test your API configuration
- **Exit**: Close the application

### Audio Playback Features

- **Streaming + File Playback**: Audio starts playing immediately via streaming, then seamlessly switches to the complete file when ready
- **Position Tracking**: Playback resumes from where streaming ended, not from the beginning
- **Progress Bar**: Shows real-time playback progress for both streaming and file-based audio
- **Playback Controls**: Play, pause, and seek through the audio

## Configuration

### TTS Server Selection

On startup, the application will prompt you to choose between:
- **Local TTS**: Run VibeVoice model locally (requires 4GB+ RAM for CPU, 8GB+ for GPU)
- **Remote TTS**: Connect to a remote TTS server via WebSocket

You can change this later via the system tray menu: **Change TTS Server**

**Remote Server Configuration:**
- Default server: `ws://10.110.31.157:3000/stream`
- Customize server URL when prompted or modify in `main.py`
- Supports voice preset configuration for different audio styles

### API Keys

Edit `TextCorrectionThread.py`, `TranslationThread.py`, and `DictionaryThread.py` to configure your preferred AI API:

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

### VibeVoice Model (Local TTS)

The VibeVoice model (`microsoft/VibeVoice-Realtime-0.5B`) will be downloaded automatically on first use.

To use a different device, modify `main.py`:
```python
device="cpu"  # or "cuda", "mps"
```

### SSL Certificate Handling

If you encounter SSL certificate errors with HTTPS APIs, you can disable SSL verification (use with caution):

Edit the relevant thread file (e.g., `TextCorrectionThread.py`):
```python
import httpx
client = httpx.Client(verify=False)  # Disable SSL verification
```

Or set environment variable:
```bash
set SSL_CERT_FILE=
```

## File Structure

```
AI-TTS/
├── main.py                      # Main application with TTS server selection
├── ClipboardCapture.py          # Clipboard access
├── GlobalShortcutHandler.py     # Double Ctrl+C detection
├── TextCorrectionThread.py      # AI text correction
├── TranslationThread.py         # AI translation
├── DictionaryThread.py          # Quick dictionary-style translation
├── VibeVoiceTTS.py              # Local VibeVoice TTS integration
├── VibeVoiceTTSRemote.py        # Remote TTS client via WebSocket
├── PopupWindow.py               # Popup UI with dictionary section
├── test_deepseek.py             # API connectivity testing utility
└── VibeVoice/                   # VibeVoice submodule
```

## Troubleshooting

### Model Loading Issues

If you encounter issues loading the VibeVoice model:
1. Ensure you have enough RAM/VRAM (at least 4GB for CPU, 8GB for GPU)
2. Try using CPU mode: change `device="cuda"` to `device="cpu"`
3. Preload the model via system tray menu before first use
4. Consider using Remote TTS mode if local resources are insufficient

### CUDA Out of Memory

If you get CUDA OOM errors:
1. Reduce batch size in VibeVoiceTTS.py
2. Use CPU mode instead
3. Close other GPU-intensive applications
4. Switch to Remote TTS mode

### Clipboard Not Working

If clipboard capture doesn't work:
1. Run the application as Administrator
2. Check if the application has proper permissions
3. Test with the "Show Current Clipboard" option in system tray

### SSL Certificate Errors

If you encounter SSL certificate errors with HTTPS APIs:
1. Run the connectivity test: Use "Test API Connectivity" from system tray
2. Temporarily disable SSL verification (see Configuration section above)
3. Check your system's certificate store
4. Update your root certificates

### WebSocket Connection Issues (Remote TTS)

If remote TTS server connection fails:
1. Verify the server URL is correct and accessible
2. Check if the server is running: `telnet 10.110.31.157 3000`
3. Ensure no firewall is blocking WebSocket connections
4. Try switching to Local TTS mode
5. Check server logs for errors

### Streaming Audio Problems

If streaming audio doesn't work properly:
1. Ensure PyAudio is installed correctly: `pip install pyaudio`
2. Check if your audio device is working
3. Verify the remote TTS server supports streaming
4. Try non-streaming mode if available
5. Check the "Show Current Clipboard" diagnostic output

### API Connectivity Issues

If AI API calls fail:
1. Test your API key using the "Test API Connectivity" option
2. Verify your API key has sufficient credits/quota
3. Check your internet connection
4. Try different API providers (DeepSeek, OpenAI, etc.)
5. Check proxy settings if behind a corporate firewall

### Dictionary Not Working

If the Quick Dictionary feature fails:
1. Check that DictionaryThread.py has valid API configuration
2. Ensure the API supports streaming responses
3. Verify text selection is working properly
4. Check console output for error messages

### Audio Playback Issues

If audio playback has problems:
1. Ensure pygame is initialized properly
2. Check if temporary WAV files are being created
3. Verify audio device is not in use by another application
4. Try restarting the application
5. Check that streaming position tracking is working correctly

## License

This project uses VibeVoice by Microsoft. Please refer to the VibeVoice license for usage terms.
