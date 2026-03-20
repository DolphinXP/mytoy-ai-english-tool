"""
Main application class for Quick Translation app.
"""
import sys
import importlib.util
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

# Add QuickTranslate directory to path for local imports
quicktranslate_dir = str(Path(__file__).parent.parent)
if quicktranslate_dir not in sys.path:
    sys.path.insert(0, quicktranslate_dir)

from config import config
from core.hotkey_manager import HotkeyManager
from core.translation_service import TranslationService
from core.history_manager import HistoryManager

# Import UI modules using importlib to avoid conflicts with top-level ui package
def _import_ui_module(module_name):
    """Import a UI module from QuickTranslate/ui directory."""
    ui_dir = Path(__file__).parent.parent / "ui"
    module_path = ui_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

tray_icon_module = _import_ui_module("tray_icon")
TrayIcon = tray_icon_module.TrayIcon

input_popup_module = _import_ui_module("input_popup")
InputPopup = input_popup_module.InputPopup

result_panel_module = _import_ui_module("result_panel")
ResultPanel = result_panel_module.ResultPanel

history_panel_module = _import_ui_module("history_panel")
HistoryPanel = history_panel_module.HistoryPanel

settings_dialog_module = _import_ui_module("settings_dialog")
SettingsDialog = settings_dialog_module.SettingsDialog


class QuickTranslateApp(QObject):
    """
    Main application class for Quick Translation.
    Coordinates all components and manages application lifecycle.
    """

    def __init__(self):
        """Initialize the application."""
        super().__init__()

        # Initialize services
        self._hotkey_manager = HotkeyManager(hotkey=config.get_hotkey())
        self._translation_service = TranslationService()
        self._history_manager = HistoryManager(max_items=config.get_history_max_items())

        # Initialize UI components
        self._tray_icon = TrayIcon()
        self._input_popup: Optional[InputPopup] = None
        self._result_panel: Optional[ResultPanel] = None
        self._history_panel: Optional[HistoryPanel] = None
        self._settings_dialog: Optional[SettingsDialog] = None

        # Current translation state
        self._current_original = ""
        self._current_translation = ""

        # Connect signals
        self._connect_signals()

        # Show tray icon
        self._tray_icon.show()

    def _connect_signals(self) -> None:
        """Connect all signals between components."""
        # Hotkey manager
        self._hotkey_manager.hotkey_triggered.connect(self._on_hotkey_triggered)

        # Translation service
        self._translation_service.translation_started.connect(self._on_translation_started)
        self._translation_service.translation_chunk.connect(self._on_translation_chunk)
        self._translation_service.translation_completed.connect(self._on_translation_completed)
        self._translation_service.translation_error.connect(self._on_translation_error)

        # Tray icon
        self._tray_icon.show_input_requested.connect(self._show_input_popup)
        self._tray_icon.show_history_requested.connect(self._show_history_panel)
        self._tray_icon.show_settings_requested.connect(self._show_settings_dialog)
        self._tray_icon.service_changed.connect(self._on_service_changed)
        self._tray_icon.exit_requested.connect(self._exit_app)

    @Slot()
    def _on_hotkey_triggered(self) -> None:
        """Handle hotkey trigger."""
        print("Hotkey triggered - showing input popup")
        self._show_input_popup()

    def _show_input_popup(self) -> None:
        """Show the input popup."""
        # Hide result panel if visible
        if self._result_panel and self._result_panel.isVisible():
            self._result_panel.hide_panel()

        # Create or show input popup
        if self._input_popup is None:
            self._input_popup = InputPopup()
            self._input_popup.translation_requested.connect(self._on_translation_requested)
            self._input_popup.popup_hidden.connect(self._on_input_popup_hidden)

        self._input_popup.show_popup()

    @Slot(str)
    def _on_translation_requested(self, text: str) -> None:
        """Handle translation request from input popup."""
        print(f"Translation requested: {text}")
        self._current_original = text
        self._current_translation = ""

        # Start translation
        service_name = config.get_current_service()
        self._translation_service.translate(text, service_name)

    @Slot()
    def _on_translation_started(self) -> None:
        """Handle translation start."""
        print("Translation started")
        # Update tray icon to show translating state
        self._tray_icon.set_translating(True)

    @Slot(str)
    def _on_translation_chunk(self, chunk: str) -> None:
        """Handle streaming translation chunk."""
        self._current_translation += chunk

        # Update result panel if visible
        if self._result_panel and self._result_panel.isVisible():
            self._result_panel.update_translation(self._current_translation)

    @Slot(str)
    def _on_translation_completed(self, translation: str) -> None:
        """Handle translation completion."""
        print(f"Translation completed: {translation}")
        self._current_translation = translation

        # Update tray icon
        self._tray_icon.set_translating(False)

        # Add to history
        self._history_manager.add_translation(self._current_original, translation)

        # Show result panel
        self._show_result_panel()

        # Auto-copy to clipboard
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(translation)
            print("Translation copied to clipboard")

    @Slot(str)
    def _on_translation_error(self, error: str) -> None:
        """Handle translation error."""
        print(f"Translation error: {error}")
        self._tray_icon.set_translating(False)

        # Get input window Y position before hiding
        input_y = None
        if self._input_popup and self._input_popup.isVisible():
            input_y = self._input_popup.pos().y()
            self._input_popup.hide_popup()

        # Show error in result panel
        if self._result_panel is None:
            self._result_panel = ResultPanel()
            self._result_panel.new_translation_requested.connect(self._show_input_popup)

        self._result_panel.show_error(error, input_y)

    def _show_result_panel(self) -> None:
        """Show the result panel with current translation."""
        # Get input window Y position before hiding
        input_y = None
        if self._input_popup and self._input_popup.isVisible():
            input_y = self._input_popup.pos().y()
            self._input_popup.hide_popup()

        if self._result_panel is None:
            self._result_panel = ResultPanel()
            self._result_panel.new_translation_requested.connect(self._show_input_popup)

        self._result_panel.show_result(self._current_original, self._current_translation, input_y)

    @Slot()
    def _on_input_popup_hidden(self) -> None:
        """Handle input popup hidden."""
        # Result panel will handle its own visibility
        pass

    def _show_history_panel(self) -> None:
        """Show the history panel."""
        if self._history_panel is None:
            self._history_panel = HistoryPanel(self._history_manager)
            self._history_panel.translation_selected.connect(self._on_history_translation_selected)

        self._history_panel.show_panel()

    @Slot(str, str)
    def _on_history_translation_selected(self, original: str, translation: str) -> None:
        """Handle history translation selection."""
        self._current_original = original
        self._current_translation = translation
        self._show_result_panel()

    def _show_settings_dialog(self) -> None:
        """Show the settings dialog."""
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog()

        self._settings_dialog.show()

    @Slot(str)
    def _on_service_changed(self, service_name: str) -> None:
        """Handle AI service change."""
        print(f"Service changed to: {service_name}")
        config.set_current_service(service_name)

    def _exit_app(self) -> None:
        """Exit the application."""
        print("Exiting application")

        # Stop services
        self._hotkey_manager.stop()
        self._translation_service.cancel()

        # Hide tray icon
        self._tray_icon.hide()

        # Quit application
        QApplication.quit()

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Application exit code
        """
        print(f"{config.APP_NAME} v{config.APP_VERSION} started")
        print(f"Press {config.get_hotkey()} to show translation window")

        # Run application event loop
        return QApplication.exec()
