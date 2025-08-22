"""
OpenAPI Specification Formatter Utility

This utility handles formatting and cleaning of OpenAPI specifications,
especially when dealing with parse errors and raw content extraction.
"""

import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OpenAPIFormatter:
    """Utility class for formatting and cleaning OpenAPI specifications."""
    
    @staticmethod
    def extract_and_format_spec(response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract and format OpenAPI spec from response data.
        
        Args:
            response_data: The response from OpenAPI generation tool
            
        Returns:
            Properly formatted OpenAPI spec dictionary or None if parsing fails
        """
        try:
            # Check if this is a parse error response with raw content
            if 'x-parse-error' in response_data and 'x-raw-generated-content' in response_data:
                logger.info(f"Parse error detected: {response_data['x-parse-error']}")
                raw_content = response_data['x-raw-generated-content']
                return OpenAPIFormatter._parse_raw_content(raw_content)
            
            # Check if this is already a valid OpenAPI spec
            elif 'openapi' in response_data and 'info' in response_data:
                return response_data
            
            # Try to parse as JSON string
            elif isinstance(response_data, str):
                return OpenAPIFormatter._parse_raw_content(response_data)
            
            else:
                logger.warning("Unknown response format for OpenAPI spec")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting OpenAPI spec: {e}")
            return None
    
    @staticmethod
    def _parse_raw_content(raw_content: str) -> Optional[Dict[str, Any]]:
        """Parse raw content string into OpenAPI spec."""
        try:
            # Clean up the raw content
            cleaned_content = OpenAPIFormatter._clean_raw_content(raw_content)
            
            # Try to parse as JSON
            spec = json.loads(cleaned_content)
            
            # Validate it's an OpenAPI spec
            if not OpenAPIFormatter._is_valid_openapi_spec(spec):
                logger.warning("Parsed content is not a valid OpenAPI spec")
                return None
            
            return spec
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            # Try to fix common JSON issues
            try:
                fixed_content = OpenAPIFormatter._fix_json_issues(cleaned_content)
                spec = json.loads(fixed_content)
                
                if OpenAPIFormatter._is_valid_openapi_spec(spec):
                    logger.info("Successfully fixed JSON formatting issues")
                    return spec
                else:
                    logger.warning("Fixed JSON is not a valid OpenAPI spec")
                    return None
                    
            except json.JSONDecodeError:
                logger.error("Could not fix JSON formatting issues")
                return None
        
        except Exception as e:
            logger.error(f"Error parsing raw content: {e}")
            return None
    
    @staticmethod
    def _clean_raw_content(raw_content: str) -> str:
        """Clean up raw content by removing literal escape characters."""
        try:
            # Remove literal \n, \r, \t characters and replace with actual whitespace
            cleaned = raw_content.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
            
            # Remove any leading/trailing whitespace
            cleaned = cleaned.strip()
            
            # If the content is wrapped in quotes, remove them
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            
            # Handle escaped quotes within the content
            cleaned = cleaned.replace('\\"', '"')
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning raw content: {e}")
            return raw_content
    
    @staticmethod
    def _fix_json_issues(json_content: str) -> str:
        """Fix common JSON formatting issues."""
        try:
            # Remove trailing commas before closing braces/brackets
            json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
            
            # Fix missing commas between object properties (basic cases)
            json_content = re.sub(r'}\s*"', '}, "', json_content)
            json_content = re.sub(r']\s*"', '], "', json_content)
            
            # Fix spacing around colons and commas
            json_content = re.sub(r':\s*(["\d\[\{])', r': \1', json_content)
            json_content = re.sub(r',\s*(["\d\[\{])', r', \1', json_content)
            
            # Remove any control characters that might cause issues
            json_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_content)
            
            return json_content
            
        except Exception as e:
            logger.error(f"Error fixing JSON issues: {e}")
            return json_content
    
    @staticmethod
    def _is_valid_openapi_spec(spec: Dict[str, Any]) -> bool:
        """Check if the parsed content is a valid OpenAPI specification."""
        try:
            # Check for required OpenAPI fields
            required_fields = ['openapi', 'info']
            if not all(field in spec for field in required_fields):
                return False
            
            # Check OpenAPI version format
            openapi_version = spec.get('openapi', '')
            if not re.match(r'3\.\d+\.\d+', openapi_version):
                return False
            
            # Check info object has required fields
            info = spec.get('info', {})
            if not isinstance(info, dict) or 'title' not in info or 'version' not in info:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating OpenAPI spec: {e}")
            return False
    
    @staticmethod
    def format_spec_for_file(spec: Dict[str, Any], indent: int = 2) -> str:
        """Format OpenAPI spec as a properly indented JSON string for file output."""
        try:
            return json.dumps(spec, indent=indent, ensure_ascii=False, separators=(',', ': '))
        except Exception as e:
            logger.error(f"Error formatting spec for file: {e}")
            return json.dumps(spec)
    
    @staticmethod
    def create_spec_file(spec: Dict[str, Any], file_path: str) -> bool:
        """Create an OpenAPI spec file at the specified path."""
        try:
            formatted_content = OpenAPIFormatter.format_spec_for_file(spec)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            logger.info(f"Successfully created OpenAPI spec file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating spec file {file_path}: {e}")
            return False
    
    @staticmethod
    def validate_and_fix_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix common issues in OpenAPI specs."""
        try:
            # Ensure required fields exist
            if 'openapi' not in spec:
                spec['openapi'] = '3.1.0'
            
            if 'info' not in spec:
                spec['info'] = {
                    'title': 'Generated API',
                    'version': '1.0.0'
                }
            elif not isinstance(spec['info'], dict):
                spec['info'] = {
                    'title': 'Generated API',
                    'version': '1.0.0'
                }
            else:
                if 'title' not in spec['info']:
                    spec['info']['title'] = 'Generated API'
                if 'version' not in spec['info']:
                    spec['info']['version'] = '1.0.0'
            
            # Ensure paths is an object
            if 'paths' not in spec:
                spec['paths'] = {}
            elif not isinstance(spec['paths'], dict):
                spec['paths'] = {}
            
            # Ensure components is an object if it exists
            if 'components' in spec and not isinstance(spec['components'], dict):
                spec['components'] = {}
            
            return spec
            
        except Exception as e:
            logger.error(f"Error validating and fixing spec: {e}")
            return spec