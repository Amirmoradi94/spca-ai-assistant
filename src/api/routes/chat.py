"""Chat API routes."""

import logging
import time
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..schemas import ChatRequest, ChatResponse, SessionInfo
from ...chatbot.gemini_client import GeminiChatbot, get_chatbot
from ...chatbot.session_manager import SessionManager, get_session_manager
from ...database.session import get_db_session
from ...database.repositories.conversation_repository import (
    ConversationRepository,
    ConversationMessageRepository,
)
from ...database.models import ConversationMessage
from ...analytics.topic_extractor import extract_topic
from ...analytics.animal_tracker import extract_animal_references

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
    http_request: Request,
    chatbot: GeminiChatbot = Depends(get_chatbot_service),
    db_session = Depends(get_db_session),
) -> ChatResponse:
    """
    Send a message to the chatbot and receive a response.

    The chatbot uses Google Gemini with File Search to provide
    information about animals available for adoption and SPCA services.
    """
    start_time = time.time()
    error_occurred = False
    sources_count = 0
    
    try:
        # Get or create conversation in database
        conv_repo = ConversationRepository(db_session)
        msg_repo = ConversationMessageRepository(db_session)
        
        # Get client IP and hash it for privacy
        client_ip = http_request.client.host if http_request.client else None
        ip_hash = None
        if client_ip:
            ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()
        
        user_agent = http_request.headers.get("user-agent")
        referrer = http_request.headers.get("referer")
        
        # Get or create conversation
        conversation, is_new = await conv_repo.get_or_create_by_session_id(
            session_id=request.session_id or "unknown",
            language=request.language,
            user_ip_hash=ip_hash,
            user_agent=user_agent,
            referrer=referrer,
        )
        
        # Log user message
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
            timestamp=datetime.utcnow(),
        )
        await msg_repo.create(user_msg)
        await conv_repo.increment_message_count(request.session_id or "unknown")
        
        # Generate response
        result = await chatbot.generate_response(
            message=request.message,
            session_id=request.session_id,
            language=request.language,
            context=request.context,
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        sources_count = len(result.get("sources", []))
        
        # Log assistant response
        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=result.get("response", ""),
            timestamp=datetime.utcnow(),
            response_time_ms=response_time_ms,
            sources_count=sources_count,
            error_occurred=False,
        )
        await msg_repo.create(assistant_msg)
        await conv_repo.increment_message_count(request.session_id or "unknown")
        await db_session.commit()
        
        return ChatResponse(**result)

    except Exception as e:
        error_occurred = True
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        
        # Try to log the error message if conversation exists
        try:
            if request.session_id:
                conv_repo = ConversationRepository(db_session)
                conversation = await conv_repo.get_by_session_id(request.session_id)
                if conversation:
                    msg_repo = ConversationMessageRepository(db_session)
                    error_msg = ConversationMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=f"Error: {str(e)}",
                        timestamp=datetime.utcnow(),
                        response_time_ms=int((time.time() - start_time) * 1000),
                        error_occurred=True,
                    )
                    await msg_repo.create(error_msg)
                    await db_session.commit()
        except Exception as log_error:
            logger.error(f"Failed to log error message: {log_error}")
        
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
    db_session = Depends(get_db_session),
) -> dict:
    """
    End a chat session.

    This will remove the session and its history.
    """
    success = await chatbot.end_session(session_id)
    
    # Update conversation in database
    try:
        conv_repo = ConversationRepository(db_session)
        await conv_repo.end_conversation(session_id)
        await db_session.commit()
    except Exception as e:
        logger.warning(f"Failed to update conversation end time: {e}")

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
