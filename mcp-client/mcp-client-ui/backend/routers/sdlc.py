"""
SDLC Router Module

FastAPI router for Software Development Life Cycle (SDLC) endpoints.
Provides dedicated endpoints for each SDLC phase: Requirements, Design, 
Development, Testing, Deployment, and Maintenance.
"""

from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
import re
import base64
import logging
import io
import json
import asyncio
from services.conversation_storage import ConversationStorage
from models.auth_models import UserClaims
from middleware.auth_middleware import get_current_user_dependency


class SDLCChatboxRequest(BaseModel):
    """Request model for SDLC-specific chatbox interactions"""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    message: str
    conversation_id: Optional[str] = None
    phase: Optional[str] = None  # Will be set by the endpoint
    project_name: Optional[str] = None
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v.strip()) > 10000:
            raise ValueError('Message too long (maximum 10000 characters)')
        return v.strip()
    
    @field_validator('conversation_id')
    @classmethod
    def validate_conversation_id(cls, v):
        if v is not None:
            if not isinstance(v, str) or not v.strip():
                raise ValueError('Conversation ID must be a non-empty string')
            if len(v.strip()) > 100:
                raise ValueError('Conversation ID too long (maximum 100 characters)')
            # Allow alphanumeric, hyphens, and underscores
            if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
                raise ValueError('Conversation ID can only contain letters, numbers, hyphens, and underscores')
            return v.strip()
        return v
    
    @field_validator('phase')
    @classmethod
    def validate_phase(cls, v):
        if v is not None:  # Phase is optional in request, set by endpoint
            allowed_phases = ['requirements', 'design', 'development', 'testing', 'deployment', 'maintenance']
            if v not in allowed_phases:
                raise ValueError(f'Phase must be one of: {", ".join(allowed_phases)}')
        return v
    
    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v):
        if v is not None:
            if not isinstance(v, str) or not v.strip():
                raise ValueError('Project name must be a non-empty string')
            if len(v.strip()) > 100:
                raise ValueError('Project name too long (maximum 100 characters)')
            # Allow alphanumeric, hyphens, underscores, and spaces
            if not re.match(r'^[a-zA-Z0-9_\-\s]+$', v.strip()):
                raise ValueError('Project name can only contain letters, numbers, hyphens, underscores, and spaces')
            return v.strip()
        return v





class DiagramData(BaseModel):
    """Model for diagram data within SDLC responses"""
    model_config = ConfigDict(
        json_encoders={
            bytes: lambda v: base64.b64encode(v).decode('utf-8') if v else None
        }
    )
    
    diagram_type: str  # "architecture", "sequence", "entity_relationship", etc.
    diagram_url: Optional[str] = None  # URL to diagram if stored externally
    diagram_data: Optional[Union[str, bytes]] = None  # Base64 encoded or raw diagram data
    diagram_metadata: Optional[Dict[str, Any]] = None  # Additional metadata like format, size, description
    
    @field_validator('diagram_type')
    @classmethod
    def validate_diagram_type(cls, v):
        allowed_types = [
            'architecture', 'sequence', 'entity_relationship', 'flowchart', 
            'component', 'deployment', 'class', 'use_case', 'network', 'other'
        ]
        if v not in allowed_types:
            raise ValueError(f'Diagram type must be one of: {", ".join(allowed_types)}')
        return v
    
    @field_validator('diagram_data')
    @classmethod
    def validate_diagram_data(cls, v):
        if v is not None:
            if isinstance(v, bytes):
                # Convert bytes to base64 string for JSON serialization
                return base64.b64encode(v).decode('utf-8')
            elif isinstance(v, str):
                # Validate that it's a valid base64 string if provided as string
                try:
                    base64.b64decode(v)
                    return v
                except Exception:
                    # If not valid base64, assume it's raw text data
                    return v
        return v


