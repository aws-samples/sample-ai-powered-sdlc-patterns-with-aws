# 🎯 Product Requirement Assistant

Transform business requirements into structured JIRA epics and user stories using Amazon Bedrock AI.

## Demo

See [`demo.mp4`](demo.mp4) for a full walkthrough of the application in action.

## Features

- 📤 **Multi-File Upload**: Upload Business Needs, User Feedback, and Market Trends
- 🤖 **AI-Powered Analysis**: Uses Claude Sonnet 4 to generate feature specifications
- 📋 **Automatic JIRA Integration**: Creates epics and stories with automatic parent-child linking
- 🔗 **Smart Linking**: Stories automatically linked to parent epics (no manual linking required)
- 📊 **Story Points**: AI estimates story points and adds them as comments
- 💾 **Session Management**: Tracks progress and saves outputs
- 🔒 **Security Features**: Input sanitization, rate limiting, file validation, and secure error handling

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram (Mermaid), data flow sequence diagram, component responsibilities, and trust boundaries.

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web UI                         │
│  (Multi-file upload, AI summaries, feature generation)      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────────────────────┐
                            ▼                                 ▼
                ┌───────────────────────┐      ┌──────────────────────┐
                │   Amazon Bedrock      │      │   MCP Client         │
                │   (Claude Sonnet 4)   │      │   (Generic Protocol) │
                └───────────────────────┘      └──────────────────────┘
                            │                                 │
                            │                                 ▼
                            │                  ┌──────────────────────┐
                            │                  │   Proxy MCP Server   │
                            │                  │   (Local)            │
                            │                  └──────────────────────┘
                            │                                 │
                            │                                 ▼
                            │                  ┌──────────────────────┐
                            │                  │  Backend MCP Server  │
                            │                  │  (AWS Lambda)        │
                            │                  └──────────────────────┘
                            │                                 │
                            ▼                                 ▼
                ┌───────────────────────────────────────────────┐
                │              JIRA Cloud                       │
                │  (Epics, Stories, Automatic Linking)          │
                └───────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.9+
- AWS Account with Amazon Bedrock access
- JIRA Cloud account
- MCP Server (for JIRA integration)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd plan-ai-requirements-manager
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   Required variables:
   ```
   AWS_REGION=us-east-1
   JIRA_PROJECT_KEY=YOUR_PROJECT_KEY
   JIRA_URL=https://your-domain.atlassian.net
   MCP_SERVER_SCRIPT=./proxy_jira_mcp.py
   MCP_BACKEND_URL=https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com/dev
   MCP_ACCESS_TOKEN=your-access-token-here
   ```

   Optional security configuration (with defaults):
   ```
   LOG_LEVEL=INFO                      # Logging level (DEBUG, INFO, WARNING, ERROR)
   RATE_LIMIT_MAX_REQUESTS=10          # Max requests per time window
   RATE_LIMIT_WINDOW_SECONDS=60        # Rate limit time window
   MAX_PROMPT_LENGTH=10000             # Maximum user input length
   MAX_JIRA_FIELD_LENGTH=32000         # Maximum JIRA field length
   MAX_FILE_SIZE_MB=10                 # Maximum file upload size
   MCP_TIMEOUT=30                      # MCP call timeout in seconds
   ```

## Usage

### 1. Start the Application

```bash
streamlit run app.py
```

Access at: http://localhost:8501

### 2. Upload Input Files

The application requires three types of input:

#### Business Needs (Required) - `.md` or `.txt` file
Example content:
```markdown
# Business Requirements

## Objective
Develop an e-commerce platform with AI-powered recommendations.

## Key Requirements
- User authentication and profiles
- Product catalog with search
- Shopping cart and checkout
- AI-based product recommendations
```

#### User Feedback (Required) - `.md` or `.txt` file
Example content:
```markdown
# User Feedback

## Pain Points
- Current checkout process is too slow
- Search results are not relevant
- Want personalized recommendations

## Feature Requests
- One-click checkout
- Save favorite items
- Email notifications for price drops
```

#### Market Trends (Optional) - `.json` file
Example content:
```json
{
  "trends": [
    "Mobile-first shopping experiences",
    "AI-powered personalization",
    "Social commerce integration"
  ],
  "competitors": {
    "feature_gaps": ["Live chat support", "AR product preview"]
  }
}
```

### 3. Review and Confirm

1. Upload all required files (Business Needs + User Feedback)
2. Optionally upload Market Trends
3. Click **"Review & Confirm Files"**
4. Review the AI-generated summary
5. Click **"Generate Feature Specifications"**

### 4. Generate Features

The AI analyzes your inputs and generates 3-5 features with:
- Feature title and description
- Business value proposition
- Priority (High/Medium/Low)
- Complexity (High/Medium/Low)
- Acceptance criteria (3-5 items)
- Dependencies

