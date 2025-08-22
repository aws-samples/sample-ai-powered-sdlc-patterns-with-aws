"""Main chatbox manager service."""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from services.session_manager import SessionManager
from services.claude_service import ClaudeService  # Temporarily disabled
from services.mcp_service import MCPService
from services.diagram_service import DiagramService

from services.text_formatter import TextFormatter
from services.output_processor import OutputProcessor


class ChatboxManager:
    """Main service for managing chatbot conversations and integrations."""
    
    def __init__(self):
        """Initialize the ChatboxManager."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize service components
        self.session_manager = SessionManager()
        self.claude_service = ClaudeService()
        self.mcp_service = MCPService()
        self.diagram_service = DiagramService()
        self.text_formatter = TextFormatter()

        self.output_processor = OutputProcessor(self.diagram_service)
        
        # Track last specification generation times
        self._last_spec_generation: Dict[str, datetime] = {}
    
    async def get_response(self, message: str, conversation_id: Optional[str] = None, phase: Optional[str] = None, user_context: Optional[Dict[str, Any]] = None, conversation_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get AI response for a message."""
        # Initialize services on first request
        await self._ensure_services_initialized()
        
        # Set ID token in MCP service if available (prefer explicit id_token, fallback to jwt_token)
        id_token = None
        if user_context:
            id_token = user_context.get('id_token') or user_context.get('jwt_token')
        
        if id_token and self.mcp_service:
            self.mcp_service.set_cognito_id_token(id_token)
            self.logger.info(f"Set Cognito ID token for user {user_context.get('username', 'unknown')}")
        
        # Create or get conversation session
        if conversation_id is None or not self.session_manager.session_exists(conversation_id):
            conversation_id = self.session_manager.create_session(conversation_id, phase)
        
        session = self.session_manager.get_session(conversation_id)
        if not session:
            return self._create_error_response(
                'Error: Could not create or retrieve conversation session',
                conversation_id
            )
        
        try:
            # Get AI response
            if self.mcp_service.is_available():
                ai_response, tools_used = await self._get_mcp_response(message, session, user_context)
            else:
                ai_response, tools_used = await self._get_basic_response(message, session)
            
            # Format the AI response for better readability (helps with URL extraction)
            ai_response = self.text_formatter.format_ai_response(ai_response)
            
            # Update session
            self.session_manager.update_session(conversation_id, message, ai_response, tools_used)
            
            return {
                'response': ai_response,
                'conversation_id': conversation_id,
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'tools_used': tools_used or []
            }
            
        except Exception as e:
            error_message = f"I apologize, but I encountered an error: {str(e)}"
            self.session_manager.update_session(conversation_id, message, error_message, [])
            
            return self._create_error_response(error_message, conversation_id)
    

    async def get_streaming_phase_response(self, message: str, phase: str, conversation_id: Optional[str] = None, project_name: Optional[str] = None, conversation_context: Optional[Dict[str, Any]] = None, user_context: Optional[Dict[str, Any]] = None):
        """Get streaming AI response for a specific SDLC phase."""
        # Validate phase
        allowed_phases = ['requirements', 'design', 'development', 'testing', 'deployment', 'maintenance']
        if phase not in allowed_phases:
            yield {
                "type": "error",
                "error": f'Invalid phase "{phase}". Allowed phases are: {", ".join(allowed_phases)}'
            }
            return
        
        # Initialize services
        await self._ensure_services_initialized()
        
        # Create or get conversation session
        if conversation_id is None or not self.session_manager.session_exists(conversation_id):
            conversation_id = self.session_manager.create_session(conversation_id, phase)
        
        session = self.session_manager.get_session(conversation_id)
        if not session:
            yield {
                "type": "error",
                "error": "Error: Could not create or retrieve conversation session"
            }
            return
        
        # Store project name in session if provided
        if project_name:
            session['project_name'] = project_name
            session['user_project_name'] = project_name
        
        try:
            # Add conversation_id and project_name to conversation_context
            if conversation_context is None:
                conversation_context = {}
            conversation_context['conversation_id'] = conversation_id
            if project_name:
                conversation_context['project_name'] = project_name
            
            # Extract ID token from user_context if available (prefer explicit id_token, fallback to jwt_token)
            id_token = None
            if user_context:
                id_token = user_context.get('id_token') or user_context.get('jwt_token')
            
            # Build conversation history
            messages = self._build_conversation_history(session, message)
            
            # Get streaming response
            full_response = ""
            tools_used = []
            
            if self.mcp_service.is_available():
                # Use enhanced Claude service with streaming support
                try:
                    from services.enhanced_claude_service import EnhancedClaudeService
                    from services.simple_tool_service import SimpleToolService
                    
                    # Initialize services if needed
                    if not hasattr(self, '_tool_service'):
                        self._tool_service = SimpleToolService(self.mcp_service.get_mcp_client(), self.mcp_service)
                        await self._tool_service.initialize()
                    
                    if not hasattr(self, '_enhanced_claude_service'):
                        self._enhanced_claude_service = EnhancedClaudeService(self._tool_service)
                    
                    self.logger.info(f"Using enhanced Claude service for streaming in phase: {phase}")
                    
                    # Check if user is requesting tools first
                    user_message = messages[-1]['content'] if messages else ""
                    
                    # Check for tool usage patterns
                    tool_response = None
                    tools_used_from_enhanced = []
                    
                    if self._tool_service:
                        # Check if this is a Confluence-related query that should use Amazon Q Business
                        if hasattr(self._enhanced_claude_service, '_is_confluence_query') and self._enhanced_claude_service._is_confluence_query(user_message):
                            yield {
                                "type": "tools",
                                "tools_used": ["mcp_amazon_q_business_retrieve"],
                                "tool_status": "processing"
                            }
                            
                            # Create user_context for enhanced Claude service
                            user_context_for_enhanced = {'jwt_token': id_token} if id_token else None
                            tool_response, tools_used_from_enhanced = await self._enhanced_claude_service._handle_confluence_query(user_message, conversation_context, user_context_for_enhanced)
                            
                            if tool_response:
                                yield {
                                    "type": "tools",
                                    "tools_used": tools_used_from_enhanced,
                                    "tool_status": "completed"
                                }
                                
                                # Stream the tool response
                                for i in range(0, len(tool_response), 5):
                                    chunk = tool_response[i:i+5]
                                    yield {
                                        "type": "content",
                                        "content": chunk
                                    }
                                    await asyncio.sleep(0.02)
                                
                                full_response = tool_response
                                tools_used = tools_used_from_enhanced
                            else:
                                # Continue with normal streaming if tool didn't return response
                                tool_response = None
                        else:
                            # Check for other tool requests
                            # Pass ID token to tool service for Amazon Q Business authentication
                            if hasattr(self._tool_service, 'set_cognito_id_token') and id_token:
                                self._tool_service.set_cognito_id_token(id_token)
                            
                            tool_response, tools_used_from_enhanced = await self._tool_service.execute_tool_if_requested(
                                user_message, conversation_context
                            )
                            
                            if tool_response:
                                yield {
                                    "type": "tools",
                                    "tools_used": tools_used_from_enhanced,
                                    "tool_status": "processing"
                                }
                                
                                await asyncio.sleep(0.5)
                                
                                yield {
                                    "type": "tools",
                                    "tools_used": tools_used_from_enhanced,
                                    "tool_status": "completed"
                                }
                                
                                # Store raw response for output processing
                                raw_response = tool_response
                                self.logger.info(f"Stored raw_response for output processing: {len(tool_response)} chars")
                                self.logger.info(f"Raw response preview: {raw_response[:200]}...")
                                # Debug: Check if tool response contains URLs
                                if "https://" in tool_response:
                                    self.logger.info("✅ Tool response contains https URLs")
                                    import re
                                    urls = re.findall(r'https://[^\s\)]+', tool_response)
                                    self.logger.info(f"URLs found in tool response: {urls}")
                                else:
                                    self.logger.warning("❌ Tool response does NOT contain https URLs")
                                
                                # Format the tool response for display
                                formatted_tool_response = self._format_tool_results(tool_response)
                                
                                # Stream the formatted tool response
                                for i in range(0, len(formatted_tool_response), 5):
                                    chunk = formatted_tool_response[i:i+5]
                                    yield {
                                        "type": "content",
                                        "content": chunk
                                    }
                                    await asyncio.sleep(0.02)
                                
                                full_response = formatted_tool_response
                                tools_used = tools_used_from_enhanced
                    
                    # If no tool response, get streaming response from Claude
                    if not tool_response:
                        # Build system prompt with phase context and conversation context
                        system_prompt = self._enhanced_claude_service._build_intelligent_system_prompt(phase, conversation_context)
                        
                        # Get streaming response from Claude and collect it first
                        raw_response = ""
                        async for chunk in self.claude_service.get_streaming_response(messages, system_prompt):
                            raw_response += chunk
                        
                        # Now format the complete response and stream it in a controlled way
                        formatted_response = self.text_formatter.format_ai_response(raw_response)
                        
                        # Stream the formatted response in chunks
                        chunk_size = 8  # Stream in small chunks for smooth effect
                        for i in range(0, len(formatted_response), chunk_size):
                            chunk = formatted_response[i:i+chunk_size]
                            yield {
                                "type": "content",
                                "content": chunk
                            }
                            await asyncio.sleep(0.02)  # Small delay for streaming effect
                        
                        full_response = formatted_response
                        
                        # After streaming is complete, check for tool calls in the raw response
                        if self._tool_service and raw_response:
                            tool_calls = self._tool_service.parse_tool_calls(raw_response)
                            if tool_calls:
                                yield {
                                    "type": "tools",
                                    "tools_used": [call["tool_name"] for call in tool_calls],
                                    "tool_status": "processing"
                                }
                                
                                # Execute tools and get additional response
                                additional_response = ""
                                failed_tools = []
                                for tool_call in tool_calls:
                                    tool_result, success = await self._tool_service.execute_tool(
                                        tool_call["tool_name"], 
                                        tool_call["arguments"],
                                        jwt_token=id_token if 'id_token' in locals() else None
                                    )
                                    if tool_result:  # Include both success and failure results
                                        if success:
                                            tools_used.append(tool_call["tool_name"])
                                        else:
                                            failed_tools.append(tool_call["tool_name"])
                                        additional_response += f"\n\n{tool_result}"
                                
                                if additional_response:
                                    # Add tool results to raw response for output processing
                                    if 'raw_response' not in locals():
                                        raw_response = ""
                                    raw_response += additional_response
                                    
                                    # Format the additional response and make it more readable
                                    formatted_additional = self._format_tool_results(additional_response)
                                    
                                    # Stream the formatted additional tool results
                                    for i in range(0, len(formatted_additional), 10):
                                        chunk = formatted_additional[i:i+10]
                                        full_response += chunk
                                        yield {
                                            "type": "content",
                                            "content": chunk
                                        }
                                        await asyncio.sleep(0.03)
                                
                                # Send tool completion status
                                tool_status = "completed" if not failed_tools else "completed_with_errors"
                                yield {
                                    "type": "tools",
                                    "tools_used": tools_used,
                                    "failed_tools": failed_tools,
                                    "tool_status": tool_status
                                }
                    
                except Exception as e:
                    self.logger.warning(f"Enhanced streaming failed, using basic streaming: {e}")
                    # Fallback to basic streaming without enhanced features
                    system_prompt = self.claude_service.build_phase_system_prompt(phase, self.mcp_service.get_available_tools())
                    
                    if conversation_context:
                        context_prompt = self._build_context_prompt(conversation_context)
                        system_prompt = f"{system_prompt}\n\n{context_prompt}"
                    
                    async for chunk in self.claude_service.get_streaming_response(messages, system_prompt):
                        full_response += chunk
                        yield {
                            "type": "content",
                            "content": chunk
                        }
            else:
                # Basic streaming without MCP
                system_prompt = self.claude_service.get_phase_context(phase)
                
                if conversation_context:
                    context_prompt = self._build_context_prompt(conversation_context)
                    system_prompt = f"{system_prompt}\n\n{context_prompt}"
                
                async for chunk in self.claude_service.get_streaming_response(messages, system_prompt):
                    full_response += chunk
                    yield {
                        "type": "content",
                        "content": chunk
                    }
            
            # Format the final response (this will convert tool calls to human-readable messages)
            if 'raw_response' in locals():
                # Use raw response for formatting to ensure tool calls are properly converted
                formatted_response = self.text_formatter.format_ai_response(raw_response)
                # If we had additional tool results, append them
                if len(full_response) > len(raw_response):
                    additional_content = full_response[len(raw_response):]
                    formatted_response += self.text_formatter.format_ai_response(additional_content)
                full_response = formatted_response
            else:
                full_response = self.text_formatter.format_ai_response(full_response)
            
            # 🎯 AUTOMATIC OUTPUT PROCESSING - Process tool outputs for diagrams, code, documents
            # This is crucial for streaming to work with all workflows
            
            # Ensure we have the complete response including tool results for processing
            if 'raw_response' in locals():
                response_for_processing = raw_response
                self.logger.info(f"Using raw_response for output processing: {len(raw_response)} chars")
                # Debug: Check if raw_response contains URLs
                if "https://" in raw_response:
                    self.logger.info("✅ Raw response contains https URLs")
                else:
                    self.logger.warning("❌ Raw response does NOT contain https URLs")
                    self.logger.info(f"Raw response preview: {raw_response[:500]}...")
            else:
                response_for_processing = full_response
                self.logger.info(f"Using full_response for output processing: {len(full_response)} chars")
                # Debug: Check if full_response contains URLs
                if "https://" in full_response:
                    self.logger.info("✅ Full response contains https URLs")
                else:
                    self.logger.warning("❌ Full response does NOT contain https URLs")
                    self.logger.info(f"Full response preview: {full_response[:500]}...")
            
            self.logger.info(f"Processing response with tools_used: {tools_used}")
            processed_outputs = await self.output_processor.process_tool_outputs(
                tools_used, response_for_processing, session
            )
            
            # Update session with processed outputs
            if processed_outputs['diagrams']:
                if 'diagrams' not in session:
                    session['diagrams'] = []
                session['diagrams'].extend(processed_outputs['diagrams'])
                self.logger.debug(f"Added {len(processed_outputs['diagrams'])} diagrams to session via streaming")
                
                # Notify about diagram generation
                yield {
                    "type": "diagrams",
                    "diagrams": processed_outputs['diagrams'],
                    "count": len(processed_outputs['diagrams'])
                }
            
            if processed_outputs['code_files']:
                if 'code_files' not in session:
                    session['code_files'] = []
                session['code_files'].extend(processed_outputs['code_files'])
                self.logger.debug(f"Added {len(processed_outputs['code_files'])} code files to session via streaming")
                
                # Notify about code generation
                yield {
                    "type": "code",
                    "code_files": processed_outputs['code_files'],
                    "count": len(processed_outputs['code_files'])
                }
            

            
            # Notify about Jira updates if any (epics or tickets)
            if processed_outputs.get('jira_data_updated', False):
                self.logger.info(f"🎫 Streaming: Jira data updated - sending notification")
                self.logger.info(f"🎫 Processed outputs: epics={len(processed_outputs.get('epics', []))}, tickets={len(processed_outputs.get('jira_tickets', []))}")
                
                jira_notification = {
                    "type": "jira",
                    "jira_data_updated": True
                }
                self.logger.info(f"🎫 YIELDING jira notification: {jira_notification}")
                yield jira_notification
                
                # Add success message for epics
                if processed_outputs.get('epics'):
                    epic_count = len(processed_outputs['epics'])
                    epic_message = f"\n\n📋 I've generated {epic_count} epic{'' if epic_count == 1 else 's'} for your project. You can view them in the epics panel above."
                    full_response += epic_message
                    
                    # Stream the epic notification
                    for i in range(0, len(epic_message), 5):
                        chunk = epic_message[i:i+5]
                        yield {
                            "type": "content",
                            "content": chunk
                        }
                        await asyncio.sleep(0.02)
            
            # Add diagram success message if diagrams were processed
            if processed_outputs['diagrams']:
                diagram_message = f"\n\n🎨 I've generated {len(processed_outputs['diagrams'])} architecture diagram(s) for your design. You can view them on the canvas above."
                full_response += diagram_message
                
                # Stream the diagram notification
                for i in range(0, len(diagram_message), 5):
                    chunk = diagram_message[i:i+5]
                    yield {
                        "type": "content",
                        "content": chunk
                    }
                    await asyncio.sleep(0.02)
            
            # Update session with the complete response and processed outputs
            self.session_manager.update_session(conversation_id, message, full_response, tools_used)
            
            # Send final completion notification
            yield {
                "type": "complete",
                "message": "Response completed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error in streaming phase response: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def _ensure_services_initialized(self):
        """Ensure all services are initialized."""
        await self.claude_service.initialize()
        await self.mcp_service.initialize()
        

    
    async def _get_mcp_response(self, message: str, session: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> tuple[str, List[str]]:
        """Get response using MCP-enabled Claude."""
        messages = self._build_conversation_history(session, message)
        system_prompt = self.claude_service.build_system_prompt(self.mcp_service.get_available_tools())
        
        # Pass user_id to Claude service if available for tool execution context
        user_id = user_context.get('user_id') if user_context else None
        response = await self.claude_service.get_response(messages, system_prompt, user_id=user_id)
        return response, []
    
    async def _get_basic_response(self, message: str, session: Dict[str, Any]) -> tuple[str, List[str]]:
        """Get basic Claude response without MCP tools."""
        messages = self._build_conversation_history(session, message)
        system_prompt = "You are Claude, an AI assistant. Please provide helpful and accurate responses."
        response = await self.claude_service.get_response(messages, system_prompt)
        return response, []
    
    async def _get_phase_mcp_response(self, message: str, session: Dict[str, Any], phase: str, conversation_context: Optional[Dict[str, Any]] = None, user_context: Optional[Dict[str, Any]] = None) -> tuple[str, List[str]]:
        """Get phase-specific response using intelligent MCP tool selection."""
        messages = self._build_conversation_history(session, message)
        
        # Try to use enhanced Claude service with dynamic tool selection
        try:
            from services.enhanced_claude_service import EnhancedClaudeService
            from services.simple_tool_service import SimpleToolService
            
            self.logger.info(f"Attempting to use enhanced Claude service for phase: {phase}")
            
            # Initialize tool service if not already done
            if not hasattr(self, '_tool_service'):
                self._tool_service = SimpleToolService(self.mcp_service.get_mcp_client(), self.mcp_service)
                await self._tool_service.initialize()
            
            # Initialize enhanced Claude service if not already done
            if not hasattr(self, '_enhanced_claude_service'):
                self._enhanced_claude_service = EnhancedClaudeService(self._tool_service)
            
            self.logger.info(f"Calling enhanced Claude service with conversation context: {bool(conversation_context)}")
            
            # Get intelligent response with dynamic tool selection and conversation context
            response, tools_used = await self._enhanced_claude_service.get_intelligent_response(
                messages, phase, conversation_context, user_context
            )
            
            self.logger.info(f"Enhanced Claude service returned response of {len(response)} characters")
            return response, tools_used
            
        except Exception as e:
            self.logger.warning(f"Enhanced Claude service failed, falling back to basic MCP response: {e}")
            # Fallback to original implementation with conversation context
            system_prompt = self.claude_service.build_phase_system_prompt(phase, self.mcp_service.get_available_tools())
            
            # Inject conversation context into system prompt
            if conversation_context:
                context_prompt = self._build_context_prompt(conversation_context)
                system_prompt = f"{system_prompt}\n\n{context_prompt}"
            
            response = await self.claude_service.get_response(messages, system_prompt)
            return response, []
    

    async def _get_phase_basic_response(self, message: str, session: Dict[str, Any], phase: str, conversation_context: Optional[Dict[str, Any]] = None) -> tuple[str, List[str]]:
        """Get phase-specific basic response without MCP tools."""
        messages = self._build_conversation_history(session, message)
        system_prompt = self.claude_service.get_phase_context(phase)
        
        # Inject conversation context into system prompt
        if conversation_context:
            context_prompt = self._build_context_prompt(conversation_context)
            system_prompt = f"{system_prompt}\n\n{context_prompt}"
        
        response = await self.claude_service.get_response(messages, system_prompt)
        return response, []
    
    def _format_tool_results(self, tool_result: str) -> str:
        """Format tool results for better readability."""
        # Return tool results as-is since MCP tools now provide properly formatted output
        return f"\n\n📄 **Tool Result:**\n\n{tool_result}\n"
    
    def _build_context_prompt(self, conversation_context: Dict[str, Any]) -> str:
        """Build context prompt from conversation history."""
        if not conversation_context:
            return ""
        
        context_parts = []
        
        # Add project context summary if available
        if conversation_context.get("summary"):
            context_parts.append("## Project Context Summary")
            context_parts.append(conversation_context["summary"])
        
        # Add recent conversation context
        if conversation_context.get("messages"):
            context_parts.append("## Recent Conversation Context")
            for msg in conversation_context["messages"]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                context_parts.append(f"**{role.title()}** ({timestamp}): {content}")
        
        context_prompt = "\n\n".join(context_parts)
        return context_prompt
        if conversation_context.get("type") == "summarized":
            total_messages = conversation_context.get("total_messages", 0)
            context_parts.append(f"\n*Note: This project has {total_messages} total messages. Above is a summary plus the last 4 messages.*")
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def _build_conversation_history(self, session: Dict[str, Any], current_message: str) -> List[Dict[str, str]]:
        """Build conversation history for Claude."""
        conversation_history = []
        
        for msg_entry in session.get('messages', []):
            conversation_history.append({"role": "user", "content": msg_entry['user_message']})
            conversation_history.append({"role": "assistant", "content": msg_entry['ai_response']})
        
        conversation_history.append({"role": "user", "content": current_message})
        return conversation_history
    

    def _convert_diagrams_to_diagram_data(self, diagrams_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert output processor diagram dictionaries to DiagramData format."""
        converted_diagrams = []
        
        for diagram_dict in diagrams_list:
            # Convert to DiagramData format
            diagram_data = {
                'diagram_type': 'architecture',  # Default type
                'diagram_url': diagram_dict.get('local_url'),
                'diagram_data': None,  # We store in S3, not inline
                'diagram_metadata': {
                    'filename': diagram_dict.get('filename'),
                    'project_name': diagram_dict.get('project_name'),
                    'timestamp': diagram_dict.get('timestamp'),
                    'original_url': diagram_dict.get('original_url'),
                    'processed_by': 'output_processor'
                }
            }
            converted_diagrams.append(diagram_data)
        
        return converted_diagrams
    
    def _is_specification_generation_requested(self, message: str, phase: str) -> bool:
        """Check if the user is explicitly requesting specification generation."""
        message_lower = message.lower()
        
        # Keywords that indicate specification generation request
        spec_keywords = [
            'generate specification',
            'create specification',
            'generate spec',
            'create spec',
            'specification document',
            'spec document',
            'generate requirement spec',
            'create requirement spec',
            'generate requirements spec',
            'create requirements spec',
            'generate a spec',
            'create a spec',
            'make a spec',
            'build a spec',
            'write a spec',
            'produce a spec'
        ]
        
        # Phase-specific keywords
        phase_spec_keywords = [
            f'generate {phase} specification',
            f'create {phase} specification',
            f'generate {phase} spec',
            f'create {phase} spec',
            f'{phase} specification document',
            f'{phase} spec document'
        ]
        
        # Check for any specification generation keywords
        all_keywords = spec_keywords + phase_spec_keywords
        
        for keyword in all_keywords:
            if keyword in message_lower:
                return True
        
        return False

    def _create_error_response(self, message: str, conversation_id: str) -> Dict[str, Any]:
        """Create a standard error response."""
        return {
            'response': message,
            'conversation_id': conversation_id,
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'tools_used': []
        }
    
    def _create_phase_error_response(self, message: str, conversation_id: str) -> Dict[str, Any]:
        """Create a phase-specific error response."""
        return {
            'response': message,
            'conversation_id': conversation_id,
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'tools_used': [],
            'specification_updated': False,
            'specification': None,
            'processing_indicator': None,
            'canvas_posted': False,
            'diagrams': None
        }
    
    # Delegate methods to session manager
    def create_session(self, conversation_id: Optional[str] = None, phase: Optional[str] = None) -> str:
        """Create a new conversation session."""
        return self.session_manager.create_session(conversation_id, phase)
    
    def get_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation session."""
        return self.session_manager.get_session(conversation_id)
    
    def session_exists(self, conversation_id: str) -> bool:
        """Check if a session exists."""
        return self.session_manager.session_exists(conversation_id)
    
    def get_session_stats(self):
        """Get session statistics."""
        return self.session_manager.get_session_stats()
    
    def cleanup_sessions(self) -> int:
        """Clean up old sessions."""
        return self.session_manager.cleanup_sessions()
    
    # MCP service delegates
    def is_mcp_available(self) -> bool:
        """Check if MCP is available."""
        return self.mcp_service.is_available()
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP status."""
        return self.mcp_service.get_status()
    
    # Additional session manager delegates
    def get_phase_sessions(self, phase: str):
        """Get sessions for a specific phase."""
        return self.session_manager.get_phase_sessions(phase)
    
    def get_conversation_context(self, conversation_id: str):
        """Get conversation context."""
        return self.session_manager.get_conversation_context(conversation_id)
    
    def get_all_conversation_ids(self, phase: Optional[str] = None):
        """Get all conversation IDs."""
        return self.session_manager.get_all_conversation_ids(phase)
    
    def get_all_conversations_for_phase(self, phase: str):
        """Get all conversations for a phase."""
        return self.session_manager.get_all_conversations_for_phase(phase)
    

    

    
    def _generate_tool_status_message(self, tools_used):
        """Generate a user-friendly status message based on tools used."""
        if not tools_used:
            return None
        
        # Map tool names to user-friendly messages
        tool_messages = {
            'createJiraIssue': '🎫 Creating Jira tickets...',
            'searchJiraIssuesUsingJql': '🔍 Searching Jira tickets...',
            'create_architecture_diagram': '🎨 Generating architecture diagrams...',
            'generate_architecture_code': '⚙️ Generating infrastructure code...',
            'analyze_architecture': '🔍 Analyzing architecture...',
            'estimate_architecture_cost': '💰 Calculating cost estimates...',
            'query_aws_knowledge': '📚 Querying AWS knowledge base...',
            'domain_analysis': '📋 Performing domain analysis...',
            'generate_documentation': '📄 Generating documentation...',
            'generate_openapi_spec': '📋 Creating OpenAPI specification...',
            'mcp_amazon_q_business_retrieve': '🔍 Retrieving information from knowledge base...',
            'mcp_amazon_q_business_create': '📝 Creating content with knowledge base...',
            'getAccessibleAtlassianResources': '🔗 Accessing Atlassian resources...',
            'getVisibleJiraProjects': '📂 Loading Jira projects...',
            'getJiraIssue': '🎫 Fetching Jira issue details...',
        }
        
        # Get the first tool that has a message (prioritize user-facing tools)
        for tool in tools_used:
            if tool in tool_messages:
                return tool_messages[tool]
        
        # Fallback for unknown tools
        return f'🔧 Using {tools_used[0].replace("_", " ").title()}...'
    
    # Architecture analysis formatting removed - no longer used