"""Claude AI service for handling AI responses."""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config.settings import settings


class ClaudeService:
    """Service for interacting with Claude via AWS Bedrock."""
    
    def __init__(self):
        """Initialize the Claude service."""
        self.logger = logging.getLogger(__name__)
        self._bedrock_client = None
        self._is_initialized = False
        self._initialization_error = None
    
    async def initialize(self) -> bool:
        """Initialize the AWS Bedrock client."""
        if self._is_initialized:
            return self._initialization_error is None
        
        try:
            # Create Bedrock client with default/local AWS credentials
            self._bedrock_client = boto3.client(
                'bedrock-runtime', 
                region_name=settings.AWS_REGION
            )
            
            # Test the connection
            sts_client = boto3.client('sts', region_name=settings.AWS_REGION)
            identity = sts_client.get_caller_identity()
            
            self._is_initialized = True
            self._initialization_error = None
            self.logger.info("Claude service initialized successfully")
            return True
            
        except Exception as e:
            self._initialization_error = str(e)
            self._is_initialized = True
            self.logger.error(f"Failed to initialize Claude service: {e}")
            return False
    
    async def get_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Get response from Claude."""
        if not await self.initialize():
            raise Exception(f"Claude service not initialized: {self._initialization_error}")
        
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "system": system_prompt,
                "messages": messages
            }
            
            response = self._bedrock_client.invoke_model(
                modelId=settings.CLAUDE_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            self.logger.error(f"Error calling Claude: {e}")
            raise Exception(f"Error calling Claude: {str(e)}")

    async def get_streaming_response(self, messages: List[Dict[str, str]], system_prompt: str):
        """Get streaming response from Claude."""
        if not await self.initialize():
            raise Exception(f"Claude service not initialized: {self._initialization_error}")
        
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "system": system_prompt,
                "messages": messages
            }
            
            response = self._bedrock_client.invoke_model_with_response_stream(
                modelId=settings.CLAUDE_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            # Process streaming response
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                if chunk['type'] == 'content_block_delta':
                    if 'delta' in chunk and 'text' in chunk['delta']:
                        yield chunk['delta']['text']
                elif chunk['type'] == 'message_stop':
                    break
                    
        except Exception as e:
            self.logger.error(f"Error calling Claude streaming: {e}")
            raise Exception(f"Error calling Claude streaming: {str(e)}")
    
    def build_system_prompt(self, available_tools: Optional[Dict[str, Any]] = None) -> str:
        """Build system prompt with available tools."""
        base_prompt = """You are Claude, an AI assistant with access to various tools and services through MCP (Model Context Protocol) servers.
You can help users with a wide variety of tasks.

IMPORTANT - Response Formatting Guidelines:
When you receive tool responses containing data (especially JSON), ALWAYS format them in a human-readable way:

1. Parse JSON data into clear, structured information
2. Extract key information and present it with proper formatting
3. Use bullet points, headers, and clear organization
4. Summarize what the data means in context
5. NEVER dump raw JSON or unformatted data in your responses

For example, if you receive JSON data about Confluence spaces, format it like:

## Your Confluence Spaces

• **My first space** (MFS)
  - Type: Global space
  - Created: July 1, 2025
  - Homepage ID: 65821

• **Company hub** 
  - Type: System space
  - Created: July 1, 2025
  - Homepage ID: 65968

Always make your responses clear, organized, and easy to read for humans."""
        
        if not available_tools:
            return base_prompt + "\n\nCurrently, no external tools are available, but I can still help with general questions and tasks."
        
        tools_description = "\n\nYou have access to the following MCP servers and their capabilities:\n\n"
        for server_id, info in available_tools.items():
            tools_description += f"**{server_id}** ({info['server_type']}):\n"
            tools_description += f"- Description: {info['description']}\n"
            tools_description += f"- Available capabilities: {', '.join(info['capabilities'])}\n\n"
        
        return base_prompt + tools_description
    
    def get_phase_context(self, phase: str) -> str:
        """Get phase-specific system prompt context for SDLC phases."""
        phase_prompts = {
            'requirements': """You are an expert Business Analyst and Requirements Engineer. Your role is to help gather, analyze, and document comprehensive software requirements.

Focus on:
- Functional requirements (what the system should do)
- Non-functional requirements (performance, security, usability, etc.)
- Business rules and constraints
- User stories and acceptance criteria
- Stakeholder needs and expectations
- Requirements traceability and validation