### 5. Create JIRA Epics and Stories

1. Review the generated features
2. Reply **"yes"** in the chat to create JIRA issues
3. The system performs the following:
   - Create one Epic per feature
   - Create Stories from acceptance criteria
   - Automatically link Stories to parent Epics
   - Add story points as comments
   - Generate implementation details and Definition of Done

## Project Structure

```
plan-ai-requirements-manager/
├── app.py                      # Main Streamlit application
├── proxy_jira_mcp.py           # Local MCP proxy server
├── requirements.txt            # Python dependencies
├── .env.example                # Environment configuration template
├── .streamlit/                 # Streamlit configuration
│   └── config.toml             # Upload limits and theme
├── README.md                   # This file
├── LICENSE                     # MIT-0 License
│
├── src/                        # Source code
│   ├── agents/                 # AI agents
│   │   ├── feature_agent.py    # Feature generation
│   │   ├── epic_agent.py       # Epic creation
│   │   └── story_agent.py      # Story generation
│   ├── tracking/               # Progress tracking
│   │   └── progress_tracker.py
│   └── utils/                  # Utilities
│       ├── file_handler.py     # File operations
│       ├── mcp_client.py       # MCP protocol client
│       └── security.py         # Security utilities
│
├── docs/                       # Documentation
│   ├── architecture.md         # Architecture diagrams
│   └── SECURITY.md             # Security design document
│
├── inputs_data/                # Sample input files
│   ├── business_requirements.md
│   ├── market_analysis.json
│   └── user_feedback.txt
│
└── outputs/                    # Generated outputs (gitignored)
    └── .gitkeep
```

## Key Features Explained

### Automatic Epic-Story Linking

The system automatically creates parent-child relationships in JIRA:
- Each feature becomes an Epic
- Each acceptance criterion becomes a Story
- Stories are automatically linked to their parent Epic
- No manual linking required!

**How it works**:
1. Backend MCP server supports `parent` field
2. Proxy MCP server maps `parent_epic` → `parent`
3. JIRA API creates proper parent-child hierarchy
4. Stories appear under their Epic in JIRA

### AI-Powered Story Generation

For each acceptance criterion, the AI generates:
- **Story Title**: Concise, scrum-board friendly (max 50 chars)
- **Implementation Details**: Technical requirements
- **Definition of Done**: Specific, testable outcomes
- **Story Points**: Estimated effort (1-5 points)

### Session Management

Each session gets a unique ID and tracks:
- Uploaded files (in memory)
- Generated features
- Created JIRA issues
- Output files

## Configuration

### Amazon Bedrock

Model: `us.anthropic.claude-sonnet-4-6` (Claude Sonnet 4)

Verify your AWS credentials have access to Amazon Bedrock in your configured region.

### JIRA Integration

The application uses an MCP (Model Context Protocol) server for JIRA integration:

1. **Proxy MCP Server** (`proxy_jira_mcp.py`): Local proxy that handles authentication and forwards requests
2. **Backend MCP Server** (AWS Lambda): Executes JIRA API calls

The backend MCP server is available as a sibling pattern in this repository:
[`implement-taskmanagement-jira-mcp`](../implement-taskmanagement-jira-mcp/). To set it up:

1. Deploy the backend following its [README](../implement-taskmanagement-jira-mcp/README.md)
2. After deployment, get your API Gateway URL:
   ```bash
   aws cloudformation describe-stacks --stack-name JiraMcpServerStack-dev \
     --query 'Stacks[0].Outputs[?OutputKey==`McpApiEndpoint`].OutputValue' --output text
   ```
3. Get a fresh access token:
   ```bash
   cd ../implement-taskmanagement-jira-mcp
   ./get_fresh_token.sh
   ```
4. Set both values in your `.env`:
   ```
   MCP_BACKEND_URL=<API Gateway URL from step 2>
   MCP_ACCESS_TOKEN=<token from step 3>
   ```

Required JIRA permissions:
- Create issues (Epic, Story)
- Add comments
- Set parent field

## Troubleshooting

