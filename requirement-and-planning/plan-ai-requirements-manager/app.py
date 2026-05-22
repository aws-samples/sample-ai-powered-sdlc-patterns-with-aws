import streamlit as st
import json
import logging
import uuid
import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from botocore.config import Config
from src.agents.feature_agent import FeatureAgent
from src.agents.epic_agent import EpicAgent
from src.agents.story_agent import StoryAgent
from src.tracking.progress_tracker import ProgressTracker
from src.utils.file_handler import FileHandler
from src.utils.mcp_client import create_jira_issue, call_mcp_tool
# Security utilities — see src/utils/security.py and docs/SECURITY.md for details.
# sanitize_prompt: filters known prompt injection patterns, enforces length limit
# sanitize_jira_input: sanitizes text for JIRA fields, enforces JIRA API length limits
# validate_jira_key: validates JIRA issue key format (e.g., PROJ-123)
# rate_limit: limits requests per session to mitigate automated abuse
# validate_file_upload: enforces file size and binary-content checks
# sanitize_error_message: strips internal details from user-facing errors
# log_security_event: logs security events for audit trail
from src.utils.security import (
    sanitize_prompt,
    sanitize_jira_input,
    validate_jira_key,
    rate_limit,
    validate_file_upload,
    sanitize_error_message,
    log_security_event,
    RateLimitExceeded,
    InputValidationError,
)

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configure boto3 with retry settings.
# max_attempts=10 with adaptive mode handles transient Bedrock throttling
# without manual backoff. read_timeout=300 accommodates large model responses.
# Review these values if you observe retry storms in CloudWatch metrics.
BOTO_CONFIG = Config(
    retries={"max_attempts": 10, "mode": "adaptive"},
    read_timeout=300,
    connect_timeout=60,
)

st.set_page_config(
    page_title="Product Requirement Assistant", page_icon="🎯", layout="wide"
)


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agents_initialized" not in st.session_state:
        st.session_state.agents_initialized = False
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if "pending_epic_creation" not in st.session_state:
        st.session_state.pending_epic_creation = False
    if "generated_features" not in st.session_state:
        st.session_state.generated_features = None

    # New multi-file upload state
    if "business_needs_content" not in st.session_state:
        st.session_state.business_needs_content = None
    if "user_feedback_content" not in st.session_state:
        st.session_state.user_feedback_content = None
    if "market_trends_content" not in st.session_state:
        st.session_state.market_trends_content = None
    if "files_confirmed" not in st.session_state:
        st.session_state.files_confirmed = False
    if "pending_confirmation" not in st.session_state:
        st.session_state.pending_confirmation = False

    # Security: Rate limiting counter
    if "request_count" not in st.session_state:
        st.session_state.request_count = 0


def initialize_agents():
    if not st.session_state.agents_initialized:
        # Validate JIRA configuration on startup
        jira_url = os.getenv("JIRA_URL", "").strip()
        jira_project_key = os.getenv("JIRA_PROJECT_KEY", "").strip()

        if not jira_url:
            st.error("⚠️ JIRA_URL not configured. Please set it in your .env file.")
            st.stop()

        if not jira_project_key:
            st.error("⚠️ JIRA_PROJECT_KEY not configured. Please set it in your .env file.")
            st.stop()

        # Validate JIRA URL format — enforce HTTPS
        if not jira_url.startswith('https://'):
            st.error("⚠️ JIRA_URL must use HTTPS (e.g., https://your-domain.atlassian.net)")
            st.stop()

        # Create single Bedrock client to be shared
        # Amazon Bedrock: AWS manages model security, data encryption at rest/in transit.
        # Customer responsibility: secure API credentials, input sanitization,
        # rate limiting, and audit logging. See docs/SECURITY.md for details.
        import boto3

        st.session_state.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            config=BOTO_CONFIG,
        )

        # Pass shared client to agents
        st.session_state.feature_agent = FeatureAgent(st.session_state.bedrock_client)
        st.session_state.epic_agent = EpicAgent(st.session_state.bedrock_client)
        st.session_state.story_agent = StoryAgent(st.session_state.bedrock_client)
        st.session_state.progress_tracker = ProgressTracker()
        st.session_state.file_handler = FileHandler()
        st.session_state.agents_initialized = True


