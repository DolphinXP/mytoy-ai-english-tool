# PDFReader - 读书笔记 Application

## Project Overview

A PDF viewer application with integrated reading notes functionality, built as a child project of AI-TTS. The app enables users to view PDFs, select text, translate/explain content via AI, and maintain persistent annotations.

## Technical Stack

- **Language**: Python 3.x
- **Conda Environment**: vibevoice
- **UI Framework**: PySide6 (inherited from parent)
- **PDF Rendering**: PyMuPDF (fitz) - fast, reliable PDF rendering
- **Data Storage**: SQLite for annotations persistence
- **API Integration**: Reuse parent's API services (translation, TTS, dictionary, explain)

## Code Quality Constraints

- **Maximum LOC per script: 400 lines** - Each Python file must not exceed 400 lines of code (excluding blank lines and comments). Split larger modules into logical sub-modules.
- Follow parent project's coding style and patterns
- Use type hints for all function signatures
- Docstrings required for all public classes and methods

## Architecture

### Directory Structure

```
PDFReader/
├── main.py                      # Entry point (~50 LOC)
├── core/
│   ├── __init__.py
│   ├── app.py                   # Main application class (~200 LOC)
│   └── annotation_manager.py    # Annotation CRUD operations (~150 LOC)
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # Main window layout (~250 LOC)
│   ├── pdf_view.py              # PDF rendering widget (~300 LOC)
│   ├── result_panel.py          # Translation/explain results (~200 LOC)
│   ├── context_menu.py          # Popup menu for text selection (~100 LOC)
│   └── annotation_navigator.py  # Navigate highlighted annotations (~150 LOC)
├── models/
│   ├── __init__.py
│   └── annotation.py            # Annotation data model (~80 LOC)
├── services/
│   ├── __init__.py
│   └── pdf_service.py           # PDF loading/text extraction (~150 LOC)
├── db/
│   ├── __init__.py
│   └── database.py              # SQLite operations (~200 LOC)
└── utils/
    ├── __init__.py
    └── helpers.py               # Utility functions (~100 LOC)
```

### Component Responsibilities

#### 1. PDF View (`ui/pdf_view.py`)
- Render PDF pages using PyMuPDF
- Handle text selection with mouse events
- Display highlight overlays for annotated text
- Emit signals when text is selected
- Support zoom and page navigation

#### 2. Context Menu (`ui/context_menu.py`)
- Show popup menu on text selection
- Options: "Translate", "AI Explain"
- Position near selected text
- Trigger corresponding API calls

#### 3. Result Panel (`ui/result_panel.py`)
- Inherit/adapt from parent's `popup_window.py`
- Display translation results with streaming
- Show AI explanations
- Include action buttons: Copy, Edit, Retranslate, Explain, Play TTS, Dictionary
- Exclude "Exit Program" button (not needed here)
- Add "Regenerate" button for updating results

#### 4. Annotation Manager (`core/annotation_manager.py`)
- Create annotations when translation/explain completes
- Store: page number, text coordinates, selected text, results, timestamp
- Update annotations on regenerate
- Query annotations by page or document

#### 5. Annotation Navigator (`ui/annotation_navigator.py`)
- List all annotations in current document
- Click to jump to annotated text
- Show preview of translation/explanation
- Filter by page or search

### Data Model

```python
@dataclass
class Annotation:
    id: str                    # UUID
    document_path: str         # PDF file path
    page_number: int           # 0-indexed page
    selected_text: str         # Original selected text
    text_rect: tuple           # (x0, y0, x1, y1) coordinates
    corrected_text: str        # AI corrected text
    translated_text: str       # Translation result
    explanation: str           # AI explanation (optional)
    tts_audio_path: str        # Path to generated audio (optional)
    created_at: datetime
    updated_at: datetime
```

### Database Schema

```sql
CREATE TABLE annotations (
    id TEXT PRIMARY KEY,
    document_path TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    selected_text TEXT NOT NULL,
    text_rect TEXT NOT NULL,      -- JSON: [x0, y0, x1, y1]
    corrected_text TEXT,
    translated_text TEXT,
    explanation TEXT,
    tts_audio_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_document_page ON annotations(document_path, page_number);
```

### Integration with Parent Project

Reuse these modules from parent AI-TTS:
- `services/api/translation.py` - TranslationThread
- `services/api/text_correction.py` - TextCorrectionThread
- `services/api/explain.py` - ExplainThread
- `services/api/dictionary.py` - DictionaryThread
- `services/tts/remote_tts.py` - RemoteTTSManager
- `core/text_processor.py` - TextProcessor pipeline
- `core/thread_manager.py` - Thread lifecycle management
- `ui/styles/theme.py` - UI theming
- `ui/mixins/` - Audio, Dictionary, Retranslate mixins

Import path setup in `main.py`:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add AI-TTS root
```

### User Flow

1. **Open PDF**: File → Open or drag-drop PDF file
2. **Select Text**: Click and drag to select text in PDF view
3. **Context Menu**: Popup appears with "Translate" and "AI Explain" options
4. **Process**:
   - Translate: correction → translation → TTS (same as parent)
   - Explain: AI generates contextual explanation
5. **Result Panel**: Shows results with all parent popup_window features
6. **Highlight**: Selected text gets highlighted in PDF view
7. **Persist**: Annotation saved to SQLite database
8. **Navigate**: Use annotation navigator to revisit previous annotations
9. **Regenerate**: Update annotation with new AI results

### Key Implementation Notes

1. **PDF Text Selection**: Use `fitz.Page.get_text("dict")` to get text blocks with coordinates, then map mouse selection to text spans.

2. **Highlight Rendering**: Draw semi-transparent rectangles over annotated regions using QPainter on the PDF view.

3. **Result Panel Adaptation**:
   - Remove exit_app_btn and related logic
   - Add regenerate_btn that re-triggers the processing pipeline
   - Connect to annotation_manager for persistence

4. **Streaming Results**: Same pattern as parent - connect to chunk signals for real-time display.

5. **TTS Integration**: Reuse parent's RemoteTTSManager and AudioMixin for playback.

## Development Phases

### Phase 1: Core PDF Viewer
- PDF loading and rendering
- Page navigation (prev/next, go to page)
- Zoom controls
- Basic text selection

### Phase 2: AI Integration
- Context menu on selection
- Translation pipeline integration
- Result panel with streaming display
- TTS playback

### Phase 3: Annotation System
- SQLite database setup
- Annotation creation on translation complete
- Highlight rendering on PDF
- Annotation navigator panel

### Phase 4: Polish
- Regenerate functionality
- Search within annotations
- Export annotations
- UI refinements

## Dependencies

```
# Additional dependencies (parent deps assumed installed)
PyMuPDF>=1.23.0
```

## Running the Application

```bash
conda activate vibevoice
cd PDFReader
python main.py
```
