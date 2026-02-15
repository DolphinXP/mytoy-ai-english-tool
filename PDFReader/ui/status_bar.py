"""
Status bar widget for PDFReader.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt


class StatusBarWidget(QWidget):
    """Status bar showing document info and progress."""

    def __init__(self, parent=None):
        """Initialize status bar."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the status bar UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #007acc;
                border-top: 1px solid #005a9e;
            }
            QLabel {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 11px;
            }
            QProgressBar {
                background-color: #005a9e;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #ffffff;
                border-radius: 2px;
            }
        """)
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(16)

        # Document info
        self._doc_label = QLabel("No document loaded")
        layout.addWidget(self._doc_label)

        layout.addStretch()

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setFixedWidth(150)
        self._progress.setFixedHeight(16)
        self._progress.setTextVisible(True)
        self._progress.hide()
        layout.addWidget(self._progress)

        # Status message
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        # Annotation count
        self._annotation_label = QLabel("")
        layout.addWidget(self._annotation_label)

    def set_document_info(self, file_path: str, page_count: int):
        """Set document information."""
        if file_path:
            # Show just filename
            import os
            filename = os.path.basename(file_path)
            self._doc_label.setText(f"{filename} ({page_count} pages)")
        else:
            self._doc_label.setText("No document loaded")

    def set_status(self, message: str):
        """Set status message."""
        self._status_label.setText(message)

    def clear_status(self):
        """Clear status message."""
        self._status_label.setText("")

    def set_annotation_count(self, count: int):
        """Set annotation count display."""
        if count > 0:
            self._annotation_label.setText(f"{count} annotation{'s' if count != 1 else ''}")
        else:
            self._annotation_label.setText("")

    def show_progress(self, value: int = 0, maximum: int = 100):
        """Show progress bar."""
        self._progress.setMaximum(maximum)
        self._progress.setValue(value)
        self._progress.show()

    def update_progress(self, value: int):
        """Update progress value."""
        self._progress.setValue(value)

    def hide_progress(self):
        """Hide progress bar."""
        self._progress.hide()
