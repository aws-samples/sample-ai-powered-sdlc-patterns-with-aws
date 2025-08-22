"""Chatbox conversation routes."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request

from models.api_models import ChatboxRequest, ChatboxResponse
from models.auth_models import UserClaims
from middleware.auth_middleware import get_current_user_dependency, AuthContext, get_auth_context
from services.conversation_storage import ConversationStorage


def create_chatbox_router(chatbox_manager, auth_service=None) -> APIRouter:
    """Create and configure the chatbox router."""
    router = APIRouter(tags=["chatbox"])
    
    # Initialize conversation storage
    conversation_storage = ConversationStorage()
    
    # Authentication dependency
    get_current_user = get_current_user_dependency(auth_service) if auth_service else None
    
    @router.post("/chatbox", response_model=ChatboxResponse)
    async def chatbox_endpoint(
        request: ChatboxRequest,
        http_request: Request,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None
    ):
        """Handle chatbox conversations with user context."""
        try:
            # Store user message first
            if request.project_name:
                user_id = current_user.user_id if current_user else None
                await conversation_storage.store_message(
                    project_name=request.project_name,
                    role="user",
                    content=request.message,
                    user_id=user_id
                )
                
                # Get conversation context for LLM
                context = await conversation_storage.get_context_for_llm(request.project_name)
            else:
                context = None
            
            # Extract JWT token from request (use what frontend is already sending)
            import logging
            logger = logging.getLogger(__name__)
            
            # Try to get ID token from x-id-token header (for future frontend updates)
            id_token = http_request.headers.get("x-id-token")
            
            # If no x-id-token header, use the JWT token from authentication state
            if not id_token and hasattr(http_request, 'state') and hasattr(http_request.state, 'jwt_token'):
                id_token = http_request.state.jwt_token
                logger.info(f"🔍 Using JWT token from auth state: {len(id_token)} chars")
            
            # If still no token, try Authorization header
            if not id_token:
                auth_header = http_request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    id_token = auth_header[7:]  # Remove "Bearer " prefix
                    logger.info(f"🔍 Using JWT token from Authorization header: {len(id_token)} chars")
            
            # Debug logging
            if id_token:
                logger.info(f"🔍 SUCCESS - ID token available for Amazon Q Business: {id_token[:50]}...")
            else:
                logger.info(f"ℹ️ No JWT token found - Amazon Q Business features will not be available")
                logger.debug(f"🔍 Available headers: {list(http_request.headers.keys())}")
            
            # Set access token (same as ID token for now)
            access_token = id_token
            
            # Add user context to the request if authenticated
            user_context = {}
            if current_user:
                user_context = {
                    'user_id': current_user.user_id,
                    'username': current_user.username,
                    'groups': current_user.groups,
                    'email': current_user.email,
                    'jwt_token': id_token,  # Prefer ID token for Amazon Q Business
                    'id_token': id_token,  # Explicit ID token for Amazon Q Business
                    'access_token': access_token  # Access token for other services
                }
            
            # Process the message using ChatboxManager with user context and conversation context
            response_data = await chatbox_manager.get_response(
                message=request.message,
                conversation_id=request.conversation_id,
                user_context=user_context,
                conversation_context=context
            )
            
            # Check if the response indicates an error
            if response_data['status'] == 'error':
                if 'session' in response_data['response'].lower():
                    raise HTTPException(status_code=400, detail=response_data)
                else:
                    raise HTTPException(status_code=500, detail=response_data)
            
            # Store assistant response
            if request.project_name:
                await conversation_storage.store_message(
                    project_name=request.project_name,
                    role="assistant",
                    content=response_data['response'],
                    user_id=current_user.user_id if current_user else None
                )
            
            # Create and return structured response
            return ChatboxResponse(
                response=response_data['response'],
                conversation_id=response_data['conversation_id'],
                status=response_data['status'],
                timestamp=response_data['timestamp'],
                tools_used=response_data.get('tools_used', []),
                jira_data_updated=response_data.get('jira_data_updated', False)
            )
            
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "response": f"Validation error: {str(e)}",
                    "conversation_id": request.conversation_id or "unknown",
                    "status": "error",
                    "timestamp": datetime.utcnow().isoformat(),
                    "tools_used": []
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "response": "I apologize, but I encountered an unexpected error. Please try again.",
                    "conversation_id": request.conversation_id or "unknown",
                    "status": "error",
                    "timestamp": datetime.utcnow().isoformat(),
                    "tools_used": []
                }
            )
    
    @router.get("/chatbox/history/{project_name}")
    async def get_project_conversation(
        project_name: str,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None
    ):
        """Get conversation history for a project - loads when user opens project."""
        try:
            messages = await conversation_storage.get_conversation_history(project_name)
            
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
    
    return router