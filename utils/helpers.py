"""
Common helper functions for text processing and language detection.
"""
import re


def clean_text(text):
    """
    Clean up copied text by removing extra whitespace and fixing formatting.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    # Replace newlines with spaces
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    # Remove extra spaces
    while "  " in text:
        text = text.replace("  ", " ")

    # Strip leading/trailing whitespace
    text = text.strip()

    # Add period if missing
    if text and not text.endswith(('.', '!', '?', ';', ':')):
        text += '.'

    return text


def is_english(text):
    """
    Check if text is primarily English (Latin characters).

    Args:
        text: Text to check

    Returns:
        True if text is primarily English, False otherwise
    """
    if not text:
        return False

    # Count English/Latin letters vs Chinese characters
    latin_chars = sum(1 for c in text if (
        '\u0020' <= c <= '\u007F') or ('\u0080' <= c <= '\u00FF'))
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

    # If there are Chinese characters, it's likely Chinese text
    if chinese_chars > 0:
        return False

    # Check if majority of alphabetic characters are Latin
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0:
        return False

    latin_ratio = latin_chars / total_alpha
    return latin_ratio > 0.5


def format_time(seconds):
    """
    Format seconds into MM:SS format.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (MM:SS)
    """
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def truncate_text(text, max_length=100, suffix="..."):
    """
    Truncate text to a maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        Truncated text string
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
