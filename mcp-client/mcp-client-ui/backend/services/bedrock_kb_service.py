"""
Bedrock Knowledge Base Service

This service uses AWS Bedrock Knowledge Base with S3 data source for project-specific
document search and retrieval. It uses a single KB with project-based filtering
instead of separate indexes per project.
"""

import os
import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BedrockKBResult:
    """Result of Bedrock KB operations."""
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    context_quality: Optional[str] = None
    total_results: int = 0


@dataclass
class ProjectContext:
    """Project context from KB."""
    project_name: str
    kb_id: str
    kb_ready: bool
    relevant_context: Dict[str, List[Dict[str, Any]]]
    context_quality: str
    recent_activity: List[Dict[str, Any]]


class BedrockKBService:
    """
    Bedrock Knowledge Base Service for project-specific document search.
    
    This service:
    - Uses a single Bedrock KB for all projects
    - Filters results by project using metadata
    - Triggers async ingestion when S3 content changes
    - Provides semantic search across project documents
    """
    
    def __init__(self):
        """Initialize Bedrock KB service."""
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Configuration from environment or use existing KB
        self.kb_id = os.getenv('BEDROCK_KNOWLEDGE_BASE_ID')  # Existing KB ID
        self.data_source_id = os.getenv('BEDROCK_DATA_SOURCE_ID')
        self.s3_bucket = os.getenv('S3_BUCKET_NAME')
        
        # Validate required configuration
        if not self.data_source_id:
            logger.warning("BEDROCK_DATA_SOURCE_ID not configured - ingestion jobs will be disabled")
            self._ingestion_enabled = False
        else:
            self._ingestion_enabled = True
            logger.info(f"Bedrock ingestion enabled with data source ID: {self.data_source_id}")
        
        # Use existing KB configuration
        logger.info(f"Initialized Bedrock KB Service with existing KB ID: {self.kb_id}")
    
    def _validate_project_name(self, project_name: str) -> str:
        """Validate and sanitize project name."""
        if not project_name or len(project_name.strip()) == 0:
            raise ValueError("Project name cannot be empty")
        
        # Sanitize project name for S3 and metadata
        sanitized = project_name.strip().lower().replace(' ', '-').replace('_', '-')
        
        # Remove any characters that aren't alphanumeric or hyphens
        import re
        sanitized = re.sub(r'[^a-z0-9-]', '', sanitized)
        
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized
    
    async def ensure_project_kb_ready(self, project_name: str) -> ProjectContext:
        """
        Ensure project KB is ready for queries.
        
        Since we use a single KB for all projects, this just validates
        the KB exists and triggers ingestion if needed.
        
        Args:
            project_name: Name of the project
            
        Returns:
            ProjectContext with KB readiness status
        """
        try:
            sanitized_name = self._validate_project_name(project_name)
            
            # Check if KB exists and is active
            kb_ready = await self._check_kb_status()
            
            if kb_ready:
                # Trigger direct ingestion for this project
                await self._trigger_direct_ingestion(sanitized_name)
            
            return ProjectContext(
                project_name=sanitized_name,
                kb_id=self.kb_id,
                kb_ready=kb_ready,
                relevant_context={},
                context_quality='ready' if kb_ready else 'not_ready',
                recent_activity=[]
            )
            
        except Exception as e:
            logger.error(f"Error ensuring KB ready for project {project_name}: {e}")
            return ProjectContext(
                project_name=project_name,
                kb_id=self.kb_id,
                kb_ready=False,
                relevant_context={},
                context_quality='error',
                recent_activity=[]
            )
    
    async def _check_kb_status(self) -> bool:
        """Check if Bedrock KB is active and ready."""
        try:
            response = self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=self.kb_id
            )
            
            status = response.get('knowledgeBase', {}).get('status')
            is_ready = status == 'ACTIVE'
            
            logger.info(f"KB {self.kb_id} status: {status}, ready: {is_ready}")
            return is_ready
            
        except Exception as e:
            logger.error(f"Error checking KB status: {e}")
            return False
    
    async def get_project_context(self, project_name: str, query: str, 
                                max_results: int = 10) -> Dict[str, Any]:
        """
        Get project context using Bedrock KB semantic search.
        
        Args:
            project_name: Name of the project to search within
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with relevant context and metadata
        """
        try:
            sanitized_name = self._validate_project_name(project_name)
            
            # Query Bedrock KB with project filtering
            kb_result = await self._query_bedrock_kb(
                query=query,
                project_filter=sanitized_name,
                max_results=max_results
            )
            
            if not kb_result.success:
                logger.warning(f"KB query failed for project {sanitized_name}: {kb_result.error_message}")
                return {
                    'relevant_context': {'documents': []},
                    'context_quality': 'error',
                    'recent_activity': [],
                    'error': kb_result.error_message
                }
            
            # Process and categorize results
            results = kb_result.data or []
            categorized_results = self._categorize_kb_results(results, sanitized_name)
            
            # Determine context quality
            context_quality = self._assess_context_quality(results, query)
            
            # Get recent activity (mock for now - would come from S3 metadata)
            recent_activity = await self._get_recent_project_activity(sanitized_name)
            
            return {
                'relevant_context': categorized_results,
                'context_quality': context_quality,
                'recent_activity': recent_activity,
                'total_results': len(results),
                'query': query,
                'project_name': sanitized_name
            }
            
        except Exception as e:
            logger.error(f"Error getting project context for {project_name}: {e}")
            return {
                'relevant_context': {'documents': []},
                'context_quality': 'error',
                'recent_activity': [],
                'error': str(e)
            }
    
    async def _query_bedrock_kb(self, query: str, project_filter: str, 
                              max_results: int = 10) -> BedrockKBResult:
        """
        Query Bedrock Knowledge Base with project filtering.
        
        Args:
            query: Search query
            project_filter: Project name to filter by
            max_results: Maximum results to return
            
        Returns:
            BedrockKBResult with search results
        """
        try:
            # Prepare the retrieve request with project filtering
            retrieve_request = {
                'knowledgeBaseId': self.kb_id,
                'retrievalQuery': {
                    'text': query
                },
                'retrievalConfiguration': {
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'overrideSearchType': 'SEMANTIC'  # Use semantic search (HYBRID not supported)
                    }
                }
            }
            
            # Note: This KB doesn't support advanced filtering, so we'll filter results post-processing
            # Get more results to filter from if we have a project filter
            if project_filter:
                retrieve_request['retrievalConfiguration']['vectorSearchConfiguration']['numberOfResults'] = max_results * 3
            
            logger.info(f"Querying Bedrock KB for project {project_filter}: {query[:100]}...")
            
            # Execute the retrieve request
            response = self.bedrock_agent.retrieve(**retrieve_request)
            
            # Process results
            retrieval_results = response.get('retrievalResults', [])
            
            processed_results = []
            for result in retrieval_results:
                content = result.get('content', {})
                metadata = result.get('metadata', {})
                score = result.get('score', 0.0)
                source_uri = metadata.get('x-amz-bedrock-kb-source-uri', '')
                
                # Filter by project if specified (post-processing filter like kb/vector_search.py)
                if project_filter and f"projects/{project_filter}/" not in source_uri:
                    continue
                
                processed_result = {
                    'content': content.get('text', ''),
                    'source': source_uri.split('/')[-1] if source_uri else 'unknown',
                    'source_uri': source_uri,
                    'project_id': project_filter,
                    'document_type': self._extract_document_type(source_uri),
                    'score': score,
                    'chunk_id': metadata.get('x-amz-bedrock-kb-chunk-id', ''),
                    'metadata': metadata
                }
                processed_results.append(processed_result)
                
                # Stop when we have enough results
                if len(processed_results) >= max_results:
                    break
            
            logger.info(f"Retrieved {len(processed_results)} results from Bedrock KB")
            
            return BedrockKBResult(
                success=True,
                data=processed_results,
                total_results=len(processed_results)
            )
            
        except Exception as e:
            error_msg = f"Error querying Bedrock KB: {str(e)}"
            logger.error(error_msg)
            return BedrockKBResult(
                success=False,
                error_message=error_msg
            )
    
    def _categorize_kb_results(self, results: List[Dict[str, Any]], 
                             project_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize KB results by document type."""
        categorized = {
            'documents': [],
            'code': [],
            'specifications': [],
            'other': []
        }
        
        for result in results:
            doc_type = result.get('document_type', 'unknown').lower()
            source = result.get('source', '').lower()
            
            # Categorize based on document type or source
            if 'code' in doc_type or any(ext in source for ext in ['.py', '.js', '.ts', '.java', '.cpp']):
                categorized['code'].append(result)
            elif 'spec' in doc_type or 'api' in doc_type or 'specification' in source:
                categorized['specifications'].append(result)
            elif doc_type in ['document', 'markdown', 'text']:
                categorized['documents'].append(result)
            else:
                categorized['other'].append(result)
        
        return categorized
    
    def _extract_document_type(self, source_uri: str) -> str:
        """Extract document type from source URI (copied from kb/ approach)."""
        if not source_uri:
            return 'unknown'
        
        if 'conversation.json' in source_uri:
            return 'conversation'
        elif 'metadata.json' in source_uri:
            return 'metadata'
        elif 'summary.json' in source_uri:
            return 'summary'
        elif 'jira_data.json' in source_uri:
            return 'jira'
        else:
            return 'document'
    
    def _assess_context_quality(self, results: List[Dict[str, Any]], query: str) -> str:
        """Assess the quality of retrieved context."""
        if not results:
            return 'no_results'
        
        # Check average score
        scores = [r.get('score', 0.0) for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        if avg_score > 0.8:
            return 'excellent'
        elif avg_score > 0.6:
            return 'good'
        elif avg_score > 0.4:
            return 'fair'
        else:
            return 'poor'
    
    async def _get_recent_project_activity(self, project_name: str) -> List[Dict[str, Any]]:
        """Get recent activity for a project (mock implementation)."""
        # In a real implementation, this would query S3 for recent file changes
        return [
            {
                'type': 'document_updated',
                'file': f'projects/{project_name}/docs/api-spec.md',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': 'modified'
            }
        ]
    
    async def _trigger_direct_ingestion(self, project_name: str) -> bool:
        """
        Trigger direct ingestion for a project using Bedrock API.
        
        Args:
            project_name: Name of the project
            
        Returns:
            True if ingestion was triggered successfully
        """
        try:
            logger.info(f"Triggering direct ingestion for project {project_name}")
            
            # Start ingestion job directly using Bedrock Agent API
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                description=f'Auto ingestion for project {project_name} - {datetime.now().isoformat()}'
            )
            
            job_id = response.get('ingestionJob', {}).get('ingestionJobId')
            status = response.get('ingestionJob', {}).get('status')
            
            logger.info(f"Started ingestion job {job_id} for project {project_name} with status {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error triggering direct ingestion for project {project_name}: {e}")
            return False
    
    async def trigger_s3_ingestion(self, project_name: str, s3_key: str = None) -> bool:
        """
        Trigger ingestion when S3 content changes using direct API call.
        
        This is called when files are added/updated in S3 for a project.
        
        Args:
            project_name: Name of the project
            s3_key: Specific S3 key that changed (optional)
            
        Returns:
            True if ingestion was triggered successfully
        """
        try:
            sanitized_name = self._validate_project_name(project_name)
            
            logger.info(f"Triggering S3 ingestion for project {sanitized_name}, key: {s3_key}")
            
            # Start ingestion job directly
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                description=f'S3 change ingestion for project {sanitized_name} - {s3_key or "multiple files"} - {datetime.now().isoformat()}'
            )
            
            job_id = response.get('ingestionJob', {}).get('ingestionJobId')
            status = response.get('ingestionJob', {}).get('status')
            
            logger.info(f"Started S3 ingestion job {job_id} for project {sanitized_name} with status {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error triggering S3 ingestion for project {project_name}: {e}")
            return False
    
    async def get_project_stats(self, project_name: str) -> Dict[str, Any]:
        """
        Get statistics for a project's KB content.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dictionary with project statistics
        """
        try:
            sanitized_name = self._validate_project_name(project_name)
            
            # Query for all documents in this project (with empty query to get all)
            kb_result = await self._query_bedrock_kb(
                query="",  # Empty query to get all documents
                project_filter=sanitized_name,
                max_results=100  # Get more results for stats
            )
            
            if not kb_result.success:
                return {
                    'error': kb_result.error_message,
                    'document_count': 0,
                    'last_sync': None
                }
            
            results = kb_result.data or []
            
            # Calculate statistics
            doc_types = {}
            sources = set()
            
            for result in results:
                doc_type = result.get('document_type', 'unknown')
                source = result.get('source', 'unknown')
                
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                sources.add(source)
            
            return {
                'document_count': len(results),
                'document_types': doc_types,
                'unique_sources': len(sources),
                'last_sync': datetime.now(timezone.utc).isoformat(),  # Mock - would come from ingestion logs
                'kb_id': self.kb_id,
                'project_name': sanitized_name
            }
            
        except Exception as e:
            logger.error(f"Error getting project stats for {project_name}: {e}")
            return {
                'error': str(e),
                'document_count': 0,
                'last_sync': None
            }
    
    async def start_ingestion_job(self, project_name: str = None) -> Dict[str, Any]:
        """
        Start a manual ingestion job for the entire KB or specific project.
        
        Args:
            project_name: Optional project name to ingest (None for all projects)
            
        Returns:
            Dictionary with ingestion job information
        """
        try:
            # Start ingestion job using Bedrock Agent
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                description=f'Manual ingestion job for {project_name or "all projects"} - {datetime.now().isoformat()}'
            )
            
            job_id = response.get('ingestionJob', {}).get('ingestionJobId')
            status = response.get('ingestionJob', {}).get('status')
            
            logger.info(f"Started ingestion job {job_id} with status {status}")
            
            return {
                'success': True,
                'job_id': job_id,
                'status': status,
                'project_name': project_name,
                'kb_id': self.kb_id,
                'data_source_id': self.data_source_id
            }
            
        except Exception as e:
            error_msg = f"Error starting ingestion job: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'project_name': project_name
            }