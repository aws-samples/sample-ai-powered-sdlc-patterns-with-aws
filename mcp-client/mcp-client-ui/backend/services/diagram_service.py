"""Diagram generation service."""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import boto3

from config.settings import settings
from services.s3_storage_service import S3StorageService


class DiagramService:
    """Service for generating and managing diagrams."""
    
    def __init__(self, s3_storage_service: Optional[S3StorageService] = None):
        """Initialize the diagram service."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize S3 storage service
        self.s3_storage_service = s3_storage_service or S3StorageService()
    
    async def generate_diagram(self, message: str, session: Dict[str, Any], mcp_client) -> Optional[List]:
        """Generate diagram based on message content."""
        if not self._should_generate_diagram(message):
            return None
        
        try:
            self.logger.info("Starting diagram generation process")
            
            # Create MCP request for diagram generation
            from mcp_client.core.models import MCPRequest
            
            mcp_request = MCPRequest(
                request_type='tools/call',
                content={
                    'name': 'create_architecture_diagram',
                    'arguments': {
                        'architecture_description': message,
                        'diagram_type': 'architecture'
                    }
                },
                required_capabilities=['create_architecture_diagram']
            )
            
            # Send request to MCP client
            response = await mcp_client.send_request(mcp_request)
            
            if response.status.value == 'success' and hasattr(response, 'content'):
                return await self._process_diagram_response(response, message, session, mcp_client)
            else:
                self.logger.warning(f"Invalid MCP response - status: {getattr(response, 'status', 'no status')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating diagram: {e}")
            return None
    
    def _should_generate_diagram(self, message: str) -> bool:
        """Determine if a diagram should be generated based on message content."""
        message_lower = message.lower()
        
        # Explicit diagram requests
        explicit_request = any(phrase in message_lower for phrase in [
            'create diagram', 'generate diagram', 'show diagram', 'design diagram',
            'please diagram', 'make diagram', 'draw diagram', 'diagram for',
            'create an architecture', 'design an architecture', 'show architecture',
            'mvc diagram', 'architecture diagram', 'system diagram'
        ])
        
        # Modification keywords with architecture context
        has_modification_word = any(word in message_lower for word in [
            'add', 'change', 'modify', 'include', 'update', 'enhance', 'also', 'additional'
        ])
        has_architecture_context = any(context in message_lower for context in [
            'architecture', 'design', 'system', 'server', 'database', 'service',
            'load balancer', 'cache', 'queue', 'gateway', 'container', 'deployment'
        ])
        modification_request = has_modification_word and has_architecture_context
        
        # Architecture and design keywords
        architecture_keywords = any(keyword in message_lower for keyword in [
            'architecture', 'system design', 'application', 'microservice', 'database',
            'mvc', 'design pattern', 'component', 'tier', 'layer', 'frontend', 'backend',
            'load balancer', 'microservice', 'api gateway', 'service mesh', 'container',
            'kubernetes', 'docker', 'redis', 'cache', 'queue', 'message broker',
            'cdn', 'content delivery', 'web server', 'app server', 'database server',
            'nosql', 'sql', 'mongodb', 'postgresql', 'mysql', 'elasticsearch'
        ])
        
        should_generate = explicit_request or modification_request or architecture_keywords
        
        self.logger.info(f"Diagram generation decision - explicit: {explicit_request}, "
                        f"modification: {modification_request}, architecture: {architecture_keywords}, "
                        f"should_generate: {should_generate}")
        
        return should_generate
    
    async def _process_diagram_response(self, response, message: str, session: Dict[str, Any], mcp_client) -> Optional[List]:
        """Process the MCP diagram response and download images."""
        content = response.content
        image_url = None
        
        # Extract image URL from response
        if isinstance(content, dict) and 'content' in content:
            for item in content['content']:
                if isinstance(item, dict) and item.get('type') == 'image':
                    image_url = item.get('data')
                    break
        
        if not image_url or not image_url.startswith('http'):
            self.logger.warning(f"No valid image URL found in MCP response. image_url={image_url}")
            return None
        
        # Download image from S3 for processing
        image_data = await self._download_s3_image_data(image_url)
        if not image_data:
            self.logger.warning("Failed to download S3 image")
            return None
        
        # Create diagram metadata
        diagram_metadata = {
            "format": "png",
            "description": "Generated architecture diagram",
            "title": "Architecture Diagram",
            "generation_timestamp": datetime.utcnow().isoformat(),
            "original_s3_url": image_url
        }
        
        # Save diagram to S3 storage
        project_id = session.get('project_name') or session.get('user_project_name') or session.get('conversation_id', 'default-project')
        try:
            s3_save_success = await self._save_diagram_to_s3(project_id, image_data, diagram_metadata)
            if s3_save_success:
                diagram_metadata['s3_sync'] = True
                diagram_metadata['s3_project_id'] = project_id
                self.logger.info(f"✅ Diagram saved to S3 for project: {project_id}")
            else:
                diagram_metadata['s3_sync'] = False
                self.logger.warning("❌ Failed to save diagram to S3")
        except Exception as s3_error:
            self.logger.warning(f"❌ S3 diagram storage failed: {s3_error}")
            diagram_metadata['s3_sync'] = False
        
        # Generate S3 serving URL
        if s3_save_success:
            # Use S3 serving endpoint
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"architecture_diagram_{timestamp}.png"
            local_url = f"/api/diagrams/{project_id}/serve/{filename}"
            diagram_metadata['filename'] = filename
        else:
            # No fallback - S3 is required
            self.logger.error("Diagram generation failed - S3 storage required")
            return None
        
        # Architecture analysis removed - no longer used in current workflow
        
        # Import DiagramData from routers.sdlc
        from routers.sdlc import DiagramData
        
        diagram_data = [DiagramData(
            diagram_type="architecture",
            diagram_url=local_url,
            diagram_data=None,
            diagram_metadata=diagram_metadata
        )]
        
        self.logger.info(f"Successfully created DiagramData with local URL: {local_url}")
        self.logger.info(f"DiagramData metadata keys: {list(diagram_metadata.keys())}")

        # Trigger code generation after successful diagram generation
        try:
            await self._trigger_code_generation(message, session, diagram_data[0], image_url, mcp_client)
        except Exception as e:
            self.logger.warning(f"Code generation failed after diagram: {e}")
        
        return diagram_data
    
    async def _download_s3_image_data(self, s3_url: str) -> Optional[bytes]:
        """Download image data from S3."""
        try:
            self.logger.info(f"Starting S3 download for URL: {s3_url}")
            
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
            
            self.logger.info(f"Successfully downloaded image data ({len(image_data)} bytes)")
            return image_data
                
        except Exception as e:
            self.logger.error(f"Error downloading S3 image: {e}")
            return None
    
    async def _save_diagram_to_s3(self, project_id: str, image_data: bytes, diagram_metadata: Dict[str, Any]) -> bool:
        """
        Save diagram to S3 storage.
        
        Args:
            project_id: Project identifier
            image_data: Binary image data
            diagram_metadata: Metadata about the diagram
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting S3 diagram save for project: {project_id}")
            
            # Generate a meaningful diagram name based on timestamp and type
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            diagram_name = f"architecture_diagram_{timestamp}"
            format = 'png'  # Default format
            filename = f"{diagram_name}.{format}"
            
            # Prepare metadata for S3 storage
            s3_metadata = {
                **diagram_metadata,
                "filename": filename,
                "project_id": project_id,
                "saved_to_s3_at": datetime.now().isoformat()
            }
            
            # Save diagram to S3
            s3_result = await self.s3_storage_service.save_diagram(
                project_id=project_id,
                diagram_name=diagram_name,
                content=image_data,
                format=format,
                metadata=s3_metadata
            )
            
            if s3_result.success:
                self.logger.info(f"✅ Successfully saved diagram to S3: {project_id}/{diagram_name}.{format}")
                self.logger.info(f"S3 diagram size: {s3_result.data['size_bytes']} bytes")
                return True
            else:
                self.logger.warning(f"❌ Failed to save diagram to S3: {s3_result.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error saving diagram to S3: {e}")
            return False
    
    async def list_project_diagrams(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all diagrams for a project from S3 only (to avoid cross-project contamination).
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of diagram information dictionaries
        """
        try:
            self.logger.info(f"Listing diagrams for project: {project_id}")
            
            diagrams = []
            
            # Get diagrams from S3 only (project-specific)
            try:
                s3_result = await self.s3_storage_service.list_diagrams(project_id)
                
                if s3_result.success:
                    s3_diagrams = s3_result.data
                    self.logger.info(f"Found {len(s3_diagrams)} diagrams in S3 for project {project_id}")
                    diagrams.extend(s3_diagrams)
                else:
                    self.logger.debug(f"No S3 diagrams found: {s3_result.error_message}")
            except Exception as s3_error:
                self.logger.debug(f"S3 diagram listing failed: {s3_error}")
            
            # Only use S3 diagrams for project-specific storage
            
            self.logger.info(f"Total diagrams found for project {project_id}: {len(diagrams)}")
            return diagrams
                
        except Exception as e:
            self.logger.error(f"Error listing project diagrams: {e}")
            return []
    

    
    async def load_diagram_from_s3(self, project_id: str, diagram_name: str, format: str = "png") -> Optional[Dict[str, Any]]:
        """
        Load a specific diagram from S3 and optionally cache it locally.
        
        Args:
            project_id: Project identifier
            diagram_name: Name of the diagram
            format: Diagram format (default: png)
            
        Returns:
            Dictionary with diagram data or None if not found
        """
        try:
            self.logger.info(f"Loading diagram from S3: {project_id}/{diagram_name}.{format}")
            
            s3_result = await self.s3_storage_service.load_diagram(project_id, diagram_name, format)
            
            if s3_result.success:
                diagram_data = s3_result.data
                self.logger.info(f"Successfully loaded diagram: {diagram_data['diagram_name']}")
                return diagram_data
            else:
                self.logger.warning(f"Failed to load diagram from S3: {s3_result.error_message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading diagram from S3: {e}")
            return None
    

    
    async def get_diagram_presigned_url(self, project_id: str, diagram_name: str, format: str = "png", expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for direct S3 access to a diagram.
        
        Args:
            project_id: Project identifier
            diagram_name: Name of the diagram
            format: Diagram format (default: png)
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string or None if failed
        """
        try:
            self.logger.info(f"Generating presigned URL for diagram: {project_id}/{diagram_name}.{format}")
            
            # Use S3 storage service to generate presigned URL
            presigned_result = await self.s3_storage_service.generate_presigned_url(
                project_id=project_id,
                file_type="diagrams",
                filename=f"{diagram_name}.{format}",
                expiration=expiration
            )
            
            if presigned_result.success:
                presigned_url = presigned_result.data.get('presigned_url')
                self.logger.info(f"Generated presigned URL for diagram: {diagram_name}")
                return presigned_url
            else:
                self.logger.warning(f"Failed to generate presigned URL: {presigned_result.error_message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating presigned URL for diagram: {e}")
            return None

    async def delete_diagram_from_s3(self, project_id: str, diagram_name: str, format: str = "png") -> bool:
        """
        Delete a diagram from S3.
        
        Args:
            project_id: Project identifier
            diagram_name: Name of the diagram
            format: Diagram format (default: png)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Deleting diagram from S3: {project_id}/{diagram_name}.{format}")
            
            s3_result = await self.s3_storage_service.delete_diagram(project_id, diagram_name, format)
            
            if s3_result.success:
                self.logger.info(f"Successfully deleted diagram: {s3_result.data['deleted_diagram']}")
                return True
            else:
                self.logger.warning(f"Failed to delete diagram from S3: {s3_result.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting diagram from S3: {e}")
            return False
    
    async def _trigger_code_generation(self, message: str, session: Dict[str, Any], diagram_data, image_url: str, mcp_client=None):
        """Trigger code generation automatically after successful diagram generation.
        This method integrates with the ArchitectureCodeGenerator to produce
        downloadable code files based on the generated diagram and conversation context."""
        try:
            self.logger.info("Starting automatic code generation")
            
            # Import required modules
            from services.architecture_code_models import CodeType, TargetPlatform
            from services.architecture_code_generator import ArchitectureCodeGenerator
            
            # Initialize the architecture code generator
            code_generator = ArchitectureCodeGenerator(mcp_client)
            
            # Create project ID - try to get user-provided name first, fallback to conversation ID
            user_project_name = session.get('project_name') or session.get('user_project_name')
            if user_project_name:
                project_id = user_project_name
                self.logger.info(f"Using user-provided project name: {project_id}")
            else:
                project_id = session.get('conversation_id', 'my-architecture-project')
                self.logger.info(f"Using conversation ID as project name: {project_id}")
            
            # Create diagram response for code generation
            diagram_response = {
                'success': True,
                'diagram_url': image_url,
                'metadata': {
                    'project_id': project_id,
                    'description': message,
                    'diagram_type': diagram_data.diagram_type,
                    'generation_timestamp': diagram_data.diagram_metadata.get('generation_timestamp')
                }
            }
            
            # Create context from session and message
            context = {
                'project_id': project_id,
                'conversation_summary': message,
                'session_messages': session.get('messages', []),
                'phase': session.get('phase', 'design')
            }
            
            # Determine code type based on message content (simplified)
            message_lower = message.lower()
            code_type = CodeType.CLOUDFORMATION  # Default
            if 'terraform' in message_lower:
                code_type = CodeType.TERRAFORM
            elif 'kubernetes' in message_lower or 'k8s' in message_lower:
                code_type = CodeType.KUBERNETES
            
            # Use the full project_id as the project name for consistency with code download API
            project_name = project_id
            
            self.logger.info(f"Generating code for project: {project_id}")
            
            # Generate code (simplified without platform specifics)
            response = await code_generator.generate_code_from_diagram(
                diagram_response=diagram_response,
                context=context,
                code_type=code_type,
                target_platform=TargetPlatform.AWS,  # Default to AWS
                project_name=project_name
            )
            
            if response.success:
                self.logger.info(f"Successfully generated code files for project {project_id}")
                
                # Store code generation info in session for later retrieval
                if 'code_generation' not in session:
                    session['code_generation'] = {}
                
                session['code_generation'][project_id] = {
                    'project_id': response.project_id,
                    'project_name': response.project_name,
                    'files_count': len(response.generated_files),
                    'generated_at': datetime.utcnow().isoformat(),
                    'code_type': code_type.value
                }
            else:
                self.logger.warning(f"Code generation failed: {response.error_message}")
                
        except Exception as e:
            self.logger.warning(f"Error in automatic code generation: {e}")
            # Don't raise the exception to avoid breaking diagram generation
    
    # Architecture analysis methods removed - no longer used in current workflow