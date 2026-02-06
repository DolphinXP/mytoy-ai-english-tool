"""
AI-TTS Application Entry Point
Simplified main.py using refactored architecture
"""
import sys
from core.app import MainApp


if __name__ == "__main__":
    main_app = MainApp()
    sys.exit(main_app.run())