Ask probing questions to uncover hidden requirements and ensure completeness. Help structure requirements in a clear, testable, and unambiguous manner.""",

            'design': """You are a Senior Software Architect and System Designer. Your role is to help create robust, scalable, and maintainable system designs.

Focus on:
- System architecture and design patterns
- Component design and interfaces
- Data modeling and database design
- Technology stack selection
- Security architecture
- Performance and scalability considerations
- Design documentation and explanations

IMPORTANT: Do NOT generate XML diagrams, mxfile content, or any diagram markup in your responses. The system has specialized diagram generation tools that will automatically create visual diagrams when appropriate. Focus on providing clear textual explanations of the architecture and design concepts.

When discussing architecture, describe the components, relationships, and patterns in text. Visual diagrams will be generated automatically by the system's MCP tools.""",

            'development': """You are a Senior Software Developer and Technical Lead. Your role is to guide development planning, coding standards, and implementation strategies.

Focus on:
- Development methodology and best practices
- Code structure and organization
- Technology implementation details
- Development environment setup
- Version control strategies
- Code review processes
- Technical debt management

Provide practical guidance on implementation approaches, coding standards, and development workflows.""",

            'testing': """You are a Quality Assurance Engineer and Test Architect. Your role is to help design comprehensive testing strategies and quality assurance processes.

Focus on:
- Test planning and strategy
- Test case design and coverage
- Automated testing approaches
- Performance and load testing
- Security testing considerations
- Quality metrics and reporting
- Bug tracking and resolution processes

Help create thorough testing plans that ensure software quality and reliability.""",

            'deployment': """You are a DevOps Engineer and Deployment Specialist. Your role is to help design and implement robust deployment and release strategies.

Focus on:
- Deployment architecture and environments
- CI/CD pipeline design
- Infrastructure as Code
- Containerization and orchestration
- Monitoring and observability
- Release management processes
- Rollback and disaster recovery strategies

Provide guidance on modern deployment practices and infrastructure management.""",

            'maintenance': """You are a System Administrator and Maintenance Specialist. Your role is to help establish ongoing maintenance, monitoring, and support processes.

Focus on:
- System monitoring and alerting
- Maintenance procedures and schedules
- Performance optimization
- Security updates and patches
- Backup and recovery processes
- User support and documentation
- System lifecycle management

Help create sustainable maintenance practices that ensure long-term system health and user satisfaction."""
        }
        
        return phase_prompts.get(phase, "You are Claude, an AI assistant. Please provide helpful and accurate responses.")
    
    def build_phase_system_prompt(self, phase: str, available_tools: Optional[Dict[str, Any]] = None) -> str:
        """Build phase-specific system prompt with available tools."""
        base_prompt = self.get_phase_context(phase)
        
        # Add formatting guidelines to all phase prompts
        formatting_guidelines = """

IMPORTANT - Response Formatting Guidelines:
When you receive tool responses containing data (especially JSON), ALWAYS format them in a human-readable way:

1. Parse JSON data into clear, structured information
2. Extract key information and present it with proper formatting
3. Use bullet points, headers, and clear organization
4. Summarize what the data means in context
5. NEVER dump raw JSON or unformatted data in your responses

EXTERNAL INTEGRATIONS:
- Never create tickets without proper descriptions
- Format the response to show user-friendly ticket information, not raw JSON

Always make your responses clear, organized, and easy to read for humans."""
        
        base_prompt += formatting_guidelines
        
        if not available_tools:
            return base_prompt + "\n\nCurrently, no external tools are available, but I can still help with phase-specific guidance and best practices."
        
        tools_description = "\n\nYou have access to the following MCP servers and their capabilities:\n\n"
        for server_id, info in available_tools.items():
            tools_description += f"**{server_id}** ({info['server_type']}):\n"
            tools_description += f"- Description: {info['description']}\n"
            tools_description += f"- Available capabilities: {', '.join(info['capabilities'])}\n\n"
        
        # Add phase-specific tool usage guidance
        if phase == 'design':
            tools_description += "\nFor design phase, prioritize using architecture and diagramming tools to create visual representations of the system design."
        elif phase == 'development':
            tools_description += "\nFor development phase, use code analysis and documentation tools to support implementation planning."
        elif phase == 'testing':
            tools_description += "\nFor testing phase, leverage testing and quality assurance tools to design comprehensive test strategies."
        
        return base_prompt + tools_description