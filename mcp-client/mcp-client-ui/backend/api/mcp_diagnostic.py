"""
MCP Diagnostic API endpoints for troubleshooting authentication and connection issues.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from services.mcp_service import MCPService
from core.dependencies import get_mcp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP Diagnostics"])


@router.get("/status")
async def get_mcp_status(mcp_service: MCPService = Depends(get_mcp_service)) -> Dict[str, Any]:
    """
    Get the current status of the MCP service.
    
    Returns:
        Dict containing MCP service status information
    """
    try:
        status = mcp_service.get_status()
        return {
            "success": True,
            "status": status,
            "available_tools": mcp_service.get_available_tools()
        }
    except Exception as e:
        logger.error(f"Failed to get MCP status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aws-credentials")
async def diagnose_aws_credentials(mcp_service: MCPService = Depends(get_mcp_service)) -> Dict[str, Any]:
    """
    Diagnose AWS credential configuration and availability.
    
    Returns:
        Dict containing AWS credential diagnostic information
    """
    try:
        diagnosis = mcp_service.diagnose_aws_credentials()
        return {
            "success": True,
            "diagnosis": diagnosis
        }
    except Exception as e:
        logger.error(f"Failed to diagnose AWS credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-amazon-q-business")
async def test_amazon_q_business_connection(mcp_service: MCPService = Depends(get_mcp_service)) -> Dict[str, Any]:
    """
    Test the connection to Amazon Q Business service.
    
    Returns:
        Dict containing test results
    """
    try:
        test_result = await mcp_service.test_amazon_q_business_connection()
        return {
            "success": test_result["success"],
            "test_result": test_result
        }
    except Exception as e:
        logger.error(f"Failed to test Amazon Q Business connection: {e}")
        return {
            "success": False,
            "test_result": {
                "success": False,
                "error_message": str(e),
                "server_registered": False,
                "authentication_working": False
            }
        }


@router.post("/register-server/{server_id}")
async def register_server(
    server_id: str,
    mcp_service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Register a specific MCP server on-demand.
    
    Args:
        server_id: The ID of the server to register
        
    Returns:
        Dict containing registration result
    """
    try:
        success = await mcp_service.ensure_server_registered(server_id)
        return {
            "success": success,
            "server_id": server_id,
            "message": f"Server {server_id} {'registered successfully' if success else 'failed to register'}"
        }
    except Exception as e:
        logger.error(f"Failed to register server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/servers")
async def list_servers(mcp_service: MCPService = Depends(get_mcp_service)) -> Dict[str, Any]:
    """
    List all available MCP servers and their registration status.
    
    Returns:
        Dict containing server information
    """
    try:
        available_tools = mcp_service.get_available_tools()
        registered_servers = mcp_service.get_registered_servers()
        server_configs = mcp_service.get_server_configs()
        
        servers = []
        for server_id, tool_info in available_tools.items():
            server_info = {
                "server_id": server_id,
                "registered": server_id in registered_servers,
                "capabilities": tool_info.get("capabilities", []),
                "server_type": tool_info.get("server_type"),
                "description": tool_info.get("description")
            }
            
            # Add endpoint URL if available
            if server_id in server_configs:
                config = server_configs[server_id]
                if hasattr(config, 'endpoint_url'):
                    server_info["endpoint_url"] = config.endpoint_url
                if hasattr(config, 'auth'):
                    server_info["auth_type"] = getattr(config.auth, 'type', 'unknown') if config.auth else 'none'
            
            servers.append(server_info)
        
        return {
            "success": True,
            "servers": servers,
            "total_servers": len(servers),
            "registered_count": len(registered_servers)
        }
    except Exception as e:
        logger.error(f"Failed to list servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/re-register-all")
async def re_register_all_servers(mcp_service: MCPService = Depends(get_mcp_service)) -> Dict[str, Any]:
    """
    Re-register all MCP servers (useful after authentication changes).
    
    Returns:
        Dict containing re-registration results
    """
    try:
        await mcp_service.re_register_all_servers()
        registered_servers = mcp_service.get_registered_servers()
        
        return {
            "success": True,
            "message": "All servers re-registered",
            "registered_count": len(registered_servers),
            "registered_servers": list(registered_servers)
        }
    except Exception as e:
        logger.error(f"Failed to re-register all servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-simple-request")
async def test_simple_request(mcp_service: MCPService = Depends(get_mcp_service)) -> Dict[str, Any]:
    """
    Test a simple request to Amazon Q Business to verify authentication.
    
    Returns:
        Dict containing test results
    """
    try:
        # Ensure the server is registered first
        server_id = "amazon-q-business"
        registration_success = await mcp_service.ensure_server_registered(server_id)
        
        if not registration_success:
            return {
                "success": False,
                "error": "Failed to register Amazon Q Business server",
                "server_registered": False
            }
        
        # Try a simple test request
        test_request = {
            "message": "Test connection - please respond with a simple acknowledgment"
        }
        
        response = await mcp_service.send_request_with_jwt(test_request, server_id)
        
        return {
            "success": True,
            "server_registered": True,
            "response": response,
            "message": "Test request completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Test request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "server_registered": registration_success if 'registration_success' in locals() else False,
            "message": "Test request failed"
        }