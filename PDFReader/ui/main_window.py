"""Main window for PDFReader application."""
from core.thread_manager import ThreadManager
from PDFReader.models.annotation import Annotation
from PDFReader.core.ai_processor import AIProcessor
from PDFReader.core.app import PDFReaderApp
from PDFReader.ui.result_panel import ResultPanel
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
        self._annotation_panel.setMaximumWidth(400)
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

        # Context menu (replaces popup window)
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
        self._viewer.page_up_requested.connect(self._app.previous_page)
        self._viewer.page_down_requested.connect(self._app.next_page)
        self._viewer.zoom_in_requested.connect(self._app.zoom_in)
        self._viewer.zoom_out_requested.connect(self._app.zoom_out)

        # Annotation panel
        self._annotation_panel.annotation_selected.connect(
            self._on_annotation_selected)
        self._annotation_panel.annotation_deleted.connect(
            self._on_annotation_delete_requested)

        # Annotation manager
        self._app.annotation_manager.annotations_loaded.connect(
            self._on_annotations_loaded)
        self._app.annotation_manager.annotation_created.connect(
            self._on_annotation_created)
        self._app.annotation_manager.annotation_deleted.connect(
            self._on_annotation_deleted)

        # Context menu
        self._context_menu.translate_clicked.connect(
            self._on_translate_selection)
        self._context_menu.explain_clicked.connect(self._on_explain_selection)

        # Side panel
        self._side_panel.bookmark_clicked.connect(self._app.go_to_page)
        self._side_panel.history_clicked.connect(self._on_history_clicked)

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
        # Load bookmarks
        bookmarks = self._app.pdf_service.get_bookmarks()
        self._side_panel.set_bookmarks(bookmarks)

    def _on_document_closed(self):
        self._viewer.clear()
        self._toolbar.set_page_count(0)
        self._status_bar.set_document_info("", 0)
        self.setWindowTitle("PDF Reader")

    def _on_page_changed(self, page: int):
        self._toolbar.set_current_page(page)
        self._clear_selection()
        self._render_current_page()
        self._update_page_highlights()
        if self._app.is_document_loaded:
            doc_path = self._app.pdf_service.document_path
            self._side_panel.add_history(doc_path, page, Path(
                doc_path).stem if doc_path else "Unknown")

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
            img = QImage(pixmap_data.samples, pixmap_data.width,
                         pixmap_data.height, pixmap_data.stride, QImage.Format_RGB888)
            words = self._app.pdf_service.get_text_words(
                self._app.current_page)
            self._viewer.display_pixmap(
                QPixmap.fromImage(img), self._app.zoom_level, words)

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

    def _on_history_clicked(self, doc_path: str, page: int):
        if self._app.pdf_service.document_path != doc_path:
            self._app.open_document(doc_path)
        self._app.go_to_page(page)

    # Annotation methods
    def _on_annotations_loaded(self, annotations: list):
        self._annotation_panel.set_annotations(annotations)
        self._status_bar.set_annotation_count(len(annotations))
        self._update_page_highlights()

    def _on_annotation_created(self, annotation: Annotation):
        self._annotation_panel.add_annotation(annotation)
        self._update_annotation_status()

    def _on_annotation_deleted(self, annotation_id: str):
        self._annotation_panel.remove_annotation(annotation_id)
        self._update_annotation_status()

    def _update_annotation_status(self):
        self._status_bar.set_annotation_count(
            self._app.annotation_manager.get_count())
        self._update_page_highlights()

    def _on_annotation_selected(self, annotation_id: str):
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

    def _update_page_highlights(self):
        if not self._app.is_document_loaded:
            return
        annotations = self._app.annotation_manager.get_by_page(
            self._app.current_page)
        highlights = []
        for ann in annotations:
            color = QColor(255, 235, 59)
            for rect in ann.text_rects:
                highlights.append((tuple(rect), color))
        self._viewer.set_highlights(highlights)

    def open_file(self, file_path: str):
        self._app.open_document(file_path)

    def _toggle_annotation_panel(self):
        """Toggle the annotation panel visibility."""
        if self._annotation_panel_visible:
            # Save current sizes before collapsing
            self._annotation_panel_sizes = self._splitter.sizes()
            self._annotation_panel.hide()
            self._annotation_panel_visible = False
        else:
            # Restore the panel
            self._annotation_panel.show()
            self._splitter.setSizes(self._annotation_panel_sizes)
            self._annotation_panel_visible = True

    # AI Processing
    def _on_translate_selection(self, text: str):
        self._current_selected_text = text
        self._show_result_panel()
        self._result_panel.set_original_text(text)
        self._result_panel.start_correction()
        self._ai_processor.start_correction(text)

    def _on_explain_selection(self, text: str):
        self._current_selected_text = text
        self._show_result_panel()
        self._result_panel.set_original_text(text)
        self._result_panel.start_explanation()
        self._ai_processor.start_explanation(text)

    def _show_result_panel(self):
        if not hasattr(self, '_result_panel') or not self._result_panel:
            self._create_result_panel()
        self._result_panel.show()
        self._position_result_panel()

    def _create_result_panel(self):
        self._result_panel = ResultPanel(self)
        self._result_panel.setFixedWidth(380)
        self._result_panel.setMinimumHeight(500)
        self._result_panel.copy_clicked.connect(self._on_copy_result)
        self._result_panel.retranslate_clicked.connect(self._on_retranslate)
        self._result_panel.explain_clicked.connect(self._on_explain)
        self._result_panel.tts_clicked.connect(self._on_tts)
        self._result_panel.regenerate_clicked.connect(self._on_regenerate)
        self._result_panel.close_clicked.connect(self._close_result_panel)
        # Connect AI processor signals
        self._ai_processor.correction_chunk.connect(
            self._result_panel.append_corrected_chunk)
        self._ai_processor.correction_done.connect(self._on_correction_done)
        self._ai_processor.correction_error.connect(self._on_correction_error)
        self._ai_processor.translation_chunk.connect(
            self._result_panel.append_translated_chunk)
        self._ai_processor.translation_done.connect(self._on_translation_done)
        self._ai_processor.translation_error.connect(
            self._on_translation_error)
        self._ai_processor.explain_chunk.connect(
            self._result_panel.append_explain_chunk)
        self._ai_processor.explain_done.connect(self._on_explain_done)
        self._ai_processor.tts_finished.connect(
            lambda: self._result_panel.set_status("Ready"))
        self._ai_processor.tts_error.connect(
            lambda e: self._result_panel.set_status(f"TTS error: {e}"))

    def _position_result_panel(self):
        if hasattr(self, '_result_panel') and self._result_panel:
            self._result_panel.move(
                self.width() - self._result_panel.width() - 20, 80)

    def _close_result_panel(self):
        if hasattr(self, '_result_panel') and self._result_panel:
            self._result_panel.hide()
            self._ai_processor.stop_all()

    def _on_correction_done(self, corrected_text: str):
        self._result_panel.set_corrected_text(corrected_text)
        self._result_panel.start_translation()
        self._ai_processor.start_translation(corrected_text)

    def _on_correction_error(self, error: str):
        self._result_panel.set_status(f"Correction error: {error}")
        self._result_panel.start_translation()
        self._ai_processor.start_translation(self._current_selected_text)

    def _on_translation_done(self, translated_text: str):
        self._result_panel.set_translated_text(translated_text)
        self._result_panel.finish_processing()
        self._result_panel.set_status("Ready")

    def _on_translation_error(self, error: str):
        self._result_panel.set_status(f"Translation error: {error}")
        self._result_panel.finish_processing()

    def _on_explain_done(self, explanation: str):
        self._result_panel.set_explanation(explanation)
        self._result_panel.finish_processing()

    def _on_copy_result(self, text_type: str):
        clipboard = QApplication.clipboard()
        text = self._result_panel.get_corrected_text(
        ) if text_type == 'corrected' else self._result_panel.get_translated_text()
        msg = "Corrected text copied" if text_type == 'corrected' else "Translation copied"
        clipboard.setText(text)
        self._status_bar.set_status(msg)
        QTimer.singleShot(2000, self._status_bar.clear_status)

    def _on_retranslate(self):
        if corrected := self._result_panel.get_corrected_text():
            self._result_panel.start_translation()
            self._ai_processor.start_translation(corrected)

    def _on_explain(self):
        if corrected := self._result_panel.get_corrected_text():
            self._result_panel.start_explanation()
            self._ai_processor.start_explanation(
                corrected, self._result_panel.get_translated_text())

    def _on_tts(self):
        if corrected := self._result_panel.get_corrected_text():
            self._result_panel.set_status("Playing TTS...")
            self._ai_processor.start_tts(corrected)

    def _on_regenerate(self):
        if self._current_selected_text:
            self._result_panel.clear()
            self._result_panel.set_original_text(self._current_selected_text)
            self._result_panel.start_correction()
            self._ai_processor.start_correction(self._current_selected_text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_result_panel()

    def closeEvent(self, event):
        self._ai_processor.stop_all()
        self._app.close_document()
        event.accept()
