"""
Quick Translation App - Main Entry Point

A lightweight, always-accessible translation tool that lives in the system tray
and provides instant English-to-Chinese translation via a global hotkey.
"""
import sys
from pathlib import Path

# Add QuickTranslate directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config import config
from core.app import QuickTranslateApp


def main():
    """Main entry point for the application."""
    # Create QApplication
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    # Create and run the main application
    main_app = QuickTranslateApp()
    exit_code = main_app.run()

    # Exit with the application's exit code
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
