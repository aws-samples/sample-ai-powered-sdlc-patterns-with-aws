"""
Simple Tool Service - Let the LLM decide which tools to use based on descriptions
"""

import logging
import json
import os
import secrets
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from mcp_client.client import MCPClient
from mcp_client.core.models import MCPRequest, MCPResponse
from .bedrock_kb_service import BedrockKBService, ProjectContext


class SimpleToolService:
    """
    Simple service that provides tool descriptions to the LLM and lets it decide which tools to use.
    No complex hardcoded logic - just tool discovery and execution.
    Drop-in replacement for DynamicToolService.
    """
    
    def __init__(self, mcp_client: Optional[MCPClient] = None, mcp_service=None):
        """Initialize the simple tool service."""
        self.mcp_client = mcp_client
        self.mcp_service = mcp_service
        self.logger = logging.getLogger(__name__)
        self.available_tools = {}
        self._active_requests = 0  # Track concurrent requests
        
        # Initialize Bedrock KB service
        self.kb_service = BedrockKBService()
        self._project_contexts = {}  # Cache for project contexts
    
    def set_cognito_id_token(self, id_token: str):
        """Set Cognito ID token for Amazon Q Business authentication."""
        if self.mcp_service:
            self.mcp_service.set_cognito_id_token(id_token)
            self.logger.info("Set Cognito ID token for Amazon Q Business")
        else:
            self.logger.warning("Cannot set ID token - MCP service not available")
        
        # Store ID token in MCP service instance (no environment variable)
        self.logger.info(f"Set ID token in MCP service: {len(id_token)} chars")
    
    def _get_tool_timeout(self, tool_name: str, server_id: str) -> float:
        """Get timeout for a specific tool and server combination."""
        # Amazon Q Business needs more time due to API Gateway + Lambda + Q Business processing
        if server_id in ["amazon-q-business", "amazon-q-business-prod"]:
            return 120.0  # 120 seconds (4 minutes - plenty of buffer for API Gateway + Lambda)
        
        # Code generation tools need more time
        if tool_name in ["generate_openapi_spec", "generate_documentation", "generate_architecture_code"]:
            return 240.0  # 4 minutes for complex code generation
        
        # Default timeout for other tools
        return 120.0  # 2 minutes default
        
    async def initialize(self):
        """Initialize the service by discovering available tools."""
        if self.mcp_client:
            await self._discover_available_tools()
            # Run schema discovery in background to avoid blocking streaming
            import asyncio
            asyncio.create_task(self._discover_tool_schemas_background())
    
    async def re_register_servers(self):
        """Re-register all MCP servers - useful after authentication changes."""
        try:
            self.logger.info("🔄 Re-registering MCP servers after authentication change...")
            
            # Clear existing tools to force fresh discovery
            old_tool_count = len(self.available_tools)
            self.available_tools.clear()
            self.logger.info(f"🧹 Cleared {old_tool_count} existing tools")
            
            # Re-discover tools from config
            await self._discover_available_tools()
            self.logger.info(f"🔍 Discovered {len(self.available_tools)} tools from config")
            
            # Re-register servers with MCP service if available
            if self.mcp_service:
                self.logger.info("🔗 Re-registering servers with MCP service...")
                # Force re-registration of all servers
                await self.mcp_service.re_register_all_servers()
                self.logger.info("✅ MCP service re-registration completed")
            else:
                self.logger.warning("⚠️ No MCP service available for re-registration")
            
            # Run schema discovery in background
            import asyncio
            asyncio.create_task(self._discover_tool_schemas_background())
            self.logger.info("🚀 Started background schema discovery")
            
            self.logger.info(f"✅ Successfully re-registered {len(self.available_tools)} tools")
            
            # Log available servers for debugging
            servers = set(tool['server_id'] for tool in self.available_tools.values())
            self.logger.info(f"📋 Available servers after re-registration: {sorted(servers)}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to re-register MCP servers: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    async def _discover_available_tools(self):
        """Discover all available MCP tools and their capabilities."""
        try:
            # Load tools from config since MCP client discovery is limited
            self._load_tools_from_config()
            self.logger.info(f"Discovered {len(self.available_tools)} tools")
            
        except Exception as e:
            self.logger.error(f"Failed to discover available tools: {e}")
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in the format ${VAR_NAME}."""
        import re
        import os
        
        def replace_var(match):
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value:
                self.logger.debug(f"Substituting ${{{var_name}}} with {value[:10]}...")
                return value
            else:
                self.logger.warning(f"Environment variable {var_name} not found")
                return match.group(0)  # Return original if not found
        
        # Use raw string pattern to match ${VAR_NAME}
        pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
        result = re.sub(pattern, replace_var, content)
        return result
    
    def _load_tools_from_config(self):
        """Load tools directly from ../mcp_servers.json file."""
        try:
            config_file = "../mcp_servers.json"
            if not os.path.exists(config_file):
                self.logger.warning(f"MCP config file {config_file} not found")
                return
            
            with open(config_file, 'r') as f:
                config_content = f.read()
                # Substitute environment variables
                config_content = self._substitute_env_vars(config_content)
                config = json.loads(config_content)
            
            # Use development environment by default
            environment = os.getenv('MCP_ENVIRONMENT', 'development')
            env_config = config.get("environments", {}).get(environment, {})
            servers = env_config.get("servers", [])
            
            self.logger.info(f"Loading tools from {environment} environment")
            self.logger.info(f"Found {len(servers)} servers in configuration")
            
            for server in servers:
                server_id = server.get("server_id", "")
                capabilities = server.get("capabilities", [])
                server_description = server.get("metadata", {}).get("description", f"{server_id} server")
                server_type = server.get("server_type", "tool")
                endpoint_url = server.get("endpoint_url", "")
                auth = server.get("auth", {})
                
                self.logger.info(f"Loading server: {server_id} with {len(capabilities)} capabilities: {capabilities}")
                
                # Store each capability as a tool with clear descriptions
                for capability in capabilities:
                    # Use a generic description initially - will be updated with actual description from MCP server
                    description = f"{capability.replace('_', ' ').title()} - {server_description}"
                    
                    self.available_tools[capability] = {
                        'name': capability,
                        'description': description,
                        'server_id': server_id,
                        'server_type': server_type,
                        'server_description': server_description,
                        'endpoint_url': endpoint_url,
                        'auth': auth,
                        'usage_count': 0,
                        'last_used': None
                    }
                    
            self.logger.info(f"Loaded {len(self.available_tools)} tools from ../mcp_servers.json")
            
            # Log all loaded servers for debugging
            loaded_servers = set(tool['server_id'] for tool in self.available_tools.values())
            self.logger.info(f"Successfully loaded servers: {sorted(loaded_servers)}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load tools from ../mcp_servers.json: {e}")
    
    async def _discover_tool_schemas(self):
        """Discover actual tool schemas using tools/list from each server."""
        if not self.mcp_client or not self.mcp_service:
            return
        
        self.logger.info("Discovering tool schemas from MCP servers...")
        
        # Get unique server IDs
        server_ids = set()
        for tool_info in self.available_tools.values():
            server_ids.add(tool_info['server_id'])
        
        for server_id in server_ids:
            try:
                # Ensure server is registered with timeout
                import asyncio
                try:
                    await asyncio.wait_for(
                        self.mcp_service.ensure_server_registered(server_id),
                        timeout=10.0  # 10 second timeout for server registration
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(f"Server registration for {server_id} timed out during schema discovery, skipping")
                    continue
                except Exception as e:
                    self.logger.warning(f"Server registration for {server_id} failed during schema discovery: {e}, skipping")
                    continue
                
                # Get tools list from this server with timeout
                request = MCPRequest(
                    request_type="tools/list",
                    content={"list_tools": True},  # Provide proper content for tools/list
                    required_capabilities=[],
                    preferred_server_id=server_id
                )
                
                response = await asyncio.wait_for(
                    self.mcp_client.send_request(request),
                    timeout=15.0  # 15 second timeout for tools/list request
                )
                
                if response and hasattr(response, 'status') and response.status.value == 'success':
                    tools_data = response.content
                    if 'tools' in tools_data:
                        # Track which tools were discovered from the server
                        discovered_tools = set()
                        for tool in tools_data['tools']:
                            tool_name = tool.get('name')
                            discovered_tools.add(tool_name)
                            schema = tool.get('inputSchema', {})
                            server_description = tool.get('description', '')
                            
                            if tool_name in self.available_tools:
                                # Update existing configured tool with server data
                                self.available_tools[tool_name]['schema'] = schema
                                if server_description:
                                    self.available_tools[tool_name]['description'] = server_description
                                    self.logger.info(f"Updated configured tool: {tool_name} with server data")
                                
                                # Debug: Log schema for Amazon Q Business tools
                                if 'amazon_q_business' in tool_name:
                                    self.logger.info(f"🔍 Amazon Q Business tool {tool_name} schema: {schema}")
                            else:
                                # Add newly discovered tool not in configuration
                                server_info = None
                                for existing_tool in self.available_tools.values():
                                    if existing_tool['server_id'] == server_id:
                                        server_info = existing_tool
                                        break
                                
                                if server_info:
                                    self.available_tools[tool_name] = {
                                        'name': tool_name,
                                        'description': server_description or f"{tool_name.replace('_', ' ').title()} - {server_info['server_description']}",
                                        'server_id': server_id,
                                        'server_type': server_info['server_type'],
                                        'server_description': server_info['server_description'],
                                        'endpoint_url': server_info['endpoint_url'],
                                        'auth': server_info['auth'],
                                        'schema': schema,
                                        'usage_count': 0,
                                        'last_used': None,
                                        'discovered_dynamically': True  # Mark as dynamically discovered
                                    }
                                    self.logger.info(f"Dynamically discovered new tool: {tool_name} from server {server_id}")
                            
                            # Log the actual schema for debugging
                            if schema and 'properties' in schema:
                                params = list(schema['properties'].keys())
                                self.logger.info(f"Updated schema for tool: {tool_name} - Parameters: {params}")
                            else:
                                self.logger.info(f"Updated schema for tool: {tool_name} - No parameters found")
                        
                        # For tools in configuration but not discovered, add basic schema
                        for tool_name, tool_info in self.available_tools.items():
                            if tool_info['server_id'] == server_id and tool_name not in discovered_tools:
                                # Add basic schema for configured tools not discovered
                                if 'schema' not in tool_info:
                                    tool_info['schema'] = {
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                self.logger.info(f"Tool {tool_name} configured but not discovered from server {server_id} - using basic schema")
                    else:
                        # If no tools were discovered at all, add basic schemas for all configured tools
                        for tool_name, tool_info in self.available_tools.items():
                            if tool_info['server_id'] == server_id:
                                if 'schema' not in tool_info:
                                    tool_info['schema'] = {
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                self.logger.info(f"No tools discovered from server {server_id}, using basic schema for configured tool: {tool_name}")
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout getting tool schemas from server {server_id}, skipping")
            except Exception as e:
                self.logger.warning(f"Failed to get tool schemas from server {server_id}: {e}")
        
        # Log summary of discovered tools
        configured_tools = [name for name, info in self.available_tools.items() if not info.get('discovered_dynamically', False)]
        dynamic_tools = [name for name, info in self.available_tools.items() if info.get('discovered_dynamically', False)]
        
        self.logger.info(f"Tool discovery completed - Total: {len(self.available_tools)} tools")
        self.logger.info(f"  - Configured tools: {len(configured_tools)} {configured_tools}")
        self.logger.info(f"  - Dynamically discovered: {len(dynamic_tools)} {dynamic_tools}")
        
        # Update server capabilities in MCP client registry with discovered tools
        await self._update_server_capabilities_with_discovered_tools()
    
    async def _discover_tool_schemas_background(self):
        """Discover tool schemas in background to avoid blocking streaming responses."""
        try:
            self.logger.info("Starting background tool schema discovery...")
            await self._discover_tool_schemas()
            self.logger.info("Background tool schema discovery completed")
        except Exception as e:
            self.logger.error(f"Background tool schema discovery failed: {e}")
            # Don't let this failure affect the main application

    async def _update_server_capabilities_with_discovered_tools(self):
        """Update MCP server capabilities with dynamically discovered tools."""
        if not self.mcp_service:
            return
            
        # Group tools by server
        server_tools = {}
        for tool_name, tool_info in self.available_tools.items():
            server_id = tool_info['server_id']
            if server_id not in server_tools:
                server_tools[server_id] = []
            server_tools[server_id].append(tool_name)
        
        # Update each server's capabilities
        for server_id, tools in server_tools.items():
            try:
                # Get the server configuration
                if hasattr(self.mcp_service, '_server_configs') and server_id in self.mcp_service._server_configs:
                    server_config = self.mcp_service._server_configs[server_id]
                    
                    # Update capabilities with all discovered tools
                    original_capabilities = len(server_config.capabilities)
                    server_config.capabilities = tools
                    
                    self.logger.info(f"Updated server {server_id} capabilities: {original_capabilities} → {len(tools)} tools")
                    self.logger.debug(f"  New capabilities: {tools}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to update capabilities for server {server_id}: {e}")

    def get_tools_for_llm(self) -> str:
        """
        Generate tool descriptions for the LLM to make intelligent tool selection decisions.
        Similar to the reference chatbot approach - let Claude decide what to use.
        """
        if not self.available_tools:
            return "No external tools are currently available."
        
        # Build system prompt similar to the reference code
        tools_description = """You have access to the following MCP servers and their capabilities:

"""
        
        # Group tools by server for better organization (like the reference code)
        servers = {}
        for tool_name, tool_info in self.available_tools.items():
            server_id = tool_info['server_id']
            if server_id not in servers:
                servers[server_id] = {
                    'server_type': tool_info['server_type'],
                    'server_description': tool_info['server_description'],
                    'capabilities': []
                }
            servers[server_id]['capabilities'].append((tool_name, tool_info['description']))
        
        # Format with actual tool schemas and parameters
        for server_id, info in servers.items():
            tools_description += f"**{server_id}** ({info['server_type']}):\n"
            tools_description += f"- Description: {info['server_description']}\n"
            tools_description += f"- Available capabilities:\n"
            for tool_name, description in info['capabilities']:
                tools_description += f"  • {tool_name}: {description}\n"
                
                # Add parameter information if available
                if tool_name in self.available_tools:
                    tool_info = self.available_tools[tool_name]
                    schema = tool_info.get('schema', {})
                    if schema and 'properties' in schema:
                        tools_description += f"    Required Parameters:\n"
                        required_params = schema.get('required', [])
                        
                        # Show required parameters first and prominently
                        if required_params:
                            tools_description += f"    🚨 REQUIRED Parameters (MUST include ALL of these):\n"
                            for param_name in required_params:
                                if param_name in schema['properties']:
                                    param_info = schema['properties'][param_name]
                                    param_type = param_info.get('type', 'string')
                                    param_desc = param_info.get('description', '')
                                    tools_description += f"      - {param_name}: {param_type}\n"
                                    if param_desc:
                                        tools_description += f"        {param_desc}\n"
                        
                        # Show optional parameters
                        optional_params = [p for p in schema['properties'].keys() if p not in required_params]
                        if optional_params:
                            tools_description += f"    📝 Optional Parameters:\n"
                            for param_name in optional_params:
                                param_info = schema['properties'][param_name]
                                param_type = param_info.get('type', 'string')
                                param_desc = param_info.get('description', '')
                                tools_description += f"      - {param_name}: {param_type}\n"
                                if param_desc:
                                    tools_description += f"        {param_desc}\n"
                
            tools_description += f"- Server ID: {server_id}\n\n"
        
        tools_description += """
CRITICAL TOOL USAGE RULES:

When you need to use a tool, you MUST respond with ONLY the tool call and NO other text:

TOOL_CALL: {"server_id": "server-name", "capability": "capability-name", "tool_name": "capability-name", "arguments": {...}}

ABSOLUTELY NO explanatory text before or after the TOOL_CALL!

Examples of CORRECT responses:
TOOL_CALL: {"server_id": "amazon-q-business", "capability": "mcp_amazon_q_business_retrieve", "tool_name": "mcp_amazon_q_business_retrieve", "arguments": {"message": "extract confluence content"}}

🚨 CRITICAL PARAMETER RULES:

1. ALWAYS include ALL parameters marked with 🚨 REQUIRED - the tool will fail without them
2. Use EXACT parameter names from the schema (case-sensitive)
3. Follow the parameter types (string, number, boolean, object, array)
4. Optional parameters (📝) can be included or omitted
5. DO NOT make up parameter names - use ONLY what's shown in the schema above

EXAMPLES of CORRECT tool calls:

For architecture diagrams:
TOOL_CALL: {"server_id": "aws-architecture-design", "capability": "create_architecture_diagram", "tool_name": "create_architecture_diagram", "arguments": {"description": "E-commerce platform architecture", "components": ["Web App", "Database", "API Gateway"], "style": "aws-icons"}}

For OpenAPI specs (with required parameters):
TOOL_CALL: {"server_id": "domain-analysis-tools", "capability": "generate_openapi_spec", "tool_name": "generate_openapi_spec", "arguments": {"info": {"title": "API Title", "version": "1.0.0"}, "servers": [], "paths": {}, "components": {}}}

CRITICAL JSON FORMATTING RULES:
- Use proper commas between array elements: ["item1", "item2", "item3"]
- Use double quotes for all strings
- No trailing commas
- Properly escape quotes inside strings

Examples of WRONG responses (DO NOT DO THIS):
"I will use the tool to help you:
TOOL_CALL: {...}
This will extract the information you need."

TOOL USAGE GUIDELINES:

CORRECT tool call examples are shown above based on available servers.

REMEMBER: 
- For Confluence content extraction: use "mcp_amazon_q_business_retrieve"
- For VISUAL DIAGRAMS (architecture, system, component diagrams): use "create_architecture_diagram" from "aws-architecture-design" server
- For API specifications (OpenAPI/Swagger): use "generate_openapi_spec" from "domain-analysis-tools" server
- The tool will execute automatically and you'll get results to provide a complete answer
- ONLY the TOOL_CALL line, nothing else!
"""
        
        return tools_description
    
    def parse_tool_calls(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM response for multiple tool call requests."""
        if "TOOL_CALL:" not in llm_response:
            self.logger.debug("No TOOL_CALL found in response")
            return []
        
        self.logger.info(f"TOOL_CALL found in response, attempting to parse multiple calls...")
        
        tool_calls = []
        search_start = 0
        
        while True:
            # Find the next TOOL_CALL
            tool_call_pos = llm_response.find("TOOL_CALL:", search_start)
            if tool_call_pos == -1:
                break
                
            try:
                tool_call_start = tool_call_pos + len("TOOL_CALL:")
                
                # Find the opening brace
                brace_start = llm_response.find("{", tool_call_start)
                if brace_start == -1:
                    self.logger.warning("No opening brace found after TOOL_CALL:")
                    search_start = tool_call_pos + 1
                    continue
                
                # Find the matching closing brace
                brace_count = 0
                brace_end = brace_start
                for i, char in enumerate(llm_response[brace_start:], brace_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            brace_end = i + 1
                            break
                
                if brace_count != 0:
                    self.logger.warning("Unmatched braces in tool call")
                    search_start = tool_call_pos + 1
                    continue
                
                tool_call_json = llm_response[brace_start:brace_end].strip()
                self.logger.info(f"Extracted tool call JSON: {tool_call_json}")
                
                # Parse the tool call
                tool_call = self._parse_single_tool_call(tool_call_json)
                if tool_call:
                    tool_calls.append(tool_call)
                
                search_start = brace_end
                
            except Exception as e:
                self.logger.error(f"Error parsing tool call: {e}")
                search_start = tool_call_pos + 1
                continue
        
        self.logger.info(f"Found {len(tool_calls)} tool calls")
        return tool_calls

    def parse_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response for tool call requests - robust parsing that handles extra text."""
        tool_calls = self.parse_tool_calls(llm_response)
        return tool_calls[0] if tool_calls else None
    
    def _parse_single_tool_call(self, tool_call_json: str) -> Optional[Dict[str, Any]]:
        """Parse a single tool call JSON string."""
        try:
            # Clean up the JSON to handle control characters and common formatting issues
            import re
            
            # First, handle newlines and whitespace in arrays properly
            # Remove newlines and extra whitespace between array elements
            tool_call_json = re.sub(r',\s*\n\s*"', ', "', tool_call_json)
            tool_call_json = re.sub(r'"\s*,\s*\n\s*"', '", "', tool_call_json)
            tool_call_json = re.sub(r'\[\s*\n\s*"', '["', tool_call_json)
            tool_call_json = re.sub(r'"\s*\n\s*\]', '"]', tool_call_json)
            
            # Replace remaining literal newlines with spaces (not escaped newlines)
            tool_call_json = tool_call_json.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            
            # Clean up multiple spaces
            tool_call_json = re.sub(r'\s+', ' ', tool_call_json)
            
            # Fix common JSON formatting issues
            # Fix pattern: "text"]["text" -> "text","text"
            tool_call_json = re.sub(r'"\]\s*\[', '","', tool_call_json)
            # Fix pattern: "text""text" -> "text","text"  
            tool_call_json = re.sub(r'"\s*"', '","', tool_call_json)
            
            try:
                tool_call = json.loads(tool_call_json)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Initial JSON parse failed: {e}")
                self.logger.info("Attempting to fix common JSON formatting issues...")
                
                # More aggressive JSON fixing
                fixed_json = tool_call_json
                
                # Fix array formatting issues more aggressively
                # Remove all newlines and normalize whitespace in arrays
                fixed_json = re.sub(r'\[\s*\n\s*', '[', fixed_json)
                fixed_json = re.sub(r'\s*\n\s*\]', ']', fixed_json)
                fixed_json = re.sub(r'",\s*\n\s*"', '", "', fixed_json)
                fixed_json = re.sub(r'"\s*\n\s*"', '", "', fixed_json)
                
                # Remove all remaining newlines and normalize spaces
                fixed_json = re.sub(r'\s*\n\s*', ' ', fixed_json)
                fixed_json = re.sub(r'\s+', ' ', fixed_json)
                
                # Fix missing commas between array elements
                fixed_json = re.sub(r'"\s+"', '", "', fixed_json)
                fixed_json = re.sub(r'"\s*"', '", "', fixed_json)
                
                try:
                    tool_call = json.loads(fixed_json)
                    self.logger.info("Successfully fixed JSON formatting")
                except json.JSONDecodeError as e2:
                    self.logger.error(f"Could not fix JSON: {e2}")
                    self.logger.error(f"Original JSON: {tool_call_json}")
                    self.logger.error(f"Fixed attempt: {fixed_json}")
                    return None
            
            # Validate required fields
            required_fields = ["server_id", "capability", "tool_name", "arguments"]
            if not all(field in tool_call for field in required_fields):
                self.logger.warning(f"Tool call missing required fields: {tool_call}")
                return None
            
            # Validate tool exists
            if tool_call["tool_name"] not in self.available_tools:
                self.logger.warning(f"Unknown tool: {tool_call['tool_name']}")
                self.logger.info(f"Available tools: {list(self.available_tools.keys())}")
                return None
            
            # Validate server matches
            tool_info = self.available_tools[tool_call["tool_name"]]
            if tool_info['server_id'] != tool_call["server_id"]:
                self.logger.warning(f"Server mismatch for tool {tool_call['tool_name']}: expected {tool_info['server_id']}, got {tool_call['server_id']}")
                return None
            
            self.logger.info(f"Successfully parsed tool call: {tool_call['tool_name']}")
            return tool_call
            
        except Exception as e:
            self.logger.error(f"Error parsing single tool call: {e}")
            return None
            import re
            
            # First, handle newlines and whitespace in arrays properly
            # Remove newlines and extra whitespace between array elements
            tool_call_json = re.sub(r',\s*\n\s*"', ', "', tool_call_json)
            tool_call_json = re.sub(r'"\s*,\s*\n\s*"', '", "', tool_call_json)
            tool_call_json = re.sub(r'\[\s*\n\s*"', '["', tool_call_json)
            tool_call_json = re.sub(r'"\s*\n\s*\]', '"]', tool_call_json)
            
            # Replace remaining literal newlines with spaces (not escaped newlines)
            tool_call_json = tool_call_json.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            
            # Clean up multiple spaces
            tool_call_json = re.sub(r'\s+', ' ', tool_call_json)
            
            # Fix common JSON formatting issues
            # Fix pattern: "text"]["text" -> "text","text"
            tool_call_json = re.sub(r'"\]\s*\[', '","', tool_call_json)
            # Fix pattern: "text""text" -> "text","text"  
            tool_call_json = re.sub(r'"\s*"', '","', tool_call_json)
            
            try:
                tool_call = json.loads(tool_call_json)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Initial JSON parse failed: {e}")
                self.logger.info("Attempting to fix common JSON formatting issues...")
                
                # More aggressive JSON fixing
                fixed_json = tool_call_json
                
                # Fix array formatting issues more aggressively
                # Remove all newlines and normalize whitespace in arrays
                fixed_json = re.sub(r'\[\s*\n\s*', '[', fixed_json)
                fixed_json = re.sub(r'\s*\n\s*\]', ']', fixed_json)
                fixed_json = re.sub(r'",\s*\n\s*"', '", "', fixed_json)
                fixed_json = re.sub(r'"\s*\n\s*"', '", "', fixed_json)
                
                # Remove all remaining newlines and normalize spaces
                fixed_json = re.sub(r'\s*\n\s*', ' ', fixed_json)
                fixed_json = re.sub(r'\s+', ' ', fixed_json)
                
                # Fix missing commas between array elements
                fixed_json = re.sub(r'"\s+"', '", "', fixed_json)
                fixed_json = re.sub(r'"\s*"', '", "', fixed_json)
                
                try:
                    tool_call = json.loads(fixed_json)
                    self.logger.info("Successfully fixed JSON formatting")
                except json.JSONDecodeError as e2:
                    self.logger.error(f"Could not fix JSON: {e2}")
                    self.logger.error(f"Original JSON: {tool_call_json}")
                    self.logger.error(f"Fixed attempt: {fixed_json}")
                    
                    # Last resort: try to manually reconstruct the JSON
                    try:
                        self.logger.info("Attempting manual JSON reconstruction...")
                        # This is a very basic fallback - extract key components
                        server_match = re.search(r'"server_id":\s*"([^"]+)"', tool_call_json)
                        capability_match = re.search(r'"capability":\s*"([^"]+)"', tool_call_json)
                        tool_match = re.search(r'"tool_name":\s*"([^"]+)"', tool_call_json)
                        
                        if server_match and capability_match and tool_match:
                            # Create a minimal valid JSON structure
                            fallback_json = {
                                "server_id": server_match.group(1),
                                "capability": capability_match.group(1),
                                "tool_name": tool_match.group(1),
                                "arguments": {"description": "Architecture diagram", "components": [], "style": "aws-icons"}
                            }
                            tool_call = fallback_json
                            self.logger.info("Successfully created fallback JSON structure")
                        else:
                            raise e2
                    except Exception as e3:
                        self.logger.error(f"Manual reconstruction failed: {e3}")
                        raise e2
            
            # Validate required fields
            required_fields = ["server_id", "capability", "tool_name", "arguments"]
            if not all(field in tool_call for field in required_fields):
                self.logger.warning(f"Tool call missing required fields: {tool_call}")
                return None
            
            # Validate tool exists
            if tool_call["tool_name"] not in self.available_tools:
                self.logger.warning(f"Unknown tool: {tool_call['tool_name']}")
                self.logger.info(f"Available tools: {list(self.available_tools.keys())}")
                return None
            
            # Validate server matches
            tool_info = self.available_tools[tool_call["tool_name"]]
            if tool_info['server_id'] != tool_call["server_id"]:
                self.logger.warning(f"Server mismatch for tool {tool_call['tool_name']}: expected {tool_info['server_id']}, got {tool_call['server_id']}")
                return None
            
            self.logger.info(f"Successfully parsed tool call: {tool_call['tool_name']}")
            return tool_call
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Failed to parse tool call: {e}")
            return None

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], user_id: Optional[str] = None, jwt_token: Optional[str] = None) -> Tuple[Optional[str], bool]:
        """
        Execute a specific tool with given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            user_id: User ID for authentication context
            
        Returns:
            Tuple of (response, success)
        """
        if not self.mcp_client or tool_name not in self.available_tools:
            return None, False
        
        # Retry logic for ConflictException (concurrent requests)
        max_retries = 5
        base_delay = 2.0  # seconds
        
        for attempt in range(max_retries + 1):
            try:
                tool_info = self.available_tools[tool_name]
                server_id = tool_info['server_id']
                
                # Atlassian authentication will be implemented later
                
                # Jira authentication will be implemented later
                
                if attempt == 0:
                    self.logger.info(f"🚀 STARTING tool execution: {tool_name} with args: {arguments}")
                else:
                    self.logger.info(f"🔄 RETRYING tool execution (attempt {attempt + 1}/{max_retries + 1}): {tool_name}")
                
                # Log request timing and track concurrent requests
                import time
                start_time = time.time()
                self._active_requests += 1
                self.logger.info(f"📊 Active concurrent requests: {self._active_requests}")
                
                # Ensure the server is registered before executing the tool
                if self.mcp_service:
                    import asyncio
                    try:
                        # Add timeout to prevent hanging on server registration
                        registration_success = await asyncio.wait_for(
                            self.mcp_service.ensure_server_registered(server_id), 
                            timeout=10.0  # 10 second timeout
                        )
                        if not registration_success:
                            self.logger.warning(f"Failed to register server {server_id}, but continuing anyway")
                            # Don't return failure - try to execute anyway
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Server registration for {server_id} timed out after 10s, continuing anyway")
                        # Don't return failure - try to execute anyway
                    except Exception as e:
                        self.logger.warning(f"Server registration for {server_id} failed: {e}, continuing anyway")
                        # Don't return failure - try to execute anyway
                
                # Create and send request
                request = MCPRequest(
                    request_type="tools/call",
                    content={
                        "name": tool_name,
                        "arguments": arguments
                    },
                    required_capabilities=[tool_name],
                    preferred_server_id=server_id
                )
                
                # Set ID token for Amazon Q Business requests
                if jwt_token and self.mcp_service:
                    self.mcp_service.set_cognito_id_token(jwt_token)
                    # JWT token is now stored in MCP service instance
                    self.logger.info(f"Using ID token for tool execution: {tool_name} - {jwt_token[:30]}...")
                elif not jwt_token:
                    self.logger.warning(f"No ID token provided for tool execution: {tool_name}")
                elif not self.mcp_service:
                    self.logger.warning(f"No MCP service available for ID token setting: {tool_name}")
                
                # Add Cognito JWT token for Amazon Q Business requests
                if server_id in ["amazon-q-business", "amazon-q-business-prod"]:
                    # Use provided ID token or get from MCP service
                    token_to_use = jwt_token or (self.mcp_service.get_cognito_id_token() if self.mcp_service else None)
                    
                    if token_to_use:
                        # Set headers that will be passed to the HTTP transport
                        request.headers = {
                            "X-Cognito-JWT": token_to_use,
                            "Content-Type": "application/json"
                        }
                        # JWT token is passed directly in request headers
                        self.logger.info(f"🔐 Using Cognito JWT token for Amazon Q Business request")
                        self.logger.info(f"🔐 JWT token length: {len(token_to_use)} chars, starts with: {token_to_use[:50]}...")
                    else:
                        self.logger.info(f"ℹ️ No Cognito JWT token provided for Amazon Q Business request")
                        self.logger.info(f"ℹ️ This is expected if not using Amazon Q Business features")
                
                # Log the exact request being sent
                self.logger.info(f"📤 SENDING request to MCP server: {server_id}")
                self.logger.info(f"🔍 EXACT REQUEST DETAILS:")
                self.logger.info(f"   - Tool Name: {tool_name}")
                self.logger.info(f"   - Server ID: {server_id}")
                self.logger.info(f"   - Request Type: {request.request_type}")
                self.logger.info(f"   - Arguments: {json.dumps(arguments, indent=2)}")
                self.logger.info(f"   - Full Request Content: {json.dumps(request.content, indent=2)}")
                
                # Add timeout to prevent hanging on tool execution
                # Use configured timeout for this specific tool
                import asyncio
                tool_timeout = self._get_tool_timeout(tool_name, server_id)
                
                # For Amazon Q Business, use the JWT-aware method
                if server_id in ["amazon-q-business", "amazon-q-business-prod"] and self.mcp_service:
                    # Convert MCPRequest to dict format expected by send_request_with_jwt
                    request_data = {
                        "method": request.request_type,
                        "params": request.content
                    }
                    response = await asyncio.wait_for(
                        self.mcp_service.send_request_with_jwt(request_data, server_id),
                        timeout=tool_timeout
                    )
                else:
                    response = await asyncio.wait_for(
                        self.mcp_client.send_request(request),
                        timeout=tool_timeout
                    )
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Log the exact response received
                self.logger.info(f"📥 RECEIVED response from MCP server:")
                if response:
                    self.logger.info(f"   - Response Status: {getattr(response, 'status', 'NO_STATUS')}")
                    self.logger.info(f"   - Response Content Type: {type(response.content) if hasattr(response, 'content') else 'NO_CONTENT'}")
                    if hasattr(response, 'content'):
                        # Don't log full content for large responses to avoid log spam, except for debugging specific tools
                        if tool_name in ['generate_openapi_spec', 'generate_documentation', 'generate_architecture_code']:
                            content_str = json.dumps(response.content, indent=2) if response.content else 'EMPTY_CONTENT'
                            self.logger.info(f"   - Response Content Length: {len(content_str)} characters")
                            # Only log first 1000 chars for debugging, but preserve full content in processing
                            self.logger.debug(f"   - Response Content Preview: {content_str[:1000]}{'...' if len(content_str) > 1000 else ''}")
                        else:
                            self.logger.info(f"   - Response Content: {json.dumps(response.content, indent=2) if response.content else 'EMPTY_CONTENT'}")
                else:
                    self.logger.info(f"   - Response: NULL/NONE")
                
                if response and hasattr(response, 'status') and response.status.value == 'success':
                    self._active_requests -= 1
                    self.logger.info(f"✅ SUCCESS: Tool {tool_name} completed in {duration:.2f}s (remaining active: {self._active_requests})")
                    tool_result = self._process_tool_response(tool_name, response)
                    # Don't truncate logging for OpenAPI specs and other code generation tools
                    if tool_name in ['generate_openapi_spec', 'generate_documentation', 'generate_architecture_code']:
                        self.logger.info(f"🔄 PROCESSED {tool_name} result: {len(tool_result) if tool_result else 0} characters - preserving full content")
                    else:
                        self.logger.info(f"🔄 PROCESSED tool result: {tool_result[:200] if tool_result else 'NULL'}...")
                    self._update_tool_usage(tool_name, success=True)
                    if attempt > 0:
                        self.logger.info(f"Tool execution succeeded on retry attempt {attempt + 1}")
                    return tool_result, True
                else:
                    self._active_requests -= 1
                    self.logger.warning(f"❌ FAILED: Tool {tool_name} execution failed (remaining active: {self._active_requests})")
                    self._update_tool_usage(tool_name, success=False)
                    return None, False
                    
            except asyncio.TimeoutError:
                end_time = time.time()
                duration = end_time - start_time
                self._active_requests -= 1
                
                if duration > 15:  # Tool execution timeout (vs server registration timeout)
                    tool_timeout = self._get_tool_timeout(tool_name, server_id)
                    self.logger.error(f"⏰ TIMEOUT: Tool {tool_name} execution timed out after {duration:.2f}s (configured timeout: {tool_timeout}s) (remaining active: {self._active_requests})")
                    timeout_message = (
                        f"⏰ **Tool Execution l took too long to respond (>{duration:.0f}s). "
                        f"This might be due to:\n"
                        f"- Server connectivity issues\n"
                        f"- Heavy server load\n"
                        f"- Authentication problems\n\n"
                        f"Please try again in a moment."
                    )
                    return timeout_message, False
                else:  # Server registration timeout
                    self.logger.error(f"⏰ TIMEOUT: Server registration for {tool_name} timed out after {duration:.2f}s (remaining active: {self._active_requests})")
                    return "Server registration timed out. Please try again.", False
                    
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                error_msg = str(e)
                
                self.logger.error(f"❌ ERROR after {duration:.2f}s: {error_msg}")
                
                # Check if it's a ConflictException (concurrent request)
                if ("ConflictException" in error_msg or 
                    "conflicts with another ongoing request" in error_msg or
                    "ChatSync operation" in error_msg):
                    if attempt < max_retries:
                        # Calculate exponential backoff delay with cryptographically secure jitter
                        jitter = 0.1 + (secrets.randbelow(400) / 1000.0)  # 0.1 to 0.5 range
                        delay = base_delay * (2 ** attempt) + jitter
                        self.logger.warning(f"⏳ ConflictException on attempt {attempt + 1}, retrying in {delay:.1f}s: {error_msg}")
                        
                        # Import asyncio for sleep
                        import asyncio
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self._active_requests -= 1
                        self.logger.error(f"💥 ConflictException persisted after {max_retries} retries (remaining active: {self._active_requests}): {error_msg}")
                        self._update_tool_usage(tool_name, success=False)
                        return "The Jira system is currently busy with concurrent requests. I've tried multiple times but the system is overloaded. Please wait a few minutes and try again, or try creating the Jira ticket manually.", False
                else:
                    # Check if it's an Atlassian authentication error
                    if (server_id == "atlassian-remote" and 
                        ("health check timed out" in error_msg or 
                         "timeout" in error_msg.lower() or
                         "connection refused" in error_msg.lower() or
                         "unavailable" in error_msg.lower())):
                        
                        self._active_requests -= 1
                        self.logger.warning(f"🔐 Atlassian authentication required (remaining active: {self._active_requests}): {error_msg}")
                        self._update_tool_usage(tool_name, success=False)
                        
                        # Return a helpful message with authentication link
                        auth_message = (
                            "🔐 **Atlassian Authentication Required**\n\n"
                            "The Atlassian integration is not currently authenticated or the connection has timed out. "
                            "To use Jira and Confluence tools, please:\n\n"
                            "1. Go to the **Jira Integration** page\n"
                            "2. Click **Connect to Atlassian** to authenticate\n"
                            "3. Complete the OAuth flow in the popup window\n"
                            "4. Return here and try your request again\n\n"
                            "Once authenticated, you'll be able to create Jira tickets, search issues, and access Confluence content."
                        )
                        return auth_message, False
                    # Check if it's a SigV4 credentials error
                    elif ("Failed to get credentials from SigV4" in error_msg or 
                          "SigV4 request context" in error_msg):
                        
                        self._active_requests -= 1
                        self.logger.warning(f"🔐 AWS SigV4 authentication error (remaining active: {self._active_requests}): {error_msg}")
                        self._update_tool_usage(tool_name, success=False)
                        
                        # Return a helpful message asking user to log out and log back in
                        auth_message = (
                            "🔐 **Authentication Error - Please Log Out and Log Back In**\n\n"
                            "AWS authentication credentials expired "
                            "Please log out of the application and log back in to refresh your session.\n\n"
                            "This will resolve the authentication issue and allow you to use the tools again."
                        )
                        return auth_message, False
                    else:
                        # Non-conflict, non-auth error, don't retry
                        self._active_requests -= 1
                        self.logger.error(f"💥 Non-retryable error (remaining active: {self._active_requests}): {e}")
                        self._update_tool_usage(tool_name, success=False)
                        return None, False
        
        # Should not reach here, but just in case
        return None, False
    
    def _is_jira_tool(self, tool_name: str) -> bool:
        """Check if a tool is Jira-related and needs authentication."""
        jira_tools = [
            'mcp_amazon_q_business_action',
            'mcp_amazon_q_business_jira_tool'
        ]
        return tool_name in jira_tools
    
    # Jira authentication methods removed - will be implemented later
    
    def _process_tool_response(self, tool_name: str, response: MCPResponse) -> Optional[str]:
        """Process tool response into human-readable format."""
        try:
            if not hasattr(response, 'content') or not response.content:
                return None
            
            content = response.content
            
            # Handle different response formats
            if isinstance(content, dict):
                # Enhanced MCP format: {"content": [{"type": "text", "text": "..."}]}
                if 'content' in content and isinstance(content['content'], list):
                    # Extract text from nested content structure
                    text_parts = []
                    for item in content['content']:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                    result = '\n'.join(text_parts) if text_parts else None
                
                # Standard MCP format: {"result": "...", "status": "success"}
                elif 'result' in content:
                    result = str(content['result'])
                elif 'analysis' in content:
                    result = str(content['analysis'])
                # Handle direct response format: {"response": "..."}
                elif 'response' in content:
                    result = str(content['response'])
                # Handle message format: {"message": "..."}
                elif 'message' in content:
                    result = str(content['message'])
                # Handle data format: {"data": "..."}
                elif 'data' in content:
                    result = str(content['data'])
                else:
                    # For standard MCP responses, the content itself might be the result
                    result = str(content)
            
            elif isinstance(content, str):
                result = content
            else:
                result = str(content)
            
            # Handle authentication-related responses for Jira tools
            if self._is_jira_tool(tool_name) and result:
                if "Requesting authorization for plugin" in result:
                    return "I need to authenticate with Jira to create tickets. Please set up Jira OAuth authentication first. You can do this by:\n\n1. Going to the OAuth settings in your application\n2. Completing the Jira authentication flow\n3. Once authenticated, I'll be able to create Jira tickets for you automatically.\n\nFor now, I can help you plan what the Jira ticket should contain, or assist with other tasks that don't require Jira integration."
                elif "AUTH_REQUIRED" in result:
                    return "Jira authentication is required to create tickets. Please complete the OAuth flow first, then I'll be able to create Jira tickets automatically."
                
                # Handle successful Jira ticket creation - don't show raw JSON
                if tool_name == 'createJiraIssue' and result and result.startswith('{"id":'):
                    try:
                        import json
                        ticket_data = json.loads(result)
                        ticket_key = ticket_data.get('key', 'Unknown')
                        return f"✅ Successfully created Jira ticket {ticket_key}"
                    except (json.JSONDecodeError, KeyError):
                        return "✅ Jira ticket created successfully"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {tool_name} response: {e}")
            return None
    
    def _update_tool_usage(self, tool_name: str, success: bool):
        """Update tool usage statistics."""
        if tool_name in self.available_tools:
            tool_info = self.available_tools[tool_name]
            tool_info['usage_count'] += 1
            tool_info['last_used'] = datetime.utcnow().isoformat()
    
    async def process_with_tools(self, user_message: str, llm_response: str, jwt_token: Optional[str] = None) -> Tuple[Optional[str], List[str]]:
        """
        Process LLM response and execute any requested tools.
        
        Args:
            user_message: Original user message
            llm_response: LLM's response (may contain tool calls)
            
        Returns:
            Tuple of (tool_response, tools_used)
        """
        tool_call = self.parse_tool_call(llm_response)
        if not tool_call:
            return None, []
        
        tool_name = tool_call["tool_name"]
        arguments = tool_call["arguments"]
        server_id = tool_call["server_id"]
        
        self.logger.info(f"Executing tool: {tool_name} from server: {server_id}")
        
        # Validate and filter arguments based on tool schema
        if tool_name in self.available_tools:
            tool_info = self.available_tools[tool_name]
            schema = tool_info.get('schema', {})
            if schema and 'properties' in schema:
                valid_params = set(schema['properties'].keys())
                provided_params = set(arguments.keys())
                invalid_params = provided_params - valid_params
                
                if invalid_params:
                    self.logger.warning(f"🚨 Tool {tool_name} received invalid parameters: {invalid_params}")
                    self.logger.warning(f"✅ Valid parameters from schema: {valid_params}")
                    # Filter out invalid parameters to prevent tool errors
                    arguments = {k: v for k, v in arguments.items() if k in valid_params}
                    self.logger.info(f"🔧 Filtered arguments: {arguments}")
            else:
                self.logger.warning(f"⚠️ No schema found for tool {tool_name}, using arguments as-is")
        
        # Check Atlassian authentication before attempting to use Atlassian tools
        # if server_id in ["atlassian-remote", "atlassian-remote-prod"]:
        #     auth_check = await self._check_atlassian_authentication()
        #     if not auth_check['authenticated']:
        #         return auth_check['message'], []
        
        # Execute the tool
        tool_result, success = await self.execute_tool(tool_name, arguments, jwt_token=jwt_token)
        
        if success and tool_result:
            return tool_result, [tool_name]
        else:
            return None, []
    
    async def execute_tool_if_requested(self, user_message: str, conversation_context: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
        """
        This method is called by the enhanced Claude service to check if tools should be used.
        Now it actually executes tools when the LLM requests them via TOOL_CALL format.
        
        Returns:
            Tuple of (tool_response, tools_used)
        """
        # This method is called AFTER the LLM has already responded
        # If the LLM response contains a TOOL_CALL, we execute it here
        return None, []
    
    # Knowledge Base methods (using existing Bedrock KB)
    
    async def ensure_project_kb_ready(self, project_name: str) -> ProjectContext:
        """
        Ensure project knowledge base is ready using existing Bedrock KB.
        
        Args:
            project_name: Name of the project
            
        Returns:
            ProjectContext with KB readiness status
        """
        try:
            # Use Bedrock KB service
            context = await self.kb_service.ensure_project_kb_ready(project_name)
            
            # Cache the context
            self._project_contexts[project_name] = context
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error ensuring KB ready for project {project_name}: {e}")
            return ProjectContext(
                project_name=project_name,
                kb_id=self.kb_service.kb_id,
                kb_ready=False,
                relevant_context={},
                context_quality='error',
                recent_activity=[]
            )
    
    async def get_project_context(self, project_name: str, query: str) -> Dict[str, Any]:
        """
        Get project context using existing Bedrock KB semantic search.
        
        Args:
            project_name: Name of the project
            query: Search query
            
        Returns:
            Dictionary with relevant context and metadata
        """
        try:
            return await self.kb_service.get_project_context(project_name, query)
        except Exception as e:
            self.logger.error(f"Error getting project context for {project_name}: {e}")
            return {
                'relevant_context': {'documents': []},
                'context_quality': 'error',
                'recent_activity': [],
                'error': str(e)
            }
    
    async def _sync_project_content(self, project_name: str) -> bool:
        """
        Trigger direct content synchronization for a project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            True if sync was triggered successfully
        """
        try:
            return await self.kb_service.trigger_s3_ingestion(project_name)
        except Exception as e:
            self.logger.error(f"Error syncing project content for {project_name}: {e}")
            return False
    
    async def trigger_s3_ingestion(self, project_name: str, s3_key: str = None) -> bool:
        """
        Trigger ingestion when S3 content changes using existing KB.
        
        Args:
            project_name: Name of the project
            s3_key: Specific S3 key that changed (optional)
            
        Returns:
            True if ingestion was triggered successfully
        """
        try:
            return await self.kb_service.trigger_s3_ingestion(project_name, s3_key)
        except Exception as e:
            self.logger.error(f"Error triggering S3 ingestion for {project_name}: {e}")
            return False
    
    def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        return {
            'total_tools': len(self.available_tools),
            'tools': self.available_tools.copy()
        }
    
    def _get_tool_timeout(self, tool_name: str, server_id: str) -> float:
        """Get the configured timeout for a specific tool."""
        # Default timeout for tools
        default_timeout = 120.0
        
        # Tool-specific timeouts based on MCP server configuration
        tool_timeouts = {
            # AWS Architecture Design tools
            'create_architecture_diagram': 300.0,
            'generate_architecture_code': 180.0,
            'query_aws_knowledge': 60.0,
            'analyze_architecture': 120.0,
            'estimate_architecture_cost': 120.0,
            
            # Domain Analysis tools
            'domain_analysis': 240.0,
            'generate_documentation': 300.0,
            'generate_openapi_spec': 240.0,
            
            # Amazon Q Business tools
            'mcp_amazon_q_business_retrieve': 120.0,
            'mcp_amazon_q_business_create': 240.0,
            
            # Atlassian tools (shorter timeouts since they're usually quick)
            'getAccessibleAtlassianResources': 60.0,
            'getVisibleJiraProjects': 60.0,
            'getJiraIssue': 30.0,
            'createJiraIssue': 90.0,
            'getConfluenceSpaces': 60.0,
            'getPagesInConfluenceSpace': 60.0,
        }
        
        # Get tool-specific timeout or use default
        timeout = tool_timeouts.get(tool_name, default_timeout)
        
        self.logger.debug(f"Using timeout of {timeout}s for tool {tool_name}")
        return timeout
    
    # Atlassian authentication will be implemented later
    
    def _process_tool_response(self, tool_name: str, response) -> str:
        """Process and format tool responses using the same approach as non-streaming mode."""
        try:
            # Extract the raw content from the response
            if hasattr(response, 'content') and response.content:
                raw_content = response.content
                
                # Convert to string if it's not already
                if isinstance(raw_content, dict):
                    import json
                    raw_content = json.dumps(raw_content)
                elif not isinstance(raw_content, str):
                    raw_content = str(raw_content)
                
                # Format ALL tool responses for better display in streaming mode
                return self._format_universal_tool_response(tool_name, raw_content)
            else:
                return "No content returned from tool"
                
        except Exception as e:
            self.logger.error(f"Error processing tool response for {tool_name}: {e}")
            # Return raw response as fallback
            if hasattr(response, 'content'):
                return str(response.content)
            return "Error processing tool response"
    
    def _format_tool_result_with_ai(self, tool_name: str, raw_content: str) -> str:
        """Format tool results using AI (same approach as non-streaming mode)."""
        try:
            # For large responses, truncate before formatting to avoid rate limits
            # EXCEPTION: Don't truncate OpenAPI specs or other code generation tools
            if len(raw_content) > 10000 and not any(spec_tool in tool_name for spec_tool in [
                'generate_openapi_spec', 'generate_documentation', 'generate_architecture_code'
            ]):
                self.logger.info("Large tool result detected, truncating for formatting")
                truncated_result = raw_content[:8000] + "\n\n[... truncated for brevity ...]"
            else:
                if len(raw_content) > 10000:
                    self.logger.info(f"Large {tool_name} result detected ({len(raw_content)} chars), but preserving full content for code generation")
                truncated_result = raw_content
            
            # Format the tool result through Claude for better presentation
            tool_formatting_prompt = f"""The user requested information and I used a tool to get the data. Please format this tool response in a clear, human-readable way:

Tool used: {tool_name}
Raw tool response: {truncated_result}

Please format this data nicely with:
1. Clear headers and organization
2. Bullet points where appropriate  
3. Summary of what the data means
4. Remove any raw JSON formatting
5. Make it easy for humans to understand

Provide a well-formatted response that explains what this data shows."""
            
            # Use Claude to format the response (we'll need to implement this)
            # For now, return the basic formatted version as fallback
            return self._basic_format_tool_result(tool_name, raw_content)
            
        except Exception as e:
            self.logger.error(f"Error formatting tool result with AI for {tool_name}: {e}")
            return self._basic_format_tool_result(tool_name, raw_content)
    
    def _format_jira_ticket_creation_response(self, raw_content: str) -> str:
        """Format Jira ticket creation response while preserving structured data for extraction."""
        try:
            import json
            
            # Parse the raw content to extract ticket information
            if isinstance(raw_content, dict):
                content_data = raw_content
            else:
                content_data = json.loads(raw_content)
            
            # # Check if this is actually a tools list response (error case)
            # if 'tools' in content_data and isinstance(content_data['tools'], list):
            #     self.logger.warning("MCP server returned tools list instead of creating Jira ticket - authentication or server registration issue")
            #     return (
            #         "❌ **Jira Ticket Creation Failed**\n\n"
            #         "The MCP server returned a tools list instead of creating a ticket. This usually means:\n"
            #         "1. The Atlassian MCP server is not properly registered\n"
            #         "2. Authentication is not working at the MCP server level\n"
            #         "3. The tool call was intercepted\n\n"
            #         "**Please try:**\n"
            #         "1. Re-authenticate with Atlassian (go to Jira Integration page)\n"
            #         "2. Wait a moment for servers to re-register\n"
            #         "3. Try creating the ticket again\n\n"
            #         "If the issue persists, there may be a problem with the MCP server connection."
            #     )
            
            # Check if this is an error response from Jira API
            if 'isError' in content_data and content_data.get('isError') == True:
                self.logger.warning("Jira API returned an error response")
                error_content = content_data.get('content', [])
                if error_content and isinstance(error_content, list) and len(error_content) > 0:
                    error_text = error_content[0].get('text', '')
                    try:
                        error_data = json.loads(error_text)
                        error_message = error_data.get('message', 'Unknown error')
                        
                        # Handle specific error types
                        if 'issue type selected is invalid' in error_message.lower():
                            return (
                                "❌ **Jira Ticket Creation Failed - Invalid Issue Type**\n\n"
                                f"**Error:** {error_message}\n\n"
                                "**Common Solutions:**\n"
                                "1. **Check available issue types** in your Jira project\n"
                                "2. **Use correct issue type names** (e.g., 'Story', 'Task', 'Bug' instead of 'Epic')\n"
                                "3. **Epic creation** may require different permissions or project configuration\n\n"
                                "**Suggested issue types to try:**\n"
                                "- Story\n"
                                "- Task\n"
                                "- Bug\n"
                                "- Improvement\n\n"
                                "**Next steps:**\n"
                                "1. Check your Jira project settings for available issue types\n"
                                "2. Try creating tickets with 'Story' or 'Task' instead of 'Epic'\n"
                                "3. Contact your Jira admin if Epic creation is needed"
                            )
                        else:
                            return (
                                "❌ **Jira Ticket Creation Failed**\n\n"
                                f"**Error:** {error_message}\n\n"
                                "**Please check:**\n"
                                "1. Project permissions\n"
                                "2. Required fields are filled\n"
                                "3. Issue type is valid for this project\n"
                                "4. Authentication is working properly"
                            )
                    except json.JSONDecodeError:
                        return (
                            "❌ **Jira Ticket Creation Failed**\n\n"
                            f"**Raw error:** {error_text}\n\n"
                            "Please check your Jira project configuration and try again."
                        )
            
            # Extract ticket information from the response
            tickets_created = []
            
            # Handle the MCP response format
            if 'content' in content_data and isinstance(content_data['content'], list):
                for item in content_data['content']:
                    if item.get('type') == 'text':
                        try:
                            # Parse the nested JSON in the text field
                            ticket_data = json.loads(item['text'])
                            if 'id' in ticket_data and 'key' in ticket_data:
                                tickets_created.append(ticket_data)
                        except json.JSONDecodeError:
                            # If it's not JSON, it might be plain text
                            continue
            
            # Format the response with both human-readable and structured data
            if tickets_created:
                formatted_response = "## ✅ Successfully Created Jira Ticket(s)\n\n"
                
                for i, ticket in enumerate(tickets_created, 1):
                    ticket_id = ticket.get('id', 'Unknown')
                    ticket_key = ticket.get('key', 'Unknown')
                    ticket_url = ticket.get('self', '')
                    
                    # Create a user-friendly URL if we have the API URL
                    if ticket_url and 'api.atlassian.com' in ticket_url:
                        # Convert API URL to user-friendly URL
                        # Extract cloudId from the API URL
                        import re
                        cloud_id_match = re.search(r'/([a-f0-9-]{36})/', ticket_url)
                        if cloud_id_match:
                            cloud_id = cloud_id_match.group(1)
                            user_url = f"https://anycompanyreads.atlassian.net/browse/{ticket_key}"
                        else:
                            user_url = ticket_url
                    else:
                        user_url = f"https://anycompanyreads.atlassian.net/browse/{ticket_key}"
                    
                    formatted_response += f"**🎫 {ticket_key}**\n"
                    formatted_response += f"- **ID**: {ticket_id}\n"
                    formatted_response += f"- **Key**: {ticket_key}\n"
                    formatted_response += f"- **URL**: {user_url}\n"
                    formatted_response += f"- **Status**: Created and ready for development\n"
                    formatted_response += f"- **Project**: CS (AnyCompanyReads)\n"
                    formatted_response += f"- **Type**: New Feature\n\n"
                    
                    # Add structured data for output processor extraction
                    formatted_response += f"<!-- JIRA_TICKET_DATA: {json.dumps(ticket)} -->\n"
                    formatted_response += f"<!-- JIRA_TICKET_URL: {user_url} -->\n\n"
                
                return formatted_response
            else:
                # Fallback if we can't parse the ticket data
                return f"## ✅ Jira Ticket Creation Completed\n\nRaw response: {raw_content}"
                
        except Exception as e:
            self.logger.error(f"Error formatting Jira ticket creation response: {e}")
            return f"## ✅ Jira Ticket Created\n\nRaw response: {raw_content}"
    
    def _format_amazon_q_business_response(self, raw_content: str) -> str:
        """Format Amazon Q Business response by parsing JSON and converting to readable text."""
        try:
            import json
            import re
            
            # If raw_content is already a dict, convert to JSON string first
            if isinstance(raw_content, dict):
                raw_content = json.dumps(raw_content)
            
            # Enhanced MCP format: Look for JSON content in the response
            json_pattern = r'\{"content":\s*\[\{"type":\s*"text",\s*"text":\s*"(.*?)"\}\]\}'
            matches = re.findall(json_pattern, raw_content, re.DOTALL)
            
            if matches:
                # Take the first (and usually only) match
                json_text = matches[0]
                
                # Decode unicode escape sequences
                formatted_text = json_text.replace('\\u2022', '•')  # Convert bullet points
                formatted_text = formatted_text.replace('\\n', '\n')  # Convert newlines
                formatted_text = formatted_text.replace('\\"', '"')   # Convert escaped quotes
                formatted_text = formatted_text.replace('\\\\', '\\')  # Convert double backslashes
                
                self.logger.info(f"Successfully formatted Amazon Q Business enhanced response for display (length: {len(formatted_text)})")
                return formatted_text
            
            # Try to parse as direct JSON (both enhanced and standard formats)
            try:
                data = json.loads(raw_content)
                
                # Enhanced format: {"content": [{"type": "text", "text": "..."}]}
                if 'content' in data and isinstance(data['content'], list):
                    for item in data['content']:
                        if item.get('type') == 'text' and 'text' in item:
                            text_content = item['text']
                            # Decode unicode escape sequences
                            text_content = text_content.replace('\\u2022', '•')
                            text_content = text_content.replace('\\n', '\n')
                            text_content = text_content.replace('\\"', '"')
                            self.logger.info(f"Successfully parsed Amazon Q Business enhanced JSON for display (length: {len(text_content)})")
                            return text_content
                
                # Standard format: {"result": "...", "status": "success"}
                elif 'result' in data:
                    result_content = str(data['result'])
                    # Decode unicode escape sequences
                    result_content = result_content.replace('\\u2022', '•')
                    result_content = result_content.replace('\\n', '\n')
                    result_content = result_content.replace('\\"', '"')
                    self.logger.info(f"Successfully parsed Amazon Q Business standard JSON for display (length: {len(result_content)})")
                    return result_content
                
                # Handle other standard formats
                elif 'response' in data:
                    response_content = str(data['response'])
                    response_content = response_content.replace('\\u2022', '•')
                    response_content = response_content.replace('\\n', '\n')
                    response_content = response_content.replace('\\"', '"')
                    return response_content
                
                elif 'message' in data:
                    message_content = str(data['message'])
                    message_content = message_content.replace('\\u2022', '•')
                    message_content = message_content.replace('\\n', '\n')
                    message_content = message_content.replace('\\"', '"')
                    return message_content
                
            except json.JSONDecodeError:
                pass
            
            # If no JSON found or parsing failed, try to clean up the raw content
            if raw_content:
                # Clean up common formatting issues in plain text responses
                formatted_content = raw_content
                formatted_content = formatted_content.replace('\\u2022', '•')
                formatted_content = formatted_content.replace('\\n', '\n')
                formatted_content = formatted_content.replace('\\"', '"')
                formatted_content = formatted_content.replace('\\\\', '\\')
                
                self.logger.info("No JSON content found in Amazon Q Business response, returning cleaned raw content")
                return formatted_content
            
            # If no JSON found or parsing failed, return the original content
            self.logger.info("No content found in Amazon Q Business response, returning original")
            return raw_content
            
        except Exception as e:
            self.logger.error(f"Error formatting Amazon Q Business response: {e}")
            return raw_content
    
    def _format_universal_tool_response(self, tool_name: str, raw_content: str) -> str:
        """Universal formatter for ALL tool responses in streaming mode."""
        try:
            # Special handling for Jira ticket creation - preserve structured data
            if tool_name == 'createJiraIssue':
                return self._format_jira_ticket_creation_response(raw_content)
            
            # Special handling for Amazon Q Business - format JSON responses
            if tool_name == 'mcp_amazon_q_business_retrieve':
                return self._format_amazon_q_business_response(raw_content)
            
            # Check if this is an Atlassian tool that needs AI formatting
            atlassian_tools = [
                'getAccessibleAtlassianResources', 'getVisibleJiraProjects', 'getJiraIssue', 
                'editJiraIssue', 'getConfluenceSpaces', 'getConfluencePage', 
                'getPagesInConfluenceSpace', 'searchConfluenceUsingCql', 'searchJiraIssuesUsingJql',
                'addCommentToJiraIssue', 'transitionJiraIssue', 'lookupJiraAccountId'
            ]
            
            if any(atlassian_tool in tool_name for atlassian_tool in atlassian_tools):
                # Use AI formatting for Atlassian tools
                return self._format_tool_result_with_ai(tool_name, raw_content)
            
            # For all other tools, apply universal formatting
            return self._format_generic_tool_response(tool_name, raw_content)
            
        except Exception as e:
            self.logger.error(f"Error in universal tool response formatting for {tool_name}: {e}")
            return self._format_generic_tool_response(tool_name, raw_content)
    
    def _format_generic_tool_response(self, tool_name: str, raw_content: str) -> str:
        """Format generic tool responses for better readability."""
        try:
            import json
            import re
            
            # Convert to string if needed
            if isinstance(raw_content, dict):
                raw_content = json.dumps(raw_content, indent=2)
            elif not isinstance(raw_content, str):
                raw_content = str(raw_content)
            
            # Try to parse as JSON and format nicely
            try:
                if raw_content.strip().startswith('{') or raw_content.strip().startswith('['):
                    parsed_json = json.loads(raw_content)
                    
                    # Check for common JSON response patterns and format them
                    formatted_response = self._format_json_response(tool_name, parsed_json)
                    if formatted_response:
                        return formatted_response
                    
                    # Fallback: pretty print the JSON
                    return f"## 🔧 {tool_name.replace('_', ' ').title()} Result\n\n```json\n{json.dumps(parsed_json, indent=2)}\n```"
                    
            except json.JSONDecodeError:
                pass
            
            # Handle plain text responses
            if raw_content:
                # Clean up common formatting issues
                formatted_content = raw_content
                
                # Convert unicode escape sequences if present
                formatted_content = formatted_content.replace('\\u2022', '•')
                formatted_content = formatted_content.replace('\\n', '\n')
                formatted_content = formatted_content.replace('\\"', '"')
                
                # Add a nice header
                tool_display_name = tool_name.replace('_', ' ').title()
                return f"## 🔧 {tool_display_name} Result\n\n{formatted_content}"
            
            return f"## 🔧 {tool_name.replace('_', ' ').title()}\n\nNo content returned from tool."
            
        except Exception as e:
            self.logger.error(f"Error formatting generic tool response for {tool_name}: {e}")
            return f"## 🔧 {tool_name.replace('_', ' ').title()}\n\n{raw_content}"
    
    def _format_json_response(self, tool_name: str, json_data: dict) -> str:
        """Format common JSON response patterns for better readability."""
        try:
            tool_display_name = tool_name.replace('_', ' ').title()
            
            # Handle list responses (like search results)
            if isinstance(json_data, list):
                if len(json_data) == 0:
                    return f"## 🔧 {tool_display_name} Result\n\nNo results found."
                
                formatted_items = []
                for i, item in enumerate(json_data[:10], 1):  # Limit to first 10 items
                    if isinstance(item, dict):
                        # Try to find key fields to display
                        title = item.get('title') or item.get('name') or item.get('summary') or f"Item {i}"
                        description = item.get('description') or item.get('content') or ""
                        
                        formatted_items.append(f"**{i}. {title}**")
                        if description:
                            formatted_items.append(f"   {description[:200]}{'...' if len(description) > 200 else ''}")
                    else:
                        formatted_items.append(f"{i}. {str(item)}")
                
                result = f"## 🔧 {tool_display_name} Result\n\n"
                result += "\n".join(formatted_items)
                
                if len(json_data) > 10:
                    result += f"\n\n*... and {len(json_data) - 10} more items*"
                
                return result
            
            # Handle object responses with common patterns
            if isinstance(json_data, dict):
                # Check for error responses
                if 'error' in json_data or 'errors' in json_data:
                    error_msg = json_data.get('error') or json_data.get('errors')
                    return f"## ❌ {tool_display_name} Error\n\n{error_msg}"
                
                # Check for success responses
                if 'success' in json_data and json_data['success']:
                    message = json_data.get('message', 'Operation completed successfully')
                    return f"## ✅ {tool_display_name} Success\n\n{message}"
                
                # Check for data responses
                if 'data' in json_data:
                    data = json_data['data']
                    if isinstance(data, list) and len(data) > 0:
                        return self._format_json_response(tool_name, data)
                
                # Enhanced MCP format: Check for content responses (like Amazon Q Business)
                if 'content' in json_data and isinstance(json_data['content'], list):
                    for item in json_data['content']:
                        if item.get('type') == 'text' and 'text' in item:
                            text_content = item['text']
                            # Format the text content
                            text_content = text_content.replace('\\u2022', '•')
                            text_content = text_content.replace('\\n', '\n')
                            return f"## 🔧 {tool_display_name} Result\n\n{text_content}"
                
                # Standard MCP format: Check for result responses
                if 'result' in json_data:
                    result_content = str(json_data['result'])
                    # Format the result content
                    result_content = result_content.replace('\\u2022', '•')
                    result_content = result_content.replace('\\n', '\n')
                    return f"## 🔧 {tool_display_name} Result\n\n{result_content}"
                
                # Standard MCP format: Check for response field
                if 'response' in json_data:
                    response_content = str(json_data['response'])
                    response_content = response_content.replace('\\u2022', '•')
                    response_content = response_content.replace('\\n', '\n')
                    return f"## 🔧 {tool_display_name} Result\n\n{response_content}"
                
                # Standard MCP format: Check for message field
                if 'message' in json_data:
                    message_content = str(json_data['message'])
                    message_content = message_content.replace('\\u2022', '•')
                    message_content = message_content.replace('\\n', '\n')
                    return f"## 🔧 {tool_display_name} Result\n\n{message_content}"
                
                # For other objects, show key-value pairs nicely
                if len(json_data) <= 10:  # Only for small objects
                    formatted_pairs = []
                    for key, value in json_data.items():
                        if isinstance(value, (str, int, float, bool)):
                            formatted_pairs.append(f"**{key.replace('_', ' ').title()}**: {value}")
                        elif isinstance(value, list) and len(value) <= 5:
                            formatted_pairs.append(f"**{key.replace('_', ' ').title()}**: {', '.join(map(str, value))}")
                    
                    if formatted_pairs:
                        return f"## 🔧 {tool_display_name} Result\n\n" + "\n".join(formatted_pairs)
            
            # If no specific pattern matched, return None to use fallback
            return None
            
        except Exception as e:
            self.logger.error(f"Error formatting JSON response for {tool_name}: {e}")
            return None
    
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
                elif tool_name == "getAccessibleAtlassianResources":
                    return self._format_atlassian_resources(data)
                elif tool_name == "createJiraIssue":
                    return self._format_jira_creation_results([{'tool_name': tool_name, 'result': tool_result, 'success': True}])
                else:
                    # Generic JSON formatting
                    return f"## {tool_name.replace('_', ' ').title()} Results\n\n```json\n{json.dumps(data, indent=2)}\n```"
            else:
                return f"## {tool_name.replace('_', ' ').title()} Results\n\n{tool_result}"
                
        except json.JSONDecodeError:
            return f"## {tool_name.replace('_', ' ').title()} Results\n\n{tool_result}"
    
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
                        browse_url = f"https://anycompanyreads.atlassian.net/browse/{ticket_key}"
                    
                    response_parts.append(f"**🎫 {ticket_key}**")
                    response_parts.append(f"- **Status**: Created and ready for development")
                    response_parts.append(f"- **Project**: CS (AnyCompanyReads)")
                    response_parts.append(f"- **Type**: New Feature")
                    if browse_url:
                        response_parts.append(f"- **View in Jira**: [Open {ticket_key}]({browse_url})")
                    response_parts.append("")
                    
                except (json.JSONDecodeError, KeyError) as e:
                    response_parts.append(f"**🎫 Ticket**: Created successfully")
                    response_parts.append(f"- **Status**: Created (details parsing failed)")
                    response_parts.append("")
        
        return "\n".join(response_parts)