"""
SQLite database operations for annotation persistence.
"""
import sqlite3
import os
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from PDFReader.models.annotation import Annotation


class AnnotationDatabase:
    """SQLite database manager for annotations."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to user data directory.
        """
        if db_path is None:
            app_data = Path(os.environ.get("APPDATA", Path.home()))
            db_dir = app_data / "PDFReader"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "annotations.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    document_path TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    selected_text TEXT NOT NULL,
                    text_rects TEXT NOT NULL,
                    corrected_text TEXT,
                    translated_text TEXT,
                    explanation TEXT,
                    tts_audio_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_page
                ON annotations(document_path, page_number)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save(self, annotation: Annotation) -> bool:
        """
        Save or update an annotation.

        Args:
            annotation: Annotation to save

        Returns:
            True if successful
        """
        annotation.update_timestamp()
        data = annotation.to_dict()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO annotations
                (id, document_path, page_number, selected_text, text_rects,
                 corrected_text, translated_text, explanation, tts_audio_path,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["document_path"], data["page_number"],
                data["selected_text"], data["text_rects"], data["corrected_text"],
                data["translated_text"], data["explanation"], data["tts_audio_path"],
                data["created_at"], data["updated_at"]
            ))
            conn.commit()
        return True

    def get_by_id(self, annotation_id: str) -> Optional[Annotation]:
        """Get annotation by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM annotations WHERE id = ?",
                (annotation_id,)
            )
            row = cursor.fetchone()
            if row:
                return Annotation.from_dict(dict(row))
        return None

    def get_by_document(self, document_path: str) -> List[Annotation]:
        """Get all annotations for a document."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM annotations WHERE document_path = ? ORDER BY page_number, created_at",
                (document_path,)
            )
            return [Annotation.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_by_page(self, document_path: str, page_number: int) -> List[Annotation]:
        """Get annotations for a specific page."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM annotations WHERE document_path = ? AND page_number = ? ORDER BY created_at",
                (document_path, page_number)
            )
            return [Annotation.from_dict(dict(row)) for row in cursor.fetchall()]

    def delete(self, annotation_id: str) -> bool:
        """Delete an annotation by ID."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
            conn.commit()
        return True

    def delete_by_document(self, document_path: str) -> int:
        """Delete all annotations for a document. Returns count deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM annotations WHERE document_path = ?",
                (document_path,)
            )
            conn.commit()
            return cursor.rowcount

    def search(self, document_path: str, query: str) -> List[Annotation]:
        """Search annotations by text content."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM annotations
                WHERE document_path = ?
                AND (selected_text LIKE ? OR translated_text LIKE ? OR corrected_text LIKE ?)
                ORDER BY page_number, created_at
            """, (document_path, f"%{query}%", f"%{query}%", f"%{query}%"))
            return [Annotation.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_document_count(self, document_path: str) -> int:
        """Get count of annotations for a document."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM annotations WHERE document_path = ?",
                (document_path,)
            )
            return cursor.fetchone()[0]
