import os
import warnings
import httpx
from openai import OpenAI

from DefaultConfigs import default_configs
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
            system_prompt = """You are a professional dictionary and translation assistant. Your task is to provide dictionary-style explanations with context-aware translations.

## Core Requirements:
1. **Language Direction**: If the selected text is English, translate to Chinese; if Chinese, translate to English.
2. **Structure**: Organize information into clear, readable sections.
3. **Conciseness**: Keep explanations focused but comprehensive.

## Required Sections:
### 1. Primary Translation
- Display clear bilingual pairing (e.g., English → Chinese)
- Use natural, context-appropriate translations

### 2. Detailed Definition
- Provide accurate, context-aware explanation
- Include part of speech (for single words)
- Add pronunciation guide (for English words, use IPA or pinyin)

### 3. Comprehensive Examples
- Include at least 2 context-rich examples
- Show usage in different sentence structures
- Translate examples to target language
- Relate examples to the provided context when possible

### 4. Additional Notes (if applicable)
- Synonyms and antonyms
- Collocations (common word combinations)
- Register (formal/informal, technical/everyday)
- Cultural notes

## Formatting Guidelines:
- Use markdown-like formatting for readability
- Emphasize key terms
- Keep line breaks between sections
- Use simple, easy-to-understand language

## Example Output Structure:
**Word/Phrase**: "serendipity"
**Translation**: 机缘巧合 / jī yuán qiǎo hé
**Part of Speech**: Noun
**Pronunciation**: /ˌser.ənˈdɪp.ə.ti/ (sair-uhn-DIP-uh-tee)
**Definition**: The occurrence of events by chance in a happy or beneficial way; fortunate coincidences that happen unexpectedly.
**Examples**:
1. Finding that rare book in a second-hand shop was pure serendipity.  
   (在二手书店找到那本珍本书纯属机缘巧合。)
2. Their collaboration began through a series of serendipitous encounters.  
   (他们的合作始于一系列偶然的相遇。)
**Notes**: Often used in positive contexts; similar to "happy accident" but with a more poetic connotation.

Remember to adapt the structure based on whether the input is a single word, phrase, or longer text segment. Keep explanations contextually relevant to the provided surrounding text."""

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
