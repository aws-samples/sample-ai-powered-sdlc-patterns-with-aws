"""
Response Models - Exact copies from original main.py

All Pydantic response models maintaining full compatibility.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatboxResponse(BaseModel):
    """Response model for chatbox conversations"""
    response: str
    conversation_id: str
    status: str
    timestamp: str
    tools_used: List[str] = []

class PhaseSpecificChatResponse(BaseModel):
    """Response model for phase-specific chat conversations"""
    response: str
    conversation_id: str
    status: str
    timestamp: str
    tools_used: List[str] = []
    specification_updated: bool = False
    specification: Optional[Dict[str, Any]] = None
    processing_indicator: Optional[Dict[str, Any]] = None
    canvas_posted: bool = False
    diagrams: Optional[List[Dict[str, Any]]] = None
    diagram_generation_status: Optional[str] = None
    diagram_generation_error: Optional[str] = None