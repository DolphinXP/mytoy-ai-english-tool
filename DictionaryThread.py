import os
import warnings
import httpx
from openai import OpenAI

from PySide6.QtCore import Signal, QThread

# Suppress SSL warnings from unverified HTTPS requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class DictionaryThread(QThread):
    """Thread for quick dictionary translation with context"""
    translation_done = Signal(str)
    translation_chunk = Signal(str)

    def __init__(self, selected_text, context_text, api_config=None):
        super().__init__()
        self.selected_text = selected_text
        self.context_text = context_text
        self.full_translation = ""
        self._is_running = True  # Flag to check if thread should continue

        # Default API configurations
        default_configs = {
            'deepseek': {
                'endpoint': "https://api.deepseek.com",
                'key': "YOUR_API_KEY_HERE",
                'model': "deepseek-chat",
                'proxy': None
            },
        }

        # Use provided config or default to deepseek
        if api_config is None:
            api_config = default_configs['deepseek']
        elif isinstance(api_config, str):
            api_config = default_configs.get(
                api_config, default_configs['deepseek'])

        self.api_key = api_config['key']
        self.base_url = api_config['endpoint']
        self.model_name = api_config['model']
        self.proxy_url = api_config.get('proxy')

        if "SSL_CERT_FILE" in os.environ:
            del os.environ["SSL_CERT_FILE"]

    def stop(self):
        """Request the thread to stop gracefully"""
        self._is_running = False
        self.quit()

    def run(self):
        try:
            # Check if thread should stop before starting
            if not self._is_running:
                return

            # Create HTTP client with SSL verification disabled
            http_client = httpx.Client(
                verify=False,
                proxy=self.proxy_url if self.proxy_url else None
            )

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=http_client
            )

            # Build system prompt for dictionary-style translation
            system_prompt = """You are a helpful dictionary and translation assistant.
When given a word or phrase with its context, provide:
1. Translation (English ↔ Chinese, based on the original language)
2. Brief explanation or definition
3. If it's a word: pronunciation guide (if applicable), part of speech
4. Usage example based on the provided context

Keep the response concise but informative. Format nicely for reading.
If the text is English, translate to Chinese and explain.
If the text is Chinese or other language, translate to English and explain."""

            # Build user message with context
            user_message = f"""Selected text: "{self.selected_text}"

Context: "{self.context_text[:500]}..."

Please provide a dictionary-style explanation for the selected text, considering its context."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True
            )

            self.full_translation = ""
            for chunk in response:
                # Check if thread should stop
                if not self._is_running:
                    print("Dictionary thread stopped during streaming")
                    return

                if chunk.choices and chunk.choices[0].delta.content is not None:
                    chunk_text = chunk.choices[0].delta.content
                    self.full_translation += chunk_text
                    self.translation_chunk.emit(chunk_text)

            # Only emit done if thread wasn't stopped
            if self._is_running:
                translated_text = self.full_translation.strip()
                self.translation_done.emit(translated_text)

        except httpx.ConnectError as e:
            print(f"Dictionary connection error: {e}")
            if self._is_running:
                self.translation_chunk.emit(f"❌ Connection error: {e}")
                self.translation_done.emit("")
        except httpx.TimeoutException as e:
            print(f"Dictionary timeout error: {e}")
            if self._is_running:
                self.translation_chunk.emit(f"❌ Timeout error: {e}")
                self.translation_done.emit("")
        except Exception as e:
            print(f"Dictionary error: {e}")
            if self._is_running:
                self.translation_chunk.emit(f"❌ Error: {e}")
                self.translation_done.emit("")
