"""Gemini API client for chatbot responses."""

import os
import logging
from typing import Optional

from google import genai
from google.genai import types

from .prompt_templates import get_system_prompt, get_suggested_questions
from .session_manager import ChatSession, get_session_manager

logger = logging.getLogger(__name__)


class GeminiChatbot:
    """Chatbot using Google Gemini with File Search."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        # Configure the new genai client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.session_manager = get_session_manager()

        # Get or create file search store
        self.file_search_store_name = None
        self._setup_file_search_store()

        # Get uploaded files for RAG
        self._files: list = []
        self._load_files()

    def _setup_file_search_store(self) -> None:
        """Get or create file search store."""
        try:
            logger.info("Setting up file search store...")
            # List existing file search stores
            stores = list(self.client.file_search_stores.list())
            logger.info(f"Found {len(stores)} existing file search stores")

            # Look for existing store named 'spca_knowledge_base'
            for store in stores:
                if hasattr(store, 'display_name') and store.display_name == 'spca_knowledge_base':
                    self.file_search_store_name = store.name
                    logger.info(f"✓ Using existing file search store: {self.file_search_store_name}")
                    return

            # Create new store if not found
            logger.info("Creating new file search store: spca_knowledge_base")
            store = self.client.file_search_stores.create(
                config={'display_name': 'spca_knowledge_base'}
            )
            self.file_search_store_name = store.name
            logger.info(f"✓ Created file search store: {self.file_search_store_name}")
        except Exception as e:
            import traceback
            logger.error(f"✗ Failed to setup file search store: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.file_search_store_name = None

    def _load_files(self) -> None:
        """Load list of uploaded files for RAG."""
        try:
            # List files using the new client API
            files_response = self.client.files.list()
            self._files = list(files_response)
            logger.info(f"Loaded {len(self._files)} files for RAG")
        except Exception as e:
            logger.warning(f"Failed to load files: {e}")
            self._files = []

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
            logger.info("Step 1: Getting system prompt")
            # Get system prompt
            system_prompt = get_system_prompt(language)

            logger.info("Step 2: Building prompt with history")
            # Build prompt with conversation history
            prompt = self._build_prompt_with_history(session, message)

            logger.info("Step 3: Calling Gemini API with File Search")

            # Build config with File Search tool
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=4096,  # High limit to allow listing many animals with full details
            )

            # Add File Search tool if store is available
            if self.file_search_store_name:
                logger.info(f"✓ Using file search store: {self.file_search_store_name}")
                config.tools = [
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[self.file_search_store_name],
                            topK=30  # Retrieve up to 30 documents for comprehensive results
                        )
                    )
                ]
                logger.info("✓ File Search configured to retrieve up to 30 documents")
            else:
                logger.warning("✗ File search store not available - responses will not use uploaded files")

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            logger.info("Step 4: Got response from Gemini")

            # Extract response text from the new API response
            response_text = response.text if hasattr(response, 'text') and response.text else "I'm sorry, I couldn't generate a response."

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
            import traceback
            logger.error(f"Error generating response: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

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

    def _build_prompt_with_history(self, session: ChatSession, current_message: str) -> str:
        """Build a text prompt with conversation history.

        The new google.genai API works with simple text prompts.
        We include conversation history as context in the prompt.
        """
        # Get conversation history (excluding the current message we just added)
        history_messages = session.messages[:-1] if len(session.messages) > 1 else []

        # Build conversation context
        if history_messages:
            context_parts = ["Previous conversation:"]
            for msg in history_messages[-10:]:  # Last 10 messages
                role = "User" if msg.role == "user" else "Assistant"
                context_parts.append(f"{role}: {msg.content}")
            context_parts.append("\nCurrent question:")
            context = "\n".join(context_parts)
            return f"{context}\n{current_message}"
        else:
            return current_message

    def _extract_sources(self, response) -> list[dict]:
        """Extract source citations from response.

        Only includes sources with valid file names and content.
        """
        sources = []

        # Check for grounding metadata
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                metadata = candidate.grounding_metadata
                if hasattr(metadata, 'grounding_chunks'):
                    chunk_count = len(metadata.grounding_chunks)
                    logger.info(f"📊 File Search retrieved {chunk_count} chunks (documents)")

                    # Count animal chunks
                    animal_chunks = 0
                    for chunk in metadata.grounding_chunks:
                        file_name = getattr(chunk, 'file_name', None)
                        snippet = getattr(chunk, 'text', '')

                        if file_name and file_name.startswith('animal_'):
                            animal_chunks += 1

                        # Only include sources with valid file names and non-empty snippets
                        if file_name and file_name != 'Unknown' and snippet.strip():
                            sources.append({
                                "file": file_name,
                                "snippet": snippet,
                            })

                    logger.info(f"📝 Retrieved {animal_chunks} animal documents out of {chunk_count} total chunks")
                    logger.info(f"📝 Returning {len(sources)} valid sources to user")

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
