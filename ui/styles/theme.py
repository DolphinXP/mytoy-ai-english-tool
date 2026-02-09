"""
Modern UI theme with colors, fonts, and spacing constants.
"""
from PySide6.QtGui import QFont


class Theme:
    """Modern UI theme constants."""

    # Color Palette
    class Colors:
        # Primary colors
        PRIMARY = "#2563eb"  # Modern blue
        PRIMARY_HOVER = "#1d4ed8"
        PRIMARY_LIGHT = "#dbeafe"

        # Secondary colors
        SECONDARY = "#64748b"  # Slate gray
        SECONDARY_HOVER = "#475569"
        SECONDARY_LIGHT = "#f1f5f9"

        # Success colors
        SUCCESS = "#10b981"  # Green
        SUCCESS_HOVER = "#059669"
        SUCCESS_LIGHT = "#d1fae5"

        # Warning colors
        WARNING = "#f59e0b"  # Amber
        WARNING_HOVER = "#d97706"
        WARNING_LIGHT = "#fef3c7"

        # Danger colors
        DANGER = "#ef4444"  # Red
        DANGER_HOVER = "#dc2626"
        DANGER_LIGHT = "#fee2e2"

        # Neutral colors
        WHITE = "#ffffff"
        BLACK = "#000000"
        GRAY_50 = "#f9fafb"
        GRAY_100 = "#f3f4f6"
        GRAY_200 = "#e5e7eb"
        GRAY_300 = "#d1d5db"
        GRAY_400 = "#9ca3af"
        GRAY_500 = "#6b7280"
        GRAY_600 = "#4b5563"
        GRAY_700 = "#374151"
        GRAY_800 = "#1f2937"
        GRAY_900 = "#111827"

        # Background colors (Dark theme friendly)
        BG_PRIMARY = GRAY_800
        BG_SECONDARY = GRAY_700
        BG_TERTIARY = GRAY_600

        # Text colors (High contrast for dark backgrounds)
        TEXT_PRIMARY = WHITE
        TEXT_SECONDARY = GRAY_300
        TEXT_TERTIARY = GRAY_400
        TEXT_INVERSE = GRAY_900

        # Border colors (Dark theme friendly)
        BORDER_LIGHT = GRAY_600
        BORDER_MEDIUM = GRAY_500
        BORDER_DARK = GRAY_400

    # Typography
    class Fonts:
        FAMILY_PRIMARY = "Segoe UI"
        FAMILY_SECONDARY = "Microsoft YaHei"
        FAMILY_MONOSPACE = "Consolas"

        SIZE_SMALL = 9
        SIZE_NORMAL = 10
        SIZE_MEDIUM = 11
        SIZE_LARGE = 12
        SIZE_XLARGE = 14
        SIZE_TITLE = 16

        WEIGHT_NORMAL = QFont.Weight.Normal
        WEIGHT_MEDIUM = QFont.Weight.Medium
        WEIGHT_BOLD = QFont.Weight.Bold

    # Spacing (8px grid system)
    class Spacing:
        XS = 4
        SM = 8
        MD = 16
        LG = 24
        XL = 32
        XXL = 48

    # Border Radius
    class Radius:
        NONE = 0
        SM = 3
        MD = 5
        LG = 8
        XL = 12
        FULL = 9999

    # Shadows
    class Shadows:
        NONE = "none"
        SM = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
        MD = "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
        LG = "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
        XL = "0 20px 25px -5px rgba(0, 0, 0, 0.1)"

    # Button Styles
    @staticmethod
    def button_style(color_type="primary"):
        """
        Get button stylesheet for a specific color type.

        Args:
            color_type: One of 'primary', 'secondary', 'success', 'warning', 'danger'

        Returns:
            CSS stylesheet string
        """
        colors = {
            "primary": (Theme.Colors.PRIMARY, Theme.Colors.PRIMARY_HOVER),
            "secondary": (Theme.Colors.SECONDARY, Theme.Colors.SECONDARY_HOVER),
            "success": (Theme.Colors.SUCCESS, Theme.Colors.SUCCESS_HOVER),
            "warning": (Theme.Colors.WARNING, Theme.Colors.WARNING_HOVER),
            "danger": (Theme.Colors.DANGER, Theme.Colors.DANGER_HOVER),
        }

        bg_color, hover_color = colors.get(color_type, colors["primary"])

        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {Theme.Colors.WHITE};
                border: none;
                padding: {Theme.Spacing.SM}px {Theme.Spacing.MD}px;
                border-radius: {Theme.Radius.SM}px;
                font-size: {Theme.Fonts.SIZE_NORMAL}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
                padding-top: {Theme.Spacing.SM + 1}px;
            }}
            QPushButton:disabled {{
                background-color: {Theme.Colors.GRAY_600};
                color: {Theme.Colors.GRAY_400};
            }}
        """

    # Text Edit Styles
    @staticmethod
    def text_edit_style():
        """Get text edit stylesheet."""
        return f"""
            QTextEdit, QTextBrowser {{
                background-color: {Theme.Colors.BG_PRIMARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.MD}px;
                padding: {Theme.Spacing.SM}px;
                font-size: {Theme.Fonts.SIZE_XLARGE}px;
                selection-background-color: {Theme.Colors.PRIMARY};
                selection-color: {Theme.Colors.WHITE};
            }}
            QTextEdit:focus, QTextBrowser:focus {{
                border: 1px solid {Theme.Colors.PRIMARY};
            }}
            QTextEdit:read-only, QTextBrowser:read-only {{
                background-color: {Theme.Colors.BG_SECONDARY};
            }}
        """

    # Label Styles
    @staticmethod
    def label_style(bold=False, size="normal"):
        """Get label stylesheet."""
        font_size = {
            "small": Theme.Fonts.SIZE_SMALL,
            "normal": Theme.Fonts.SIZE_NORMAL,
            "medium": Theme.Fonts.SIZE_MEDIUM,
            "large": Theme.Fonts.SIZE_LARGE,
            "title": Theme.Fonts.SIZE_TITLE,
        }.get(size, Theme.Fonts.SIZE_NORMAL)

        weight = "bold" if bold else "normal"

        return f"""
            QLabel {{
                color: {Theme.Colors.TEXT_PRIMARY};
                font-size: {font_size}px;
                font-weight: {weight};
            }}
        """

    # Progress Bar Styles
    @staticmethod
    def progress_bar_style():
        """Get progress bar stylesheet."""
        return f"""
            QProgressBar {{
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.SM}px;
                background-color: {Theme.Colors.BG_SECONDARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.Colors.PRIMARY};
                border-radius: {Theme.Radius.SM}px;
            }}
        """

    # Menu Styles
    @staticmethod
    def menu_style():
        """Get menu stylesheet."""
        return f"""
            QMenu {{
                background-color: {Theme.Colors.BG_PRIMARY};
                color: {Theme.Colors.TEXT_PRIMARY};
                border: 1px solid {Theme.Colors.BORDER_LIGHT};
                border-radius: {Theme.Radius.MD}px;
                padding: {Theme.Spacing.XS}px;
            }}
            QMenu::item {{
                color: {Theme.Colors.TEXT_PRIMARY};
                padding: {Theme.Spacing.SM}px {Theme.Spacing.MD}px;
                border-radius: {Theme.Radius.SM}px;
            }}
            QMenu::item:selected {{
                background-color: {Theme.Colors.PRIMARY};
                color: {Theme.Colors.WHITE};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {Theme.Colors.BORDER_LIGHT};
                margin: {Theme.Spacing.XS}px 0;
            }}
        """
