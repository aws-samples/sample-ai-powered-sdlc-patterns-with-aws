# Knowledge Base Monitoring and Analytics Implementation

## Overview

This document describes the comprehensive monitoring and analytics infrastructure implemented for the AI Assistant Knowledge Base system. The implementation provides real-time monitoring, custom metrics, alerting, and audit logging for all Knowledge Base operations.

## Architecture Components

### 1. CloudWatch Dashboards

#### Knowledge Base Dashboard
- **Name**: `ai-assistant-knowledge-base-dashboard`
- **Purpose**: Centralized monitoring of all Knowledge Base operations
- **Widgets**:
  - Bedrock Model Performance (latency, throttles, errors)
  - Chat Lambda Performance (duration, errors, invocations)
  - Document Management Lambda Performance
  - DynamoDB Performance (capacity, throttles)
  - Custom Knowledge Base Metrics
  - Ingestion Job Status and Analytics
  - Query Performance Analytics
  - Recent Admin Actions Log

### 2. Custom Metrics Namespaces

#### AI-Assistant/KnowledgeBase
- `QueryResponseTime` - Response time for Knowledge Base queries
- `QuerySuccessRate` - Success rate percentage for queries
- `QueriesExecuted` - Total number of queries executed
- `SourcesFoundPerQuery` - Average number of sources found per query
- `IngestionJobDuration` - Time taken for document ingestion
- `IngestionJobsCompleted` - Count of successful ingestion jobs
- `IngestionJobsFailed` - Count of failed ingestion jobs
- `IngestionJobsInProgress` - Count of currently running jobs
- `IngestionJobSuccessRate` - Success rate for ingestion jobs
- `DocumentProcessingErrors` - Count of document processing errors

#### AI-Assistant/Chat
- `ResponseTime` - Chat response time by model
- `TokenUsage` - Token consumption by model
- `QualityScore` - Response quality metrics (advanced RAG)
- `CompletenessScore` - Response completeness metrics
- `ReliabilityScore` - Response reliability metrics

#### AI-Assistant/Admin
- `AdminActions` - Count of admin actions by type and user
- `OperationDuration` - Duration of admin operations
- `OperationSuccess` - Success/failure count for admin operations

### 3. CloudWatch Alarms

#### Bedrock Model Alarms
- **High Latency**: Triggers when Bedrock invocation latency > 10 seconds
- **Model Errors**: Triggers on Bedrock server errors (threshold: 5 errors)
- **Throttling**: Monitors Bedrock throttling exceptions

#### Lambda Function Alarms
- **Chat Lambda Errors**: Monitors chat function errors (threshold: 10 errors)
- **Document Lambda Errors**: Monitors document function errors (threshold: 5 errors)
- **Admin Lambda Errors**: Monitors admin function errors

#### Knowledge Base Specific Alarms
- **Query Success Rate**: Triggers when success rate < 90%
- **Response Time**: Triggers when average response time > 15 seconds
- **Query Latency**: Performance degradation alarm (> 10 seconds)
- **Ingestion Failures**: Triggers on any ingestion job failure

#### Infrastructure Alarms
- **DynamoDB Throttling**: Monitors DynamoDB throttled requests
- **OpenSearch Performance**: Monitors vector search performance

### 4. Audit Logging

#### Admin Audit Log
- **Log Group**: `/aws/ai-assistant/admin-audit`
- **Purpose**: Track all administrative actions
- **Logged Events**:
  - Knowledge Base status checks
  - Ingestion job management (start, retry, cancel)
  - Metrics access
  - Data source synchronization
  - User access patterns

#### Knowledge Base Metrics Log
- **Log Group**: `/aws/ai-assistant/knowledge-base-metrics`
- **Purpose**: Detailed operational metrics
- **Logged Events**:
  - Query performance details
  - Ingestion job progress
  - Document processing status
  - Error details and stack traces

### 5. SNS Alerting

#### Alert Topic
- **Topic**: `ai-assistant-alerts`
- **Purpose**: Centralized alerting for all monitoring events
- **Subscribers**: Email addresses configured in Terraform variables
- **Alert Types**:
  - Performance degradation
  - Error rate increases
  - Infrastructure issues
  - Security events

## Implementation Details

### Lambda Function Metrics Integration

#### Chat Handler Metrics
```typescript
// Track Knowledge Base query metrics
await this.trackKnowledgeBaseQueryMetrics(
  question,
  userId,
  responseTime,
  success,
  sourcesFound
);

// Track advanced RAG metrics
await this.trackAdvancedMetrics(
  modelUsed,
  tokenUsage,
  responseTime,
  qualityMetrics,
  ragConfig
);
```

#### Admin Service Metrics
```typescript
// Track ingestion job metrics
await trackIngestionJobMetrics(
  jobId,
  status,
  'COMPLETED',
  duration,
  documentsProcessed
);

// Log admin actions for audit
await logAdminAction(
  userId,
  'START_KNOWLEDGE_BASE_SYNC',
  { requestId, ingestionJobId },
  sourceIp,
  userAgent
);
```

### Terraform Configuration

