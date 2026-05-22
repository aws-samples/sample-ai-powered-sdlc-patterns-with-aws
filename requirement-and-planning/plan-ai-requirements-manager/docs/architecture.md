# Architecture

## System Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface"
        UI[Streamlit Web UI<br/>File Upload · Chat · Progress]
    end

    subgraph "Application Layer"
        APP[app.py<br/>Session Management · Routing]
        FA[FeatureAgent<br/>Generates features from requirements]
        EA[EpicAgent<br/>Transforms features into epics]
        SA[StoryAgent<br/>Breaks epics into user stories]
        FH[FileHandler<br/>Input loading · Output persistence]
        SEC[Security Module<br/>Sanitization · Rate Limiting · Encryption]
        PT[ProgressTracker<br/>Completion metrics]
    end

    subgraph "AI Service"
        BEDROCK[Amazon Bedrock<br/>Claude Sonnet 4<br/>us.anthropic.claude-sonnet-4-20250514-v1:0]
    end

    subgraph "MCP Integration"
        MCP_CLIENT[MCP Client<br/>Generic JSON-RPC over stdio]
        PROXY[Proxy MCP Server<br/>Local · Auth · Field Mapping]
        BACKEND[Backend MCP Server<br/>AWS Lambda · JIRA API]
    end

    subgraph "External Services"
        JIRA[JIRA Cloud<br/>Epics · Stories · Linking]
    end

    subgraph "Local Storage"
        INPUTS[inputs_data/<br/>Business Reqs · Market Analysis · Feedback]
        OUTPUTS[outputs/<br/>features.json · traceability.json · Markdown]
    end

    UI -->|User prompts & file uploads| APP
    APP --> SEC
    APP --> FA
    APP --> EA
    APP --> SA
    APP --> FH
    APP --> PT

    FA -->|invoke_model| BEDROCK
    EA -->|invoke_model| BEDROCK
    SA -->|invoke_model| BEDROCK

    APP -->|call_mcp_tool| MCP_CLIENT
    MCP_CLIENT -->|stdio JSON-RPC| PROXY
    PROXY -->|HTTPS| BACKEND
    BACKEND -->|HTTPS REST API| JIRA

    FH -->|Read| INPUTS
    FH -->|Write| OUTPUTS
    PT -->|Read| OUTPUTS

    BEDROCK -.->|TLS 1.2+ encrypted| FA
    BEDROCK -.->|TLS 1.2+ encrypted| EA
    BEDROCK -.->|TLS 1.2+ encrypted| SA
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant App as app.py
    participant Sec as Security Module
    participant FA as FeatureAgent
    participant EA as EpicAgent
    participant SA as StoryAgent
    participant BR as Amazon Bedrock
    participant MCP as MCP Client
    participant JIRA as JIRA Cloud

    U->>UI: Upload files (md, json)
    UI->>App: File content (in-memory)
    App->>Sec: validate_file_upload()
    App->>Sec: sanitize_prompt()

    U->>UI: "Generate features"
    UI->>App: Chat prompt
    App->>Sec: rate_limit(session_id)
    App->>FA: generate_features(requirements)
    FA->>BR: invoke_model (HTTPS/TLS)
    BR-->>FA: Feature specifications (JSON)
    FA-->>App: List[Feature]
    App->>App: Save features.json & features.md

    U->>UI: "Create JIRA epics"
    UI->>App: Confirmation
    App->>EA: generate_epics(features)
    EA->>BR: invoke_model (HTTPS/TLS)
    BR-->>EA: Epic specifications
    EA-->>App: List[Epic]

    loop For each Epic
        App->>MCP: jira_create_issue(epic)
        MCP->>JIRA: Create Epic
        JIRA-->>MCP: Epic key (e.g. PROJ-1)

        App->>SA: generate_stories(epic)
        SA->>BR: invoke_model (HTTPS/TLS)
        BR-->>SA: Story specifications

        loop For each Story
            App->>MCP: jira_create_issue(story, parent=epic_key)
            MCP->>JIRA: Create Story linked to Epic
        end
    end

    App->>App: Save traceability.json
    App-->>UI: Summary with JIRA links
```

## Component Responsibilities

| Component | Responsibility | Security Controls |
|-----------|---------------|-------------------|
| app.py | Session management, routing, orchestration | Rate limiting, input validation |
| FeatureAgent | Generate features from business requirements | Input sanitization before prompt construction |
| EpicAgent | Transform features into epic specifications | Input sanitization, template injection prevention |
| StoryAgent | Break epics into user stories | Input sanitization, template injection prevention |
| FileHandler | Read inputs, write outputs with path validation | Path traversal prevention, symlink rejection, size limits |
| Security Module | Centralized security utilities | Fernet encryption, rate limiting, prompt sanitization |
| MCP Client | Generic JSON-RPC communication over stdio | Path validation, subprocess hardening |
| ProgressTracker | Calculate completion metrics from traceability data | Read-only operations, error handling |

## Trust Boundaries

1. **User → Application**: All user input (file uploads, chat prompts) passes through `sanitize_prompt()`, `validate_file_upload()`, and `rate_limit()` before processing.
2. **Application → Amazon Bedrock**: Communication over HTTPS/TLS (managed by boto3). IAM credentials required.
3. **Application → MCP Server**: Local subprocess communication via stdio. Script path validated and resolved before execution.
4. **MCP Proxy → Backend**: HTTPS communication to AWS Lambda.
5. **Backend → JIRA Cloud**: HTTPS REST API with OAuth authentication managed by the MCP server layer.