def main():
    st.title("🎯 Product Requirement Assistant")
    st.markdown(
        "Accelerate product development with AI-generated requirements"
    )

    initialize_session_state()
    initialize_agents()

    # Sidebar with configuration info
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("Amazon Bedrock")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        st.info(f"**Region:** {aws_region}")
        st.info("**Model:** Claude Sonnet 4")
        st.caption("Model ID: us.anthropic.claude-sonnet-4-6")

        st.divider()

        st.subheader("JIRA Integration")
        jira_url = os.getenv("JIRA_URL", "").rstrip("/")
        st.info(f"**URL:** {jira_url}")

    # File upload section with three uploaders
    st.markdown("### 📤 Upload Input Files")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Business Needs** (Required)")
        business_needs_file = st.file_uploader(
            "Upload Business Needs",
            type=["md", "txt"],
            key="business_needs",
            help="Upload business requirements document (.md or .txt)",
            label_visibility="collapsed",
        )
        if business_needs_file and st.session_state.business_needs_content is None:
            try:
                # Security: Validate file upload.
                # MAX_FILE_SIZE_MB (default 10) prevents resource exhaustion from
                # oversized uploads. Only .md/.txt allowed to reject executable content.
                # You are responsible for ensuring uploaded files do not contain
                # sensitive data unless properly authorized for AI processing.
                file_content = business_needs_file.read()
                max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
                validate_file_upload(file_content, ['.md', '.txt'], max_size_mb)

                st.session_state.business_needs_content = file_content.decode("utf-8")
                st.success("✅ Uploaded")
            except InputValidationError as e:
                st.error(f"❌ File validation failed: {str(e)}")
                log_security_event("file_upload_validation_failed", {
                    "file_type": "business_needs",
                    "error": str(e)
                })
        elif st.session_state.business_needs_content:
            st.success("✅ Uploaded")

    with col2:
        st.markdown("**User Feedback** (Required)")
        user_feedback_file = st.file_uploader(
            "Upload User Feedback",
            type=["md", "txt"],
            key="user_feedback",
            help="Upload user feedback document (.md or .txt)",
            label_visibility="collapsed",
        )
        if user_feedback_file and st.session_state.user_feedback_content is None:
            try:
                # Security: Validate file upload.
                # MAX_FILE_SIZE_MB (default 10) prevents resource exhaustion.
                # Only .md/.txt allowed to reject executable content.
                file_content = user_feedback_file.read()
                max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
                validate_file_upload(file_content, ['.md', '.txt'], max_size_mb)

                st.session_state.user_feedback_content = file_content.decode("utf-8")
                st.success("✅ Uploaded")
            except InputValidationError as e:
                st.error(f"❌ File validation failed: {str(e)}")
                log_security_event("file_upload_validation_failed", {
                    "file_type": "user_feedback",
                    "error": str(e)
                })
        elif st.session_state.user_feedback_content:
            st.success("✅ Uploaded")

    with col3:
        st.markdown("**Market Trends** (Optional)")
        market_trends_file = st.file_uploader(
            "Upload Market Trends",
            type=["json"],
            key="market_trends",
            help="Upload market analysis data (.json)",
            label_visibility="collapsed",
        )
        if market_trends_file and st.session_state.market_trends_content is None:
            try:
                # Security: Validate file upload.
                # MAX_FILE_SIZE_MB (default 10) prevents resource exhaustion.
                # Only .json allowed; parsed to reject malformed content.
                file_content = market_trends_file.read()
                max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
                validate_file_upload(file_content, ['.json'], max_size_mb)

                st.session_state.market_trends_content = json.loads(file_content.decode("utf-8"))
                st.success("✅ Uploaded")
            except (InputValidationError, json.JSONDecodeError) as e:
                st.error(f"❌ File validation failed: {sanitize_error_message(e, include_details=True)}")
                log_security_event("file_upload_validation_failed", {
                    "file_type": "market_trends",
                    "error": str(e)
                })
        elif st.session_state.market_trends_content:
            st.success("✅ Uploaded")

    # Show confirmation button when required files are uploaded
    required_files_uploaded = (
        st.session_state.business_needs_content is not None and
        st.session_state.user_feedback_content is not None
    )

    if required_files_uploaded and not st.session_state.files_confirmed:
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            if st.button("📋 Review & Confirm Files", use_container_width=True, type="primary"):
                show_file_summary()

    # Chat interface - display messages below upload section
    st.markdown("---")
    st.markdown("### 💬 Conversation")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(
        "Ask me to process requirements, create epics, or track progress..."
    ):
        # Security: Apply rate limiting.
        # Limits requests per session to mitigate automated abuse.
        # Default: 10 requests/60s. Configure via RATE_LIMIT_MAX_REQUESTS and
        # RATE_LIMIT_WINDOW_SECONDS in .env. Production: adjust based on expected
        # legitimate traffic. When exceeded, the request is rejected with an error.
        try:
            max_requests = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10"))
            window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
            rate_limit(st.session_state.session_id, max_requests, window_seconds)
        except RateLimitExceeded as e:
            st.error(f"⚠️ Rate limit exceeded. This security control helps protect against abuse. "
                     f"You can configure limits in your .env file (RATE_LIMIT_MAX_REQUESTS, "
                     f"RATE_LIMIT_WINDOW_SECONDS). Please wait and try again.")
            log_security_event("rate_limit_exceeded", {
                "session_id": st.session_state.session_id
            })
            return

        # Security: Sanitize user input.
        # MAX_PROMPT_LENGTH (default 10000) limits token-exhaustion attacks.
        # sanitize_prompt() filters known injection patterns (instruction override,
        # XSS payloads). See src/utils/security.py for the full pattern list.
        try:
            max_prompt_length = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
            sanitized_prompt = sanitize_prompt(prompt, max_prompt_length)
        except InputValidationError as e:
            st.error(f"⚠️ Invalid input: {str(e)}")
            log_security_event("input_validation_failed", {
                "session_id": st.session_state.session_id,
                "error": str(e)
            })
            return

        st.session_state.messages.append({"role": "user", "content": sanitized_prompt})
        with st.chat_message("user"):
            st.markdown(sanitized_prompt)

        with st.chat_message("assistant"):
            try:
                response = process_chat_input(sanitized_prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = sanitize_error_message(e, include_details=False)
                st.error(f"❌ {error_msg}")
                log_security_event("chat_processing_error", {
                    "session_id": st.session_state.session_id,
                    "error": str(e)
                })

    # Show Generate Features button after confirmation - below chat
    if st.session_state.files_confirmed and not st.session_state.pending_epic_creation:
        st.markdown("---")
        col_gen1, col_gen2, col_gen3 = st.columns([1, 1, 1])
        with col_gen2:
            if st.button("🚀 Generate Feature Specifications", use_container_width=True, type="primary"):
                with st.spinner("Analyzing requirements and generating features..."):
                    response = process_requirements_from_uploads()
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()

    # Show JIRA creation buttons after features are generated
    if st.session_state.pending_epic_creation:
        st.markdown("---")
        st.markdown("### 🎫 Create JIRA Tickets")
        st.info("Review the generated features above. Ready to create epics and stories in JIRA?")

        col_jira1, col_jira2, col_jira3 = st.columns([1, 1, 1])

        with col_jira1:
            if st.button("✅ Create JIRA Tickets", use_container_width=True, type="primary"):
                st.session_state.pending_epic_creation = False
                with st.spinner("Creating epics and stories in JIRA..."):
                    response = create_epics()
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()

        with col_jira3:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.pending_epic_creation = False
                st.session_state.generated_features = None
                cancel_msg = "JIRA ticket creation cancelled. You can regenerate features or upload new files."
                st.session_state.messages.append({"role": "assistant", "content": cancel_msg})
                st.rerun()


def process_chat_input(prompt):
    prompt_lower = prompt.lower()

    # Check for tracking/status queries first (highest priority)
    if any(keyword in prompt_lower for keyword in ["status", "track", "progress"]):
        return handle_tracking_query(prompt)

    # Check for questions about existence/counting (should NOT trigger creation)
    if any(phrase in prompt_lower for phrase in [
        "are there", "is there", "how many", "list", "show me",
        "do we have", "have we", "any epic", "any stories"
    ]):
        # These are informational queries, not creation requests
        return handle_generic_question(prompt)

    # Check for explicit creation requests (must have clear action verbs)
    if "epic" in prompt_lower and any(word in prompt_lower for word in ["create", "generate", "make", "build"]):
        # Only create epics if user explicitly asks to create them
        return create_epics()
    elif ("story" in prompt_lower or "stories" in prompt_lower) and any(word in prompt_lower for word in ["create", "generate", "make", "build"]):
        # Only create stories if user explicitly asks to create them
        return generate_stories()
    else:
        # Use AI to handle all other questions
        return handle_generic_question(prompt)


def handle_generic_question(prompt: str) -> str:
    """Use AI to answer generic questions about the system"""
    try:
        bedrock = st.session_state.bedrock_client

        # Get current state context
        files_uploaded = (
            st.session_state.business_needs_content is not None and
            st.session_state.user_feedback_content is not None
        )
        files_confirmed = st.session_state.files_confirmed
        features_generated = st.session_state.generated_features is not None
        pending_epic_creation = st.session_state.pending_epic_creation

        # Build dynamic context based on current state
        state_context = ""
        if not files_uploaded:
            state_context = "The user has not uploaded files yet."
        elif not files_confirmed:
            state_context = "The user has uploaded files but not confirmed them yet."
        elif not features_generated:
            state_context = "The user has confirmed files but not generated features yet."
        elif pending_epic_creation:
            state_context = "The user has generated features and can now create JIRA tickets."
        else:
            state_context = "The user has completed the workflow and can track progress."

        # Check if epics exist
        try:
            epics = st.session_state.file_handler.load_traceability()
            epics_exist = len(epics) > 0 if epics else False
        except Exception:
            epics_exist = False

        system_context = f"""You are an AI assistant for a Feature & Requirement Management system.

SYSTEM CAPABILITIES:
1. Upload business requirements (Business Needs, User Feedback, Market Trends)
2. Generate feature specifications using AI (Claude Sonnet 4)
3. Create JIRA epics and stories automatically
4. Track real-time progress of features from JIRA

WORKFLOW:
Step 1: Upload 3 files
   - Business Needs (.md or .txt) - Required
   - User Feedback (.md or .txt) - Required
   - Market Trends (.json) - Optional

Step 2: Review & Confirm Files
   - AI generates a summary of uploaded content
   - User confirms to proceed

Step 3: Generate Feature Specifications
   - AI analyzes requirements and creates 3-5 features
   - Each feature includes: title, description, business value, priority, complexity, acceptance criteria

Step 4: Create JIRA Tickets
   - Creates 1 epic per feature in JIRA
   - Creates stories from acceptance criteria
   - Automatically links stories to epics

Step 5: Track Progress
   - Ask about specific features: "What's the status of [feature name]?"
   - Ask for overall progress: "Show overall progress"
   - Real-time data fetched from JIRA

CURRENT STATE: {state_context}
EPICS CREATED: {"Yes - epics have been created in JIRA" if epics_exist else "No - no epics have been created yet"}

JIRA INTEGRATION:
- Connected to: {os.getenv("JIRA_URL", "Not configured")}
- Creates Epics and Stories with automatic linking
- Fetches real-time status updates

IMPORTANT INSTRUCTIONS:
- If user asks about counting/listing epics or stories (e.g., "how many epics", "are there any epics", "list epics"),
  tell them to use: "show overall progress" or "track status" to see all epics and stories with real-time data from JIRA.
- If no epics exist yet, guide them through the workflow to create them.
- Do not suggest creating epics unless the user explicitly asks to create them.

Answer the user's question helpfully, concisely, and in context of their current state.
If they ask how to do something, guide them based on where they are in the workflow.
If they ask about capabilities, explain what the system can do.
Keep responses friendly and conversational."""

        ai_prompt = f"""User question: {prompt}

Provide a helpful, concise answer (2-4 sentences max unless more detail is needed)."""

        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 600,
                "messages": [
                    {"role": "user", "content": system_context},
                    {"role": "user", "content": ai_prompt}
                ]
            })
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    except Exception as e:
        # Fallback to help menu if AI fails
        return f"""I can help you with:
- **Upload Files**: Upload Business Needs, User Feedback, and Market Trends
- **Generate Features**: Analyze requirements and create feature specifications (after uploading files)
- **Create Epics**: Transform features into structured epics in JIRA
- **Generate Stories**: Create user stories with acceptance criteria
- **Track Progress**: Ask about specific features or get overall progress (e.g., "What's the status of feature_001?" or "Show overall progress")

What would you like to do?

(Note: I encountered an error processing your question: {str(e)})"""


