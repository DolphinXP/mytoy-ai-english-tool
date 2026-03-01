"""
Annotation CRUD operations manager.
"""
from typing import List, Optional, Callable
from PySide6.QtCore import QObject, Signal

from PDFReader.models.annotation import Annotation
from PDFReader.db.database import AnnotationDatabase
from PDFReader.utils.helpers import normalize_path


class AnnotationManager(QObject):
    """
    Manages annotation lifecycle and persistence.

    Signals:
        annotation_created: Emitted when a new annotation is created
        annotation_updated: Emitted when an annotation is updated
        annotation_deleted: Emitted when an annotation is deleted
        annotations_loaded: Emitted when annotations are loaded for a document
    """

    annotation_created = Signal(object)  # Annotation
    annotation_updated = Signal(object)  # Annotation
    annotation_deleted = Signal(str)  # annotation_id
    annotations_loaded = Signal(list)  # List[Annotation]

    def __init__(self, parent=None):
        """Initialize annotation manager."""
        super().__init__(parent)
        self._database = AnnotationDatabase()
        self._current_document: str = ""
        self._annotations: dict[str, Annotation] = {}  # id -> Annotation

    @property
    def current_document(self) -> str:
        """Get current document path."""
        return self._current_document

    def set_document(self, document_path: str):
        """
        Set current document and load its annotations.

        Args:
            document_path: Path to PDF document
        """
        self._current_document = normalize_path(document_path)
        self._annotations.clear()

        if self._current_document:
            annotations = self._database.get_by_document(self._current_document)
            for ann in annotations:
                self._annotations[ann.id] = ann
            self.annotations_loaded.emit(annotations)

    def create(self, page_number: int, selected_text: str,
               text_rects: list, corrected_text: str = "",
               translated_text: str = "", explanation: str = "") -> Annotation:
        """
        Create a new annotation.

        Args:
            page_number: Page number (0-indexed)
            selected_text: Original selected text
            text_rects: List of text rectangles
            corrected_text: AI-corrected text
            translated_text: Translation result
            explanation: AI explanation

        Returns:
            Created Annotation object
        """
        annotation = Annotation(
            document_path=self._current_document,
            page_number=page_number,
            selected_text=selected_text,
            text_rects=text_rects,
            corrected_text=corrected_text,
            translated_text=translated_text,
            explanation=explanation,
        )

        self._database.save(annotation)
        self._annotations[annotation.id] = annotation
        self.annotation_created.emit(annotation)

        return annotation

    def update(self, annotation_id: str, **kwargs) -> Optional[Annotation]:
        """
        Update an existing annotation.

        Args:
            annotation_id: ID of annotation to update
            **kwargs: Fields to update (corrected_text, translated_text, etc.)

        Returns:
            Updated Annotation or None if not found
        """
        annotation = self._annotations.get(annotation_id)
        if not annotation:
            annotation = self._database.get_by_id(annotation_id)
            if not annotation:
                return None

        # Update fields
        for key, value in kwargs.items():
            if hasattr(annotation, key):
                setattr(annotation, key, value)

        annotation.update_timestamp()
        self._database.save(annotation)
        self._annotations[annotation.id] = annotation
        self.annotation_updated.emit(annotation)

        return annotation

    def delete(self, annotation_id: str) -> bool:
        """
        Delete an annotation.

        Args:
            annotation_id: ID of annotation to delete

        Returns:
            True if deleted successfully
        """
        if annotation_id in self._annotations:
            del self._annotations[annotation_id]

        self._database.delete(annotation_id)
        self.annotation_deleted.emit(annotation_id)
        return True

    def get(self, annotation_id: str) -> Optional[Annotation]:
        """Get annotation by ID."""
        if annotation_id in self._annotations:
            return self._annotations[annotation_id]
        return self._database.get_by_id(annotation_id)

    def get_all(self) -> List[Annotation]:
        """Get all annotations for current document."""
        return list(self._annotations.values())

    def get_by_page(self, page_number: int) -> List[Annotation]:
        """Get annotations for a specific page."""
        return [a for a in self._annotations.values() if a.page_number == page_number]

    def search(self, query: str) -> List[Annotation]:
        """Search annotations by text content."""
        if not self._current_document:
            return []
        return self._database.search(self._current_document, query)

    def get_count(self) -> int:
        """Get total annotation count for current document."""
        return len(self._annotations)

    def clear_document(self):
        """Clear all annotations for current document."""
        if self._current_document:
            self._database.delete_by_document(self._current_document)
            self._annotations.clear()
            self.annotations_loaded.emit([])
