import time
import threading
from PySide6.QtCore import QObject, Signal, QMetaObject, Qt, Slot
from pynput import keyboard


class GlobalShortcutHandler(QObject):
    """
    Detects a *double* Ctrl+C press (two separate Ctrl+C combos) within
    a configurable time window using pynput's GlobalHotKeys.
    """
    double_ctrl_c_triggered = Signal()

    def __init__(self, parent=None, threshold: float = 1.0):
        super().__init__(parent)

        # --- configuration -------------------------------------------------
        self._threshold = threshold          # seconds between two combos
        # ------------------------------------------------------------------

        # --- state ---------------------------------------------------------
        self._last_combo_time = 0.0          # time of the last *combo*
        # ------------------------------------------------------------------

        # --- listener ------------------------------------------------------
        self._hotkey_listener = None
        self._setup_listener()
        # ------------------------------------------------------------------

        # --- hook‑health monitor -------------------------------------------
        # Note: The monitor thread is less critical with GlobalHotKeys but
        # kept for robustness against potential listener failures.
        self._monitor_thread = threading.Thread(
            target=self._monitor_hook, daemon=True)
        self._monitor_thread.start()
        # ------------------------------------------------------------------

    # ----------------------------------------------------------------------
    # Listener helpers
    # ----------------------------------------------------------------------
    def _setup_listener(self):
        """Create / restart the global key listener using GlobalHotKeys."""
        if self._hotkey_listener and self._hotkey_listener.is_alive():
            self._hotkey_listener.stop()
            self._hotkey_listener = None

        # Define the hotkey and its callback
        hotkeys = {
            '<ctrl>+c': self._on_ctrl_c_activated
        }

        # We need both press and release callbacks
        self._hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
        self._hotkey_listener.start()
        print("Global Ctrl+C hotkey registered successfully")

    def _on_ctrl_c_activated(self):
        """Called by the listener thread when Ctrl+C is pressed."""
        print("Ctrl+C combination detected")
        now = time.time()

        # Check if this combo is within the threshold of the last one
        if now - self._last_combo_time <= self._threshold:
            # Emit the Qt signal *via* a queued connection to the main thread
            QMetaObject.invokeMethod(
                self, "_emit_double", Qt.QueuedConnection)
            print("Double Ctrl+C detected!")
            # Reset the timer to prevent a third press from also triggering
            self._last_combo_time = 0.0
        else:
            # This is the first press, or too much time has passed
            self._last_combo_time = now

    @Slot()
    def _emit_double(self):
        """Slot that actually emits the signal on the main GUI thread."""
        self.double_ctrl_c_triggered.emit()

    # ----------------------------------------------------------------------
    # Hook‑health monitor
    # ----------------------------------------------------------------------
    def _monitor_hook(self):
        """Periodically check that the listener is still alive."""
        while True:
            time.sleep(30)  # every 30 s
            if not self._hotkey_listener or not self._hotkey_listener.is_alive():
                print("Hotkey listener inactive – re‑registering")
                self._setup_listener()

    # ----------------------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------------------
    def stop(self):
        """Stop the listener."""
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        # The monitor thread is a daemon; it will exit when the app quits.
