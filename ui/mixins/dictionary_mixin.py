"""
Dictionary and context menu mixin for PopupWindow.
Handles text selection, context menus, and dictionary lookups.
"""
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtGui import QAction, QCursor

from ui.styles.theme import Theme


class DictionaryMixin:
    """Mixin providing dictionary and context menu functionality."""

    def _init_dictionary_state(self):
        """Initialize dictionary-related state variables."""
        self.dictionary_thread = None
        self._orphan_dictionary_threads = []
        self._dictionary_markdown = ""

    # ── Context menu & dictionary ──────────────────────────────────────

    def _copy_text(self, text_widget):
        text = text_widget.toPlainText()
        placeholder = {"Correcting...", "Translating..."}
        if text and text not in placeholder:
            QApplication.clipboard().setText(text)

    def _show_context_menu(self, text_edit, pos):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.menu_style())

        cursor = text_edit.textCursor()

        copy_action = QAction("Copy", self)
        icon = self.icon_mgr.make_menu_icon("copy")
        if not icon.isNull():
            copy_action.setIcon(icon)
        copy_action.triggered.connect(text_edit.copy)
        copy_action.setEnabled(cursor.hasSelection())
        menu.addAction(copy_action)

        sel_all_action = QAction("Select All", self)
        icon = self.icon_mgr.make_menu_icon("select_all")
        if not icon.isNull():
            sel_all_action.setIcon(icon)
        sel_all_action.triggered.connect(text_edit.selectAll)
        menu.addAction(sel_all_action)

        menu.addSeparator()

        translate_action = QAction("Translate to Dictionary", self)
        icon = self.icon_mgr.make_menu_icon("translate")
        if not icon.isNull():
            translate_action.setIcon(icon)
        translate_action.triggered.connect(lambda: self._translate_selected(text_edit))
        translate_action.setEnabled(cursor.hasSelection())
        menu.addAction(translate_action)

        explain_action = QAction("Explain with AI", self)
        icon = self.icon_mgr.make_menu_icon("search")
        if not icon.isNull():
            explain_action.setIcon(icon)
        explain_action.triggered.connect(lambda: self._open_explain_dialog(text_edit))
        menu.addAction(explain_action)

        menu.exec(text_edit.mapToGlobal(pos))

    def _show_translate_menu(self, text_edit):
        cursor = text_edit.textCursor()
        if not cursor.hasSelection():
            return

        gpos = QCursor.pos()
        gpos.setX(gpos.x() - 20)
        gpos.setY(gpos.y() - 10)

        menu = QMenu(self)
        menu.setStyleSheet(Theme.menu_style())
        action = QAction("Translate to Dictionary", self)
        icon = self.icon_mgr.make_menu_icon("translate")
        if not icon.isNull():
            action.setIcon(icon)
        action.triggered.connect(lambda: self._translate_selected(text_edit))
        menu.addAction(action)

        explain_action = QAction("Explain with AI", self)
        icon = self.icon_mgr.make_menu_icon("search")
        if not icon.isNull():
            explain_action.setIcon(icon)
        explain_action.triggered.connect(lambda: self._open_explain_dialog(text_edit))
        menu.addAction(explain_action)

        menu.exec(gpos)

    def _translate_selected(self, text_edit):
        cursor = text_edit.textCursor()
        selected = cursor.selectedText().strip()
        if not selected:
            return

        full_text = text_edit.toPlainText()
        self._dictionary_markdown = ""
        translating_prefix = self.icon_mgr.get_icon_label("translating", "Translating:")
        self.dictionary_display.setPlainText(f"{translating_prefix} {selected}...")

        if self.dictionary_thread and self.dictionary_thread.isRunning():
            self._stop_dictionary_thread(immediate=True)

        from services.api.dictionary import DictionaryThread
        self.dictionary_thread = DictionaryThread(selected, full_text)
        self.dictionary_thread.translation_chunk.connect(self._on_dict_chunk)
        self.dictionary_thread.translation_done.connect(self._on_dict_done)
        self.dictionary_thread.start()

    def _stop_dictionary_thread(self, immediate=False):
        if not self.dictionary_thread or not self.dictionary_thread.isRunning():
            return
        try:
            self.dictionary_thread.translation_chunk.disconnect()
            self.dictionary_thread.translation_done.disconnect()
        except:
            pass
        self.dictionary_thread.stop()
        if immediate:
            if not self.dictionary_thread.wait(150):
                self.dictionary_thread.terminate()
                self.dictionary_thread.wait(150)
        else:
            self.dictionary_thread.finished.connect(self._cleanup_orphan_threads)
            self._orphan_dictionary_threads.append(self.dictionary_thread)
        self.dictionary_thread = None

    def _cleanup_orphan_threads(self):
        self._orphan_dictionary_threads = [t for t in self._orphan_dictionary_threads if t.isRunning()]

    def _on_dict_chunk(self, chunk):
        self._dictionary_markdown += chunk
        self._render_dictionary()

    def _on_dict_done(self, result):
        if self._dictionary_markdown:
            self._render_dictionary()

    def _render_dictionary(self):
        scrollbar = self.dictionary_display.verticalScrollBar()
        scroll_pos = scrollbar.value()

        if HAS_MARKDOWN:
            html = markdown.markdown(self._dictionary_markdown, extensions=['extra', 'nl2br', 'sane_lists'])
            styled = f"""
            <style>
                body {{
                    font-family: '{Theme.Fonts.FAMILY_SECONDARY}', sans-serif;
                    line-height: 1.6;
                    color: {Theme.Colors.TEXT_PRIMARY};
                }}
                h1, h2, h3 {{ color: {Theme.Colors.GRAY_300}; margin-top: 10px; }}
                strong {{ color: {Theme.Colors.PRIMARY_LIGHT}; }}
                code {{ background-color: {Theme.Colors.GRAY_600}; padding: 2px 5px; border-radius: 3px; }}
                ul, ol {{ margin-left: 20px; }}
                p {{ margin: 5px 0; }}
            </style>
            {html}
            """
            self.dictionary_display.setHtml(styled)
        else:
            self.dictionary_display.setPlainText(self._dictionary_markdown)

        scrollbar.setValue(scroll_pos)

    def _open_explain_dialog(self, text_edit=None):
        """Open the explain dialog for AI Q&A."""
        from ui.dialogs.explain_dialog import ExplainDialog

        corrected = self.corrected_text_display.toPlainText()
        translated = self.translated_text_display.toPlainText()

        # Don't open if no content yet
        if corrected in ("", "Correcting...") and translated in ("", "Translating..."):
            return

        # Get selected text if available
        selected_text = ""
        if text_edit:
            cursor = text_edit.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()

        dialog = ExplainDialog(corrected, translated, selected_text, self)
        dialog.show()

    def _cleanup_dictionary(self):
        """Clean up dictionary thread on close."""
        if self.dictionary_thread and self.dictionary_thread.isRunning():
            try:
                self.dictionary_thread.translation_chunk.disconnect()
                self.dictionary_thread.translation_done.disconnect()
            except:
                pass
            self.dictionary_thread.stop()
            if not self.dictionary_thread.wait(1000):
                self.dictionary_thread.terminate()
                self.dictionary_thread.wait(500)
            self.dictionary_thread = None
