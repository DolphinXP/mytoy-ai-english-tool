"""
Annotation CRUD operations manager with JSON file persistence.

Stores annotations as a JSON file alongside the PDF document.
For a PDF at '/path/to/document.pdf', annotations are stored at
'/path/to/document_annotations.json'.
"""
import json
import os
from typing import List, Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal

from PDFReader.models.annotation import Annotation
from PDFReader.utils.helpers import normalize_path


def _annotations_path(document_path: str) -> str:
    """Compute the JSON annotations file path for a given PDF document."""
    p = Path(document_path)
    return str(p.parent / f"{p.stem}_annotations.json")


class AnnotationManager(QObject):
    """
    Manages annotation lifecycle with JSON file persistence.

    Annotations are saved to a JSON file in the same directory as the PDF.

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
        self._current_document: str = ""
        self._annotations: dict[str, Annotation] = {}  # id -> Annotation
        self._direct_translations: list[tuple[str, str]] = []

    @property
    def current_document(self) -> str:
        """Get current document path."""
        return self._current_document

    def set_document(self, document_path: str):
        """
        Set current document and load its annotations from JSON.

        Args:
            document_path: Path to PDF document
        """
        self._current_document = normalize_path(document_path)
        self._annotations.clear()
        self._direct_translations.clear()

        if self._current_document:
            self._load_from_json()
            self.annotations_loaded.emit(list(self._annotations.values()))

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

        self._annotations[annotation.id] = annotation
        self._save_to_json()
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
            return None

        # Update fields
        for key, value in kwargs.items():
            if hasattr(annotation, key):
                setattr(annotation, key, value)

        annotation.update_timestamp()
        self._annotations[annotation.id] = annotation
        self._save_to_json()
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

        self._save_to_json()
        self.annotation_deleted.emit(annotation_id)
        return True

    def get(self, annotation_id: str) -> Optional[Annotation]:
        """Get annotation by ID."""
        return self._annotations.get(annotation_id)

    def get_all(self) -> List[Annotation]:
        """Get all annotations for current document."""
        return list(self._annotations.values())

    def get_by_page(self, page_number: int) -> List[Annotation]:
        """Get annotations for a specific page."""
        return [a for a in self._annotations.values() if a.page_number == page_number]

    def search(self, query: str) -> List[Annotation]:
        """Search annotations by text content."""
        query_lower = query.lower()
        results = []
        for ann in self._annotations.values():
            if (query_lower in ann.selected_text.lower() or
                    query_lower in ann.corrected_text.lower() or
                    query_lower in ann.translated_text.lower()):
                results.append(ann)
        return results

    def get_count(self) -> int:
        """Get total annotation count for current document."""
        return len(self._annotations)

    def clear_document(self):
        """Clear all annotations for current document."""
        self._annotations.clear()
        self._direct_translations.clear()
        self._save_to_json()
        self.annotations_loaded.emit([])

    def get_direct_translations(self) -> List[tuple[str, str]]:
        """Get persisted direct translation history for current document."""
        return list(self._direct_translations)

    def add_direct_translation(self, source_text: str, translated_text: str):
        """Add one direct translation record and persist."""
        src = (source_text or "").strip()
        dst = (translated_text or "").strip()
        if not src or not dst:
            return

        self._direct_translations.insert(0, (src, dst))
        self._direct_translations = self._direct_translations[:200]
        self._save_to_json()

    def delete_direct_translation(self, index: int) -> bool:
        """Delete one direct translation by index and persist."""
        if index < 0 or index >= len(self._direct_translations):
            return False
        del self._direct_translations[index]
        self._save_to_json()
        return True

    # ─── JSON Persistence ─────────────────────────────────────────────────

    def _load_from_json(self):
        """Load annotations from the JSON file alongside the PDF."""
        json_path = _annotations_path(self._current_document)
        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for ann_data in data.get("annotations", []):
                # Ensure document_path is set correctly
                ann_data["document_path"] = self._current_document
                ann = Annotation.from_dict(ann_data)
                self._annotations[ann.id] = ann

            self._direct_translations.clear()
            for item in data.get("direct_translations", []):
                if isinstance(item, dict):
                    src = str(item.get("source_text", "")).strip()
                    dst = str(item.get("translated_text", "")).strip()
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    src = str(item[0]).strip()
                    dst = str(item[1]).strip()
                else:
                    continue
                if src and dst:
                    self._direct_translations.append((src, dst))
            self._direct_translations = self._direct_translations[:200]

        except Exception as e:
            print(f"Error loading annotations from {json_path}: {e}")

    def _save_to_json(self):
        """Save all annotations to the JSON file alongside the PDF."""
        if not self._current_document:
            return

        json_path = _annotations_path(self._current_document)

        try:
            annotations_data = []
            for ann in sorted(self._annotations.values(),
                              key=lambda a: (a.page_number, a.created_at)):
                annotations_data.append(ann.to_dict())

            data = {
                "document_path": self._current_document,
                "annotations": annotations_data,
                "direct_translations": [
                    {
                        "source_text": src,
                        "translated_text": dst,
                    }
                    for src, dst in self._direct_translations
                ],
            }

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Error saving annotations to {json_path}: {e}")
