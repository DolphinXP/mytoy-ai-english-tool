# Quick Translation App - Development Plan

## Overview
A lightweight, always-accessible translation tool that lives in the system tray and provides instant English-to-Chinese translation via a global hotkey.

## User Preferences (Confirmed)
- **Default AI Service**: DeepSeek (mimo-v2-flash) - Cloud-based, fast response
- **UI Style**: Semi-transparent overlay - Glass-like effect, very modern
- **Translation Display**: Streaming - Show partial results as they arrive (more responsive)
- **Auto-copy**: Yes - Auto-copy translation to clipboard for easy pasting
- **History**: Yes - Include basic history (last 10-20 translations) in MVP
- **Hotkey Customization**: Yes - Allow hotkey customization in settings
- **Add multiple language support (not just English-Chinese)**: Future enhancement, not in MVP

## Core Features

### 1. System Tray Integration
- App starts minimized to system tray
- Tray icon with right-click context menu
- Menu options:
  - Select AI Service (DeepSeek, Ollama, etc.)
  - Settings (API configuration)
  - About
  - Exit

### 2. Global Hotkey (Ctrl+Alt+Q)
- Registers system-wide hotkey using `pynput` library
- When triggered:
  - Shows centered input box (topmost window)
  - Input box has clean, minimal design
  - Auto-focuses for immediate typing

### 3. Translation Input Box
- Centered on screen
- Always on top (topmost)
- Clean, modern UI with PySide6
- Placeholder text: "Enter English text to translate..."
- Press Enter to translate
- Press Escape to hide

### 4. Result Panel
- Rolls down from input box after translation completes
- Displays:
  - Original English text
  - Chinese translation
- Smooth animation (roll down/up)
- Rolls up when:
  - User clicks input box for new input
  - New hotkey is pressed
  - User clicks outside panel

### 5. AI Service Integration
- Reuse existing translation infrastructure from parent project
- Support multiple AI providers:
  - DeepSeek (default)
  - Ollama (local)
  - Extensible for others
- Configuration via JSON file
- Streaming response support for real-time feedback

### 6. Text-to-Speech (TTS)
- Add TTS button in result panel
- Speak original English text
- Speak Chinese translation
- Use system TTS or cloud TTS service
- Adjustable speech rate and volume

## Technical Architecture

### File Structure
```
QuickTranslate/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── requirements.txt       # Dependencies
├── README.md             # Documentation
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

### Key Components

#### 1. `main.py` - Entry Point
- Initialize QApplication
- Create and run main app
- Handle application lifecycle

#### 2. `core/app.py` - Main Application
- Manages application state
- Coordinates between components
- Handles hotkey triggers
- Manages popup lifecycle

#### 3. `core/hotkey_manager.py` - Global Hotkey
- Uses `pynput.keyboard.GlobalHotKeys`
- Registers Ctrl+Alt+Q combination (customizable)
- Emits signal when hotkey pressed
- Includes health monitoring thread
- Supports hotkey re-registration on change

#### 4. `core/translation_service.py` - AI Translation
- Extends `BaseAPIThread` pattern from parent project
- Supports streaming responses
- Handles multiple AI providers
- Error handling and retry logic

#### 5. `ui/tray_icon.py` - System Tray
- Uses `QSystemTrayIcon`
- Context menu for service selection
- Tooltip with current status
- Icon state indicators (idle/translating)

#### 6. `ui/input_popup.py` - Input Box
- `QWidget` with `Qt.WindowStaysOnTopHint`
- Centered on primary screen
- Semi-transparent overlay design
- Auto-focus on show
- Enter to submit, Escape to hide
- Blur effect for background

#### 7. `ui/result_panel.py` - Result Display
- Animated panel below input box
- Shows original + translation
- Smooth roll down/up animation
- Auto-hide on outside click
- Auto-copy translation to clipboard
- Shows "Copied" indicator
- TTS buttons for English and Chinese

#### 8. `core/tts_service.py` - Text-to-Speech
- Speak English text
- Speak Chinese text
- Use system TTS (pyttsx3) or cloud TTS
- Adjustable speech rate and volume
- Stop/pause functionality

#### 9. `core/history_manager.py` - History Management
- Stores last 10-20 translations
- JSON file storage
- Quick access from system tray menu
- Search/filter history

#### 9. `ui/history_panel.py` - History Viewer
- Shows translation history
- Click to re-translate or copy
- Clear history option
- Search functionality

#### 10. `ui/settings_dialog.py` - Settings
- Hotkey customization
- AI service selection
- UI preferences (opacity, theme)
- API configuration

## UI/UX Design

### Input Box Design (Semi-transparent Overlay)
```
┌─────────────────────────────────────┐
│  🔤 Quick Translation               │
├─────────────────────────────────────┤
│  [Enter English text to translate]  │
│                                     │
└─────────────────────────────────────┘
```

### Result Panel Design (After Translation - Rolls Down)
```
┌─────────────────────────────────────┐
│  🔤 Quick Translation               │
├─────────────────────────────────────┤
│  [Enter English text to translate]  │
├─────────────────────────────────────┤
│  Original:                          │
│  "Hello, how are you?"              │
│  [🔊 Speak]                         │
│                                     │
│  Translation:                       │
│  "你好，你好吗？"                    │
│  [🔊 Speak]                         │
│                                     │
│  [📋 Copied to clipboard]           │
└─────────────────────────────────────┘
```

### Visual Style (Semi-transparent Overlay)
- Dark theme with glass-like effect
- Semi-transparent background (opacity: 0.85-0.90)
- Rounded corners (12px radius)
- Subtle blur effect behind panel
- Soft shadow for depth
- Font: System default, clear and readable
- Smooth fade-in animation

## Dependencies

### Required Packages
```
PySide6>=6.5.0
pynput>=1.7.6
httpx>=0.24.0
openai>=1.0.0
pyttsx3>=2.90
```

### Reused from Parent Project
- `services/api/base_api_thread.py` - Base API thread pattern
- `utils/config.py` - Configuration management
- Translation system prompts and logic

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create project structure
2. Set up configuration system
3. Implement hotkey manager
4. Create basic app skeleton

### Phase 2: UI Components
1. Implement system tray icon
2. Create input popup window
3. Create result panel
4. Add animations

### Phase 3: Translation Service
1. Integrate AI translation service
2. Add streaming support
3. Implement error handling
4. Add service selection

### Phase 4: Integration & Polish
1. Connect all components
2. Add settings management
3. Polish UI/UX
4. Testing and bug fixes

## Configuration

### config.json Structure
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
  "ui": {
    "theme": "dark",
    "opacity": 0.95,
    "animation_duration": 300
  }
}
```

