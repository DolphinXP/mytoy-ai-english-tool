"""
Dictionary service for word/phrase lookup with context.
"""
import httpx
from PySide6.QtCore import Signal

from services.api.base_api_thread import BaseAPIThread


class DictionaryThread(BaseAPIThread):
    """Thread for dictionary-style translation with context."""

    translation_done = Signal(str)
    translation_chunk = Signal(str)

    def __init__(self, selected_text, context_text, api_config=None):
        super().__init__(api_config)
        self.selected_text = selected_text
        self.context_text = context_text
        self.full_translation = ""

        # Connect base signals to specific signals
        self.chunk_received.connect(self.translation_chunk.emit)

    def _get_system_prompt(self):
        """Get the system prompt for dictionary lookup."""
        return """You are a professional dictionary and translation assistant. Your task is to provide dictionary-style explanations with context-aware translations.

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

    def run(self):
        """Execute dictionary lookup."""
        try:
            # Check if thread should stop before starting
            if not self._is_running:
                return

            user_message = f"""Selected text: "{self.selected_text}"

Context: "{self.context_text[:500]}..."

Please provide a dictionary-style explanation for the selected text, considering its context."""

            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_message}
            ]

            response = self.make_streaming_request(messages)

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
        finally:
            self.cleanup()
