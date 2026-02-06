"""
Base class for API-based QThread operations with common functionality.
"""
import os
import warnings
import httpx
from openai import OpenAI
from PySide6.QtCore import Signal, QThread

from utils.config import get_api_config

# Suppress SSL warnings from unverified HTTPS requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class BaseAPIThread(QThread):
    """
    Base class for API threads that use OpenAI-compatible APIs.
    Provides common functionality for HTTP client setup, error handling,
    and streaming responses.
    """

    # Signals that subclasses can use
    chunk_received = Signal(str)  # For streaming chunks
    completed = Signal(str)  # For completion with result
    error_occurred = Signal(str)  # For error messages

    def __init__(self, api_config=None):
        super().__init__()

        # Use provided config or default to deepseek
        if api_config is None:
            api_config = get_api_config('deepseek')
        elif isinstance(api_config, str):
            api_config = get_api_config(api_config)

        self.api_key = api_config['key']
        self.base_url = api_config['endpoint']
        self.model_name = api_config['model']
        self.proxy_url = api_config.get('proxy')
        self.timeout = api_config.get('timeout', 60.0)
        self.verify_ssl = api_config.get('verify_ssl', True)

        # State management
        self._is_running = True
        self._http_client = None
        self._response = None

        # Remove SSL_CERT_FILE from environment if present
        if "SSL_CERT_FILE" in os.environ:
            del os.environ["SSL_CERT_FILE"]

    def create_http_client(self):
        """
        Create an HTTP client with proper configuration.

        Returns:
            httpx.Client configured for API requests
        """
        return httpx.Client(
            verify=False,  # Disable SSL verification to fix certificate errors
            proxy=self.proxy_url if self.proxy_url else None,
            timeout=self.timeout
        )

    def create_openai_client(self):
        """
        Create an OpenAI client with configured HTTP client.

        Returns:
            OpenAI client instance
        """
        self._http_client = self.create_http_client()
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=self._http_client
        )

    def make_streaming_request(self, messages, extra_body=None):
        """
        Make a streaming API request.

        Args:
            messages: List of message dictionaries for the API
            extra_body: Optional extra parameters for the request

        Returns:
            Generator yielding response chunks
        """
        client = self.create_openai_client()

        request_params = {
            'model': self.model_name,
            'messages': messages,
            'stream': True
        }

        if extra_body:
            request_params['extra_body'] = extra_body

        response = client.chat.completions.create(**request_params)
        self._response = response

        return response

    def process_streaming_response(self, response):
        """
        Process a streaming response and emit chunks.

        Args:
            response: Streaming response from API

        Returns:
            Complete accumulated text
        """
        full_text = ""

        for chunk in response:
            # Check if thread should stop
            if not self._is_running:
                print(f"{self.__class__.__name__} stopped during streaming")
                return full_text

            if chunk.choices and chunk.choices[0].delta.content is not None:
                chunk_text = chunk.choices[0].delta.content
                full_text += chunk_text
                self.chunk_received.emit(chunk_text)

        return full_text

    def handle_error(self, error, context="API request"):
        """
        Handle errors with consistent logging and signaling.

        Args:
            error: Exception that occurred
            context: Context description for the error
        """
        error_msg = f"{context} error: {str(error)}"
        print(error_msg)

        if self._is_running:
            self.error_occurred.emit(error_msg)

    def stop(self):
        """Request the thread to stop gracefully."""
        self._is_running = False

        # Close response if active
        if self._response is not None:
            try:
                close_fn = getattr(self._response, "close", None)
                if callable(close_fn):
                    close_fn()
            except Exception:
                pass
            self._response = None

        # Close HTTP client
        if self._http_client is not None:
            try:
                self._http_client.close()
            except Exception:
                pass
            self._http_client = None

        self.quit()

    def cleanup(self):
        """Clean up resources."""
        if self._http_client is not None:
            try:
                self._http_client.close()
            except Exception:
                pass
            self._http_client = None
        self._response = None

    def run(self):
        """
        Main thread execution method.
        Subclasses should override this to implement specific logic.
        """
        raise NotImplementedError("Subclasses must implement run()")
