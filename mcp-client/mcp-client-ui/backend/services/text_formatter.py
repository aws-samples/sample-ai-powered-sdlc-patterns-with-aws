"""
Text formatting service for AI responses.
Converts AI responses into properly formatted, readable text.
"""

import re
from typing import List


class TextFormatter:
    """Service for formatting AI text responses for better readability."""
    
    def __init__(self):
        """Initialize the text formatter."""
        pass
    
    def format_ai_response(self, text: str) -> str:
        """
        Format AI response text for better readability.
        
        Args:
            text: Raw AI response text
            
        Returns:
            Formatted text with proper line breaks and structure
        """
        if not text or not isinstance(text, str):
            return text
        
        # Clean up the text first
        formatted_text = self._clean_text(text)
        
        # Format tool calls into human-readable messages
        formatted_text = self._format_tool_calls(formatted_text)
        
        # Apply formatting rules
        formatted_text = self._format_numbered_lists(formatted_text)
        formatted_text = self._format_bullet_points(formatted_text)
        formatted_text = self._format_headers(formatted_text)
        formatted_text = self._format_paragraphs(formatted_text)
        formatted_text = self._format_code_blocks(formatted_text)
        formatted_text = self._format_links(formatted_text)
        
        return formatted_text.strip()
    
    def _format_tool_calls(self, text: str) -> str:
        """
        Format raw tool calls into human-readable messages.
        
        Converts:
        TOOL_CALL: {"server_id": "atlassian-remote", "capability": "getAccessibleAtlassianResources", "tool_name": "getAccessibleAtlassianResources", "arguments": {}}
        
        Into:
        🔧 Accessing Atlassian resources...
        """
        import json
        
        # Remove unwanted meta-text about tool usage
        text = self._remove_meta_text(text)
        
        # Tool call to human-readable mapping
        tool_descriptions = {
            'getAccessibleAtlassianResources': '🔗 Retrieving your Atlassian Cloud instances and permissions...',
            'createJiraIssue': '🎫 Creating Jira tickets and epics...',
            'create_architecture_diagram': '🎨 Generating architecture diagrams...',
            'generate_architecture_code': '💻 Generating infrastructure code...',
            'domain_analysis': '🔍 Analyzing domain requirements...',
            'analyze_architecture': '🏗️ Analyzing system architecture...',
            'estimate_architecture_cost': '💰 Calculating cost estimates...',
            'query_aws_knowledge': '☁️ Querying AWS knowledge base...',
            'generate_documentation': '📄 Generating documentation...',
            'mcp_amazon_q_business_retrieve': '🔍 Retrieving information from knowledge base...',
            'generate_openapi_spec': '📋 Generating API specifications...',
            'mcp_amazon_q_business_authenticate': '🔐 Authenticating with knowledge base...',
        }
        
        # Find and replace all TOOL_CALL instances
        def find_and_replace_tool_calls(text):
            result = ""
            search_pos = 0
            
            while True:
                # Find next TOOL_CALL
                tool_call_pos = text.find("TOOL_CALL:", search_pos)
                if tool_call_pos == -1:
                    # No more tool calls, add remaining text
                    result += text[search_pos:]
                    break
                
                # Add text before TOOL_CALL
                result += text[search_pos:tool_call_pos]
                
                # Find the JSON object
                json_start = text.find("{", tool_call_pos)
                if json_start == -1:
                    # No JSON found, skip this TOOL_CALL
                    result += text[tool_call_pos:tool_call_pos + 10]  # Add "TOOL_CALL:"
                    search_pos = tool_call_pos + 10
                    continue
                
                # Find matching closing brace
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if brace_count != 0:
                    # Unmatched braces, skip this TOOL_CALL
                    result += text[tool_call_pos:json_start + 1]
                    search_pos = json_start + 1
                    continue
                
                try:
                    # Parse the JSON
                    tool_call_json = text[json_start:json_end]
                    tool_call_data = json.loads(tool_call_json)
                    tool_name = tool_call_data.get('tool_name', '')
                    
                    # Get human-readable description
                    description = tool_descriptions.get(tool_name, f'🔧 Using {tool_name}...')
                    
                    # Add some context based on arguments if available
                    arguments = tool_call_data.get('arguments', {})
                    if arguments:
                        if 'message' in arguments:
                            description += f"\n📝 Query: {arguments['message'][:100]}{'...' if len(arguments['message']) > 100 else ''}"
                        elif 'description' in arguments:
                            description += f"\n📝 Description: {arguments['description'][:100]}{'...' if len(arguments['description']) > 100 else ''}"
                        elif 'epic_name' in arguments:
                            description += f"\n📋 Epic: {arguments['epic_name']}"
                    
                    # Add the formatted description
                    result += f"\n\n{description}\n"
                    search_pos = json_end
                    
                except (json.JSONDecodeError, KeyError) as e:
                    # If parsing fails, add a generic message
                    result += "\n\n🔧 Executing tool...\n"
                    search_pos = json_end
            
            return result
        
        return find_and_replace_tool_calls(text)
    
    def _remove_meta_text(self, text: str) -> str:
        """Remove unwanted meta-text about tool usage."""
        # Remove Amazon Q Business meta-text
        patterns_to_remove = [
            r'I will use Amazon Q Business to extract relevant information from your Confluence documentation[^.]*\.',
            r'Based on the extracte[^.]*\.',
            r'📋\[Name\] Epic and bullet points with • for features\. Include rough story point estimates for each feature\.\"\}\}',
            r'Let me extract information from your knowledge base\.\.\.',
            r'🔍 Retrieving information from knowledge base\.\.\.',
            r'📝 Query: [^.]*\.\.\.',
            r'## \[Name\] Epic and bullet points with • for features\. Include estimates for story points\.\"\}\}',
            r'Format the response with epic headers using ## \[Name\] Epic and bullet points with • for features\. Include estimates for story points\.\"\}\}',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean up the raw text."""
        # Remove excessive whitespace but preserve intentional line breaks
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n +', '\n', text)  # Remove spaces at start of lines
        text = re.sub(r' +\n', '\n', text)  # Remove spaces at end of lines
        
        return text
    
    def _format_numbered_lists(self, text: str) -> str:
        """Format numbered lists with proper spacing."""
        # Pattern for numbered lists like "1. **Title**" followed by description
        pattern = r'(\d+\.\s*\*\*[^*]+\*\*)\s*([A-Z][^.]*\.)'
        text = re.sub(pattern, r'\n\n\1\n\2', text)
        
        # Pattern for simple numbered lists
        pattern = r'(\d+\.\s+[A-Z][^\n]*)'
        text = re.sub(pattern, r'\n\n\1', text)
        
        # Add line breaks after numbered items when followed by new sentences
        pattern = r'(\d+\.\s*\*\*[^*]+\*\*[^.]*\.) ([A-Z][^.]*\.)'
        text = re.sub(pattern, r'\1\n\n\2', text)
        
        return text
    
    def _format_bullet_points(self, text: str) -> str:
        """Format bullet points and dashes."""
        # Convert various bullet formats to consistent format
        text = re.sub(r'\n-\s+', '\n• ', text)
        text = re.sub(r'\n\*\s+', '\n• ', text)
        
        # Add spacing before bullet point sections
        text = re.sub(r'([.:])\s*\n(• )', r'\1\n\n\2', text)
        
        return text
    
    def _format_headers(self, text: str) -> str:
        """Format headers and section titles."""
        # Format markdown headers (## Header)
        text = re.sub(r'\n(#{1,3}\s+[^\n]+)', r'\n\n\1\n', text)
        
        # Bold headers (keep existing ** formatting)
        # Add extra spacing around headers
        text = re.sub(r'\n(\*\*[^*]+\*\*)', r'\n\n\1', text)
        text = re.sub(r'(\*\*[^*]+\*\*)\n', r'\1\n\n', text)
        
        # Handle tier descriptions like "Presentation Tier (Client Tier)"
        pattern = r'(\d+\.\s*\*\*[^*]+\*\*)'
        text = re.sub(pattern, r'\n\1', text)
        
        return text
    
    def _format_paragraphs(self, text: str) -> str:
        """Add proper paragraph spacing."""
        # Add spacing between sentences that should be separate paragraphs
        # Look for sentence endings followed by capital letters (new topics)
        text = re.sub(r'(\.) ([A-Z][a-z]+ (tier|layer|architecture|component))', r'\1\n\n\2', text)
        
        # Add spacing after colons when followed by detailed explanations
        text = re.sub(r'(:) ([A-Z][^.]*\. [A-Z])', r'\1\n\n\2', text)
        
        # Add spacing after periods when followed by "This tier/layer"
        text = re.sub(r'(\.) (This (tier|layer))', r'\1\n\n\2', text)
        
        # Add spacing between different concepts
        text = re.sub(r'(\.) ([A-Z][a-z]+ [a-z]+ [a-z]+ [a-z]+ [a-z]+)', r'\1\n\n\2', text)
        
        # Clean up excessive line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _format_code_blocks(self, text: str) -> str:
        """Format code blocks and technical terms."""
        # Add spacing around code-like terms in parentheses
        text = re.sub(r'\(([A-Z][a-z]+, [A-Z][a-z]+[^)]*)\)', r'\n(\1)', text)
        
        # Format markdown tables - add spacing
        text = re.sub(r'\n(\|[^|\n]+\|)', r'\n\n\1', text)
        
        # Format code blocks - add spacing
        text = re.sub(r'\n(```[^`]*```)', r'\n\n\1\n\n', text)
        
        return text
    
    def _format_links(self, text: str) -> str:
        """Format URLs and links."""
        # Add spacing before URLs
        text = re.sub(r'([a-z]) (https?://)', r'\1\n\n\2', text)
        
        # Group multiple URLs together
        text = re.sub(r'(https?://[^\s]+)\s+(https?://)', r'\1\n\2', text)
        
        return text
    
    def format_architecture_analysis(self, analysis_text: str) -> str:
        """
        Specifically format architecture analysis text.
        
        Args:
            analysis_text: Architecture analysis text
            
        Returns:
            Formatted analysis text
        """
        if not analysis_text:
            return analysis_text
        
        # Apply general formatting
        formatted = self.format_ai_response(analysis_text)
        
        # Specific formatting for analysis sections
        formatted = re.sub(r'(\*\*Overview:\*\*)', r'\n\1', formatted)
        formatted = re.sub(r'(\*\*Components Identified:\*\*)', r'\n\1', formatted)
        formatted = re.sub(r'(\*\*Recommendations:\*\*)', r'\n\1', formatted)
        formatted = re.sub(r'(\*\*Potential Considerations:\*\*)', r'\n\1', formatted)
        
        return formatted