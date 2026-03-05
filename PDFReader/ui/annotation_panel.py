"""
Annotation panel widget with embedded AI results display.

Contains an annotation list and a detail view that shows AI processing
results (correction, translation, explanation) for the selected annotation.
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QSizePolicy, QSplitter,
    QApplication, QSlider, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from PDFReader.models.annotation import Annotation


# ─── Annotation Card ──────────────────────────────────────────────────────────

class AnnotationCard(QFrame):
    """Card widget displaying a single annotation summary."""

    delete_clicked = Signal(str)  # annotation_id
    card_clicked = Signal(str)  # annotation_id

    def __init__(self, annotation: Annotation, parent=None):
        super().__init__(parent)
        self._annotation = annotation
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._update_style()
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Top row: page number + delete button
        top_row = QHBoxLayout()
        page_label = QLabel(f"Page {self._annotation.page_number + 1}")
        page_label.setStyleSheet(
            "color: #888888; font-size: 11px; background: transparent; border: none;")
        top_row.addWidget(page_label)
        top_row.addStretch()

        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 12px; color: #666666; }
            QPushButton:hover { background-color: #4a2020; border-radius: 4px; color: #ff6666; }
        """)
        delete_btn.clicked.connect(
            lambda: self.delete_clicked.emit(self._annotation.id))
        top_row.addWidget(delete_btn)
        layout.addLayout(top_row)

        # Selected text preview
        preview = self._annotation.selected_text[:80]
        if len(self._annotation.selected_text) > 80:
            preview += "..."
        text_label = QLabel(preview)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(
            "color: #e0e0e0; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(text_label)

        # Status indicator
        status_parts = []
        if self._annotation.corrected_text:
            status_parts.append("✓ Corrected")
        if self._annotation.translated_text:
            status_parts.append("✓ Translated")
        if self._annotation.explanation:
            status_parts.append("✓ Explained")

        if status_parts:
            status_label = QLabel("  ".join(status_parts))
            status_label.setStyleSheet(
                "color: #4ec9b0; font-size: 10px; background: transparent; border: none;")
            layout.addWidget(status_label)
        else:
            pending_label = QLabel("⏳ Processing...")
            pending_label.setStyleSheet(
                "color: #d7ba7d; font-size: 10px; background: transparent; border: none;")
            layout.addWidget(pending_label)

    def set_selected(self, selected: bool):
        """Set the selected visual state."""
        self._selected = selected
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                AnnotationCard {
                    background-color: #264f78;
                    border: 1px solid #0078d4;
                    border-radius: 6px;
                    margin: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                AnnotationCard {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    border-radius: 6px;
                    margin: 2px;
                }
                AnnotationCard:hover {
                    border-color: #0078d4;
                    background-color: #363636;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self._annotation.id)
        super().mousePressEvent(event)

    @property
    def annotation(self) -> Annotation:
        return self._annotation


# ─── Annotation Detail View ──────────────────────────────────────────────────

class AnnotationDetailView(QWidget):
    """Detail view showing AI results for a selected annotation."""

    copy_clicked = Signal(str)  # 'corrected' or 'translated'
    retranslate_clicked = Signal()
    explain_clicked = Signal()
    tts_clicked = Signal()
    tts_play_clicked = Signal()
    tts_stop_clicked = Signal()
    tts_settings_clicked = Signal()
    regenerate_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_annotation_id: str = ""
        self._corrected_text: str = ""
        self._translated_text: str = ""
        self._explanation: str = ""
        self._is_processing: bool = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Content container (shown when an annotation is selected)
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Original text
        content_layout.addWidget(self._section_label("Original Text"))
        self._original_display = self._create_text_display(80)
        content_layout.addWidget(self._original_display)

        # Corrected text
        corrected_header = QHBoxLayout()
        corrected_header.addWidget(self._section_label("Corrected"))
        self._copy_corrected_btn = self._small_btn("Copy")
        self._copy_corrected_btn.clicked.connect(
            lambda: self._copy_text('corrected'))
        corrected_header.addWidget(self._copy_corrected_btn)
        corrected_header.addStretch()
        content_layout.addLayout(corrected_header)

        self._corrected_display = self._create_text_display(100)
        content_layout.addWidget(self._corrected_display)

        # Translation
        trans_header = QHBoxLayout()
        trans_header.addWidget(self._section_label("Translation"))
        self._copy_trans_btn = self._small_btn("Copy")
        self._copy_trans_btn.clicked.connect(
            lambda: self._copy_text('translated'))
        trans_header.addWidget(self._copy_trans_btn)
        self._retranslate_btn = self._small_btn("Re-translate", max_width=110)
        self._retranslate_btn.clicked.connect(self.retranslate_clicked.emit)
        trans_header.addWidget(self._retranslate_btn)
        trans_header.addStretch()
        content_layout.addLayout(trans_header)

        self._translated_display = self._create_text_display(120)
        content_layout.addWidget(self._translated_display)

        # Explanation (stretches to fill ALL remaining space, renders markdown)
        explain_header = QHBoxLayout()
        explain_header.addWidget(self._section_label("Explanation"))
        self._explain_btn = self._small_btn("Explain")
        self._explain_btn.clicked.connect(self.explain_clicked.emit)
        explain_header.addWidget(self._explain_btn)
        explain_header.addStretch()
        content_layout.addLayout(explain_header)

        self._explain_display = self._create_markdown_display()
        # Always visible so it always occupies remaining space
        content_layout.addWidget(self._explain_display, 1)  # stretch factor 1

        # Status label
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("""
            QLabel {
                color: #888888; font-size: 11px;
                padding: 2px 8px;
                background-color: #252526;
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self._status_label)

        # TTS player controls
        tts_layout = QHBoxLayout()
        tts_layout.setSpacing(4)

        self._tts_btn = QPushButton("🔊 TTS")
        self._tts_btn.setFixedWidth(60)
        self._tts_btn.setStyleSheet(self._btn_style("primary"))
        self._tts_btn.clicked.connect(self.tts_clicked.emit)
        tts_layout.addWidget(self._tts_btn)

        self._tts_play_btn = QPushButton("▶")
        self._tts_play_btn.setFixedWidth(28)
        self._tts_play_btn.setStyleSheet(self._btn_style("secondary"))
        self._tts_play_btn.clicked.connect(self.tts_play_clicked.emit)
        self._tts_play_btn.hide()
        tts_layout.addWidget(self._tts_play_btn)

        self._tts_stop_btn = QPushButton("⏹")
        self._tts_stop_btn.setFixedWidth(28)
        self._tts_stop_btn.setStyleSheet(self._btn_style("secondary"))
        self._tts_stop_btn.clicked.connect(self.tts_stop_clicked.emit)
        self._tts_stop_btn.hide()
        tts_layout.addWidget(self._tts_stop_btn)

        self._tts_progress = QProgressBar()
        self._tts_progress.setMaximumHeight(14)
        self._tts_progress.setTextVisible(False)
        self._tts_progress.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e1e;
                border: 1px solid #444444;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        self._tts_progress.hide()
        tts_layout.addWidget(self._tts_progress, 1)

        # TTS settings button
        self._tts_settings_btn = QPushButton("⚙")
        self._tts_settings_btn.setFixedWidth(28)
        self._tts_settings_btn.setToolTip("TTS Settings")
        self._tts_settings_btn.setStyleSheet(self._btn_style("secondary"))
        self._tts_settings_btn.clicked.connect(self.tts_settings_clicked.emit)
        tts_layout.addWidget(self._tts_settings_btn)

        content_layout.addLayout(tts_layout)

        # Regenerate button
        regen_layout = QHBoxLayout()
        regen_layout.setSpacing(6)

        self._regenerate_btn = QPushButton("🔄 Regenerate")
        self._regenerate_btn.setStyleSheet(self._btn_style("secondary"))
        self._regenerate_btn.clicked.connect(self.regenerate_clicked.emit)
        regen_layout.addWidget(self._regenerate_btn)

        regen_layout.addStretch()
        content_layout.addLayout(regen_layout)

        layout.addWidget(self._content_widget, 1)

        # Empty state
        self._empty_label = QLabel("Select an annotation to view details")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #666666; padding: 20px;")
        layout.addWidget(self._empty_label)

        # Initially show empty state
        self._content_widget.hide()

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setStyleSheet("color: #888888;")
        return label

    def _small_btn(self, text: str, max_width: int = 70) -> QPushButton:
        btn = QPushButton(text)
        btn.setMaximumWidth(max_width)
        btn.setStyleSheet(self._btn_style("secondary"))
        return btn

    def _btn_style(self, style_type: str) -> str:
        if style_type == "primary":
            return """
                QPushButton {
                    background-color: #0078d4; color: white;
                    border-radius: 4px; padding: 5px 10px; border: none; font-size: 12px;
                }
                QPushButton:hover { background-color: #1084d8; }
                QPushButton:disabled { background-color: #555555; color: #888888; }
            """
        return """
            QPushButton {
                background-color: #3c3c3c; color: #e0e0e0;
                border-radius: 4px; padding: 5px 10px;
                border: 1px solid #555555; font-size: 12px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #2d2d2d; color: #666666; }
        """

    def _create_text_display(self, max_height: int) -> QTextEdit:
        display = QTextEdit()
        display.setReadOnly(True)
        display.setMaximumHeight(max_height)
        display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: #e0e0e0;
            }
        """)
        return display

    def _create_markdown_display(self) -> QTextEdit:
        """Create a text display that renders markdown and stretches to fill space."""
        display = QTextEdit()
        display.setReadOnly(True)
        display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                color: #e0e0e0;
            }
        """)
        display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return display

    def _copy_text(self, text_type: str):
        clipboard = QApplication.clipboard()
        if text_type == 'corrected':
            clipboard.setText(self._corrected_text)
        elif text_type == 'translated':
            clipboard.setText(self._translated_text)
        self.copy_clicked.emit(text_type)

    # ─── Public API ───────────────────────────────────────────────────────

    @property
    def current_annotation_id(self) -> str:
        return self._current_annotation_id

    def show_annotation(self, annotation: Annotation):
        """Display an annotation's stored AI results."""
        self._current_annotation_id = annotation.id
        self._empty_label.hide()
        self._content_widget.show()

        self._original_display.setPlainText(annotation.selected_text)
        self._corrected_text = annotation.corrected_text
        self._corrected_display.setPlainText(annotation.corrected_text or "")
        self._translated_text = annotation.translated_text
        self._translated_display.setPlainText(annotation.translated_text or "")
        self._explanation = annotation.explanation
        if annotation.explanation:
            self._explain_display.setMarkdown(annotation.explanation)
        else:
            self._explain_display.clear()

        self._status_label.setText("Ready")
        self.set_processing(False)

    def show_empty(self):
        """Show empty state."""
        self._current_annotation_id = ""
        self._content_widget.hide()
        self._empty_label.show()

    def set_original_text(self, text: str):
        self._original_display.setPlainText(text)

    def set_corrected_text(self, text: str):
        self._corrected_text = text
        self._corrected_display.setPlainText(text)

    def append_corrected_chunk(self, chunk: str):
        current = self._corrected_display.toPlainText()
        if current == "Correcting...":
            current = ""
        self._corrected_display.setPlainText(current + chunk)
        self._corrected_text = current + chunk

    def set_translated_text(self, text: str):
        self._translated_text = text
        self._translated_display.setPlainText(text)

    def append_translated_chunk(self, chunk: str):
        current = self._translated_display.toPlainText()
        if current == "Translating...":
            current = ""
        self._translated_display.setPlainText(current + chunk)
        self._translated_text = current + chunk

    def set_explanation(self, text: str):
        self._explanation = text
        self._explain_display.setMarkdown(text)

    def append_explain_chunk(self, chunk: str):
        if self._explanation == "" or self._explanation == "Explaining...":
            self._explanation = ""
        self._explanation += chunk
        self._explain_display.setMarkdown(self._explanation)

    def set_status(self, status: str):
        self._status_label.setText(status)

    def set_processing(self, processing: bool):
        self._is_processing = processing
        self._retranslate_btn.setEnabled(not processing)
        self._explain_btn.setEnabled(not processing)
        self._tts_btn.setEnabled(not processing)
        self._regenerate_btn.setEnabled(not processing)

    def start_correction(self):
        self._corrected_display.setPlainText("Correcting...")
        self.set_status("Correcting text...")
        self.set_processing(True)

    def start_translation(self):
        self._translated_display.setPlainText("Translating...")
        self.set_status("Translating...")

    def start_explanation(self):
        self._explanation = "Explaining..."
        self._explain_display.setPlainText("Explaining...")
        self.set_status("Generating explanation...")

    def finish_processing(self):
        self.set_status("Ready")
        self.set_processing(False)

    def get_corrected_text(self) -> str:
        return self._corrected_text

    def get_translated_text(self) -> str:
        return self._translated_text

    def get_explanation(self) -> str:
        return self._explanation

    def clear_results(self):
        self._corrected_text = ""
        self._translated_text = ""
        self._explanation = ""
        self._original_display.clear()
        self._corrected_display.clear()
        self._translated_display.clear()
        self._explain_display.clear()
        self.reset_tts_player()
        self.set_status("Ready")

    # ─── TTS Player UI ───────────────────────────────────────────────────

    def show_tts_generating(self):
        """Show TTS generating state."""
        self._tts_btn.setEnabled(False)
        self._tts_progress.show()
        self._tts_progress.setRange(0, 0)  # Indeterminate
        self._tts_play_btn.hide()
        self._tts_stop_btn.hide()

    def show_tts_ready(self, duration_seconds: int):
        """Show TTS ready-to-play state with controls."""
        self._tts_btn.setEnabled(True)
        self._tts_progress.show()
        self._tts_progress.setRange(0, max(1, duration_seconds))
        self._tts_progress.setValue(0)
        self._tts_play_btn.show()
        self._tts_play_btn.setText("⏸")  # Start playing immediately
        self._tts_stop_btn.show()

    def update_tts_progress(self, value: int, maximum: int = -1):
        """Update TTS playback progress."""
        if maximum >= 0:
            self._tts_progress.setMaximum(maximum)
        self._tts_progress.setValue(value)

    def set_tts_playing(self, playing: bool):
        """Update play button state based on whether audio is playing."""
        self._tts_play_btn.setEnabled(not playing)
        self._tts_stop_btn.setEnabled(playing)

    def reset_tts_player(self):
        """Reset TTS player to initial state."""
        self._tts_btn.setEnabled(True)
        self._tts_progress.hide()
        self._tts_progress.setValue(0)
        self._tts_play_btn.hide()
        self._tts_stop_btn.hide()


# ─── Annotation Panel ─────────────────────────────────────────────────────────

class AnnotationPanel(QWidget):
    """Panel with annotation list and embedded AI results detail view."""

    # Signals
    annotation_selected = Signal(str)  # annotation_id
    annotation_deleted = Signal(str)  # annotation_id
    # Detail view action signals
    copy_clicked = Signal(str)  # text_type
    retranslate_clicked = Signal()
    explain_clicked = Signal()
    tts_clicked = Signal()
    tts_play_clicked = Signal()
    tts_stop_clicked = Signal()
    tts_settings_clicked = Signal()
    regenerate_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, AnnotationCard] = {}
        self._selected_id: str = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(
            "background-color: #252526; border-bottom: 1px solid #333333;")
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

        # Splitter: annotation list (top) + detail view (bottom)
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet(
            "QSplitter::handle { background-color: #333333; height: 2px; }")

        # ─── Annotation list ──────────────────────
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: #1e1e1e; }
            QScrollBar:vertical {
                background-color: #2d2d2d; width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a; border-radius: 4px;
            }
        """)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(6, 6, 6, 6)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        list_layout.addWidget(scroll)

        self._empty_label = QLabel(
            "No annotations yet.\nSelect text and click Mark to create one.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #999999; padding: 20px;")
        self._container_layout.insertWidget(0, self._empty_label)

        splitter.addWidget(list_widget)

        # ─── Detail view ──────────────────────────
        self._detail_view = AnnotationDetailView()
        self._detail_view.copy_clicked.connect(self.copy_clicked.emit)
        self._detail_view.retranslate_clicked.connect(
            self.retranslate_clicked.emit)
        self._detail_view.explain_clicked.connect(self.explain_clicked.emit)
        self._detail_view.tts_clicked.connect(self.tts_clicked.emit)
        self._detail_view.tts_play_clicked.connect(self.tts_play_clicked.emit)
        self._detail_view.tts_stop_clicked.connect(self.tts_stop_clicked.emit)
        self._detail_view.tts_settings_clicked.connect(
            self.tts_settings_clicked.emit)
        self._detail_view.regenerate_clicked.connect(
            self.regenerate_clicked.emit)
        splitter.addWidget(self._detail_view)

        splitter.setSizes([200, 400])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    @property
    def detail_view(self) -> AnnotationDetailView:
        """Access the detail view for streaming AI results."""
        return self._detail_view

    @property
    def selected_id(self) -> str:
        """Get currently selected annotation ID."""
        return self._selected_id

    def set_annotations(self, annotations: List[Annotation]):
        """Set the list of annotations to display."""
        self.clear()
        for annotation in annotations:
            self._add_card(annotation)
        self._update_count()
        self._update_empty_state()

    def add_annotation(self, annotation: Annotation):
        """Add a single annotation and select it."""
        self._add_card(annotation)
        self._update_count()
        self._update_empty_state()
        self.select_annotation(annotation.id)

    def update_annotation(self, annotation: Annotation):
        """Update an existing annotation card."""
        if annotation.id in self._cards:
            old_card = self._cards[annotation.id]
            idx = self._container_layout.indexOf(old_card)
            self._container_layout.removeWidget(old_card)
            old_card.deleteLater()

            card = AnnotationCard(annotation)
            card.card_clicked.connect(self._on_card_clicked)
            card.delete_clicked.connect(self.annotation_deleted.emit)
            self._cards[annotation.id] = card

            if idx >= 0:
                self._container_layout.insertWidget(idx, card)
            else:
                count = self._container_layout.count()
                self._container_layout.insertWidget(count - 1, card)

            if annotation.id == self._selected_id:
                card.set_selected(True)

    def remove_annotation(self, annotation_id: str):
        """Remove an annotation card."""
        if annotation_id in self._cards:
            card = self._cards.pop(annotation_id)
            self._container_layout.removeWidget(card)
            card.deleteLater()
            if annotation_id == self._selected_id:
                self._selected_id = ""
                self._detail_view.show_empty()
            self._update_count()
            self._update_empty_state()

    def select_annotation(self, annotation_id: str):
        """Select an annotation by ID and show its details."""
        # Deselect previous
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)

        self._selected_id = annotation_id

        # Select new
        if annotation_id in self._cards:
            card = self._cards[annotation_id]
            card.set_selected(True)
            self._detail_view.show_annotation(card.annotation)
            self.annotation_selected.emit(annotation_id)

    def clear(self):
        """Clear all annotation cards."""
        for card in self._cards.values():
            self._container_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_id = ""
        self._detail_view.show_empty()
        self._update_count()
        self._update_empty_state()

    def _add_card(self, annotation: Annotation):
        card = AnnotationCard(annotation)
        card.card_clicked.connect(self._on_card_clicked)
        card.delete_clicked.connect(self.annotation_deleted.emit)
        self._cards[annotation.id] = card
        count = self._container_layout.count()
        self._container_layout.insertWidget(count - 1, card)

    def _on_card_clicked(self, annotation_id: str):
        self.select_annotation(annotation_id)

    def _update_count(self):
        self._count_label.setText(str(len(self._cards)))

    def _update_empty_state(self):
        self._empty_label.setVisible(len(self._cards) == 0)
