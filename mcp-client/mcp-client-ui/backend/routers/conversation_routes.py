"""
Conversation Routes

API endpoints for managing project conversations:
- Store messages
- Retrieve conversation history
- Get context for LLM
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from services.conversation_storage import ConversationStorage
from services.authentication_service import AuthenticationService

logger = logging.getLogger(__name__)

class MessageRequest(BaseModel):
    project_name: str
    role: str  # "user" or "assistant"
    content: str

class ConversationHistoryRequest(BaseModel):
    project_name: str
    limit: Optional[int] = None

def create_conversation_router(auth_service: AuthenticationService = None) -> APIRouter:
    router = APIRouter(prefix="/api/conversations", tags=["conversations"])
    conversation_storage = ConversationStorage()
    
    @router.post("/message")
    async def store_message(request: MessageRequest):
        """Store a new message in the conversation"""
        try:
            # Get user ID if authenticated (optional for now)
            user_id = None  # We can add auth later if needed
            
            message = await conversation_storage.store_message(
                project_name=request.project_name,
                role=request.role,
                content=request.content,
                user_id=user_id
            )
            
            return {
                "success": True,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/history")
    async def get_conversation_history(request: ConversationHistoryRequest):
        """Get conversation history for a project"""
        try:
            messages = await conversation_storage.get_conversation_history(
                project_name=request.project_name,
                limit=request.limit
            )
            
            return {
                "success": True,
                "project_name": request.project_name,
                "messages": messages,
                "count": len(messages)
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/context/{project_name}")
    async def get_llm_context(project_name: str):
        """Get optimized context for LLM"""
        try:
            context = await conversation_storage.get_context_for_llm(project_name)
            
            return {
                "success": True,
                "project_name": project_name,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"Error getting LLM context: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/info")
    async def get_storage_info():
        """Get storage configuration info"""
        try:
            info = conversation_storage.get_bucket_info()
            return {
                "success": True,
                "storage_info": info
            }
            
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router