"""
TTS manager interface for managing TTS services.
"""


class TTSManager:
    """
    Abstract interface for TTS managers.
    Provides a common interface for both local and remote TTS services.
    """

    def create_tts_thread(self, text, **kwargs):
        """
        Create a TTS thread for generating speech.

        Args:
            text: Text to convert to speech
            **kwargs: Additional parameters specific to the TTS implementation

        Returns:
            QThread instance for TTS generation
        """
        raise NotImplementedError("Subclasses must implement create_tts_thread()")

    def get_tts_instance(self, **kwargs):
        """
        Get or create a TTS instance.

        Args:
            **kwargs: Parameters for TTS initialization

        Returns:
            TTS instance
        """
        raise NotImplementedError("Subclasses must implement get_tts_instance()")
