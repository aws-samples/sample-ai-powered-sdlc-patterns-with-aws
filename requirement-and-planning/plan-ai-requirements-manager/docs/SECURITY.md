# Security Design Document

## 1. Security Architecture Overview

This application processes business requirements through Amazon Bedrock AI and creates JIRA issues via MCP servers. Security is implemented in layers:

- **Input layer**: Sanitization, validation, and rate limiting before any processing
- **Processing layer**: Isolated AI agents with no direct external access
- **Integration layer**: Hardened subprocess communication and HTTPS-only external calls
- **Storage layer**: Path-validated local file operations
- **Encryption layer**: Fernet symmetric encryption for session data; TLS for all network traffic

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Fernet encryption for session data | Industry-standard symmetric encryption via `cryptography` library; replaces initial XOR placeholder |
| Environment-variable-based secrets | Avoids hardcoded keys; supports rotation without code changes |
| HTTPS-only JIRA connections | Prevents credential exposure over unencrypted channels |
| Subprocess with shell=False | Prevents shell injection in MCP server communication |
| Path validation with realpath | Prevents symlink-based path traversal attacks |
| Rate limiting per session | Mitigates automated abuse without impacting legitimate multi-user scenarios |

## 2. Amazon Bedrock Security Guidelines

### Authentication and Credentials

