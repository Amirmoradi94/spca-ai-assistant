"""Gemini API client for chatbot responses."""

import os
import logging
from typing import Optional

import google.generativeai as genai

from .prompt_templates import get_system_prompt, get_suggested_questions
from .session_manager import ChatSession, get_session_manager

logger = logging.getLogger(__name__)


class GeminiChatbot:
    """Chatbot using Google Gemini with File Search."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        genai.configure(api_key=self.api_key)
        self.model_name = model_name
        self.session_manager = get_session_manager()

        # Get uploaded files for RAG
        self._files: list = []
        self._load_files()

    def _load_files(self) -> None:
        """Load list of uploaded files for RAG."""
        try:
            self._files = list(genai.list_files())
            logger.info(f"Loaded {len(self._files)} files for RAG")
        except Exception as e:
            logger.warning(f"Failed to load files: {e}")
            self._files = []

    def _get_model(self, language: str = "en") -> genai.GenerativeModel:
        """Get a configured Gemini model."""
        system_instruction = get_system_prompt(language)

        return genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1024,
            ),
        )

    async def generate_response(
        self,
        message: str,
        session_id: Optional[str] = None,
        language: str = "en",
        context: Optional[dict] = None,
    ) -> dict:
        """Generate a response to a user message."""
        # Get or create session
        session = self.session_manager.get_or_create_session(
            session_id=session_id,
            language=language,
        )

        # Add user message to history
        session.add_message("user", message)

        try:
            # Get model
            model = self._get_model(language)

            # Build content with history and files
            contents = self._build_contents(session, message)

            # Generate response
            response = model.generate_content(contents)

            # Extract response text
            response_text = response.text if response.text else "I'm sorry, I couldn't generate a response."

            # Add assistant response to history
            session.add_message("assistant", response_text)

            # Get sources (file citations)
            sources = self._extract_sources(response)

            return {
                "response": response_text,
                "session_id": session.session_id,
                "sources": sources,
                "suggested_questions": get_suggested_questions(language)[:3],
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")

            # Add error message to history
            error_msg = "I apologize, but I encountered an error. Please try again."
            session.add_message("assistant", error_msg)

            return {
                "response": error_msg,
                "session_id": session.session_id,
                "sources": [],
                "suggested_questions": get_suggested_questions(language)[:3],
                "error": str(e),
            }

    def _build_contents(self, session: ChatSession, current_message: str) -> list:
        """Build content list with history and files."""
        contents = []

        # Add relevant files for RAG
        # Filter to get only processed/active files
        active_files = [
            f for f in self._files
            if hasattr(f, 'state') and f.state.name == 'ACTIVE'
        ]

        # Add files to content (Gemini will use them for context)
        if active_files:
            # Add a sample of files (too many can slow down)
            for f in active_files[:20]:
                contents.append(f)

        # Add conversation history
        history = session.get_history(limit=10)
        for msg in history[:-1]:  # Exclude current message
            contents.append(msg)

        # Add current message
        contents.append({
            "role": "user",
            "parts": [current_message],
        })

        return contents

    def _extract_sources(self, response) -> list[dict]:
        """Extract source citations from response."""
        sources = []

        # Check for grounding metadata
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                metadata = candidate.grounding_metadata
                if hasattr(metadata, 'grounding_chunks'):
                    for chunk in metadata.grounding_chunks:
                        sources.append({
                            "file": getattr(chunk, 'file_name', 'Unknown'),
                            "snippet": getattr(chunk, 'text', '')[:200],
                        })

        return sources

    async def create_session(self, language: str = "en") -> dict:
        """Create a new chat session."""
        session = self.session_manager.create_session(language=language)
        return session.to_dict()

    async def end_session(self, session_id: str) -> bool:
        """End a chat session."""
        return self.session_manager.end_session(session_id)

    async def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get information about a session."""
        session = self.session_manager.get_session(session_id)
        if session:
            return session.to_dict()
        return None

    def refresh_files(self) -> None:
        """Refresh the list of uploaded files."""
        self._load_files()


# Global chatbot singleton
_chatbot: Optional[GeminiChatbot] = None


def get_chatbot() -> GeminiChatbot:
    """Get the global chatbot instance."""
    global _chatbot
    if _chatbot is None:
        _chatbot = GeminiChatbot()
    return _chatbot
