"""
Output Processing Service

Automatically detects and processes tool outputs:
- Diagram URLs → Store in S3 and display in left panel
- Code files → Store in S3 and display in code panel
- Other outputs → Process appropriately
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import aiohttp
import asyncio

from services.diagram_service import DiagramService
from services.s3_storage_service import S3StorageService


class OutputProcessor:
    """Processes tool outputs and stores them appropriately."""
    
    def __init__(self, diagram_service: DiagramService = None, s3_storage_service: S3StorageService = None):
        """Initialize the output processor."""
        self.logger = logging.getLogger(__name__)
        self.diagram_service = diagram_service or DiagramService()
        self.s3_storage_service = s3_storage_service or S3StorageService()
    
    async def process_tool_outputs(
        self, 
        tools_used: List[str], 
        ai_response: str, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process all tool outputs and extract useful content.
        
        Returns:
            Dictionary with processed outputs (diagrams, code, etc.)
        """
        processed_outputs = {
            'diagrams': [],
            'code_files': [],
            'documents': [],
            'jira_tickets': [],
            'epics': [],
            'other_outputs': [],
            'jira_data_updated': False  # Flag to indicate if Jira data was updated
        }
        
        try:
            # Debug: Log AI response content
            self.logger.info(f"AI response length: {len(ai_response)} characters")
            if "https://" in ai_response:
                self.logger.info("AI response contains https URLs")
                # Find all https URLs for debugging
                import re
                all_urls = re.findall(r'https://[^\s\)]+', ai_response)
                self.logger.info(f"All https URLs found: {all_urls}")
                
                # Check specifically for S3 URLs
                s3_urls = [url for url in all_urls if 's3.amazonaws.com' in url]
                if s3_urls:
                    self.logger.info(f"S3 URLs found: {s3_urls}")
                
                # Check for diagram-related URLs
                diagram_related = [url for url in all_urls if any(keyword in url.lower() for keyword in ['diagram', 'architecture', 'technical', '.png', '.jpg', '.svg'])]
                if diagram_related:
                    self.logger.info(f"Diagram-related URLs found: {diagram_related}")
            else:
                self.logger.info("AI response does NOT contain https URLs")
            
            # Extract diagram URLs from AI response
            diagram_urls = self._extract_diagram_urls(ai_response)
            if diagram_urls:
                self.logger.info(f"Processing {len(diagram_urls)} diagram URLs")
                for url in diagram_urls:
                    diagram_data = await self._process_diagram_url(url, session)
                    if diagram_data:
                        processed_outputs['diagrams'].append(diagram_data)
                    else:
                        self.logger.error(f"Failed to process diagram URL: {url}")
            else:
                self.logger.info("No diagram URLs found in AI response text")
            
            # Extract code blocks from AI response
            code_blocks = self._extract_code_blocks(ai_response)
            if code_blocks:
                self.logger.info(f"Processing {len(code_blocks)} code blocks")
                for code_block in code_blocks:
                    code_file = await self._process_code_block(code_block, session)
                    if code_file:
                        processed_outputs['code_files'].append(code_file)
            
            # Extract document URLs (PDFs, etc.)
            document_urls = self._extract_document_urls(ai_response)
            if document_urls:
                self.logger.info(f"Processing {len(document_urls)} document URLs")
                for url in document_urls:
                    document_data = await self._process_document_url(url, session)
                    if document_data:
                        processed_outputs['documents'].append(document_data)
            

            
            # Extract Jira tickets ONLY when Jira creation tools were actually used
            jira_creation_tools = ['createJiraIssue', 'jira_create_issue', 'create_jira_issue']
            jira_tool_used = any(tool in tools_used for tool in jira_creation_tools) if tools_used else False
            
            if jira_tool_used:
                used_tool = next((tool for tool in jira_creation_tools if tool in tools_used), 'createJiraIssue')
                self.logger.info(f"{used_tool} tool was used - extracting Jira tickets from response")
                jira_tickets = self._extract_jira_tickets(ai_response)
                if jira_tickets:
                    self.logger.info(f"Processing {len(jira_tickets)} Jira tickets from {used_tool} tool")
                    await self._process_jira_tickets(jira_tickets, session)
                    processed_outputs['jira_tickets'] = jira_tickets
                    processed_outputs['jira_data_updated'] = True
                else:
                    self.logger.warning(f"{used_tool} tool was used but no tickets were extracted from response")
            else:
                self.logger.info(f"No Jira creation tools used (checked: {jira_creation_tools}) - skipping Jira ticket extraction")
                if tools_used:
                    self.logger.info(f"Tools that were used: {tools_used}")
            
            # Extract epic information ONLY when mcp_amazon_q_business_retrieve tool was actually used
            if tools_used and 'mcp_amazon_q_business_retrieve' in tools_used:
                self.logger.info("mcp_amazon_q_business_retrieve tool was used - extracting epics from response")
                
                # First, try to parse any JSON tool results in the response and format them properly
                formatted_response = self._format_amazon_q_response(ai_response)
                
                # Extract epics from the formatted response
                epics = self._extract_epics(formatted_response)
                if epics:
                    self.logger.info(f"✅ Processing {len(epics)} epics from formatted response")
                    await self._process_epics(epics, session)
                    processed_outputs['epics'] = epics
                    processed_outputs['jira_data_updated'] = True
                else:
                    self.logger.warning("mcp_amazon_q_business_retrieve tool was used but no epics were extracted from response")
            else:
                self.logger.info("mcp_amazon_q_business_retrieve tool was not used - skipping epic extraction")
            
            # Only log if something was processed
            total_processed = len(processed_outputs['diagrams']) + len(processed_outputs['code_files']) + len(processed_outputs['documents'])
            if total_processed > 0:
                self.logger.info(f"Processed {len(processed_outputs['diagrams'])} diagrams, {len(processed_outputs['code_files'])} code files, {len(processed_outputs['documents'])} documents")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing tool outputs: {e}")
        
        return processed_outputs
    
    def _extract_diagram_urls(self, text: str) -> List[str]:
        """Extract diagram URLs from text."""
        # Debug logging to see what text we're processing
        self.logger.debug(f"Extracting diagram URLs from text (length: {len(text)})")
        if "https://" in text:
            self.logger.debug(f"Text contains https URLs: {text[:500]}...")
        
        # Look for various diagram URL patterns
        patterns = [
            r'https?://[^\s\)]+\.(?:png|jpg|jpeg|gif|svg)',  # Image URLs (fixed to handle markdown)
            r'https?://[^\s\)]+/diagram[^\s\)]*',  # URLs containing 'diagram'
            r'https?://[^\s\)]+/architecture[^\s\)]*',  # URLs containing 'architecture'
            r'!\[.*?\]\((https?://[^\s\)]+\.(?:png|jpg|jpeg|gif|svg))\)',  # Markdown image syntax
            r'https?://[^\s\)]+\.s3\.amazonaws\.com[^\s\)]*\.(?:png|jpg|jpeg|gif|svg)',  # S3 image URLs
            r'https?://[^\s\)]+\.s3\.amazonaws\.com[^\s\)]*_diagram\.png',  # S3 diagram URLs with _diagram suffix
            r'https?://[^\s\)]+\.s3\.amazonaws\.com[^\s\)]*architecture[^\s\)]*\.png',  # S3 architecture diagram URLs
            r'https?://[^\s\)]+\.s3\.amazonaws\.com[^\s\)]*technical[^\s\)]*\.png',  # S3 technical diagram URLs
        ]
        
        urls = []
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                self.logger.debug(f"Pattern {i+1} found {len(matches)} matches: {matches}")
                # Handle both tuple and string matches from regex groups
                for match in matches:
                    if isinstance(match, tuple):
                        # From markdown syntax pattern - take the URL part
                        urls.append(match[0] if match[0] else match[1])
                    else:
                        urls.append(match)
            else:
                self.logger.debug(f"Pattern {i+1} found no matches")
        
        # Remove duplicates and filter valid URLs
        unique_urls = list(set(urls))
        valid_urls = [url for url in unique_urls if self._is_valid_url(url)]
        
        if valid_urls:
            self.logger.info(f"Found {len(valid_urls)} valid diagram URLs: {valid_urls}")
        else:
            self.logger.debug("No diagram URLs found in text")
        
        return valid_urls
    
    def _extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from text."""
        # Look for code blocks in various formats
        patterns = [
            r'```(\w+)?\n(.*?)\n```',  # Standard code blocks
            r'`([^`\n]+)`',  # Inline code
        ]
        
        code_blocks = []
        
        # Extract fenced code blocks
        fenced_pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.findall(fenced_pattern, text, re.DOTALL)
        for language, code in matches:
            if len(code.strip()) > 10:  # Only process substantial code blocks
                code_blocks.append({
                    'language': language or 'text',
                    'code': code.strip(),
                    'type': 'block'
                })
        
        return code_blocks
    
    def _extract_document_urls(self, text: str) -> List[str]:
        """Extract document URLs from text."""
        patterns = [
            r'https?://[^\s]+\.(?:pdf|doc|docx|txt)',  # Document URLs
            r'https?://[^\s]+/document[^\s]*',  # URLs containing 'document'
            r'https?://[^\s]+/specification[^\s]*',  # URLs containing 'specification'
        ]
        
        urls = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
        
        return list(set(urls))
    
    def _extract_openapi_specs(self, text: str) -> List[Dict[str, Any]]:
        """Extract OpenAPI specifications from text."""
        specs = []
        
        self.logger.info(f"Extracting OpenAPI specs from text (length: {len(text)})")
        
        # Look for JSON code blocks that contain OpenAPI specifications
        json_pattern = r'```(?:json|yaml|yml)?\n(.*?)\n```'
        code_blocks = re.findall(json_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for code_block in code_blocks:
            try:
                # Try to parse as JSON first
                import json
                spec_data = json.loads(code_block.strip())
                
                # Check if it's an OpenAPI spec by looking for key indicators
                if self._is_openapi_spec(spec_data):
                    self.logger.info("Found OpenAPI spec in JSON format")
                    specs.append({
                        'format': 'json',
                        'content': code_block.strip(),
                        'parsed': spec_data,
                        'title': spec_data.get('info', {}).get('title', 'API Specification'),
                        'version': spec_data.get('info', {}).get('version', '1.0.0')
                    })
                    
            except json.JSONDecodeError:
                # Try YAML parsing
                try:
                    import yaml
                    spec_data = yaml.safe_load(code_block.strip())
                    
                    if self._is_openapi_spec(spec_data):
                        self.logger.info("Found OpenAPI spec in YAML format")
                        specs.append({
                            'format': 'yaml',
                            'content': code_block.strip(),
                            'parsed': spec_data,
                            'title': spec_data.get('info', {}).get('title', 'API Specification'),
                            'version': spec_data.get('info', {}).get('version', '1.0.0')
                        })
                        
                except (yaml.YAMLError, json.JSONDecodeError, KeyError, ValueError) as yaml_error:
                    # Not a valid OpenAPI spec, skip this potential spec
                    continue
                    
        # Also look for OpenAPI spec URLs or file references
        spec_url_patterns = [
            r'https?://[^\s]+\.(?:json|yaml|yml)',  # Direct spec file URLs
            r'https?://[^\s]+/openapi[^\s]*',       # URLs containing 'openapi'
            r'https?://[^\s]+/swagger[^\s]*',       # URLs containing 'swagger'
            r'https?://[^\s]+/api-docs[^\s]*',      # URLs containing 'api-docs'
        ]
        
        for pattern in spec_url_patterns:
            urls = re.findall(pattern, text, re.IGNORECASE)
            for url in urls:
                if self._is_valid_url(url):
                    specs.append({
                        'format': 'url',
                        'content': url,
                        'parsed': None,
                        'title': 'External API Specification',
                        'version': 'Unknown'
                    })
        
        if specs:
            self.logger.info(f"Found {len(specs)} OpenAPI specifications")
        
        return specs
    
    def _is_openapi_spec(self, data: Dict[str, Any]) -> bool:
        """Check if the parsed data is an OpenAPI specification."""
        if not isinstance(data, dict):
            return False
            
        # Check for OpenAPI 3.x indicators
        if 'openapi' in data and isinstance(data['openapi'], str):
            return True
            
        # Check for Swagger 2.0 indicators
        if 'swagger' in data and data['swagger'] == '2.0':
            return True
            
        # Check for common OpenAPI structure
        required_fields = ['info', 'paths']
        if all(field in data for field in required_fields):
            # Additional validation - check if info has title
            info = data.get('info', {})
            if isinstance(info, dict) and 'title' in info:
                return True
                
        return False
    
    async def _process_openapi_spec(self, spec: Dict[str, Any], session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and store OpenAPI specification."""
        try:
            project_name = session.get('project_name', 'unknown-project')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Generate filename based on spec format
            if spec['format'] == 'json':
                filename = f"openapi_spec_{timestamp}.json"
                content_type = 'application/json'
            elif spec['format'] == 'yaml':
                filename = f"openapi_spec_{timestamp}.yaml"
                content_type = 'application/x-yaml'
            else:  # URL format
                return {
                    'type': 'openapi_spec',
                    'title': spec['title'],
                    'version': spec['version'],
                    'format': spec['format'],
                    'url': spec['content'],
                    'swagger_ui_url': f"/swagger-ui?url={spec['content']}",
                    'timestamp': timestamp
                }
            
            # Store the spec file in S3
            s3_key = f"projects/{project_name}/generated-code/{timestamp}/{filename}"
            
            try:
                await self.s3_storage_service.store_file(
                    content=spec['content'],
                    s3_key=s3_key,
                    content_type=content_type
                )
                
                # Also store in 'latest' folder for easy access
                latest_s3_key = f"projects/{project_name}/generated-code/latest/{filename}"
                await self.s3_storage_service.store_file(
                    content=spec['content'],
                    s3_key=latest_s3_key,
                    content_type=content_type
                )
                
                self.logger.info(f"Stored OpenAPI spec: {s3_key}")
                
                # Generate S3 URL for the spec
                spec_url = f"https://{self.s3_storage_service.bucket_name}.s3.amazonaws.com/{s3_key}"
                
                return {
                    'type': 'openapi_spec',
                    'title': spec['title'],
                    'version': spec['version'],
                    'format': spec['format'],
                    'filename': filename,
                    's3_key': s3_key,
                    'url': spec_url,
                    'swagger_ui_url': f"/swagger-ui?url={spec_url}",
                    'content': spec['content'],
                    'parsed': spec.get('parsed'),
                    'timestamp': timestamp,
                    'project_name': project_name
                }
                
            except Exception as storage_error:
                self.logger.error(f"Failed to store OpenAPI spec: {storage_error}")
                # Return spec data even if storage failed, for immediate display
                return {
                    'type': 'openapi_spec',
                    'title': spec['title'],
                    'version': spec['version'],
                    'format': spec['format'],
                    'content': spec['content'],
                    'parsed': spec.get('parsed'),
                    'timestamp': timestamp,
                    'project_name': project_name,
                    'storage_error': str(storage_error)
                }
                
        except Exception as e:
            self.logger.error(f"Error processing OpenAPI spec: {e}")
            return None
    
    def _extract_jira_tickets(self, text: str) -> List[Dict[str, str]]:
        """Extract Jira ticket information from text with improved description handling."""
        tickets = []
        
        # Debug: Log the text we're processing
        self.logger.info(f"Extracting Jira tickets from text (length: {len(text)})")
        if "api.atlassian.com" in text:
            self.logger.info("Text contains Jira API URLs")
        
        # First, look for structured data in HTML comments (new format)
        comment_pattern = r'<!-- JIRA_TICKET_DATA: ({[^}]+}) -->'
        url_pattern = r'<!-- JIRA_TICKET_URL: ([^\s]+) -->'
        
        comment_matches = re.findall(comment_pattern, text)
        url_matches = re.findall(url_pattern, text)
        
        self.logger.info(f"HTML comment ticket data found: {len(comment_matches)}")
        self.logger.info(f"HTML comment URLs found: {len(url_matches)}")
        
        # Process structured data from HTML comments
        for i, ticket_json in enumerate(comment_matches):
            try:
                import json
                ticket_data = json.loads(ticket_json)
                
                # Get corresponding URL if available
                browse_url = url_matches[i] if i < len(url_matches) else f"https://anycompanyreads.atlassian.net/browse/{ticket_data.get('key', 'Unknown')}"
                
                # Extract summary from the surrounding text
                ticket_key = ticket_data.get('key', 'Unknown')
                ticket_summary = self._extract_ticket_summary_from_context(text, ticket_key)
                
                tickets.append({
                    'key': ticket_data.get('key', 'Unknown'),
                    'id': ticket_data.get('id', 'Unknown'),
                    'url': browse_url,
                    'summary': ticket_summary,
                    'description': 'Detailed implementation requirements and acceptance criteria.',
                    'status': 'Open',
                    'issue_type': 'New Feature'
                })
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse ticket JSON from comment: {e}")
        
        # If we found tickets from HTML comments, return them
        if tickets:
            self.logger.info(f"Successfully extracted {len(tickets)} tickets from HTML comments")
            return tickets
        
        # Fallback: Look for JSON-formatted Jira ticket data in the response (old format)
        # Pattern: {"id":"10354","key":"CS-42","self":"https://api.atlassian.com/ex/jira/.../issue/10354"}
        json_pattern = r'\{"id":"(\d+)","key":"(CS-\d+)","self":"(https://api\.atlassian\.com/ex/jira/[^"]+)"\}'
        json_matches = re.findall(json_pattern, text)
        
        self.logger.info(f"JSON pattern matches found: {len(json_matches)}")
        
        for ticket_id, key, url in json_matches:
            # Try to extract more detailed information about this ticket
            ticket_summary = f"Feature Request - {key}"  # Default
            ticket_description = "Detailed implementation requirements and acceptance criteria."  # Default
            
            # Look for ticket information in the AI response context
            key_index = text.find(key)
            if key_index != -1:
                # Look in a larger window around the ticket key for context
                context_start = max(0, key_index - 500)
                context_end = min(len(text), key_index + 500)
                context = text[context_start:context_end]
                
                # Try to find a summary/title in this context
                summary_patterns = [
                    r'(?:Summary|Title|Subject):\s*([^\n]+)',
                    r'\*\*(?:Summary|Title|Subject)\*\*:\s*([^\n]+)',
                    r'•\s*([^•\n]{10,100})',  # Bullet points with reasonable length
                    r'(?:Creating|Created)\s+ticket[^:]*:\s*([^\n]+)',  # "Creating ticket: Title"
                ]
                
                for pattern in summary_patterns:
                    context_matches = re.findall(pattern, context, re.IGNORECASE)
                    if context_matches:
                        candidate = context_matches[0].strip()
                        if len(candidate) > 5 and not candidate.isdigit() and not candidate.startswith('http'):
                            ticket_summary = candidate
                            break
                
                # Try to find description/details in this context
                description_patterns = [
                    r'(?:Description|Details?):\s*([^\n]+(?:\n[^\n]+)*)',
                    r'\*\*(?:Description|Details?)\*\*:\s*([^\n]+(?:\n[^\n]+)*)',
                    r'(?:Acceptance Criteria|Requirements?):\s*([^\n]+(?:\n[^\n]+)*)',
                ]
                
                for pattern in description_patterns:
                    desc_matches = re.findall(pattern, context, re.IGNORECASE | re.DOTALL)
                    if desc_matches:
                        candidate = desc_matches[0].strip()
                        if len(candidate) > 10:
                            ticket_description = candidate[:500]  # Limit length
                            break
            
            # Convert API URL to user-friendly browse URL
            browse_url = url
            if 'api.atlassian.com' in url:
                browse_url = f"https://anycompanyreads.atlassian.net/browse/{key}"
            
            tickets.append({
                'key': key,
                'id': ticket_id,
                'url': browse_url,  # Use browse URL instead of API URL
                'summary': ticket_summary,
                'description': ticket_description,
                'status': 'Open',
                'issue_type': 'New Feature'
            })
        
        # Look for ticket summaries/titles in various formats (do this for all tickets)
        summary_patterns = [
            r'(?:Summary|summary):\s*([^\n]+)',
            r'(?:Title|title):\s*([^\n]+)',
            r'(?:Subject|subject):\s*([^\n]+)',
            r'(?:Description|description):\s*([^\n]+)',
            # Look for ticket titles in structured format like "**Title**: Some Title"
            r'\*\*(?:Title|Summary|Subject)\*\*:\s*([^\n]+)',
            # Look for bullet points that might be ticket titles
            r'•\s*([^•\n]+?)(?:\s*-\s*CS-\d+|\s*\(CS-\d+\))',
            # Look for lines that contain ticket keys and might have titles
            r'(.*?)\s*(?:-\s*)?(?:CS-\d+|Issue Key:|Issue ID:)',
        ]
        
        summary_matches = []
        for pattern in summary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            summary_matches.extend(matches)
            if matches:
                self.logger.info(f"Found {len(matches)} summaries with pattern: {pattern}")
        
        # Clean up summary matches - remove empty strings and common non-title text
        cleaned_summaries = []
        for summary in summary_matches:
            summary = summary.strip()
            
            # Skip if it's too short, contains only numbers, or is common metadata
            if (len(summary) > 5 and 
                not summary.isdigit() and 
                not summary.startswith('http') and
                'Issue Key' not in summary and
                'Issue ID' not in summary and
                'URL' not in summary):
                cleaned_summaries.append(summary)
        
        summary_matches = cleaned_summaries[:10]  # Limit to first 10 reasonable summaries

        # Fallback: Look for structured ticket information in the AI response
        if not tickets:
            self.logger.info("No JSON matches found, trying fallback patterns")
            
            # Look for the actual format in the AI response:
            # - **Issue Key**: CS-46
            # - **Issue ID**: 10358
            # - **URL**: https://api.atlassian.com/ex/jira/.../issue/10358
            
            # Updated patterns to match the actual AI response format
            jira_key_pattern = r'\*\*Issue Key\*\*:\s*(CS-\d+)'
            jira_id_pattern = r'\*\*Issue ID\*\*:\s*(\d+)'
            jira_url_pattern = r'\*\*URL\*\*:\s*(https://api\.atlassian\.com/ex/jira/[^\s]+/rest/api/3/issue/\d+)'
            
            # Find ticket keys, IDs, and URLs
            key_matches = re.findall(jira_key_pattern, text)
            id_matches = re.findall(jira_id_pattern, text)
            url_matches = re.findall(jira_url_pattern, text)
            
            self.logger.info(f"Fallback patterns - Keys: {len(key_matches)}, IDs: {len(id_matches)}, URLs: {len(url_matches)}")
            self.logger.info(f"Key matches: {key_matches}")
            self.logger.info(f"ID matches: {id_matches}")
            self.logger.info(f"URL matches: {url_matches}")
            
            # Extract ticket information from structured format
            ticket_blocks = re.findall(r'Ticket \d+:\s*•\s*Issue Key: (CS-\d+)\s*•\s*Issue ID: (\d+)\s*•\s*URL: (https://[^\s]+)', text)
            
            for key, ticket_id, url in ticket_blocks:
                tickets.append({
                    'key': key,
                    'id': ticket_id,
                    'url': url,
                    'summary': 'Generated Ticket',
                    'status': 'Open',
                    'issue_type': 'New Feature'
                })
            
            # If we have matches, combine them into tickets
            if key_matches and id_matches and url_matches:
                # We should have the same number of keys, IDs, and URLs
                max_tickets = min(len(key_matches), len(id_matches), len(url_matches))
                for i in range(max_tickets):
                    # Try to get a meaningful summary
                    if i < len(summary_matches) and summary_matches[i]:
                        summary = summary_matches[i]
                    else:
                        # Generate a more descriptive default based on the ticket key
                        summary = f"Feature Request - {key_matches[i]}"
                    
                    ticket = {
                        'key': key_matches[i],
                        'id': id_matches[i],
                        'url': url_matches[i],
                        'summary': summary,
                        'status': 'Open',
                        'issue_type': 'New Feature'
                    }
                    tickets.append(ticket)
            elif not tickets and (key_matches or id_matches or url_matches):
                # Fallback if we don't have all three but have some
                max_tickets = max(len(key_matches), len(id_matches), len(url_matches))
                for i in range(max_tickets):
                    key = key_matches[i] if i < len(key_matches) else f'CS-{i+1}'
                    
                    # Try to get a meaningful summary
                    if i < len(summary_matches) and summary_matches[i]:
                        summary = summary_matches[i]
                    else:
                        # Generate a more descriptive default based on the ticket key
                        summary = f"Feature Request - {key}"
                    
                    ticket = {
                        'key': key,
                        'id': id_matches[i] if i < len(id_matches) else str(i+1),
                        'url': url_matches[i] if i < len(url_matches) else '',
                        'summary': summary,
                        'status': 'Open',
                        'issue_type': 'New Feature'
                    }
                    tickets.append(ticket)
        
        if tickets:
            self.logger.info(f"Extracted {len(tickets)} Jira tickets from response")
            for i, ticket in enumerate(tickets):
                self.logger.info(f"Final extracted ticket {i+1}: Key={ticket['key']}, Summary='{ticket['summary']}', URL={ticket['url']}")
        else:
            self.logger.warning("No Jira tickets extracted from response")
            
        # Debug: Log summary extraction results
        if summary_matches:
            self.logger.info(f"Found {len(summary_matches)} potential summaries: {summary_matches[:5]}")  # Log first 5
        
        return tickets
    
    def _extract_ticket_summary_from_context(self, text: str, ticket_key: str) -> str:
        """Extract ticket summary from the context around the ticket key."""
        try:
            # Look for the ticket key in the text
            key_index = text.find(ticket_key)
            if key_index == -1:
                return f"Feature Request - {ticket_key}"
            
            # Look in a larger window around the ticket key for context
            context_start = max(0, key_index - 1000)
            context_end = min(len(text), key_index + 1000)
            context = text[context_start:context_end]
            
            # Try to find a summary/title in this context
            summary_patterns = [
                rf'\*\*🎫 Ticket \d+: {re.escape(ticket_key)}\*\*',  # Our formatted ticket header
                r'(?:Summary|Title|Subject):\s*([^\n]+)',
                r'\*\*(?:Summary|Title|Subject)\*\*:\s*([^\n]+)',
                r'•\s*([^•\n]{10,100})',  # Bullet points with reasonable length
                r'(?:Creating|Created)\s+ticket[^:]*:\s*([^\n]+)',  # "Creating ticket: Title"
                r'"summary":\s*"([^"]+)"',  # JSON summary field
            ]
            
            for pattern in summary_patterns:
                context_matches = re.findall(pattern, context, re.IGNORECASE)
                if context_matches:
                    candidate = context_matches[0].strip()
                    if len(candidate) > 5 and not candidate.isdigit() and not candidate.startswith('http'):
                        return candidate
            
            # If no specific summary found, try to extract from the tool call arguments
            tool_call_pattern = r'"summary":\s*"([^"]+)"'
            tool_matches = re.findall(tool_call_pattern, context)
            if tool_matches:
                return tool_matches[0]
            
            return f"Feature Request - {ticket_key}"
            
        except Exception as e:
            self.logger.warning(f"Error extracting ticket summary for {ticket_key}: {e}")
            return f"Feature Request - {ticket_key}"
    
    def _extract_tool_result_content(self, ai_response: str) -> str:
        """Extract only the tool result content from the AI response."""
        # Look for tool result patterns
        tool_result_patterns = [
            r'📄 Tool Result:(.*?)(?=\n\n[^📄]|\Z)',  # Tool Result: content until next section
            r'Tool Result:(.*?)(?=\n\n[^T]|\Z)',      # Alternative Tool Result pattern
            r'Based on.*?documentation[^:]*:(.*?)(?=\n\n|\Z)',  # "Based on documentation:" pattern
        ]
        
        for pattern in tool_result_patterns:
            match = re.search(pattern, ai_response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                self.logger.info(f"Found tool result content (length: {len(content)})")
                return content
        
        # If no specific tool result pattern found, look for content between specific markers
        # that indicate the start and end of tool output
        lines = ai_response.split('\n')
        tool_content_lines = []
        in_tool_result = False
        
        for line in lines:
            # Start capturing when we see tool result indicators
            if any(indicator in line.lower() for indicator in ['tool result', '📄', 'based on', 'analyzed']):
                in_tool_result = True
                continue
            
            # Stop capturing when we see AI commentary indicators
            if in_tool_result and any(indicator in line.lower() for indicator in [
                'let me know', 'i can', 'would suggest', 'here are', 'i\'ve', 'once the'
            ]):
                break
            
            if in_tool_result:
                tool_content_lines.append(line)
        
        if tool_content_lines:
            content = '\n'.join(tool_content_lines).strip()
            self.logger.info(f"Extracted tool content from markers (length: {len(content)})")
            return content
        
        self.logger.warning("No tool result content found in AI response")
        return ""
    
    def _parse_tool_result_json(self, tool_result_content: str) -> str:
        """Parse JSON tool result content and extract the formatted text."""
        try:
            import json
            
            # Try to parse as JSON
            if tool_result_content.strip().startswith('{'):
                data = json.loads(tool_result_content)
                
                # Handle Amazon Q Business response format
                if 'content' in data and isinstance(data['content'], list):
                    for item in data['content']:
                        if item.get('type') == 'text' and 'text' in item:
                            # Decode unicode escape sequences
                            text_content = item['text']
                            # Replace unicode bullet points and newlines
                            text_content = text_content.replace('\\u2022', '•')
                            text_content = text_content.replace('\\n', '\n')
                            self.logger.info(f"Successfully parsed JSON tool result (length: {len(text_content)})")
                            return text_content
                
                # Handle other JSON formats
                if 'text' in data:
                    return data['text']
                
                # If it's a simple JSON object, convert to string
                return str(data)
            
            # If not JSON, return as-is
            return tool_result_content
            
        except json.JSONDecodeError:
            self.logger.warning("Tool result content is not valid JSON, returning as-is")
            return tool_result_content
        except Exception as e:
            self.logger.error(f"Error parsing tool result JSON: {e}")
            return tool_result_content
    
    def _format_amazon_q_response(self, ai_response: str) -> str:
        """Format Amazon Q Business response by parsing JSON content and converting to readable text."""
        try:
            # Look for JSON content in the response
            import re
            import json
            
            # Look for JSON blocks that contain the Amazon Q response
            # The pattern needs to handle nested JSON and multiline content
            json_pattern = r'\{"content":\s*\[\{"type":\s*"text",\s*"text":\s*"(.*?)"\}\]\}'
            matches = re.findall(json_pattern, ai_response, re.DOTALL)
            
            if matches:
                # Take the first (and usually only) match
                json_text = matches[0]
                
                # Decode unicode escape sequences
                formatted_text = json_text.replace('\\u2022', '•')  # Convert bullet points
                formatted_text = formatted_text.replace('\\n', '\n')  # Convert newlines
                formatted_text = formatted_text.replace('\\"', '"')   # Convert escaped quotes
                formatted_text = formatted_text.replace('\\\\', '\\')  # Convert double backslashes
                
                self.logger.info(f"Successfully formatted Amazon Q response (length: {len(formatted_text)})")
                return formatted_text
            
            # Alternative: Look for any JSON structure with content array
            json_blocks = re.findall(r'\{.*?"content".*?\}', ai_response, re.DOTALL)
            for json_block in json_blocks:
                try:
                    data = json.loads(json_block)
                    if 'content' in data and isinstance(data['content'], list):
                        for item in data['content']:
                            if item.get('type') == 'text' and 'text' in item:
                                text_content = item['text']
                                # Decode unicode escape sequences
                                text_content = text_content.replace('\\u2022', '•')
                                text_content = text_content.replace('\\n', '\n')
                                self.logger.info(f"Successfully parsed JSON block (length: {len(text_content)})")
                                return text_content
                except json.JSONDecodeError:
                    continue
            
            # If no JSON found, return the original response
            self.logger.info("No JSON content found in Amazon Q response, using original")
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error formatting Amazon Q response: {e}")
            return ai_response

    def _extract_epics(self, text: str) -> List[Dict[str, Any]]:
        """Extract epic information from text - simplified and filtered."""
        epics = []
        
        self.logger.info(f"Extracting epics from text (length: {len(text)})")
        
        # FIRST: Filter out TOOL_CALL text to prevent it from being treated as epics
        if "TOOL_CALL:" in text:
            self.logger.info("Filtering out TOOL_CALL text from epic extraction")
            # Remove TOOL_CALL lines completely
            lines = text.split('\n')
            filtered_lines = []
            for line in lines:
                if not line.strip().startswith('TOOL_CALL:') and 'TOOL_CALL' not in line:
                    filtered_lines.append(line)
            text = '\n'.join(filtered_lines)
            self.logger.info(f"Filtered text length: {len(text)}")
        
        # Look for ONLY proper epic headers - be much more strict
        epic_patterns = [
            r'## ([^#\n]*Epic[^#\n]*)',  # ## User Management Epic 
            r'###\s*([^#\n]*Epic[^#\n]*)', # ### User Management Epic
            r'^\s*([A-Za-z\s]+Epic)\s*$',   # Plain epic titles on their own line (strict)
        ]
        
        epic_matches = []
        for pattern in epic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                self.logger.info(f"Found {len(matches)} epics with pattern: {pattern}")
                epic_matches.extend(matches)
                break  # Use first pattern that matches
        
        if epic_matches:
            self.logger.info(f"Processing {len(epic_matches)} epic matches: {epic_matches}")
            
            # Debug: Log a sample of the text to see what we're working with
            sample_text = text[:1000] + "..." if len(text) > 1000 else text
            self.logger.info(f"Sample text being processed: {sample_text}")
            
            # Split text by epic headers to get sections
            split_patterns = [
                r'📋\s*([^#\n]*Epic[^#\n]*)',  # 📋 User Management Epic
                r'## ([^#\n]*Epic[^#\n]*)',
                r'## Epic \d+: ([^\n]+)',
                r'\*\*([^*]*Epic[^*]*)\*\*',
                r'###\s*([^#\n]*Epic[^#\n]*)',
                r'^([^#\n]*Epic[^#\n]*)$'  # Plain epic titles
            ]
            
            sections = []
            for pattern in split_patterns:
                sections = re.split(pattern, text, flags=re.IGNORECASE)
                if len(sections) > 1:
                    break
            
            # Process each epic section
            for i in range(1, len(sections), 2):  # Skip empty sections, take title and content pairs
                if i + 1 < len(sections):
                    title = sections[i].strip()
                    content = sections[i + 1].strip()
                    
                    # Extract features (bullet points) - be more aggressive in finding them
                    features = []
                    feature_patterns = [
                        r'[•]\s*([^\n]+)',      # Bullet points with • (preferred)
                        r'[\-\*]\s*([^\n]+)',   # Dash or asterisk bullets
                        r'^\s*-\s*([^\n]+)',    # Dash bullets at start of line
                        r'^\s*\*\s*([^\n]+)',   # Asterisk bullets at start of line
                        r'^\s*•\s*([^\n]+)',    # Bullet points at start of line
                    ]
                    
                    for feature_pattern in feature_patterns:
                        feature_matches = re.findall(feature_pattern, content, re.MULTILINE)
                        if feature_matches:
                            # Clean up features and filter out empty ones
                            features = [f.strip() for f in feature_matches if f.strip() and len(f.strip()) > 3]
                            if features:  # Only break if we found meaningful features
                                break
                    
                    # Filter out unwanted meta-text that got picked up as "epics"
                    if self._is_valid_epic_title(title) and (features or len(content) > 20):  # Only add if we have features or substantial content
                        # Create a clean description that doesn't duplicate the features
                        # Extract any text that comes before the bullet points
                        content_lines = content.split('\n')
                        description_lines = []
                        
                        for line in content_lines:
                            line = line.strip()
                            # Stop when we hit bullet points
                            if line.startswith(('•', '-', '*')) or re.match(r'^\s*[•\-\*]', line):
                                break
                            # Add non-empty lines that aren't bullet points
                            if line and not re.match(r'^\s*[•\-\*]', line):
                                description_lines.append(line)
                        
                        # Create description from non-bullet content, or generate a default
                        if description_lines:
                            description = ' '.join(description_lines)
                        else:
                            # Generate a clean description based on the title
                            clean_title = title.replace('Epic', '').strip()
                            description = f"Epic focused on {clean_title.lower()} functionality and requirements"
                        
                        # Limit description length
                        if len(description) > 150:
                            description = description[:150] + '...'
                        
                        epic = {
                            'title': title,
                            'description': description,
                            'features': features
                        }
                        epics.append(epic)
                        self.logger.info(f"Added epic: {title} with {len(features)} features and description: {description[:50]}...")
                    else:
                        self.logger.info(f"Filtered out invalid epic title: {title}")
        
        # NO FALLBACK - only extract properly formatted epics
        # This prevents TOOL_CALL text from being treated as epics
        
        if epics:
            self.logger.info(f"Successfully extracted {len(epics)} epics from response")
            for i, epic in enumerate(epics):
                self.logger.info(f"Epic {i+1}: '{epic['title']}' with {len(epic['features'])} features")
        else:
            self.logger.warning("No epics extracted from response")
        
        return epics
    
    def _is_valid_epic_title(self, title: str) -> bool:
        """Check if a title is a valid epic title (not meta-text)."""
        if not title or len(title.strip()) < 3:
            return False
        
        # Filter out titles that contain meta-text patterns
        invalid_patterns = [
            r'TOOL_CALL',  # TOOL_CALL text
            r'\{.*server_id.*\}',  # JSON tool call patterns
            r'capability.*arguments',  # Tool call parameters
            r'\[Name\]',  # [Name] Epic pattern from instructions
            r'bullet points with',  # Meta-text about formatting
            r'Include estimates',  # Meta-text about story points
            r'story points',  # Meta-text about story points
            r'\"\}\}',  # JSON artifacts
            r'Format the response',  # Meta-text about formatting
            r'amazon-q-business',  # Server names
            r'mcp_amazon_q_business',  # Tool names
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return False
        
        return True
    
    async def _process_jira_tickets(self, tickets: List[Dict[str, str]], session: Dict[str, Any]) -> None:
        """Process and store Jira tickets."""
        try:
            if not tickets:
                return
            
            project_name = session.get('project_name', 'unknown-project')
            self.logger.info(f"Processing {len(tickets)} Jira tickets for project: {project_name}")
            
            # Debug: Log the extracted tickets
            for i, ticket in enumerate(tickets):
                self.logger.info(f"Extracted ticket {i+1}: {ticket}")
            
            # Import and use Jira storage service
            from services.jira_storage_service import JiraStorageService
            jira_service = JiraStorageService()
            
            # Convert to the format expected by the storage service
            tickets_data = []
            for ticket in tickets:
                ticket_data = {
                    'result': f'{{"id":"{ticket["id"]}","key":"{ticket["key"]}","self":"{ticket["url"]}"}}',
                    'summary': ticket['summary'],
                    'description': ticket.get('description', 'No description provided'),
                    'issue_type': ticket['issue_type']
                }
                tickets_data.append(ticket_data)
                self.logger.info(f"Formatted ticket data: {ticket_data}")
            
            success = await jira_service.save_jira_tickets(project_name, tickets_data)
            
            if success:
                self.logger.info(f"✅ Successfully saved {len(tickets)} Jira tickets for project: {project_name}")
            else:
                self.logger.error(f"❌ Failed to save Jira tickets for project: {project_name}")
                
        except Exception as e:
            self.logger.error(f"❌ Error processing Jira tickets: {e}")
    
    async def _process_epics(self, epics: List[Dict[str, Any]], session: Dict[str, Any]) -> None:
        """Process and store epics."""
        try:
            if not epics:
                return
            
            project_name = session.get('project_name', 'unknown-project')
            
            # Import and use Jira storage service
            from services.jira_storage_service import JiraStorageService
            jira_service = JiraStorageService()
            
            success = await jira_service.save_epics(project_name, epics)
            
            if success:
                self.logger.info(f"✅ Successfully saved {len(epics)} epics for project: {project_name}")
            else:
                self.logger.error(f"❌ Failed to save epics for project: {project_name}")
                
        except Exception as e:
            self.logger.error(f"❌ Error processing epics: {e}")
    
    async def _process_diagram_url(self, url: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a diagram URL by downloading and storing it."""
        try:
            project_name = session.get('project_name', 'unknown-project')
            
            # Download the image using the same method as diagram service
            image_data = await self._download_s3_image_data(url)
            if image_data:
                # Generate filename (same approach as diagram service)
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                diagram_name = f"architecture_diagram_{timestamp}"
                format = 'png'
                filename = f"{diagram_name}.{format}"
                
                # Store in S3 using the same method as diagram service
                result = await self.s3_storage_service.save_diagram(
                    project_id=project_name,
                    diagram_name=diagram_name,
                    content=image_data,
                    format=format,
                    metadata={
                        "filename": filename,
                        "project_id": project_name,
                        "original_url": url,
                        "processed_by": "output_processor",
                        "saved_at": datetime.now().isoformat()
                    }
                )
                success = result.success
                
                if success:
                    # Generate local URL for serving
                    local_url = f"/api/diagrams/{project_name}/serve/{filename}"
                    
                    self.logger.info(f"✅ Stored diagram: {filename} → {local_url}")
                    
                    return {
                        'filename': filename,
                        'local_url': local_url,
                        'original_url': url,
                        'project_name': project_name,
                        'timestamp': timestamp,
                        'is_latest': True,  # New diagrams are always latest
                        'type': 'diagram'
                    }
            else:
                self.logger.error(f"❌ Failed to download image data from: {url}")
        
        except Exception as e:
            self.logger.error(f"❌ Failed to process diagram URL {url}: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return None
    
    async def _process_code_block(self, code_block: Dict[str, str], session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a code block by storing it as a file."""
        try:
            project_name = session.get('project_name', 'unknown-project')
            language = code_block.get('language', 'text')
            code = code_block.get('code', '')
            
            # Generate filename based on language
            extensions = {
                'python': 'py',
                'javascript': 'js',
                'typescript': 'ts',
                'yaml': 'yml',
                'json': 'json',
                'terraform': 'tf',
                'cloudformation': 'yaml',
                'dockerfile': 'Dockerfile',
                'bash': 'sh',
                'shell': 'sh'
            }
            
            extension = extensions.get(language.lower(), 'txt')
            
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{language}_{timestamp}.{extension}"
            
            # Store in S3 using save_generated_code method
            files_dict = {filename: code}
            result = await self.s3_storage_service.save_generated_code(
                project_name, files_dict
            )
            
            if result.success:
                self.logger.debug(f"Stored code file: {filename}")
                
                return {
                    'filename': filename,
                    'language': language,
                    'project_name': project_name,
                    'timestamp': timestamp
                }
        
        except Exception as e:
            self.logger.error(f"❌ Failed to process code block: {e}")
        
        return None
    
    async def _process_document_url(self, url: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a document URL by downloading and storing it."""
        try:
            project_name = session.get('project_name', 'unknown-project')
            
            # Download the document
            async with aiohttp.ClientSession() as client_session:
                async with client_session.get(url) as response:
                    if response.status == 200:
                        document_data = await response.read()
                        
                        # Extract filename from URL
                        parsed_url = urlparse(url)
                        original_filename = parsed_url.path.split('/')[-1]
                        
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"document_{timestamp}_{original_filename}"
                        
                        # For now, skip document storage as there's no specific method
                        # TODO: Implement document storage method in S3StorageService
                        success = False
                        self.logger.info(f"Document storage not implemented yet: {filename}")
                        
                        if success:
                            self.logger.info(f"✅ Stored document: {filename}")
                            
                            return {
                                'filename': filename,
                                'original_url': url,
                                'project_name': project_name,
                                'timestamp': timestamp,
                                's3_key': s3_key
                            }
        
        except Exception as e:
            self.logger.error(f"❌ Failed to process document URL {url}: {e}")
        
        return None
    
    async def _download_s3_image_data(self, s3_url: str) -> Optional[bytes]:
        """Download image data from S3 (same method as diagram service)."""
        try:
            self.logger.info(f"Starting S3 download for URL: {s3_url}")
            
            # Clean the URL
            s3_url = s3_url.rstrip("'}")
            
            # Parse S3 URL to get bucket and key
            from urllib.parse import urlparse
            parsed = urlparse(s3_url)
            
            # Handle different S3 URL formats
            if parsed.netloc.endswith('.s3.amazonaws.com'):
                bucket_name = parsed.netloc.split('.')[0]
                key = parsed.path.lstrip('/')
            elif 's3.amazonaws.com' in parsed.netloc:
                path_parts = parsed.path.lstrip('/').split('/', 1)
                bucket_name = path_parts[0]
                key = path_parts[1] if len(path_parts) > 1 else ''
            else:
                raise ValueError(f"Unsupported S3 URL format: {s3_url}")
            
            # Download the object
            import boto3
            from config.settings import settings
            s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            image_data = response['Body'].read()
            
            self.logger.info(f"Successfully downloaded image data ({len(image_data)} bytes)")
            return image_data
                
        except Exception as e:
            self.logger.error(f"Error downloading S3 image: {e}")
            return None

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False