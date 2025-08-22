"""
Dependency injection for FastAPI endpoints.
"""

from fastapi import HTTPException
from services.mcp_service import MCPService
import __main__


def get_mcp_service() -> MCPService:
    """
    Get the MCP service instance.
    
    Returns:
        MCPService: The global MCP service instance
        
    Raises:
        HTTPException: If MCP service is not available
    """
    if hasattr(__main__, 'mcp_service') and __main__.mcp_service:
        return __main__.mcp_service
    
    raise HTTPException(
        status_code=503,
        detail="MCP service is not available"
    )