def show_file_summary():
    """Show combined summary of all uploaded files and ask for confirmation"""
    try:
        bedrock = st.session_state.bedrock_client

        # Combine all content
        combined_content = ""

        if st.session_state.business_needs_content:
            combined_content += "=== BUSINESS NEEDS ===\n\n"
            combined_content += st.session_state.business_needs_content[:2000]
            combined_content += "\n\n"

        if st.session_state.user_feedback_content:
            combined_content += "=== USER FEEDBACK ===\n\n"
            combined_content += st.session_state.user_feedback_content[:2000]
            combined_content += "\n\n"

        if st.session_state.market_trends_content:
            combined_content += "=== MARKET TRENDS ===\n\n"
            combined_content += json.dumps(st.session_state.market_trends_content, indent=2)[:2000]

        # Generate AI summary
        prompt = f"""Summarize the following uploaded documents in 4-6 concise bullet points. Focus on:
- Main business objectives
- Key user needs and feedback
- Market opportunities (if provided)
- Critical requirements

Documents:
{combined_content[:4000]}

Provide a brief, actionable summary."""

        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        result = json.loads(response["body"].read())
        ai_summary = result["content"][0]["text"]

        # Build summary message
        summary_msg = "## 📋 Uploaded Files Summary\n\n"
        summary_msg += "### Files Received:\n"
        summary_msg += "✅ **Business Needs** - Markdown document\n"
        summary_msg += "✅ **User Feedback** - Markdown document\n"
        if st.session_state.market_trends_content:
            summary_msg += "✅ **Market Trends** - JSON data\n"
        else:
            summary_msg += "⚪ **Market Trends** - Not provided (optional)\n"

        summary_msg += f"\n### Content Summary:\n\n{ai_summary}\n\n"
        summary_msg += "---\n\n"
        summary_msg += "**Ready to proceed?** Click the 'Generate Feature Specifications' button to continue."

        st.session_state.messages.append({"role": "assistant", "content": summary_msg})
        st.session_state.files_confirmed = True
        st.rerun()

    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")


