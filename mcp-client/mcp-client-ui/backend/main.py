"""
Refactored FastAPI Server

A clean, modular FastAPI-based web server with separated concerns
and improved maintainability.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Configure logging for development
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from root .env file
from dotenv import load_dotenv
import os
# Load from root directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


# Environment variables already loaded above

from config.settings import settings
from services.chatbox_manager import ChatboxManager
from services.authentication_service import AuthenticationService
from services.authorization_service import AuthorizationService
from services.cognito_config_service import CognitoConfigService
from middleware.auth_middleware import AuthenticationMiddleware
from routers.sdlc import create_sdlc_router
from routers.api_routes import create_api_router, create_legacy_api_router
from routers.chatbox_routes import create_chatbox_router
from routers.code_routes import create_code_router
from routers.auth_routes import create_auth_router
from routers.secure_project_routes import create_secure_project_router
from routers.conversation_routes import create_conversation_router
from routers.project_creation_routes import create_project_creation_router
from routers.jira_routes import router as jira_router


# Configure logging with startup info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create main logger
main_logger = logging.getLogger(__name__)

# Silence noisy AWS loggers but keep some service logs
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore.credentials').setLevel(logging.WARNING)
# Keep uvicorn.access at INFO level to show green endpoint logs

# Initialize global services
chatbox_manager = ChatboxManager()

# Initialize time synchronization service
from services.time_sync_service import time_sync_service
try:
    time_sync_service.sync_with_ntp()
    main_logger.info("Time synchronization service initialized")
except Exception as e:
    main_logger.debug(f"Time synchronization initialization: {e}")

# Initialize authentication services (with fallback for missing config)
try:
    # Settings loaded silently
    
    cognito_config = CognitoConfigService(
        user_pool_id=settings.COGNITO_USER_POOL_ID if hasattr(settings, 'COGNITO_USER_POOL_ID') else None,
        client_id=settings.COGNITO_CLIENT_ID if hasattr(settings, 'COGNITO_CLIENT_ID') else None,
        region=settings.AWS_REGION if hasattr(settings, 'AWS_REGION') else 'us-east-1'
    )
    auth_service = AuthenticationService(cognito_config)
    authorization_service = AuthorizationService()
    auth_enabled = True
except Exception as e:
    logging.warning(f"Authentication services not available: {e}")
    auth_service = None
    authorization_service = None
    auth_enabled = False

# Initialize MCP service
try:
    from services.mcp_service import MCPService
    
    mcp_service = MCPService()
    
    # Initialize MCP service asynchronously
    import asyncio
    try:
        # Try to initialize in the current event loop if available
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule initialization for later
            asyncio.create_task(mcp_service.initialize())
        else:
            # Run initialization now
            loop.run_until_complete(mcp_service.initialize())
    except RuntimeError:
        # No event loop, create one
        asyncio.run(mcp_service.initialize())
    
    main_logger.info("MCP service initialized successfully")
except Exception as e:
    main_logger.warning(f"MCP service not available: {e}")
    main_logger.debug(f"MCP initialization error details: {str(e)}")
    mcp_service = None

# Initialize FastAPI application
app = FastAPI(
    title="iCode Backend Server",
    version="2.0.0",
    description="A modular FastAPI server for AI-powered development assistance"
)

# # Allow all origins for development - simplified CORS
# cors_origins = ["*"]

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=cors_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Add authentication middleware if available
if auth_enabled and auth_service:
    app.add_middleware(
        AuthenticationMiddleware,
        auth_service=auth_service,
        excluded_paths=[
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",  # Browser requests
            "/manifest.json",  # React manifest
            "/static",  # All static files (CSS, JS, images)
            "/api/auth/login",
            "/api/auth/signup",  # Allow signup without authentication
            "/api/auth/refresh",
            "/api/oauth/jira/callback",  # Allow OAuth callback without authentication (for future Jira implementation)
            "/api/sdlc",  # All SDLC endpoints (including PDF generation)
            "/chatbox"  # Keep chatbox accessible for now
            # Removed /diagrams and /api/diagrams - now require authentication
        ]
    )

# Serve React frontend static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(create_sdlc_router(chatbox_manager, auth_service))
app.include_router(create_api_router(auth_service))
app.include_router(create_legacy_api_router())
app.include_router(create_chatbox_router(chatbox_manager, auth_service))
app.include_router(create_code_router(auth_service))


# Include authentication routes if available
if auth_enabled and auth_service:
    app.include_router(create_auth_router(auth_service, authorization_service, cognito_config))
    # Include secure project routes that use Cognito credentials for S3 access
    app.include_router(create_secure_project_router(auth_service))
    # Include project creation routes
    app.include_router(create_project_creation_router(auth_service))
    
    # OAuth routes removed - Jira integration no longer available
    main_logger.info("OAuth routes disabled - external integrations removed")

# Include conversation routes
app.include_router(create_conversation_router(auth_service))

# Include Jira routes
app.include_router(jira_router)

# Include MCP diagnostic routes
try:
    from api.mcp_diagnostic import router as mcp_diagnostic_router
    app.include_router(mcp_diagnostic_router)
    main_logger.info("MCP diagnostic routes initialized successfully")
except ImportError as e:
    main_logger.warning(f"MCP diagnostic routes not available: {e}")

# Atlassian authentication routes removed - will be implemented later

# Include Swagger routes
try:
    from api.swagger_endpoints import create_swagger_router
    app.include_router(create_swagger_router(auth_service))
    main_logger.info("Swagger routes initialized successfully")
except ImportError as e:
    main_logger.warning(f"Swagger routes not available: {e}")

# Include Knowledge Base routes (if available)
try:
    from api.kb_endpoints import router as kb_router, set_dynamic_service
    from services.simple_tool_service import SimpleToolService
    from mcp_client.client import MCPClient
    
    # Initialize MCP client if not already available
    if not mcp_service:
        from services.mcp_service import MCPService
        mcp_service = MCPService()
    
    # Initialize MCP client with proper config
    from mcp_client.core.models import MCPClientConfig
    mcp_config = MCPClientConfig(
        aws_region=os.getenv('AWS_REGION', 'us-east-1'),
        enable_aws_auth=True,
        timeout_seconds=30.0,
        max_retries=3
    )
    mcp_client = MCPClient(config=mcp_config)
    
    # Initialize simple tool service with proper dependencies
    dynamic_service = SimpleToolService(mcp_client=mcp_client, mcp_service=mcp_service)
    
    # Initialize the service asynchronously
    import asyncio
    try:
        # Try to initialize in the current event loop if available
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule initialization for later
            asyncio.create_task(dynamic_service.initialize())
        else:
            # Run initialization now
            loop.run_until_complete(dynamic_service.initialize())
    except RuntimeError:
        # No event loop, create one
        asyncio.run(dynamic_service.initialize())
    
    # Make dynamic_service available globally for MCP re-registration
    import __main__
    __main__.dynamic_service = dynamic_service
    
    # Set the service for KB endpoints
    set_dynamic_service(dynamic_service)
    
    # Add KB endpoints
    app.include_router(kb_router)
    main_logger.info("Knowledge Base endpoints initialized successfully with MCP integration")
    
except Exception as e:
    main_logger.warning(f"Knowledge Base endpoints not available: {e}")
    main_logger.debug(f"KB initialization error details: {str(e)}")
    dynamic_service = None

# Make MCP service available globally for diagnostic endpoints
if mcp_service:
    import __main__
    __main__.mcp_service = mcp_service


# Root route removed - handled by catch-all route for SPA
# @app.get("/")
# async def root():
#     """API root endpoint."""
#     return {
#         "message": "iCode Backend API",
#         "version": "2.0.0",
#         "status": "running",
#         "docs": "/docs"
#     }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "services": {
            "mcp": chatbox_manager.is_mcp_available(),
            "sessions": chatbox_manager.get_session_stats().dict(),
            "authentication": {
                "enabled": auth_enabled,
                "cognito_configured": auth_service is not None
            },
            "time_sync": {
                "offset_seconds": time_sync_service.get_clock_skew().total_seconds() if time_sync_service.get_clock_skew() else 0,
                "last_sync": time_sync_service._last_sync.isoformat() if time_sync_service._last_sync else None
            }
        }
    }
    
    # Add authentication service health if available
    if auth_service:
        try:
            # Test Cognito connection
            health_status["services"]["authentication"]["cognito_connection"] = "healthy"
        except Exception as e:
            health_status["services"]["authentication"]["cognito_connection"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
    
    return health_status

@app.get("/auth-test")
async def auth_test(request: Request):
    """Test endpoint to check authentication status."""
    auth_header = request.headers.get("Authorization")
    return {
        "has_auth_header": bool(auth_header),
        "auth_header_preview": auth_header[:20] + "..." if auth_header else None,
        "method": request.method,
        "path": request.url.path
    }


@app.post("/{path:path}")
async def handle_post(path: str = ""):
    """POST route handler that processes POST requests to any endpoint."""
    return {"message": "Request received", "status": "success"}


@app.api_route("/{path:path}", methods=["PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def handle_other_methods(request: Request, path: str = ""):
    """Catch-all route handler for other HTTP methods."""
    return {"message": "Request received", "status": "success"}


# OAuth callback removed - will be implemented with Jira functionality later

@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve React SPA for all non-API routes."""
    # If the path starts with 'api', let it be handled by API routes
    if path.startswith('api/'):
        return {"error": "API endpoint not found"}, 404
    
    # For all other paths, serve the React app
    return FileResponse('static/index.html')


if __name__ == "__main__":
    try:
        pass  # Server starting
        uvicorn.run(
            app,
            host=settings.HOST,
            port=settings.PORT,
            log_level="info",   # Show info logs including endpoints
            access_log=True,    # Enable access logs to show endpoints
            timeout_keep_alive=300,  # Keep connections alive for 5 minutes
            timeout_graceful_shutdown=30,  # Graceful shutdown timeout
        )
    except Exception as e:
        logging.error(f"Error starting server: {e}")
        exit(1)