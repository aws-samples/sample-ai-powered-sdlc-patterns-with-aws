"""
Enhanced Claude Service with Dynamic Tool Integration

This service integrates with the Dynamic Tool Service to enable intelligent tool selection
based on user requests rather than hardcoded phase-specific behavior.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from services.claude_service import ClaudeService
from services.simple_tool_service import SimpleToolService

logger = logging.getLogger(__name__)

class EnhancedClaudeService(ClaudeService):
    """
    Enhanced Claude service that can dynamically select and use tools based on user intent.
    """
    
    def __init__(self, tool_service: Optional[SimpleToolService] = None):
        """Initialize the enhanced Claude service."""
        super().__init__()
        self.tool_service = tool_service

    
    async def get_intelligent_response(
        self, 
        messages: List[Dict[str, str]], 
        phase: str,
        conversation_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """Get intelligent response (non-streaming version)."""
        logger.info(f"Enhanced Claude service get_intelligent_response called with phase: {phase}, context type: {conversation_context.get('type') if conversation_context else 'None'}")
        
        try:
            # Get the user's latest message
            user_message = messages[-1]['content'] if messages else ""
            
            # Check if user is requesting specification document generation
            if self._is_specification_request(user_message, phase):
                return await self._handle_specification_generation(user_message, phase, conversation_context, messages)
            
            # Check if tools should be used based on user intent
            tool_response = None
            tools_used = []
            
            if self.tool_service:
                # Check if tools should be used for this request
                tool_response, tools_used = await self.tool_service.execute_tool_if_requested(
                    user_message, conversation_context
                )
            
            # Build system prompt with available tools and conversation context
            system_prompt = self._build_intelligent_system_prompt(phase, conversation_context)
            
            # Get Claude's response
            claude_response = await self.get_response(messages, system_prompt)
            
            # Check if Claude wants to use tools (support multiple tool calls)
            if self.tool_service:
                self.logger.debug(f"Checking for tool calls in response: {claude_response[:200]}...")
                tool_calls = self.tool_service.parse_tool_calls(claude_response)
                if tool_calls:
                    self.logger.info(f"Found {len(tool_calls)} tool calls")
                    
                    # Execute all tool calls
                    all_results = []
                    all_tools_used = []
                    
                    for i, tool_call in enumerate(tool_calls):
                        self.logger.info(f"Executing tool call {i+1}/{len(tool_calls)}: {tool_call['tool_name']}")
                        
                        # Execute the tool
                        user_id = user_context.get('user_id') if user_context else None
                        jwt_token = user_context.get('jwt_token') if user_context else None
                        tool_result, success = await self.tool_service.execute_tool(
                            tool_call["tool_name"], 
                            tool_call["arguments"],
                            user_id=user_id,
                            jwt_token=jwt_token
                        )
                        
                        if success and tool_result:
                            self.logger.info(f"Tool execution {i+1} successful, result length: {len(tool_result)} characters")
                            all_results.append({
                                'tool_name': tool_call["tool_name"],
                                'result': tool_result,
                                'success': True
                            })
                            all_tools_used.append(tool_call["tool_name"])
                        else:
                            self.logger.warning(f"Tool execution {i+1} failed for {tool_call['tool_name']}")
                            all_results.append({
                                'tool_name': tool_call["tool_name"],
                                'result': f"Tool execution failed",
                                'success': False
                            })
                    
                    # If we have results, format them
                    if all_results:
                        # For OpenAPI specification generation, handle parse errors and save spec to S3
                        if any('generate_openapi_spec' in result['tool_name'] for result in all_results):
                            await self._handle_openapi_spec_generation(all_results, conversation_context)
                        
                        # For Amazon Q Business tools, only return directly if no other analysis is requested
                        # Check if user is asking for domain analysis, diagrams, or other processing
                        user_message_lower = messages[-1]["content"].lower() if messages else ""
                        needs_further_processing = any(keyword in user_message_lower for keyword in [
                            'domain analysis', 'analyze', 'diagram', 'architecture', 'design', 'create', 'generate'
                        ])
                        
                        if not needs_further_processing:
                            for result in all_results:
                                if result['success'] and result['tool_name'].startswith("mcp_amazon_q_business"):
                                    self.logger.info("Amazon Q Business tool detected - returning polished response directly")
                                    return result['result'], all_tools_used
                        
                        # Combine all successful tool results
                        successful_results = [r for r in all_results if r['success']]
                        
                        if len(successful_results) == 1:
                            # Single result - handle formatting if needed
                            result = successful_results[0]
                            
                            # Return tool results directly without special formatting
                            self.logger.info(f"Returning {result['tool_name']} result directly")
                            return result['result'], all_tools_used
                        
                        elif len(successful_results) > 1:
                            # Multiple results - combine them with clear headers
                            self.logger.info(f"Combining {len(successful_results)} successful tool results")
                            combined_result = ""
                            
                            for i, result in enumerate(successful_results):
                                tool_name = result['tool_name'].replace('_', ' ').title()
                                if i > 0:
                                    combined_result += "\n\n---\n\n"
                                combined_result += f"## {tool_name} Results\n\n{result['result']}"
                            
                            return combined_result, all_tools_used
                        
                        # If no successful results, return Claude's original response
                        self.logger.warning("All tool executions failed")
                        return claude_response, []
                else:
                    self.logger.info("No tool calls detected in Claude response")
                    if "TOOL_CALL:" in claude_response:
                        self.logger.warning("TOOL_CALL found in response but parsing failed")
            
            # No tool call or tool service not available
            return claude_response, tools_used
            
        except Exception as e:
            logger.error(f"Error in get_intelligent_response: {e}")
            # Fallback to basic response with conversation context and formatting guidelines
            available_tools = self._convert_tools_format() if self.tool_service else None
            system_prompt = self.build_phase_system_prompt(phase, available_tools)
            if conversation_context:
                context_prompt = self._build_context_prompt(conversation_context)
                system_prompt = f"{system_prompt}\n\n{context_prompt}"
            response = await self.get_response(messages, system_prompt)
            return response, []


    
    def _build_intelligent_system_prompt(self, phase: str, conversation_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a system prompt that enables intelligent tool usage.
        """
        # Use the enhanced system prompt with formatting guidelines
        available_tools = self._convert_tools_format() if self.tool_service else None
        base_prompt = self.build_phase_system_prompt(phase, available_tools)
        
        # Add dynamic tool information
        tools_info = ""
        if self.tool_service:
            tools_info = self.tool_service.get_tools_for_llm()
        
        # Build conversation context section
        context_section = ""
        if conversation_context:
            context_section = self._build_context_prompt(conversation_context)
        
        intelligent_prompt = f"""{base_prompt}

{tools_info}

{context_section}

IMPORTANT INSTRUCTIONS:
🚨 STRICT TOOL SELECTION RULES - FOLLOW EXACTLY:
- MAXIMUM 1 TOOL per request unless explicitly told otherwise
- When user asks for ONE specific thing, use ONLY that tool
- DO NOT add extra tools "to be helpful" - stick to what's requested

EXPLICIT TOOL MAPPING:
- "create epics" or "extract epics" → ONLY use mcp_amazon_q_business_retrieve
- "domain analysis" or "use domain analysis tool" → ONLY use domain_analysis 
- "open api spec" or "generate openapi spec" → ONLY use generate_openapi_spec
- "architecture diagram" or "create diagram" → ONLY use create_architecture_diagram
- "cost estimate" → ONLY use estimate_architecture_cost

🚨 CRITICAL: If user says "just use that tool" or "only use X tool", use EXACTLY that tool and NO others.

- You are not limited by the current phase ({phase}) when selecting tools
- Always explain what you're doing when using tools
- Use the conversation context provided above to maintain continuity and reference previous discussions
- Provide comprehensive responses that combine tool results with your expertise

🚨 CRITICAL EPIC FORMATTING REQUIREMENT:
When users ask to "create epics" or "extract epics", you MUST call Amazon Q Business with this EXACT message:
"Extract requirements from project documentation and organize them into epics. You MUST format the response EXACTLY like this:

## User Management Epic
• User registration and authentication system
• Role-based access control (Customer, Admin)
• Profile management with reading preferences

## Book Catalog Management Epic
• Book browsing and search functionality
• Detailed book information pages
• Category/Genre classification

CRITICAL: Use ## [Epic Name] Epic headers and • bullet points ONLY. No other formatting allowed."

EPIC CREATION WORKFLOW:
- When asked to create epics: use ONLY mcp_amazon_q_business_retrieve
- When asked for domain analysis: use ONLY domain_analysis 
- When asked for OpenAPI spec: use ONLY generate_openapi_spec
- When asked for architecture diagram: use ONLY create_architecture_diagram

🚨 NEVER combine tools unless explicitly requested by user
🚨 ONE REQUEST = ONE TOOL (maximum)

EPIC FORMAT REQUIREMENTS:
When creating epics, you MUST format them exactly like this for proper extraction:

## [Epic Name] Epic
• Feature description 1
• Feature description 2
• Feature description 3
• Feature description 4

## [Another Epic Name] Epic
• Feature description A
• Feature description B
• Feature description C

CRITICAL FORMATTING RULES:
- Each epic MUST start with "## [Epic Name] Epic"
- Features MUST use bullet points with "•" character
- Each feature should be on its own line
- Keep epic names descriptive but concise
- Include 3-7 features per epic

AMAZON Q BUSINESS PROMPTING:
🚨 MANDATORY: When user asks for epics, you MUST call mcp_amazon_q_business_retrieve with this EXACT message:

"Extract requirements from AnyCompanyReads project documentation and organize them into epics. You MUST format the response EXACTLY like this:

## User Management Epic
• User registration and authentication system
• Role-based access control (Customer, Admin)
• Profile management with reading preferences

## Book Catalog Management Epic
• Book browsing and search functionality
• Detailed book information pages
• Category/Genre classification

CRITICAL: Use ## [Epic Name] Epic headers and • bullet points ONLY. No other formatting allowed."

DO NOT modify this prompt. DO NOT add explanations. Use it exactly as written.

- Amazon Q Business should be used for:
  * Extracting information from Confluence spaces
  * Analyzing requirements and creating epic breakdowns in the EXACT format above
  * Understanding business context and user needs
  * Creating detailed feature specifications
  * ONLY when user asks to "create epics" or "analyze requirements"

- External integrations are no longer available

EPIC CREATION FROM CONFLUENCE:
- When asked to "create epics" from Confluence data (NOT when asked to create tickets):
  1. Use Amazon Q Business with specific formatting instructions
  2. Ensure the response follows the exact epic format above
  3. Present the epic analysis for review

IMPORTANT DISTINCTION:
- "Create epics" = Use Amazon Q Business to analyze and format epic information
- External ticket creation is no longer available

DOMAIN ANALYSIS WORKFLOW:
- When asked for "domain analysis" or to "analyze" requirements:
  1. If Confluence data is involved, first use Amazon Q Business to extract information
  2. Then use the domain_analysis tool to create comprehensive domain models
  3. The domain analysis should include business context, entities, relationships, and technical requirements
  4. Present structured analysis with clear sections for different aspects of the domain

PHASE CONTEXT:
Current phase is "{phase}" - this provides context for your responses but does not limit which tools you can use.
"""
        
        return intelligent_prompt
    
    def _build_context_prompt(self, conversation_context: Dict[str, Any]) -> str:
        """Build context prompt from conversation history + project KB."""
        if not conversation_context:
            logger.warning("No conversation context provided to enhanced Claude service")
            return ""
        
        logger.info(f"Enhanced Claude service building context with: {conversation_context.get('type')} type, {len(conversation_context.get('messages', []))} messages, summary: {bool(conversation_context.get('summary'))}")
        
        context_parts = []
        
        # Add project context summary if available
        if conversation_context.get("summary"):
            context_parts.append("## Previous Conversation Summary")
            context_parts.append(conversation_context["summary"])
        
        # Add recent conversation context (limit to last 5 messages and truncate long content)
        if conversation_context.get("messages"):
            context_parts.append("## Recent Conversation History")
            recent_messages = conversation_context["messages"][-5:]  # Only last 5 messages
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                # Truncate very long messages
                if len(content) > 300:
                    content = content[:300] + "..."
                context_parts.append(f"**{role.title()}** ({timestamp}): {content}")
        
        # Add project-specific KB context
        kb_context = conversation_context.get("kb_context")
        if kb_context and kb_context.get("context_quality", 0) > 0:
            context_parts.append(f"## Project Knowledge Base Context ({kb_context.get('phase', 'general')} phase)")
            
            # Add relevant conversations from KB
            if kb_context.get("relevant_conversations"):
                context_parts.append("### Previous Project Discussions:")
                for conv in kb_context["relevant_conversations"]:
                    content_preview = conv.get("content", "")[:200] + "..." if len(conv.get("content", "")) > 200 else conv.get("content", "")
                    context_parts.append(f"- {content_preview}")
            
            # Add relevant code examples from KB
            if kb_context.get("relevant_code"):
                context_parts.append("### Related Code Examples:")
                for code in kb_context["relevant_code"]:
                    file_path = code.get("file_path", "unknown")
                    content_preview = code.get("content", "")[:150] + "..." if len(code.get("content", "")) > 150 else code.get("content", "")
                    context_parts.append(f"- From {file_path}: {content_preview}")
            
            # Add relevant diagrams from KB
            if kb_context.get("relevant_diagrams"):
                context_parts.append("### Related Architecture Diagrams:")
                for diagram in kb_context["relevant_diagrams"]:
                    diagram_content = diagram.get("content", "")
                    diagram_url = diagram.get("metadata", {}).get("diagram_url", "")
                    context_parts.append(f"- {diagram_content}")
                    if diagram_url:
                        context_parts.append(f"  Diagram URL: {diagram_url}")
            
            context_parts.append(f"*Found {kb_context.get('context_quality', 0)} relevant items from this project's history*")
        
        context_prompt = "\n\n".join(context_parts) if context_parts else ""
        logger.info(f"Enhanced Claude service built context prompt with {len(context_prompt)} characters")
        if context_prompt and len(context_prompt) > 10000:
            logger.warning(f"Large context prompt detected ({len(context_prompt)} chars), consider optimization")
        if context_prompt:
            logger.debug(f"Context prompt preview: {context_prompt[:200]}...")
        return context_prompt
    
    async def analyze_user_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze user intent to understand what they're asking for.
        
        Returns:
            Dictionary with intent analysis including suggested tools
        """
        message_lower = message.lower()
        
        intent_analysis = {
            'primary_intent': 'general_question',
            'suggested_tools': [],
            'confidence': 0.5,
            'keywords_found': []
        }
        
        # Cost-related intent
        cost_keywords = ['cost', 'price', 'budget', 'estimate', 'expensive', 'cheap', 'billing', 'money']
        if any(keyword in message_lower for keyword in cost_keywords):
            intent_analysis['primary_intent'] = 'cost_estimation'
            intent_analysis['suggested_tools'].append('estimate_architecture_cost')
            intent_analysis['confidence'] = 0.8
            intent_analysis['keywords_found'].extend([kw for kw in cost_keywords if kw in message_lower])
        
        # Diagram-related intent
        diagram_keywords = ['diagram', 'draw', 'visualize', 'architecture', 'chart', 'visual', 'show']
        if any(keyword in message_lower for keyword in diagram_keywords):
            intent_analysis['primary_intent'] = 'visualization'
            intent_analysis['suggested_tools'].append('create_architecture_diagram')
            intent_analysis['confidence'] = 0.9
            intent_analysis['keywords_found'].extend([kw for kw in diagram_keywords if kw in message_lower])
        
        # Code generation intent
        code_keywords = ['code', 'cloudformation', 'terraform', 'template', 'infrastructure', 'iac']
        if any(keyword in message_lower for keyword in code_keywords):
            intent_analysis['primary_intent'] = 'code_generation'
            intent_analysis['suggested_tools'].append('generate_architecture_code')
            intent_analysis['confidence'] = 0.85
            intent_analysis['keywords_found'].extend([kw for kw in code_keywords if kw in message_lower])
        
        # Analysis intent
        analysis_keywords = ['analyze', 'review', 'assess', 'evaluate', 'recommendations', 'best practices']
        if any(keyword in message_lower for keyword in analysis_keywords):
            intent_analysis['primary_intent'] = 'analysis'
            intent_analysis['suggested_tools'].append('analyze_architecture')
            intent_analysis['confidence'] = 0.75
            intent_analysis['keywords_found'].extend([kw for kw in analysis_keywords if kw in message_lower])
        
        # AWS knowledge intent
        aws_keywords = ['aws', 'amazon', 'ec2', 'rds', 's3', 'lambda', 'cloudfront', 'vpc']
        if any(keyword in message_lower for keyword in aws_keywords):
            intent_analysis['primary_intent'] = 'aws_knowledge'
            intent_analysis['suggested_tools'].append('query_aws_knowledge')
            intent_analysis['confidence'] = 0.8
            intent_analysis['keywords_found'].extend([kw for kw in aws_keywords if kw in message_lower])
        
        return intent_analysis
    
    def _convert_tools_format(self) -> Optional[Dict[str, Any]]:
        """Convert SimpleToolService format to Claude service format."""
        if not self.tool_service or not hasattr(self.tool_service, 'available_tools'):
            return None
        
        # Group tools by server_id
        servers = {}
        for tool_name, tool_info in self.tool_service.available_tools.items():
            server_id = tool_info['server_id']
            if server_id not in servers:
                servers[server_id] = {
                    'server_type': tool_info.get('server_type', 'tool'),
                    'description': tool_info.get('server_description', f'{server_id} server'),
                    'capabilities': []
                }
            servers[server_id]['capabilities'].append(tool_name)
        
        return servers
    
    def _basic_format_tool_result(self, tool_name: str, tool_result: str) -> str:
        """Basic formatting fallback when Claude formatting fails due to rate limits."""
        try:
            import json
            
            # Try to parse as JSON and format it
            if tool_result.strip().startswith('{') or tool_result.strip().startswith('['):
                data = json.loads(tool_result)
                
                if tool_name == "getPagesInConfluenceSpace":
                    return self._format_confluence_pages(data)
                elif tool_name == "getConfluenceSpaces":
                    return self._format_confluence_spaces(data)
                else:
                    # Generic JSON formatting
                    return f"## {tool_name.replace('_', ' ').title()} Results\n\n```json\n{json.dumps(data, indent=2)}\n```"
            else:
                return f"## {tool_name.replace('_', ' ').title()} Results\n\n{tool_result}"
                
        except json.JSONDecodeError:
            return f"## {tool_name.replace('_', ' ').title()} Results\n\n{tool_result}"
    
    def _format_confluence_pages(self, data: dict) -> str:
        """Format Confluence pages data."""
        if not data.get('results'):
            return "## Confluence Pages\n\nNo pages found in this space."
        
        formatted = "## Confluence Pages\n\n"
        for page in data['results']:
            formatted += f"### 📄 {page.get('title', 'Untitled')}\n"
            formatted += f"- **ID**: {page.get('id')}\n"
            formatted += f"- **Status**: {page.get('status', 'unknown').title()}\n"
            if page.get('createdAt'):
                formatted += f"- **Created**: {page.get('createdAt')}\n"
            if page.get('body'):
                body_preview = page['body'][:200] + "..." if len(page['body']) > 200 else page['body']
                formatted += f"- **Content Preview**: {body_preview}\n"
            formatted += "\n"
        
        return formatted
    
    def _format_confluence_spaces(self, data: dict) -> str:
        """Format Confluence spaces data."""
        if not data.get('results'):
            return "## Confluence Spaces\n\nNo spaces found."
        
        formatted = "## Your Confluence Spaces\n\n"
        for space in data['results']:
            formatted += f"### 📁 {space.get('name', 'Untitled Space')}\n"
            formatted += f"- **Key**: {space.get('key')}\n"
            formatted += f"- **Type**: {space.get('type', 'unknown').replace('_', ' ').title()}\n"
            formatted += f"- **Created**: {space.get('createdAt', 'unknown')}\n"
            if space.get('description'):
                formatted += f"- **Description**: {space['description']}\n"
            formatted += "\n"
        
        return formatted
    
    async def _handle_openapi_spec_generation(self, results: List[Dict[str, Any]], conversation_context: Dict[str, Any]):
        """Handle OpenAPI spec generation results, including parse error recovery."""
        from utils.openapi_formatter import OpenAPIFormatter
        
        for result in results:
            if 'generate_openapi_spec' in result['tool_name'] and result['success']:
                try:
                    import json
                    
                    tool_result = result['result']
                    self.logger.info(f"Processing OpenAPI spec generation result, length: {len(tool_result)} chars")
                    
                    # Try to parse the result as JSON first
                    try:
                        spec_data = json.loads(tool_result)
                    except json.JSONDecodeError:
                        # If it's not JSON, treat it as raw content
                        spec_data = tool_result
                    
                    # Use the OpenAPI formatter to extract and clean the spec
                    formatted_spec = OpenAPIFormatter.extract_and_format_spec(spec_data)
                    
                    if formatted_spec:
                        # Validate and fix any remaining issues
                        validated_spec = OpenAPIFormatter.validate_and_fix_spec(formatted_spec)
                        
                        # Format as pretty JSON
                        formatted_json = OpenAPIFormatter.format_spec_for_file(validated_spec)
                        
                        # Update the result with the cleaned spec
                        result['result'] = formatted_json
                        
                        self.logger.info("Successfully processed and formatted OpenAPI spec")
                        
                        # Save the spec to S3
                        await self._save_openapi_spec_to_s3([result], conversation_context)
                        
                    else:
                        self.logger.error("Could not extract valid OpenAPI spec from result")
                        
                except Exception as e:
                    self.logger.error(f"Error handling OpenAPI spec generation: {e}")

    
    async def _save_openapi_spec_to_s3(self, results: List[Dict[str, Any]], conversation_context: Dict[str, Any]):
        """Save OpenAPI spec to S3 if available."""
        try:
            # This method would save the spec to S3 - implementation depends on your S3 setup
            # For now, just log that we would save it
            for result in results:
                if 'generate_openapi_spec' in result['tool_name'] and result['success']:
                    self.logger.info("OpenAPI spec ready for S3 storage")
                    # TODO: Implement S3 storage logic here
                    
        except Exception as e:
            self.logger.error(f"Error saving OpenAPI spec to S3: {e}")

    def _format_atlassian_resources(self, data: list) -> str:
        """Format Atlassian resources data."""
        if not data:
            return "## Atlassian Resources\n\nNo resources found."
        
        formatted = "## Your Atlassian Resources\n\n"
        for resource in data:
            formatted += f"### 🏢 {resource.get('name', 'Unknown')}\n"
            formatted += f"- **URL**: {resource.get('url')}\n"
            formatted += f"- **ID**: {resource.get('id')}\n"
            if resource.get('scopes'):
                formatted += f"- **Permissions**: {', '.join(resource['scopes'])}\n"
            formatted += "\n"
        
        return formatted
    
    def _format_jira_creation_results(self, results: List[Dict[str, Any]]) -> str:
        """Format multiple Jira ticket creation results with user-friendly output."""
        successful_tickets = [r for r in results if r['success'] and 'createJiraIssue' in r['tool_name']]
        failed_tickets = [r for r in results if not r['success'] and 'createJiraIssue' in r['tool_name']]
        
        if not successful_tickets and not failed_tickets:
            return "No Jira tickets were processed."
        
        response_parts = []
        
        if successful_tickets:
            response_parts.append(f"## ✅ Successfully Created {len(successful_tickets)} Jira Ticket(s)")
            response_parts.append("")
            
            for i, result in enumerate(successful_tickets, 1):
                try:
                    import json
                    ticket_data = json.loads(result['result'])
                    ticket_key = ticket_data.get('key', 'Unknown')
                    ticket_id = ticket_data.get('id', 'Unknown')
                    ticket_url = ticket_data.get('self', '')
                    
                    # Convert API URL to user-friendly browse URL
                    browse_url = ticket_url
                    if ticket_url and 'api.atlassian.com' in ticket_url:
                        # Extract the cloud ID and convert to browse URL
                        import re
                        cloud_id_match = re.search(r'/ex/jira/([^/]+)/', ticket_url)
                        if cloud_id_match:
                            cloud_id = cloud_id_match.group(1)
                            browse_url = f"https://anycompanyreads.atlassian.net/browse/{ticket_key}"
                    
                    response_parts.append(f"**🎫 Ticket {i}: {ticket_key}**")
                    response_parts.append(f"- **Status**: Created and ready for development")
                    response_parts.append(f"- **Project**: CS (AnyCompanyReads)")
                    response_parts.append(f"- **Type**: New Feature")
                    if browse_url:
                        response_parts.append(f"- **View in Jira**: [Open {ticket_key}]({browse_url})")
                    response_parts.append("")
                    
                except (json.JSONDecodeError, KeyError) as e:
                    response_parts.append(f"**🎫 Ticket {i}**: Created successfully")
                    response_parts.append(f"- **Status**: Created (details parsing failed)")
                    response_parts.append("")
        
        if failed_tickets:
            response_parts.append(f"## ❌ Failed to Create {len(failed_tickets)} Ticket(s)")
            response_parts.append("")
            
            for i, result in enumerate(failed_tickets, 1):
                error_msg = result['result']
                # Clean up common error messages
                if "ConflictException" in error_msg:
                    error_msg = "Jira system was busy with concurrent requests. Please try again."
                elif "AUTH_REQUIRED" in error_msg:
                    error_msg = "Jira authentication required. Please complete OAuth setup."
                
                response_parts.append(f"**❌ Failed Ticket {i}**: {error_msg}")
                response_parts.append("")
        
        # Add summary with next steps
        total_requested = len(successful_tickets) + len(failed_tickets)
        response_parts.append(f"## 📊 Summary")
        response_parts.append(f"- **Total Requested**: {total_requested}")
        response_parts.append(f"- **Successfully Created**: {len(successful_tickets)}")
        response_parts.append(f"- **Failed**: {len(failed_tickets)}")
        
        if successful_tickets:
            response_parts.append("")
            response_parts.append("## 🚀 Next Steps")
            response_parts.append("- All tickets are now available in your Jira project")
            response_parts.append("- You can assign them to team members")
            response_parts.append("- Add them to your current sprint for development")
            response_parts.append("- Each ticket includes detailed descriptions and acceptance criteria")
        
        return "\n".join(response_parts)
    
    async def _save_openapi_spec_to_s3(self, results: List[Dict[str, Any]], conversation_context: Dict[str, Any]) -> None:
        """Extract OpenAPI specification from tool results and save to S3 as a generated code file."""
        try:
            # Find the successful OpenAPI generation result
            openapi_result = None
            for result in results:
                if result['success'] and 'generate_openapi_spec' in result['tool_name']:
                    openapi_result = result
                    break
            
            if not openapi_result:
                self.logger.warning("No successful OpenAPI generation result found")
                return
            
            # Extract the raw OpenAPI JSON from the tool response
            tool_response = openapi_result['result']
            openapi_json = self._extract_openapi_json_from_response(tool_response)
            
            if not openapi_json:
                self.logger.warning("Could not extract OpenAPI JSON from tool response, creating fallback file")
                # Create a fallback JSON with the raw response for debugging
                import json
                fallback_json = {
                    "openapi": "3.1.0",
                    "info": {
                        "title": "Generated API (Parse Error)",
                        "version": "1.0.0",
                        "description": "Raw generated content due to JSON parsing error"
                    },
                    "x-parse-error": "Could not extract valid OpenAPI JSON from tool response",
                    "x-raw-tool-response": tool_response[:5000] + "..." if len(tool_response) > 5000 else tool_response
                }
                openapi_json = json.dumps(fallback_json, indent=2, ensure_ascii=False)
            
            # Get project name from conversation context
            project_name = self._extract_project_name_from_context(conversation_context)
            
            # Generate filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"openapi_spec_{timestamp}.json"
            
            # Save to S3 using the S3 storage service
            from services.s3_storage_service import S3StorageService
            s3_service = S3StorageService()
            
            # Create files dictionary for the save_generated_code method
            files_dict = {filename: openapi_json}
            
            result = await s3_service.save_generated_code(project_name, files_dict)
            
            if result.success:
                self.logger.info(f"✅ Successfully saved OpenAPI specification to S3: {filename}")
            else:
                self.logger.error(f"❌ Failed to save OpenAPI specification to S3: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"❌ Error saving OpenAPI spec to S3: {e}")
    

    
    def _extract_openapi_json_from_response(self, tool_response: str) -> str:
        """Extract and format the OpenAPI JSON from the tool response."""
        try:
            import json
            import re
            
            self.logger.info(f"Extracting OpenAPI JSON from response (length: {len(tool_response)})")
            
            # Method 1: Try to parse the entire response as JSON (if it's already valid JSON)
            try:
                parsed_json = json.loads(tool_response)
                if isinstance(parsed_json, dict) and 'openapi' in parsed_json:
                    self.logger.info("Found valid OpenAPI JSON in direct response")
                    return json.dumps(parsed_json, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
            
            # Method 2: Look for JSON in code blocks
            json_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', tool_response, re.DOTALL)
            if json_block_match:
                json_content = json_block_match.group(1).strip()
                try:
                    parsed_json = json.loads(json_content)
                    if isinstance(parsed_json, dict) and 'openapi' in parsed_json:
                        self.logger.info("Found valid OpenAPI JSON in code block")
                        return json.dumps(parsed_json, indent=2, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSON from code block: {e}")
            
            # Method 3: Look for x-raw-generated-content field (for error responses)
            raw_content_match = re.search(r'"x-raw-generated-content":\s*"(.*?)"(?=\s*[,}])', tool_response, re.DOTALL)
            if raw_content_match:
                escaped_json = raw_content_match.group(1)
                # Properly unescape the JSON string
                unescaped_json = escaped_json.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\').replace('\\/', '/')
                try:
                    parsed_json = json.loads(unescaped_json)
                    if isinstance(parsed_json, dict) and 'openapi' in parsed_json:
                        self.logger.info("Found valid OpenAPI JSON in x-raw-generated-content")
                        return json.dumps(parsed_json, indent=2, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSON from x-raw-generated-content: {e}")
                    # Try to fix the truncated JSON
                    fixed_json = self._attempt_json_completion(unescaped_json)
                    if fixed_json:
                        try:
                            parsed_json = json.loads(fixed_json)
                            if isinstance(parsed_json, dict) and 'openapi' in parsed_json:
                                self.logger.info("Successfully fixed truncated OpenAPI JSON from x-raw-generated-content")
                                return json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        except json.JSONDecodeError:
                            pass
                    
                    # Try to create a minimal valid OpenAPI spec from the truncated content
                    minimal_spec = self._create_minimal_openapi_from_truncated(unescaped_json)
                    if minimal_spec:
                        self.logger.info("Created minimal OpenAPI spec from truncated content")
                        return json.dumps(minimal_spec, indent=2, ensure_ascii=False)
                    
                    # Return the unescaped content as-is for debugging
                    return unescaped_json
            
            # Method 4: Try to find a complete JSON object with balanced braces
            def find_balanced_json(text, start_pos=0):
                """Find a balanced JSON object starting from start_pos."""
                brace_count = 0
                start_idx = -1
                
                for i in range(start_pos, len(text)):
                    if text[i] == '{':
                        if brace_count == 0:
                            start_idx = i
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_idx != -1:
                            return text[start_idx:i+1]
                return None
            
            # Look for JSON objects that contain "openapi"
            pos = 0
            while pos < len(tool_response):
                openapi_pos = tool_response.find('"openapi"', pos)
                if openapi_pos == -1:
                    break
                
                # Find the start of the JSON object containing this "openapi" field
                json_start = tool_response.rfind('{', 0, openapi_pos)
                if json_start != -1:
                    json_content = find_balanced_json(tool_response, json_start)
                    if json_content:
                        try:
                            parsed_json = json.loads(json_content)
                            if isinstance(parsed_json, dict) and 'openapi' in parsed_json:
                                self.logger.info("Found valid OpenAPI JSON using balanced brace matching")
                                return json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        except json.JSONDecodeError:
                            pass
                
                pos = openapi_pos + 1
            
            self.logger.warning("Could not find valid OpenAPI JSON in tool response")
            self.logger.debug(f"Response preview: {tool_response[:500]}...")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting OpenAPI JSON: {e}")
            return None
    
    def _attempt_json_completion(self, truncated_json: str) -> Optional[str]:
        """Attempt to complete a truncated JSON string by adding missing closing braces."""
        try:
            # First, try to find where the JSON was likely truncated
            # Look for incomplete strings or values at the end
            completion = truncated_json.rstrip()
            
            # Special handling for OpenAPI specs that get cut off mid-array or mid-object
            if '"data": [' in completion and not completion.rstrip().endswith(']'):
                # Find the last complete object in the data array
                last_complete_obj = completion.rfind('},')
                if last_complete_obj != -1:
                    # Truncate to the last complete object and close the array
                    completion = completion[:last_complete_obj + 1] + ']'
                    # Find the parent object that contains this array and close it
                    data_array_start = completion.rfind('"data": [')
                    if data_array_start != -1:
                        # Look for the opening brace of the parent object
                        parent_start = completion.rfind('{', 0, data_array_start)
                        if parent_start != -1:
                            completion += '}'
            
            # Handle truncation in the middle of an object (common pattern)
            elif completion.count('{') > completion.count('}'):
                # Find the last complete key-value pair
                patterns_to_try = [
                    '",\n',  # Complete string value with newline
                    '",',    # Complete string value
                    '},',    # Complete object
                    '],',    # Complete array
                ]
                
                last_complete_pos = -1
                for pattern in patterns_to_try:
                    pos = completion.rfind(pattern)
                    if pos > last_complete_pos:
                        last_complete_pos = pos
                
                if last_complete_pos != -1:
                    # Truncate to the last complete element
                    if completion[last_complete_pos:last_complete_pos+2] == '",':
                        completion = completion[:last_complete_pos + 1]
                    else:
                        completion = completion[:last_complete_pos + 1]
            
            # If it ends with a comma or incomplete string, try to clean it up
            if completion.endswith(','):
                # Remove trailing comma
                completion = completion.rstrip(',').rstrip()
            elif completion.endswith('"') and not completion.endswith('"}'):
                # Check if it's an incomplete string value
                # Count quotes to see if we're in the middle of a string
                quote_count = completion.count('"')
                if quote_count % 2 == 1:  # Odd number means incomplete string
                    # Find the last complete key-value pair
                    last_complete_pos = completion.rfind('",')
                    if last_complete_pos != -1:
                        completion = completion[:last_complete_pos + 1]
            
            # Handle incomplete array elements (common in OpenAPI examples)
            if completion.endswith('{\n      "id": "r') or completion.endswith('{\n                      "id": "r'):
                # Find the start of this incomplete object
                incomplete_start = completion.rfind('{\n')
                if incomplete_start != -1:
                    # Remove the incomplete object
                    completion = completion[:incomplete_start].rstrip().rstrip(',')
            
            # Count open and close braces/brackets to determine what's missing
            brace_stack = []
            for char in completion:
                if char in '{[':
                    brace_stack.append(char)
                elif char in '}]':
                    if brace_stack:
                        opening = brace_stack.pop()
                        # Verify matching pairs
                        if (char == '}' and opening != '{') or (char == ']' and opening != '['):
                            self.logger.warning("Mismatched braces/brackets in JSON")
                            return None
            
            # Add missing closing characters in reverse order
            while brace_stack:
                opening = brace_stack.pop()
                if opening == '{':
                    completion += '}'
                elif opening == '[':
                    completion += ']'
            
            self.logger.info(f"Attempted to complete truncated JSON (original: {len(truncated_json)} chars, completed: {len(completion)} chars)")
            return completion
            
        except Exception as e:
            self.logger.error(f"Error attempting to complete JSON: {e}")
            return None

    def _create_minimal_openapi_from_truncated(self, truncated_json: str) -> Optional[dict]:
        """Create a minimal valid OpenAPI spec from truncated content."""
        try:
            # Extract basic info if available
            title = "Generated API"
            version = "1.0.0"
            description = "API specification generated from truncated content"
            
            # Try to extract title from the truncated content
            if '"title":' in truncated_json:
                title_match = re.search(r'"title":\s*"([^"]+)"', truncated_json)
                if title_match:
                    title = title_match.group(1)
            
            # Try to extract version
            if '"version":' in truncated_json:
                version_match = re.search(r'"version":\s*"([^"]+)"', truncated_json)
                if version_match:
                    version = version_match.group(1)
            
            # Try to extract description
            if '"description":' in truncated_json:
                desc_match = re.search(r'"description":\s*"([^"]+)"', truncated_json)
                if desc_match:
                    description = desc_match.group(1)
            
            # Extract any complete paths that we can find
            paths = {}
            if '"paths":' in truncated_json:
                # Extract paths more comprehensively
                # Look for path definitions like "/books": {
                path_pattern = r'"(/[^"]*)":\s*\{'
                path_matches = re.finditer(path_pattern, truncated_json)
                
                for match in path_matches:
                    path_name = match.group(1)
                    # Try to extract operations for this path
                    path_start = match.end()
                    
                    # Look for HTTP methods
                    methods = ['get', 'post', 'put', 'delete', 'patch']
                    path_obj = {}
                    
                    for method in methods:
                        method_pattern = f'"{method}":\\s*\\{{'
                        method_match = re.search(method_pattern, truncated_json[path_start:path_start+2000])
                        if method_match:
                            # Try to extract summary
                            summary_pattern = r'"summary":\s*"([^"]+)"'
                            summary_match = re.search(summary_pattern, truncated_json[path_start:path_start+1000])
                            summary = summary_match.group(1) if summary_match else f"{method.title()} {path_name}"
                            
                            path_obj[method] = {
                                "summary": summary,
                                "responses": {
                                    "200": {
                                        "description": "Successful response"
                                    }
                                }
                            }
                    
                    if path_obj:
                        paths[path_name] = path_obj
            
            # Create minimal valid OpenAPI spec
            minimal_spec = {
                "openapi": "3.1.0",
                "info": {
                    "title": title,
                    "version": version,
                    "description": f"{description} (Generated from truncated content)"
                },
                "paths": paths if paths else {
                    "/": {
                        "get": {
                            "summary": "Root endpoint",
                            "responses": {
                                "200": {
                                    "description": "Successful response"
                                }
                            }
                        }
                    }
                }
            }
            
            self.logger.info(f"Created minimal OpenAPI spec with {len(paths)} paths from truncated content")
            return minimal_spec
            
        except Exception as e:
            self.logger.error(f"Error creating minimal OpenAPI spec: {e}")
            return None

    def _extract_project_name_from_context(self, conversation_context: Dict[str, Any]) -> str:
        """Extract project name from conversation context."""
        if not conversation_context:
            return "unknown-project"
        
        # Try various ways to get the project name
        project_name = (
            conversation_context.get('project_name') or
            conversation_context.get('project_id') or
            conversation_context.get('conversation_id', '').split('_')[1] if '_' in conversation_context.get('conversation_id', '') else None
        )
        
        return project_name or "unknown-project"
    
    def _is_specification_request(self, user_message: str, phase: str) -> bool:
        """Check if the user is requesting specification document generation."""
        message_lower = user_message.lower()
        
        # General specification keywords
        spec_keywords = [
            'generate specification',
            'create specification', 
            'generate spec',
            'create spec',
            'specification document',
            'spec document',
            'generate document',
            'create document',

        ]
        
        # Phase-specific keywords
        phase_keywords = [
            f'generate {phase} specification',
            f'create {phase} specification',
            f'generate {phase} spec',
            f'create {phase} spec',
            f'{phase} specification document',
            f'{phase} spec document',
            f'generate {phase} document',
            f'create {phase} document'
        ]
        
        all_keywords = spec_keywords + phase_keywords
        
        return any(keyword in message_lower for keyword in all_keywords)
    

    
    def _extract_project_id(self, conversation_context: Dict[str, Any]) -> str:
        """Extract project ID from conversation context."""
        # Try to get project ID from various sources
        if conversation_context:
            # Check if there's a project_id in the context
            if 'project_id' in conversation_context:
                return conversation_context['project_id']
            
            # Check if there's a conversation ID we can extract from
            if 'conversation_id' in conversation_context:
                conv_id = conversation_context['conversation_id']
                if '_' in conv_id:
                    parts = conv_id.split('_')
                    if len(parts) >= 2:
                        return parts[1]  # Assuming format like "phase_projectid_timestamp"
            
            # Check for project info in the summary or messages
            summary = conversation_context.get('summary', '')
            if 'project:' in summary.lower():
                import re
                project_match = re.search(r'project:\s*([a-zA-Z0-9_-]+)', summary.lower())
                if project_match:
                    return project_match.group(1)
            
            # Look for project ID patterns in summary
            if summary:
                # Look for patterns like "Project: fvdfev" or "project fvdfev"
                import re
                patterns = [
                    r'project[:\s]+([a-zA-Z0-9_-]+)',
                    r'project\s+([a-zA-Z0-9_-]+)',
                    r'([a-zA-Z0-9_-]+)\s+project'
                ]
                for pattern in patterns:
                    match = re.search(pattern, summary.lower())
                    if match:
                        project_id = match.group(1)
                        if len(project_id) > 2 and project_id not in ['the', 'this', 'that', 'and', 'for']:
                            return project_id
            
            # Check messages for project references
            messages = conversation_context.get('messages', [])
            for msg in messages:
                content = msg.get('content', '').lower()
                if 'project' in content:
                    # Try to extract project name/id from content
                    import re
                    project_match = re.search(r'project[:\s]+([a-zA-Z0-9_-]+)', content)
                    if project_match:
                        return project_match.group(1).lower().replace(' ', '-')
        
        # Fallback to timestamp-based ID
        from datetime import datetime
        return f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _prepare_conversation_history(
        self, 
        conversation_context: Dict[str, Any], 
        current_messages: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Prepare conversation history for PDF generation."""
        from datetime import datetime
        
        history = []
        
        # Add context messages if available
        if conversation_context and 'messages' in conversation_context:
            for msg in conversation_context['messages']:
                history.append({
                    'user_message': msg.get('content', '') if msg.get('role') == 'user' else '',
                    'ai_response': msg.get('content', '') if msg.get('role') == 'assistant' else '',
                    'timestamp': msg.get('timestamp', datetime.now().isoformat()),
                    'tools_used': msg.get('tools_used', [])
                })
        
        # Add current conversation messages
        for i in range(0, len(current_messages), 2):
            user_msg = current_messages[i] if i < len(current_messages) else {'content': ''}
            ai_msg = current_messages[i + 1] if i + 1 < len(current_messages) else {'content': ''}
            
            history.append({
                'user_message': user_msg.get('content', ''),
                'ai_response': ai_msg.get('content', ''),
                'timestamp': datetime.now().isoformat(),
                'tools_used': []
            })
        
        return history
    
    def _format_file_size(self, size_bytes: Optional[int]) -> str:
        """Format file size in human-readable format."""
        if not size_bytes:
            return "Unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
  
  

    