class SDLCChatboxResponse(BaseModel):
    """Response model for SDLC-specific chatbox interactions"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            bytes: lambda v: base64.b64encode(v).decode('utf-8') if v else None
        }
    )
    
    response: str
    conversation_id: str
    phase: str
    status: str
    timestamp: str
    tools_used: Optional[list] = None
    tool_status: Optional[str] = None  # Add tool status for frontend loading indicators
    specification_updated: bool = False
    specification: Optional[Dict[str, Any]] = None
    processing_indicator: Optional[Dict[str, Any]] = None
    canvas_posted: bool = False
    processing_status: Optional[str] = None
    jira_data_updated: bool = False  # Add Jira data update flag
    
    # Enhanced diagram-related fields for MCP integration
    diagrams: Optional[List[DiagramData]] = None
    






class SDLCRouter:
    """Router class for handling SDLC phase endpoints"""
    
    def __init__(self, chatbox_manager, auth_service=None):
        """
        Initialize SDLC router with chatbox manager dependency
        
        Args:
            chatbox_manager: ChatboxManager instance for handling conversations
            auth_service: Authentication service for user validation
        """
        self.chatbox_manager = chatbox_manager
        self.conversation_storage = ConversationStorage()
        self.logger = logging.getLogger(__name__)
        self.router = APIRouter(prefix="/api/sdlc", tags=["SDLC"])
        self.auth_service = auth_service
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up all SDLC phase routes"""
        
        @self.router.post("/requirements")
        async def requirements_endpoint(
            request: SDLCChatboxRequest,
            http_request: Request
        ):
            """Requirements gathering streaming chatbox endpoint"""
            request.phase = "requirements"
            return await self._handle_streaming_phase_request(request, http_request)
        
        @self.router.post("/design")
        async def design_endpoint(
            request: SDLCChatboxRequest,
            http_request: Request
        ):
            """Design and architecture streaming chatbox endpoint"""
            request.phase = "design"
            return await self._handle_streaming_phase_request(request, http_request)
        
        @self.router.post("/development")
        async def development_endpoint(
            request: SDLCChatboxRequest,
            http_request: Request
        ):
            """Development planning streaming chatbox endpoint"""
            request.phase = "development"
            return await self._handle_streaming_phase_request(request, http_request)
        
        @self.router.post("/testing")
        async def testing_endpoint(
            request: SDLCChatboxRequest,
            http_request: Request
        ):
            """Testing strategy streaming chatbox endpoint"""
            request.phase = "testing"
            return await self._handle_streaming_phase_request(request, http_request)
        
        @self.router.post("/deployment")
        async def deployment_endpoint(
            request: SDLCChatboxRequest,
            http_request: Request
        ):
            """Deployment planning streaming chatbox endpoint"""
            request.phase = "deployment"
            return await self._handle_streaming_phase_request(request, http_request)
        
        @self.router.post("/maintenance")
        async def maintenance_endpoint(
            request: SDLCChatboxRequest,
            http_request: Request
        ):
            """Maintenance procedures streaming chatbox endpoint"""
            request.phase = "maintenance"
            return await self._handle_streaming_phase_request(request, http_request)
        

        
        @self.router.get("/conversation/{project_name}")
        async def get_project_conversation_history(project_name: str):
            """Get conversation history for a project - loads when user opens project"""
            try:
                messages = await self.conversation_storage.get_conversation_history(project_name)
                
                return {
                    "success": True,
                    "project_name": project_name,
                    "messages": messages,
                    "count": len(messages)
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error loading conversation history: {str(e)}"
                )
    

    
    async def _handle_streaming_phase_request(self, request: SDLCChatboxRequest, http_request: Request) -> StreamingResponse:
        """
        Handle streaming requests for specific SDLC phases
        
        Args:
            request: SDLCChatboxRequest containing message, conversation_id, and phase
            
        Returns:
            StreamingResponse: Server-sent events stream with AI response chunks
            
        Raises:
            HTTPException: For validation errors or internal server errors
        """
        try:
            self.logger.info(f"Starting streaming phase request for phase: {request.phase}, project: {request.project_name}")
            
            # Store user message first if project_name is provided
            if request.project_name:
                await self.conversation_storage.store_message(
                    project_name=request.project_name,
                    role="user",
                    content=request.message,
                    user_id=None
                )
                
                # Get conversation context for LLM
                try:
                    conversation_context = await self.conversation_storage.get_context_for_llm(request.project_name)
                except Exception as e:
                    self.logger.error(f"Error getting conversation context: {e}", exc_info=True)
                    conversation_context = None
                
                # Get project-specific KB context
                try:
                    from services.simple_tool_service import SimpleToolService
                    
                    # Use the new Bedrock KB service via SimpleToolService
                    self.logger.info("Getting KB context for streaming response...")
                    tool_service = SimpleToolService()
                    # Skip MCP initialization for KB-only usage
                    
                    phase_query = f"{request.phase} phase {request.message}"
                    kb_results = await tool_service.get_project_context(
                        project_name=request.project_name,
                        query=phase_query
                    )
                    
                    self.logger.info(f"KB context retrieved: {kb_results.get('total_results', 0)} results")
                    
                    if conversation_context is None:
                        conversation_context = {}
                    
                    conversation_context['kb_context'] = {
                        'relevant_conversations': kb_results.get('relevant_context', {}).get('documents', [])[:3],
                        'relevant_code': kb_results.get('relevant_context', {}).get('code', [])[:2],
                        'relevant_diagrams': kb_results.get('relevant_context', {}).get('other', [])[:2],
                        'context_quality': kb_results.get('total_results', 0),
                        'phase': request.phase
                    }
                    
                except Exception as e:
                    self.logger.warning(f"KB context retrieval failed (continuing without): {e}")
                    
            else:
                conversation_context = None
            
            # Generate phase-specific conversation ID if not provided
            if not request.conversation_id:
                if request.project_name:
                    safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '-', request.project_name.lower())
                    request.conversation_id = f"{request.phase}_{safe_project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                else:
                    request.conversation_id = f"{request.phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                if not request.conversation_id.startswith(f"{request.phase}_"):
                    request.conversation_id = f"{request.phase}_{request.conversation_id}"
            
            # Create streaming response generator
            async def generate_streaming_response():
                try:
                    # Send initial metadata
                    initial_data = {
                        "type": "metadata",
                        "conversation_id": request.conversation_id,
                        "phase": request.phase,
                        "timestamp": datetime.now().isoformat(),
                        "status": "streaming"
                    }
                    yield f"data: {json.dumps(initial_data)}\n\n"
                    
                    # Get streaming response from chatbox manager
                    full_response = ""
                    tools_used = []
                    
                    # Extract ID token from request headers (Amazon Q Business needs ID token, not access token)
                    id_token = http_request.headers.get("x-id-token")
                    
                    # Fallback: Extract access token from Authorization header
                    access_token = None
                    if hasattr(http_request, 'state') and hasattr(http_request.state, 'jwt_token'):
                        access_token = http_request.state.jwt_token
                        self.logger.info(f"Access token found in request state: {access_token[:30] if access_token else 'None'}...")
                    else:
                        auth_header = http_request.headers.get("authorization")
                        if auth_header and auth_header.startswith("Bearer "):
                            access_token = auth_header[7:]
                            self.logger.info(f"Access token found in Authorization header: {access_token[:30] if access_token else 'None'}...")
                        else:
                            self.logger.warning("No access token found in request state or Authorization header")
                            self.logger.info(f"Available headers: {list(http_request.headers.keys())}")
                    
                    # Create user context with ID token (preferred) or access token (fallback)
                    user_context = None
                    if id_token or access_token:
                        user_context = {
                            'jwt_token': id_token,  # For backward compatibility
                            'id_token': id_token,  # Explicit ID token for Amazon Q Business
                            'access_token': access_token  # Access token for other services
                        }
                    self.logger.info(f"Created user_context: {user_context is not None}, ID token available: {id_token is not None}, Access token available: {access_token is not None}")
                    
                    async for chunk_data in self.chatbox_manager.get_streaming_phase_response(
                        message=request.message,
                        phase=request.phase,
                        conversation_id=request.conversation_id,
                        project_name=request.project_name,
                        conversation_context=conversation_context,
                        user_context=user_context
                    ):
                        if chunk_data.get("type") == "content":
                            # Send content chunk
                            content_data = {
                                "type": "content",
                                "content": chunk_data.get("content", ""),
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(content_data)}\n\n"
                            full_response += chunk_data.get("content", "")
                            
                        elif chunk_data.get("type") == "tools":
                            # Send tool usage update
                            tools_data = {
                                "type": "tools",
                                "tools_used": chunk_data.get("tools_used", []),
                                "tool_status": chunk_data.get("tool_status"),
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(tools_data)}\n\n"
                            tools_used = chunk_data.get("tools_used", [])
                            
                        elif chunk_data.get("type") == "jira":
                            # Send jira update notification
                            jira_data = {
                                "type": "jira",
                                "jira_data_updated": chunk_data.get("jira_data_updated", False),
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(jira_data)}\n\n"
                            
                        elif chunk_data.get("type") == "diagrams":
                            # Send diagram notification
                            diagram_data = {
                                "type": "diagrams",
                                "diagrams": chunk_data.get("diagrams", []),
                                "count": chunk_data.get("count", 0),
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(diagram_data)}\n\n"
                            
                        elif chunk_data.get("type") == "code":
                            # Send code generation notification
                            code_data = {
                                "type": "code",
                                "code_files": chunk_data.get("code_files", []),
                                "count": chunk_data.get("count", 0),
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(code_data)}\n\n"
                            

                            
                        elif chunk_data.get("type") == "error":
                            # Send error
                            error_data = {
                                "type": "error",
                                "error": chunk_data.get("error", "Unknown error"),
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            return
                    
                    # Store assistant response if project_name is provided
                    if request.project_name and full_response:
                        await self.conversation_storage.store_message(
                            project_name=request.project_name,
                            role="assistant",
                            content=full_response,
                            user_id=None
                        )
                    
                    # Send completion data
                    completion_data = {
                        "type": "complete",
                        "conversation_id": request.conversation_id,
                        "phase": request.phase,
                        "status": "success",
                        "tools_used": tools_used,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    
                except Exception as e:
                    self.logger.error(f"Error in streaming response: {e}", exc_info=True)
                    error_data = {
                        "type": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingResponse(
                generate_streaming_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up streaming response: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error setting up streaming response: {str(e)}"
            )
    



def create_sdlc_router(chatbox_manager, auth_service=None) -> APIRouter:
    """
    Factory function to create SDLC router with chatbox manager dependency
    
    Args:
        chatbox_manager: ChatboxManager instance
        auth_service: Authentication service for user validation
        
    Returns:
        APIRouter: Configured SDLC router
    """
    sdlc_router_instance = SDLCRouter(chatbox_manager, auth_service)
    return sdlc_router_instance.router