def process_requirements_from_uploads():
    """Process requirements from uploaded files (no file system access)"""
    try:
        # Combine business needs and user feedback into business_requirements
        business_requirements = ""

        if st.session_state.business_needs_content:
            business_requirements += "# Business Needs\n\n"
            business_requirements += st.session_state.business_needs_content
            business_requirements += "\n\n"

        if st.session_state.user_feedback_content:
            business_requirements += "# User Feedback\n\n"
            business_requirements += st.session_state.user_feedback_content

        # Prepare requirements dict for feature agent
        requirements_dict = {
            "business_requirements": business_requirements,
            "market_analysis": st.session_state.market_trends_content or {}
        }

        # Generate features using the agent
        features = st.session_state.feature_agent.generate_features(requirements_dict)
        st.session_state.file_handler.save_features(features)

        # Generate detailed response
        response = f"✅ **Generated {len(features)} Features**\n\n"

        for i, feature in enumerate(features, 1):
            response += f"### Feature {i}: {feature.title}\n\n"
            response += f"**Description:** {feature.description}\n\n"
            response += f"**Business Value:** {feature.business_value}\n\n"
            response += f"**Priority:** {feature.priority} | **Complexity:** {feature.complexity}\n\n"
            response += "**Acceptance Criteria:**\n"
            for criterion in feature.acceptance_criteria:
                response += f"- {criterion}\n"
            response += "\n"
            if feature.dependencies:
                response += (
                    f"**Dependencies:** {', '.join(feature.dependencies)}\n\n"
                )
            response += "---\n\n"

        # Save to markdown file
        session_id = st.session_state.session_id
        output_file = Path("outputs") / f"{session_id}-features.md"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Generated Features\n\n")
            f.write(f"**Session ID:** {session_id}\n\n")
            f.write(f"**Total Features:** {len(features)}\n\n")
            f.write("---\n\n")
            f.write(response)

        response += f"\n📄 **Saved to:** `{output_file}`"

        # Store features and prompt for epic creation
        st.session_state.generated_features = features
        st.session_state.pending_epic_creation = True

        response += "\n\n**Features generated successfully!** Use the buttons below to create JIRA tickets or continue with other actions."

        return response
    except Exception as e:
        return f"❌ Error processing requirements: {str(e)}"


def create_story_from_criterion(
    project_key: str,
    epic_key: str,
    criterion: str,
    feature_title: str,
    story_number: int,
) -> Dict[str, Any]:
    """Create a story from an acceptance criterion with implementation details and DoD"""
    # Use AI to generate story details
    bedrock = st.session_state.bedrock_client

    prompt = f"""Create a user story from this acceptance criterion for feature "{feature_title}":

Criterion: {criterion}

Generate:
1. Story title - Short, descriptive phrase (max 50 characters). NO "As a user" or "I want". Just the feature name. Example: "Personalized Product Recommendations"
2. Implementation details (what needs to be built)
3. Definition of Done (specific, testable outcomes)
4. Story points estimate (1, 2, or 3 for most stories; only use 5 for exceptional cases)

IMPORTANT:
- Title must be succinct and fit on scrum boards (max 50 chars)
- Maximum story points is 5. Most stories should be 1-3 points.

Return JSON:
{{
  "title": "Feature Name",
  "implementation": "Technical implementation details",
  "definition_of_done": ["DoD item 1", "DoD item 2"],
  "story_points": 2
}}"""

    try:
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        result = json.loads(response["body"].read())
        ai_text = result["content"][0]["text"]

        # Try to extract JSON from the response
        import re

        json_match = re.search(r"\{.*\}", ai_text, re.DOTALL)
        if json_match:
            story_details = json.loads(json_match.group())
        else:
            raise ValueError(f"No JSON found in AI response: {ai_text[:200]}")

        # Create story in Jira (without acceptance criterion, only implementation and DoD)
        # Security: Sanitize JIRA inputs.
        # MAX_JIRA_FIELD_LENGTH (default 32000) aligns with JIRA API field limits (~32,767 chars).
        # Summary capped at 255 chars per JIRA API constraint.
        max_jira_length = int(os.getenv("MAX_JIRA_FIELD_LENGTH", "32000"))
        story_summary = sanitize_jira_input(story_details["title"], max_length=255)

        description = f"""**Implementation Details:**
{story_details['implementation']}

**Definition of Done:**
"""
        for dod in story_details["definition_of_done"]:
            description += f"- {dod}\n"

        description = sanitize_jira_input(description, max_jira_length)

        story_result = create_jira_issue(
            project_key=project_key,
            summary=story_summary,
            description=description,
            issue_type="Story",
            parent_epic=epic_key,
            story_points=story_details["story_points"],
        )

        story_result["story_points"] = story_details["story_points"]
        return story_result

    except Exception as e:
        logger.error(f"Error creating story: {str(e)}")
        # Fallback: create basic story
        # Security: Sanitize JIRA inputs
        max_jira_length = int(os.getenv("MAX_JIRA_FIELD_LENGTH", "32000"))
        story_summary = sanitize_jira_input(f"Story {story_number}: {criterion[:60]}", max_length=255)
        story_description = sanitize_jira_input("Implementation needed for this story.", max_jira_length)

        story_result = create_jira_issue(
            project_key=project_key,
            summary=story_summary,
            description=story_description,
            issue_type="Story",
            parent_epic=epic_key,
            story_points=3,
        )
        story_result["story_points"] = 3
        return story_result