## Key Technical Decisions

### 1. Global Hotkey Implementation
**Choice**: `pynput.keyboard.GlobalHotKeys`
**Reason**: 
- Cross-platform support
- Reliable detection
- Already used in parent project
- No admin privileges required

### 2. UI Framework
**Choice**: PySide6 (Qt for Python)
**Reason**:
- Consistent with parent project
- Rich widget set
- Good animation support
- System tray integration built-in

### 3. Translation Service
**Choice**: Reuse parent project's `BaseAPIThread` pattern
**Reason**:
- Proven, working implementation
- Streaming support
- Error handling
- Multiple provider support

### 4. Animation
**Choice**: `QPropertyAnimation` with `QParallelAnimationGroup`
**Reason**:
- Native Qt animation system
- Smooth, hardware-accelerated
- Easy to control timing and easing

## Potential Challenges & Solutions

### Challenge 1: Hotkey Conflicts
**Solution**: 
- Allow user to customize hotkey in settings
- Check for conflicts on registration
- Provide fallback hotkey options

### Challenge 2: Multi-Monitor Support
**Solution**:
- Detect active monitor
- Center popup on active screen
- Remember last position per monitor

### Challenge 3: Translation Latency
**Solution**:
- Show loading indicator
- Stream partial results
- Cache recent translations

### Challenge 4: API Key Security
**Solution**:
- Store in user config directory
- Use environment variables as fallback
- Never log API keys

## Testing Strategy

### Unit Tests
- Hotkey registration/unregistration
- Translation service mocking
- Configuration loading/saving

### Integration Tests
- Full translation workflow
- System tray interactions
- Animation sequences

### Manual Testing
- Different screen resolutions
- Multiple monitors
- Various AI services
- Network conditions

## Future Enhancements (Post-MVP)

1. **Multiple Languages**: Support more language pairs
2. **Custom Prompts**: Allow custom translation prompts
3. **Keyboard Shortcuts**: Additional shortcuts for common actions
4. **Themes**: Light/dark theme toggle
5. **Export**: Export history to file
6. **Cloud Sync**: Sync history across devices
7. **Plugin System**: Support for custom AI providers
8. **Cloud TTS**: Support for cloud-based TTS services (Google, Azure, etc.)

## Success Criteria

1. ✅ App starts minimized to system tray
2. ✅ Ctrl+Alt+Q shows input box centered on screen
3. ✅ Input box is always on top
4. ✅ Translation completes within 5 seconds (network dependent)
5. ✅ Result panel animates smoothly
6. ✅ Multiple AI services work correctly
7. ✅ App consumes minimal resources when idle
8. ✅ Clean exit from system tray menu

## Next Steps

1. ✅ Review this plan with user
2. ✅ Answer clarification questions
3. ✅ Finalize design decisions
4. Switch to Code mode for implementation
5. Begin Phase 1: Core Infrastructure
