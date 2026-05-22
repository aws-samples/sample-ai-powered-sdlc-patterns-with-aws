import json
from typing import List, Dict, Any
from pydantic import BaseModel


class Feature(BaseModel):
    id: str
    title: str
    description: str
    business_value: str
    priority: str
    complexity: str
    acceptance_criteria: List[str]
    dependencies: List[str]


class FeatureAgent:
    def __init__(self, bedrock_client):
        self.bedrock = bedrock_client
        self.model_id = "us.anthropic.claude-sonnet-4-6"

    def generate_features(self, requirements: Dict[str, Any]) -> List[Feature]:
        """Generate features from business requirements using Claude Sonnet 4"""

        prompt = self._build_feature_prompt(requirements)

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
                        "max_tokens": 4000,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )
        except Exception as e:
            raise RuntimeError(f"Amazon Bedrock API call failed: {e}") from e

        result = json.loads(response["body"].read())
        features_json = result["content"][0]["text"]

        # Parse the JSON response
        try:
            features_data = json.loads(features_json)
            return [Feature(**feature) for feature in features_data["features"]]
        except json.JSONDecodeError:
            # Fallback: extract JSON from text response
            import re

            json_match = re.search(r"\{.*\}", features_json, re.DOTALL)
            if json_match:
                features_data = json.loads(json_match.group())
                return [Feature(**feature) for feature in features_data["features"]]
            else:
                raise ValueError("Could not parse features from AI response")

    # Prompt injection mitigated by sanitize_prompt() in calling code (app.py)
    def _build_feature_prompt(self, requirements: Dict[str, Any]) -> str:
        # Extract business requirements and market data
        business_reqs = str(requirements.get("business_requirements", ""))
        market_data = requirements.get("market_analysis", {})

        # Safely serialize market data
        try:
            market_json = json.dumps(market_data, indent=2)
        except (TypeError, ValueError):
            market_json = "{}"

        return f"""
You are a product manager analyzing business requirements to generate software features.

Business Requirements:
{business_reqs}

Market Analysis:
{market_json}

Generate 3-5 high-level features that address these requirements. For each feature, provide:
- Unique ID (feature_001, feature_002, etc.)
- Clear title and description
- Business value proposition
- Priority (High/Medium/Low)
- Complexity (High/Medium/Low)
- Acceptance criteria (3-5 items)
- Dependencies (if any)

Return ONLY a JSON object in this format:
{{
  "features": [
    {{
      "id": "feature_001",
      "title": "Feature Title",
      "description": "Detailed description",
      "business_value": "Value proposition",
      "priority": "High",
      "complexity": "Medium",
      "acceptance_criteria": ["Criteria 1", "Criteria 2"],
      "dependencies": ["dependency1"]
    }}
  ]
}}
"""
