"""
Conversation Storage Service

Handles storing and retrieving conversations for projects with:
- Single session per project
- Persistent conversation history
- S3 storage following existing bucket structure
- Context management for LLM (last 4 + summaries)
"""

import json
import boto3
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from botocore.exceptions import ClientError
import logging
import os

logger = logging.getLogger(__name__)

class ConversationStorage:
    def __init__(self, bucket_name: str = None):
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        self.bucket_name = bucket_name or self._get_bucket_name()
        
    def _get_bucket_name(self) -> str:
        """Get bucket name from environment or settings"""
        import os
        
        # First try environment variable
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if bucket_name:
            return bucket_name
            
        # Try to get from settings
        try:
            from config.settings import settings
            if hasattr(settings, 'S3_BUCKET_NAME') and settings.S3_BUCKET_NAME:
                return settings.S3_BUCKET_NAME
        except Exception as e:
            logger.warning(f"Could not get bucket from settings: {e}")
            
        # Fallback: try to discover icode bucket (only if we have permissions)
        try:
            response = self.s3_client.list_buckets()
            for bucket in response['Buckets']:
                if 'icode-projects-bucket' in bucket['Name']:
                    return bucket['Name']
        except Exception as e:
            logger.warning(f"Could not discover S3 bucket: {e}")
            
        # Final fallback: get from environment variable
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if bucket_name:
            logger.info(f"Using bucket from environment: {bucket_name}")
            return bucket_name
        
        # If no bucket configured, raise error
        raise ValueError("S3_BUCKET_NAME environment variable not set")
    
    def _get_conversation_key(self, project_name: str) -> str:
        """Get S3 key for project conversation file"""
        return f"projects/{project_name}/conversations/conversation.json"
    
    def _get_metadata_key(self, project_name: str) -> str:
        """Get S3 key for project metadata"""
        return f"projects/{project_name}/conversations/metadata.json"
    
    async def store_message(self, project_name: str, role: str, content: str, user_id: str = None) -> Dict[str, Any]:
        """Store a single message in the conversation"""
        message = {
            "id": f"{datetime.utcnow().isoformat()}_{role}",
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,  # "user" or "assistant"
            "content": content,
            "user_id": user_id
        }
        
        try:
            logger.info(f"Starting to store message for project {project_name}: {role}")
            
            # Get existing conversation
            logger.info(f"Getting existing conversation for {project_name}")
            conversation = await self.get_conversation(project_name)
            
            # Add new message
            conversation["messages"].append(message)
            conversation["updated_at"] = datetime.utcnow().isoformat()
            conversation["message_count"] = len(conversation["messages"])
            
            logger.info(f"Updated conversation, now has {conversation['message_count']} messages")
            
            # Store updated conversation
            logger.info(f"Storing updated conversation to S3")
            await self._store_conversation(project_name, conversation)
            
            # Update metadata and trigger summarization asynchronously (fire and forget)
            logger.info(f"Triggering background metadata update and summarization check")
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, self._update_metadata_sync, project_name, conversation["message_count"])
            self._check_and_trigger_summarization(project_name, conversation["message_count"])
            
            logger.info(f"Successfully stored message for project {project_name}: {role}")
            return message
            
        except Exception as e:
            logger.error(f"Error storing message for project {project_name}: {e}", exc_info=True)
            raise
    
    async def get_conversation(self, project_name: str) -> Dict[str, Any]:
        """Get full conversation for a project"""
        conversation_key = self._get_conversation_key(project_name)
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=conversation_key
            )
            conversation = json.loads(response['Body'].read().decode('utf-8'))
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Create new conversation
                conversation = {
                    "project_name": project_name,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "messages": [],
                    "message_count": 0
                }
                await self._store_conversation(project_name, conversation)
            else:
                raise
        
        return conversation
    
    async def get_context_for_llm(self, project_name: str) -> Dict[str, Any]:
        """Get conversation context optimized for LLM"""
        logger.info(f"Getting LLM context for project: {project_name}")
        
        conversation = await self.get_conversation(project_name)
        messages = conversation["messages"]
        message_count = len(messages)
        
        logger.info(f"Found {message_count} messages for project {project_name}")
        
        if message_count <= 10:
            # Return last 7 messages directly for conversations up to 10 messages
            recent_messages = messages[-7:] if message_count > 7 else messages
            logger.info(f"Returning direct context with {len(recent_messages)} recent messages")
            return {
                "type": "direct",
                "messages": recent_messages,
                "summary": None
            }
        
        # Get summary + last 7 messages for larger conversations
        summary = await self._get_or_create_summary(project_name, message_count)
        recent_messages = messages[-7:]  # Last 7 messages
        
        logger.info(f"Returning summarized context with {len(recent_messages)} recent messages and summary: {bool(summary)}")
        if summary:
            logger.info(f"Summary preview: {summary[:200]}...")
            
        return {
            "type": "summarized",
            "messages": recent_messages,
            "summary": summary,
            "total_messages": message_count
        }
    
    async def _store_conversation(self, project_name: str, conversation: Dict[str, Any]):
        """Store conversation to S3"""
        conversation_key = self._get_conversation_key(project_name)
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=conversation_key,
            Body=json.dumps(conversation, indent=2),
            ContentType='application/json'
        )
        
        # Trigger KB ingestion for new conversation content
        try:
            from services.simple_tool_service import SimpleToolService
            import asyncio
            
            tool_service = SimpleToolService()
            # Trigger async KB ingestion - don't wait for completion
            asyncio.create_task(tool_service.trigger_s3_ingestion(project_name, conversation_key))
            logger.info(f"Triggered KB ingestion for conversation: {project_name}")
        except Exception as e:
            logger.warning(f"Failed to trigger KB ingestion for {project_name}: {e}")
    
    async def _update_metadata(self, project_name: str, message_count: int):
        """Update project metadata"""
        metadata_key = self._get_metadata_key(project_name)
        
        metadata = {
            "project_name": project_name,
            "message_count": message_count,
            "last_updated": datetime.utcnow().isoformat(),
            "needs_summary": message_count >= 20 and message_count % 20 == 0
        }
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )
        
        # Trigger KB ingestion for updated metadata
        try:
            from services.simple_tool_service import SimpleToolService
            import asyncio
            
            tool_service = SimpleToolService()
            # Trigger async KB ingestion - don't wait for completion
            asyncio.create_task(tool_service.trigger_s3_ingestion(project_name, metadata_key))
            logger.info(f"Triggered KB ingestion for metadata: {project_name}")
        except Exception as e:
            logger.warning(f"Failed to trigger KB ingestion for metadata {project_name}: {e}")
    
    def _update_metadata_sync(self, project_name: str, message_count: int):
        """Update project metadata synchronously (for background execution)"""
        try:
            metadata_key = self._get_metadata_key(project_name)
            
            metadata = {
                "project_name": project_name,
                "message_count": message_count,
                "last_updated": datetime.utcnow().isoformat(),
                "needs_summary": message_count >= 20 and message_count % 20 == 0
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Background metadata update completed for {project_name}")
        except Exception as e:
            logger.error(f"Error in background metadata update: {e}", exc_info=True)
    
    async def _get_or_create_summary(self, project_name: str, message_count: int) -> Optional[str]:
        """Get existing summary from S3 with timeout"""
        try:
            summary_key = f"projects/{project_name}/conversations/summary.json"
            
            # Add a timeout to prevent hanging
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=summary_key
            )
            
            summary_data = json.loads(response['Body'].read().decode('utf-8'))
            return summary_data.get('summary')
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"No summary found for {project_name}")
                return None
            else:
                logger.error(f"Error getting summary: {e}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error getting summary: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return None
    
    async def get_conversation_history(self, project_name: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get conversation history for display in frontend"""
        conversation = await self.get_conversation(project_name)
        messages = conversation["messages"]
        
        if limit:
            messages = messages[-limit:]
            
        return messages
    
    async def check_summarization_needed(self, project_name: str) -> bool:
        """Check if project needs summarization"""
        try:
            metadata_key = self._get_metadata_key(project_name)
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            metadata = json.loads(response['Body'].read().decode('utf-8'))
            return metadata.get("needs_summary", False)
            
        except ClientError:
            return False
    
    def _check_and_trigger_summarization(self, project_name: str, message_count: int):
        """Check if summarization is needed and trigger Lambda"""
        logger.info(f"Checking summarization trigger for {project_name}: {message_count} messages")
        
        if message_count % 10 == 0 and message_count >= 10:
            try:
                lambda_function_arn = os.getenv('CONVERSATION_SUMMARIZER_LAMBDA_ARN')
                if not lambda_function_arn:
                    logger.warning("CONVERSATION_SUMMARIZER_LAMBDA_ARN not set, skipping summarization")
                    return
                    
                logger.info(f"Triggering summarization Lambda: {lambda_function_arn}")
                
                payload = {
                    'project_name': project_name,
                    'message_count': message_count,
                    's3_bucket': self.bucket_name
                }
                
                # Trigger Lambda asynchronously (fire and forget)
                response = self.lambda_client.invoke(
                    FunctionName=lambda_function_arn,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps(payload)
                )
                
                logger.info(f"Successfully triggered summarization Lambda for {project_name} at {message_count} messages. Response: {response.get('StatusCode')}")
                
            except Exception as e:
                logger.error(f"Error triggering summarization Lambda: {e}", exc_info=True)
                # Don't raise - summarization failure shouldn't break conversation storage
        else:
            logger.info(f"No summarization needed for {project_name} at {message_count} messages")
    
    def get_bucket_info(self) -> Dict[str, str]:
        """Get bucket information for debugging"""
        return {
            "bucket_name": self.bucket_name,
            "conversation_path_example": f"projects/[project-name]/conversations/conversation.json"
        }