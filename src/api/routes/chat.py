"""Chat API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..schemas import ChatRequest, ChatResponse, SessionInfo
from ...chatbot.gemini_client import GeminiChatbot, get_chatbot
from ...chatbot.session_manager import SessionManager, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_chatbot_service() -> GeminiChatbot:
    """Dependency to get chatbot instance."""
    return get_chatbot()


def get_session_service() -> SessionManager:
    """Dependency to get session manager."""
    return get_session_manager()


@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    chatbot: GeminiChatbot = Depends(get_chatbot_service),
) -> ChatResponse:
    """
    Send a message to the chatbot and receive a response.

    The chatbot uses Google Gemini with File Search to provide
    information about animals available for adoption and SPCA services.
    """
    try:
        result = await chatbot.generate_response(
            message=request.message,
            session_id=request.session_id,
            language=request.language,
            context=request.context,
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.post("/session", response_model=SessionInfo)
async def create_session(
    language: str = "en",
    chatbot: GeminiChatbot = Depends(get_chatbot_service),
) -> SessionInfo:
    """
    Create a new chat session.

    Sessions are used to maintain conversation context and history.
    They expire after 1 hour of inactivity.
    """
    try:
        session_data = await chatbot.create_session(language=language)
        return SessionInfo(**session_data)

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    chatbot: GeminiChatbot = Depends(get_chatbot_service),
) -> SessionInfo:
    """Get information about a chat session."""
    session_data = await chatbot.get_session_info(session_id)

    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )

    return SessionInfo(**session_data)


@router.delete("/session/{session_id}")
async def end_session(
    session_id: str,
    chatbot: GeminiChatbot = Depends(get_chatbot_service),
) -> dict:
    """
    End a chat session.

    This will remove the session and its history.
    """
    success = await chatbot.end_session(session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {"status": "session ended", "session_id": session_id}


@router.post("/refresh-files")
async def refresh_files(
    chatbot: GeminiChatbot = Depends(get_chatbot_service),
) -> dict:
    """
    Refresh the list of files available for RAG.

    Call this after uploading new content to Google File Search.
    """
    try:
        chatbot.refresh_files()
        return {"status": "success", "message": "Files refreshed"}
    except Exception as e:
        logger.error(f"Error refreshing files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh files: {str(e)}"
        )


@router.get("/stats")
async def get_stats(
    session_manager: SessionManager = Depends(get_session_service),
) -> dict:
    """Get chatbot statistics."""
    return {
        "active_sessions": session_manager.get_session_count(),
        "max_sessions": session_manager.max_sessions,
    }
