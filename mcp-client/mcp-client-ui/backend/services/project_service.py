"""Enhanced Project Service with S3 persistence integration."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .s3_storage_service import S3StorageService, S3OperationResult

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Project context data model."""
    project_id: str
    metadata: Dict[str, Any]
    generated_code_versions: List[str]
    diagrams: List[str]
    last_sync: Optional[datetime]
    s3_sync_status: str  # 'synced', 'pending', 'error', 'local_only'


@dataclass
class ProjectSyncResult:
    """Result of project synchronization operation."""
    success: bool
    project_id: str
    sync_status: str
    error_message: Optional[str] = None
    files_synced: int = 0


class ProjectService:
    """Enhanced project service with S3 persistence capabilities."""
    
    def __init__(self, s3_service: Optional[S3StorageService] = None):
        """
        Initialize project service.
        
        Args:
            s3_service: S3 storage service instance (creates default if None)
        """
        self.s3_service = s3_service or S3StorageService()
    

    
    async def create_project(self, project_data: Dict[str, Any]) -> str:
        """
        Create a new project directly in S3.
        
        Args:
            project_data: Project metadata dictionary
            
        Returns:
            Project ID
        """
        # Generate project ID from name if not provided
        project_id = project_data.get('name', f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Add creation metadata
        enhanced_project_data = {
            **project_data,
            'project_id': project_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_updated': datetime.now(timezone.utc).isoformat(),
            's3_sync_status': 'synced'
        }
        
        # Save directly to S3
        s3_result = await self.s3_service.save_project_metadata(project_id, enhanced_project_data)
        if not s3_result.success:
            raise RuntimeError(f"Failed to save project to S3: {s3_result.error_message}")
        
        logger.info(f"Created project: {project_id}")
        return project_id
    
    async def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Load project directly from S3.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Project data dictionary or None if not found
        """
        # Load directly from S3
        s3_result = await self.s3_service.load_project_metadata(project_id)
        if s3_result.success and s3_result.data:
            logger.info(f"Loaded project from S3: {project_id}")
            return s3_result.data
        
        logger.warning(f"Project not found in S3 storage: {project_id}")
        return None
    
    async def save_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """
        Save project directly to S3.
        
        Args:
            project_id: Project identifier
            project_data: Project data dictionary
            
        Returns:
            True if saved successfully
        """
        # Update metadata
        enhanced_project_data = {
            **project_data,
            'project_id': project_id,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            's3_sync_status': 'synced'
        }
        
        # Save directly to S3
        s3_result = await self.s3_service.save_project_metadata(project_id, enhanced_project_data)
        
        logger.info(f"Saved project: {project_id}, S3 result: {s3_result.success}")
        return s3_result.success
    

    
    async def project_exists(self, project_id: str) -> bool:
        """
        Check project existence in S3 storage.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if project exists in S3
        """
        # Check S3 existence
        s3_result = await self.s3_service.load_project_metadata(project_id)
        return s3_result.success
    
    async def save_project_context(self, project_id: str) -> bool:
        """
        Save complete project context including metadata and related files.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if context saved successfully
        """
        try:
            # Load current project data
            project_data = await self.load_project(project_id)
            if not project_data:
                logger.error(f"Cannot save context for non-existent project: {project_id}")
                return False
            
            # Create project context
            context = ProjectContext(
                project_id=project_id,
                metadata=project_data,
                generated_code_versions=self._get_generated_code_versions(project_id),
                diagrams=self._get_project_diagrams(project_id),
                last_sync=datetime.now(timezone.utc),
                s3_sync_status='pending'
            )
            
            # Save context metadata
            context_data = {
                'project_id': context.project_id,
                'metadata': context.metadata,
                'generated_code_versions': context.generated_code_versions,
                'diagrams': context.diagrams,
                'last_sync': context.last_sync.isoformat() if context.last_sync else None,
                's3_sync_status': 'synced'
            }
            
            # Save directly to S3
            s3_result = await self.s3_service.save_project_metadata(project_id, context_data)
            
            return s3_result.success
            
        except Exception as e:
            logger.error(f"Error saving project context: {str(e)}")
            return False
    
    async def restore_project_context(self, project_id: str) -> bool:
        """
        Restore complete project context from storage.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if context restored successfully
        """
        try:
            # Load project data with S3 fallback
            project_data = await self.load_project(project_id)
            if not project_data:
                logger.error(f"Cannot restore context for non-existent project: {project_id}")
                return False
            
            logger.info(f"Restored project context: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring project context: {str(e)}")
            return False
    
    def _get_generated_code_versions(self, project_id: str) -> List[str]:
        """Get list of generated code versions for project from S3 only."""
        # This method is deprecated - code versions are now managed in S3
        # Return empty list as local storage is no longer used
        return []
    
    def _get_project_diagrams(self, project_id: str) -> List[str]:
        """Get list of diagrams for project from S3 only."""
        # Diagrams are now stored in S3, not locally
        # Use DiagramService.list_project_diagrams() for S3-based diagram listing
        return []
    
    async def list_projects(self) -> Dict[str, List[str]]:
        """
        List projects from both local and S3 storage.
        
        Returns:
            Dictionary with local and s3 project lists
        """
        # Get local projects
        local_projects = []
        try:
            if os.path.exists(self.local_storage_path):
                local_projects = [
                    f.replace('.json', '') for f in os.listdir(self.local_storage_path)
                    if f.endswith('.json')
                ]
        except Exception as e:
            logger.error(f"Error listing local projects: {str(e)}")
        
        # Get S3 projects
        s3_projects = []
        try:
            s3_result = await self.s3_service.list_projects()
            if s3_result.success and s3_result.data:
                s3_projects = s3_result.data
        except Exception as e:
            logger.error(f"Error listing S3 projects: {str(e)}")
        
        # Combine and deduplicate
        all_projects = list(set(local_projects + s3_projects))
        
        return {
            'local': local_projects,
            's3': s3_projects,
            'all': all_projects
        }