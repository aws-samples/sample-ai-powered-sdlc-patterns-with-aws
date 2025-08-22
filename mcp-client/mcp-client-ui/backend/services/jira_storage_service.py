"""
Jira Storage Service

Handles storage and retrieval of Jira tickets and epics for projects.
"""

import json
import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from services.s3_storage_service import S3StorageService

logger = logging.getLogger(__name__)

@dataclass
class JiraTicket:
    """Represents a Jira ticket."""
    id: str
    key: str
    url: str
    summary: str
    issue_type: str
    description: str = "No description provided"
    status: str = "Open"
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class Epic:
    """Represents an epic with its details."""
    title: str
    description: str
    features: List[str]
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class Sprint:
    """Represents a sprint with its details."""
    name: str
    goal: str
    duration: str
    tickets: List[str]  # List of ticket keys/IDs
    start_date: str = None
    end_date: str = None
    status: str = "Planning"  # Planning, Active, Completed
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class JiraProjectData:
    """Container for all Jira-related data for a project."""
    project_id: str
    tickets: List[JiraTicket]
    epics: List[Epic]
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

class JiraStorageService:
    """Service for storing and retrieving Jira tickets and epics."""
    
    def __init__(self):
        self.s3_service = S3StorageService()
    
    def _get_jira_key(self, project_id: str) -> str:
        """Get the S3 key for Jira data."""
        return f"projects/{project_id}/jira/jira_data.json"
    
    async def save_jira_tickets(self, project_id: str, tickets: List[Dict[str, Any]]) -> bool:
        """
        Save Jira tickets for a project.
        
        Args:
            project_id: The project identifier
            tickets: List of ticket data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Saving {len(tickets)} Jira tickets for project: {project_id}")
            
            # Convert ticket dictionaries to JiraTicket objects
            jira_tickets = []
            for ticket_data in tickets:
                logger.info(f"Processing ticket data: {ticket_data}")
                # Parse the ticket response (it comes as JSON string)
                if isinstance(ticket_data.get('result'), str):
                    try:
                        parsed_ticket = json.loads(ticket_data['result'])
                        logger.info(f"Parsed ticket from result: {parsed_ticket}")
                        
                        # Convert API URL to user-facing URL
                        api_url = parsed_ticket.get('self', '')
                        ticket_key = parsed_ticket.get('key', '')
                        
                        if ticket_key:
                            # Use environment variable for Jira base URL
                            jira_base_url = os.getenv('JIRA_BASE_URL')
                            if jira_base_url:
                                user_url = f"{jira_base_url}/browse/{ticket_key}"
                            else:
                                logger.warning("JIRA_BASE_URL environment variable not set, using API URL as fallback")
                                user_url = api_url
                        elif api_url:
                            # Fallback to API URL if no ticket key
                            user_url = api_url
                        else:
                            user_url = ''
                        
                        logger.info(f"Converted URL from '{api_url}' to '{user_url}'")
                        
                        jira_ticket = JiraTicket(
                            id=parsed_ticket.get('id', ''),
                            key=parsed_ticket.get('key', ''),
                            url=user_url,
                            summary=ticket_data.get('summary', 'Unknown'),
                            description=ticket_data.get('description', 'No description provided'),
                            issue_type=ticket_data.get('issue_type', 'New Feature')
                        )
                        jira_tickets.append(jira_ticket)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse ticket data: {ticket_data}")
                        continue
            
            # Load existing data or create new
            existing_data = await self.get_jira_data(project_id)
            if existing_data:
                # APPEND tickets instead of replacing, but avoid duplicates
                existing_ticket_ids = {ticket.id for ticket in existing_data.tickets if ticket.id}
                existing_ticket_keys = {ticket.key for ticket in existing_data.tickets if ticket.key}
                
                # Only add new tickets that don't already exist (check both ID and key)
                new_tickets = []
                for ticket in jira_tickets:
                    if ticket.id and ticket.id in existing_ticket_ids:
                        logger.info(f"Ticket with ID {ticket.id} already exists, skipping")
                    elif ticket.key and ticket.key in existing_ticket_keys:
                        logger.info(f"Ticket with key {ticket.key} already exists, skipping")
                    else:
                        new_tickets.append(ticket)
                        logger.info(f"Adding new ticket: {ticket.key} (ID: {ticket.id})")
                
                # Append new tickets to existing ones
                existing_data.tickets.extend(new_tickets)
                existing_data.last_updated = datetime.now().isoformat()
                jira_data = existing_data
                
                logger.info(f"Total tickets after append: {len(existing_data.tickets)} (added {len(new_tickets)} new)")
            else:
                # Create new data structure
                jira_data = JiraProjectData(
                    project_id=project_id,
                    tickets=jira_tickets,
                    epics=[]
                )
            
            # Save to S3 using basic S3 operations
            jira_key = self._get_jira_key(project_id)
            data_json = json.dumps(asdict(jira_data), indent=2, ensure_ascii=False)
            
            # Use the sync method with async executor
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self.s3_service._executor,
                self.s3_service._sync_put_object,
                jira_key,
                data_json.encode('utf-8'),
                "application/json"
            )
            
            if success:
                logger.info(f"✅ Successfully saved Jira tickets to S3: {jira_key}")
                return True
            else:
                logger.error(f"❌ Failed to save Jira tickets to S3: {jira_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving Jira tickets for project {project_id}: {e}")
            return False
    
    async def save_epics(self, project_id: str, epics: List[Dict[str, Any]]) -> bool:
        """
        Save epics for a project.
        
        Args:
            project_id: The project identifier
            epics: List of epic data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Saving {len(epics)} epics for project: {project_id}")
            
            # Convert epic dictionaries to Epic objects
            epic_objects = []
            for epic_data in epics:
                epic = Epic(
                    title=epic_data.get('title', 'Unknown Epic'),
                    description=epic_data.get('description', ''),
                    features=epic_data.get('features', [])
                )
                epic_objects.append(epic)
            
            # Load existing data or create new
            existing_data = await self.get_jira_data(project_id)
            if existing_data:
                # APPEND epics instead of replacing them
                existing_epic_titles = {epic.title for epic in existing_data.epics}
                
                # Only add new epics that don't already exist
                new_epics = []
                for epic in epic_objects:
                    if epic.title not in existing_epic_titles:
                        new_epics.append(epic)
                        logger.info(f"Adding new epic: {epic.title}")
                    else:
                        logger.info(f"Epic already exists, skipping: {epic.title}")
                
                # Append new epics to existing ones
                existing_data.epics.extend(new_epics)
                existing_data.last_updated = datetime.now().isoformat()
                jira_data = existing_data
                
                logger.info(f"Total epics after append: {len(existing_data.epics)} (added {len(new_epics)} new)")
            else:
                # Create new data structure
                jira_data = JiraProjectData(
                    project_id=project_id,
                    tickets=[],
                    epics=epic_objects
                )
            
            # Save to S3 using basic S3 operations
            jira_key = self._get_jira_key(project_id)
            data_json = json.dumps(asdict(jira_data), indent=2, ensure_ascii=False)
            
            # Use the sync method with async executor
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self.s3_service._executor,
                self.s3_service._sync_put_object,
                jira_key,
                data_json.encode('utf-8'),
                "application/json"
            )
            
            if success:
                logger.info(f"✅ Successfully saved epics to S3: {jira_key}")
                return True
            else:
                logger.error(f"❌ Failed to save epics to S3: {jira_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving epics for project {project_id}: {e}")
            return False
    
    async def get_jira_data(self, project_id: str) -> Optional[JiraProjectData]:
        """
        Get all Jira data for a project.
        
        Args:
            project_id: The project identifier
            
        Returns:
            JiraProjectData or None if not found
        """
        try:
            jira_key = self._get_jira_key(project_id)
            
            # Try to load from S3 using basic S3 operations
            loop = asyncio.get_event_loop()
            file_content = await loop.run_in_executor(
                self.s3_service._executor,
                self.s3_service._sync_get_object,
                jira_key
            )
            
            if not file_content:
                logger.info(f"No Jira data found for project: {project_id}")
                return None
            
            # Parse JSON
            data_dict = json.loads(file_content.decode('utf-8'))
            
            # Convert back to dataclass
            tickets = [JiraTicket(**ticket) for ticket in data_dict.get('tickets', [])]
            epics = [Epic(**epic) for epic in data_dict.get('epics', [])]
            
            jira_data = JiraProjectData(
                project_id=data_dict['project_id'],
                tickets=tickets,
                epics=epics,
                last_updated=data_dict.get('last_updated')
            )
            
            logger.info(f"Successfully loaded Jira data for project: {project_id} ({len(tickets)} tickets, {len(epics)} epics)")
            return jira_data
            
        except Exception as e:
            logger.error(f"Error loading Jira data for project {project_id}: {e}")
            return None
    
    async def get_tickets(self, project_id: str) -> List[JiraTicket]:
        """Get just the tickets for a project."""
        jira_data = await self.get_jira_data(project_id)
        return jira_data.tickets if jira_data else []
    
    async def get_epics(self, project_id: str) -> List[Epic]:
        """Get just the epics for a project."""
        jira_data = await self.get_jira_data(project_id)
        return jira_data.epics if jira_data else []
    
    async def get_metadata(self, project_id: str) -> Dict[str, Any]:
        """Get metadata about Jira data for a project."""
        jira_data = await self.get_jira_data(project_id)
        if not jira_data:
            return {
                'has_tickets': False,
                'has_epics': False,
                'total_tickets': 0,
                'total_epics': 0
            }
        
        return {
            'has_tickets': len(jira_data.tickets) > 0,
            'has_epics': len(jira_data.epics) > 0,
            'total_tickets': len(jira_data.tickets),
            'total_epics': len(jira_data.epics),
            'last_updated': jira_data.last_updated
        }