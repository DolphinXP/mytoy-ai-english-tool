"""
PDF viewer widget with text-flow selection support.

Implements word-level text selection that follows reading order,
similar to how text editors select text across lines.
"""
from typing import Optional, Tuple, List, Callable
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QMouseEvent, QPaintEvent, QWheelEvent


class PDFPageWidget(QWidget):
    """Widget displaying a single PDF page with text-flow selection overlay."""

    selection_started = Signal()
    # (selected_text, word_rects in page coords)
    text_selected = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._zoom: float = 1.0
        self._is_selecting: bool = False
        # Annotation highlights
        self._highlight_rects: List[Tuple[QRect, QColor]] = []
        # Per-line selection highlight rects (display coords)
        self._selection_rects: List[QRect] = []
        # External highlights (e.g., search results)
        self._external_text_rects: List[QRect] = []

        # Word-level text data from PyMuPDF get_text("words")
        # Each word: (x0, y0, x1, y1, word_text, block_no, line_no, word_no)
        self._words: List[Tuple] = []
        self._start_word_idx: int = -1
        self._end_word_idx: int = -1
        self._selected_indices: List[int] = []

        self.setMouseTracking(True)
        self.setCursor(Qt.IBeamCursor)

    def set_page(self, pixmap: QPixmap, zoom: float = 1.0, words: List[Tuple] = None):
        """Set the page pixmap and word data to display."""
        self._pixmap = pixmap
        self._zoom = zoom
        self._words = sorted(words or [], key=lambda w: (w[5], w[6], w[7]))
        self._clear_selection_internal()
        self._external_text_rects.clear()
        if pixmap:
            self.setFixedSize(pixmap.size())
        self.update()

    def _clear_selection_internal(self):
        """Clear selection state without triggering signals."""
        self._is_selecting = False
        self._selection_rects.clear()
        self._selected_indices.clear()
        self._start_word_idx = -1
        self._end_word_idx = -1

    def clear(self):
        """Clear the page display."""
        self._pixmap = None
        self._highlight_rects.clear()
        self._external_text_rects.clear()
        self._words.clear()
        self._clear_selection_internal()
        self.update()

    def set_highlights(self, rects: List[Tuple[Tuple[float, float, float, float], QColor]]):
        """Set highlight rectangles for annotations."""
        self._highlight_rects.clear()
        for rect_tuple, color in rects:
            x0, y0, x1, y1 = rect_tuple
            qrect = QRect(
                int(x0 * self._zoom), int(y0 * self._zoom),
                int((x1 - x0) * self._zoom), int((y1 - y0) * self._zoom)
            )
            self._highlight_rects.append((qrect, color))
        self.update()

    def set_text_selection_rects(self, rects: List[Tuple[float, float, float, float]]):
        """Set text selection rectangles from external source (e.g., search highlights)."""
        self._external_text_rects.clear()
        for rect_tuple in rects:
            x0, y0, x1, y1 = rect_tuple
            qrect = QRect(
                int(x0 * self._zoom), int(y0 * self._zoom),
                int((x1 - x0) * self._zoom), int((y1 - y0) * self._zoom)
            )
            self._external_text_rects.append(qrect)
        self.update()

    def get_selection_rect(self) -> QRect:
        """Get bounding rect of the current selection in display coordinates."""
        if not self._selection_rects:
            return QRect()
        x0 = min(r.x() for r in self._selection_rects)
        y0 = min(r.y() for r in self._selection_rects)
        x1 = max(r.x() + r.width() for r in self._selection_rects)
        y1 = max(r.y() + r.height() for r in self._selection_rects)
        return QRect(x0, y0, x1 - x0, y1 - y0)

    def clear_selection(self):
        """Clear text selection."""
        self._clear_selection_internal()
        self._external_text_rects.clear()
        self.update()

    def _find_word_at_pos(self, pos: QPoint) -> int:
        """
        Find the word index at or nearest to the given display position.

        Uses text-editor logic:
        1. Find the line closest to the vertical position
        2. Find the word on that line closest to the horizontal position
        3. If point is past the end of a line, select the last word
        4. If point is before the start of a line, select the first word
        """
        if not self._words:
            return -1

        zoom = self._zoom
        # Convert display coords to page coords
        px = pos.x() / zoom
        py = pos.y() / zoom

        # Group words by line key (block_no, line_no)
        lines = {}
        for i, w in enumerate(self._words):
            key = (w[5], w[6])
            if key not in lines:
                lines[key] = []
            lines[key].append(i)

        if not lines:
            return -1

        # Sort lines by vertical position of their first word
        sorted_lines = sorted(
            lines.items(), key=lambda item: self._words[item[1][0]][1])

        # Find the line closest to py
        best_line_indices = None
        best_y_dist = float('inf')

        for _key, indices in sorted_lines:
            # Compute line vertical bounds from all words in line
            line_y0 = min(self._words[i][1] for i in indices)
            line_y1 = max(self._words[i][3] for i in indices)

            # Point is within the line's vertical range
            if line_y0 <= py <= line_y1:
                best_line_indices = indices
                break

            # Calculate vertical distance
            if py < line_y0:
                dist = line_y0 - py
            else:
                dist = py - line_y1

            if dist < best_y_dist:
                best_y_dist = dist
                best_line_indices = indices

        if best_line_indices is None:
            return -1

        # Sort words on the line by x position
        sorted_line = sorted(
            best_line_indices, key=lambda i: self._words[i][0])

        # Find best word on the line by x position
        best_idx = sorted_line[0]
        best_x_dist = float('inf')

        for idx in sorted_line:
            w = self._words[idx]
            x0, x1 = w[0], w[2]

            # Point is within the word's horizontal range
            if x0 <= px <= x1:
                return idx

            dist = min(abs(px - x0), abs(px - x1))
            if dist < best_x_dist:
                best_x_dist = dist
                best_idx = idx

        return best_idx

    def _update_selection_rects(self):
        """Recompute per-line selection highlight rects from selected word indices."""
        if self._start_word_idx < 0 or self._end_word_idx < 0:
            self._selection_rects.clear()
            self._selected_indices.clear()
            return

        # Determine selection range in reading order
        lo = min(self._start_word_idx, self._end_word_idx)
        hi = max(self._start_word_idx, self._end_word_idx)
        self._selected_indices = list(range(lo, hi + 1))

        zoom = self._zoom

        # Group selected words by line for per-line highlight rectangles
        line_groups = {}
        for idx in self._selected_indices:
            w = self._words[idx]
            key = (w[5], w[6])
            if key not in line_groups:
                line_groups[key] = []
            line_groups[key].append(w)

        self._selection_rects.clear()
        for key in sorted(line_groups.keys()):
            words = line_groups[key]
            x0 = min(w[0] for w in words) * zoom
            y0 = min(w[1] for w in words) * zoom
            x1 = max(w[2] for w in words) * zoom
            y1 = max(w[3] for w in words) * zoom
            self._selection_rects.append(QRect(
                int(x0), int(y0), int(x1 - x0), int(y1 - y0)
            ))

    def _get_selected_text_and_rects(self) -> Tuple[str, List[Tuple[float, float, float, float]]]:
        """Get the selected text and word bounding boxes in page coordinates."""
        if not self._selected_indices:
            return "", []

        text_parts = []
        text_rects = []
        prev_line_key = None

        for idx in sorted(self._selected_indices):
            w = self._words[idx]
            line_key = (w[5], w[6])

            # Add newline between different lines, space between words on same line
            if prev_line_key is not None and prev_line_key != line_key:
                text_parts.append("\n")
            elif prev_line_key is not None:
                text_parts.append(" ")

            text_parts.append(w[4])
            text_rects.append((w[0], w[1], w[2], w[3]))
            prev_line_key = line_key

        return "".join(text_parts), text_rects

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._pixmap:
            self._is_selecting = True
            self._start_word_idx = self._find_word_at_pos(event.pos())
            self._end_word_idx = self._start_word_idx
            self._external_text_rects.clear()
            self._update_selection_rects()
            self.selection_started.emit()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_selecting and self._pixmap:
            self._end_word_idx = self._find_word_at_pos(event.pos())
            self._update_selection_rects()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._is_selecting:
            self._is_selecting = False
            text, text_rects = self._get_selected_text_and_rects()
            if text.strip():
                self.text_selected.emit(text, text_rects)
            else:
                self._clear_selection_internal()
            self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._pixmap:
            painter.drawPixmap(0, 0, self._pixmap)

        # Draw annotation highlights
        for qrect, color in self._highlight_rects:
            highlight_color = QColor(color)
            highlight_color.setAlpha(60)
            painter.fillRect(qrect, highlight_color)

        # Draw external text highlights (e.g., search results)
        if self._external_text_rects:
            ext_color = QColor(0, 120, 215, 80)
            for qrect in self._external_text_rects:
                painter.fillRect(qrect, ext_color)

        # Draw text-flow selection highlights (per-line rects)
        if self._selection_rects:
            sel_color = QColor(0, 120, 215, 80)
            for qrect in self._selection_rects:
                painter.fillRect(qrect, sel_color)

        painter.end()


