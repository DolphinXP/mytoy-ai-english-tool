import os
import warnings
import httpx
from openai import OpenAI

from PySide6.QtCore import Signal, QThread
from DefaultConfigs import default_configs

# Suppress SSL warnings from unverified HTTPS requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class TranslationThread(QThread):
    translation_done = Signal(str)
    translation_chunk = Signal(str)

    def __init__(self, text_to_translate, api_config=None):
        super().__init__()
        self.text_to_translate = text_to_translate
        self.full_translation = ""



        # Use provided config or default to deepseek
        if api_config is None:
            api_config = default_configs['deepseek']
        elif isinstance(api_config, str):
            api_config = default_configs.get(
                api_config, default_configs['deepseek'])

        self.api_key = api_config['key']
        self.base_url = api_config['endpoint']
        self.model_name = api_config['model']
        self.proxy_url = api_config['proxy']
        self.timeout = api_config.get('timeout', 30.0)

        if "SSL_CERT_FILE" in os.environ:
            del os.environ["SSL_CERT_FILE"]

    def run(self):
        try:
            # Create HTTP client with SSL verification disabled
            # This fixes SSL certificate verification errors in conda environments
            http_client = httpx.Client(
                verify=False,  # Disable SSL verification to fix certificate errors
                proxy=self.proxy_url if self.proxy_url else None
            )
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=http_client
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a translation assistant. Please translate English to Chinese, and translate all non-English text (including Chinese) to English. "
                    "All text I send you needs to be translated. Just answer with the translation result, don't repeat original text. "
                    "Make the translation conform to the target language's habits. "
                    "Adjust punctuation and format appropriately for readability."
                }
            ]

            messages.append(
                {"role": "user", "content": self.text_to_translate})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True
            )

            self.full_translation = ""
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    chunk_text = chunk.choices[0].delta.content
                    self.full_translation += chunk_text
                    self.translation_chunk.emit(chunk_text)

            translated_text = self.full_translation.strip()
            self.translation_done.emit(translated_text)

        except httpx.ConnectError as e:
            print(f"Translation connection error: {e}")
            # If connection fails, use original text
            self.translation_done.emit(self.text_to_translate)
        except httpx.TimeoutException as e:
            print(f"Translation timeout error: {e}")
            # If timeout, use original text
            self.translation_done.emit(self.text_to_translate)
        except Exception as e:
            print(f"Translation error: {e}")
            self.translation_done.emit(self.text_to_translate)
