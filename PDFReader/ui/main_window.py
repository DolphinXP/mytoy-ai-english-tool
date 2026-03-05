"""Main window for PDFReader application."""
from core.thread_manager import ThreadManager
from PDFReader.models.annotation import Annotation
from PDFReader.core.ai_processor import AIProcessor
from PDFReader.core.app import PDFReaderApp
from PDFReader.ui.context_menu import TextContextMenu
from PDFReader.ui.side_panel import SidePanel
from PDFReader.ui.status_bar import StatusBarWidget
from PDFReader.ui.annotation_panel import AnnotationPanel
from PDFReader.ui.pdf_viewer import PDFViewerWidget
from PDFReader.ui.toolbar import ToolbarWidget
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QColor
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QApplication
)
from typing import Optional
import sys
from pathlib import Path

_parent_dir = str(Path(__file__).parent.parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


DARK_THEME = """
    QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }
    QSplitter::handle { background-color: #333333; }
    QMessageBox { background-color: #2d2d2d; color: #ffffff; }
    QMessageBox QPushButton { background-color: #0078d4; color: #ffffff; border: none; padding: 6px 16px; border-radius: 4px; }
    QMessageBox QPushButton:hover { background-color: #1084d8; }
"""


class MainWindow(QMainWindow):
    """Main application window."""

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
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()

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

        # Main content with side panel
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Side panel (bookmarks + history)
        self._side_panel = SidePanel()
        content_layout.addWidget(self._side_panel)

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

        content_layout.addWidget(self._splitter, 1)
        layout.addLayout(content_layout, 1)

        self._status_bar = StatusBarWidget()
        layout.addWidget(self._status_bar)

        # Context menu for text selection
        self._context_menu = TextContextMenu(self)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence.Open, self, self._on_open_file)
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
        self._toolbar.zoom_level_changed.connect(self._app.set_zoom)
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
        self._annotation_panel.regenerate_clicked.connect(self._on_regenerate)

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
        self._side_panel.history_clicked.connect(self._on_history_clicked)

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
        self._ai_processor.tts_finished.connect(
            lambda: self._annotation_panel.detail_view.set_status("Ready"))
        self._ai_processor.tts_error.connect(
            lambda e: self._annotation_panel.detail_view.set_status(f"TTS error: {e}"))

    # ─── File / Document ──────────────────────────────────────────────────

    def _on_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self._app.open_document(file_path)

    def _on_document_loaded(self, file_path: str):
        self._toolbar.set_page_count(self._app.page_count)
        self._toolbar.set_current_page(0)
        self._status_bar.set_document_info(file_path, self._app.page_count)
        self.setWindowTitle(f"PDF Reader - {Path(file_path).name}")
        self._render_current_page()
        bookmarks = self._app.pdf_service.get_bookmarks()
        self._side_panel.set_bookmarks(bookmarks)

    def _on_document_closed(self):
        self._viewer.clear()
        self._toolbar.set_page_count(0)
        self._status_bar.set_document_info("", 0)
        self.setWindowTitle("PDF Reader")

    def open_file(self, file_path: str):
        self._app.open_document(file_path)

    # ─── Page & Zoom ──────────────────────────────────────────────────────

    def _on_page_changed(self, page: int):
        self._toolbar.set_current_page(page)
        self._clear_selection()
        self._render_current_page()
        self._update_page_highlights()
        if self._app.is_document_loaded:
            doc_path = self._app.pdf_service.document_path
            self._side_panel.add_history(
                doc_path, page, Path(doc_path).stem if doc_path else "Unknown")

    def _on_zoom_changed(self, zoom: float):
        self._toolbar.set_zoom_level(zoom)
        self._render_current_page()
        self._update_page_highlights()

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
        # Show context menu at selection end
        global_pos = self._viewer.mapToGlobal(
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

    def _on_history_clicked(self, doc_path: str, page: int):
        if self._app.pdf_service.document_path != doc_path:
            self._app.open_document(doc_path)
        self._app.go_to_page(page)

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
        detail = self._annotation_panel.detail_view
        corrected = detail.get_corrected_text()
        if corrected:
            detail.set_status("Playing TTS...")
            self._ai_processor.start_tts(corrected)

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
        self._ai_processor.stop_all()
        self._app.close_document()
        event.accept()
