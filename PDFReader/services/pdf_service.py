"""
PDF document handling service using PyMuPDF.
"""
from typing import Optional, Tuple, List, Any, Dict
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
        # OCR cache keyed by page number to avoid expensive repeated OCR passes.
        self._ocr_words_cache: Dict[int, List[Tuple]] = {}
        self._ocr_attempted_pages: set[int] = set()

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
        self._ocr_words_cache.clear()
        self._ocr_attempted_pages.clear()

    def _run_page_ocr_words(self, page_number: int) -> List[Tuple]:
        """
        Run OCR for a page and return word-level tuples.

        Returns:
            List of word tuples in the same shape as page.get_text("words")
        """
        if not self._document or page_number < 0 or page_number >= self.page_count:
            return []
        if page_number in self._ocr_words_cache:
            return self._ocr_words_cache[page_number]
        if page_number in self._ocr_attempted_pages:
            return []

        self._ocr_attempted_pages.add(page_number)
        page = self._document[page_number]

        try:
            # PyMuPDF OCR API. This requires Tesseract to be available.
            try:
                textpage = page.get_textpage_ocr(full=True, dpi=200)
            except TypeError:
                # Compatibility fallback for older PyMuPDF signatures.
                textpage = page.get_textpage_ocr(dpi=200)
            words = textpage.extractWORDS() if textpage else []
            if words:
                words = sorted(words, key=lambda w: (w[5], w[6], w[7]))
                self._ocr_words_cache[page_number] = words
                return words
        except Exception as e:
            # OCR may be unavailable in the runtime environment; fail gracefully.
            print(f"OCR unavailable for page {page_number}: {e}")

        self._ocr_words_cache[page_number] = []
        return []

    @staticmethod
    def _chars_from_words(words: List[Tuple]) -> List[Tuple]:
        """
        Build character-level tuples from word-level tuples.

        This uses proportional slicing inside each word bbox when only
        OCR word boxes are available.
        """
        chars: List[Tuple] = []
        line_char_no: Dict[Tuple[int, int], int] = {}

        for w in words:
            if len(w) < 8:
                continue
            x0, y0, x1, y1, text, block_no, line_no, _word_no = w[:8]
            word_text = str(text or "")
            if not word_text:
                continue
            key = (int(block_no), int(line_no))
            cur_char_no = line_char_no.get(key, 0)
            width = max(0.0, float(x1) - float(x0))
            step = width / max(1, len(word_text))
            for i, c in enumerate(word_text):
                cx0 = float(x0) + i * step
                cx1 = float(x0) + (i + 1) * step
                chars.append(
                    (cx0, float(y0), cx1, float(y1), c, int(block_no), int(line_no), cur_char_no)
                )
                cur_char_no += 1
            line_char_no[key] = cur_char_no

        return sorted(chars, key=lambda c: (c[5], c[6], c[7]))

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

    def get_text_words(self, page_number: int) -> List[Tuple]:
        """
        Get word-level text data with bounding boxes.

        Each word entry is a tuple:
        (x0, y0, x1, y1, word_text, block_no, line_no, word_no)

        Args:
            page_number: Page index (0-based)

        Returns:
            List of word tuples sorted in reading order
        """
        page = self.get_page(page_number)
        if not page:
            return []

        try:
            words = page.get_text("words")
            if not words:
                # Scanned / image-only PDF: fall back to OCR words.
                words = self._run_page_ocr_words(page_number)
            # Sort by reading order: block, line, word
            return sorted(words, key=lambda w: (w[5], w[6], w[7]))
        except Exception as e:
            print(f"Error getting text words: {e}")
            return []

    def get_text_chars(self, page_number: int) -> List[Tuple]:
        """
        Get character-level text data with bounding boxes.

        Each entry is shaped like:
        (x0, y0, x1, y1, char_text, block_no, line_no, char_no)

        Uses rawdict character boxes when available; otherwise falls back to
        per-span proportional slicing.
        """
        page = self.get_page(page_number)
        if not page:
            return []

        chars: List[Tuple] = []
        try:
            raw = page.get_text("rawdict")
            for block_idx, block in enumerate(raw.get("blocks", [])):
                if block.get("type") != 0:
                    continue

                for line_idx, line in enumerate(block.get("lines", [])):
                    line_char_no = 0
                    for span in line.get("spans", []):
                        span_chars = span.get("chars")
                        if isinstance(span_chars, list) and span_chars:
                            for ch in span_chars:
                                c = ch.get("c", "")
                                bbox = ch.get("bbox")
                                if bbox is None or len(bbox) < 4:
                                    continue
                                x0, y0, x1, y1 = bbox[:4]
                                chars.append(
                                    (x0, y0, x1, y1, c, block_idx, line_idx, line_char_no)
                                )
                                line_char_no += 1
                            continue

                        # Fallback for environments where span-level chars are unavailable.
                        text = span.get("text", "")
                        bbox = span.get("bbox")
                        if not text or bbox is None or len(bbox) < 4:
                            continue
                        x0, y0, x1, y1 = bbox[:4]
                        width = max(0.0, float(x1) - float(x0))
                        step = width / max(1, len(text))
                        for i, c in enumerate(text):
                            cx0 = x0 + i * step
                            cx1 = x0 + (i + 1) * step
                            chars.append(
                                (cx0, y0, cx1, y1, c, block_idx, line_idx, line_char_no)
                            )
                            line_char_no += 1

            chars = sorted(chars, key=lambda c: (c[5], c[6], c[7]))
            if chars:
                return chars

            # Scanned / image-only PDF: fall back to OCR words -> chars.
            ocr_words = self._run_page_ocr_words(page_number)
            return self._chars_from_words(ocr_words)
        except Exception as e:
            print(f"Error getting text chars: {e}")
            return []

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