#### Monitoring Module Usage
```hcl
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  
  # Alert configuration
  alert_email_addresses = var.alert_email_addresses
  log_retention_days    = 30
  
  # Resource references for monitoring
  bedrock_model_id                = "anthropic.claude-opus-4-1-20250805-v1:0"
  chat_lambda_function_name       = module.chat_handler_lambda.chat_handler_function_name
  document_lambda_function_name   = module.document_management_lambda.lambda_function_name
  admin_lambda_function_name      = module.admin_management_lambda.lambda_function_name
  documents_table_name            = module.dynamodb.table_name
  knowledge_base_id               = aws_bedrockagent_knowledge_base.main.id
  s3_bucket_name                  = aws_s3_bucket.documents.bucket
}
```

## Monitoring Workflows

### 1. Document Upload Monitoring
1. Document uploaded to S3
2. Ingestion job started (tracked with `STARTED` metrics)
3. Processing monitored via CloudWatch logs
4. Completion tracked with success/failure metrics
5. Alerts sent if ingestion fails

### 2. Query Performance Monitoring
1. Query received by chat handler
2. Response time measured
3. Success/failure tracked
4. Source count recorded
5. Quality metrics calculated (advanced RAG)
6. Alerts triggered for performance degradation

### 3. Admin Action Auditing
1. Admin action initiated
2. User, action, and context logged
3. Operation duration measured
4. Success/failure recorded
5. Audit trail maintained in CloudWatch Logs

## Dashboard Access

### CloudWatch Console
- **URL Pattern**: `https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards:name=ai-assistant-knowledge-base-dashboard`
- **Access**: Requires AWS console access with CloudWatch permissions

### Key Metrics to Monitor

#### Performance Metrics
- Average query response time (target: < 10 seconds)
- Query success rate (target: > 95%)
- Ingestion job completion rate (target: > 90%)
- Token usage efficiency

#### Operational Metrics
- Active ingestion jobs
- Document processing throughput
- Error rates by component
- Admin action frequency

#### Cost Metrics
- Bedrock model usage costs
- OpenSearch Serverless OCU consumption
- Lambda execution costs
- CloudWatch logs storage costs

## Alerting Thresholds

### Critical Alerts (Immediate Response)
- Knowledge Base query success rate < 90%
- Bedrock model errors > 5 per 5 minutes
- Any ingestion job failure
- DynamoDB throttling events

### Warning Alerts (Monitor Closely)
- Query response time > 10 seconds
- Lambda function errors > threshold
- High token usage costs
- Unusual admin activity patterns

### Informational Alerts
- Ingestion job completions
- Performance trend changes
- Capacity utilization updates

## Troubleshooting Guide

### High Query Latency
1. Check Bedrock model performance metrics
2. Review OpenSearch Serverless OCU usage
3. Analyze Knowledge Base retrieval configuration
4. Check Lambda function memory allocation

### Ingestion Job Failures
1. Review ingestion job logs in CloudWatch
2. Check S3 bucket permissions and access
3. Verify document format compatibility
4. Monitor OpenSearch collection capacity

### Alert Fatigue
1. Review alert thresholds and adjust if needed
2. Implement alert suppression for known issues
3. Use composite alarms for complex conditions
4. Regular review of alert effectiveness

## Security Considerations

### Access Control
- CloudWatch dashboard access via IAM roles
- Log group access restricted to authorized users
- SNS topic subscription management
- Audit log retention and access controls

### Data Privacy
- PII scrubbing in log messages
- Secure transmission of metrics data
- Encrypted storage of audit logs
- Access logging for compliance

## Cost Optimization

### Metrics Storage
- Appropriate retention periods for different log types
- Efficient metric aggregation strategies
- Regular cleanup of old metrics data

### Alerting Costs
- Optimized SNS usage
- Consolidated alert messages
- Appropriate alert frequency settings

## Testing and Validation

### Monitoring Test Suite
Run the comprehensive test suite to validate monitoring implementation:

```bash
cd terraform
npx ts-node test-monitoring-implementation.ts
```

### Test Coverage
- CloudWatch dashboard accessibility
- All expected alarms configured
- Log groups created and accessible
- SNS topics configured
- Custom metrics namespaces active

## Maintenance

### Regular Tasks
- Review alert effectiveness monthly
- Update dashboard widgets as needed
- Clean up old log data
- Monitor costs and optimize

### Quarterly Reviews
- Analyze monitoring data trends
- Update alert thresholds based on performance
- Review audit logs for security insights
- Optimize dashboard layout and metrics

## Success Metrics

### Implementation Quality
- All monitoring components deployed successfully
- Zero false positive alerts in first week
- Complete audit trail for all admin actions
- Dashboard provides actionable insights

### Operational Excellence
- Mean time to detection (MTTD) < 5 minutes
- Mean time to resolution (MTTR) < 30 minutes
- 99.9% monitoring system uptime
- Complete visibility into Knowledge Base operations

This comprehensive monitoring and analytics implementation ensures full observability of the AI Assistant Knowledge Base system, enabling proactive issue detection, performance optimization, and operational excellence.