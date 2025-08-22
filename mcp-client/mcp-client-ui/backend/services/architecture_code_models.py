"""
Core data models for architecture code generation.

This module provides models that integrate with the existing MCP infrastructure
and chatbot capabilities for generating architecture code from diagrams.
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Import existing MCP models for integration
from mcp_client.core.models import MCPRequest, MCPResponse, MCPError, ErrorCode


class CodeType(str, Enum):
    """Supported code generation types (matches MCP server capabilities)."""
    
    CLOUDFORMATION = "cloudformation"
    TERRAFORM = "terraform"
    KUBERNETES = "kubernetes"
    CDK = "cdk"
    PULUMI = "pulumi"


class TargetPlatform(str, Enum):
    """Supported target platforms."""
    
    AWS = "aws"


class FileType(str, Enum):
    """Types of generated files."""
    
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    CONFIG = "config"
    DOCUMENTATION = "documentation"


class CodeGenerationRequest(BaseModel):
    """Request model for architecture code generation (compatible with MCP server)."""
    
    architecture_description: str = Field(
        ..., 
        description="Detailed description of the architecture to generate code for"
    )
    diagram_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata from the generated diagram"
    )
    code_type: CodeType = Field(
        default=CodeType.CLOUDFORMATION,
        description="Type of code to generate"
    )
    target_platform: TargetPlatform = Field(
        default=TargetPlatform.AWS,
        description="Target platform for deployment"
    )
    components: List[str] = Field(
        default_factory=list,
        description="List of architectural components identified from the diagram"
    )
    technologies: List[str] = Field(
        default_factory=list,
        description="List of technologies and frameworks to include"
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Name for the generated project"
    )
    output_directory: Optional[str] = Field(
        default=None,
        description="Custom output directory path"
    )
    include_documentation: bool = Field(
        default=True,
        description="Whether to generate documentation files"
    )
    include_tests: bool = Field(
        default=False,
        description="Whether to generate test files"
    )
    
    @field_validator("architecture_description")
    def validate_architecture_description(cls, v: str) -> str:
        """Validate that architecture description is not empty."""
        if not v or not v.strip():
            raise ValueError("Architecture description cannot be empty")
        return v.strip()
    
    @field_validator("components", "technologies")
    def validate_lists(cls, v: List[str]) -> List[str]:
        """Validate and clean component/technology lists."""
        return [item.strip() for item in v if item and item.strip()]
    
    def to_mcp_request(self) -> Dict[str, Any]:
        """Convert to MCP request format for generate_architecture_code capability."""
        return {
            "architecture_description": self.architecture_description,
            "code_type": self.code_type.value,
            "target_platform": self.target_platform.value,
            "components": self.components,
            "technologies": self.technologies,
            "project_name": self.project_name or "generated-architecture",
            "include_documentation": self.include_documentation,
            "include_tests": self.include_tests,
            "metadata": self.diagram_metadata
        }


class GeneratedCodeFile(BaseModel):
    """Model representing a generated code file (compatible with chatbot file handling)."""
    
    filename: str = Field(..., description="Name of the generated file")
    content: str = Field(..., description="Content of the generated file")
    file_type: FileType = Field(..., description="Type/category of the file")
    language: str = Field(..., description="Programming/markup language of the file")
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the file's purpose"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of dependencies this file requires"
    )
    download_url: Optional[str] = Field(
        default=None,
        description="URL for frontend download access"
    )
    file_size: int = Field(
        default=0,
        description="Size of the file in bytes"
    )
    relative_path: str = Field(
        default="",
        description="Relative path within the project structure"
    )
    local_path: Optional[str] = Field(
        default=None,
        description="Local file system path where file is saved"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the file was generated"
    )
    
    @field_validator("filename")
    def validate_filename(cls, v: str) -> str:
        """Validate filename format."""
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        # Allow relative paths but validate format
        if v.startswith('/') or '\\' in v:
            raise ValueError("Filename cannot be absolute path or contain backslashes")
        return v.strip()
    
    @field_validator("content")
    def validate_content(cls, v: str) -> str:
        """Validate file content."""
        if v is None:
            return ""
        return v
    
    def model_post_init(self, __context):
        """Calculate file size after initialization."""
        if self.content:
            self.file_size = len(self.content.encode('utf-8'))
    
    def save_to_directory(self, base_directory: str) -> str:
        """
        DEPRECATED: Local file saving is no longer used.
        Files are saved to S3 only. This method is kept for compatibility.
        """
        # Return a placeholder path since local saving is disabled
        return os.path.join(base_directory, self.filename)


class CodeGenerationResponse(BaseModel):
    """Response model for architecture code generation (compatible with chatbot processing)."""
    
    success: bool = Field(..., description="Whether code generation was successful")
    generated_files: List[GeneratedCodeFile] = Field(
        default_factory=list,
        description="List of generated code files"
    )
    directory_structure: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hierarchical structure of generated files and directories"
    )
    project_name: str = Field(
        default="generated-architecture",
        description="Name of the generated project"
    )
    project_id: str = Field(
        default="",
        description="Unique identifier for the generated project"
    )
    zip_download_url: Optional[str] = Field(
        default=None,
        description="URL to download the complete project as ZIP"
    )
    local_directory: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Local directory field kept for compatibility"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if generation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the generation process"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when generation completed"
    )
    total_files: int = Field(
        default=0,
        description="Total number of files generated"
    )
    total_size: int = Field(
        default=0,
        description="Total size of all generated files in bytes"
    )
    
    def model_post_init(self, __context):
        """Calculate totals after initialization."""
        self.total_files = len(self.generated_files)
        self.total_size = sum(file.file_size for file in self.generated_files)
    
    @classmethod
    def from_mcp_response(cls, mcp_response: MCPResponse, request: CodeGenerationRequest) -> 'CodeGenerationResponse':
        """Create CodeGenerationResponse from MCP server response."""
        try:
            content = mcp_response.content
            
            # Handle different response formats from MCP server
            generated_files = []
            
            if 'files' in content and isinstance(content['files'], list):
                # Standard format with files array
                for file_data in content['files']:
                    if isinstance(file_data, dict):
                        generated_files.append(GeneratedCodeFile(
                            filename=file_data.get('filename', 'unknown.txt'),
                            content=file_data.get('content', ''),
                            file_type=FileType.INFRASTRUCTURE,  # Default type
                            language=file_data.get('language', 'text'),
                            description=file_data.get('description'),
                            relative_path=file_data.get('path', ''),
                            dependencies=file_data.get('dependencies', [])
                        ))
            
            elif 'content' in content and isinstance(content['content'], list):
                # Alternative format with content array
                for item in content['content']:
                    if isinstance(item, dict) and item.get('type') == 'file':
                        generated_files.append(GeneratedCodeFile(
                            filename=item.get('filename', 'unknown.txt'),
                            content=item.get('data', ''),
                            file_type=FileType.INFRASTRUCTURE,
                            language=item.get('language', 'text'),
                            description=item.get('description'),
                            relative_path=item.get('path', '')
                        ))
            
            elif 'code' in content:
                # Simple format with single code content
                code_content = content['code']
                if isinstance(code_content, str):
                    filename = f"{request.project_name or 'template'}.{request.code_type.value}"
                    generated_files.append(GeneratedCodeFile(
                        filename=filename,
                        content=code_content,
                        file_type=FileType.INFRASTRUCTURE,
                        language=request.code_type.value,
                        description=f"Generated {request.code_type.value} template"
                    ))
            
            return cls(
                success=True,
                generated_files=generated_files,
                project_name=request.project_name or "generated-architecture",
                project_id=str(uuid.uuid4()),
                directory_structure=content.get('directory_structure', {}),
                metadata={
                    'mcp_server_id': getattr(mcp_response, 'server_id', 'unknown'),
                    'generation_method': 'mcp',
                    'code_type': request.code_type.value,
                    'target_platform': request.target_platform.value
                }
            )
            
        except Exception as e:
            return cls(
                success=False,
                project_name=request.project_name or "generated-architecture",
                project_id=str(uuid.uuid4()),
                error_message=f"Failed to process MCP response: {str(e)}",
                metadata={'error_type': 'response_processing_error'}
            )


class DiagramWithCodeRequest(BaseModel):
    """Request model for combined diagram and code generation."""
    
    conversation_history: List[Dict[str, Any]] = Field(
        ...,
        description="Conversation history for diagram generation"
    )
    diagram_type: str = Field(
        default="architecture",
        description="Type of diagram to generate"
    )
    code_generation_enabled: bool = Field(
        default=True,
        description="Whether to enable automatic code generation after diagram"
    )
    code_type: CodeType = Field(
        default=CodeType.CLOUDFORMATION,
        description="Type of code to generate"
    )
    target_platform: TargetPlatform = Field(
        default=TargetPlatform.AWS,
        description="Target platform for deployment"
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Name for the generated project"
    )
    output_directory: Optional[str] = Field(
        default=None,
        description="Custom output directory path"
    )
    
    @field_validator("conversation_history")
    def validate_conversation_history(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate conversation history format."""
        if not v:
            raise ValueError("Conversation history cannot be empty")
        return v


