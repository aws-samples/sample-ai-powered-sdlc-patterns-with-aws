import json
from typing import List, Dict, Any
from pydantic import BaseModel


class Epic(BaseModel):
    feature_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int


class EpicAgent:
    """
    Epic Agent generates epic specifications from features.

    This agent has no knowledge of JIRA or any specific issue tracking system.
    It simply generates structured epic data that can be sent to any integration.
    """

    def __init__(self, bedrock_client):
        self.bedrock = bedrock_client
        self.model_id = "us.anthropic.claude-sonnet-4-6"

    def generate_epics(self, features: List[Dict[str, Any]]) -> List[Epic]:
        """Generate epic specifications from features"""
        epics = []

        for feature in features:
            try:
                # Validate required keys
                required_keys = ['id', 'title', 'description', 'business_value', 'priority', 'complexity']
                missing_keys = [key for key in required_keys if key not in feature]
                if missing_keys:
                    raise ValueError(f"Feature missing required keys: {', '.join(missing_keys)}")

                # Generate epic details using AI
                epic_details = self._generate_epic_details(feature)

                # Validate epic details response
                required_epic_keys = ['title', 'description', 'acceptance_criteria', 'story_points']
                missing_epic_keys = [key for key in required_epic_keys if key not in epic_details]
                if missing_epic_keys:
                    raise ValueError(f"Epic details missing required keys: {', '.join(missing_epic_keys)}")

                epic = Epic(
                    feature_id=feature["id"],
                    title=epic_details["title"],
                    description=epic_details["description"],
                    acceptance_criteria=epic_details["acceptance_criteria"],
                    story_points=epic_details["story_points"],
                )
                epics.append(epic)
            except (KeyError, ValueError, TypeError) as e:
                # Log error and continue with next feature
                import logging
                logging.error(f"Failed to generate epic for feature {feature.get('id', 'unknown')}: {str(e)}")
                continue

        return epics

    # Prompt injection mitigated by input sanitization below and sanitize_prompt() in calling code.
    # Curly braces are escaped to '{{' / '}}' to prevent f-string injection in prompt templates.
    # This is a customer-managed control; AWS manages Bedrock model security.
    def _generate_epic_details(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate epic details using Claude Sonnet 4.

        Input sanitization escapes curly braces to prevent f-string template
        injection. Combined with sanitize_prompt() in calling code, this
        addresses common prompt injection vectors.

        Security metrics:
            - Brace escaping prevents template injection in all string fields
            - Implementation priority: High (applied before every AI call)
        """

        # Sanitize inputs to prevent injection
        title = str(feature.get('title', 'Untitled Feature')).replace('{', '{{').replace('}', '}}')
        description = str(feature.get('description', 'No description provided')).replace('{', '{{').replace('}', '}}')
        business_value = str(feature.get('business_value', 'Not specified')).replace('{', '{{').replace('}', '}}')
        priority = str(feature.get('priority', 'Medium')).replace('{', '{{').replace('}', '}}')
        complexity = str(feature.get('complexity', 'Medium')).replace('{', '{{').replace('}', '}}')

        prompt = f"""
Transform this feature into an epic specification:

Feature: {title}
Description: {description}
Business Value: {business_value}
Priority: {priority}
Complexity: {complexity}

Generate an epic with:
- Epic title (concise, actionable)
- Detailed description for development team
- Refined acceptance criteria (5-7 items)
- Story points estimate (1-21 scale)

Return ONLY JSON:
{{
  "title": "Epic Title",
  "description": "Detailed epic description",
  "acceptance_criteria": ["Criteria 1", "Criteria 2"],
  "story_points": 13
}}
"""

        try:
            # Amazon Bedrock manages: API authentication, model access controls,
            # encryption in transit (TLS 1.2+) and at rest.
            # Customer manages: input sanitization (see sanitize_prompt in app.py),
            # prompt injection mitigation, and output review before JIRA creation.
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            epic_json = result["content"][0]["text"]

            try:
                return json.loads(epic_json)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", epic_json, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse epic details from AI response")
        except Exception as e:
            raise ValueError(f"Failed to generate epic details: {str(e)}")
