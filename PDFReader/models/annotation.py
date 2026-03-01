"""
Annotation data model for PDF reading notes.
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Tuple, List


@dataclass
class Annotation:
    """
    Represents an annotation/reading note for a PDF document.

    Attributes:
        id: Unique identifier (UUID)
        document_path: Path to the PDF file
        page_number: 0-indexed page number
        selected_text: Original selected text from PDF
        text_rects: List of (x0, y0, x1, y1) coordinates for text regions
        corrected_text: AI-corrected text
        translated_text: Translation result
        explanation: AI explanation (optional)
        tts_audio_path: Path to generated audio file (optional)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    document_path: str
    page_number: int
    selected_text: str
    text_rects: List[Tuple[float, float, float, float]]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    corrected_text: str = ""
    translated_text: str = ""
    explanation: str = ""
    tts_audio_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert annotation to dictionary for database storage."""
        return {
            "id": self.id,
            "document_path": self.document_path,
            "page_number": self.page_number,
            "selected_text": self.selected_text,
            "text_rects": json.dumps(self.text_rects),
            "corrected_text": self.corrected_text,
            "translated_text": self.translated_text,
            "explanation": self.explanation,
            "tts_audio_path": self.tts_audio_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        """Create annotation from dictionary (database row)."""
        text_rects = data.get("text_rects", "[]")
        if isinstance(text_rects, str):
            text_rects = json.loads(text_rects)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=data["id"],
            document_path=data["document_path"],
            page_number=data["page_number"],
            selected_text=data["selected_text"],
            text_rects=[tuple(r) for r in text_rects],
            corrected_text=data.get("corrected_text", ""),
            translated_text=data.get("translated_text", ""),
            explanation=data.get("explanation", ""),
            tts_audio_path=data.get("tts_audio_path", ""),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )

    def update_timestamp(self):
        """Update the updated_at timestamp to now."""
        self.updated_at = datetime.now()

    def get_preview(self, max_length: int = 50) -> str:
        """Get a preview of the annotation content."""
        text = self.translated_text or self.corrected_text or self.selected_text
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
