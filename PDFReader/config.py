"""
Configuration settings for PDFReader.
"""
from pathlib import Path


class Config:
    """Application configuration."""

    # Application info
    APP_NAME = "PDF Reader"
    APP_VERSION = "1.0.0"

    # Paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    ANNOTATIONS_DIR = DATA_DIR / "annotations"

    # PDF settings
    DEFAULT_ZOOM = 1.0
    MIN_ZOOM = 0.25
    MAX_ZOOM = 4.0
    ZOOM_STEP = 0.25

    # UI settings
    WINDOW_MIN_WIDTH = 1024
    WINDOW_MIN_HEIGHT = 768
    ANNOTATION_PANEL_WIDTH = 320

    # Ensure directories exist
    @classmethod
    def init_dirs(cls):
        """Create required directories."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.ANNOTATIONS_DIR.mkdir(exist_ok=True)


# Initialize on import
Config.init_dirs()
