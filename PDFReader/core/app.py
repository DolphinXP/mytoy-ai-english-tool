"""
Main application class for PDFReader.
"""
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for shared imports BEFORE other imports
_parent_dir = str(Path(__file__).parent.parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

from PDFReader.services.pdf_service import PDFService
from PDFReader.core.annotation_manager import AnnotationManager
from PDFReader.config import Config


class PDFReaderApp(QObject):
    """
    Main application controller for PDFReader.

    Coordinates between services, managers, and UI components.
    """

    # Signals
    document_loaded = Signal(str)  # file_path
    document_closed = Signal()
    page_changed = Signal(int)  # page_number
    zoom_changed = Signal(float)  # zoom_level
    error_occurred = Signal(str)  # error_message

    def __init__(self, parent=None):
        """Initialize application."""
        super().__init__(parent)

        # Services
        self._pdf_service = PDFService()
        self._annotation_manager = AnnotationManager(self)

        # State
        self._current_page: int = 0
        self._zoom_level: float = 1.0
        self._config = Config()

    @property
    def pdf_service(self) -> PDFService:
        """Get PDF service instance."""
        return self._pdf_service

    @property
    def annotation_manager(self) -> AnnotationManager:
        """Get annotation manager instance."""
        return self._annotation_manager

    @property
    def config(self) -> Config:
        """Get configuration instance."""
        return self._config

    @property
    def current_page(self) -> int:
        """Get current page number."""
        return self._current_page

    @property
    def zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_level

    @property
    def page_count(self) -> int:
        """Get total page count."""
        return self._pdf_service.page_count

    @property
    def is_document_loaded(self) -> bool:
        """Check if a document is loaded."""
        return self._pdf_service.is_loaded

    @property
    def document_path(self) -> str:
        """Get current document path."""
        return self._pdf_service.file_path

    def open_document(self, file_path: str) -> bool:
        """
        Open a PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            True if opened successfully
        """
        if not Path(file_path).exists():
            self.error_occurred.emit(f"File not found: {file_path}")
            return False

        if not self._pdf_service.load(file_path):
            self.error_occurred.emit(f"Failed to load PDF: {file_path}")
            return False

        # Reset state
        self._current_page = 0
        self._zoom_level = 1.0

        # Load annotations for this document
        self._annotation_manager.set_document(file_path)

        self.document_loaded.emit(file_path)
        # document_loaded handlers may restore a saved page, so emit the
        # effective current page instead of always forcing page 0.
        self.page_changed.emit(self._current_page)

        return True

    def close_document(self):
        """Close the current document."""
        self._pdf_service.close()
        self._annotation_manager.set_document("")
        self._current_page = 0
        self.document_closed.emit()

    def go_to_page(self, page_number: int) -> bool:
        """
        Navigate to a specific page.

        Args:
            page_number: Page index (0-based)

        Returns:
            True if navigation successful
        """
        if not self.is_document_loaded:
            return False

        if page_number < 0 or page_number >= self.page_count:
            return False

        self._current_page = page_number
        self.page_changed.emit(page_number)
        return True

    def next_page(self) -> bool:
        """Go to next page."""
        return self.go_to_page(self._current_page + 1)

    def previous_page(self) -> bool:
        """Go to previous page."""
        return self.go_to_page(self._current_page - 1)

    def first_page(self) -> bool:
        """Go to first page."""
        return self.go_to_page(0)

    def last_page(self) -> bool:
        """Go to last page."""
        return self.go_to_page(self.page_count - 1)

    def set_zoom(self, zoom_level: float) -> bool:
        """
        Set zoom level.

        Args:
            zoom_level: Zoom factor (0.25 to 4.0)

        Returns:
            True if zoom changed
        """
        zoom_level = max(0.25, min(4.0, zoom_level))

        if zoom_level != self._zoom_level:
            self._zoom_level = zoom_level
            self.zoom_changed.emit(zoom_level)
            return True

        return False

    def zoom_in(self) -> bool:
        """Increase zoom by 25%."""
        return self.set_zoom(self._zoom_level + 0.25)

    def zoom_out(self) -> bool:
        """Decrease zoom by 25%."""
        return self.set_zoom(self._zoom_level - 0.25)

    def reset_zoom(self) -> bool:
        """Reset zoom to 100%."""
        return self.set_zoom(1.0)

    def render_current_page(self) -> Optional[bytes]:
        """Render current page at current zoom level."""
        return self._pdf_service.render_page(self._current_page, self._zoom_level)

    def get_text_in_selection(self, rect: tuple) -> tuple:
        """
        Get text within a selection rectangle.

        Args:
            rect: Selection rectangle (x0, y0, x1, y1) in page coordinates

        Returns:
            Tuple of (text, text_rects)
        """
        # Adjust for zoom
        adjusted_rect = tuple(c / self._zoom_level for c in rect)
        return self._pdf_service.get_text_in_rect(self._current_page, adjusted_rect)
