"""
Icon management for UI elements.
"""
import os
import sys
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase


class IconManager:
    """Manages icons and glyphs for the UI."""

    def __init__(self):
        self._is_windows_11 = self._check_windows_11()
        self._menu_icon_font = self._get_menu_icon_font()
        self._icons = self._get_icon_texts()
        self._menu_glyphs = self._get_menu_glyphs()
        self._button_glyphs = self._get_button_glyphs()

    def _check_windows_11(self):
        """Check if running on Windows 11 or newer."""
        if os.name != "nt":
            return True
        try:
            return sys.getwindowsversion().build >= 22000
        except Exception:
            return True

    def _get_menu_icon_font(self):
        """Get the font family for menu icons."""
        if os.name != "nt":
            return ""
        families = set(QFontDatabase.families())
        if "Segoe MDL2 Assets" in families:
            return "Segoe MDL2 Assets"
        return ""

    def _get_icon_texts(self):
        """Get icon text mappings based on OS version."""
        if self._is_windows_11:
            return {
                "power": "⏻",
                "dictionary": "📖",
                "close": "✕",
                "search": "🔍",
                "translating": "🔄",
                "play": "▶",
                "stop": "⏸",
                "audio": "🔊",
                "ready": "✅",
                "error": "❌",
                "copy": "📋",
                "edit": "✏️",
                "restore": "↶",
                "translate": "🌐",
            }

        # Windows 10 - use text-only labels
        return {
            "power": "",
            "dictionary": "",
            "close": "",
            "search": "",
            "translating": "",
            "play": "",
            "stop": "",
            "audio": "",
            "ready": "",
            "error": "",
            "copy": "",
            "edit": "",
            "restore": "",
            "translate": "",
        }

    def _get_menu_glyphs(self):
        """Get Segoe MDL2 Assets glyphs for menu items."""
        if not self._menu_icon_font:
            return {}
        return {
            "copy": "\uE8C8",
            "select_all": "\uE8B3",
            "translate": "\uE721",
            "search": "\uE99A",
        }

    def _get_button_glyphs(self):
        """Get Segoe MDL2 Assets glyphs for buttons."""
        if not self._menu_icon_font:
            return {}
        return {
            "power": "\uE7E8",
            "play": "\uE768",
            "stop": "\uE769",
            "close": "\uE711",
            "search": "\uE99A",
        }

    def get_icon_label(self, key, text):
        """
        Get a label with icon prefix.

        Args:
            key: Icon key
            text: Text to append after icon

        Returns:
            Formatted string with icon and text
        """
        icon = self._icons.get(key, "")
        if icon:
            return f"{icon} {text}"
        return text

    def make_menu_icon(self, glyph_key):
        """
        Create a menu icon from a glyph.

        Args:
            glyph_key: Key for the glyph

        Returns:
            QIcon instance
        """
        glyph = self._menu_glyphs.get(glyph_key, "")
        if not glyph or not self._menu_icon_font:
            return QIcon()

        font = QFont(self._menu_icon_font, 12)
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, glyph)
        painter.end()
        return QIcon(pixmap)

    def make_button_icon(self, glyph_key):
        """
        Create a button icon from a glyph.

        Args:
            glyph_key: Key for the glyph

        Returns:
            QIcon instance
        """
        glyph = self._button_glyphs.get(glyph_key, "")
        if not glyph or not self._menu_icon_font:
            return QIcon()

        font = QFont(self._menu_icon_font, 14)
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, glyph)
        painter.end()
        return QIcon(pixmap)

    def set_button_icon(self, button, glyph_key):
        """
        Set icon on a button.

        Args:
            button: QPushButton instance
            glyph_key: Key for the glyph
        """
        icon = self.make_button_icon(glyph_key)
        if not icon.isNull():
            button.setIcon(icon)
            button.setIconSize(button.iconSize())
        else:
            button.setIcon(QIcon())

    def has_menu_icons(self):
        """Check if menu icons are available."""
        return bool(self._menu_icon_font)

    def has_button_icons(self):
        """Check if button icons are available."""
        return bool(self._menu_icon_font)


# Global icon manager instance
_icon_manager = None


def get_icon_manager():
    """Get the global icon manager instance."""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager
