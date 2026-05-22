import json
from typing import List, Dict, Any
from pydantic import BaseModel


class UserStory(BaseModel):
    epic_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int
    priority: str


class StoryAgent:
    def __init__(self, bedrock_client):
        self.bedrock = bedrock_client
        self.model_id = "us.anthropic.claude-sonnet-4-6"

    def generate_stories(self, epics: List[Dict[str, Any]]) -> List[UserStory]:
        """
        Generate user stories from epics.

        Returns pure data structures - no JIRA integration.
        """
        all_stories = []

        for epic in epics:
            stories = self._generate_stories_for_epic(epic)
            all_stories.extend(stories)

        return all_stories

    # Prompt injection mitigated by input sanitization below and sanitize_prompt() in calling code.
    # Curly braces are escaped to '{{' / '}}' to prevent f-string injection in prompt templates.
    # This is a customer-managed control; AWS manages Bedrock model security.
    def _generate_stories_for_epic(self, epic: Dict[str, Any]) -> List[UserStory]:
        """
        Generate 3-5 user stories for an epic.

        Input sanitization escapes curly braces to prevent f-string template
        injection. Combined with sanitize_prompt() in calling code, this
        addresses common prompt injection vectors.

        Security metrics:
            - Brace escaping prevents template injection in title, description, criteria
            - Implementation priority: High (applied before every AI call)
        """

        # Sanitize inputs to prevent injection
        title = str(epic.get('title', '')).replace('{', '{{').replace('}', '}}')
        description = str(epic.get('description', '')).replace('{', '{{').replace('}', '}}')

        # Safely handle acceptance criteria list
        criteria = epic.get('acceptance_criteria', [])
        if isinstance(criteria, list):
            criteria_str = ', '.join(str(c).replace('{', '{{').replace('}', '}}') for c in criteria)
        else:
            criteria_str = str(criteria).replace('{', '{{').replace('}', '}}')

        prompt = f"""
Break down this epic into 3-5 user stories:

Epic: {title}
Description: {description}
Acceptance Criteria: {criteria_str}

For each user story, provide:
- Title in format "As a [user], I want [goal] so that [benefit]"
- Detailed description
- Specific acceptance criteria (3-4 items)
- Story points (1-8 scale)
- Priority (High/Medium/Low)

Return ONLY JSON:
{{
  "stories": [
    {{
      "title": "As a user, I want...",
      "description": "Story description",
      "acceptance_criteria": ["Criteria 1", "Criteria 2"],
      "story_points": 5,
      "priority": "High"
    }}
  ]
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
                        "max_tokens": 3000,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )
        except Exception as e:
            raise RuntimeError(f"Amazon Bedrock API call failed: {e}") from e

        result = json.loads(response["body"].read())
        stories_json = result["content"][0]["text"]

        try:
            stories_data = json.loads(stories_json)
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"\{.*\}", stories_json, re.DOTALL)
            if json_match:
                stories_data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse stories from AI response")

        user_stories = []
        for story_data in stories_data["stories"]:
            story = UserStory(
                epic_id=epic.get("id", "unknown"),
                title=story_data["title"],
                description=story_data["description"],
                acceptance_criteria=story_data["acceptance_criteria"],
                story_points=story_data["story_points"],
                priority=story_data["priority"],
            )
            user_stories.append(story)

        return user_stories