def create_epics():
    try:
        with st.spinner("Creating epics and stories in JIRA..."):
            features = st.session_state.file_handler.load_features()
            if not features:
                return "❌ No features found. Please upload files and generate features first."

            created_epics = []
            all_stories = []
            response = "✅ **Created Epics and Stories in JIRA**\n\n"

            # Get project key from environment
            project_key = os.getenv("JIRA_PROJECT_KEY", "PROJ")

            # Create 1 epic per feature
            for feature in features:
                try:
                    # Handle both dict and object formats
                    feature_id = (
                        feature.get("id") if isinstance(feature, dict) else feature.id
                    )
                    feature_title = (
                        feature.get("title")
                        if isinstance(feature, dict)
                        else feature.title
                    )
                    feature_desc = (
                        feature.get("description")
                        if isinstance(feature, dict)
                        else feature.description
                    )
                    feature_value = (
                        feature.get("business_value")
                        if isinstance(feature, dict)
                        else feature.business_value
                    )
                    feature_priority = (
                        feature.get("priority")
                        if isinstance(feature, dict)
                        else feature.priority
                    )
                    feature_complexity = (
                        feature.get("complexity")
                        if isinstance(feature, dict)
                        else feature.complexity
                    )
                    feature_criteria = (
                        feature.get("acceptance_criteria")
                        if isinstance(feature, dict)
                        else feature.acceptance_criteria
                    )

                    # Create epic in Jira with all acceptance criteria
                    # Security: Sanitize JIRA inputs
                    max_jira_length = int(os.getenv("MAX_JIRA_FIELD_LENGTH", "32000"))
                    epic_summary = sanitize_jira_input(f"[EPIC] {feature_title}", max_length=255)
                    epic_description = f"{feature_desc}\n\n**Business Value:** {feature_value}\n\n**Acceptance Criteria:**\n"
                    for idx, criterion in enumerate(feature_criteria, 1):
                        epic_description += f"{idx}. {criterion}\n"
                    epic_description = sanitize_jira_input(epic_description, max_jira_length)

                    epic_result = create_jira_issue(
                        project_key=project_key,
                        summary=epic_summary,
                        description=epic_description,
                        issue_type="Epic",
                    )

                    # Extract epic key from response
                    if 'key' in epic_result:
                        epic_key = epic_result['key']
                    elif 'text' in epic_result:
                        # Extract key from text response
                        import re
                        match = re.search(r'Key:\s*([A-Z]+-\d+)', epic_result['text'])
                        epic_key = match.group(1) if match else "N/A"
                    else:
                        epic_key = "N/A"

                    epic_data = {
                        "feature_id": feature_id,
                        "jira_key": epic_key,
                        "title": feature_title,
                        "description": feature_desc,
                        "stories": [],
                    }

                    response += f"## Epic: {epic_key} - {feature_title}\n\n"
                    response += f"**Priority:** {feature_priority} | **Complexity:** {feature_complexity}\n\n"
                    response += "### Stories:\n\n"

                    # Create stories from acceptance criteria
                    for idx, criterion in enumerate(feature_criteria, 1):
                        story_result = create_story_from_criterion(
                            project_key=project_key,
                            epic_key=epic_key,
                            criterion=criterion,
                            feature_title=feature_title,
                            story_number=idx,
                        )

                        if story_result:
                            story_data = {
                                "epic_key": epic_key,
                                "jira_key": story_result.get("key", "N/A"),
                                "criterion": criterion,
                                "story_points": story_result.get("story_points", 3),
                            }
                            epic_data["stories"].append(story_data)
                            all_stories.append(story_data)

                            response += f"- **{story_result.get('key')}**: {criterion[:80]}... ({story_result.get('story_points', 3)} points)\n"

                    response += "\n---\n\n"
                    created_epics.append(epic_data)

                except Exception as e:
                    response += f"⚠️ Failed to create epic for feature {feature_id if 'feature_id' in locals() else 'unknown'}: {str(e)}\n\n"

            # Save traceability - pass the list of epics directly
            st.session_state.file_handler.save_traceability(created_epics)

            # Save to markdown
            session_id = st.session_state.session_id
            output_file = Path("outputs") / f"{session_id}-epics-and-stories.md"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# Created Epics and Stories\n\n")
                f.write(f"**Session ID:** {session_id}\n\n")
                f.write(f"**Total Epics:** {len(created_epics)}\n\n")
                f.write(f"**Total Stories:** {len(all_stories)}\n\n")
                f.write("---\n\n")
                f.write(response)

            response += f"\n📄 **Saved to:** `{output_file}`"

            return response
    except Exception as e:
        return f"❌ Error creating epics: {str(e)}"


def generate_stories():
    try:
        with st.spinner("Generating user stories..."):
            epics = st.session_state.file_handler.load_traceability()
            if not epics:
                return "❌ No epics found. Create epics first."

            stories = st.session_state.story_agent.generate_stories(epics)
            st.session_state.file_handler.update_traceability(stories)

            return f"✅ Generated {len(stories)} user stories with acceptance criteria."
    except Exception as e:
        return f"❌ Error generating stories: {str(e)}"


def handle_tracking_query(prompt: str) -> str:
    """Handle tracking queries - both specific features and overall progress"""
    try:
        # Load traceability data - returns list of epics
        epics = st.session_state.file_handler.load_traceability()
        if not epics:
            return "❌ No epics found. Please create JIRA tickets first."

        # Check if user is asking for overall progress
        if "overall" in prompt.lower() or "all" in prompt.lower() or prompt.lower().strip() in ["progress", "track", "status"]:
            return track_overall_progress(epics)

        # Otherwise, try to find specific feature/epic
        return track_specific_feature(prompt, epics)

    except Exception as e:
        logger.error(f"Error tracking progress: {str(e)}", exc_info=True)
        return f"❌ Error tracking progress: {sanitize_error_message(e, include_details=False)}"


