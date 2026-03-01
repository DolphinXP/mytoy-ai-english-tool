"""
Annotation panel widget for displaying and managing annotations.
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from PDFReader.models.annotation import Annotation


class AnnotationCard(QFrame):
    """Card widget displaying a single annotation."""

    # Signals
    delete_clicked = Signal(str)  # annotation_id
    play_tts_clicked = Signal(str)  # annotation_id
    card_clicked = Signal(str)  # annotation_id

    def __init__(self, annotation: Annotation, parent=None):
        """Initialize annotation card."""
        super().__init__(parent)
        self._annotation = annotation
        self._setup_ui()

    def _setup_ui(self):
        """Set up the card UI."""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            AnnotationCard {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                margin: 4px;
            }
            AnnotationCard:hover {
                border-color: #0078d4;
                background-color: #363636;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Page number label
        page_label = QLabel(f"Page {self._annotation.page_number + 1}")
        page_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(page_label)

        # Selected text (original)
        if self._annotation.selected_text:
            original_label = QLabel("Original:")
            original_label.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold;")
            layout.addWidget(original_label)

            text_label = QLabel(self._truncate_text(self._annotation.selected_text, 100))
            text_label.setWordWrap(True)
            text_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            layout.addWidget(text_label)

        # Corrected text
        if self._annotation.corrected_text:
            corrected_label = QLabel("Corrected:")
            corrected_label.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold;")
            layout.addWidget(corrected_label)

            corrected_text = QLabel(self._truncate_text(self._annotation.corrected_text, 100))
            corrected_text.setWordWrap(True)
            corrected_text.setStyleSheet("color: #6cb6ff; font-size: 12px;")
            layout.addWidget(corrected_text)

        # Translation
        if self._annotation.translated_text:
            trans_label = QLabel("Translation:")
            trans_label.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold;")
            layout.addWidget(trans_label)

            trans_text = QLabel(self._truncate_text(self._annotation.translated_text, 150))
            trans_text.setWordWrap(True)
            trans_text.setStyleSheet("color: #7ee787; font-size: 12px;")
            layout.addWidget(trans_text)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        # TTS button
        if self._annotation.tts_audio_path:
            tts_btn = QPushButton("🔊")
            tts_btn.setFixedSize(28, 28)
            tts_btn.setToolTip("Play TTS")
            tts_btn.clicked.connect(lambda: self.play_tts_clicked.emit(self._annotation.id))
            btn_layout.addWidget(tts_btn)

        btn_layout.addStretch()

        # Delete button
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setToolTip("Delete annotation")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a2020;
                border-radius: 4px;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._annotation.id))
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def mousePressEvent(self, event):
        """Handle click to select annotation."""
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self._annotation.id)
        super().mousePressEvent(event)

    @property
    def annotation(self) -> Annotation:
        """Get the annotation."""
        return self._annotation


class AnnotationPanel(QWidget):
    """Panel for displaying and managing annotations."""

    # Signals
    annotation_selected = Signal(str)  # annotation_id
    annotation_deleted = Signal(str)  # annotation_id
    play_tts_requested = Signal(str)  # annotation_id

    def __init__(self, parent=None):
        """Initialize annotation panel."""
        super().__init__(parent)
        self._cards: dict[str, AnnotationCard] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #252526; border-bottom: 1px solid #333333;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Annotations")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self._count_label)

        header_layout.addStretch()

        layout.addWidget(header)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                border-radius: 5px;
            }
        """)

        # Container for cards
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(8, 8, 8, 8)
        self._container_layout.setSpacing(8)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        # Empty state label
        self._empty_label = QLabel("No annotations yet.\nSelect text in the PDF to create one.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #999999; padding: 20px;")
        self._container_layout.insertWidget(0, self._empty_label)

    def set_annotations(self, annotations: List[Annotation]):
        """
        Set the list of annotations to display.

        Args:
            annotations: List of Annotation objects
        """
        # Clear existing cards
        self.clear()

        # Add new cards
        for annotation in annotations:
            self._add_card(annotation)

        self._update_count()
        self._update_empty_state()

    def add_annotation(self, annotation: Annotation):
        """Add a single annotation."""
        self._add_card(annotation)
        self._update_count()
        self._update_empty_state()

    def update_annotation(self, annotation: Annotation):
        """Update an existing annotation card."""
        if annotation.id in self._cards:
            # Remove old card
            old_card = self._cards[annotation.id]
            self._container_layout.removeWidget(old_card)
            old_card.deleteLater()

            # Add updated card
            self._add_card(annotation)

    def remove_annotation(self, annotation_id: str):
        """Remove an annotation card."""
        if annotation_id in self._cards:
            card = self._cards.pop(annotation_id)
            self._container_layout.removeWidget(card)
            card.deleteLater()
            self._update_count()
            self._update_empty_state()

    def clear(self):
        """Clear all annotation cards."""
        for card in self._cards.values():
            self._container_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._update_count()
        self._update_empty_state()

    def _add_card(self, annotation: Annotation):
        """Add a card for an annotation."""
        card = AnnotationCard(annotation)
        card.card_clicked.connect(self.annotation_selected.emit)
        card.delete_clicked.connect(self.annotation_deleted.emit)
        card.play_tts_clicked.connect(self.play_tts_requested.emit)

        self._cards[annotation.id] = card

        # Insert before the stretch
        count = self._container_layout.count()
        self._container_layout.insertWidget(count - 1, card)

    def _update_count(self):
        """Update the count label."""
        self._count_label.setText(str(len(self._cards)))

    def _update_empty_state(self):
        """Show/hide empty state label."""
        self._empty_label.setVisible(len(self._cards) == 0)