### Application won't start
- Check Python version: `python --version` (requires 3.9+)
- Verify virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`

### Amazon Bedrock errors
- Verify AWS credentials: `aws sts get-caller-identity`
- Check Amazon Bedrock access in your region
- Verify model ID is correct in `.env`

### JIRA integration issues
- Verify MCP server path in `.env`
- Check JIRA project key exists
- Verify OAuth token is fresh (refresh if needed)
- Verify project supports Epic and Story issue types

### Files not uploading
- Check file formats: Business Needs/User Feedback must be `.md` or `.txt`, Market Trends must be `.json`
- Verify files are not empty
- Check file size (default limit: 10MB, configurable via `MAX_FILE_SIZE_MB`)
- Try refreshing the browser

### Rate limit errors
- Default limit: 10 requests per 60 seconds
- Adjust via `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` in `.env`
- Wait for the time window to reset
- Consider increasing limits for production use

## Development

### Running Tests

No automated tests are currently included in this repository.

### Code Style

The project uses:
- `flake8` for linting
- Type hints for better code clarity
- Pydantic models for data validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review [docs/SECURITY.md](docs/SECURITY.md) for security-related questions
3. Check JIRA MCP server logs

## Changelog

### Latest Version
- ✅ Multi-file upload support (Business Needs, User Feedback, Market Trends)
- ✅ Automatic epic-story linking
- ✅ AI-powered story generation with DoD
- ✅ Story points estimation
- ✅ Clean architecture with MCP integration
- ✅ Session-based output management
- ✅ Comprehensive security features (input sanitization, rate limiting, validation)
- ✅ Production-ready configuration

### Previous Features
- Single file upload
- Basic feature generation
- Manual JIRA linking (deprecated)

See [docs/SECURITY.md](docs/SECURITY.md) for historical security documentation.

## Architecture Notes

### Clean Separation of Concerns

1. **Application Layer** (`app.py`, `src/agents/`):
   - Pure business logic
   - No JIRA-specific code
   - Works with any MCP server

2. **MCP Client** (`src/utils/mcp_client.py`):
   - Generic MCP protocol implementation
   - No knowledge of JIRA
   - Reusable for other integrations

3. **MCP Servers** (external):
   - Proxy: Local authentication and field mapping
   - Backend: AWS Lambda with JIRA API integration

This architecture allows easy swapping of JIRA with other project management tools by simply changing the MCP server.

## Sample Workflow

```
1. User uploads files
   ↓
2. AI generates summary
   ↓
3. User confirms
   ↓
4. AI analyzes requirements
   ↓
5. AI generates 3-5 features
   ↓
6. User approves
   ↓
7. System creates JIRA epics
   ↓
8. System creates stories with:
   - Implementation details
   - Definition of Done
   - Story points
   - Automatic parent linking
   ↓
9. Done! Check JIRA for results
```

## Performance

- Feature generation: ~10-15 seconds
- Epic/Story creation: ~2-3 seconds per issue
- Typical session: 3-5 features = 15-25 JIRA issues created in ~1 minute

## Security

For the full security design document, IAM policies, Amazon Bedrock security guidelines, and shared responsibility model, see [docs/SECURITY.md](docs/SECURITY.md).

### Built-in Security
- ✅ **Input Sanitization**: Designed to help prevent prompt injection and XSS attacks
- ✅ **Rate Limiting**: Helps protect against API abuse (configurable limits)
- ✅ **File Upload Validation**: Size limits and content validation
- ✅ **Path Validation**: Designed to prevent path traversal attacks
- ✅ **Error Sanitization**: Generic error messages in production
- ✅ **JIRA Validation**: Startup validation of JIRA configuration; HTTPS enforced
- ✅ **Configurable Timeouts**: Helps prevent hanging connections
- ✅ **Environment-based Logging**: Secure logging levels
- ✅ **Session Encryption**: Fernet symmetric encryption for session data

### Authentication
- JIRA OAuth tokens managed by external MCP server
- Application is designed to not handle JIRA credentials directly
- Token refresh handled by external script

### Shared Responsibility
- AWS manages Amazon Bedrock infrastructure security, API endpoint protection, and model hosting
- Customers manage application-level security: input validation, rate limiting, IAM policies, credential rotation, and data classification
- See [docs/SECURITY.md](docs/SECURITY.md) for the full responsibility matrix

### Configuration
All security settings are configurable via environment variables in `.env`:
- `LOG_LEVEL`: Control logging verbosity (INFO for production)
- `RATE_LIMIT_MAX_REQUESTS`: Max requests per time window
- `MAX_FILE_SIZE_MB`: Maximum upload size
- `MAX_PROMPT_LENGTH`: Maximum user input length
- `MCP_TIMEOUT`: Timeout for MCP calls

**Streamlit Configuration** (`.streamlit/config.toml`):
- `maxUploadSize`: Set to 10MB to match security settings
- This ensures the UI shows the correct file size limit

### Production Deployment
For production deployment:
1. Set `LOG_LEVEL=WARNING` or `ERROR`
2. Generate new `SESSION_ENCRYPTION_KEY`
3. Review and adjust rate limits
4. Configure external logging service (Amazon CloudWatch, Splunk)
5. Set up monitoring for security events

See [docs/SECURITY.md](docs/SECURITY.md) for detailed security documentation.


## Disclaimer

The solution architecture sample code is provided without any guarantees, and you're not recommended to use it for production-grade workloads. The intention is to provide content to build and learn. Be sure of reading the licensing terms.

## Security

See [CONTRIBUTING](https://github.com/aws-samples/sample-ai-powered-sdlc-patterns-with-aws/blob/main/CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.

