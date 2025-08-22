"""Session management service."""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

from config.settings import settings
from models.session import ConversationSession, MessageEntry, SessionStats


class SessionManager:
    """Manages conversation sessions with persistence."""
    
    def __init__(self):
        """Initialize the SessionManager."""
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage for conversation sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timestamps: Dict[str, datetime] = {}
        
        # Configuration
        self._max_sessions = settings.MAX_SESSIONS
        self._session_timeout_hours = settings.SESSION_TIMEOUT_HOURS
        
        # Note: Using in-memory storage only for simplicity
    
    def create_session(self, conversation_id: Optional[str] = None, phase: Optional[str] = None) -> str:
        """Create a new conversation session."""
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        session_data = {
            'conversation_id': conversation_id,
            'messages': [],
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'message_count': 0,
            'phase': phase,
            'specification_generated': False,
            'specification_data': None
        }
        
        self._sessions[conversation_id] = session_data
        self._session_timestamps[conversation_id] = datetime.utcnow()
        
        # Session created in memory only
        
        # Cleanup if needed
        self._cleanup_old_sessions()
        
        return conversation_id
    
    def get_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation session by ID."""
        if conversation_id in self._sessions:
            self._sessions[conversation_id]['last_activity'] = datetime.utcnow()
            return self._sessions[conversation_id]
        
        # Session not found in memory
        
        return None
    
    def update_session(self, conversation_id: str, message: str, response: str, tools_used: Optional[List[str]] = None) -> bool:
        """Update a session with new message and response."""
        if conversation_id not in self._sessions:
            return False
        
        session = self._sessions[conversation_id]
        
        message_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_message': message,
            'ai_response': response,
            'tools_used': tools_used or []
        }
        
        session['messages'].append(message_entry)
        session['message_count'] += 1
        session['last_activity'] = datetime.utcnow()
        
        # Session updated in memory
        
        return True
    
    def session_exists(self, conversation_id: str) -> bool:
        """Check if a conversation session exists."""
        return conversation_id in self._sessions
    
    def get_session_count(self) -> int:
        """Get the total number of active sessions."""
        return len(self._sessions)
    
    def get_session_stats(self) -> SessionStats:
        """Get statistics about current sessions."""
        if not self._sessions:
            return SessionStats(
                total_sessions=0,
                total_messages=0,
                average_messages_per_session=0,
                oldest_session_age_hours=0,
                newest_session_age_hours=0
            )
        
        current_time = datetime.utcnow()
        total_messages = sum(session.get('message_count', 0) for session in self._sessions.values())
        
        session_ages = []
        for session in self._sessions.values():
            created_at = session.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            age_hours = (current_time - created_at).total_seconds() / 3600
            session_ages.append(age_hours)
        
        return SessionStats(
            total_sessions=len(self._sessions),
            total_messages=total_messages,
            average_messages_per_session=total_messages / len(self._sessions),
            oldest_session_age_hours=max(session_ages) if session_ages else 0,
            newest_session_age_hours=min(session_ages) if session_ages else 0
        )
    
    def cleanup_sessions(self) -> int:
        """Manually trigger session cleanup."""
        return self._cleanup_old_sessions()
    
    def _cleanup_old_sessions(self) -> int:
        """Clean up old sessions based on timeout and max session limits."""
        current_time = datetime.utcnow()
        sessions_to_remove = []
        
        # Find sessions that have timed out
        for conversation_id, session in self._sessions.items():
            last_activity = session.get('last_activity', session.get('created_at'))
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            
            time_diff = current_time - last_activity
            if time_diff.total_seconds() > (self._session_timeout_hours * 3600):
                sessions_to_remove.append(conversation_id)
        
        # Remove excess sessions if over limit
        if len(self._sessions) > self._max_sessions:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1].get('last_activity', x[1].get('created_at'))
            )
            
            excess_count = len(self._sessions) - self._max_sessions
            for i in range(excess_count):
                conversation_id = sorted_sessions[i][0]
                if conversation_id not in sessions_to_remove:
                    sessions_to_remove.append(conversation_id)
        
        # Remove the sessions
        for conversation_id in sessions_to_remove:
            if conversation_id in self._sessions:
                del self._sessions[conversation_id]
            if conversation_id in self._session_timestamps:
                del self._session_timestamps[conversation_id]
        
        return len(sessions_to_remove)
    
    # JSON persistence methods removed - using in-memory only for simplicity
    
    def _convert_session_to_json(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Convert session data to JSON-serializable format for API responses."""
        context = session.copy()
        
        # Convert datetime objects to ISO strings
        if isinstance(context.get('created_at'), datetime):
            context['created_at'] = context['created_at'].isoformat()
        if isinstance(context.get('last_activity'), datetime):
            context['last_activity'] = context['last_activity'].isoformat()
        
        return context
    
    def get_phase_sessions(self, phase: str) -> List[Dict[str, Any]]:
        """Get all sessions for a specific SDLC phase."""
        phase_sessions = []
        for conversation_id, session in self._sessions.items():
            if session.get('phase') == phase:
                phase_sessions.append(session)
        return phase_sessions
    
    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation context in JSON format."""
        session = self.get_session(conversation_id)
        if not session:
            return {}
        
        context = {
            'conversation_id': conversation_id,
            'phase': session.get('phase'),
            'message_count': session.get('message_count', 0),
            'specification_generated': session.get('specification_generated', False),
            'specification_data': session.get('specification_data'),
            'messages': session.get('messages', []),
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity')
        }
        
        return self._convert_session_to_json(context)
    
    def get_all_conversation_ids(self, phase: Optional[str] = None) -> List[str]:
        """Get all conversation IDs in memory, optionally filtered by phase."""
        if phase:
            return [
                conv_id for conv_id, session in self._sessions.items()
                if session.get('phase') == phase
            ]
        else:
            return list(self._sessions.keys())
    
    def get_all_conversations_for_phase(self, phase: str) -> List[Dict[str, Any]]:
        """Get all conversations for a specific phase from memory."""
        conversations = []
        
        for conversation_id, session in self._sessions.items():
            if session.get('phase') == phase:
                context = self.get_conversation_context(conversation_id)
                conversations.append(context)
        
        return conversations