"""S3 Storage Service for project context persistence."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .s3_config import s3_config_service

logger = logging.getLogger(__name__)


@dataclass
class S3OperationResult:
    """Result of an S3 operation."""
    success: bool
    error_message: Optional[str] = None
    data: Optional[Any] = None


class S3StorageService:
    """Service for handling S3 operations for project data persistence."""
    
    def __init__(self, bucket_name: Optional[str] = None, aws_region: Optional[str] = None):
        """
        Initialize S3 storage service.
        
        Args:
            bucket_name: S3 bucket name (uses config default if None)
            aws_region: AWS region (uses config default if None)
        """
        self.bucket_name = bucket_name or s3_config_service.get_bucket_configuration()["bucket_name"]
        self.aws_region = aws_region or s3_config_service.get_bucket_configuration()["region"]
        self._s3_client = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    def _get_s3_client(self) -> boto3.client:
        """
        Get or create S3 client.
        
        Returns:
            boto3 S3 client
            
        Raises:
            RuntimeError: If S3 client cannot be created or validated
        """
        if not self._s3_client:
            self._s3_client = s3_config_service.get_s3_client()
            if not self._s3_client:
                raise RuntimeError("Failed to create or validate S3 client")
        return self._s3_client
    
    def _generate_s3_key(self, project_id: str, file_type: str, filename: str = "") -> str:
        """
        Generate S3 key for project files.
        
        Args:
            project_id: Project identifier
            file_type: Type of file (metadata, generated-code, diagrams, sessions)
            filename: Optional filename for specific files
            
        Returns:
            S3 key path
        """
        base_key = f"projects/{project_id}"
        
        if file_type == "metadata":
            return f"{base_key}/metadata.json"
        elif file_type == "generated-code":
            if filename:
                return f"{base_key}/generated-code/{filename}"
            return f"{base_key}/generated-code/"
        elif file_type == "diagrams":
            if filename:
                return f"{base_key}/diagrams/{filename}"
            return f"{base_key}/diagrams/"
        elif file_type == "sessions":
            if filename:
                return f"{base_key}/sessions/{filename}"
            return f"{base_key}/sessions/"
        else:
            return f"{base_key}/{file_type}/{filename}" if filename else f"{base_key}/{file_type}/"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, ConnectionError))
    )
    def _sync_put_object(self, key: str, body: bytes, content_type: str = "application/json") -> bool:
        """
        Synchronous put object to S3 with retry logic.
        
        Args:
            key: S3 object key
            body: Object content as bytes
            content_type: Content type header
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ClientError: If S3 operation fails after retries
        """
        try:
            s3_client = self._get_s3_client()
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type,
                ServerSideEncryption='AES256'
            )
            logger.debug(f"Successfully uploaded object to S3: {key}")
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to upload object to S3 {key}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3 {key}: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "UnexpectedError", "Message": str(e)}},
                operation_name="PutObject"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, ConnectionError))
    )
    def _sync_get_object(self, key: str) -> Optional[bytes]:
        """
        Synchronous get object from S3 with retry logic.
        
        Args:
            key: S3 object key
            
        Returns:
            Object content as bytes, None if not found
            
        Raises:
            ClientError: If S3 operation fails after retries (except NoSuchKey)
        """
        try:
            s3_client = self._get_s3_client()
            response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read()
            logger.debug(f"Successfully retrieved object from S3: {key}")
            return content
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.debug(f"Object not found in S3: {key}")
                return None
            logger.error(f"Failed to retrieve object from S3 {key}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving from S3 {key}: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "UnexpectedError", "Message": str(e)}},
                operation_name="GetObject"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, ConnectionError))
    )
    def _sync_list_objects(self, prefix: str) -> List[str]:
        """
        Synchronous list objects in S3 with retry logic.
        
        Args:
            prefix: S3 key prefix to filter objects
            
        Returns:
            List of object keys
            
        Raises:
            ClientError: If S3 operation fails after retries
        """
        try:
            s3_client = self._get_s3_client()
            response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            
            objects = []
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
            
            logger.debug(f"Successfully listed {len(objects)} objects with prefix: {prefix}")
            return objects
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to list objects in S3 with prefix {prefix}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing S3 objects with prefix {prefix}: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "UnexpectedError", "Message": str(e)}},
                operation_name="ListObjects"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, ConnectionError))
    )
    def _sync_list_objects_with_metadata(self, prefix: str) -> List[dict]:
        """
        Synchronous list objects in S3 with full metadata.
        
        Args:
            prefix: S3 key prefix to filter objects
            
        Returns:
            List of object metadata dictionaries
            
        Raises:
            ClientError: If S3 operation fails after retries
        """
        try:
            s3_client = self._get_s3_client()
            response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            
            objects = []
            if 'Contents' in response:
                objects = response['Contents']  # Return full object metadata
            
            logger.debug(f"Successfully listed {len(objects)} objects with metadata for prefix: {prefix}")
            return objects
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to list objects with metadata in S3 with prefix {prefix}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing S3 objects with metadata for prefix {prefix}: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "UnexpectedError", "Message": str(e)}},
                operation_name="ListObjects"
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to list objects in S3 with prefix {prefix}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing S3 objects with prefix {prefix}: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "UnexpectedError", "Message": str(e)}},
                operation_name="ListObjects"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, ConnectionError))
    )
    def _sync_delete_object(self, key: str) -> bool:
        """
        Synchronous delete object from S3 with retry logic.
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ClientError: If S3 operation fails after retries
        """
        try:
            s3_client = self._get_s3_client()
            s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Successfully deleted object from S3: {key}")
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to delete object from S3 {key}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting from S3 {key}: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "UnexpectedError", "Message": str(e)}},
                operation_name="DeleteObject"
            )
    
    async def save_project_metadata(self, project_id: str, metadata: Dict[str, Any]) -> S3OperationResult:
        """
        Save project metadata to S3.
        
        Args:
            project_id: Project identifier
            metadata: Project metadata dictionary
            
        Returns:
            S3OperationResult with operation status
        """
        try:
            # Add timestamp to metadata
            metadata_with_timestamp = {
                **metadata,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id
            }
            
            # Convert to JSON bytes
            json_data = json.dumps(metadata_with_timestamp, indent=2).encode('utf-8')
            
            # Generate S3 key
            s3_key = self._generate_s3_key(project_id, "metadata")
            
            # Upload to S3 asynchronously
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_put_object, 
                s3_key, 
                json_data, 
                "application/json"
            )
            
            if success:
                logger.info(f"Successfully saved project metadata to S3: {project_id}")
                
                # Trigger KB ingestion for new/updated metadata
                try:
                    from services.simple_tool_service import SimpleToolService
                    
                    tool_service = SimpleToolService()
                    # Trigger async KB ingestion - don't wait for completion
                    asyncio.create_task(tool_service.trigger_s3_ingestion(project_id, s3_key))
                    logger.info(f"Triggered KB ingestion for project metadata: {project_id}")
                except Exception as e:
                    logger.warning(f"Failed to trigger KB ingestion for project {project_id}: {e}")
                
                return S3OperationResult(success=True, data={"s3_key": s3_key})
            else:
                return S3OperationResult(success=False, error_message="Failed to upload metadata")
                
        except Exception as e:
            error_msg = f"Error saving project metadata to S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def load_project_metadata(self, project_id: str) -> S3OperationResult:
        """
        Load project metadata from S3.
        
        Args:
            project_id: Project identifier
            
        Returns:
            S3OperationResult with metadata or error
        """
        try:
            # Generate S3 key
            s3_key = self._generate_s3_key(project_id, "metadata")
            
            # Download from S3 asynchronously
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor, 
                self._sync_get_object, 
                s3_key
            )
            
            if content is None:
                return S3OperationResult(
                    success=False, 
                    error_message=f"Project metadata not found: {project_id}"
                )
            
            # Parse JSON
            metadata = json.loads(content.decode('utf-8'))
            
            logger.info(f"Successfully loaded project metadata from S3: {project_id}")
            return S3OperationResult(success=True, data=metadata)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in project metadata: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Error loading project metadata from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def list_projects(self) -> S3OperationResult:
        """
        List all projects in S3.
        
        Returns:
            S3OperationResult with list of project IDs
        """
        try:
            # List objects with projects prefix
            prefix = "projects/"
            
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            # Extract project IDs from keys
            project_ids = set()
            for key in object_keys:
                # Keys look like: projects/{project_id}/metadata.json
                parts = key.split('/')
                if len(parts) >= 2 and parts[0] == "projects":
                    project_ids.add(parts[1])
            
            project_list = sorted(list(project_ids))
            
            logger.info(f"Successfully listed {len(project_list)} projects from S3")
            return S3OperationResult(success=True, data=project_list)
            
        except Exception as e:
            error_msg = f"Error listing projects from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def project_exists(self, project_id: str) -> S3OperationResult:
        """
        Check if a project exists in S3.
        
        Args:
            project_id: Project identifier
            
        Returns:
            S3OperationResult with boolean data indicating existence
        """
        try:
            # Try to load metadata to check existence
            result = await self.load_project_metadata(project_id)
            exists = result.success
            
            logger.debug(f"Project existence check for {project_id}: {exists}")
            return S3OperationResult(success=True, data=exists)
            
        except Exception as e:
            error_msg = f"Error checking project existence: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def delete_project(self, project_id: str) -> S3OperationResult:
        """
        Delete a project and all its data from S3.
        
        Args:
            project_id: Project identifier
            
        Returns:
            S3OperationResult with operation status
        """
        try:
            # List all objects for this project
            prefix = f"projects/{project_id}/"
            
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            if not object_keys:
                return S3OperationResult(
                    success=False, 
                    error_message=f"Project not found: {project_id}"
                )
            
            # Delete all objects for this project
            deleted_count = 0
            for key in object_keys:
                try:
                    await loop.run_in_executor(
                        self._executor, 
                        self._sync_delete_object, 
                        key
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete object {key}: {str(e)}")
            
            logger.info(f"Successfully deleted {deleted_count} objects for project: {project_id}")
            return S3OperationResult(
                success=True, 
                data={"deleted_objects": deleted_count}
            )
            
        except Exception as e:
            error_msg = f"Error deleting project from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def save_generated_code(self, project_id: str, files: Dict[str, str], version: Optional[str] = None) -> S3OperationResult:
        """
        Save generated code files to S3.
        
        Args:
            project_id: Project identifier
            files: Dictionary of filename -> content
            version: Optional version identifier (defaults to timestamp)
            
        Returns:
            S3OperationResult with operation status
        """
        try:
            if not version:
                version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
            uploaded_files = []
            
            # Upload each file
            for filename, content in files.items():
                # Generate versioned key
                s3_key = self._generate_s3_key(project_id, "generated-code", f"{version}/{filename}")
                
                # Convert content to bytes
                if isinstance(content, str):
                    file_bytes = content.encode('utf-8')
                    content_type = "text/plain"
                else:
                    file_bytes = content
                    content_type = "application/octet-stream"
                
                # Upload to S3
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    self._executor, 
                    self._sync_put_object, 
                    s3_key, 
                    file_bytes, 
                    content_type
                )
                
                if success:
                    uploaded_files.append(s3_key)
                    
                    # Also save as "latest" version
                    latest_key = self._generate_s3_key(project_id, "generated-code", f"latest/{filename}")
                    await loop.run_in_executor(
                        self._executor, 
                        self._sync_put_object, 
                        latest_key, 
                        file_bytes, 
                        content_type
                    )
            
            logger.info(f"Successfully saved {len(uploaded_files)} generated code files to S3: {project_id}")
            return S3OperationResult(
                success=True, 
                data={
                    "version": version,
                    "uploaded_files": uploaded_files,
                    "file_count": len(uploaded_files)
                }
            )
            
        except Exception as e:
            error_msg = f"Error saving generated code to S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def load_generated_code(self, project_id: str, version: str = "latest") -> S3OperationResult:
        """
        Load generated code files from S3.
        
        Args:
            project_id: Project identifier
            version: Version to load (defaults to "latest")
            
        Returns:
            S3OperationResult with files dictionary
        """
        try:
            # List files for the specified version
            prefix = self._generate_s3_key(project_id, "generated-code", f"{version}/")
            
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            if not object_keys:
                return S3OperationResult(
                    success=False, 
                    error_message=f"No generated code found for project {project_id} version {version}"
                )
            
            # Download each file
            files = {}
            for key in object_keys:
                # Extract filename from key
                filename = key.split('/')[-1]
                
                # Download content
                content = await loop.run_in_executor(
                    self._executor, 
                    self._sync_get_object, 
                    key
                )
                
                if content:
                    try:
                        # Try to decode as text
                        files[filename] = content.decode('utf-8')
                    except UnicodeDecodeError:
                        # Keep as bytes for binary files
                        files[filename] = content
            
            logger.info(f"Successfully loaded {len(files)} generated code files from S3: {project_id}")
            return S3OperationResult(
                success=True, 
                data={
                    "version": version,
                    "files": files,
                    "file_count": len(files)
                }
            )
            
        except Exception as e:
            error_msg = f"Error loading generated code from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def list_code_versions(self, project_id: str) -> S3OperationResult:
        """
        List available code versions for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            S3OperationResult with list of versions
        """
        try:
            # List objects in generated-code directory
            prefix = self._generate_s3_key(project_id, "generated-code")
            
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            # Extract versions from keys
            versions = set()
            for key in object_keys:
                # Keys look like: projects/{project_id}/generated-code/{version}/{filename}
                parts = key.split('/')
                if len(parts) >= 4 and parts[2] == "generated-code":
                    versions.add(parts[3])
            
            version_list = sorted(list(versions))
            
            logger.info(f"Successfully listed {len(version_list)} code versions for project: {project_id}")
            return S3OperationResult(success=True, data=version_list)
            
        except Exception as e:
            error_msg = f"Error listing code versions from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def save_diagram(self, project_id: str, diagram_name: str, content: bytes, format: str = "png", metadata: Optional[Dict[str, Any]] = None) -> S3OperationResult:
        """
        Save diagram file to S3.
        
        Args:
            project_id: Project identifier
            diagram_name: Name of the diagram (without extension)
            content: Diagram content as bytes
            format: Diagram format (png, svg, etc.)
            metadata: Optional metadata dictionary
            
        Returns:
            S3OperationResult with operation status
        """
        try:
            # Ensure diagram name has proper extension
            if not diagram_name.endswith(f'.{format}'):
                diagram_filename = f"{diagram_name}.{format}"
            else:
                diagram_filename = diagram_name
            
            # Generate S3 key for diagram
            s3_key = self._generate_s3_key(project_id, "diagrams", diagram_filename)
            
            # Determine content type based on format
            content_type_map = {
                'png': 'image/png',
                'svg': 'image/svg+xml',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif'
            }
            content_type = content_type_map.get(format.lower(), 'application/octet-stream')
            
            # Upload diagram to S3
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_put_object, 
                s3_key, 
                content, 
                content_type
            )
            
            if success:
                # Save metadata if provided
                if metadata:
                    metadata_key = self._generate_s3_key(project_id, "diagrams", f"{diagram_name}_metadata.json")
                    metadata_with_timestamp = {
                        **metadata,
                        "diagram_name": diagram_name,
                        "format": format,
                        "saved_at": datetime.now(timezone.utc).isoformat(),
                        "s3_key": s3_key
                    }
                    metadata_json = json.dumps(metadata_with_timestamp, indent=2).encode('utf-8')
                    
                    await loop.run_in_executor(
                        self._executor, 
                        self._sync_put_object, 
                        metadata_key, 
                        metadata_json, 
                        "application/json"
                    )
                
                logger.info(f"Successfully saved diagram to S3: {project_id}/{diagram_filename}")
                return S3OperationResult(
                    success=True, 
                    data={
                        "s3_key": s3_key,
                        "diagram_name": diagram_filename,
                        "format": format,
                        "size_bytes": len(content)
                    }
                )
            else:
                return S3OperationResult(success=False, error_message="Failed to upload diagram")
                
        except Exception as e:
            error_msg = f"Error saving diagram to S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def load_diagram(self, project_id: str, diagram_name: str, format: str = "png") -> S3OperationResult:
        """
        Load diagram file from S3.
        
        Args:
            project_id: Project identifier
            diagram_name: Name of the diagram (with or without extension)
            format: Expected diagram format
            
        Returns:
            S3OperationResult with diagram content and metadata
        """
        try:
            # Ensure diagram name has proper extension
            if not diagram_name.endswith(f'.{format}'):
                diagram_filename = f"{diagram_name}.{format}"
            else:
                diagram_filename = diagram_name
                diagram_name = diagram_name.rsplit('.', 1)[0]  # Remove extension for metadata lookup
            
            # Generate S3 key for diagram
            s3_key = self._generate_s3_key(project_id, "diagrams", diagram_filename)
            
            # Download diagram from S3
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor, 
                self._sync_get_object, 
                s3_key
            )
            
            if content is None:
                return S3OperationResult(
                    success=False, 
                    error_message=f"Diagram not found: {project_id}/{diagram_filename}"
                )
            
            # Try to load metadata
            metadata = None
            try:
                metadata_key = self._generate_s3_key(project_id, "diagrams", f"{diagram_name}_metadata.json")
                metadata_content = await loop.run_in_executor(
                    self._executor, 
                    self._sync_get_object, 
                    metadata_key
                )
                if metadata_content:
                    metadata = json.loads(metadata_content.decode('utf-8'))
            except Exception as meta_error:
                logger.debug(f"Could not load diagram metadata: {meta_error}")
            
            logger.info(f"Successfully loaded diagram from S3: {project_id}/{diagram_filename}")
            return S3OperationResult(
                success=True, 
                data={
                    "content": content,
                    "diagram_name": diagram_filename,
                    "format": format,
                    "size_bytes": len(content),
                    "metadata": metadata
                }
            )
            
        except Exception as e:
            error_msg = f"Error loading diagram from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def list_diagrams(self, project_id: str) -> S3OperationResult:
        """
        List all diagrams for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            S3OperationResult with list of diagram information
        """
        try:
            # List objects in diagrams directory
            prefix = self._generate_s3_key(project_id, "diagrams")
            
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            # Process diagram files (exclude metadata files)
            diagrams = []
            for key in object_keys:
                filename = key.split('/')[-1]
                
                # Skip metadata files
                if filename.endswith('_metadata.json'):
                    continue
                
                # Extract diagram info
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    diagram_name, format = name_parts
                    # Extract timestamp for ordering
                    import re
                    timestamp_match = re.search(r'(\d{8}_\d{6})', diagram_name)
                    timestamp = timestamp_match.group(1) if timestamp_match else None
                    
                    diagrams.append({
                        "name": diagram_name,
                        "filename": filename,
                        "format": format,
                        "s3_key": key,
                        "timestamp": timestamp,
                        "is_latest": False  # Will be set after sorting
                    })
            
            # Sort by name (newest first) - extract timestamp from filename
            def extract_timestamp(diagram):
                name = diagram['name']
                # Extract timestamp from names like "architecture_diagram_20250719_223224"
                import re
                match = re.search(r'(\d{8}_\d{6})', name)
                if match:
                    return match.group(1)
                return name
            
            diagrams.sort(key=extract_timestamp, reverse=True)
            
            # Mark the latest diagram
            if diagrams:
                diagrams[0]['is_latest'] = True
            
            logger.info(f"Successfully listed {len(diagrams)} diagrams for project: {project_id}")
            return S3OperationResult(success=True, data=diagrams)
            
        except Exception as e:
            error_msg = f"Error listing diagrams from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    async def delete_diagram(self, project_id: str, diagram_name: str, format: str = "png") -> S3OperationResult:
        """
        Delete a diagram from S3.
        
        Args:
            project_id: Project identifier
            diagram_name: Name of the diagram (with or without extension)
            format: Diagram format
            
        Returns:
            S3OperationResult with operation status
        """
        try:
            # Ensure diagram name has proper extension
            if not diagram_name.endswith(f'.{format}'):
                diagram_filename = f"{diagram_name}.{format}"
            else:
                diagram_filename = diagram_name
                diagram_name = diagram_name.rsplit('.', 1)[0]  # Remove extension for metadata lookup
            
            # Delete diagram file
            diagram_key = self._generate_s3_key(project_id, "diagrams", diagram_filename)
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_delete_object, 
                diagram_key
            )
            
            # Also try to delete metadata file
            try:
                metadata_key = self._generate_s3_key(project_id, "diagrams", f"{diagram_name}_metadata.json")
                await loop.run_in_executor(
                    self._executor, 
                    self._sync_delete_object, 
                    metadata_key
                )
            except Exception as meta_error:
                logger.debug(f"Could not delete diagram metadata (may not exist): {meta_error}")
            
            if success:
                logger.info(f"Successfully deleted diagram from S3: {project_id}/{diagram_filename}")
                return S3OperationResult(success=True, data={"deleted_diagram": diagram_filename})
            else:
                return S3OperationResult(success=False, error_message="Failed to delete diagram")
                
        except Exception as e:
            error_msg = f"Error deleting diagram from S3: {str(e)}"
            logger.error(error_msg)
            return S3OperationResult(success=False, error_message=error_msg)
    
    def close(self):
        """Close the executor and clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("S3StorageService executor shut down")
    
    # PDF Storage Methods
    
    async def save_pdf(self, project_id: str, phase: str, pdf_data: bytes, filename: str = None) -> S3OperationResult:
        """
        Save PDF to S3.
        
        Args:
            project_id: Project identifier
            phase: SDLC phase
            pdf_data: PDF binary data
            filename: Optional custom filename
            
        Returns:
            S3OperationResult with success status and metadata
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"{phase}_specification_{timestamp}.pdf"
            
            # S3 key structure: pdfs/{project_id}/{filename}
            s3_key = f"pdfs/{project_id}/{filename}"
            
            # Save to S3
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                self._sync_put_object,
                s3_key,
                pdf_data,
                "application/pdf"
            )
            
            # Generate metadata
            metadata = {
                "project_id": project_id,
                "phase": phase,
                "filename": filename,
                "s3_key": s3_key,
                "size": len(pdf_data),
                "content_type": "application/pdf",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "version": timestamp if not filename else "custom"
            }
            
            logger.info(f"Successfully saved PDF to S3: {s3_key}")
            
            return S3OperationResult(
                success=True,
                data=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to save PDF to S3: {str(e)}")
            return S3OperationResult(
                success=False,
                error_message=f"Failed to save PDF: {str(e)}"
            )
    
    async def load_pdf(self, project_id: str, filename: str) -> S3OperationResult:
        """
        Load PDF from S3.
        
        Args:
            project_id: Project identifier
            filename: PDF filename
            
        Returns:
            S3OperationResult with PDF data
        """
        try:
            s3_key = f"pdfs/{project_id}/{filename}"
            
            loop = asyncio.get_event_loop()
            pdf_data = await loop.run_in_executor(
                self._executor,
                self._sync_get_object,
                s3_key
            )
            
            logger.info(f"Successfully loaded PDF from S3: {s3_key}")
            
            return S3OperationResult(
                success=True,
                data=pdf_data
            )
            
        except Exception as e:
            logger.error(f"Failed to load PDF from S3: {str(e)}")
            return S3OperationResult(
                success=False,
                error_message=f"Failed to load PDF: {str(e)}"
            )
    
    async def list_project_pdfs(self, project_id: str) -> S3OperationResult:
        """
        List all PDFs for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            S3OperationResult with list of PDF metadata
        """
        try:
            prefix = f"pdfs/{project_id}/"
            
            loop = asyncio.get_event_loop()
            objects = await loop.run_in_executor(
                self._executor,
                self._sync_list_objects_with_metadata,
                prefix
            )
            
            pdfs = []
            if objects:
                for obj in objects:
                    # Handle both dict and string formats
                    if isinstance(obj, dict):
                        filename = obj['Key'].replace(prefix, '')
                        pdfs.append({
                            "filename": filename,
                            "s3_key": obj['Key'],
                            "size": obj.get('Size', 0),
                            "last_modified": obj.get('LastModified', datetime.now(timezone.utc)).isoformat() if hasattr(obj.get('LastModified'), 'isoformat') else str(obj.get('LastModified', '')),
                            "phase": self._extract_phase_from_filename(filename)
                        })
                    else:
                        # Handle string format (just key)
                        filename = str(obj).replace(prefix, '')
                        if filename:  # Skip empty filenames
                            pdfs.append({
                                "filename": filename,
                                "s3_key": str(obj),
                                "size": 0,
                                "last_modified": datetime.now(timezone.utc).isoformat(),
                                "phase": self._extract_phase_from_filename(filename)
                            })
            
            logger.info(f"Found {len(pdfs)} PDFs for project {project_id}")
            
            return S3OperationResult(
                success=True,
                data=pdfs
            )
            
        except Exception as e:
            logger.error(f"Failed to list PDFs for project {project_id}: {str(e)}")
            return S3OperationResult(
                success=False,
                error_message=f"Failed to list PDFs: {str(e)}"
            )
    
    async def delete_pdf(self, project_id: str, filename: str) -> S3OperationResult:
        """
        Delete PDF from S3.
        
        Args:
            project_id: Project identifier
            filename: PDF filename
            
        Returns:
            S3OperationResult with success status
        """
        try:
            s3_key = f"pdfs/{project_id}/{filename}"
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                self._sync_delete_object,
                s3_key
            )
            
            logger.info(f"Successfully deleted PDF from S3: {s3_key}")
            
            return S3OperationResult(success=True)
            
        except Exception as e:
            logger.error(f"Failed to delete PDF from S3: {str(e)}")
            return S3OperationResult(
                success=False,
                error_message=f"Failed to delete PDF: {str(e)}"
            )
    
    def _extract_phase_from_filename(self, filename: str) -> str:
        """Extract phase from PDF filename."""
        phases = ['requirements', 'design', 'development', 'testing', 'deployment', 'maintenance']
        filename_lower = filename.lower()
        
        for phase in phases:
            if phase in filename_lower:
                return phase
        
        return 'unknown'