"""
Helper utilities for Quick Translation app.
"""
import os
import sys
from pathlib import Path
from typing import Optional


def get_app_directory() -> Path:
    """
    Get the application directory.

    Returns:
        Path to the application directory
    """
    return Path(__file__).parent.parent


def get_config_directory() -> Path:
    """
    Get the configuration directory.

    Returns:
        Path to the configuration directory
    """
    # Use user's home directory for config
    config_dir = Path.home() / ".quick_translate"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.

    Args:
        relative_path: Relative path to resource

    Returns:
        Absolute path to resource
    """
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = get_app_directory()

    return base_path / relative_path


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform.startswith('win')


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform.startswith('darwin')


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith('linux')


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to specified length.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def format_timestamp(timestamp: str) -> str:
    """
    Format ISO timestamp to readable format.

    Args:
        timestamp: ISO format timestamp

    Returns:
        Formatted timestamp string
    """
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return timestamp


def validate_hotkey(hotkey: str) -> bool:
    """
    Validate hotkey combination format.

    Args:
        hotkey: Hotkey combination string

    Returns:
        True if valid, False otherwise
    """
    if not hotkey:
        return False

    # Check for valid modifiers
    valid_modifiers = ['<ctrl>', '<alt>', '<shift>', '<cmd>', '<super>']
    parts = hotkey.lower().split('+')

    # At least one modifier and one key
    if len(parts) < 2:
        return False

    # Check if at least one part is a modifier
    has_modifier = any(part in valid_modifiers for part in parts)
    if not has_modifier:
        return False

    return True


def get_system_info() -> dict:
    """
    Get system information.

    Returns:
        Dictionary with system information
    """
    import platform

    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.machine()
    }