- The application uses boto3's default credential chain. In production, use **IAM roles** (EC2 instance profiles, ECS task roles, or Lambda execution roles) rather than static access keys.
- boto3 handles credential refresh automatically when using IAM roles or AWS SSO.
- Do not store `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in `.env` files or source code.

### Data Privacy

- Prompts sent to Amazon Bedrock may contain business requirements and market analysis data. Review your organization's data classification policies before processing sensitive content.
- Amazon Bedrock does not use customer inputs to train models. See [Amazon Bedrock Data Privacy](https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html).
- All communication with Amazon Bedrock uses TLS 1.2+ encryption in transit (enforced by boto3).

### Model Access Controls

- Restrict `bedrock:InvokeModel` to the specific model ARN used by this application (see IAM Policy section below).
- Use AWS CloudTrail to audit all Amazon Bedrock API invocations.
- The application uses `adaptive` retry mode with `max_attempts=10` to handle transient throttling. Monitor CloudWatch metrics to detect abnormal invocation patterns.

### Rate Limiting and Quotas

- Amazon Bedrock enforces per-account rate limits. The application's own rate limiting (configurable via `RATE_LIMIT_MAX_REQUESTS`) provides an additional layer.
- Monitor `ThrottlingException` errors in application logs to detect quota pressure.

### Error Handling

- All Amazon Bedrock API calls are wrapped in try/except blocks that raise `RuntimeError` with context.
- Error messages are sanitized via `sanitize_error_message()` before being shown to users to avoid leaking internal details.

## 3. IAM Policy Documentation

### Minimum Required Permissions

The application requires only `bedrock:InvokeModel` scoped to the specific model and region. Replace `us-east-1` with your configured `AWS_REGION`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBedrockInvokeModel",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-20250514-v1:0",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

### Recommended Production Policy (with region restriction)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBedrockInvokeModelRegionScoped",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-20250514-v1:0",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

Replace `us-east-1` with your configured `AWS_REGION`.

### Credential Best Practices

| Environment | Recommended Approach |
|-------------|---------------------|
| Local development | AWS SSO (`aws sso login`) or named profiles with temporary credentials |
| EC2 | Instance profile with the IAM role above |
| ECS / Fargate | Task execution role |
| Lambda | Execution role |

- **Do not** use long-lived IAM user access keys.
- **Do not** add `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` to `.env` files.
- Enable MFA on any IAM user that has console access.
- Review IAM access quarterly using IAM Access Analyzer.

### Access Review Procedures

1. Run `aws iam list-attached-role-policies --role-name <role>` to verify only the minimum policy is attached.
2. Enable AWS CloudTrail and review `InvokeModel` events monthly.
3. Use IAM Access Analyzer to identify unused permissions.

## 4. AWS Lambda and IAM Security Guidelines

### AWS Lambda (Backend MCP Server)

- **Execution role**: Assign a dedicated IAM execution role to the Lambda function with only the permissions it needs (e.g., `jira:*` via JIRA OAuth, no AWS service permissions beyond what is required).
- **Least privilege**: Do not attach `AdministratorAccess` or broad managed policies. Scope permissions to specific resources.
- **Environment variables**: Store JIRA OAuth tokens and other secrets in Lambda environment variables encrypted with AWS KMS, or retrieve them from AWS Secrets Manager at runtime.
- **VPC configuration**: If the Lambda function accesses private resources, deploy it inside a VPC with appropriate security groups and subnet routing.
- **Timeout and memory**: Set a conservative timeout (e.g., 30 seconds) and memory allocation to limit blast radius from runaway invocations.
- **Concurrency limits**: Set reserved concurrency to prevent the function from consuming all available Lambda capacity in the account.
- **Logging**: Enable Amazon CloudWatch Logs for the Lambda function. Review logs for unexpected invocation patterns or errors.
- **Code signing**: Consider enabling Lambda code signing to verify that only trusted deployment packages are executed.

### IAM Credentials

- **Prefer IAM roles over access keys**: Use EC2 instance profiles, ECS task roles, or Lambda execution roles instead of long-lived IAM user access keys.
- **Credential rotation**: If static access keys are unavoidable, rotate them at least every 90 days. Use IAM Access Analyzer to identify unused credentials.
- **MFA enforcement**: Require MFA for any IAM user with console access or the ability to assume privileged roles.
- **Permission boundaries**: Apply IAM permission boundaries to limit the maximum permissions any role or user can have, even if broader policies are attached.
- **Service control policies (SCPs)**: In AWS Organizations, use SCPs to enforce guardrails (e.g., deny `bedrock:*` outside approved regions).
- **Audit with CloudTrail**: Enable AWS CloudTrail in all regions and review `AssumeRole`, `CreateAccessKey`, and `AttachRolePolicy` events regularly.
- **Access Analyzer**: Run IAM Access Analyzer to detect roles and policies that grant unintended external access.

## 6. Shared Responsibility Model

### AWS Responsibilities

AWS manages security **of** the cloud:

| Area | AWS Manages |
|------|-------------|
| Amazon Bedrock | Model hosting, API endpoint security, encryption of data at rest within the service, DDoS protection, physical infrastructure |
| Network | TLS termination, VPC infrastructure, AWS PrivateLink endpoints |
| Lambda (MCP Backend) | Execution environment isolation, OS patching, runtime security |
| IAM | Authentication infrastructure, credential vaulting, STS token issuance |

### Customer Responsibilities

Customers manage security **in** the cloud:

| Area | Customer Manages |
|------|-----------------|
| Application security | Input sanitization, rate limiting, prompt injection mitigation, error handling |
| IAM configuration | Least-privilege policies, credential rotation, MFA enforcement |
| Data classification | Determining sensitivity of business requirements and AI outputs |
| Encryption keys | Generating and rotating `SESSION_ENCRYPTION_KEY`, securing `.env` files |
| JIRA credentials | OAuth token management, refresh procedures, access scoping |
| MCP server security | Validating MCP server script integrity, securing the execution environment |
| File security | Ensuring uploaded files do not contain sensitive data beyond what is intended for AI processing |
| Monitoring | Setting up CloudWatch alarms, reviewing CloudTrail logs, monitoring rate limit events |
| Network security | Configuring security groups, NACLs, and VPC settings for production deployments |

### Security Controls Mapping

| Control | Implemented By | Location |
|---------|---------------|----------|
| Prompt sanitization | Customer (this app) | `src/utils/security.py` → `sanitize_prompt()` |
| Rate limiting | Customer (this app) | `src/utils/security.py` → `rate_limit()` |
| File upload validation | Customer (this app) | `src/utils/security.py` → `validate_file_upload()` |
| Path traversal prevention | Customer (this app) | `src/utils/file_handler.py` → `_validate_path()` |
| Session encryption | Customer (this app) | `src/utils/security.py` → `encrypt_session_data()` (Fernet) |
| TLS for Amazon Bedrock API | AWS (boto3 default) | Enforced by AWS SDK |
| TLS for JIRA API | AWS + Customer | Backend MCP server uses HTTPS; customer verifies JIRA URL is HTTPS |
| IAM authentication | AWS + Customer | AWS provides IAM; customer configures least-privilege policies |
| Model access control | AWS + Customer | AWS enforces IAM; customer scopes `bedrock:InvokeModel` to specific model ARN |
| Subprocess hardening | Customer (this app) | `src/utils/mcp_client.py` → path validation, shell=False, realpath resolution |

## 7. Encryption Details

### Encryption in Transit

| Path | Encryption | Managed By |
|------|-----------|------------|
| User → Streamlit | HTTP (localhost) or HTTPS (required in production — see note below) | Customer |
| Application → Amazon Bedrock | TLS 1.2+ | AWS (boto3) |
| MCP Proxy → Backend Lambda | HTTPS | Customer / AWS |
| Backend Lambda → JIRA Cloud | HTTPS | Customer / Atlassian |
| Application → MCP subprocess | Local stdio (same-host IPC) | See note below |

**HTTPS for Streamlit in production**: Streamlit does not terminate TLS by default. For production deployments, place Streamlit behind a reverse proxy (e.g., nginx, AWS Application Load Balancer) that terminates HTTPS. Do not expose the Streamlit port directly on a public interface without TLS. Example nginx configuration:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Note on MCP subprocess IPC**: Communication between the application and the local MCP proxy server uses stdio pipes on the same host. This is not network traffic and does not traverse any network boundary. The data stays within the same OS process boundary and is protected by OS-level process isolation. JIRA credentials are managed by the MCP proxy server externally and are not passed through the stdio channel.

### Encryption at Rest

| Data | Current State | Recommendation |
|------|--------------|----------------|
| Session data | Fernet-encrypted via `SESSION_ENCRYPTION_KEY` | Rotate key periodically (see key management below) |
| Output files (features.json, traceability.json) | Plaintext on local disk | Use OS-level disk encryption (FileVault on macOS, LUKS on Linux) or encrypt before write for sensitive deployments |
| Input files | Plaintext (user-provided) | User responsibility to classify and protect |
| `.env` file | Plaintext | Restrict file permissions (`chmod 600`); use AWS Secrets Manager in production |

### Key Management

The `SESSION_ENCRYPTION_KEY` is used for Fernet symmetric encryption of session data. Follow these procedures:

| Step | Action |
|------|--------|
| Generation | `python -c "import secrets; print(secrets.token_hex(32))"` — run once per environment |
| Storage | Store in environment variable or AWS Secrets Manager; do not commit to source control |
| Access control | Restrict `.env` file permissions to the application user only (`chmod 600 .env`) |
| Rotation | Generate a new key, update the environment variable, and restart the application. Active sessions will be invalidated on rotation. |
| Backup | Store a backup of the current key in a secure vault (e.g., AWS Secrets Manager) before rotating |
| Compromise response | If the key is exposed, rotate immediately and treat all previously encrypted session data as potentially compromised |

## 8. Security Configuration Reference

| Variable | Default | Purpose | Priority |
|----------|---------|---------|----------|
| `SESSION_ENCRYPTION_KEY` | *(required)* | Fernet encryption key for session data | Critical — must set before production |
| `RATE_LIMIT_MAX_REQUESTS` | 10 | Max requests per time window | High — adjust for expected load |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Rate limit window | High |
| `MAX_PROMPT_LENGTH` | 10000 | Max user input characters | High — limits prompt injection surface |
| `MAX_FILE_SIZE_MB` | 10 | Max upload size in MB | High — prevents resource exhaustion |
| `MAX_JIRA_FIELD_LENGTH` | 32000 | Max JIRA field length | Medium — aligns with JIRA API limits |
| `MCP_TIMEOUT` | 30 | MCP call timeout in seconds | Medium — prevents hanging connections |
| `LOG_LEVEL` | INFO | Logging verbosity | Medium — use WARNING+ in production |


## 9. Risk Assessment

### Identified Risks

| Risk | Category | Likelihood | Impact | Mitigation | Residual Risk |
|------|----------|-----------|--------|------------|---------------|
| Prompt injection via user input | Security | Medium | Medium | `sanitize_prompt()` filters known patterns; template injection prevented by brace escaping in agents | Sophisticated novel injection patterns may bypass filters |
| Oversized file upload causing resource exhaustion | Security | Low | Medium | `validate_file_upload()` enforces `MAX_FILE_SIZE_MB` limit; Streamlit config caps upload size | None significant |
| JIRA API rate limiting / throttling | Operational | Medium | Low | Application rate limiting via `rate_limit()`; MCP timeout prevents hanging | Burst creation of many epics/stories may hit JIRA limits |
| Amazon Bedrock throttling | Operational | Low | Medium | boto3 adaptive retry with `max_attempts=10`; application rate limiting | Extended outages require manual retry |
| MCP server script tampering | Security | Low | High | Path validation rejects symlinks and world-writable files; `realpath` resolution | Attacker with write access to the script path could modify it |
| Credential exposure in logs | Security | Low | High | `sanitize_error_message()` strips internal details; `LOG_LEVEL=WARNING+` in production | Debug-level logging may expose sensitive context |
| AI-generated content inaccuracy | Operational | Medium | Medium | Human review before JIRA creation; features displayed for approval before proceeding | Users may approve without thorough review |
| Path traversal via crafted filenames | Security | Low | High | `_validate_path()` with `resolve()` and `relative_to()` checks; symlink rejection | None significant |
| Session encryption key compromise | Security | Low | High | Key sourced from environment variable; Fernet provides authenticated encryption | Key rotation requires application restart |

### Compliance Considerations

- **Data privacy**: Business requirements processed by Amazon Bedrock are subject to the [AWS Data Privacy policy](https://aws.amazon.com/compliance/data-privacy/). Amazon Bedrock does not use customer inputs for model training.
- **GDPR/CCPA**: If uploaded documents contain personal data, customers are responsible for ensuring compliance with applicable data protection regulations.
- **SOC 2**: Amazon Bedrock is SOC 2 compliant. Application-level controls (input validation, access logging, encryption) support customer SOC 2 compliance efforts.

### Operational Risks

- **Amazon Bedrock availability**: The application depends on Amazon Bedrock API availability. Monitor the [AWS Health Dashboard](https://health.aws.amazon.com/) for service status.
- **JIRA API dependencies**: JIRA Cloud availability and API rate limits affect issue creation. The MCP timeout (`MCP_TIMEOUT`) prevents indefinite blocking.
- **Local storage**: Output files are stored on local disk. Disk failure results in data loss. For production, consider backing up the `outputs/` directory.

## 10. Data Classification

| Data Type | Classification | Handling Requirements |
|-----------|---------------|----------------------|
| Business requirements (uploaded .md files) | Confidential | Validate before processing; do not log content; store locally only |
| Market analysis (uploaded .json files) | Internal | Validate JSON structure; do not log content |
| User feedback (uploaded .txt files) | Internal | Validate before processing; do not log content |
| AI-generated features | Internal | Store in `outputs/`; review before sharing externally |
| JIRA issue content (epics, stories) | Internal | Created via MCP server; content visible in JIRA per project permissions |
| Traceability data (traceability.json) | Internal | Contains JIRA keys and feature mappings; restrict file access |
| Session encryption key | Restricted | Store in environment variable only; do not commit to source control |
| AWS credentials | Restricted | Use IAM roles; do not store in `.env` or source code |
| JIRA OAuth tokens | Restricted | Managed by external MCP server; application does not handle directly |

## 11. AI Output Review, Bias Considerations, and Dataset Compliance

### Human Review Process

All AI-generated content goes through a mandatory human review step before any external action:

1. **Feature generation**: AI generates features → displayed in chat → user reviews and explicitly confirms before proceeding to epic creation.
2. **Epic creation**: User must reply "yes" in chat to trigger JIRA epic creation. No automatic creation occurs.
3. **Story generation**: Stories are generated and displayed for review. JIRA creation requires explicit user confirmation.

At no point does the application create JIRA issues without user approval.

### Bias and Fairness Considerations

- **Priority assignment**: AI assigns priority levels (High/Medium/Low) based on the input requirements. These are suggestions and should be validated against business objectives by the product team.
- **Complexity estimates**: Story point estimates are AI-generated starting points. Teams should re-estimate during sprint planning using their own velocity data.
- **Feature selection**: The AI generates 3-5 features from requirements. It may favor features that are more explicitly described in the input. Ensure input documents represent all stakeholder perspectives.
- **Recommendation**: Treat all AI outputs as drafts requiring human judgment. The application is a productivity tool, not a decision-making authority.

### Dataset Compliance

- Input files (business requirements, market analysis, user feedback) are provided by the user. The user is responsible for confirming they have the right to process this data and that it complies with applicable data protection regulations (GDPR, CCPA, etc.).
- Before processing user-uploaded data through Amazon Bedrock, confirm the following:
  1. The data owner has authorized AI processing of the content.
  2. The data does not contain personal data unless a lawful basis for processing exists.
  3. The data classification (Confidential, Internal, Public) is understood and appropriate handling is applied.
- No third-party training datasets are used by the application itself. Amazon Bedrock model training data is managed by AWS and Anthropic.
- Output files are derived from user inputs and AI processing. They inherit the classification of the input data.

### Third-Party MCP Server Legal Approval

This application integrates with a third-party MCP server (`jira-mcp-server`) for JIRA integration. Before deploying this integration in a production environment, confirm the following:

| Requirement | Action Required |
|-------------|----------------|
| Right to use | Verify the MCP server license permits your intended use (commercial, internal, etc.) |
| Distribution | If bundling or redistributing the MCP server, confirm the license allows it |
| Security assessment | Review the MCP server source code or obtain a security attestation before deployment |
| Data handling | Confirm the MCP server does not log or transmit JIRA credentials or issue content to third parties |
| Dependency review | Audit the MCP server's dependencies for known vulnerabilities before deployment |

Document the outcome of this review in your organization's software approval records before production deployment.

## 12. Audit Logging

### Logged Events

| Event | Logger | Level | Location |
|-------|--------|-------|----------|
| File read operations | `src.utils.file_handler` | INFO | `FILE_READ: path=..., size=...` |
| File write operations | `src.utils.file_handler` | INFO | `FILE_WRITE: path=..., type=...` |
| Rate limit exceeded | `src.utils.security` | WARNING | `SECURITY EVENT: rate_limit` |
| Input validation failure | `src.utils.security` | WARNING | `SECURITY EVENT: validation_error` |
| Prompt injection detected | `src.utils.security` | WARNING | `Potential prompt injection detected` |
| MCP server start/stop | `src.utils.mcp_client` | INFO | `Starting/Stopping MCP server` |
| MCP tool call failure | `src.utils.mcp_client` | WARNING | `MCP tool call failed` |
| Amazon Bedrock API failure | Agent modules | ERROR | `Amazon Bedrock API call failed` |

### Production Logging Configuration

Set `LOG_LEVEL=WARNING` in production to capture security events without verbose debug output. For full audit trails, configure a log aggregation service:

```bash
# .env for production
LOG_LEVEL=WARNING
```

For centralized logging, pipe application output to Amazon CloudWatch Logs, Splunk, or your preferred SIEM.

## 13. Security Implementation Priority

| Priority | Control | Status | Expected Impact |
|----------|---------|--------|-----------------|
| 1 - Critical | `SESSION_ENCRYPTION_KEY` configuration | Required before production | Protects session data with Fernet encryption |
| 2 - Critical | Input sanitization (`sanitize_prompt`) | Implemented | Helps reduce risk of prompt injection |
| 3 - Critical | Path validation (`_validate_path`) | Implemented | Designed to prevent path traversal attacks |
| 4 - High | HTTPS enforcement for JIRA URL | Implemented | Prevents credential exposure over unencrypted connections |
| 5 - High | Rate limiting | Implemented | Helps mitigate automated abuse |
| 6 - High | File upload validation | Implemented | Helps prevent resource exhaustion and malicious uploads |
| 7 - High | IAM least-privilege policy | Documented | Restricts Amazon Bedrock access to specific model ARN |
| 8 - Medium | MCP subprocess hardening | Implemented | Reduces command injection risk via path validation and shell=False |
| 9 - Medium | Error message sanitization | Implemented | Prevents internal detail leakage to users |
| 10 - Medium | Access logging | Implemented | Provides audit trail for file operations and security events |
| 11 - Low | Configurable timeouts | Implemented | Prevents resource exhaustion from hanging connections |