class PDFViewerWidget(QScrollArea):
    """Scrollable PDF viewer with page display and text-flow selection."""

    # bounding_rect, text, text_rects
    selection_made = Signal(tuple, str, list)
    page_clicked = Signal(QPoint)
    page_up_requested = Signal()
    page_down_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_widget = PDFPageWidget()
        self.setWidget(self._page_widget)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignCenter)

        # Dark theme styling
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6a6a6a;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
        """)

        self._page_widget.text_selected.connect(self._on_text_selected)

    def display_page(self, image_data: bytes, zoom: float = 1.0, words: list = None):
        """Display a page from image data."""
        if not image_data:
            self._page_widget.clear()
            return
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        self._page_widget.set_page(pixmap, zoom, words)

    def display_pixmap(self, pixmap: QPixmap, zoom: float = 1.0, words: list = None):
        """Display a page from pixmap."""
        self._page_widget.set_page(pixmap, zoom, words)

    def clear(self):
        self._page_widget.clear()

    def set_highlights(self, rects):
        self._page_widget.set_highlights(rects)

    def clear_selection(self):
        self._page_widget.clear_selection()

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for page navigation."""
        # Check if at scroll boundaries
        vbar = self.verticalScrollBar()
        at_top = vbar.value() <= vbar.minimum()
        at_bottom = vbar.value() >= vbar.maximum()

        delta = event.angleDelta().y()

        if delta > 0 and at_top:
            # Scroll up at top - go to previous page
            self.page_up_requested.emit()
            event.accept()
            return
        elif delta < 0 and at_bottom:
            # Scroll down at bottom - go to next page
            self.page_down_requested.emit()
            event.accept()
            return

        # Normal scroll behavior
        super().wheelEvent(event)

    def _on_text_selected(self, text: str, text_rects: list):
        """Handle text selection from page widget."""
        if not text or not text_rects:
            return
        # Compute bounding rect from text_rects (page coordinates)
        x0 = min(r[0] for r in text_rects)
        y0 = min(r[1] for r in text_rects)
        x1 = max(r[2] for r in text_rects)
        y1 = max(r[3] for r in text_rects)
        # Scale to display coordinates for the bounding rect tuple
        zoom = self._page_widget._zoom
        rect_tuple = (x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom)
        self.selection_made.emit(rect_tuple, text, text_rects)
