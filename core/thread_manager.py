"""
Thread lifecycle management for API and TTS threads.
"""


class ThreadManager:
    """Manages lifecycle of worker threads."""

    def __init__(self):
        self.correction_thread = None
        self.translation_thread = None
        self.tts_thread = None

    def stop_correction_thread(self):
        """Stop and cleanup correction thread."""
        if self.correction_thread is not None:
            if self.correction_thread.isRunning():
                self.correction_thread.terminate()
                self.correction_thread.wait(1000)
            self.correction_thread = None

    def stop_translation_thread(self):
        """Stop and cleanup translation thread."""
        if self.translation_thread is not None:
            if self.translation_thread.isRunning():
                self.translation_thread.terminate()
                self.translation_thread.wait(1000)
            self.translation_thread = None

    def stop_tts_thread(self):
        """Stop and cleanup TTS thread."""
        if self.tts_thread is not None:
            if self.tts_thread.isRunning():
                self.tts_thread.stop()
                if not self.tts_thread.wait(5000):
                    print("TTS thread did not stop in time, terminating...")
                    self.tts_thread.terminate()
                    self.tts_thread.wait(1000)
            self.tts_thread = None

    def stop_all_threads(self):
        """Stop all running threads."""
        self.stop_correction_thread()
        self.stop_translation_thread()
        self.stop_tts_thread()

    def set_correction_thread(self, thread):
        """Set the correction thread."""
        self.stop_correction_thread()
        self.correction_thread = thread

    def set_translation_thread(self, thread):
        """Set the translation thread."""
        self.stop_translation_thread()
        self.translation_thread = thread

    def set_tts_thread(self, thread):
        """Set the TTS thread."""
        self.stop_tts_thread()
        self.tts_thread = thread

    def is_correction_running(self):
        """Check if correction thread is running."""
        return self.correction_thread is not None and self.correction_thread.isRunning()

    def is_translation_running(self):
        """Check if translation thread is running."""
        return self.translation_thread is not None and self.translation_thread.isRunning()

    def is_tts_running(self):
        """Check if TTS thread is running."""
        return self.tts_thread is not None and self.tts_thread.isRunning()
