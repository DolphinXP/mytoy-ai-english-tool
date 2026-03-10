"""Side panel for PDF bookmarks and annotations."""
from typing import List

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QInputDialog,
    QTabWidget,
)

from PDFReader.models.annotation import Annotation


def _create_text_icon(text: str, size: int = 20, color: str = "#d4d4d4") -> QIcon:
    """Create an icon from text/symbol."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    font = QFont("Segoe UI Symbol", int(size * 0.7))
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()

    return QIcon(pixmap)


class BookmarkPanel(QWidget):
    """Panel for displaying PDF bookmarks/outline as a tree."""

    bookmark_clicked = Signal(int)  # page_number
    bookmark_edited = Signal(int, str)  # index, new_title
    bookmark_deleted = Signal(int)  # index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bookmarks: List[tuple] = []
        self._current_page: int = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(1)
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setStyleSheet(
            """
            QTreeWidget {
                background-color: #1e1e1e;
                border: none;
                color: #d4d4d4;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 8px 12px;
            }
            QTreeWidget::item:hover {
                background-color: #2a2d2e;
            }
            QTreeWidget::item:selected {
                background-color: #0e639c;
            }
        """
        )
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(
            self._on_context_menu_requested
        )
        layout.addWidget(self._tree)

        self._empty_label = QLabel("No bookmarks in this PDF")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #7f7f7f; padding: 20px;")
        layout.addWidget(self._empty_label)

    def set_bookmarks(self, bookmarks: List[tuple]):
        """Set bookmarks list. Each tuple: (title, page_number, level)."""
        self._bookmarks = sorted(
            list(bookmarks), key=lambda item: (item[1], str(item[0]).lower())
        )
        self._tree.clear()
        if not self._bookmarks:
            self._empty_label.show()
            self._tree.hide()
            return

        self._empty_label.hide()
        self._tree.show()

        # Build a hierarchy from bookmark level while preserving sorted order.
        level_stack: list[QTreeWidgetItem] = []
        for idx, (title, page, level) in enumerate(self._bookmarks):
            item = QTreeWidgetItem()
            item.setText(0, title)
            item.setData(0, Qt.UserRole, page)
            item.setData(0, Qt.UserRole + 1, idx)
            item.setData(0, Qt.UserRole + 2, title)
            try:
                level = max(0, int(level))
            except (TypeError, ValueError):
                level = 0

            while len(level_stack) > level:
                level_stack.pop()

            if level == 0 or not level_stack:
                self._tree.addTopLevelItem(item)
            else:
                level_stack[-1].addChild(item)

            level_stack.append(item)

        self._tree.expandAll()
        self._update_active_bookmark()

    def set_current_page(self, page_number: int):
        """Highlight bookmark that best matches the current page."""
        self._current_page = max(0, int(page_number))
        self._update_active_bookmark()

    def _collect_tree_items(self) -> List[QTreeWidgetItem]:
        items: List[QTreeWidgetItem] = []
        stack = [
            self._tree.topLevelItem(i)
            for i in range(self._tree.topLevelItemCount())
        ]
        while stack:
            item = stack.pop()
            if item is None:
                continue
            items.append(item)
            for i in range(item.childCount() - 1, -1, -1):
                stack.append(item.child(i))
        return items

    def _update_active_bookmark(self):
        if not self._bookmarks or self._tree.topLevelItemCount() == 0:
            self._tree.setCurrentItem(None)
            return

        selected_item = None
        selected_page = -1
        for item in self._collect_tree_items():
            page = item.data(0, Qt.UserRole)
            if page is None:
                continue
            try:
                page = int(page)
            except (TypeError, ValueError):
                continue
            if page <= self._current_page and page >= selected_page:
                selected_item = item
                selected_page = page

        if selected_item is None:
            selected_item = self._tree.topLevelItem(0)

        self._tree.setCurrentItem(selected_item)
        self._tree.scrollToItem(selected_item)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        page = item.data(0, Qt.UserRole)
        if page is not None:
            self.bookmark_clicked.emit(page)

    def _on_context_menu_requested(self, pos):
        item = self._tree.itemAt(pos)
        if item is None:
            return

        index = item.data(0, Qt.UserRole + 1)
        current_title = item.data(0, Qt.UserRole + 2) or ""
        if index is None:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Bookmark")
        delete_action = menu.addAction("Delete Bookmark")
        chosen = menu.exec(self._tree.mapToGlobal(pos))
        if chosen == edit_action:
            new_title, ok = QInputDialog.getText(
                self, "Edit Bookmark", "Bookmark title:", text=current_title
            )
            if ok:
                new_title = new_title.strip()
                if new_title:
                    self.bookmark_edited.emit(index, new_title)
        elif chosen == delete_action:
            self.bookmark_deleted.emit(index)


class AnnotationListPanel(QWidget):
    """Panel for displaying annotations in a compact list."""

    annotation_selected = Signal(str)  # annotation_id
    annotation_deleted = Signal(str)  # annotation_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setStyleSheet(
            """
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #d4d4d4;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QListWidget::item:selected {
                background-color: #0e639c;
            }
        """
        )
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(
            self._on_context_menu_requested
        )
        layout.addWidget(self._list)

        self._empty_label = QLabel(
            "No annotations yet.\nSelect text and use Mark Selection."
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #7f7f7f; padding: 20px;")
        layout.addWidget(self._empty_label)

    def _create_row_widget(self, text: str, on_delete):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(6)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #d4d4d4;")
        row_layout.addWidget(label, 1)

        delete_btn = QPushButton("")
        delete_btn.setFixedSize(22, 22)
        delete_btn.setToolTip("Delete annotation")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #8a8a8a;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a2020;
                border-radius: 4px;
                color: #f48771;
            }
            """
        )
        delete_btn.setIcon(_create_text_icon("✕", 18, "#d4d4d4"))
        delete_btn.setIconSize(QSize(18, 18))
        delete_btn.clicked.connect(on_delete)
        row_layout.addWidget(delete_btn)

        row.setContextMenuPolicy(Qt.CustomContextMenu)
        def _show_row_menu(pos):
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Annotation")
            chosen = menu.exec(row.mapToGlobal(pos))
            if chosen == delete_action:
                on_delete()
        row.customContextMenuRequested.connect(_show_row_menu)

        return row

    def _annotation_text(self, ann: Annotation) -> str:
        preview = " ".join(ann.selected_text.split())
        if len(preview) > 80:
            preview = preview[:77].rstrip() + "..."
        return f"P{ann.page_number + 1}: {preview}"

    def set_annotations(self, annotations: List[Annotation]):
        self._list.clear()
        if not annotations:
            self._empty_label.show()
            self._list.hide()
            return

        self._empty_label.hide()
        self._list.show()

        sorted_annotations = sorted(
            annotations, key=lambda ann: (ann.page_number, ann.created_at)
        )
        for ann in sorted_annotations:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, ann.id)
            self._list.addItem(item)
            row_widget = self._create_row_widget(
                self._annotation_text(ann),
                lambda _checked=False, ann_id=ann.id: self.annotation_deleted.emit(ann_id),
            )
            item.setSizeHint(row_widget.sizeHint())
            self._list.setItemWidget(item, row_widget)

    def add_annotation(self, annotation: Annotation):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, annotation.id)
        self._list.addItem(item)
        row_widget = self._create_row_widget(
            self._annotation_text(annotation),
            lambda _checked=False, ann_id=annotation.id: self.annotation_deleted.emit(ann_id),
        )
        item.setSizeHint(row_widget.sizeHint())
        self._list.setItemWidget(item, row_widget)
        self._empty_label.hide()
        self._list.show()

    def update_annotation(self, annotation: Annotation):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.UserRole) == annotation.id:
                row_widget = self._create_row_widget(
                    self._annotation_text(annotation),
                    lambda _checked=False, ann_id=annotation.id: self.annotation_deleted.emit(ann_id),
                )
                item.setSizeHint(row_widget.sizeHint())
                self._list.setItemWidget(item, row_widget)
                break

    def remove_annotation(self, annotation_id: str):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.UserRole) == annotation_id:
                self._list.takeItem(i)
                break

        is_empty = self._list.count() == 0
        self._empty_label.setVisible(is_empty)
        self._list.setVisible(not is_empty)

    def select_annotation(self, annotation_id: str):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.UserRole) == annotation_id:
                self._list.setCurrentItem(item)
                break

    def _on_item_clicked(self, item: QListWidgetItem):
        ann_id = item.data(Qt.UserRole)
        if ann_id:
            self.annotation_selected.emit(ann_id)

    def _on_context_menu_requested(self, pos):
        item = self._list.itemAt(pos)
        if item is None:
            return

        ann_id = item.data(Qt.UserRole)
        if not ann_id:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("Delete Annotation")
        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen == delete_action:
            self.annotation_deleted.emit(ann_id)


