"""
Design MCP Integration Service

Handles conversation-to-diagram generation using MCP servers for the design phase.
Provides automatic diagram generation, conversation context preparation, and error handling
with fallback when MCP diagram tools are unavailable.
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, field_validator

from mcp_client.client import MCPClient
from mcp_client.core.models import MCPRequest, MCPResponse, MCPError, ErrorCode
from services.mcp_discovery import MCPServerDiscovery, ServerAvailabilityStatus
from services.architecture_code_generator import ArchitectureCodeGenerator
from services.architecture_code_models import CodeType, TargetPlatform


class DiagramGenerationRequest(BaseModel):
    """Request model for diagram generation"""
    conversation_history: List[Dict[str, Any]]
    diagram_type: str = "architecture"  # architecture, sequence, flowchart, component
    title: Optional[str] = None
    description: Optional[str] = None
    format: str = "png"  # png, svg
    
    @field_validator('diagram_type')
    @classmethod
    def validate_diagram_type(cls, v):
        allowed_types = ['architecture', 'sequence', 'flowchart', 'component', 'class', 'entity_relationship']
        if v not in allowed_types:
            raise ValueError(f'Diagram type must be one of: {", ".join(allowed_types)}')
        return v
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        allowed_formats = ['png', 'svg']
        if v not in allowed_formats:
            raise ValueError(f'Format must be one of: {", ".join(allowed_formats)}')
        return v


class DiagramGenerationResponse(BaseModel):
    """Response model for diagram generation"""
    success: bool
    diagram_url: Optional[str] = None
    diagram_data: Optional[bytes] = None
    diagram_type: str
    format: str
    title: str
    description: Optional[str] = None
    error_message: Optional[str] = None
    used_mcp: bool = False
    fallback_used: bool = False
    metadata: Dict[str, Any] = {}


class DesignMCPIntegration:
    """
    Design MCP Integration class for conversation-to-diagram generation
    
    Handles:
    - Conversation context preparation for MCP diagram tools
    - Sending conversation history to MCP tools and receiving generated PDFs
    - Automatic diagram generation triggers
    - Error handling and fallback when MCP tools are unavailable
    """
    
    def __init__(self, mcp_client: Optional[MCPClient] = None, mcp_discovery: Optional[MCPServerDiscovery] = None):
        """
        Initialize the Design MCP Integration service
        
        Args:
            mcp_client: Optional MCP client instance
            mcp_discovery: Optional MCP discovery service instance
        """
        self.mcp_client = mcp_client
        self.mcp_discovery = mcp_discovery or (MCPServerDiscovery(mcp_client) if mcp_client else None)
        self.logger = logging.getLogger(__name__)
        
        # Initialize architecture code generator
        self.code_generator = ArchitectureCodeGenerator(mcp_client, mcp_discovery)
        
        # Diagram generation capabilities required from MCP servers
        self.diagram_capabilities = [
            "create_architecture_diagram",
            "analyze_architecture",
            "generate_architecture_code",
            "query_aws_knowledge"
        ]
        
        # Conversation analysis patterns for diagram triggers
        self.diagram_trigger_patterns = {
            'architecture': [
                r'architecture', r'system design', r'components?', r'modules?',
                r'services?', r'layers?', r'tiers?', r'infrastructure'
            ],
            'sequence': [
                r'flow', r'sequence', r'process', r'workflow', r'steps?',
                r'interactions?', r'communications?'
            ],
            'flowchart': [
                r'flowchart', r'decision', r'branch', r'logic', r'algorithm',
                r'process flow', r'workflow'
            ],
            'component': [
                r'component', r'interface', r'api', r'connection', r'relationship',
                r'dependency', r'integration'
            ]
        }
        
        self.logger.debug("Initialized Design MCP Integration service")
    
    async def should_generate_diagram(
        self, 
        conversation_history: List[Dict[str, Any]], 
        min_messages: int = 1
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determine if a diagram should be automatically generated from conversation
        
        Args:
            conversation_history: List of conversation messages
            min_messages: Minimum number of messages required
            
        Returns:
            Tuple of (should_generate, diagram_type, analysis)
        """
        if len(conversation_history) < min_messages:
            return False, "", {"reason": "insufficient_messages"}
        
        # Extract conversation text
        conversation_text = self._extract_conversation_text(conversation_history)
        text_lower = conversation_text.lower()
        
        analysis = {
            "message_count": len(conversation_history),
            "text_length": len(conversation_text),
            "diagram_mentions": {},
            "trigger_scores": {},
            "explicit_requests": [],
            "design_complexity": 0
        }
        
        # Check for explicit diagram requests
        explicit_patterns = [
            r'generate.*diagram', r'create.*diagram', r'draw.*diagram',
            r'show.*diagram', r'diagram.*please', r'visual.*representation',
            r'can you.*diagram', r'need.*diagram'
        ]
        
        for pattern in explicit_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                analysis["explicit_requests"].extend(matches)
        
        if analysis["explicit_requests"]:
            # User explicitly requested a diagram
            suggested_type = self._determine_diagram_type(conversation_text)
            return True, suggested_type, analysis
        
        # Analyze conversation for diagram trigger patterns
        for diagram_type, patterns in self.diagram_trigger_patterns.items():
            score = 0
            mentions = []
            
            for pattern in patterns:
                # Use word boundaries for better matching
                pattern_with_boundaries = r'\b' + pattern + r'\b'
                matches = re.findall(pattern_with_boundaries, text_lower)
                if matches:
                    score += len(matches)
                    mentions.extend(matches)
            
            analysis["diagram_mentions"][diagram_type] = mentions
            analysis["trigger_scores"][diagram_type] = score
        
        # Calculate design complexity score
        complexity_indicators = [
            'database', 'api', 'service', 'component', 'module', 'layer',
            'interface', 'integration', 'authentication', 'authorization',
            'microservice', 'frontend', 'backend', 'client', 'server'
        ]
        
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in text_lower)
        analysis["design_complexity"] = complexity_score
        
        # Determine if diagram should be generated
        max_score = max(analysis["trigger_scores"].values()) if analysis["trigger_scores"] else 0
        best_type = max(analysis["trigger_scores"], key=analysis["trigger_scores"].get) if analysis["trigger_scores"] else "architecture"
        
        # Trigger conditions (made more sensitive):
        # 1. High trigger score (2+ mentions of diagram-related terms)
        # 2. Medium complexity score (3+ design elements) + some trigger score
        # 3. Recent messages contain design discussions
        # 4. Any explicit architecture/design mention
        should_generate = (
            max_score >= 2 or
            (complexity_score >= 3 and max_score >= 1) or
            self._has_recent_design_discussion(conversation_history) or
            any(keyword in text_lower for keyword in ['architecture', 'design', 'system', 'application'])
        )
        
        return should_generate, best_type, analysis
    
    def _extract_conversation_text(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Extract and format conversation text for analysis"""
        conversation_parts = []
        
        for message in conversation_history:
            user_msg = message.get('user_message', '').strip()
            ai_msg = message.get('ai_response', '').strip()
            
            if user_msg:
                conversation_parts.append(user_msg)
            if ai_msg:
                conversation_parts.append(ai_msg)
        
        return " ".join(conversation_parts)
    
    def _determine_diagram_type(self, conversation_text: str) -> str:
        """Determine the most appropriate diagram type from conversation content"""
        text_lower = conversation_text.lower()
        
        # Score each diagram type based on content
        type_scores = {}
        for diagram_type, patterns in self.diagram_trigger_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            type_scores[diagram_type] = score
        
        # Return the type with highest score, default to architecture
        if type_scores:
            return max(type_scores, key=type_scores.get)
        return "architecture"
    
    def _has_recent_design_discussion(self, conversation_history: List[Dict[str, Any]]) -> bool:
        """Check if recent messages contain design-related discussions"""
        if len(conversation_history) < 2:
            return False
        
        # Check last 2 messages for design content
        recent_messages = conversation_history[-2:]
        recent_text = ""
        
        for message in recent_messages:
            recent_text += f" {message.get('user_message', '')} {message.get('ai_response', '')}"
        
        recent_text = recent_text.lower()
        
        design_keywords = [
            'design', 'architecture', 'structure', 'component', 'system',
            'interface', 'api', 'database', 'service', 'module'
        ]
        
        keyword_count = sum(1 for keyword in design_keywords if keyword in recent_text)
        return keyword_count >= 3
    
    async def generate_diagram_from_conversation(
        self, 
        conversation_history: List[Dict[str, Any]],
        diagram_type: str = "architecture",
        title: Optional[str] = None,
        force_generation: bool = False
    ) -> DiagramGenerationResponse:
        """
        Generate diagram from conversation context using MCP tools
        
        Args:
            conversation_history: List of conversation messages
            diagram_type: Type of diagram to generate
            title: Optional title for the diagram
            force_generation: Force generation even if conditions not met
            
        Returns:
            DiagramGenerationResponse with diagram data or error information
        """
        try:
            # Check if diagram generation should proceed
            if not force_generation:
                should_generate, suggested_type, analysis = await self.should_generate_diagram(conversation_history)
                if not should_generate:
                    return DiagramGenerationResponse(
                        success=False,
                        diagram_type=diagram_type,
                        format="png",
                        title=title or "Design Diagram",
                        error_message="Insufficient design information for diagram generation",
                        metadata={"analysis": analysis}
                    )
                
                # Use suggested type if not explicitly specified
                if diagram_type == "architecture" and suggested_type != "architecture":
                    diagram_type = suggested_type
            
            # Prepare conversation context for MCP tool
            context = self.prepare_conversation_context(conversation_history, diagram_type)
            
            # Check MCP availability
            if self.mcp_discovery:
                mcp_available = await self.mcp_discovery.is_mcp_available_for_capabilities_async(
                    self.diagram_capabilities
                )
            else:
                mcp_available = self.mcp_client is not None
            
            if mcp_available and self.mcp_client:
                # Try MCP diagram generation
                try:
                    mcp_response = await self._generate_diagram_via_mcp(context, diagram_type, title)
                    if mcp_response.success:
                        return mcp_response
                    else:
                        self.logger.warning(f"MCP diagram generation failed: {mcp_response.error_message}")
                except Exception as e:
                    self.logger.error(f"Error in MCP diagram generation: {e}")
            
            # Fallback to text-based specification
            return await self._generate_fallback_diagram_spec(context, diagram_type, title)
            
        except Exception as e:
            self.logger.error(f"Error in diagram generation: {e}")
            return DiagramGenerationResponse(
                success=False,
                diagram_type=diagram_type,
                format="png",
                title=title or "Design Diagram",
                error_message=f"Diagram generation failed: {str(e)}"
            )
    
    def prepare_conversation_context(
        self, 
        conversation_history: List[Dict[str, Any]], 
        diagram_type: str
    ) -> Dict[str, Any]:
        """
        Format conversation context for MCP diagram tool consumption
        
        Args:
            conversation_history: List of conversation messages
            diagram_type: Type of diagram to generate
            
        Returns:
            Formatted context dictionary for MCP tool
        """
        # Extract key information from conversation
        conversation_text = self._extract_conversation_text(conversation_history)
        
        # Extract design elements based on diagram type
        design_elements = self._extract_design_elements(conversation_text, diagram_type)
        
        # Create structured context
        context = {
            "diagram_type": diagram_type,
            "conversation_summary": self._summarize_conversation(conversation_history),
            "design_elements": design_elements,
            "raw_conversation": conversation_text,
            "metadata": {
                "message_count": len(conversation_history),
                "timestamp": datetime.now().isoformat(),
                "extraction_method": "automated"
            }
        }
        
        return context
    
    def _extract_design_elements(self, conversation_text: str, diagram_type: str) -> Dict[str, List[str]]:
        """Extract design elements relevant to the diagram type"""
        text_lower = conversation_text.lower()
        elements = {
            "components": [],
            "relationships": [],
            "data_flows": [],
            "interfaces": [],
            "technologies": []
        }
        
        if diagram_type == "architecture":
            # Extract architectural components
            component_patterns = [
                r'(\w+)\s+service',
                r'(\w+)\s+component',
                r'(\w+)\s+module',
                r'(\w+)\s+layer',
                r'(\w+)\s+api',
                r'(\w+)\s+database',
                r'service\s+(\w+)',
                r'component\s+(\w+)',
                r'module\s+(\w+)'
            ]
            
            for pattern in component_patterns:
                matches = re.findall(pattern, text_lower)
                elements["components"].extend([match for match in matches if len(match) > 2])
            
            # Also look for explicit service mentions
            service_mentions = re.findall(r'(\w+)\s+service', text_lower)
            elements["components"].extend([match for match in service_mentions if len(match) > 2])
        
        elif diagram_type == "sequence":
            # Extract sequence/flow elements
            flow_patterns = [
                r'(\w+)\s+(?:calls|sends|requests)',
                r'(?:from|to)\s+(\w+)',
                r'(\w+)\s+(?:responds|returns)',
                r'step\s+\d+[:\s]+(\w+)'
            ]
            
            for pattern in flow_patterns:
                matches = re.findall(pattern, text_lower)
                elements["data_flows"].extend([match for match in matches if len(match) > 2])
        
        # Extract relationships
        relationship_patterns = [
            r'(\w+)\s+(?:connects to|integrates with|depends on)\s+(\w+)',
            r'(\w+)\s+(?:uses|calls|accesses)\s+(\w+)',
            r'(\w+)\s+and\s+(\w+)\s+(?:communicate|interact)'
        ]
        
        for pattern in relationship_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    elements["relationships"].append(f"{match[0]} -> {match[1]}")
        
        # Extract technologies
        tech_keywords = [
            'react', 'angular', 'vue', 'node', 'python', 'java', 'spring',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'mysql', 'postgresql',
            'mongodb', 'redis', 'nginx', 'apache', 'rest', 'graphql', 'grpc'
        ]
        
        for tech in tech_keywords:
            if tech in text_lower:
                elements["technologies"].append(tech)
        
        # Clean up and deduplicate
        for key in elements:
            elements[key] = list(set([item for item in elements[key] if item and len(str(item).strip()) > 1]))
        
        return elements
    
    def _summarize_conversation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Create a concise summary of the conversation for diagram context"""
        if not conversation_history:
            return "System architecture design"
        
        # Get the most recent user message as the primary context
        latest_message = conversation_history[-1] if conversation_history else {}
        user_msg = latest_message.get('user_message', '').strip()
        
        if user_msg:
            # Use just the user's request, keep it under 500 chars to be safe
            if len(user_msg) <= 500:
                return user_msg
            else:
                # Take first sentence or first 500 chars, whichever is shorter
                first_sentence = user_msg.split('.')[0].strip()
                if len(first_sentence) <= 500:
                    return first_sentence
                else:
                    return user_msg[:497] + "..."
        
        return "System architecture design"
    
    async def _generate_diagram_via_mcp(
        self, 
        context: Dict[str, Any], 
        diagram_type: str, 
        title: Optional[str]
    ) -> DiagramGenerationResponse:
        """
        Generate diagram using MCP diagram tool
        
        Args:
            context: Prepared conversation context
            diagram_type: Type of diagram to generate
            title: Optional diagram title
            
        Returns:
            DiagramGenerationResponse with MCP-generated diagram
        """
        try:
            # Create MCP request for diagram generation
            mcp_request = MCPRequest(
                request_type="tools/call",
                content={
                    "name": "create_architecture_diagram",
                    "arguments": {
                        "architecture_description": context.get("conversation_summary", "System architecture design"),
                        "diagram_type": diagram_type,
                        "title": title or f"{diagram_type.title()} Diagram",
                        "components": context.get("design_elements", {}).get("components", []),
                        "relationships": context.get("design_elements", {}).get("relationships", []),
                        "technologies": context.get("design_elements", {}).get("technologies", [])
                    }
                },
                required_capabilities=self.diagram_capabilities
            )
            
            # Send request via MCP discovery with fallback
            if self.mcp_discovery:
                response, used_mcp = await self.mcp_discovery.send_request_with_fallback(
                    mcp_request,
                    fallback_handler=None  # No fallback handler for this call
                )
            else:
                response = await self.mcp_client.send_request(mcp_request)
                used_mcp = True
            
            if not response or not used_mcp:
                raise MCPError(
                    error_code=ErrorCode.SERVER_ERROR,
                    message="No response from MCP diagram service"
                )
            
            # Process MCP response
            content = response.content
            
            # Check for direct diagram_url field
            if "diagram_url" in content:
                return DiagramGenerationResponse(
                    success=True,
                    diagram_url=content["diagram_url"],
                    diagram_type=diagram_type,
                    format="png",
                    title=title or f"{diagram_type.title()} Diagram",
                    description=content.get("description"),
                    used_mcp=True,
                    metadata={
                        "mcp_server_id": getattr(response, 'server_id', 'unknown'),
                        "generation_time": content.get("generation_time"),
                        "diagram_elements": content.get("elements_count", 0)
                    }
                )
            # Check for diagram_data field
            elif "diagram_data" in content:
                return DiagramGenerationResponse(
                    success=True,
                    diagram_data=content["diagram_data"],
                    diagram_type=diagram_type,
                    format="png",
                    title=title or f"{diagram_type.title()} Diagram",
                    description=content.get("description"),
                    used_mcp=True,
                    metadata={
                        "mcp_server_id": getattr(response, 'server_id', 'unknown'),
                        "generation_time": content.get("generation_time"),
                        "diagram_elements": content.get("elements_count", 0)
                    }
                )
            # Check for content array with image items (AWS MCP server format)
            elif "content" in content and isinstance(content["content"], list):
                for item in content["content"]:
                    if isinstance(item, dict) and item.get("type") == "image" and "data" in item:
                        image_url = item["data"]
                        if image_url and image_url.startswith("http"):
                            return DiagramGenerationResponse(
                                success=True,
                                diagram_url=image_url,
                                diagram_type=diagram_type,
                                format="png",  # AWS server returns PNG images
                                title=title or f"{diagram_type.title()} Diagram",
                                description=content.get("description", "Generated architecture diagram"),
                                used_mcp=True,
                                metadata={
                                    "mcp_server_id": getattr(response, 'server_id', 'unknown'),
                                    "generation_time": content.get("generation_time"),
                                    "diagram_elements": content.get("elements_count", 0),
                                    "aws_s3_url": True
                                }
                            )
            # Check for direct content array (alternative format)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image" and "data" in item:
                        image_url = item["data"]
                        if image_url and image_url.startswith("http"):
                            return DiagramGenerationResponse(
                                success=True,
                                diagram_url=image_url,
                                diagram_type=diagram_type,
                                format="png",
                                title=title or f"{diagram_type.title()} Diagram",
                                description="Generated architecture diagram",
                                used_mcp=True,
                                metadata={
                                    "mcp_server_id": getattr(response, 'server_id', 'unknown'),
                                    "aws_s3_url": True
                                }
                            )
            
            # If no diagram found in expected formats
            self.logger.warning(f"MCP response structure: {content}")
            raise ValueError("MCP response does not contain diagram URL or data in expected format")
                
        except Exception as e:
            self.logger.error(f"MCP diagram generation failed: {e}")
            return DiagramGenerationResponse(
                success=False,
                diagram_type=diagram_type,
                format="png",
                title=title or f"{diagram_type.title()} Diagram",
                error_message=f"MCP diagram generation failed: {str(e)}",
                used_mcp=False
            )
    
    async def _generate_fallback_diagram_spec(
        self, 
        context: Dict[str, Any], 
        diagram_type: str, 
        title: Optional[str]
    ) -> DiagramGenerationResponse:
        """
        Generate fallback text-based diagram specification when MCP is unavailable
        
        Args:
            context: Prepared conversation context
            diagram_type: Type of diagram to generate
            title: Optional diagram title
            
        Returns:
            DiagramGenerationResponse with text-based specification
        """
        try:
            # Create text-based diagram specification
            spec_content = self._create_text_diagram_spec(context, diagram_type)
            
            return DiagramGenerationResponse(
                success=True,
                diagram_type=diagram_type,
                format="text",
                title=title or f"{diagram_type.title()} Specification",
                description="Text-based diagram specification (MCP diagram service unavailable)",
                fallback_used=True,
                metadata={
                    "fallback_reason": "MCP diagram service unavailable",
                    "spec_content": spec_content,
                    "elements_identified": len(context.get("design_elements", {}).get("components", []))
                }
            )
            
        except Exception as e:
            self.logger.error(f"Fallback diagram specification generation failed: {e}")
            return DiagramGenerationResponse(
                success=False,
                diagram_type=diagram_type,
                format="text",
                title=title or f"{diagram_type.title()} Specification",
                error_message=f"Fallback diagram generation failed: {str(e)}",
                fallback_used=True
            )
    
    def _create_text_diagram_spec(self, context: Dict[str, Any], diagram_type: str) -> str:
        """Create a text-based diagram specification"""
        design_elements = context.get("design_elements", {})
        
        spec_lines = [
            f"# {diagram_type.title()} Diagram Specification",
            "",
            "## Overview",
            context.get("conversation_summary", "Design discussion summary not available"),
            "",
            "## Components"
        ]
        
        components = design_elements.get("components", [])
        if components:
            for i, component in enumerate(components[:10], 1):  # Limit to 10 components
                spec_lines.append(f"{i}. {component.title()}")
        else:
            spec_lines.append("- No specific components identified")
        
        spec_lines.extend([
            "",
            "## Relationships"
        ])
        
        relationships = design_elements.get("relationships", [])
        if relationships:
            for relationship in relationships[:8]:  # Limit to 8 relationships
                spec_lines.append(f"- {relationship}")
        else:
            spec_lines.append("- No specific relationships identified")
        
        if design_elements.get("technologies"):
            spec_lines.extend([
                "",
                "## Technologies",
                "- " + ", ".join(design_elements["technologies"][:10])
            ])
        
        spec_lines.extend([
            "",
            "## Notes",
            "This is a text-based specification generated when visual diagram tools are unavailable.",
            "For visual diagrams, ensure MCP diagram services are properly configured and available."
        ])
        
        return "\n".join(spec_lines)
    
    async def integrate_with_specification_generation(
        self, 
        conversation_history: List[Dict[str, Any]], 
        specification_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Integrate diagram generation into design phase specification generation
        
        Args:
            conversation_history: List of conversation messages
            specification_content: Existing specification content
            
        Returns:
            Enhanced specification content with diagram information
        """
        try:
            # Check if diagram should be generated
            should_generate, diagram_type, analysis = await self.should_generate_diagram(conversation_history)
            
            if should_generate:
                self.logger.info(f"Generating {diagram_type} diagram for design specification")
                
                # Generate diagram
                diagram_response = await self.generate_diagram_from_conversation(
                    conversation_history,
                    diagram_type=diagram_type,
                    title="Design Architecture Diagram"
                )
                
                # Add diagram information to specification
                if diagram_response.success:
                    specification_content["diagram"] = {
                        "type": diagram_response.diagram_type,
                        "title": diagram_response.title,
                        "url": diagram_response.diagram_url,
                        "description": diagram_response.description,
                        "format": diagram_response.format,
                        "generated_via_mcp": diagram_response.used_mcp,
                        "fallback_used": diagram_response.fallback_used,
                        "metadata": diagram_response.metadata
                    }
                    
                    self.logger.info(f"Successfully integrated {diagram_type} diagram into specification")
                else:
                    specification_content["diagram_error"] = {
                        "attempted": True,
                        "error_message": diagram_response.error_message,
                        "diagram_type": diagram_response.diagram_type
                    }
                    
                    self.logger.warning(f"Failed to generate diagram: {diagram_response.error_message}")
            else:
                specification_content["diagram_analysis"] = {
                    "should_generate": False,
                    "reason": analysis.get("reason", "Insufficient design information"),
                    "analysis": analysis
                }
            
            return specification_content
            
        except Exception as e:
            self.logger.error(f"Error integrating diagram generation: {e}")
            specification_content["diagram_error"] = {
                "attempted": True,
                "error_message": f"Integration error: {str(e)}",
                "diagram_type": "unknown"
            }
            return specification_content
    
    async def generate_diagram_with_code(
        self,
        conversation_history: List[Dict[str, Any]],
        diagram_type: str = "architecture",
        title: Optional[str] = None,
        code_type: CodeType = CodeType.CLOUDFORMATION,
        target_platform: TargetPlatform = TargetPlatform.AWS,
        project_name: Optional[str] = None,
        force_generation: bool = False
    ) -> Tuple[DiagramGenerationResponse, Optional[Any]]:
        """
        Combined workflow for generating both diagram and corresponding architecture code.
        
        This method orchestrates the complete workflow from conversation to both
        visual diagram and implementable code artifacts.
        
        Args:
            conversation_history: List of conversation messages
            diagram_type: Type of diagram to generate
            title: Optional title for the diagram
            code_type: Type of code to generate (CloudFormation, Terraform, etc.)
            target_platform: Target platform for deployment
            project_name: Optional project name for generated code
            force_generation: Force generation even if conditions not met
            
        Returns:
            Tuple of (DiagramGenerationResponse, CodeGenerationResponse or None)
        """
        try:
            self.logger.info(f"Starting combined diagram and code generation workflow for project: {project_name}")
            
            # Step 1: Generate diagram using existing workflow
            diagram_response = await self.generate_diagram_from_conversation(
                conversation_history=conversation_history,
                diagram_type=diagram_type,
                title=title,
                force_generation=force_generation
            )
            
            # Step 2: If diagram generation was successful, trigger code generation
            code_response = None
            if diagram_response.success:
                self.logger.info("Diagram generated successfully, triggering code generation")
                
                # Prepare context for code generation
                context = self.prepare_conversation_context(conversation_history, diagram_type)
                
                # Trigger code generation as post-diagram hook
                code_response = await self.trigger_code_generation(
                    diagram_response=diagram_response.__dict__,
                    context=context,
                    code_type=code_type,
                    target_platform=target_platform,
                    project_name=project_name
                )
                
                if code_response and code_response.success:
                    self.logger.info(f"Code generation completed successfully with {len(code_response.generated_files)} files")
                else:
                    self.logger.warning(f"Code generation failed: {code_response.error_message if code_response else 'Unknown error'}")
            else:
                self.logger.warning(f"Diagram generation failed, skipping code generation: {diagram_response.error_message}")
            
            return diagram_response, code_response
            
        except Exception as e:
            self.logger.error(f"Combined workflow failed: {e}")
            # Return diagram response even if code generation fails
            return diagram_response if 'diagram_response' in locals() else DiagramGenerationResponse(
                success=False,
                diagram_type=diagram_type,
                format="png",
                title=title or "Design Diagram",
                error_message=f"Combined workflow failed: {str(e)}"
            ), None
    
    async def trigger_code_generation(
        self,
        diagram_response: Dict[str, Any],
        context: Dict[str, Any],
        code_type: CodeType = CodeType.CLOUDFORMATION,
        target_platform: TargetPlatform = TargetPlatform.AWS,
        project_name: Optional[str] = None
    ) -> Optional[Any]:
        """
        Post-diagram hook that triggers architecture code generation.
        
        This method is called automatically after successful diagram generation
        to create corresponding implementation artifacts.
        
        Args:
            diagram_response: Response from diagram generation
            context: Conversation context and design elements
            code_type: Type of code to generate
            target_platform: Target platform for deployment
            project_name: Optional project name for generated code
            
        Returns:
            CodeGenerationResponse or None if generation fails/skipped
        """
        try:
            self.logger.info("Triggering code generation as post-diagram hook")
            
            # Validate prerequisites before attempting code generation
            if not self.validate_code_generation_prerequisites(diagram_response, context):
                self.logger.info("Code generation prerequisites not met, skipping code generation")
                return None
            
            # Generate project name if not provided
            if not project_name:
                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                diagram_type = diagram_response.get('diagram_type', 'architecture')
                project_name = f"{diagram_type}-{timestamp}"
            
            # Use the architecture code generator to create code
            code_response = await self.code_generator.generate_code_from_diagram(
                diagram_response=diagram_response,
                context=context,
                code_type=code_type,
                target_platform=target_platform,
                project_name=project_name
            )
            
            if code_response.success:
                self.logger.info(f"Code generation triggered successfully for project: {project_name}")
                return code_response
            else:
                self.logger.warning(f"Code generation failed: {code_response.error_message}")
                return code_response
                
        except Exception as e:
            self.logger.error(f"Failed to trigger code generation: {e}")
            return None
    
    def validate_code_generation_prerequisites(
        self,
        diagram_response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Pre-generation checks to validate if code generation should proceed.
        
        Validates that we have sufficient information and successful diagram
        generation to proceed with architecture code generation.
        
        Args:
            diagram_response: Response from diagram generation
            context: Conversation context and design elements
            
        Returns:
            bool: True if code generation should proceed, False otherwise
        """
        try:
            # Check if diagram generation was successful
            if not diagram_response.get('success', False):
                self.logger.info("Code generation skipped: diagram generation was not successful")
                return False
            
            # Check if we have a diagram URL or data
            has_diagram_output = (
                diagram_response.get('diagram_url') or 
                diagram_response.get('diagram_data') or
                diagram_response.get('used_mcp', False)
            )
            
            if not has_diagram_output:
                self.logger.info("Code generation skipped: no diagram output available")
                return False
            
            # Check if we have meaningful architecture description
            architecture_description = (
                diagram_response.get('description') or
                context.get('conversation_summary') or
                ""
            )
            
            if len(architecture_description.strip()) < 10:
                self.logger.info("Code generation skipped: insufficient architecture description")
                return False
            
            # Check if we have design elements or components
            has_design_elements = (
                context.get('design_elements', {}).get('components') or
                context.get('design_elements', {}).get('technologies') or
                diagram_response.get('metadata', {}).get('design_elements')
            )
            
            # For architecture diagrams, we should have some design elements
            diagram_type = diagram_response.get('diagram_type', 'architecture')
            if diagram_type == 'architecture' and not has_design_elements:
                self.logger.info("Code generation skipped: no design elements identified for architecture diagram")
                return False
            
            # Check if MCP was used for diagram generation (indicates higher quality)
            used_mcp = diagram_response.get('used_mcp', False)
            fallback_used = diagram_response.get('fallback_used', False)
            
            # If fallback was used, we might still proceed but with lower confidence
            if fallback_used and not used_mcp:
                self.logger.info("Code generation proceeding with caution: diagram was generated using fallback")
            
            self.logger.info("Code generation prerequisites validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating code generation prerequisites: {e}")
            return False