def track_specific_feature(prompt: str, epics: List[Dict[str, Any]]) -> str:
    """Track status of a specific feature, epic, or story"""
    try:
        # Check if user provided a direct JIRA key (e.g., DP-123, EP-300)
        import re
        jira_key_match = re.search(r'\b([A-Z]+-\d+)\b', prompt)

        if jira_key_match:
            jira_key = jira_key_match.group(1)

            # First, check if this epic exists in our traceability data
            target_epic = None
            for epic in epics:
                if not isinstance(epic, dict):
                    continue
                if epic.get('jira_key') == jira_key:
                    target_epic = epic
                    break

            if target_epic:
                # Epic found in our data, fetch full status
                return fetch_epic_status(target_epic)
            else:
                # Epic not in our data, try to fetch directly from JIRA
                return fetch_jira_issue_directly(jira_key)

        # No direct JIRA key found, use AI to match user query to feature/epic/story
        bedrock = st.session_state.bedrock_client

        # Build context of available features, epics, and stories
        features_context = "EPICS:\n"
        stories_context = "\nSTORIES:\n"

        for epic in epics:
            if not isinstance(epic, dict):
                continue
            features_context += f"- Epic: {epic.get('title')} (Key: {epic.get('jira_key')})\n"

            # Add stories from this epic
            stories = epic.get('stories', [])
            for story in stories:
                if isinstance(story, dict):
                    story_key = story.get('jira_key')
                    # Try to get story title from criterion (will be replaced with actual title from JIRA)
                    story_title = story.get('criterion', 'Unknown')
                    stories_context += f"  - Story: {story_title[:80]} (Key: {story_key}, Epic: {epic.get('jira_key')})\n"

        match_prompt = f"""User is asking: "{prompt}"

Available features, epics, and stories:
{features_context}
{stories_context}

Which item is the user asking about?
- If asking about an epic, return the epic key (e.g., DP-123)
- If asking about a story, return the story key (e.g., DP-124)
- Return ONLY the JIRA key (e.g., DP-123)
- If you cannot determine a match, return "NONE"."""

        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": match_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        match_result = result["content"][0]["text"].strip()

        if match_result == "NONE":
            return f"❌ Could not find a matching feature, epic, or story in tracked items. Available epics:\n\n" + "\n".join([f"- {e.get('title')} ({e.get('jira_key')})" for e in epics if isinstance(e, dict)])

        # Check if it's a story key
        for epic in epics:
            if not isinstance(epic, dict):
                continue
            stories = epic.get('stories', [])
            for story in stories:
                if isinstance(story, dict) and story.get('jira_key') == match_result:
                    # Found a story - fetch its details with epic context
                    return fetch_story_status(story, epic)

        # Otherwise, find the epic
        target_epic = None
        for epic in epics:
            if not isinstance(epic, dict):
                continue
            if match_result in [epic.get('jira_key'), epic.get('feature_id')]:
                target_epic = epic
                break

        if not target_epic:
            # Maybe it's a story or other issue not in our epic list
            return fetch_jira_issue_directly(match_result)

        # Fetch real-time status from JIRA
        return fetch_epic_status(target_epic)

    except Exception as e:
        logger.error(f"Error tracking feature: {str(e)}", exc_info=True)
        return f"❌ Error tracking feature: {sanitize_error_message(e, include_details=False)}"


def fetch_story_status(story: Dict[str, Any], epic: Dict[str, Any]) -> str:
    """Fetch real-time status of a story created by this app"""
    try:
        story_key = story.get('jira_key')
        epic_key = epic.get('jira_key')
        epic_title = epic.get('title', 'Unknown')
        jira_url = os.getenv("JIRA_URL", "").rstrip("/")

        # Get story details from JIRA
        story_result = call_mcp_tool("jira_get_issue", {"issue_key": story_key})

        if not story_result or (isinstance(story_result, dict) and 'error' in story_result):
            return f"❌ Could not find JIRA story {story_key}. Please verify the issue key exists in JIRA."

        # Parse story details
        story_status = "Unknown"
        story_summary = story.get('criterion', 'Unknown')
        story_description = ""
        story_points = story.get('story_points', 0)

        if isinstance(story_result, dict):
            if 'fields' in story_result:
                fields = story_result['fields']
                status_obj = fields.get('status', {})
                story_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                story_summary = fields.get('summary', story_summary)
                story_description = fields.get('description', '')
            elif 'text' in story_result:
                # Parse JSON from text field
                import re
                text = story_result['text']

                # Extract JSON from text (format: "JIRA Issue Details:\n{...json...}")
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    try:
                        issue_data = json.loads(json_match.group(0))
                        if 'fields' in issue_data:
                            fields = issue_data['fields']
                            status_obj = fields.get('status', {})
                            story_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                            story_summary = fields.get('summary', story_summary)
                            story_description = fields.get('description', '')
                    except json.JSONDecodeError:
                        # Fallback to regex extraction
                        status_match = re.search(r'Status:\s*([^\n]+)', text)
                        if status_match:
                            story_status = status_match.group(1).strip()

                        summary_match = re.search(r'Summary:\s*([^\n]+)', text)
                        if summary_match:
                            story_summary = summary_match.group(1).strip()

        # Build response
        status_emoji = "✅" if story_status.lower() in ['done', 'closed', 'resolved'] else "🔄" if story_status.lower() in ['in progress', 'in review'] else "⚪"

        response = f"## {status_emoji} Story: {story_key}\n\n"
        response += f"**Link:** [{story_key}]({jira_url}/browse/{story_key})\n\n"
        response += f"**Title:** {story_summary}\n\n"
        response += f"**Status:** {story_status}\n\n"
        response += f"**Story Points:** {story_points}\n\n"
        response += f"**Parent Epic:** [{epic_key}]({jira_url}/browse/{epic_key}) - {epic_title}\n\n"

        if story_description:
            response += f"**Description:**\n\n{story_description}\n\n"

        response += "\n---\n\n"
        response += f"💡 **Tip:** To see all stories for this epic, ask: 'What is the status of {epic_title}?'"

        return response

    except Exception as e:
        logger.error(f"Error fetching story {story.get('jira_key')}: {str(e)}", exc_info=True)
        return f"❌ Error fetching story {story.get('jira_key')}: {sanitize_error_message(e, include_details=False)}"