class DirectTranslationPanel(QWidget):
    """Panel for displaying direct translation history."""

    translation_deleted = Signal(int)  # index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setStyleSheet(
            """
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #d4d4d4;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QListWidget::item:selected {
                background-color: #0e639c;
            }
        """
        )
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(
            self._on_context_menu_requested
        )
        layout.addWidget(self._list)

        self._empty_label = QLabel(
            "No direct translations yet.\nUse context menu 'To Chinese'."
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #7f7f7f; padding: 20px;")
        layout.addWidget(self._empty_label)

    def _create_row_widget(self, en_text: str, zh_text: str, on_delete):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(6)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        en_label = QLabel(f"EN: {self._shorten(en_text, 80)}")
        en_label.setWordWrap(True)
        en_label.setStyleSheet("color: #d4d4d4;")
        text_layout.addWidget(en_label)

        zh_label = QLabel(f"ZH: {self._shorten(zh_text, 100)}")
        zh_label.setWordWrap(True)
        zh_label.setStyleSheet("color: #c5e1ff;")
        text_layout.addWidget(zh_label)

        row_layout.addWidget(text_container, 1)

        delete_btn = QPushButton("")
        delete_btn.setFixedSize(22, 22)
        delete_btn.setToolTip("Delete translation")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #8a8a8a;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a2020;
                border-radius: 4px;
                color: #f48771;
            }
            """
        )
        delete_btn.setIcon(_create_text_icon("✕", 18, "#d4d4d4"))
        delete_btn.setIconSize(QSize(18, 18))
        delete_btn.clicked.connect(on_delete)
        row_layout.addWidget(delete_btn)

        row.setContextMenuPolicy(Qt.CustomContextMenu)

        def _show_row_menu(pos):
            parent_item = self._find_item_for_row(row)
            if parent_item is None:
                return
            self._show_translation_context_menu(
                row.mapToGlobal(pos), parent_item
            )

        row.customContextMenuRequested.connect(_show_row_menu)

        return row

    @staticmethod
    def _shorten(text: str, max_len: int) -> str:
        clean = " ".join((text or "").split())
        if len(clean) <= max_len:
            return clean
        return clean[: max_len - 3].rstrip() + "..."

    def set_translations(self, items: List[tuple]):
        self._list.clear()
        for en_text, zh_text in items:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, en_text)
            item.setData(Qt.UserRole + 1, zh_text)
            self._list.addItem(item)
            row_widget = self._create_row_widget(
                en_text,
                zh_text,
                lambda _checked=False, it=item: self._emit_delete_for_item(it),
            )
            row_size = row_widget.sizeHint()
            row_size.setHeight(max(62, row_size.height()))
            item.setSizeHint(row_size)
            self._list.setItemWidget(item, row_widget)
        is_empty = self._list.count() == 0
        self._empty_label.setVisible(is_empty)
        self._list.setVisible(not is_empty)

    def add_translation(self, en_text: str, zh_text: str):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, en_text)
        item.setData(Qt.UserRole + 1, zh_text)
        self._list.insertItem(0, item)
        row_widget = self._create_row_widget(
            en_text,
            zh_text,
            lambda _checked=False, it=item: self._emit_delete_for_item(it),
        )
        row_size = row_widget.sizeHint()
        row_size.setHeight(max(62, row_size.height()))
        item.setSizeHint(row_size)
        self._list.setItemWidget(item, row_widget)
        self._empty_label.hide()
        self._list.show()

    def clear_translations(self):
        self._list.clear()
        self._empty_label.show()
        self._list.hide()

    def _emit_delete_for_item(self, item: QListWidgetItem):
        idx = self._list.row(item)
        if idx >= 0:
            self.translation_deleted.emit(idx)

    def _on_context_menu_requested(self, pos):
        item = self._list.itemAt(pos)
        if item is None:
            return

        self._show_translation_context_menu(self._list.mapToGlobal(pos), item)

    def _show_translation_context_menu(self, global_pos, item: QListWidgetItem):
        idx = self._list.row(item)
        if idx < 0:
            return

        en_text = str(item.data(Qt.UserRole) or "")
        zh_text = str(item.data(Qt.UserRole + 1) or "")

        menu = QMenu(self)
        copy_menu = menu.addMenu("Copy")
        copy_en_action = copy_menu.addAction("Copy Source (EN)")
        copy_zh_action = copy_menu.addAction("Copy Translation (ZH)")
        copy_both_action = copy_menu.addAction("Copy Both")
        menu.addSeparator()
        delete_action = menu.addAction("Delete Translation")

        has_en = bool(en_text.strip())
        has_zh = bool(zh_text.strip())
        copy_en_action.setEnabled(has_en)
        copy_zh_action.setEnabled(has_zh)
        copy_both_action.setEnabled(has_en or has_zh)

        chosen = menu.exec(global_pos)
        if chosen == copy_en_action:
            QApplication.clipboard().setText(en_text.strip())
        elif chosen == copy_zh_action:
            QApplication.clipboard().setText(zh_text.strip())
        elif chosen == copy_both_action:
            if has_en and has_zh:
                QApplication.clipboard().setText(
                    f"EN: {en_text.strip()}\nZH: {zh_text.strip()}"
                )
            elif has_en:
                QApplication.clipboard().setText(en_text.strip())
            elif has_zh:
                QApplication.clipboard().setText(zh_text.strip())
        elif chosen == delete_action:
            self.translation_deleted.emit(idx)

    def _find_item_for_row(self, row: QWidget):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if self._list.itemWidget(item) is row:
                return item
        return None


class SidePanel(QWidget):
    """Collapsible side panel with bookmarks and annotations."""

    bookmark_clicked = Signal(int)
    bookmark_edited = Signal(int, str)
    bookmark_deleted = Signal(int)
    annotation_selected = Signal(str)
    annotation_deleted = Signal(str)
    translation_deleted = Signal(int)
    collapse_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background-color: #252526;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self._collapse_btn = QPushButton("Hide")
        self._collapse_btn.setFixedSize(76, 24)
        self._collapse_btn.setToolTip("Hide side panel")
        self._collapse_btn.setIcon(_create_text_icon("<", 20, "#d4d4d4"))
        self._collapse_btn.setIconSize(QSize(20, 20))
        self._collapse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #d4d4d4;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-radius: 4px;
            }
        """
        )
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self._collapse_btn)
        header_layout.addStretch()

        layout.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            """
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background-color: #252526;
                color: #d4d4d4;
                padding: 6px 10px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0e639c;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #333333;
            }
        """
        )

        self._bookmark_panel = BookmarkPanel()
        self._bookmark_panel.bookmark_clicked.connect(self.bookmark_clicked.emit)
        self._bookmark_panel.bookmark_edited.connect(self.bookmark_edited.emit)
        self._bookmark_panel.bookmark_deleted.connect(self.bookmark_deleted.emit)
        self._tabs.addTab(self._bookmark_panel, "Bookmarks")

        self._annotation_panel = AnnotationListPanel()
        self._annotation_panel.annotation_selected.connect(self.annotation_selected.emit)
        self._annotation_panel.annotation_deleted.connect(self.annotation_deleted.emit)
        self._tabs.addTab(self._annotation_panel, "Annotations")

        self._direct_translation_panel = DirectTranslationPanel()
        self._direct_translation_panel.translation_deleted.connect(
            self.translation_deleted.emit
        )
        self._tabs.addTab(self._direct_translation_panel, "Translations")

        layout.addWidget(self._tabs)

        self.setMinimumWidth(280)
        self.setMaximumWidth(500)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._tabs.hide()
            self._collapse_btn.setText("Show")
            self._collapse_btn.setToolTip("Show side panel")
            self._collapse_btn.setIcon(_create_text_icon(">", 20, "#d4d4d4"))
            self.setFixedWidth(72)
        else:
            self._tabs.show()
            self._collapse_btn.setText("Hide")
            self._collapse_btn.setToolTip("Hide side panel")
            self._collapse_btn.setIcon(_create_text_icon("<", 20, "#d4d4d4"))
            self.setMinimumWidth(280)
            self.setMaximumWidth(500)
        self.collapse_toggled.emit(self._collapsed)

    def set_bookmarks(self, bookmarks: List[tuple]):
        self._bookmark_panel.set_bookmarks(bookmarks)

    def set_current_page(self, page_number: int):
        self._bookmark_panel.set_current_page(page_number)

    def set_annotations(self, annotations: List[Annotation]):
        self._annotation_panel.set_annotations(annotations)

    def add_annotation(self, annotation: Annotation):
        self._annotation_panel.add_annotation(annotation)

    def update_annotation(self, annotation: Annotation):
        self._annotation_panel.update_annotation(annotation)

    def remove_annotation(self, annotation_id: str):
        self._annotation_panel.remove_annotation(annotation_id)

    def select_annotation(self, annotation_id: str):
        self._tabs.setCurrentIndex(1)
        self._annotation_panel.select_annotation(annotation_id)

    def set_direct_translations(self, items: List[tuple]):
        self._direct_translation_panel.set_translations(items)

    def add_direct_translation(self, en_text: str, zh_text: str):
        self._tabs.setCurrentIndex(2)
        self._direct_translation_panel.add_translation(en_text, zh_text)

    def clear_direct_translations(self):
        self._direct_translation_panel.clear_translations()

    def is_collapsed(self) -> bool:
        return self._collapsed
