"""
AWS Bedrock integration for the MCP Client.

This module provides integration with AWS Bedrock for Claude models,
implementing the MCP server interface for Bedrock services.
"""

import json
import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime
import asyncio

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    boto3 = None

from mcp_client.core.models import (
    ErrorCode,
    MCPError,
    MCPRequest,
    MCPResponse,
    MCPServerInfo,
    ResponseStatus,
    ServerType,
)
from mcp_client.aws.auth import AWSCredentialProvider

logger = logging.getLogger(__name__)


class BedrockModelConfig:
    """Configuration for Bedrock models."""
    
    # Claude 3 model configurations
    CLAUDE_3_OPUS = {
        "model_id": "anthropic.claude-3-opus-20240229-v1:0",
        "max_tokens": 4096,
        "supports_streaming": True,
        "cost_tier": "premium",
        "capabilities": ["chat", "text-generation", "analysis", "coding"]
    }
    
    CLAUDE_3_SONNET = {
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "max_tokens": 4096,
        "supports_streaming": True,
        "cost_tier": "balanced",
        "capabilities": ["chat", "text-generation", "analysis", "coding"]
    }
    
    CLAUDE_3_HAIKU = {
        "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
        "max_tokens": 4096,
        "supports_streaming": True,
        "cost_tier": "fast",
        "capabilities": ["chat", "text-generation", "quick-responses"]
    }
    
    # Titan models
    TITAN_TEXT_EXPRESS = {
        "model_id": "amazon.titan-text-express-v1",
        "max_tokens": 8192,
        "supports_streaming": False,
        "cost_tier": "economical",
        "capabilities": ["text-generation", "completion"]
    }
    
    TITAN_IMAGE_GENERATOR = {
        "model_id": "amazon.titan-image-generator-v1",
        "max_tokens": None,
        "supports_streaming": False,
        "cost_tier": "standard",
        "capabilities": ["image-generation"]
    }
    
    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model."""
        configs = {
            "claude-3-opus": cls.CLAUDE_3_OPUS,
            "claude-3-sonnet": cls.CLAUDE_3_SONNET,
            "claude-3-haiku": cls.CLAUDE_3_HAIKU,
            "titan-text-express": cls.TITAN_TEXT_EXPRESS,
            "titan-image-generator": cls.TITAN_IMAGE_GENERATOR,
        }
        
        return configs.get(model_name, {})
    
    @classmethod
    def list_available_models(cls) -> List[str]:
        """List all available model names."""
        return [
            "claude-3-opus",
            "claude-3-sonnet", 
            "claude-3-haiku",
            "titan-text-express",
            "titan-image-generator"
        ]


class BedrockMCPAdapter:
    """MCP adapter for AWS Bedrock services."""
    
    def __init__(
        self,
        credential_provider: AWSCredentialProvider,
        model_name: str = "claude-3-sonnet",
        region: str = "us-east-1"
    ):
        """
        Initialize the Bedrock MCP adapter.
        
        Args:
            credential_provider: AWS credential provider
            model_name: Name of the Bedrock model to use
            region: AWS region for Bedrock service
        """
        if boto3 is None:
            raise ImportError("boto3 is required for Bedrock integration. Install with: pip install boto3")
        
        self.credential_provider = credential_provider
        self.model_name = model_name
        self.region = region
        self.model_config = BedrockModelConfig.get_model_config(model_name)
        
        if not self.model_config:
            raise ValueError(f"Unknown model: {model_name}. Available: {BedrockModelConfig.list_available_models()}")
        
        self._bedrock_client = None
        self._bedrock_runtime_client = None
    
    def _get_bedrock_client(self):
        """Get or create Bedrock client."""
        if self._bedrock_client is None:
            session = self.credential_provider.get_session()
            self._bedrock_client = session.client('bedrock', region_name=self.region)
        return self._bedrock_client
    
    def _get_bedrock_runtime_client(self):
        """Get or create Bedrock Runtime client."""
        if self._bedrock_runtime_client is None:
            session = self.credential_provider.get_session()
            self._bedrock_runtime_client = session.client('bedrock-runtime', region_name=self.region)
        return self._bedrock_runtime_client
    
    async def invoke_model(self, request: MCPRequest) -> MCPResponse:
        """
        Invoke a Bedrock model with an MCP request.
        
        Args:
            request: MCP request to process
            
        Returns:
            MCPResponse: Response from the model
        """
        try:
            # Prepare the model input based on request type
            if request.request_type in ["chat", "text-generation"]:
                return await self._handle_text_request(request)
            elif request.request_type == "image-generation":
                return await self._handle_image_request(request)
            else:
                raise MCPError(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Unsupported request type: {request.request_type}",
                    details={"request_type": request.request_type}
                )
        
        except ClientError as e:
            return self._handle_bedrock_error(e, request)
        except Exception as e:
            logger.error(f"Bedrock model invocation failed: {e}")
            raise MCPError(
                error_code=ErrorCode.SERVER_ERROR,
                message=f"Model invocation failed: {str(e)}",
                details={"model": self.model_name, "error": str(e)}
            )
    
    async def invoke_model_streaming(self, request: MCPRequest) -> AsyncIterator[Dict[str, Any]]:
        """
        Invoke a Bedrock model with streaming response.
        
        Args:
            request: MCP request to process
            
        Yields:
            Dict[str, Any]: Streaming response chunks
        """
        if not self.model_config.get("supports_streaming", False):
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Model {self.model_name} does not support streaming",
                details={"model": self.model_name}
            )
        
        try:
            runtime_client = self._get_bedrock_runtime_client()
            
            # Prepare the model input
            model_input = self._prepare_model_input(request)
            
            # Invoke model with streaming
            response = runtime_client.invoke_model_with_response_stream(
                modelId=self.model_config["model_id"],
                body=json.dumps(model_input),
                contentType="application/json",
                accept="application/json"
            )
            
            # Process streaming response
            for event in response['body']:
                if 'chunk' in event:
                    chunk_data = json.loads(event['chunk']['bytes'].decode())
                    yield chunk_data
                    
                    # Add small delay to prevent overwhelming the client
                    await asyncio.sleep(0.01)
        
        except ClientError as e:
            error_response = self._handle_bedrock_error(e, request)
            yield {"error": error_response.content}
        except Exception as e:
            logger.error(f"Bedrock streaming failed: {e}")
            yield {"error": {"message": str(e), "type": "streaming_error"}}
    
    async def _handle_text_request(self, request: MCPRequest) -> MCPResponse:
        """Handle text generation and chat requests."""
        runtime_client = self._get_bedrock_runtime_client()
        
        # Prepare the model input
        model_input = self._prepare_model_input(request)
        
        # Invoke the model
        response = runtime_client.invoke_model(
            modelId=self.model_config["model_id"],
            body=json.dumps(model_input),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract the generated text based on model type
        if "claude" in self.model_name:
            content = self._extract_claude_response(response_body)
        elif "titan" in self.model_name:
            content = self._extract_titan_response(response_body)
        else:
            content = {"text": str(response_body)}
        
        return MCPResponse(
            status=ResponseStatus.SUCCESS,
            content=content,
            server_id=f"bedrock-{self.model_name}",
            request_id=request.metadata.get("request_id", "unknown"),
            timestamp=datetime.now(),
            metadata={
                "model": self.model_name,
                "model_id": self.model_config["model_id"],
                "region": self.region
            }
        )
    
    async def _handle_image_request(self, request: MCPRequest) -> MCPResponse:
        """Handle image generation requests."""
        if "image" not in self.model_config.get("capabilities", []):
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Model {self.model_name} does not support image generation",
                details={"model": self.model_name}
            )
        
        runtime_client = self._get_bedrock_runtime_client()
        
        # Prepare image generation input
        model_input = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": request.content.get("prompt", ""),
                "negativeText": request.content.get("negative_prompt", ""),
            },
            "imageGenerationConfig": {
                "numberOfImages": request.content.get("num_images", 1),
                "height": request.content.get("height", 1024),
                "width": request.content.get("width", 1024),
                "cfgScale": request.content.get("cfg_scale", 8.0),
                "seed": request.content.get("seed", 0) if request.content.get("seed") else None,
            }
        }
        
        # Remove None values
        if model_input["imageGenerationConfig"]["seed"] is None:
            del model_input["imageGenerationConfig"]["seed"]
        
        # Invoke the model
        response = runtime_client.invoke_model(
            modelId=self.model_config["model_id"],
            body=json.dumps(model_input),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract image data
        images = response_body.get("images", [])
        if not images:
            raise MCPError(
                error_code=ErrorCode.SERVER_ERROR,
                message="No images generated",
                details={"response": response_body}
            )
        
        return MCPResponse(
            status=ResponseStatus.SUCCESS,
            content={
                "image_data": images[0],  # Base64 encoded image
                "num_images": len(images),
                "prompt": request.content.get("prompt", "")
            },
            server_id=f"bedrock-{self.model_name}",
            request_id=request.metadata.get("request_id", "unknown"),
            timestamp=datetime.now(),
            metadata={
                "model": self.model_name,
                "model_id": self.model_config["model_id"],
                "region": self.region
            }
        )
    
    def _prepare_model_input(self, request: MCPRequest) -> Dict[str, Any]:
        """Prepare input for the specific model type."""
        if "claude" in self.model_name:
            return self._prepare_claude_input(request)
        elif "titan" in self.model_name:
            return self._prepare_titan_input(request)
        else:
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Unknown model type: {self.model_name}",
                details={"model": self.model_name}
            )
    
    def _prepare_claude_input(self, request: MCPRequest) -> Dict[str, Any]:
        """Prepare input for Claude models."""
        model_input = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": min(
                request.content.get("max_tokens", 1000),
                self.model_config["max_tokens"]
            ),
            "temperature": request.content.get("temperature", 0.7),
            "top_p": request.content.get("top_p", 0.9),
        }
        
        # Handle different request types
        if request.request_type == "chat":
            # Convert chat messages to Claude format
            messages = request.content.get("messages", [])
            if not messages:
                raise MCPError(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Chat request requires messages",
                    details={"content": request.content}
                )
            
            # Convert to Claude message format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    claude_messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            model_input["messages"] = claude_messages
            if system_message:
                model_input["system"] = system_message
        
        else:  # text-generation
            # Convert to single message format
            prompt = request.content.get("prompt", "")
            if not prompt:
                raise MCPError(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Text generation request requires prompt",
                    details={"content": request.content}
                )
            
            model_input["messages"] = [
                {"role": "user", "content": prompt}
            ]
        
        return model_input
    
    def _prepare_titan_input(self, request: MCPRequest) -> Dict[str, Any]:
        """Prepare input for Titan models."""
        prompt = request.content.get("prompt", "")
        if not prompt:
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Titan request requires prompt",
                details={"content": request.content}
            )
        
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": min(
                    request.content.get("max_tokens", 1000),
                    self.model_config["max_tokens"]
                ),
                "temperature": request.content.get("temperature", 0.7),
                "topP": request.content.get("top_p", 0.9),
                "stopSequences": request.content.get("stop_sequences", [])
            }
        }
    
    def _extract_claude_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Extract response content from Claude model."""
        content = response_body.get("content", [])
        if not content:
            return {"text": ""}
        
        # Claude returns content as a list of content blocks
        text_content = ""
        for block in content:
            if block.get("type") == "text":
                text_content += block.get("text", "")
        
        return {
            "text": text_content,
            "usage": response_body.get("usage", {}),
            "stop_reason": response_body.get("stop_reason", "")
        }
    
    def _extract_titan_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Extract response content from Titan model."""
        results = response_body.get("results", [])
        if not results:
            return {"text": ""}
        
        return {
            "text": results[0].get("outputText", ""),
            "completion_reason": results[0].get("completionReason", "")
        }
    
    def _handle_bedrock_error(self, error: ClientError, request: MCPRequest) -> MCPResponse:
        """Handle Bedrock-specific errors."""
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        error_message = error.response.get("Error", {}).get("Message", str(error))
        
        # Map Bedrock errors to MCP errors
        if error_code in ["ValidationException", "InvalidRequestException"]:
            mcp_error_code = ErrorCode.VALIDATION_ERROR
        elif error_code in ["AccessDeniedException", "UnauthorizedException"]:
            mcp_error_code = ErrorCode.AUTHENTICATION_ERROR
        elif error_code in ["ThrottlingException", "ServiceQuotaExceededException"]:
            mcp_error_code = ErrorCode.SERVER_ERROR
        elif error_code in ["ModelTimeoutException", "ModelErrorException"]:
            mcp_error_code = ErrorCode.TIMEOUT_ERROR
        else:
            mcp_error_code = ErrorCode.SERVER_ERROR
        
        logger.error(f"Bedrock error: {error_code} - {error_message}")
        
        return MCPResponse(
            status=ResponseStatus.ERROR,
            content={
                "error": error_message,
                "error_code": error_code,
                "bedrock_error": True
            },
            server_id=f"bedrock-{self.model_name}",
            request_id=request.metadata.get("request_id", "unknown"),
            timestamp=datetime.now(),
            metadata={
                "model": self.model_name,
                "error_type": "bedrock_error"
            }
        )
    
    def get_server_info(self) -> MCPServerInfo:
        """Get MCP server info for this Bedrock adapter."""
        return MCPServerInfo(
            server_id=f"bedrock-{self.model_name}",
            endpoint_url=f"bedrock://{self.region}/{self.model_config['model_id']}",
            capabilities=self.model_config.get("capabilities", []),
            server_type=ServerType.CONVERSATIONAL,
            metadata={
                "model": self.model_name,
                "model_id": self.model_config["model_id"],
                "region": self.region,
                "max_tokens": self.model_config.get("max_tokens"),
                "supports_streaming": self.model_config.get("supports_streaming", False),
                "cost_tier": self.model_config.get("cost_tier", "unknown"),
                "provider": "aws_bedrock"
            }
        )


def create_bedrock_servers(
    credential_provider: AWSCredentialProvider,
    models: Optional[List[str]] = None,
    region: str = "us-east-1"
) -> List[MCPServerInfo]:
    """
    Create MCP server info for Bedrock models.
    
    Args:
        credential_provider: AWS credential provider
        models: List of model names to create servers for
        region: AWS region
        
    Returns:
        List[MCPServerInfo]: List of server configurations
    """
    if models is None:
        models = ["claude-3-sonnet", "claude-3-haiku"]  # Default models
    
    servers = []
    for model_name in models:
        try:
            adapter = BedrockMCPAdapter(credential_provider, model_name, region)
            server_info = adapter.get_server_info()
            servers.append(server_info)
        except Exception as e:
            logger.warning(f"Failed to create server for model {model_name}: {e}")
    
    return servers