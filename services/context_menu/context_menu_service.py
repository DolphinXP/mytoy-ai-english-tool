"""
Universal context menu service that monitors for middle-click
and shows a floating context menu when text is selected.
"""
import time
import threading
from PySide6.QtCore import QObject, Signal, QMetaObject, Qt, Slot
from pynput import mouse


class ContextMenuService(QObject):
    """
    Monitors for middle mouse button clicks and triggers a context menu
    when text might be selected.
    """
    menu_requested = Signal(int, int)  # x, y screen coordinates

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False
        self._mouse_listener = None
        self._monitor_thread = None
        self._running = False
        # Store pending coordinates for cross-thread communication
        self._pending_x = 0
        self._pending_y = 0

    def set_enabled(self, enabled: bool):
        """Enable or disable the context menu service."""
        if enabled == self._enabled:
            return

        self._enabled = enabled
        if enabled:
            self._start_listener()
        else:
            self._stop_listener()

    def is_enabled(self) -> bool:
        """Check if the service is enabled."""
        return self._enabled

    def _start_listener(self):
        """Start the mouse listener."""
        if self._mouse_listener and self._mouse_listener.is_alive():
            return

        self._running = True
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()

        # Start monitor thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_listener, daemon=True)
        self._monitor_thread.start()

        print("Universal context menu: Mouse listener started")

    def _stop_listener(self):
        """Stop the mouse listener."""
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        print("Universal context menu: Mouse listener stopped")

    def _on_click(self, x, y, button, pressed):
        """Handle mouse click events."""
        if not self._enabled:
            return

        # Detect middle mouse button release
        if button == mouse.Button.middle and not pressed:
            print(f"Middle-click detected at ({x}, {y})")
            # Store coordinates for the slot to use
            self._pending_x = x
            self._pending_y = y
            # Emit signal on main thread using simple invokeMethod
            QMetaObject.invokeMethod(
                self, "_emit_menu_request",
                Qt.QueuedConnection
            )

    @Slot()
    def _emit_menu_request(self):
        """Emit menu request signal on main thread."""
        self.menu_requested.emit(self._pending_x, self._pending_y)

    def _monitor_listener(self):
        """Monitor the listener and restart if needed."""
        while self._running:
            time.sleep(30)
            if self._running and self._enabled:
                if not self._mouse_listener or not self._mouse_listener.is_alive():
                    print("Mouse listener inactive - restarting")
                    self._start_listener()

    def stop(self):
        """Stop the service completely."""
        self._running = False
        self._stop_listener()
