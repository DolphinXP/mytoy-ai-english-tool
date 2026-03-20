# Quick Translation

A lightweight, always-accessible translation tool that lives in the system tray and provides instant English-to-Chinese translation via a global hotkey.

## Features

- **Global Hotkey**: Press `Ctrl+Alt+Q` to show the translation window
- **System Tray**: Runs minimized in the system tray for easy access
- **AI Translation**: Uses DeepSeek or Ollama for high-quality translations
- **Streaming Results**: See translations appear in real-time
- **Text-to-Speech**: Listen to original and translated text
- **Translation History**: Save and access recent translations
- **Auto-copy**: Translations are automatically copied to clipboard
- **Customizable**: Configure hotkey, AI service, and UI preferences

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

- PySide6 >= 6.5.0 (UI framework)
- pynput >= 1.7.6 (Global hotkey support)
- httpx >= 0.24.0 (HTTP client)
- openai >= 1.0.0 (AI API client)
- pyttsx3 >= 2.90 (Text-to-speech)

## Usage

### Starting the Application

```bash
python main.py
```

The application will start minimized in the system tray.

### Using the Translation Feature

1. Press `Ctrl+Alt+Q` to show the translation window
2. Enter English text to translate
3. Press Enter or click "Translate"
4. View the Chinese translation below the input box
5. Translation is automatically copied to clipboard

### System Tray Menu

Right-click the system tray icon to access:

- **Show Translation Window**: Open the translation input
- **Translation History**: View recent translations
- **AI Service**: Switch between DeepSeek and Ollama
- **Settings**: Configure application preferences
- **Exit**: Close the application

### Text-to-Speech

Click the 🔊 button next to original or translation text to hear it spoken aloud.

## Configuration

The application stores configuration in `config.json` in the application directory.

### Default Configuration

```json
{
  "current_service": "deepseek",
  "services": {
    "deepseek": {
      "endpoint": "https://api.xiaomimimo.com/v1",
      "key": "sk-xxx",
      "model": "mimo-v2-flash",
      "timeout": 60.0
    },
    "ollama": {
      "endpoint": "http://localhost:11434/v1",
      "key": "ollama",
      "model": "qwen3.5:9b",
      "timeout": 120.0
    }
  },
  "hotkey": "<ctrl>+<alt>+q",
  "ui": {
    "theme": "dark",
    "opacity": 0.90,
    "animation_duration": 300
  },
  "tts": {
    "enabled": true,
    "rate": 150,
    "volume": 0.8
  },
  "history": {
    "max_items": 20,
    "auto_save": true
  }
}
```

### Settings

Access settings via the system tray menu:

- **Hotkey**: Customize the global hotkey combination
- **AI Service**: Choose between DeepSeek and Ollama
- **Window Opacity**: Adjust transparency (0.5 - 1.0)
- **Animation Duration**: Adjust animation speed (100 - 1000 ms)
- **Speech Rate**: Adjust TTS speed (50 - 300)
- **Volume**: Adjust TTS volume (0.0 - 1.0)
- **Max History Items**: Number of translations to keep (5 - 100)

## Project Structure

```
QuickTranslate/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── requirements.txt       # Dependencies
├── README.md             # This file
├── core/
│   ├── __init__.py
│   ├── app.py            # Main application class
│   ├── hotkey_manager.py # Global hotkey handling
│   ├── translation_service.py  # AI translation service
│   ├── history_manager.py # Translation history management
│   └── tts_service.py    # Text-to-speech service
├── ui/
│   ├── __init__.py
│   ├── tray_icon.py      # System tray icon
│   ├── input_popup.py    # Input box popup
│   ├── result_panel.py   # Translation result display
│   ├── history_panel.py  # History viewer panel
│   └── settings_dialog.py # Settings configuration dialog
└── utils/
    ├── __init__.py
    └── helpers.py         # Utility functions
```

## Development

### Architecture

The application follows a modular architecture:

- **Core**: Business logic and services
- **UI**: User interface components
- **Utils**: Helper functions and utilities

### Key Components

1. **QuickTranslateApp**: Main application coordinator
2. **HotkeyManager**: Global hotkey registration and detection
3. **TranslationService**: AI translation using parent project's infrastructure
4. **HistoryManager**: Translation history storage and retrieval
5. **TTSService**: Text-to-speech functionality
6. **TrayIcon**: System tray icon and menu
7. **InputPopup**: Translation input window
8. **ResultPanel**: Translation result display
9. **HistoryPanel**: History viewer
10. **SettingsDialog**: Settings configuration

### Adding New Features

1. Create new module in appropriate directory (core/, ui/, or utils/)
2. Import and integrate in core/app.py
3. Add UI components if needed
4. Update configuration if needed

## Troubleshooting

### Hotkey Not Working

- Ensure no other application is using the same hotkey
- Try customizing the hotkey in settings
- Restart the application

### Translation Errors

- Check your internet connection
- Verify API key is correct
- Try switching to a different AI service

### TTS Not Working

- Ensure pyttsx3 is installed correctly
- Check system audio settings
- Try adjusting volume in settings

## License

This project is part of the AI-TTS project.

## Credits

- Built with PySide6 (Qt for Python)
- Uses pynput for global hotkey support
- Translation powered by DeepSeek and Ollama