class CodeGenerationStatus(str, Enum):
    """Status of code generation process."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CodeGenerationJob(BaseModel):
    """Model for tracking code generation jobs."""
    
    job_id: str = Field(..., description="Unique identifier for the job")
    status: CodeGenerationStatus = Field(
        default=CodeGenerationStatus.PENDING,
        description="Current status of the job"
    )
    request: CodeGenerationRequest = Field(
        ...,
        description="Original generation request"
    )
    response: Optional[CodeGenerationResponse] = Field(
        default=None,
        description="Generation response when completed"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the job was created"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="When generation started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When generation completed"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if job failed"
    )
    progress_percentage: int = Field(
        default=0,
        description="Progress percentage (0-100)"
    )
    current_step: Optional[str] = Field(
        default=None,
        description="Description of current generation step"
    )


class ArchitectureCodeGenerator:
    """
    Architecture Code Generation Service
    
    Integrates with the existing chatbot and MCP infrastructure to generate
    architecture code from diagrams and conversations.
    """
    
    def __init__(self, mcp_client=None, logger=None):
        """Initialize the architecture code generator."""
        self.mcp_client = mcp_client
        self.logger = logger or logging.getLogger(__name__)
        
        # Code generation capabilities required from MCP servers
        self.code_generation_capabilities = [
            "generate_architecture_code",
            "analyze_architecture"
        ]
        
        # No local output directory needed - files are saved to S3 only
    
    async def generate_code_from_diagram(
        self, 
        diagram_metadata: Dict[str, Any],
        architecture_description: str,
        code_type: CodeType = CodeType.CLOUDFORMATION,
        target_platform: TargetPlatform = TargetPlatform.AWS,
        project_name: Optional[str] = None
    ) -> CodeGenerationResponse:
        """
        Generate architecture code from diagram metadata.
        
        Args:
            diagram_metadata: Metadata from generated diagram
            architecture_description: Description of the architecture
            code_type: Type of code to generate
            target_platform: Target platform
            project_name: Optional project name
            
        Returns:
            CodeGenerationResponse with generated code files
        """
        try:
            # Create generation request
            request = CodeGenerationRequest(
                architecture_description=architecture_description,
                diagram_metadata=diagram_metadata,
                code_type=code_type,
                target_platform=target_platform,
                project_name=project_name or f"architecture-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                components=self._extract_components_from_metadata(diagram_metadata),
                technologies=self._extract_technologies_from_metadata(diagram_metadata)
            )
            
            # Generate code via MCP
            if self.mcp_client:
                return await self._generate_via_mcp(request)
            else:
                return await self._generate_fallback(request)
                
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            return CodeGenerationResponse(
                success=False,
                project_name=project_name or "failed-generation",
                error_message=f"Code generation failed: {str(e)}"
            )
    
    async def _generate_via_mcp(self, request: CodeGenerationRequest) -> CodeGenerationResponse:
        """Generate code using MCP server."""
        try:
            # Create MCP request
            mcp_request = MCPRequest(
                request_type="tools/call",
                content={
                    "name": "generate_architecture_code",
                    "arguments": request.to_mcp_request()
                },
                required_capabilities=self.code_generation_capabilities
            )
            
            self.logger.info(f"Sending code generation request to MCP server")
            
            # Send request to MCP server
            mcp_response = await self.mcp_client.send_request(mcp_request)
            
            if not mcp_response or mcp_response.status != "success":
                raise MCPError(
                    error_code=ErrorCode.SERVER_ERROR,
                    message=f"MCP code generation failed: {getattr(mcp_response, 'content', 'Unknown error')}"
                )
            
            # Convert MCP response to our format
            response = CodeGenerationResponse.from_mcp_response(mcp_response, request)
            
            # Files are saved to S3 by the ArchitectureCodeGenerator service
            
            return response
            
        except Exception as e:
            self.logger.error(f"MCP code generation failed: {e}")
            return CodeGenerationResponse(
                success=False,
                project_name=request.project_name,
                error_message=f"MCP code generation failed: {str(e)}"
            )
    
    async def _generate_fallback(self, request: CodeGenerationRequest) -> CodeGenerationResponse:
        """Generate basic code template when MCP is unavailable."""
        try:
            # Create basic template based on code type
            template_content = self._create_basic_template(request)
            
            generated_file = GeneratedCodeFile(
                filename=f"{request.project_name}.{request.code_type.value}",
                content=template_content,
                file_type=FileType.INFRASTRUCTURE,
                language=request.code_type.value,
                description=f"Basic {request.code_type.value} template (fallback)"
            )
            
            response = CodeGenerationResponse(
                success=True,
                generated_files=[generated_file],
                project_name=request.project_name,
                project_id=str(uuid.uuid4()),
                metadata={'generation_method': 'fallback'}
            )
            
            # Files are saved to S3 by the ArchitectureCodeGenerator service
            
            return response
            
        except Exception as e:
            self.logger.error(f"Fallback code generation failed: {e}")
            return CodeGenerationResponse(
                success=False,
                project_name=request.project_name,
                error_message=f"Fallback code generation failed: {str(e)}"
            )
    
    def _extract_components_from_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Extract architectural components from diagram metadata."""
        components = []
        
        # Look for components in various metadata fields
        if 'components' in metadata:
            components.extend(metadata['components'])
        
        if 'design_elements' in metadata and 'components' in metadata['design_elements']:
            components.extend(metadata['design_elements']['components'])
        
        return list(set(components))  # Remove duplicates
    
    def _extract_technologies_from_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Extract technologies from diagram metadata."""
        technologies = []
        
        # Look for technologies in various metadata fields
        if 'technologies' in metadata:
            technologies.extend(metadata['technologies'])
        
        if 'design_elements' in metadata and 'technologies' in metadata['design_elements']:
            technologies.extend(metadata['design_elements']['technologies'])
        
        return list(set(technologies))  # Remove duplicates
    
    def _create_basic_template(self, request: CodeGenerationRequest) -> str:
        """Create a basic code template for fallback generation."""
        if request.code_type == CodeType.CLOUDFORMATION:
            return self._create_cloudformation_template(request)
        elif request.code_type == CodeType.TERRAFORM:
            return self._create_terraform_template(request)
        else:
            return f"# {request.code_type.value.title()} Template\n# Generated for: {request.architecture_description}\n\n# TODO: Implement {request.code_type.value} configuration"
    
    def _create_cloudformation_template(self, request: CodeGenerationRequest) -> str:
        """Create basic CloudFormation template."""
        return f'''AWSTemplateFormatVersion: '2010-09-09'
Description: '{request.architecture_description}'

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

Resources:
  # TODO: Add resources based on architecture description
  # Components identified: {', '.join(request.components) if request.components else 'None'}
  # Technologies: {', '.join(request.technologies) if request.technologies else 'None'}
  
  PlaceholderResource:
    Type: AWS::CloudFormation::WaitConditionHandle
    Properties: {{}}

Outputs:
  StackName:
    Description: Name of the CloudFormation stack
    Value: !Ref AWS::StackName
'''
    
    def _create_terraform_template(self, request: CodeGenerationRequest) -> str:
        """Create basic Terraform template."""
        return f'''# Terraform configuration for: {request.architecture_description}
# Generated on: {datetime.now().isoformat()}

terraform {{
  required_version = ">= 1.0"
  
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}}

variable "environment" {{
  description = "Environment name"
  type        = string
  default     = "dev"
}}

# TODO: Add resources based on architecture description
# Components identified: {', '.join(request.components) if request.components else 'None'}
# Technologies: {', '.join(request.technologies) if request.technologies else 'None'}

output "environment" {{
  description = "Environment name"
  value       = var.environment
}}
'''
    
    # Local file saving removed - files are saved to S3 only