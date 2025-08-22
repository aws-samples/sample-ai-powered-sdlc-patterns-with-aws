"""
Jira Routes

API endpoints for managing Jira tickets and epics.
"""

import logging
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.jira_storage_service import JiraStorageService, JiraTicket, Epic

logger = logging.getLogger(__name__)

router = APIRouter()
jira_service = JiraStorageService()

class JiraTicketResponse(BaseModel):
    """Response model for Jira tickets."""
    id: str
    key: str
    url: str
    summary: str
    issue_type: str
    status: str
    created_at: str

class EpicResponse(BaseModel):
    """Response model for epics."""
    title: str
    description: str
    features: List[str]
    created_at: str

class JiraDataResponse(BaseModel):
    """Response model for all Jira data."""
    project_id: str
    tickets: List[JiraTicketResponse]
    epics: List[EpicResponse]
    last_updated: str
    total_tickets: int
    total_epics: int

@router.get("/api/jira/{project_id}/tickets")
async def get_jira_tickets(project_id: str):
    """
    Get all Jira tickets for a project.
    
    Args:
        project_id: The project identifier
        
    Returns:
        List of Jira tickets
    """
    try:
        logger.info(f"Getting Jira tickets for project: {project_id}")
        
        # Get tickets
        tickets = await jira_service.get_tickets(project_id)
        
        # Convert to response format
        ticket_responses = [
            JiraTicketResponse(
                id=ticket.id,
                key=ticket.key,
                url=ticket.url,
                summary=ticket.summary,
                issue_type=ticket.issue_type,
                status=ticket.status,
                created_at=ticket.created_at
            )
            for ticket in tickets
        ]
        
        logger.info(f"Successfully retrieved {len(ticket_responses)} Jira tickets for project: {project_id}")
        return ticket_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Jira tickets for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/jira/{project_id}/epics")
async def get_epics(project_id: str):
    """
    Get all epics for a project.
    
    Args:
        project_id: The project identifier
        
    Returns:
        List of epics
    """
    try:
        logger.info(f"Getting epics for project: {project_id}")
        
        # Get epics
        epics = await jira_service.get_epics(project_id)
        
        # Convert to response format
        epic_responses = [
            EpicResponse(
                title=epic.title,
                description=epic.description,
                features=epic.features,
                created_at=epic.created_at
            )
            for epic in epics
        ]
        
        logger.info(f"Successfully retrieved {len(epic_responses)} epics for project: {project_id}")
        return epic_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting epics for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/jira/{project_id}/all")
async def get_all_jira_data(project_id: str):
    """
    Get all Jira data (tickets and epics) for a project.
    
    Args:
        project_id: The project identifier
        
    Returns:
        Complete Jira data for the project
    """
    try:
        logger.info(f"Getting all Jira data for project: {project_id}")
        
        # Get all Jira data
        jira_data = await jira_service.get_jira_data(project_id)
        
        if not jira_data:
            # Return empty data structure
            return JiraDataResponse(
                project_id=project_id,
                tickets=[],
                epics=[],
                last_updated="",
                total_tickets=0,
                total_epics=0
            )
        
        # Convert to response format
        ticket_responses = [
            JiraTicketResponse(
                id=ticket.id,
                key=ticket.key,
                url=ticket.url,
                summary=ticket.summary,
                issue_type=ticket.issue_type,
                status=ticket.status,
                created_at=ticket.created_at
            )
            for ticket in jira_data.tickets
        ]
        
        epic_responses = [
            EpicResponse(
                title=epic.title,
                description=epic.description,
                features=epic.features,
                created_at=epic.created_at
            )
            for epic in jira_data.epics
        ]
        
        response = JiraDataResponse(
            project_id=jira_data.project_id,
            tickets=ticket_responses,
            epics=epic_responses,
            last_updated=jira_data.last_updated,
            total_tickets=len(ticket_responses),
            total_epics=len(epic_responses)
        )
        
        logger.info(f"Successfully retrieved all Jira data for project: {project_id} ({len(ticket_responses)} tickets, {len(epic_responses)} epics)")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all Jira data for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/jira/{project_id}/metadata")
async def get_jira_metadata(project_id: str):
    """
    Get metadata about Jira data for a project.
    
    Args:
        project_id: The project identifier
        
    Returns:
        Metadata about Jira tickets and epics
    """
    try:
        logger.info(f"Getting Jira metadata for project: {project_id}")
        
        # Get metadata directly
        metadata = await jira_service.get_metadata(project_id)
        
        logger.info(f"Successfully retrieved Jira metadata for project: {project_id}")
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Jira metadata for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")