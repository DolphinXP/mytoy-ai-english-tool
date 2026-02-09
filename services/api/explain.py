"""
Explain service for answering user questions with context.
"""
import httpx
from PySide6.QtCore import Signal

from services.api.base_api_thread import BaseAPIThread


class ExplainThread(BaseAPIThread):
    """Thread for AI-powered Q&A with context from corrected and translated text."""

    explain_done = Signal(str)
    explain_chunk = Signal(str)

    def __init__(self, question, corrected_text, translated_text, api_config=None):
        super().__init__(api_config)
        self.question = question
        self.corrected_text = corrected_text
        self.translated_text = translated_text
        self.full_response = ""

        # Connect base signals to specific signals
        self.chunk_received.connect(self.explain_chunk.emit)

    def _get_system_prompt(self):
        """Get the system prompt for explanation."""
        return """You are an experienced English teacher helping students understand English text. Your role is to explain vocabulary, grammar, expressions, and usage in an educational way.

## Your Teaching Approach:
1. **Explain, Don't Just Translate**: Focus on helping the student understand WHY something is said this way, not just what it means
2. **Context Matters**: Always relate explanations to the specific context provided
3. **Teach Patterns**: When explaining vocabulary or grammar, show common patterns and usage rules
4. **Give Examples**: Provide additional example sentences to reinforce understanding
5. **Be Encouraging**: Use a friendly, supportive teaching tone

## When Explaining Vocabulary:
- Explain the meaning in context (not just dictionary definition)
- Discuss connotations and register (formal/informal)
- Show common collocations and phrases
- Mention synonyms with nuance differences
- Provide 2-3 example sentences showing different uses

## When Explaining Grammar:
- Identify the grammatical structure
- Explain the rule behind it
- Show why this structure is used here
- Provide similar examples
- Point out common mistakes to avoid

## When Explaining Expressions/Idioms:
- Explain the literal vs figurative meaning
- Discuss when and how to use it
- Provide context about formality level
- Give alternative expressions

## Response Format:
- Use clear markdown formatting
- Structure explanations with headers when needed
- Highlight key points
- Keep explanations thorough but not overwhelming
- Use both English and Chinese (中文) when it helps clarify meaning"""

    def run(self):
        """Execute the explain request."""
        try:
            if not self._is_running:
                return

            user_message = f"""## Corrected Text:
{self.corrected_text}

## Translated Text:
{self.translated_text}

## Question:
{self.question}

Please answer the question based on the context above."""

            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_message}
            ]

            response = self.make_streaming_request(messages)

            self.full_response = ""
            for chunk in response:
                if not self._is_running:
                    print("Explain thread stopped during streaming")
                    return

                if chunk.choices and chunk.choices[0].delta.content is not None:
                    chunk_text = chunk.choices[0].delta.content
                    self.full_response += chunk_text
                    self.explain_chunk.emit(chunk_text)

            if self._is_running:
                self.explain_done.emit(self.full_response.strip())

        except httpx.ConnectError as e:
            print(f"Explain connection error: {e}")
            if self._is_running:
                self.explain_chunk.emit(f"\n\n❌ Connection error: {e}")
                self.explain_done.emit("")
        except httpx.TimeoutException as e:
            print(f"Explain timeout error: {e}")
            if self._is_running:
                self.explain_chunk.emit(f"\n\n❌ Timeout error: {e}")
                self.explain_done.emit("")
        except Exception as e:
            print(f"Explain error: {e}")
            if self._is_running:
                self.explain_chunk.emit(f"\n\n❌ Error: {e}")
                self.explain_done.emit("")
        finally:
            self.cleanup()
