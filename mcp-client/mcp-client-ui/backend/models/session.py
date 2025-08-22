"""Session-related data models."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator


class MessageEntry(BaseModel):
    """Individual message entry in a conversation."""
    timestamp: str
    user_message: str
    ai_response: str
    tools_used: List[str] = []


class ConversationSession(BaseModel):
    """Conversation session data model."""
    conversation_id: str
    messages: List[MessageEntry] = []
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    phase: Optional[str] = None
    specification_generated: bool = False
    specification_data: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionStats(BaseModel):
    """Session statistics model."""
    total_sessions: int
    total_messages: int
    average_messages_per_session: float
    oldest_session_age_hours: float
    newest_session_age_hours: float