def fetch_jira_issue_directly(issue_key: str) -> str:
    """Fetch status of any JIRA issue directly (not just tracked epics)"""
    try:
        jira_url = os.getenv("JIRA_URL", "").rstrip("/")

        # Get issue details from JIRA
        issue_result = call_mcp_tool("jira_get_issue", {"issue_key": issue_key})

        if not issue_result or (isinstance(issue_result, dict) and 'error' in issue_result):
            return f"❌ Could not find JIRA issue {issue_key}. Please verify the issue key exists in JIRA."

        # Parse issue details
        issue_type = "Unknown"
        issue_status = "Unknown"
        issue_summary = "Unknown"
        issue_description = ""

        if isinstance(issue_result, dict):
            if 'fields' in issue_result:
                fields = issue_result['fields']
                issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
                issue_status = fields.get('status', {}).get('name', 'Unknown')
                issue_summary = fields.get('summary', 'Unknown')
                issue_description = fields.get('description', '')
            elif 'text' in issue_result:
                # Parse JSON from text field
                import re
                text = issue_result['text']

                # Extract JSON from text (format: "JIRA Issue Details:\n{...json...}")
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    try:
                        issue_data = json.loads(json_match.group(0))
                        if 'fields' in issue_data:
                            fields = issue_data['fields']
                            issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
                            issue_status = fields.get('status', {}).get('name', 'Unknown')
                            issue_summary = fields.get('summary', 'Unknown')
                            issue_description = fields.get('description', '')
                    except json.JSONDecodeError:
                        # Fallback to regex extraction
                        type_match = re.search(r'Type:\s*([^\n]+)', text)
                        if type_match:
                            issue_type = type_match.group(1).strip()

                        status_match = re.search(r'Status:\s*([^\n]+)', text)
                        if status_match:
                            issue_status = status_match.group(1).strip()

                        summary_match = re.search(r'Summary:\s*([^\n]+)', text)
                        if summary_match:
                            issue_summary = summary_match.group(1).strip()

        # Build response
        response = f"## 📊 JIRA Issue: {issue_key}\n\n"
        response += f"**Link:** [{issue_key}]({jira_url}/browse/{issue_key})\n\n"
        response += f"**Type:** {issue_type}\n\n"
        response += f"**Status:** {issue_status}\n\n"
        response += f"**Summary:** {issue_summary}\n\n"

        if issue_description:
            response += f"**Description:** {issue_description[:200]}{'...' if len(issue_description) > 200 else ''}\n\n"

        response += "\n---\n\n"
        response += "**Note:** This issue was not created by this application, so detailed story tracking is not available. To track features created by this app, use 'show overall progress'."

        return response

    except Exception as e:
        logger.error(f"Error fetching JIRA issue {issue_key}: {str(e)}", exc_info=True)
        return f"❌ Error fetching JIRA issue {issue_key}: {sanitize_error_message(e, include_details=False)}"


def fetch_epic_status(epic: Dict[str, Any]) -> str:
    """Fetch real-time status of an epic and its stories from JIRA"""
    try:
        epic_key = epic.get('jira_key')
        jira_url = os.getenv("JIRA_URL", "").rstrip("/")

        # Get epic details
        try:
            epic_result = call_mcp_tool("jira_get_issue", {"issue_key": epic_key})

            # Debug: Log the raw response
            import logging
            logging.info(f"Epic {epic_key} raw response: {epic_result}")

        except Exception as e:
            return f"❌ Error fetching epic {epic_key} from JIRA: {str(e)}\n\nPlease verify:\n1. JIRA connection is working\n2. Issue key {epic_key} exists in JIRA\n3. You have permission to view this issue"

        # Parse epic status
        epic_status = "Unknown"
        if isinstance(epic_result, dict):
            if 'fields' in epic_result:
                status_obj = epic_result['fields'].get('status', {})
                epic_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
            elif 'text' in epic_result:
                # Parse JSON from text field
                import re
                text = epic_result['text']

                # Extract JSON from text (format: "JIRA Issue Details:\n{...json...}")
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    try:
                        issue_data = json.loads(json_match.group(0))
                        if 'fields' in issue_data:
                            status_obj = issue_data['fields'].get('status', {})
                            epic_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                    except json.JSONDecodeError:
                        # Fallback to regex extraction
                        status_match = re.search(r'Status:\s*([^\n]+)', text)
                        if status_match:
                            epic_status = status_match.group(1).strip()
            elif 'status' in epic_result:
                # Direct status field
                epic_status = epic_result['status']

        # Build response
        response = f"## 📊 Status Report: {epic.get('title')}\n\n"
        response += f"**Epic:** [{epic_key}]({jira_url}/browse/{epic_key})\n\n"
        response += f"**Status:** {epic_status}\n\n"
        response += f"**Description:** {epic.get('description', 'N/A')}\n\n"

        # Get stories
        stories = epic.get('stories', [])
        if stories:
            response += f"### Stories ({len(stories)} total)\n\n"

            total_points = 0
            completed_points = 0
            completed_stories = 0  # Track completed stories count

            for story in stories:
                story_key = story.get('jira_key')
                story_points = story.get('story_points', 0)
                total_points += story_points

                # Fetch story status and details
                try:
                    story_result = call_mcp_tool("jira_get_issue", {"issue_key": story_key})
                    story_status = "Unknown"
                    story_summary = story.get('criterion', 'N/A')
                    story_description = ""

                    if isinstance(story_result, dict):
                        if 'fields' in story_result:
                            fields = story_result['fields']
                            status_obj = fields.get('status', {})
                            story_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                            story_summary = fields.get('summary', story_summary)
                            story_description = fields.get('description', '')
                        elif 'text' in story_result:
                            import re
                            text = story_result['text']

                            # Extract JSON from text (format: "JIRA Issue Details:\n{...json...}")
                            json_match = re.search(r'\{.*\}', text, re.DOTALL)
                            if json_match:
                                try:
                                    issue_data = json.loads(json_match.group(0))
                                    if 'fields' in issue_data:
                                        fields = issue_data['fields']
                                        status_obj = fields.get('status', {})
                                        story_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                                        story_summary = fields.get('summary', story_summary)
                                        story_description = fields.get('description', '')
                                except json.JSONDecodeError:
                                    # Fallback to regex extraction
                                    status_match = re.search(r'Status:\s*([^\n]+)', text)
                                    if status_match:
                                        story_status = status_match.group(1).strip()
                        elif 'status' in story_result:
                            story_status = story_result['status']

                    # Count completed points and stories
                    if story_status.lower() in ['done', 'closed', 'resolved']:
                        completed_points += story_points
                        completed_stories += 1

                    status_emoji = "✅" if story_status.lower() in ['done', 'closed', 'resolved'] else "🔄" if story_status.lower() in ['in progress', 'in review'] else "⚪"

                    response += f"{status_emoji} **[{story_key}]({jira_url}/browse/{story_key})** - {story_summary}\n"
                    response += f"   - **Status:** {story_status} | **Story Points:** {story_points}\n"

                    # Add description if available (truncated for readability)
                    if story_description:
                        desc_preview = story_description[:150].replace('\n', ' ')
                        response += f"   - **Description:** {desc_preview}{'...' if len(story_description) > 150 else ''}\n"

                    response += "\n"

                except Exception as e:
                    response += f"⚠️ **{story_key}** - Could not fetch status: {str(e)}\n\n"

            # Progress summary
            progress_pct = (completed_points / total_points * 100) if total_points > 0 else 0
            response += f"\n### Progress Summary\n\n"
            response += f"- **Story Points:** {completed_points}/{total_points} completed ({progress_pct:.1f}%)\n"
            response += f"- **Stories:** {completed_stories}/{len(stories)} completed\n"

        return response

    except Exception as e:
        logger.error(f"Error fetching epic status: {str(e)}", exc_info=True)
        return f"❌ Error fetching epic status: {sanitize_error_message(e, include_details=False)}"


