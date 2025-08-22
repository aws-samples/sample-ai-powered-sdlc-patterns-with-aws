"""
Architecture Code Generator Service

Handles automatic code generation from architecture diagrams using MCP servers.
Integrates with the existing diagram generation workflow to provide seamless
transition from design visualization to implementation artifacts.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


# Optional import for HTTP downloading (if needed in future)
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from mcp_client.client import MCPClient
from mcp_client.core.models import MCPRequest, MCPResponse, MCPError, ErrorCode
from services.mcp_discovery import MCPServerDiscovery, ServerAvailabilityStatus
from services.s3_storage_service import S3StorageService
from services.architecture_code_models import (
    CodeGenerationRequest,
    CodeGenerationResponse,
    GeneratedCodeFile,
    CodeType,
    TargetPlatform,
    FileType
)


class ArchitectureCodeGenerator:
    """
    Architecture Code Generation Service
    
    Main orchestrator for generating architecture code from diagrams.
    Integrates with MCP servers to provide automatic code generation
    after successful diagram creation.
    """
    
    def __init__(
        self, 
        mcp_client: Optional[MCPClient] = None, 
        mcp_discovery: Optional[MCPServerDiscovery] = None,
        s3_storage_service: Optional[S3StorageService] = None
    ):
        """
        Initialize the Architecture Code Generator service
        
        Args:
            mcp_client: Optional MCP client instance
            mcp_discovery: Optional MCP discovery service instance
            s3_storage_service: Optional S3 storage service for code persistence
        """
        self.mcp_client = mcp_client
        self.mcp_discovery = mcp_discovery or (MCPServerDiscovery(mcp_client) if mcp_client else None)
        self.s3_storage_service = s3_storage_service or S3StorageService()
        self.logger = logging.getLogger(__name__)
        
        # Code generation capabilities required from MCP servers
        self.code_generation_capabilities = [
            "generate_architecture_code",
            "analyze_architecture",
            "create_architecture_diagram"
        ]
        
        # No local output directory needed - files are saved to S3 only
        
        # Note: Diagrams are stored in S3, no local directory needed

        
        # Note: Diagram downloading is handled by DiagramService, not here
        
        self.logger.debug("Initialized Architecture Code Generator service with S3 integration")
    
    async def check_s3_availability(self) -> Dict[str, Any]:
        """
        Check S3 availability and configuration status.
        
        Returns:
            Dictionary with S3 status information
        """
        try:
            from services.s3_config import s3_config_service
            
            # Check if S3 client can be created
            s3_client = s3_config_service.get_s3_client()
            
            if s3_client is None:
                # Try to validate connection to get specific error
                is_valid, error_message = s3_config_service.validate_s3_connection()
                return {
                    'available': False,
                    'configured': False,
                    'error': error_message or 'S3 client could not be created',
                    'bucket_name': s3_config_service.get_bucket_configuration()['bucket_name']
                }
            
            # Test basic S3 operation
            bucket_config = s3_config_service.get_bucket_configuration()
            test_result = await self.s3_storage_service.list_projects()
            
            return {
                'available': test_result.success,
                'configured': True,
                'error': test_result.error_message if not test_result.success else None,
                'bucket_name': bucket_config['bucket_name'],
                'region': bucket_config['region']
            }
            
        except Exception as e:
            return {
                'available': False,
                'configured': False,
                'error': f'S3 check failed: {str(e)}',
                'bucket_name': 'unknown'
            }
    
    async def load_generated_code_from_s3(self, project_id: str, version: str = "latest") -> Optional[Dict[str, str]]:
        """
        Load generated code files from S3.
        
        Args:
            project_id: Project identifier
            version: Version to load (defaults to "latest")
            
        Returns:
            Dictionary of filename -> content, or None if not found
        """
        try:
            s3_result = await self.s3_storage_service.load_generated_code(project_id, version)
            
            if s3_result.success:
                self.logger.info(f"Successfully loaded {s3_result.data['file_count']} files from S3 for project {project_id}")
                return s3_result.data['files']
            else:
                self.logger.warning(f"Failed to load generated code from S3: {s3_result.error_message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading generated code from S3: {e}")
            return None
    
    async def list_code_versions_from_s3(self, project_id: str) -> List[str]:
        """
        List available code versions for a project in S3.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of version identifiers
        """
        try:
            s3_result = await self.s3_storage_service.list_code_versions(project_id)
            
            if s3_result.success:
                self.logger.info(f"Successfully listed {len(s3_result.data)} versions from S3 for project {project_id}")
                return s3_result.data
            else:
                self.logger.warning(f"Failed to list code versions from S3: {s3_result.error_message}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error listing code versions from S3: {e}")
            return []
    
    async def get_code_files_metadata(self, project_id: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """
        Get metadata about generated code files without loading content.
        
        Args:
            project_id: Project identifier
            version: Version to check (defaults to "latest")
            
        Returns:
            Metadata dictionary with file information
        """
        try:
            # First try to get from S3
            files = await self.load_generated_code_from_s3(project_id, version)
            
            if files:
                metadata = {
                    'project_id': project_id,
                    'version': version,
                    'source': 's3',
                    'total_files': len(files),
                    'total_size': sum(len(content) if isinstance(content, str) else len(content) for content in files.values()),
                    'files': [
                        {
                            'filename': filename,
                            'size': len(content) if isinstance(content, str) else len(content),
                            'type': self._get_file_type_from_extension(filename)
                        }
                        for filename, content in files.items()
                    ]
                }
                return metadata
            
            # No local storage fallback - S3 is required
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting code files metadata: {e}")
            return None
    
    def _get_file_type_from_extension(self, filename: str) -> str:
        """Get file type from filename extension."""
        ext = os.path.splitext(filename)[1].lower()
        type_map = {
            '.yaml': 'infrastructure',
            '.yml': 'infrastructure', 
            '.json': 'config',
            '.tf': 'infrastructure',
            '.py': 'application',
            '.js': 'application',
            '.jsx': 'application',
            '.md': 'documentation',
            '.sh': 'script',
            '.cloudformation': 'infrastructure'
        }
        return type_map.get(ext, 'application')
    
    async def generate_code_from_diagram(
        self, 
        diagram_response: Dict[str, Any],
        context: Dict[str, Any],
        code_type: CodeType = CodeType.CLOUDFORMATION,
        target_platform: TargetPlatform = TargetPlatform.AWS,
        project_name: Optional[str] = None
    ) -> CodeGenerationResponse:
        """
        Generate architecture code from diagram metadata and context.
        
        This is the main entry point for code generation after diagram creation.
        
        Args:
            diagram_response: Response from diagram generation containing metadata
            context: Additional context from conversation and design elements
            code_type: Type of code to generate (CloudFormation, Terraform, etc.)
            target_platform: Target platform for deployment
            project_name: Optional project name for generated code
            
        Returns:
            CodeGenerationResponse with generated code files or error information
        """
        try:
            self.logger.info(f"Starting code generation from diagram for project: {project_name}")
            
            # Extract diagram metadata and architecture description
            diagram_metadata = self._extract_diagram_metadata(diagram_response)
            architecture_description = self._extract_architecture_description(diagram_response, context)
            
            # Get local diagram path if available (already downloaded by DiagramService)
            local_diagram_path = self._get_local_diagram_path(diagram_response)
            
            # Validate prerequisites for code generation
            if not self._validate_code_generation_prerequisites(diagram_metadata, architecture_description):
                return CodeGenerationResponse(
                    success=False,
                    project_name=project_name or "invalid-generation",
                    error_message="Insufficient diagram data for code generation"
                )
            
            # Prepare code generation request
            request = self.prepare_code_generation_request(
                diagram_metadata=diagram_metadata,
                architecture_description=architecture_description,
                context=context,
                code_type=code_type,
                target_platform=target_platform,
                project_name=project_name,
                local_diagram_path=local_diagram_path
            )
            
            # Check MCP availability for code generation
            if self.mcp_discovery:
                mcp_available = await self.mcp_discovery.is_mcp_available_for_capabilities_async(
                    self.code_generation_capabilities
                )
            else:
                mcp_available = self.mcp_client is not None
            
            if mcp_available and self.mcp_client:
                # Generate code via MCP server
                try:
                    mcp_response = await self._generate_code_via_mcp(request)
                    if mcp_response.success:
                        # Files are already saved in _generate_code_via_mcp
                        return mcp_response
                    else:
                        self.logger.error(f"MCP code generation failed: {mcp_response.error_message}")
                        return mcp_response  # Return the failed response as-is
                except Exception as e:
                    self.logger.error(f"Error in MCP code generation: {e}")
                    return CodeGenerationResponse(
                        success=False,
                        project_name=request.project_name,
                        error_message=f"MCP code generation error: {str(e)}"
                    )
            else:
                # No MCP available
                return CodeGenerationResponse(
                    success=False,
                    project_name=request.project_name,
                    error_message="MCP code generation service is not available"
                )
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            return CodeGenerationResponse(
                success=False,
                project_name=project_name or "failed-generation",
                error_message=f"Code generation failed: {str(e)}"
            )
    
    def prepare_code_generation_request(
        self,
        diagram_metadata: Dict[str, Any],
        architecture_description: str,
        context: Dict[str, Any],
        code_type: CodeType = CodeType.CLOUDFORMATION,
        target_platform: TargetPlatform = TargetPlatform.AWS,
        project_name: Optional[str] = None,
        local_diagram_path: Optional[str] = None
    ) -> CodeGenerationRequest:
        """
        Format MCP requests with diagram context for code generation.
        
        Prepares a structured request that includes all necessary information
        for the MCP server to generate appropriate architecture code.
        
        Args:
            diagram_metadata: Metadata extracted from diagram response
            architecture_description: Description of the architecture to implement
            context: Additional context from conversation and design elements
            code_type: Type of code to generate
            target_platform: Target platform for deployment
            project_name: Optional project name
            
        Returns:
            CodeGenerationRequest formatted for MCP server consumption
        """
        # Extract components and technologies from context and metadata
        components = self._extract_components_from_context(diagram_metadata, context)
        technologies = self._extract_technologies_from_context(diagram_metadata, context)
        
        # Generate project name if not provided
        if not project_name:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            project_name = f"architecture-{timestamp}"
        
        # Add local diagram path to metadata if available
        if local_diagram_path:
            diagram_metadata['local_diagram_path'] = local_diagram_path
        
        # Create structured request
        request = CodeGenerationRequest(
            architecture_description=architecture_description,
            diagram_metadata=diagram_metadata,
            code_type=code_type,
            target_platform=target_platform,
            components=components,
            technologies=technologies,
            project_name=project_name,
            include_documentation=True,
            include_tests=False  # Can be made configurable
        )
        
        self.logger.info(f"Prepared code generation request for {len(components)} components")
        return request
    
    async def process_code_generation_response(
        self, 
        mcp_response: MCPResponse,
        original_request: CodeGenerationRequest
    ) -> CodeGenerationResponse:
        """
        Handle MCP responses and extract code files.
        
        Processes the response from MCP server and converts it into
        a structured CodeGenerationResponse with generated files.
        
        Args:
            mcp_response: Raw response from MCP server
            original_request: Original code generation request
            
        Returns:
            CodeGenerationResponse with processed code files
        """
        try:
            self.logger.info("Processing MCP code generation response")
            
            # Validate MCP response
            if not mcp_response or mcp_response.status != "success":
                raise MCPError(
                    error_code=ErrorCode.SERVER_ERROR,
                    message=f"Invalid MCP response: {getattr(mcp_response, 'content', 'Unknown error')}"
                )
            
            # Convert MCP response to our format
            response = CodeGenerationResponse.from_mcp_response(mcp_response, original_request)
            
            # Enhance response with additional processing
            if response.success and response.generated_files:
                # Classify file types
                self._classify_generated_files(response.generated_files)
                
                # Create directory structure
                response.directory_structure = self._create_directory_structure(response.generated_files)
                
                # Generate download URLs (will be handled by FileOrganizer in later tasks)
                self._prepare_download_metadata(response)
                
                self.logger.info(f"Successfully processed {len(response.generated_files)} generated files")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to process MCP response: {e}")
            return CodeGenerationResponse(
                success=False,
                project_name=original_request.project_name,
                error_message=f"Failed to process MCP response: {str(e)}"
            )
    
    def _extract_diagram_metadata(self, diagram_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metadata from diagram generation response"""
        metadata = {}
        
        # Extract metadata from different response formats
        if 'metadata' in diagram_response:
            metadata.update(diagram_response['metadata'])
        
        # Extract design elements if available
        if 'design_elements' in diagram_response:
            metadata['design_elements'] = diagram_response['design_elements']
        
        # Extract diagram URL for reference
        if 'diagram_url' in diagram_response:
            metadata['diagram_url'] = diagram_response['diagram_url']
        
        # Extract diagram type
        if 'diagram_type' in diagram_response:
            metadata['diagram_type'] = diagram_response['diagram_type']
        
        return metadata
    
    def _extract_architecture_description(
        self, 
        diagram_response: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Extract architecture description from diagram response and context"""
        
        # Try to get description from diagram response
        if 'description' in diagram_response:
            return diagram_response['description']
        
        # Try to get from context
        if 'conversation_summary' in context:
            return context['conversation_summary']
        
        # Try to get from metadata
        if 'metadata' in diagram_response and 'description' in diagram_response['metadata']:
            return diagram_response['metadata']['description']
        
        # Fallback to generic description
        return "Architecture design for code generation"
    
    def _validate_code_generation_prerequisites(
        self, 
        diagram_metadata: Dict[str, Any], 
        architecture_description: str
    ) -> bool:
        """Validate that we have sufficient information for code generation"""
        
        # Check if we have a meaningful architecture description
        if not architecture_description or len(architecture_description.strip()) < 10:
            self.logger.warning("Architecture description too short for code generation")
            return False
        
        # Check if diagram generation was successful
        if not diagram_metadata:
            self.logger.warning("No diagram metadata available for code generation")
            return False
        
        return True
    
    def _extract_components_from_context(
        self, 
        diagram_metadata: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[str]:
        """Extract architectural components from diagram metadata and context"""
        components = []
        
        # Extract from diagram metadata
        if 'design_elements' in diagram_metadata and 'components' in diagram_metadata['design_elements']:
            components.extend(diagram_metadata['design_elements']['components'])
        
        # Extract from context
        if 'design_elements' in context and 'components' in context['design_elements']:
            components.extend(context['design_elements']['components'])
        
        # Extract from direct metadata
        if 'components' in diagram_metadata:
            components.extend(diagram_metadata['components'])
        
        if 'components' in context:
            components.extend(context['components'])
        
        # Remove duplicates and filter out empty/short components
        components = list(set([
            comp.strip() for comp in components 
            if comp and len(comp.strip()) > 2
        ]))
        
        return components
    
    def _extract_technologies_from_context(
        self, 
        diagram_metadata: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[str]:
        """Extract technologies from diagram metadata and context"""
        technologies = []
        
        # Extract from diagram metadata
        if 'design_elements' in diagram_metadata and 'technologies' in diagram_metadata['design_elements']:
            technologies.extend(diagram_metadata['design_elements']['technologies'])
        
        # Extract from context
        if 'design_elements' in context and 'technologies' in context['design_elements']:
            technologies.extend(context['design_elements']['technologies'])
        
        # Extract from direct metadata
        if 'technologies' in diagram_metadata:
            technologies.extend(diagram_metadata['technologies'])
        
        if 'technologies' in context:
            technologies.extend(context['technologies'])
        
        # Remove duplicates and filter
        technologies = list(set([
            tech.strip().lower() for tech in technologies 
            if tech and len(tech.strip()) > 1
        ]))
        
        return technologies
    

    

    
    def _create_basic_template(self, request: CodeGenerationRequest) -> str:
        """Create a basic code template for fallback generation"""
        if request.code_type == CodeType.CLOUDFORMATION:
            return self._create_cloudformation_template(request)
        elif request.code_type == CodeType.TERRAFORM:
            return self._create_terraform_template(request)
        elif request.code_type == CodeType.KUBERNETES:
            return self._create_kubernetes_template(request)
        else:
            return f"# {request.code_type.value.title()} Template\n# Generated for: {request.architecture_description}\n\n# TODO: Implement {request.code_type.value} configuration"
    
    async def _save_generated_files(self, response: CodeGenerationResponse) -> None:
        """Save generated code files to S3 only (no local storage)"""
        try:
            if not response.success or not response.generated_files:
                self.logger.warning("No files to save - response unsuccessful or no files generated")
                return
            
            self.logger.info(f"Saving {len(response.generated_files)} files to S3 for project: {response.project_name}")
            
            # Prepare files for S3 storage only
            files_for_s3 = {}
            
            # Prepare each file for S3 storage (no local saving)
            for file in response.generated_files:
                # Use relative path for S3 key
                s3_file_key = os.path.join(file.relative_path, file.filename) if file.relative_path else file.filename
                files_for_s3[s3_file_key] = file.content
                
                self.logger.info(f"Prepared file for S3: {file.filename} ({len(file.content)} characters)")
            
            # Create a README file for the project (S3 only)
            readme_content = f"""# {response.project_name}

Generated architecture code files.

## Files Generated
{chr(10).join([f"- **{file.filename}**: {file.description}" for file in response.generated_files])}

## Generation Details
- Generated at: {datetime.now().isoformat()}
- Project ID: {response.project_id}
- Total files: {len(response.generated_files)}

## Usage
Review the generated files and customize them according to your specific requirements before deployment.
"""
            
            # Add README to S3 files (no local saving)
            files_for_s3["README.md"] = readme_content
            
            # Save files to S3 with versioning
            # Save files to S3 with versioning
            try:
                project_name_for_s3 = response.project_name
                self.logger.info(f"Attempting to save {len(files_for_s3)} files to S3 for project {project_name_for_s3}")
                
                s3_result = await self.s3_storage_service.save_generated_code(
                    project_id=project_name_for_s3,
                    files=files_for_s3
                )
                
                # Check S3 save result
                if s3_result.success:
                    self.logger.info(f"✅ Successfully saved {s3_result.data['file_count']} files to S3 for project {project_name_for_s3}")
                    self.logger.info(f"S3 version: {s3_result.data['version']}")
                    # Update response with S3 metadata
                    if not response.metadata:
                        response.metadata = {}
                    response.metadata.update({
                        's3_sync': True,
                        's3_version': s3_result.data['version'],
                        's3_files_count': s3_result.data['file_count']
                    })
                    # Updated response metadata with S3 info
                else:
                    self.logger.error(f"❌ Failed to save files to S3: {s3_result.error_message}")
                    raise Exception(f"S3 storage failed: {s3_result.error_message}")
                    
            except Exception as s3_error:
                self.logger.error(f"❌ S3 storage exception: {s3_error}")
                import traceback
                self.logger.error(f"❌ S3 storage failed - operation cannot continue: {s3_error}")
                raise Exception(f"S3 storage is required but failed: {s3_error}")
            
            self.logger.info(f"Successfully saved all files for project {response.project_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to save generated files: {e}")
            raise
    
    def _create_cloudformation_template(self, request: CodeGenerationRequest) -> str:
        """Create basic CloudFormation template"""
        components_comment = f"# Components: {', '.join(request.components)}" if request.components else "# No specific components identified"
        technologies_comment = f"# Technologies: {', '.join(request.technologies)}" if request.technologies else "# No specific technologies identified"
        
        return f'''AWSTemplateFormatVersion: '2010-09-09'
Description: '{request.architecture_description}'

{components_comment}
{technologies_comment}

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
    Description: Environment name for resource naming

  ProjectName:
    Type: String
    Default: {request.project_name}
    Description: Project name for resource naming

Resources:
  # VPC for the architecture
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${{ProjectName}}-${{Environment}}-vpc'

  # Internet Gateway
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub '${{ProjectName}}-${{Environment}}-igw'

  # Attach Internet Gateway to VPC
  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      InternetGatewayId: !Ref InternetGateway
      VpcId: !Ref VPC

  # Public Subnet
  PublicSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs '']
      CidrBlock: 10.0.1.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${{ProjectName}}-${{Environment}}-public-subnet'

  # Route Table for Public Subnet
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{ProjectName}}-${{Environment}}-public-rt'

  # Route to Internet Gateway
  DefaultPublicRoute:
    Type: AWS::EC2::Route
    DependsOn: InternetGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  # Associate Route Table with Public Subnet
  PublicSubnetRouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PublicRouteTable
      SubnetId: !Ref PublicSubnet

Outputs:
  VPCId:
    Description: VPC ID
    Value: !Ref VPC
    Export:
      Name: !Sub '${{ProjectName}}-${{Environment}}-vpc-id'

  PublicSubnetId:
    Description: Public Subnet ID
    Value: !Ref PublicSubnet
    Export:
      Name: !Sub '${{ProjectName}}-${{Environment}}-public-subnet-id'

  StackName:
    Description: Name of the CloudFormation stack
    Value: !Ref AWS::StackName
'''
    
    def _create_terraform_template(self, request: CodeGenerationRequest) -> str:
        """Create basic Terraform template"""
        components_comment = f"# Components: {', '.join(request.components)}" if request.components else "# No specific components identified"
        technologies_comment = f"# Technologies: {', '.join(request.technologies)}" if request.technologies else "# No specific technologies identified"
        
        return f'''# Terraform configuration for: {request.architecture_description}
# Generated on: {datetime.now().isoformat()}

{components_comment}
{technologies_comment}

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

variable "project_name" {{
  description = "Project name"
  type        = string
  default     = "{request.project_name}"
}}

# VPC
resource "aws_vpc" "main" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {{
    Name        = "${{var.project_name}}-${{var.environment}}-vpc"
    Environment = var.environment
    Project     = var.project_name
  }}
}}

# Internet Gateway
resource "aws_internet_gateway" "main" {{
  vpc_id = aws_vpc.main.id

  tags = {{
    Name        = "${{var.project_name}}-${{var.environment}}-igw"
    Environment = var.environment
    Project     = var.project_name
  }}
}}

# Public Subnet
resource "aws_subnet" "public" {{
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {{
    Name        = "${{var.project_name}}-${{var.environment}}-public-subnet"
    Environment = var.environment
    Project     = var.project_name
  }}
}}

# Route Table
resource "aws_route_table" "public" {{
  vpc_id = aws_vpc.main.id

  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }}

  tags = {{
    Name        = "${{var.project_name}}-${{var.environment}}-public-rt"
    Environment = var.environment
    Project     = var.project_name
  }}
}}

# Route Table Association
resource "aws_route_table_association" "public" {{
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}}

# Data source for availability zones
data "aws_availability_zones" "available" {{
  state = "available"
}}

output "vpc_id" {{
  description = "VPC ID"
  value       = aws_vpc.main.id
}}

output "public_subnet_id" {{
  description = "Public Subnet ID"
  value       = aws_subnet.public.id
}}

output "environment" {{
  description = "Environment name"
  value       = var.environment
}}
'''
    
    def _create_kubernetes_template(self, request: CodeGenerationRequest) -> str:
        """Create basic Kubernetes template"""
        components_comment = f"# Components: {', '.join(request.components)}" if request.components else "# No specific components identified"
        technologies_comment = f"# Technologies: {', '.join(request.technologies)}" if request.technologies else "# No specific technologies identified"
        
        return f'''# Kubernetes configuration for: {request.architecture_description}
# Generated on: {datetime.now().isoformat()}

{components_comment}
{technologies_comment}

apiVersion: v1
kind: Namespace
metadata:
  name: {request.project_name.lower().replace('_', '-')}
  labels:
    name: {request.project_name.lower().replace('_', '-')}
    environment: dev

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {request.project_name.lower().replace('_', '-')}-app
  namespace: {request.project_name.lower().replace('_', '-')}
  labels:
    app: {request.project_name.lower().replace('_', '-')}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {request.project_name.lower().replace('_', '-')}
  template:
    metadata:
      labels:
        app: {request.project_name.lower().replace('_', '-')}
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: {request.project_name.lower().replace('_', '-')}-service
  namespace: {request.project_name.lower().replace('_', '-')}
spec:
  selector:
    app: {request.project_name.lower().replace('_', '-')}
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
'''
    
    async def _generate_code_via_mcp(self, request: CodeGenerationRequest) -> CodeGenerationResponse:
        """Generate code using MCP server"""
        try:
            # Create MCP request arguments
            mcp_arguments = request.to_mcp_request()
            
            # Add diagram data if available for MCP servers that can process images
            if 'local_diagram_path' in request.diagram_metadata:
                diagram_path = request.diagram_metadata['local_diagram_path']
                mcp_arguments['diagram_file_path'] = diagram_path
                self.logger.info(f"✅ Including local diagram file in MCP request: {diagram_path}")
            elif 'original_s3_url' in request.diagram_metadata:
                # Use S3 binary data approach
                s3_url = request.diagram_metadata['original_s3_url']
                try:
                    # Download binary data from S3 for MCP request
                    image_data = await self._download_s3_diagram_data(s3_url)
                    if image_data:
                        import base64
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        mcp_arguments['diagram_image_data'] = image_base64
                        mcp_arguments['diagram_format'] = 'png'
                        self.logger.info(f"✅ Including S3 diagram binary data in MCP request ({len(image_base64)} chars)")
                    else:
                        self.logger.warning("❌ Failed to download S3 diagram data")
                except Exception as e:
                    self.logger.warning(f"❌ Error downloading S3 diagram data: {e}")
            else:
                self.logger.info("No diagram data available - MCP request will be text-only")
            
            # Create MCP request
            mcp_request = MCPRequest(
                request_type="tools/call",
                content={
                    "name": "generate_architecture_code",
                    "arguments": mcp_arguments
                },
                required_capabilities=self.code_generation_capabilities
            )
            
            self.logger.info(f"Sending code generation request to MCP server for project: {request.project_name}")
            
            # Send request via MCP discovery with fallback
            if self.mcp_discovery:
                mcp_response, used_mcp = await self.mcp_discovery.send_request_with_fallback(
                    mcp_request,
                    fallback_handler=None
                )
            else:
                mcp_response = await self.mcp_client.send_request(mcp_request)
                used_mcp = True
            
            if not mcp_response or not used_mcp:
                raise MCPError(
                    error_code=ErrorCode.SERVER_ERROR,
                    message="No response from MCP code generation service"
                )
            
            # Process the response
            self.logger.info(f"MCP response status: {mcp_response.status}")
            self.logger.info(f"MCP response content keys: {list(mcp_response.content.keys()) if hasattr(mcp_response, 'content') and isinstance(mcp_response.content, dict) else 'No content or not dict'}")
            
            # Process the MCP response directly
            try:
                content = mcp_response.content
                self.logger.info(f"Processing MCP response content: {type(content)}")
                
                # Debug: Log the actual content structure
                if isinstance(content, dict):
                    for key, value in content.items():
                        self.logger.info(f"MCP content['{key}']: {type(value)} - {str(value)[:200]}...")
                else:
                    self.logger.info(f"MCP content (non-dict): {str(content)[:200]}...")
                
                # Handle different response formats from MCP server
                generated_files = []
                
                if isinstance(content, dict):
                    if 'files' in content and isinstance(content['files'], list):
                        # Standard format with files array
                        self.logger.info(f"Found {len(content['files'])} files in MCP response")
                        for file_data in content['files']:
                            if isinstance(file_data, dict):
                                generated_files.append(GeneratedCodeFile(
                                    filename=file_data.get('filename', 'unknown.txt'),
                                    content=file_data.get('content', ''),
                                    file_type=FileType.INFRASTRUCTURE,
                                    language=file_data.get('language', 'text'),
                                    description=file_data.get('description'),
                                    relative_path=file_data.get('path', ''),
                                    dependencies=file_data.get('dependencies', [])
                                ))
                    
                    elif 'content' in content:
                        # Alternative format with content array or single content
                        content_data = content['content']
                        self.logger.info(f"Found content in MCP response: {type(content_data)}")
                        
                        if isinstance(content_data, list):
                            self.logger.info(f"Processing {len(content_data)} content items from MCP response")
                            for item in content_data:
                                if isinstance(item, dict):
                                    # Check for different content formats
                                    if item.get('type') == 'file':
                                        generated_files.append(GeneratedCodeFile(
                                            filename=item.get('filename', 'unknown.txt'),
                                            content=item.get('data', ''),
                                            file_type=FileType.INFRASTRUCTURE,
                                            language=item.get('language', 'text'),
                                            description=item.get('description'),
                                            relative_path=item.get('path', '')
                                        ))
                                    elif 'text' in item:
                                        # Handle text content that might contain code
                                        text_content = item['text']
                                        if len(text_content) > 100:  # Assume substantial content is code
                                            # Extract code from markdown code blocks if present
                                            code_content = self._extract_code_from_markdown(text_content)
                                            if code_content:
                                                # Determine filename based on code type and content
                                                filename = self._determine_filename_from_content(
                                                    code_content, request.project_name, request.code_type
                                                )
                                                generated_files.append(GeneratedCodeFile(
                                                    filename=filename,
                                                    content=code_content,
                                                    file_type=FileType.INFRASTRUCTURE,
                                                    language=self._determine_language_from_content(code_content, request.code_type),
                                                    description=f"Generated {request.code_type.value} from MCP response"
                                                ))
                                            else:
                                                # Use raw text if no code blocks found
                                                filename = f"{request.project_name or 'generated'}.{request.code_type.value}"
                                                generated_files.append(GeneratedCodeFile(
                                                    filename=filename,
                                                    content=text_content,
                                                    file_type=FileType.INFRASTRUCTURE,
                                                    language=request.code_type.value,
                                                    description=f"Generated {request.code_type.value} from MCP response"
                                                ))
                                elif isinstance(item, str) and len(item) > 100:
                                    # Handle direct string content
                                    code_content = self._extract_code_from_markdown(item)
                                    if code_content:
                                        filename = self._determine_filename_from_content(
                                            code_content, request.project_name, request.code_type
                                        )
                                        generated_files.append(GeneratedCodeFile(
                                            filename=filename,
                                            content=code_content,
                                            file_type=FileType.INFRASTRUCTURE,
                                            language=self._determine_language_from_content(code_content, request.code_type),
                                            description=f"Generated {request.code_type.value} from MCP response"
                                        ))
                                    else:
                                        filename = f"{request.project_name or 'generated'}.{request.code_type.value}"
                                        generated_files.append(GeneratedCodeFile(
                                            filename=filename,
                                            content=item,
                                            file_type=FileType.INFRASTRUCTURE,
                                            language=request.code_type.value,
                                            description=f"Generated {request.code_type.value} from MCP response"
                                        ))
                        elif isinstance(content_data, dict):
                            # Handle single content object
                            if content_data.get('type') == 'file':
                                generated_files.append(GeneratedCodeFile(
                                    filename=content_data.get('filename', 'unknown.txt'),
                                    content=content_data.get('data', ''),
                                    file_type=FileType.INFRASTRUCTURE,
                                    language=content_data.get('language', 'text'),
                                    description=content_data.get('description'),
                                    relative_path=content_data.get('path', '')
                                ))
                            elif 'text' in content_data:
                                text_content = content_data['text']
                                if len(text_content) > 100:
                                    code_content = self._extract_code_from_markdown(text_content)
                                    if code_content:
                                        filename = self._determine_filename_from_content(
                                            code_content, request.project_name, request.code_type
                                        )
                                        generated_files.append(GeneratedCodeFile(
                                            filename=filename,
                                            content=code_content,
                                            file_type=FileType.INFRASTRUCTURE,
                                            language=self._determine_language_from_content(code_content, request.code_type),
                                            description=f"Generated {request.code_type.value} from MCP response"
                                        ))
                                    else:
                                        filename = f"{request.project_name or 'generated'}.{request.code_type.value}"
                                        generated_files.append(GeneratedCodeFile(
                                            filename=filename,
                                            content=text_content,
                                            file_type=FileType.INFRASTRUCTURE,
                                            language=request.code_type.value,
                                            description=f"Generated {request.code_type.value} from MCP response"
                                        ))
                        elif isinstance(content_data, str) and len(content_data) > 100:
                            # Handle direct string content
                            code_content = self._extract_code_from_markdown(content_data)
                            if code_content:
                                filename = self._determine_filename_from_content(
                                    code_content, request.project_name, request.code_type
                                )
                                generated_files.append(GeneratedCodeFile(
                                    filename=filename,
                                    content=code_content,
                                    file_type=FileType.INFRASTRUCTURE,
                                    language=self._determine_language_from_content(code_content, request.code_type),
                                    description=f"Generated {request.code_type.value} from MCP response"
                                ))
                            else:
                                filename = f"{request.project_name or 'generated'}.{request.code_type.value}"
                                generated_files.append(GeneratedCodeFile(
                                    filename=filename,
                                    content=content_data,
                                    file_type=FileType.INFRASTRUCTURE,
                                    language=request.code_type.value,
                                    description=f"Generated {request.code_type.value} from MCP response"
                                ))
                    
                    elif 'code' in content:
                        # Simple format with single code content
                        self.logger.info("Found single code content in MCP response")
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
                    else:
                        self.logger.warning(f"Unknown MCP response format. Content keys: {list(content.keys())}")
                        # Try to extract any text content as a fallback
                        for key, value in content.items():
                            if isinstance(value, str) and len(value) > 100:
                                self.logger.info(f"Extracting text content from key '{key}' as potential code")
                                code_content = self._extract_code_from_markdown(value)
                                if code_content:
                                    filename = self._determine_filename_from_content(
                                        code_content, request.project_name, request.code_type
                                    )
                                    generated_files.append(GeneratedCodeFile(
                                        filename=filename,
                                        content=code_content,
                                        file_type=FileType.INFRASTRUCTURE,
                                        language=self._determine_language_from_content(code_content, request.code_type),
                                        description=f"Generated {request.code_type.value} from MCP response key '{key}'"
                                    ))
                                else:
                                    filename = f"{request.project_name or 'generated'}.{request.code_type.value}"
                                    generated_files.append(GeneratedCodeFile(
                                        filename=filename,
                                        content=value,
                                        file_type=FileType.INFRASTRUCTURE,
                                        language=request.code_type.value,
                                        description=f"Generated {request.code_type.value} from MCP response key '{key}'"
                                    ))
                                break  # Only take the first substantial text content
                
                elif isinstance(content, str) and len(content) > 100:
                    # Handle case where entire content is a string
                    self.logger.info("MCP response is a string, treating as code content")
                    code_content = self._extract_code_from_markdown(content)
                    if code_content:
                        filename = self._determine_filename_from_content(
                            code_content, request.project_name, request.code_type
                        )
                        generated_files.append(GeneratedCodeFile(
                            filename=filename,
                            content=code_content,
                            file_type=FileType.INFRASTRUCTURE,
                            language=self._determine_language_from_content(code_content, request.code_type),
                            description=f"Generated {request.code_type.value} from MCP response"
                        ))
                    else:
                        filename = f"{request.project_name or 'generated'}.{request.code_type.value}"
                        generated_files.append(GeneratedCodeFile(
                            filename=filename,
                            content=content,
                            file_type=FileType.INFRASTRUCTURE,
                            language=request.code_type.value,
                            description=f"Generated {request.code_type.value} from MCP response"
                        ))
                
                if generated_files:
                    response = CodeGenerationResponse(
                        success=True,
                        generated_files=generated_files,
                        project_name=request.project_name,
                        project_id=str(uuid.uuid4()),
                        metadata={
                            'generation_method': 'mcp',
                            'code_type': request.code_type.value,
                            'target_platform': request.target_platform.value if request.target_platform else 'aws'
                        }
                    )
                    
                    # Save files locally
                    await self._save_generated_files(response)
                    return response
                else:
                    self.logger.error("No files could be extracted from MCP response - this indicates a parsing issue")
                    return CodeGenerationResponse(
                        success=False,
                        project_name=request.project_name,
                        error_message="MCP server returned content but no files could be extracted. This may indicate an unsupported response format."
                    )
                    
            except Exception as e:
                self.logger.error(f"Failed to process MCP response: {e}")
                return CodeGenerationResponse(
                    success=False,
                    project_name=request.project_name,
                    error_message=f"Failed to process MCP server response: {str(e)}"
                )
            
        except Exception as e:
            self.logger.error(f"MCP code generation failed: {e}")
            return CodeGenerationResponse(
                success=False,
                project_name=request.project_name,
                error_message=f"MCP code generation failed: {str(e)}"
            )
    
    # Fallback code generation methods removed - we only use MCP server responses
    
    def _classify_generated_files(self, files: List[GeneratedCodeFile]) -> None:
        """Classify generated files by type based on filename and content"""
        for file in files:
            filename_lower = file.filename.lower()
            
            # Classify based on file extension and name patterns
            if any(ext in filename_lower for ext in ['.yaml', '.yml', '.json', '.tf']):
                file.file_type = FileType.INFRASTRUCTURE
            elif any(ext in filename_lower for ext in ['.py', '.js', '.jsx', '.ts', '.tsx']):
                file.file_type = FileType.APPLICATION
            elif any(name in filename_lower for name in ['readme', 'doc', '.md']):
                file.file_type = FileType.DOCUMENTATION
            elif any(name in filename_lower for name in ['config', 'env', 'properties']):
                file.file_type = FileType.CONFIG
            else:
                file.file_type = FileType.INFRASTRUCTURE  # Default
    
    def _create_directory_structure(self, files: List[GeneratedCodeFile]) -> Dict[str, Any]:
        """Create hierarchical directory structure from generated files"""
        structure = {}
        
        for file in files:
            # Split path into components
            path_parts = file.filename.split('/')
            current_level = structure
            
            # Navigate/create directory structure
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # This is the file
                    current_level[part] = {
                        'type': 'file',
                        'file_type': file.file_type.value,
                        'language': file.language,
                        'size': file.file_size
                    }
                else:
                    # This is a directory
                    if part not in current_level:
                        current_level[part] = {'type': 'directory', 'contents': {}}
                    current_level = current_level[part]['contents']
        
        return structure
    
    def _prepare_download_metadata(self, response: CodeGenerationResponse) -> None:
        """Prepare metadata for download functionality (URLs will be set by FileOrganizer)"""
        # Set placeholder download URLs that will be replaced by FileOrganizer
        for file in response.generated_files:
            file.download_url = f"/api/code-download/{response.project_id}/file/{file.filename}"
        
        # Set ZIP download URL
        response.zip_download_url = f"/api/code-download/{response.project_id}/zip"
    

    
    def _get_local_diagram_path(self, diagram_response: Dict[str, Any]) -> Optional[str]:
        """
        Get the local diagram path from the diagram response metadata.
        Since we use S3 storage, we'll check for S3 URL and return None to use binary data instead.
        
        Args:
            diagram_response: Response containing diagram metadata
            
        Returns:
            Local path to diagram file if available, None otherwise (uses S3 binary data)
        """
        try:
            # Check if metadata contains local path (legacy support)
            if 'metadata' in diagram_response:
                metadata = diagram_response['metadata']
                
                if 'local_path' in metadata:
                    local_path = metadata['local_path']
                    self.logger.info(f"Found local diagram path in metadata: {local_path}")
                    
                    # Verify file exists
                    if os.path.exists(local_path):
                        self.logger.info(f"✅ Using existing local diagram: {local_path}")
                        return local_path
                    else:
                        self.logger.warning(f"❌ Local diagram path does not exist: {local_path}")
                
                # Check for S3 URL - we'll use binary data instead of local path
                if 'original_s3_url' in metadata:
                    s3_url = metadata['original_s3_url']
                    self.logger.info(f"✅ S3 diagram available, will use binary data for MCP: {s3_url}")
                    # Return None to indicate we should use binary data approach
                    return None
            
            # No diagram path available
            self.logger.info("No diagram path found - code generation will proceed text-only")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get local diagram path: {e}")
            return None
    
    async def _download_s3_diagram_data(self, s3_url: str) -> Optional[bytes]:
        """
        Download diagram binary data from S3 URL.
        
        Args:
            s3_url: S3 URL of the diagram
            
        Returns:
            Binary image data or None if download fails
        """
        try:
            import boto3
            from urllib.parse import urlparse
            from config.settings import settings
            
            self.logger.info(f"Downloading diagram data from S3: {s3_url}")
            
            # Clean the URL
            s3_url = s3_url.rstrip("'}")
            
            # Parse S3 URL to get bucket and key
            parsed = urlparse(s3_url)
            
            # Handle different S3 URL formats
            if parsed.netloc.endswith('.s3.amazonaws.com'):
                bucket_name = parsed.netloc.split('.')[0]
                key = parsed.path.lstrip('/')
            elif 's3.amazonaws.com' in parsed.netloc:
                path_parts = parsed.path.lstrip('/').split('/', 1)
                bucket_name = path_parts[0]
                key = path_parts[1] if len(path_parts) > 1 else ''
            else:
                raise ValueError(f"Unsupported S3 URL format: {s3_url}")
            
            # Download the object
            s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            image_data = response['Body'].read()
            
            self.logger.info(f"Successfully downloaded diagram data ({len(image_data)} bytes)")
            return image_data
                
        except Exception as e:
            self.logger.error(f"Error downloading S3 diagram data: {e}")
            return None
    
    def _extract_code_from_markdown(self, text: str) -> Optional[str]:
        """Extract code content from markdown code blocks."""
        import re
        
        # Look for code blocks with language specifiers
        code_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        
        if matches:
            # Return the first (and usually only) code block
            return matches[0].strip()
        
        # Look for indented code blocks (4+ spaces)
        lines = text.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.startswith('    ') or (in_code_block and line.strip() == ''):
                code_lines.append(line[4:] if line.startswith('    ') else line)
                in_code_block = True
            elif in_code_block and not line.strip():
                code_lines.append('')
            else:
                if in_code_block:
                    break
                in_code_block = False
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return None
    
    def _determine_filename_from_content(self, content: str, project_name: str, code_type: CodeType) -> str:
        """Determine appropriate filename based on content analysis."""
        project_name = project_name or 'generated'
        
        # Check for specific patterns in content to determine file type
        content_lower = content.lower()
        
        if 'from aws_cdk import' in content_lower or 'import aws_cdk' in content_lower:
            return f"{project_name}_stack.py"
        elif 'awstemplateformatversion' in content_lower.replace(' ', ''):
            return f"{project_name}.yaml"
        elif 'terraform' in content_lower or 'provider "aws"' in content_lower:
            return f"{project_name}.tf"
        elif 'apiversion:' in content_lower and 'kind:' in content_lower:
            return f"{project_name}.yaml"
        else:
            # Default based on code type
            if code_type == CodeType.CLOUDFORMATION:
                return f"{project_name}.yaml"
            elif code_type == CodeType.TERRAFORM:
                return f"{project_name}.tf"
            elif code_type == CodeType.CDK:
                return f"{project_name}_stack.py"
            else:
                return f"{project_name}.{code_type.value}"
    
    def _determine_language_from_content(self, content: str, code_type: CodeType) -> str:
        """Determine programming language from content analysis."""
        content_lower = content.lower()
        
        if 'from aws_cdk import' in content_lower or 'import aws_cdk' in content_lower:
            return 'python'
        elif 'awstemplateformatversion' in content_lower.replace(' ', ''):
            return 'yaml'
        elif 'terraform' in content_lower or 'provider "aws"' in content_lower:
            return 'hcl'
        elif 'apiversion:' in content_lower and 'kind:' in content_lower:
            return 'yaml'
        else:
            # Default based on code type
            if code_type == CodeType.CLOUDFORMATION:
                return 'yaml'
            elif code_type == CodeType.TERRAFORM:
                return 'hcl'
            elif code_type == CodeType.CDK:
                return 'python'
            else:
                return code_type.value