"""
Global hotkey manager for Quick Translation app.
"""
import time
import threading
from PySide6.QtCore import QObject, Signal
from pynput import keyboard


class HotkeyManager(QObject):
    """
    Manages global hotkey registration and detection.
    Uses pynput for cross-platform hotkey support.
    """

    # Signal emitted when hotkey is triggered
    hotkey_triggered = Signal()

    def __init__(self, parent=None, hotkey: str = "<ctrl>+<alt>+q"):
        """
        Initialize hotkey manager.

        Args:
            parent: Parent QObject
            hotkey: Hotkey combination string (e.g., "<ctrl>+<alt>+q")
        """
        super().__init__(parent)

        self._hotkey = hotkey
        self._hotkey_listener = None
        self._monitor_thread = None
        self._is_running = True

        # Setup the listener
        self._setup_listener()

        # Start health monitor thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_hook, daemon=True
        )
        self._monitor_thread.start()

    def _setup_listener(self) -> None:
        """Create / restart the global key listener."""
        if self._hotkey_listener and self._hotkey_listener.is_alive():
            self._hotkey_listener.stop()
            self._hotkey_listener = None

        try:
            # Define the hotkey and its callback
            hotkeys = {
                self._hotkey: self._on_hotkey_activated
            }

            self._hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
            self._hotkey_listener.start()
            print(f"Global hotkey registered: {self._hotkey}")
        except Exception as e:
            print(f"Error registering hotkey: {e}")

    def _on_hotkey_activated(self) -> None:
        """Called by the listener thread when hotkey is pressed."""
        print(f"Hotkey combination detected: {self._hotkey}")
        # Emit the Qt signal directly - PySide6 handles thread-safe emission
        self.hotkey_triggered.emit()


    def _monitor_hook(self) -> None:
        """Periodically check that the listener is still alive."""
        while self._is_running:
            time.sleep(30)  # Check every 30 seconds
            if not self._hotkey_listener or not self._hotkey_listener.is_alive():
                print("Hotkey listener inactive – re-registering")
                self._setup_listener()

    def update_hotkey(self, new_hotkey: str) -> None:
        """
        Update the hotkey combination.

        Args:
            new_hotkey: New hotkey combination string
        """
        if new_hotkey != self._hotkey:
            print(f"Updating hotkey from {self._hotkey} to {new_hotkey}")
            self._hotkey = new_hotkey
            self._setup_listener()

    def get_hotkey(self) -> str:
        """Get current hotkey combination."""
        return self._hotkey

    def stop(self) -> None:
        """Stop the hotkey listener."""
        self._is_running = False
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
