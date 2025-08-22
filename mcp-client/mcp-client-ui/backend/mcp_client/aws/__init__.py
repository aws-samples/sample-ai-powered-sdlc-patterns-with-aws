"""
AWS integration components for the MCP Client.
"""

from mcp_client.aws.auth import AWSAuthenticator, AWSCredentialProvider
from mcp_client.aws.bedrock import BedrockMCPAdapter, BedrockModelConfig, create_bedrock_servers

__all__ = [
    "AWSAuthenticator",
    "AWSCredentialProvider",
    "BedrockMCPAdapter",
    "BedrockModelConfig", 
    "create_bedrock_servers",
]