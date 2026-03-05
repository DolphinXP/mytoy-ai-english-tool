"""Main window for PDFReader application."""
import json
import os
import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QApplication, QMenu
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QColor, QAction

from PDFReader.ui.toolbar import ToolbarWidget
from PDFReader.ui.pdf_viewer import PDFViewerWidget
from PDFReader.ui.annotation_panel import AnnotationPanel
from PDFReader.ui.status_bar import StatusBarWidget
from PDFReader.ui.side_panel import SidePanel
from PDFReader.ui.context_menu import TextContextMenu
from PDFReader.core.app import PDFReaderApp
from PDFReader.core.ai_processor import AIProcessor
from PDFReader.models.annotation import Annotation
from core.thread_manager import ThreadManager
from services.audio.file_player import FileAudioPlayer

_parent_dir = str(Path(__file__).parent.parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


DARK_THEME = """
    QMainWindow, QWidget { background-color: #1e1e1e; color: #d4d4d4; }
    QSplitter::handle { background-color: #333333; }
    QMessageBox { background-color: #252526; color: #d4d4d4; }
    QMessageBox QPushButton { background-color: #0e639c; color: #ffffff; border: none; padding: 6px 16px; border-radius: 4px; }
    QMessageBox QPushButton:hover { background-color: #1177bb; }
"""


class MainWindow(QMainWindow):
    """Main application window."""

    # Path for persisting recent document history
    _HISTORY_FILE = os.path.join(
        os.environ.get("APPDATA", str(Path.home())), "PDFReader", "history.json")

    def __init__(self):
        super().__init__()
        self._app = PDFReaderApp()
        self._thread_manager = ThreadManager()
        self._ai_processor = AIProcessor(self._thread_manager, self)
        self._current_selection_rect = None
        self._current_text_rects = []
        self._current_selected_text = ""
        self._annotation_panel_visible = True
        self._annotation_panel_sizes = [980, 420]
        # Track which annotation is currently being processed by AI
        self._processing_annotation_id: Optional[str] = None
        # Recent document history and last-used directory
        self._last_open_dir: str = ""
        self._view_positions: dict = {}  # Maps file path to (page, scroll_x, scroll_y, zoom)
        self._recent_docs: List[str] = self._load_history()
        # Audio player for TTS
        self._audio_player = FileAudioPlayer()
        self._tts_update_timer = QTimer(self)
        self._tts_update_timer.setInterval(200)
        self._tts_update_timer.timeout.connect(self._update_tts_progress)
        self._setup_ui()
        self._setup_file_menu()
        self._setup_shortcuts()
        self._connect_signals()

    def _setup_file_menu(self):
        """Create the File menu and attach it to the toolbar."""
        menu_style = """
            QMenu {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                color: #d4d4d4;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 30px 6px 20px;
            }
            QMenu::item:selected {
                background-color: #0e639c;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3c3c3c;
                margin: 4px 8px;
            }
        """

        self._file_menu = QMenu("File", self)
        self._file_menu.setStyleSheet(menu_style)

        # Open action
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._on_open_file)
        self.addAction(open_action)
        self._file_menu.addAction(open_action)

        self._file_menu.addSeparator()

        # Recent-documents submenu
        self._history_menu = self._file_menu.addMenu("Recent &Documents")
        self._history_menu.setStyleSheet(menu_style)
        self._rebuild_history_menu()
        self._toolbar.set_file_menu(self._file_menu)

    def _rebuild_history_menu(self):
        """Rebuild the history submenu with recent documents."""
        self._history_menu.clear()

        if self._recent_docs:
            for doc_path in self._recent_docs:
                name = Path(doc_path).name
                action = QAction(name, self)
                action.setToolTip(doc_path)
                action.setData(doc_path)
                action.triggered.connect(
                    lambda checked, p=doc_path: self._open_recent_document(p))
                self._history_menu.addAction(action)

            self._history_menu.addSeparator()

        clear_action = QAction("Clear All History", self)
        clear_action.triggered.connect(self._clear_history)
        self._history_menu.addAction(clear_action)

    def _open_recent_document(self, doc_path: str):
        """Open a document from the recent history."""
        if Path(doc_path).exists():
            self._app.open_document(doc_path)
        else:
            QMessageBox.warning(
                self, "File Not Found",
                f"The file no longer exists:\n{doc_path}")
            # Remove from history
            if doc_path in self._recent_docs:
                self._recent_docs.remove(doc_path)
                self._save_history()
                self._rebuild_history_menu()

    def _add_to_history(self, file_path: str):
        """Add a document to the recent history."""
        # Normalize path
        normalized = str(Path(file_path).resolve())
        # Remove if already exists (will re-add at top)
        if normalized in self._recent_docs:
            self._recent_docs.remove(normalized)
        # Add to top
        self._recent_docs.insert(0, normalized)
        # Limit to 20 entries
        self._recent_docs = self._recent_docs[:20]
        self._save_history()
        self._rebuild_history_menu()

    def _clear_history(self):
        """Clear all document history."""
        self._recent_docs.clear()
        self._save_history()
        self._rebuild_history_menu()

    def _load_history(self) -> List[str]:
        """Load document history from disk."""
        try:
            if os.path.exists(self._HISTORY_FILE):
                with open(self._HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # New format with last_dir and view positions
                        self._last_open_dir = data.get("last_dir", "")
                        self._view_positions = data.get("view_positions", {})
                        return data.get("recent", [])
                    elif isinstance(data, list):
                        return data
        except Exception:
            pass
        return []

    def _save_history(self):
        """Save document history to disk."""
        try:
            os.makedirs(os.path.dirname(self._HISTORY_FILE), exist_ok=True)
            data = {
                "recent": self._recent_docs,
                "last_dir": self._last_open_dir,
                "view_positions": getattr(self, '_view_positions', {}),
            }
            with open(self._HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _setup_ui(self):
        self.setWindowTitle("PDF Reader")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)
        self.setStyleSheet(DARK_THEME)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = ToolbarWidget()
        layout.addWidget(self._toolbar)

        # Left side panel (bookmarks only)
        self._side_panel = SidePanel()

        # Splitter for viewer and annotation panel
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setStyleSheet(
            "QSplitter::handle { background-color: #333333; width: 2px; }")

        self._viewer = PDFViewerWidget()
        self._splitter.addWidget(self._viewer)

        self._annotation_panel = AnnotationPanel()
        self._annotation_panel.setMinimumWidth(0)
        self._annotation_panel.setMaximumWidth(500)
        self._splitter.addWidget(self._annotation_panel)

        self._splitter.setSizes([980, 420])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, True)

        # Outer splitter makes the left panel user-resizable
        self._main_splitter = QSplitter(Qt.Horizontal)
        self._main_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #333333; width: 2px; }")
        self._main_splitter.addWidget(self._side_panel)
        self._main_splitter.addWidget(self._splitter)
        self._main_splitter.setSizes([240, 1160])
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.setCollapsible(0, True)
        self._main_splitter.setCollapsible(1, False)

        layout.addWidget(self._main_splitter, 1)

        self._status_bar = StatusBarWidget()
        layout.addWidget(self._status_bar)

        # Context menu for text selection
        self._context_menu = TextContextMenu(self)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Left), self, self._app.previous_page)
        QShortcut(QKeySequence(Qt.Key_Right), self, self._app.next_page)
        QShortcut(QKeySequence(Qt.Key_Home), self, self._app.first_page)
        QShortcut(QKeySequence(Qt.Key_End), self, self._app.last_page)
        QShortcut(QKeySequence(Qt.Key_PageUp), self, self._app.previous_page)
        QShortcut(QKeySequence(Qt.Key_PageDown), self, self._app.next_page)
        QShortcut(QKeySequence.ZoomIn, self, self._app.zoom_in)
        QShortcut(QKeySequence.ZoomOut, self, self._app.zoom_out)
        QShortcut(QKeySequence(Qt.CTRL | Qt.Key_0), self, self._app.reset_zoom)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._clear_selection)

    def _connect_signals(self):
        # Toolbar
        self._toolbar.open_file_clicked.connect(self._on_open_file)
        self._toolbar.first_page_clicked.connect(self._app.first_page)
        self._toolbar.prev_page_clicked.connect(self._app.previous_page)
        self._toolbar.next_page_clicked.connect(self._app.next_page)
        self._toolbar.last_page_clicked.connect(self._app.last_page)
        self._toolbar.page_number_changed.connect(self._app.go_to_page)
        self._toolbar.zoom_in_clicked.connect(self._app.zoom_in)
        self._toolbar.zoom_out_clicked.connect(self._app.zoom_out)
        self._toolbar.zoom_reset_clicked.connect(self._app.reset_zoom)
        self._toolbar.zoom_fit_width_clicked.connect(self._fit_to_width)
        self._toolbar.zoom_fit_window_clicked.connect(self._fit_to_window)
        self._toolbar.zoom_level_changed.connect(self._app.set_zoom)
        self._toolbar.regenerate_clicked.connect(self._on_regenerate)
        self._toolbar.toggle_annotations_clicked.connect(
            self._toggle_annotation_panel)

        # App
        self._app.document_loaded.connect(self._on_document_loaded)
        self._app.document_closed.connect(self._on_document_closed)
        self._app.page_changed.connect(self._on_page_changed)
        self._app.zoom_changed.connect(self._on_zoom_changed)
        self._app.error_occurred.connect(self._on_error)

        # Viewer
        self._viewer.selection_made.connect(self._on_selection_made)
        self._viewer.highlight_clicked.connect(self._on_highlight_clicked)
        self._viewer.page_up_requested.connect(self._app.previous_page)
        self._viewer.page_down_requested.connect(self._app.next_page)
        self._viewer.zoom_in_requested.connect(self._app.zoom_in)
        self._viewer.zoom_out_requested.connect(self._app.zoom_out)

        # Annotation panel
        self._annotation_panel.annotation_selected.connect(
            self._on_annotation_selected)
        self._annotation_panel.annotation_deleted.connect(
            self._on_annotation_delete_requested)

        # Annotation panel detail view actions
        self._annotation_panel.copy_clicked.connect(self._on_copy_result)
        self._annotation_panel.retranslate_clicked.connect(
            self._on_retranslate)
        self._annotation_panel.explain_clicked.connect(self._on_explain)
        self._annotation_panel.tts_clicked.connect(self._on_tts)
        self._annotation_panel.tts_play_clicked.connect(self._on_tts_play)
        self._annotation_panel.tts_stop_clicked.connect(self._on_tts_stop)
        self._annotation_panel.tts_settings_clicked.connect(
            self._on_tts_settings)

        # Annotation manager
        self._app.annotation_manager.annotations_loaded.connect(
            self._on_annotations_loaded)
        self._app.annotation_manager.annotation_created.connect(
            self._on_annotation_created)
        self._app.annotation_manager.annotation_updated.connect(
            self._on_annotation_updated)
        self._app.annotation_manager.annotation_deleted.connect(
            self._on_annotation_deleted)

        # Context menu — Mark action
        self._context_menu.mark_clicked.connect(self._on_mark_selection)

        # Side panel
        self._side_panel.bookmark_clicked.connect(self._app.go_to_page)

        # AI processor signals
        self._ai_processor.correction_chunk.connect(self._on_correction_chunk)
        self._ai_processor.correction_done.connect(self._on_correction_done)
        self._ai_processor.correction_error.connect(self._on_correction_error)
        self._ai_processor.translation_chunk.connect(
            self._on_translation_chunk)
        self._ai_processor.translation_done.connect(self._on_translation_done)
        self._ai_processor.translation_error.connect(
            self._on_translation_error)
        self._ai_processor.explain_chunk.connect(self._on_explain_chunk)
        self._ai_processor.explain_done.connect(self._on_explain_done)
        self._ai_processor.tts_completed.connect(self._on_tts_audio_ready)
        self._ai_processor.tts_error.connect(self._on_tts_error)

    # ─── File / Document ──────────────────────────────────────────────────

    def _on_open_file(self):
        # Determine starting directory
        start_dir = self._last_open_dir
        if not start_dir or not os.path.isdir(start_dir):
            # Fall back to My Documents
            start_dir = str(Path.home() / "Documents")
            if not os.path.isdir(start_dir):
                start_dir = str(Path.home())

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", start_dir, "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            # Remember the directory for next time
            self._last_open_dir = str(Path(file_path).parent)
            self._save_history()
            self._app.open_document(file_path)

    def _on_document_loaded(self, file_path: str):
        self._toolbar.set_page_count(self._app.page_count)
        
        # Normalize file path for consistent lookup
        normalized_path = str(Path(file_path).resolve())
        
        # Restore last view position if available
        if normalized_path in self._view_positions:
            pos_data = self._view_positions[normalized_path]
            last_page = pos_data.get("page", 0)
            last_zoom = pos_data.get("zoom", 1.0)
            last_scroll_x = pos_data.get("scroll_x", 0)
            last_scroll_y = pos_data.get("scroll_y", 0)
            
            # Clamp page to valid range
            last_page = max(0, min(last_page, self._app.page_count - 1))
            
            # Set zoom first
            if last_zoom != self._app.zoom_level:
                self._app.set_zoom(last_zoom)
            
            # Go to the last page
            if last_page != 0:
                self._app.go_to_page(last_page)
            else:
                self._toolbar.set_current_page(0)
                self._render_current_page()
            
            # Restore scroll position after a short delay to ensure page is rendered
            QTimer.singleShot(100, lambda: self._restore_scroll_position(last_scroll_x, last_scroll_y))
        else:
            # No saved position, start at page 0
            self._toolbar.set_current_page(0)
            self._render_current_page()
        
        self._status_bar.set_document_info(file_path, self._app.page_count)
        self.setWindowTitle(f"PDF Reader - {Path(file_path).name}")
        bookmarks = self._app.pdf_service.get_bookmarks()
        self._side_panel.set_bookmarks(bookmarks)
        # Add to recent documents history
        self._add_to_history(file_path)
    
    def _restore_scroll_position(self, x: int, y: int):
        """Restore scroll position in the viewer."""
        h_bar = self._viewer.horizontalScrollBar()
        v_bar = self._viewer.verticalScrollBar()
        h_bar.setValue(x)
        v_bar.setValue(y)

    def _on_document_closed(self):
        # Save current view position before closing
        self._save_current_view_position()
        
        self._viewer.clear()
        self._toolbar.set_page_count(0)
        self._status_bar.set_document_info("", 0)
        self.setWindowTitle("PDF Reader")
    
    def _save_current_view_position(self):
        """Save the current page, zoom, and scroll position for the open document."""
        if not self._app.is_document_loaded:
            return
        
        file_path = self._app.pdf_service.file_path
        if not file_path:
            return
        
        # Normalize file path
        normalized_path = str(Path(file_path).resolve())
        
        # Get current state
        current_page = self._app.current_page
        current_zoom = self._app.zoom_level
        h_bar = self._viewer.horizontalScrollBar()
        v_bar = self._viewer.verticalScrollBar()
        scroll_x = h_bar.value()
        scroll_y = v_bar.value()
        
        # Save position
        self._view_positions[normalized_path] = {
            "page": current_page,
            "zoom": current_zoom,
            "scroll_x": scroll_x,
            "scroll_y": scroll_y,
        }
        
        # Persist to disk
        self._save_history()

    def open_file(self, file_path: str):
        self._app.open_document(file_path)

    # ─── Page & Zoom ──────────────────────────────────────────────────────

    def _on_page_changed(self, page: int):
        self._toolbar.set_current_page(page)
        self._clear_selection()
        self._render_current_page()
        self._update_page_highlights()
        # Save position when page changes
        self._save_current_view_position()

    def _on_zoom_changed(self, zoom: float):
        self._toolbar.set_zoom_level(zoom)
        self._render_current_page()
        self._update_page_highlights()
        # Save position when zoom changes
        self._save_current_view_position()

    def _fit_to_width(self):
        """Zoom so the page width fits the viewer viewport width."""
        if not self._app.is_document_loaded:
            return
        page_w, _page_h = self._app.pdf_service.get_page_size(
            self._app.current_page)
        if page_w <= 0:
            return
        viewport_w = self._viewer.get_viewport_size().width()
        # Subtract a small margin for scrollbar clearance
        zoom = (viewport_w - 20) / page_w
        self._app.set_zoom(max(0.25, min(4.0, zoom)))

    def _fit_to_window(self):
        """Zoom so the entire page fits in the viewer viewport."""
        if not self._app.is_document_loaded:
            return
        page_w, page_h = self._app.pdf_service.get_page_size(
            self._app.current_page)
        if page_w <= 0 or page_h <= 0:
            return
        viewport = self._viewer.get_viewport_size()
        zoom_w = (viewport.width() - 20) / page_w
        zoom_h = (viewport.height() - 20) / page_h
        zoom = min(zoom_w, zoom_h)
        self._app.set_zoom(max(0.25, min(4.0, zoom)))

    def _on_error(self, message: str):
        QMessageBox.warning(self, "Error", message)

    def _render_current_page(self):
        if not self._app.is_document_loaded:
            return
        pixmap_data = self._app.pdf_service.get_page_pixmap(
            self._app.current_page, self._app.zoom_level)
        if pixmap_data:
            from PySide6.QtGui import QImage
            img = QImage(
                pixmap_data.samples, pixmap_data.width,
                pixmap_data.height, pixmap_data.stride,
                QImage.Format_RGB888)
            words = self._app.pdf_service.get_text_words(
                self._app.current_page)
            self._viewer.display_pixmap(
                QPixmap.fromImage(img), self._app.zoom_level, words)

    # ─── Selection ────────────────────────────────────────────────────────

    def _on_selection_made(self, rect: tuple, text: str, text_rects: list):
        if not text:
            return
        self._current_selection_rect = rect
        self._current_text_rects = text_rects
        self._current_selected_text = text
        # Show context menu at bottom-right of selection, mapped from page widget coordinates
        global_pos = self._viewer.map_page_to_global(
            QPoint(int(rect[2]), int(rect[3])))
        self._context_menu.show_at(global_pos, text)

    def _clear_selection(self):
        self._viewer.clear_selection()
        self._current_selection_rect = None
        self._current_text_rects = []

    # ─── Mark (Create Annotation) ─────────────────────────────────────────

    def _on_mark_selection(self, text: str):
        """Handle Mark action from context menu: create annotation and start AI processing."""
        if not self._app.is_document_loaded or not text:
            return

        # Ensure annotation panel is visible
        if not self._annotation_panel_visible:
            self._toggle_annotation_panel()

        # Create annotation
        annotation = self._app.annotation_manager.create(
            page_number=self._app.current_page,
            selected_text=text,
            text_rects=self._current_text_rects,
        )

        # Select it in the panel and start AI processing
        self._processing_annotation_id = annotation.id
        self._annotation_panel.select_annotation(annotation.id)

        # Show processing state in detail view
        detail = self._annotation_panel.detail_view
        detail.set_original_text(text)
        detail.start_correction()

        # Start AI correction → translation pipeline
        self._ai_processor.start_correction(text)

        # Update highlights
        self._update_page_highlights()
        self._clear_selection()

    # ─── Highlight Click ──────────────────────────────────────────────────

    def _on_highlight_clicked(self, annotation_id: str):
        """Handle click on a highlighted annotation area."""
        if not self._annotation_panel_visible:
            self._toggle_annotation_panel()
        self._annotation_panel.select_annotation(annotation_id)

    # ─── Annotation Panel Events ──────────────────────────────────────────

    def _on_annotation_selected(self, annotation_id: str):
        """Handle annotation selection in the panel."""
        annotation = self._app.annotation_manager.get(annotation_id)
        if annotation and annotation.page_number != self._app.current_page:
            self._app.go_to_page(annotation.page_number)

    def _on_annotation_delete_requested(self, annotation_id: str):
        reply = QMessageBox.question(
            self, "Delete Annotation", "Delete this annotation?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._app.annotation_manager.delete(annotation_id)

    def _on_annotations_loaded(self, annotations: list):
        self._annotation_panel.set_annotations(annotations)
        self._status_bar.set_annotation_count(len(annotations))
        self._update_page_highlights()

    def _on_annotation_created(self, annotation: Annotation):
        self._annotation_panel.add_annotation(annotation)
        self._update_annotation_status()

    def _on_annotation_updated(self, annotation: Annotation):
        self._annotation_panel.update_annotation(annotation)

    def _on_annotation_deleted(self, annotation_id: str):
        self._annotation_panel.remove_annotation(annotation_id)
        self._update_annotation_status()

    def _update_annotation_status(self):
        self._status_bar.set_annotation_count(
            self._app.annotation_manager.get_count())
        self._update_page_highlights()

    def _update_page_highlights(self):
        """Update yellow highlights on the page for all annotations."""
        if not self._app.is_document_loaded:
            return
        annotations = self._app.annotation_manager.get_by_page(
            self._app.current_page)
        highlights = []
        for ann in annotations:
            color = QColor(255, 235, 59)  # Yellow
            for rect in ann.text_rects:
                highlights.append((tuple(rect), color, ann.id))
        self._viewer.set_highlights(highlights)

    # ─── Toggle Panel ─────────────────────────────────────────────────────

    def _toggle_annotation_panel(self):
        if self._annotation_panel_visible:
            self._annotation_panel_sizes = self._splitter.sizes()
            self._annotation_panel.hide()
            self._annotation_panel_visible = False
        else:
            self._annotation_panel.show()
            self._splitter.setSizes(self._annotation_panel_sizes)
            self._annotation_panel_visible = True

    # ─── AI Processing Pipeline ───────────────────────────────────────────

    def _on_correction_chunk(self, chunk: str):
        self._annotation_panel.detail_view.append_corrected_chunk(chunk)

    def _on_correction_done(self, corrected_text: str):
        detail = self._annotation_panel.detail_view
        detail.set_corrected_text(corrected_text)

        # Save to annotation
        if self._processing_annotation_id:
            self._app.annotation_manager.update(
                self._processing_annotation_id,
                corrected_text=corrected_text)

        # Start translation
        detail.start_translation()
        self._ai_processor.start_translation(corrected_text)

    def _on_correction_error(self, error: str):
        detail = self._annotation_panel.detail_view
        detail.set_status(f"Correction error: {error}")
        # Fall back to translating original text
        detail.start_translation()
        text = self._current_selected_text or detail._original_display.toPlainText()
        self._ai_processor.start_translation(text)

    def _on_translation_chunk(self, chunk: str):
        self._annotation_panel.detail_view.append_translated_chunk(chunk)

    def _on_translation_done(self, translated_text: str):
        detail = self._annotation_panel.detail_view
        detail.set_translated_text(translated_text)
        detail.finish_processing()

        # Save to annotation
        if self._processing_annotation_id:
            self._app.annotation_manager.update(
                self._processing_annotation_id,
                translated_text=translated_text)
            self._processing_annotation_id = None

    def _on_translation_error(self, error: str):
        detail = self._annotation_panel.detail_view
        detail.set_status(f"Translation error: {error}")
        detail.finish_processing()
        self._processing_annotation_id = None

    def _on_explain_chunk(self, chunk: str):
        self._annotation_panel.detail_view.append_explain_chunk(chunk)

    def _on_explain_done(self, explanation: str):
        detail = self._annotation_panel.detail_view
        detail.set_explanation(explanation)
        detail.finish_processing()

        # Save to annotation
        ann_id = detail.current_annotation_id
        if ann_id:
            self._app.annotation_manager.update(
                ann_id, explanation=explanation)

    # ─── Detail View Actions ──────────────────────────────────────────────

    def _on_copy_result(self, text_type: str):
        msg = "Corrected text copied" if text_type == 'corrected' else "Translation copied"
        self._status_bar.set_status(msg)
        QTimer.singleShot(2000, self._status_bar.clear_status)

    def _on_retranslate(self):
        detail = self._annotation_panel.detail_view
        corrected = detail.get_corrected_text()
        if corrected:
            ann_id = detail.current_annotation_id
            self._processing_annotation_id = ann_id
            detail.start_translation()
            self._ai_processor.start_translation(corrected)

    def _on_explain(self):
        detail = self._annotation_panel.detail_view
        corrected = detail.get_corrected_text()
        if corrected:
            detail.start_explanation()
            self._ai_processor.start_explanation(
                corrected, detail.get_translated_text())

    def _on_tts(self):
        """Generate TTS audio and start playback."""
        detail = self._annotation_panel.detail_view
        corrected = detail.get_corrected_text()
        if corrected:
            # Stop any current playback
            self._stop_tts_playback()
            detail.set_status("Generating TTS audio...")
            detail.show_tts_generating()
            self._ai_processor.start_tts(corrected)

    def _on_tts_audio_ready(self, file_path: str):
        """Handle TTS audio file ready — load and play immediately."""
        detail = self._annotation_panel.detail_view
        try:
            duration = self._audio_player.load_audio(file_path)
            detail.show_tts_ready(duration)
            self._start_tts_playback()
        except Exception as e:
            detail.set_status(f"TTS playback error: {e}")
            detail.reset_tts_player()

    def _on_tts_error(self, error: str):
        detail = self._annotation_panel.detail_view
        detail.set_status(f"TTS error: {error}")
        detail.reset_tts_player()

    def _on_tts_play(self):
        """Play TTS audio from the beginning."""
        if self._audio_player.audio_file_path:
            self._start_tts_playback()

    def _on_tts_stop(self):
        """Stop TTS playback."""
        self._stop_tts_playback()

    def _start_tts_playback(self):
        """Start file-based audio playback."""
        detail = self._annotation_panel.detail_view
        if self._audio_player.play():
            detail.set_tts_playing(True)
            detail.set_status("Playing...")
            self._tts_update_timer.start()

    def _stop_tts_playback(self):
        """Stop file-based audio playback and reset UI."""
        self._audio_player.stop()
        self._tts_update_timer.stop()
        detail = self._annotation_panel.detail_view
        detail.set_tts_playing(False)
        length = self._audio_player.audio_length
        detail.update_tts_progress(0, length if length > 0 else 100)
        detail.set_status("Ready")

    def _update_tts_progress(self):
        """Timer callback to update TTS progress bar."""
        detail = self._annotation_panel.detail_view
        self._audio_player.update_position()
        pos = self._audio_player.current_position
        length = self._audio_player.audio_length

        if length > 0:
            detail.update_tts_progress(int(pos), int(length))

        # Check if playback finished
        if not self._audio_player.is_busy():
            self._tts_update_timer.stop()
            self._audio_player.is_playing = False
            detail.set_tts_playing(False)
            detail.update_tts_progress(0, int(length) if length > 0 else 100)
            detail.set_status("Ready")

    def _on_tts_settings(self):
        """Show TTS settings dialog."""
        from PySide6.QtWidgets import QDialog, QFormLayout, QRadioButton, QLineEdit, QDialogButtonBox, QButtonGroup
        from services.tts.remote_tts import RemoteTTSManager

        manager = RemoteTTSManager()

        dialog = QDialog(self)
        dialog.setWindowTitle("TTS Settings")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog { background-color: #252526; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QRadioButton { color: #d4d4d4; }
            QLineEdit {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #3f3f46; border-radius: 4px; padding: 4px;
            }
        """)

        form = QFormLayout(dialog)

        # TTS source selection
        group = QButtonGroup(dialog)
        remote_radio = QRadioButton("Remote TTS (WebSocket)")
        local_radio = QRadioButton("Local TTS (System)")
        group.addButton(remote_radio, 0)
        group.addButton(local_radio, 1)
        remote_radio.setChecked(True)
        form.addRow("Source:", remote_radio)
        form.addRow("", local_radio)

        # Server URL
        url_input = QLineEdit(manager.get_server_url())
        form.addRow("Server URL:", url_input)

        # Voice preset
        voice_input = QLineEdit(manager.get_voice_preset())
        form.addRow("Voice:", voice_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QPushButton { background-color: #0e639c; color: white; border: none; padding: 6px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #1177bb; }
        """)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            manager.set_server_url(url_input.text().strip())
            manager.set_voice_preset(voice_input.text().strip())

    def _on_regenerate(self):
        detail = self._annotation_panel.detail_view
        ann_id = detail.current_annotation_id
        if not ann_id:
            return
        annotation = self._app.annotation_manager.get(ann_id)
        if not annotation:
            return
        self._processing_annotation_id = ann_id
        detail.clear_results()
        detail.set_original_text(annotation.selected_text)
        detail.start_correction()
        self._ai_processor.start_correction(annotation.selected_text)

    # ─── Window Events ────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def closeEvent(self, event):
        # Save current view position before closing
        self._save_current_view_position()
        
        self._tts_update_timer.stop()
        self._audio_player.cleanup()
        self._ai_processor.stop_all()
        self._app.close_document()
        event.accept()
