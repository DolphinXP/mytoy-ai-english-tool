"""
PDF viewer widget with text selection support.
"""
from typing import Optional, Tuple, List, Callable
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QMouseEvent, QPaintEvent, QWheelEvent


class PDFPageWidget(QWidget):
    """Widget displaying a single PDF page with selection overlay."""

    selection_started = Signal()
    selection_changed = Signal(QRect)
    selection_finished = Signal(QRect)
    text_selected = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._zoom: float = 1.0
        self._is_selecting: bool = False
        self._selection_start: QPoint = QPoint()
        self._selection_rect: QRect = QRect()
        self._highlight_rects: List[Tuple[QRect, QColor]] = []
        self._text_rects: List[QRect] = []

        self.setMouseTracking(True)
        self.setCursor(Qt.IBeamCursor)  # Text cursor for selection

    def set_page(self, pixmap: QPixmap, zoom: float = 1.0):
        """Set the page pixmap to display."""
        self._pixmap = pixmap
        self._zoom = zoom
        self._selection_rect = QRect()
        self._text_rects.clear()
        if pixmap:
            self.setFixedSize(pixmap.size())
        self.update()

    def clear(self):
        """Clear the page display."""
        self._pixmap = None
        self._selection_rect = QRect()
        self._highlight_rects.clear()
        self._text_rects.clear()
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
        """Set text selection rectangles for highlighting."""
        self._text_rects.clear()
        for rect_tuple in rects:
            x0, y0, x1, y1 = rect_tuple
            qrect = QRect(
                int(x0 * self._zoom), int(y0 * self._zoom),
                int((x1 - x0) * self._zoom), int((y1 - y0) * self._zoom)
            )
            self._text_rects.append(qrect)
        self.update()

    def get_selection_rect(self) -> QRect:
        return self._selection_rect

    def clear_selection(self):
        self._selection_rect = QRect()
        self._text_rects.clear()
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._pixmap:
            self._is_selecting = True
            self._selection_start = event.pos()
            self._selection_rect = QRect(self._selection_start, QSize())
            self._text_rects.clear()
            self.selection_started.emit()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_selecting and self._pixmap:
            self._selection_rect = QRect(self._selection_start, event.pos()).normalized()
            self.selection_changed.emit(self._selection_rect)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._is_selecting:
            self._is_selecting = False
            if self._selection_rect.width() > 5 and self._selection_rect.height() > 5:
                self.selection_finished.emit(self._selection_rect)
            else:
                self._selection_rect = QRect()
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

        # Draw text selection highlights
        if self._text_rects:
            selection_color = QColor(0, 120, 215, 80)
            for qrect in self._text_rects:
                painter.fillRect(qrect, selection_color)

        # Draw selection rectangle
        if not self._selection_rect.isNull():
            fill_color = QColor(0, 120, 215, 40)
            painter.fillRect(self._selection_rect, fill_color)
            pen = QPen(QColor(0, 120, 215), 2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self._selection_rect)

        painter.end()


class PDFViewerWidget(QScrollArea):
    """Scrollable PDF viewer with page display and selection."""

    selection_made = Signal(tuple, str, list)  # rect, text, text_rects
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

        self._page_widget.selection_finished.connect(self._on_selection_finished)
        self._text_extractor: Optional[Callable] = None

    def set_text_extractor(self, extractor: Callable):
        """Set callback for text extraction."""
        self._text_extractor = extractor

    def display_page(self, image_data: bytes, zoom: float = 1.0):
        """Display a page from image data."""
        if not image_data:
            self._page_widget.clear()
            return
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        self._page_widget.set_page(pixmap, zoom)

    def display_pixmap(self, pixmap: QPixmap, zoom: float = 1.0):
        """Display a page from pixmap."""
        self._page_widget.set_page(pixmap, zoom)

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

    def _on_selection_finished(self, rect: QRect):
        if self._text_extractor:
            rect_tuple = (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
            text, text_rects = self._text_extractor(rect_tuple)
            if text:
                self._page_widget.set_text_selection_rects(text_rects)
                self.selection_made.emit(rect_tuple, text, text_rects)
