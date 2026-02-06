# Testing Checklist

## Before Testing

- [ ] Ensure you're in the project root directory: `c:\XL\Git\AI-TTS-VibeVoice`
- [ ] All dependencies are installed: `pip install -r requirements.txt`
- [ ] Dark system theme is enabled (to verify dark theme support)

## Quick Import Test

Run this to verify all imports work:

```bash
python -c "from core.app import MainApp; from ui.popup_window import PopupWindow; print('✅ Imports OK')"
```

## Launch Test

```bash
python main_new.py
```

## Visual Checks (Dark Theme)

- [ ] **Window appears** - Main popup window shows up
- [ ] **Text is readable** - All text is white/light colored on dark backgrounds
- [ ] **Borders are visible** - All text boxes have visible borders
- [ ] **Buttons are clear** - Button text is readable, states are visible
- [ ] **Labels are readable** - Section titles and labels are visible
- [ ] **Status text is visible** - Status messages at bottom are readable
- [ ] **Menu items readable** - Right-click menus have visible text
- [ ] **Progress bar visible** - Progress bar and percentage are visible

## Functional Checks

- [ ] **System tray icon** - Icon appears in system tray
- [ ] **TTS server dialog** - Dialog shows on startup
- [ ] **Test button** - "Test Double Ctrl+C" from tray menu works
- [ ] **Text correction** - AI corrects text with streaming
- [ ] **Translation** - AI translates text with streaming
- [ ] **Copy buttons** - All copy buttons work
- [ ] **Edit/Restore** - Edit button toggles correctly
- [ ] **Retranslate** - Retranslate button works
- [ ] **Dictionary** - Right-click translate works
- [ ] **Audio playback** - Audio plays (if TTS server is available)
- [ ] **Window position** - Position saves when moved
- [ ] **Auto-close timer** - Countdown shows and works
- [ ] **Exit button** - Exit Program button works

## Comparison Test

Run both versions side-by-side:

```bash
# Terminal 1
python main.py

# Terminal 2
python main_new.py
```

- [ ] Both versions launch successfully
- [ ] New version has better visibility in dark theme
- [ ] Both versions have same functionality
- [ ] New version has modern UI design

## Known Issues to Check

- [ ] No import errors on startup
- [ ] No Qt warnings (or only harmless style warnings)
- [ ] Threads clean up properly on exit
- [ ] No memory leaks during extended use
- [ ] Audio resources release properly

## If Issues Occur

1. **Import errors**: Check you're in the project root directory
2. **Text not visible**: Verify theme.py changes were applied
3. **Missing dependencies**: Run `pip install -r requirements.txt`
4. **Qt errors**: Usually harmless, check if app still works
5. **Audio issues**: Check TTS server is accessible

## Success Criteria

✅ All visual elements are clearly visible in dark theme
✅ All functionality works as expected
✅ No critical errors in console
✅ Application exits cleanly
✅ Better than original in terms of code organization and UI

## Rollback if Needed

If you encounter critical issues, you can always use the original:

```bash
python main.py
```

All original files are unchanged and fully functional.

---

**Ready to test!** Run `python main_new.py` and go through this checklist.
