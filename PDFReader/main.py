"""
Application entry point for PDFReader.
"""
import sys
from pathlib import Path

# Add parent directory for shared imports BEFORE other imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from PDFReader.ui.main_window import MainWindow


def main():
    """Main entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Set application info
    app.setApplicationName("PDF Reader")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AI-TTS")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Handle command line argument for opening file
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if Path(file_path).exists() and file_path.lower().endswith('.pdf'):
            window.open_file(file_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
