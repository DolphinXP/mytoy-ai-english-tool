"""
Utility functions for PDFReader.
"""
import os
import re
from typing import Tuple, List


def normalize_path(path: str) -> str:
    """
    Normalize file path for consistent storage and comparison.

    Args:
        path: File path to normalize

    Returns:
        Normalized absolute path
    """
    if not path:
        return ""
    return os.path.normpath(os.path.abspath(path))


def clean_selected_text(text: str) -> str:
    """
    Clean up text selected from PDF.

    Args:
        text: Raw selected text

    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    # Replace various whitespace with single space
    text = re.sub(r'[\n\r\t]+', ' ', text)

    # Remove extra spaces
    text = re.sub(r' +', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def rect_contains_point(rect: Tuple[float, float, float, float],
                        x: float, y: float) -> bool:
    """
    Check if a rectangle contains a point.

    Args:
        rect: (x0, y0, x1, y1) rectangle coordinates
        x: Point x coordinate
        y: Point y coordinate

    Returns:
        True if point is inside rectangle
    """
    x0, y0, x1, y1 = rect
    return x0 <= x <= x1 and y0 <= y <= y1


def rects_overlap(rect1: Tuple[float, float, float, float],
                  rect2: Tuple[float, float, float, float]) -> bool:
    """
    Check if two rectangles overlap.

    Args:
        rect1: First rectangle (x0, y0, x1, y1)
        rect2: Second rectangle (x0, y0, x1, y1)

    Returns:
        True if rectangles overlap
    """
    x0_1, y0_1, x1_1, y1_1 = rect1
    x0_2, y0_2, x1_2, y1_2 = rect2

    # Check for no overlap conditions
    if x1_1 < x0_2 or x1_2 < x0_1:
        return False
    if y1_1 < y0_2 or y1_2 < y0_1:
        return False

    return True


def merge_rects(rects: List[Tuple[float, float, float, float]]
                ) -> Tuple[float, float, float, float]:
    """
    Merge multiple rectangles into a bounding rectangle.

    Args:
        rects: List of rectangles

    Returns:
        Bounding rectangle containing all input rectangles
    """
    if not rects:
        return (0, 0, 0, 0)

    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[2] for r in rects)
    y1 = max(r[3] for r in rects)

    return (x0, y0, x1, y1)


def format_page_number(page: int, total: int) -> str:
    """
    Format page number for display.

    Args:
        page: Current page (0-indexed)
        total: Total pages

    Returns:
        Formatted string like "Page 1 / 10"
    """
    return f"Page {page + 1} / {total}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
