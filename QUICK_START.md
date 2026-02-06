# Quick Start Guide - Refactored AI-TTS-VibeVoice

## Testing the Refactored Code

### Step 1: Verify Structure

Check that all new packages were created:

```bash
# Should show 33 new Python files
find core ui services utils -name "*.py" | wc -l
```

### Step 2: Test Import Structure

Create a test script to verify imports work:

```python
# test_imports.py
print("Testing imports...")

try:
    from core.app import MainApp
    print("✓ core.app")

    from core.text_processor import TextProcessor
    print("✓ core.text_processor")

    from core.thread_manager import ThreadManager
    print("✓ core.thread_manager")

    from services.api.base_api_thread import BaseAPIThread
    print("✓ services.api.base_api_thread")

    from services.api.text_correction import TextCorrectionThread
    print("✓ services.api.text_correction")

    from services.api.translation import TranslationThread
    print("✓ services.api.translation")

    from services.api.dictionary import DictionaryThread
    print("✓ services.api.dictionary")

    from services.tts.remote_tts import RemoteTTSThread, RemoteTTSManager
    print("✓ services.tts.remote_tts")

    from services.audio.streaming_player import StreamingAudioPlayer
    print("✓ services.audio.streaming_player")

    from services.audio.file_player import FileAudioPlayer
    print("✓ services.audio.file_player")

    from services.clipboard.clipboard_service import ClipboardService
    print("✓ services.clipboard.clipboard_service")

    from ui.popup_window import PopupWindow
    print("✓ ui.popup_window")

    from ui.widgets.translatable_text_edit import TranslatableTextEdit
    print("✓ ui.widgets.translatable_text_edit")

    from ui.widgets.text_section import TextSection
    print("✓ ui.widgets.text_section")

    from ui.widgets.audio_controls import AudioControls
    print("✓ ui.widgets.audio_controls")

    from ui.dialogs.tts_server_dialog import TTSServerSelectionDialog
    print("✓ ui.dialogs.tts_server_dialog")

    from ui.styles.theme import Theme
    print("✓ ui.styles.theme")

    from ui.styles.icons import get_icon_manager
    print("✓ ui.styles.icons")

    from utils.config import get_api_config
    print("✓ utils.config")

    from utils.shortcuts import GlobalShortcutHandler
    print("✓ utils.shortcuts")

    from utils.helpers import clean_text, is_english
    print("✓ utils.helpers")

    print("\n✅ All imports successful!")

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    import traceback
    traceback.print_exc()
```

Run the test:
```bash
python test_imports.py
```

### Step 3: Run the Refactored Application

```bash
python main_new.py
```

### Step 4: Test Core Functionality

1. **System Tray**: Check that the tray icon appears
2. **TTS Server Dialog**: Should appear on startup
3. **Test Double Ctrl+C**: Use the tray menu option
4. **Copy Text**: Copy some text and press Ctrl+C twice quickly
5. **Verify UI**: Check that the modern UI displays correctly
6. **Test Audio**: Verify audio playback works
7. **Test Dictionary**: Select text and right-click to translate
8. **Test Edit/Retranslate**: Edit corrected text and retranslate

### Step 5: Compare with Original

Run the original version side-by-side:

```bash
# Terminal 1
python main.py

# Terminal 2
python main_new.py
```

Verify both behave identically.

## Common Issues and Solutions

### Issue: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'core'`

**Solution**: Make sure you're running from the project root directory:
```bash
cd c:\XL\Git\AI-TTS-VibeVoice
python main_new.py
```

### Issue: Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'PySide6'`

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Qt Application Errors

**Problem**: `QApplication: invalid style override passed`

**Solution**: This is usually harmless. The application should still work.

### Issue: Audio Not Playing

**Problem**: No audio output

**Solution**:
1. Check that pyaudio is installed: `pip install pyaudio`
2. Check that pygame is installed: `pip install pygame`
3. Verify audio device is working
4. Check TTS server is accessible (for remote mode)

### Issue: Window Not Appearing

**Problem**: Application starts but no window shows

**Solution**:
1. Check system tray for the icon
2. Use "Test Double Ctrl+C" from tray menu
3. Check console for error messages

## Rollback to Original

If you encounter issues, you can always use the original code:

```bash
python main.py
```

All original files are unchanged and fully functional.

## Getting Help

1. Check console output for error messages
2. Review [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)
3. Compare behavior with original `main.py`
4. Check that all dependencies are installed

## Success Criteria

The refactored code is working correctly if:

- ✅ Application starts without errors
- ✅ System tray icon appears
- ✅ TTS server dialog shows on startup
- ✅ Double Ctrl+C triggers text processing
- ✅ Text correction works with streaming
- ✅ Translation works with streaming
- ✅ Audio generation and playback work
- ✅ Dictionary lookup works
- ✅ Edit and retranslate work
- ✅ Modern UI displays correctly
- ✅ All buttons and menus work
- ✅ Window position persists
- ✅ Clean shutdown on exit

## Next Steps After Testing

Once testing is complete and successful:

1. **Rename files** (optional):
   ```bash
   mv main.py main_old.py
   mv main_new.py main.py
   ```

2. **Update documentation**: Document any changes or improvements

3. **Add tests**: Create unit tests for new components

4. **Optimize**: Profile and optimize any bottlenecks

5. **Extend**: Add new features using the modular architecture

---

**Happy Testing!** 🚀
