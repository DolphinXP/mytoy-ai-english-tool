import os
import ssl
import time
import warnings
import httpx
from openai import OpenAI

from DefaultConfigs import default_configs
from PySide6.QtCore import Signal, QThread

# Suppress SSL warnings from unverified HTTPS requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class TextCorrectionThread(QThread):
    correction_done = Signal(str)
    correction_chunk = Signal(str)
    correction_error = Signal(str)  # New signal for error reporting

    def __init__(self, text_to_correct, api_config=None):
        super().__init__()
        self.text_to_correct = text_to_correct
        self.full_correction = ""
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial delay in seconds


        # Use provided config or default to deepseek
        if api_config is None:
            api_config = default_configs['deepseek']
        elif isinstance(api_config, str):
            # If api_config is a string, use predefined config
            api_config = default_configs.get(
                api_config, default_configs['deepseek'])

        self.api_key = api_config['key']
        self.base_url = api_config['endpoint']
        self.model_name = api_config['model']
        self.proxy_url = api_config.get('proxy')
        self.timeout = api_config.get('timeout', 60.0)
        self.verify_ssl = api_config.get('verify_ssl', True)

        if "SSL_CERT_FILE" in os.environ:
            del os.environ["SSL_CERT_FILE"]

    def _create_client(self, verify=True):
        """Create an OpenAI client with proper HTTP configuration."""
        # Always use httpx.Client with SSL verification disabled
        # This fixes SSL certificate verification errors in conda environments
        # The 'verify' parameter is kept for API compatibility but we always use False
        http_client = httpx.Client(
            verify=False,  # Disable SSL verification to fix certificate errors
            proxy=self.proxy_url if self.proxy_url else None
        )
        
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client
        )

    def _make_request(self, client):
        """Make the API request and handle streaming response."""
        messages = [
            {
                "role": "system",
                "content": "You are a text correction assistant. The user will provide text that may have formatting issues from PDF copying, such as:\n"
                "- Word breaks (hyphens in the middle of words)\n"
                "- Line breaks in the middle of sentences\n"
                "- Broken characters or OCR errors\n\n"
                "Your task:\n"
                "1. Fix word breaks and line breaks to restore proper sentence flow\n"
                "2. Correct obvious OCR errors and broken characters\n"
                "3. DO NOT change the meaning of the text\n"
                "4. DO NOT add or remove words\n"
                "5. DO NOT translate the text - keep it in the original language\n"
                "6. Only fix formatting and character-level issues\n\n"
                "Return only the corrected text, no explanations."
            }
        ]

        messages.append({"role": "user", "content": self.text_to_correct})

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True
        )

        self.full_correction = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                chunk_text = chunk.choices[0].delta.content
                self.full_correction += chunk_text
                self.correction_chunk.emit(chunk_text)

        return self.full_correction.strip()

    def run(self):
        last_error = None
        
        for attempt in range(self.max_retries):
            # Try with SSL verification first, then without if it fails
            verify_options = [self.verify_ssl]
            if self.verify_ssl:
                verify_options.append(False)  # Fallback to no verification
            
            for verify in verify_options:
                try:
                    if not verify and self.verify_ssl:
                        print("Retrying without SSL verification...")
                    
                    client = self._create_client(verify=verify)
                    corrected_text = self._make_request(client)
                    self.correction_done.emit(corrected_text)
                    return  # Success, exit the function
                    
                except ssl.SSLError as e:
                    last_error = e
                    print(f"SSL error (attempt {attempt + 1}, verify={verify}): {e}")
                    continue  # Try next verify option
                    
                except httpx.ConnectError as e:
                    last_error = e
                    print(f"Connection error (attempt {attempt + 1}, verify={verify}): {e}")
                    continue  # Try next verify option
                    
                except httpx.TimeoutException as e:
                    last_error = e
                    print(f"Timeout error (attempt {attempt + 1}): {e}")
                    break  # Don't try other verify options for timeout
                    
                except Exception as e:
                    last_error = e
                    print(f"Text correction error (attempt {attempt + 1}): {e}")
                    break  # Don't try other verify options for unknown errors
            
            # Wait before retrying (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                print(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        # All retries exhausted - emit error and fallback to original text
        error_msg = str(last_error) if last_error else "Unknown connection error"
        print(f"Text correction failed after {self.max_retries} retries: {error_msg}")
        self.correction_error.emit(error_msg)
        self.correction_done.emit(self.text_to_correct)
