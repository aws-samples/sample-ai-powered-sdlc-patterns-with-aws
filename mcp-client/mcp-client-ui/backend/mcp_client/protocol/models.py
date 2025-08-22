"""
Protocol-specific data models for the MCP Client.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from mcp_client.core.models import MCPRequest, MCPResponse, ResponseStatus, ServerType


class RequestType(str, Enum):
    """Types of MCP requests."""

    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CHAT = "chat"
    ACTION = "action"
    CUSTOM = "custom"


class TextGenerationRequest(MCPRequest):
    """A request for text generation."""

    request_type: str = RequestType.TEXT_GENERATION
    content: Dict[str, Any] = Field(...)
    required_capabilities: List[str] = Field(default_factory=lambda: ["text-generation"])

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains a prompt."""
        if "prompt" not in v:
            raise ValueError("Content must contain a prompt")
        return v


class ImageGenerationRequest(MCPRequest):
    """A request for image generation."""

    request_type: str = RequestType.IMAGE_GENERATION
    content: Dict[str, Any] = Field(...)
    required_capabilities: List[str] = Field(default_factory=lambda: ["image-generation"])

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains a prompt."""
        if "prompt" not in v:
            raise ValueError("Content must contain a prompt")
        return v


class EmbeddingRequest(MCPRequest):
    """A request for embedding generation."""

    request_type: str = RequestType.EMBEDDING
    content: Dict[str, Any] = Field(...)
    required_capabilities: List[str] = Field(default_factory=lambda: ["embedding"])

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains text."""
        if "text" not in v:
            raise ValueError("Content must contain text")
        return v


class ChatMessage(BaseModel):
    """A chat message."""

    role: str
    content: str


class ChatRequest(MCPRequest):
    """A request for chat."""

    request_type: str = RequestType.CHAT
    content: Dict[str, Any] = Field(...)
    required_capabilities: List[str] = Field(default_factory=lambda: ["chat"])

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains messages."""
        if "messages" not in v:
            raise ValueError("Content must contain messages")
        return v


class ActionRequest(MCPRequest):
    """A request for an action."""

    request_type: str = RequestType.ACTION
    content: Dict[str, Any] = Field(...)
    required_capabilities: List[str] = Field(default_factory=lambda: ["action"])

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains an action."""
        if "action" not in v:
            raise ValueError("Content must contain an action")
        return v


class TextGenerationResponse(MCPResponse):
    """A response from a text generation request."""

    content: Dict[str, Any] = Field(...)

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains generated text."""
        if "text" not in v:
            raise ValueError("Content must contain generated text")
        return v


class ImageGenerationResponse(MCPResponse):
    """A response from an image generation request."""

    content: Dict[str, Any] = Field(...)

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains an image URL or data."""
        if "image_url" not in v and "image_data" not in v:
            raise ValueError("Content must contain an image URL or data")
        return v


class EmbeddingResponse(MCPResponse):
    """A response from an embedding request."""

    content: Dict[str, Any] = Field(...)

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains embeddings."""
        if "embeddings" not in v:
            raise ValueError("Content must contain embeddings")
        return v


class ChatResponse(MCPResponse):
    """A response from a chat request."""

    content: Dict[str, Any] = Field(...)

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains a message."""
        if "message" not in v:
            raise ValueError("Content must contain a message")
        return v


class ActionResponse(MCPResponse):
    """A response from an action request."""

    content: Dict[str, Any] = Field(...)

    @field_validator("content")
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the content contains a result."""
        if "result" not in v:
            raise ValueError("Content must contain a result")
        return v


# Type aliases for convenience
MCPRequestTypes = Union[
    TextGenerationRequest,
    ImageGenerationRequest,
    EmbeddingRequest,
    ChatRequest,
    ActionRequest,
    MCPRequest,
]

MCPResponseTypes = Union[
    TextGenerationResponse,
    ImageGenerationResponse,
    EmbeddingResponse,
    ChatResponse,
    ActionResponse,
    MCPResponse,
]