"""
PDF document handling service using PyMuPDF.
"""
from typing import Optional, Tuple, List
from pathlib import Path

import fitz  # PyMuPDF


class PDFService:
    """
    Service for PDF document operations.

    Handles loading, rendering, and text extraction from PDF files.
    """

    def __init__(self):
        """Initialize PDF service."""
        self._document: Optional[fitz.Document] = None
        self._file_path: str = ""

    @property
    def is_loaded(self) -> bool:
        """Check if a document is loaded."""
        return self._document is not None

    @property
    def file_path(self) -> str:
        """Get current file path."""
        return self._file_path

    @property
    def document_path(self) -> str:
        """Get current document path (alias for file_path)."""
        return self._file_path

    @property
    def page_count(self) -> int:
        """Get total page count."""
        if self._document:
            return len(self._document)
        return 0

    def load(self, file_path: str) -> bool:
        """
        Load a PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            True if loaded successfully
        """
        try:
            self.close()
            self._document = fitz.open(file_path)
            self._file_path = str(Path(file_path).resolve())
            return True
        except Exception as e:
            print(f"Error loading PDF: {e}")
            return False

    def close(self):
        """Close the current document."""
        if self._document:
            self._document.close()
            self._document = None
            self._file_path = ""

    def get_page(self, page_number: int) -> Optional[fitz.Page]:
        """
        Get a page object.

        Args:
            page_number: Page index (0-based)

        Returns:
            Page object or None
        """
        if not self._document or page_number < 0 or page_number >= self.page_count:
            return None
        return self._document[page_number]

    def get_page_size(self, page_number: int) -> Tuple[float, float]:
        """
        Get page dimensions.

        Args:
            page_number: Page index (0-based)

        Returns:
            Tuple of (width, height)
        """
        page = self.get_page(page_number)
        if page:
            rect = page.rect
            return rect.width, rect.height
        return 0, 0

    def render_page(self, page_number: int, zoom: float = 1.0) -> Optional[bytes]:
        """
        Render a page to PNG bytes.

        Args:
            page_number: Page index (0-based)
            zoom: Zoom factor

        Returns:
            PNG image bytes or None
        """
        page = self.get_page(page_number)
        if not page:
            return None

        try:
            matrix = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix)
            return pixmap.tobytes("png")
        except Exception as e:
            print(f"Error rendering page: {e}")
            return None

    def get_page_pixmap(self, page_number: int, zoom: float = 1.0) -> Optional[fitz.Pixmap]:
        """
        Get page as pixmap object.

        Args:
            page_number: Page index (0-based)
            zoom: Zoom factor

        Returns:
            Pixmap object or None
        """
        page = self.get_page(page_number)
        if not page:
            return None

        try:
            matrix = fitz.Matrix(zoom, zoom)
            return page.get_pixmap(matrix=matrix)
        except Exception as e:
            print(f"Error getting pixmap: {e}")
            return None

    def get_text(self, page_number: int) -> str:
        """
        Extract all text from a page.

        Args:
            page_number: Page index (0-based)

        Returns:
            Page text content
        """
        page = self.get_page(page_number)
        if not page:
            return ""

        try:
            return page.get_text()
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def get_text_in_rect(self, page_number: int, rect: Tuple[float, float, float, float]) -> Tuple[str, List]:
        """
        Extract text within a rectangle.

        Args:
            page_number: Page index (0-based)
            rect: Rectangle (x0, y0, x1, y1) in page coordinates

        Returns:
            Tuple of (text, list of text rectangles)
        """
        page = self.get_page(page_number)
        if not page:
            return "", []

        try:
            # Create fitz.Rect from tuple
            fitz_rect = fitz.Rect(rect)

            # Get text blocks in the area
            text_dict = page.get_text("dict", clip=fitz_rect)

            text_parts = []
            text_rects = []

            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_rect = fitz.Rect(span["bbox"])
                            if fitz_rect.intersects(span_rect):
                                text_parts.append(span["text"])
                                text_rects.append(tuple(span["bbox"]))

            return " ".join(text_parts), text_rects

        except Exception as e:
            print(f"Error extracting text in rect: {e}")
            return "", []

    def search_text(self, page_number: int, query: str) -> List[Tuple[float, float, float, float]]:
        """
        Search for text on a page.

        Args:
            page_number: Page index (0-based)
            query: Text to search for

        Returns:
            List of rectangles where text was found
        """
        page = self.get_page(page_number)
        if not page:
            return []

        try:
            results = page.search_for(query)
            return [tuple(r) for r in results]
        except Exception as e:
            print(f"Error searching text: {e}")
            return []

    def get_metadata(self) -> dict:
        """Get document metadata."""
        if not self._document:
            return {}

        return {
            "title": self._document.metadata.get("title", ""),
            "author": self._document.metadata.get("author", ""),
            "subject": self._document.metadata.get("subject", ""),
            "creator": self._document.metadata.get("creator", ""),
            "producer": self._document.metadata.get("producer", ""),
            "page_count": self.page_count,
        }

    def get_bookmarks(self) -> List[Tuple[str, int, int]]:
        """
        Get document bookmarks/outline.

        Returns:
            List of tuples (title, page_number, level)
        """
        if not self._document:
            return []

        try:
            toc = self._document.get_toc()
            bookmarks = []
            for item in toc:
                level = item[0] - 1  # Convert to 0-based level
                title = item[1]
                page = item[2] - 1  # Convert to 0-based page
                if page >= 0:
                    bookmarks.append((title, page, level))
            return bookmarks
        except Exception as e:
            print(f"Error getting bookmarks: {e}")
            return []