def track_overall_progress(epics: List[Dict[str, Any]]) -> str:
    """Track overall progress across all epics"""
    try:
        jira_url = os.getenv("JIRA_URL", "").rstrip("/")

        response = "## 📊 Overall Progress Report\n\n"
        response += f"**Total Epics:** {len(epics)}\n\n"

        total_stories = 0
        total_points = 0
        completed_stories = 0
        completed_points = 0

        for epic in epics:
            # Verify epic is a dict
            if not isinstance(epic, dict):
                continue

            epic_key = epic.get('jira_key')
            if not epic_key:
                continue

            stories = epic.get('stories', [])
            total_stories += len(stories)

            # Fetch epic status
            try:
                epic_result = call_mcp_tool("jira_get_issue", {"issue_key": epic_key})
                epic_status = "Unknown"

                if isinstance(epic_result, dict):
                    if 'fields' in epic_result:
                        epic_status = epic_result['fields'].get('status', {}).get('name', 'Unknown')
                    elif 'text' in epic_result:
                        import re
                        text = epic_result['text']

                        # Extract JSON from text (format: "JIRA Issue Details:\n{...json...}")
                        json_match = re.search(r'\{.*\}', text, re.DOTALL)
                        if json_match:
                            try:
                                issue_data = json.loads(json_match.group(0))
                                if 'fields' in issue_data:
                                    status_obj = issue_data['fields'].get('status', {})
                                    epic_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                            except json.JSONDecodeError:
                                # Fallback to regex extraction
                                status_match = re.search(r'Status:\s*([^\n]+)', text)
                                if status_match:
                                    epic_status = status_match.group(1).strip()

                status_emoji = "✅" if epic_status.lower() in ['done', 'closed'] else "🔄" if epic_status.lower() in ['in progress'] else "⚪"

                response += f"\n### {status_emoji} [{epic_key}]({jira_url}/browse/{epic_key}) - {epic.get('title', 'Unknown')}\n"
                response += f"**Status:** {epic_status} | **Stories:** {len(stories)}\n\n"

                # Check story statuses
                for story in stories:
                    if not isinstance(story, dict):
                        continue

                    story_key = story.get('jira_key')
                    if not story_key:
                        continue

                    story_points = story.get('story_points', 0)
                    total_points += story_points

                    try:
                        story_result = call_mcp_tool("jira_get_issue", {"issue_key": story_key})
                        story_status = "Unknown"

                        if isinstance(story_result, dict):
                            if 'fields' in story_result:
                                story_status = story_result['fields'].get('status', {}).get('name', 'Unknown')
                            elif 'text' in story_result:
                                import re
                                text = story_result['text']

                                # Extract JSON from text (format: "JIRA Issue Details:\n{...json...}")
                                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                                if json_match:
                                    try:
                                        issue_data = json.loads(json_match.group(0))
                                        if 'fields' in issue_data:
                                            status_obj = issue_data['fields'].get('status', {})
                                            story_status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else str(status_obj)
                                    except json.JSONDecodeError:
                                        # Fallback to regex extraction
                                        status_match = re.search(r'Status:\s*([^\n]+)', text)
                                        if status_match:
                                            story_status = status_match.group(1).strip()

                        if story_status.lower() in ['done', 'closed', 'resolved']:
                            completed_stories += 1
                            completed_points += story_points
                    except Exception as story_error:
                        # Skip stories that fail to fetch — non-critical for progress display
                        logger_msg = f"Could not fetch story status: {story_error}"
                        pass

            except Exception as epic_error:
                response += f"⚠️ Could not fetch status for {epic_key}: {str(epic_error)}\n\n"

        # Summary
        story_progress = (completed_stories / total_stories * 100) if total_stories > 0 else 0
        points_progress = (completed_points / total_points * 100) if total_points > 0 else 0

        response += f"\n---\n\n### Summary\n\n"
        response += f"- **Stories Completed:** {completed_stories}/{total_stories} ({story_progress:.1f}%)\n"
        response += f"- **Story Points Completed:** {completed_points}/{total_points} ({points_progress:.1f}%)\n"

        return response

    except Exception as e:
        logger.error(f"Error tracking overall progress: {str(e)}", exc_info=True)
        return f"❌ Error tracking overall progress: {sanitize_error_message(e, include_details=False)}"


def track_progress():
    try:
        with st.spinner("Tracking progress..."):
            progress = st.session_state.progress_tracker.get_progress()
            st.session_state.file_handler.save_progress(progress)

            # Display progress summary
            summary = f"""📊 **Progress Summary**
- Features: {progress.get('total_features', 0)}
- Epics: {progress.get('total_epics', 0)} ({progress.get('completed_epics', 0)} completed)
- Stories: {progress.get('total_stories', 0)} ({progress.get('completed_stories', 0)} completed)
- Overall Progress: {progress.get('overall_percentage', 0):.1f}%"""

            return summary
    except Exception as e:
        return f"❌ Error tracking progress: {str(e)}"



if __name__ == "__main__":
    main()
