/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS monitoring infrastructure deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# CloudWatch Monitoring Module for AI Assistant Knowledge Base
# This module documents comprehensive monitoring for Knowledge Base operations,
# custom metrics, dashboards, and alerting infrastructure

# SNS Topic for Alerts - ACTUAL DEPLOYED RESOURCE
# ARN: arn:aws:sns:us-west-2:254539707041:ai-assistant-alerts
resource "aws_sns_topic" "alerts" {
  name         = "ai-assistant-alerts"
  display_name = "AI Assistant Alerts"

  tags = {
    Name        = "ai-assistant-alerts"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# SNS Topic Subscription for Email Alerts
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = length(var.alert_email_addresses)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_addresses[count.index]
}

# CloudWatch Log Groups - ACTUAL DEPLOYED RESOURCES

# Custom Knowledge Base Metrics Log Group
resource "aws_cloudwatch_log_group" "knowledge_base_metrics" {
  name              = "/aws/ai-assistant/knowledge-base-metrics"
  retention_in_days = 30

  tags = {
    Name        = "ai-assistant-kb-metrics"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Admin Actions Audit Log Group
resource "aws_cloudwatch_log_group" "admin_audit" {
  name              = "/aws/ai-assistant/admin-audit"
  retention_in_days = 30

  tags = {
    Name        = "ai-assistant-admin-audit"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# API Gateway Log Group
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/ai-assistant"
  retention_in_days = 14

  tags = {
    Name        = "ai-assistant-api-gateway-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# CloudFront Log Group
resource "aws_cloudwatch_log_group" "cloudfront" {
  name              = "/aws/cloudfront/ai-assistant-dev"
  retention_in_days = 30

  tags = {
    Name        = "ai-assistant-cloudfront-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Lambda Function Log Groups
resource "aws_cloudwatch_log_group" "chat_lambda" {
  name              = "/aws/lambda/ai-assistant-chat-endpoints"
  retention_in_days = 14

  tags = {
    Name        = "ai-assistant-chat-lambda-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

resource "aws_cloudwatch_log_group" "admin_lambda" {
  name              = "/aws/lambda/ai-assistant-dev-admin-management"
  retention_in_days = 14

  tags = {
    Name        = "ai-assistant-admin-lambda-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

resource "aws_cloudwatch_log_group" "document_management_lambda" {
  name              = "/aws/lambda/ai-assistant-dev-document-management"
  retention_in_days = 14

  tags = {
    Name        = "ai-assistant-document-management-lambda-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

resource "aws_cloudwatch_log_group" "document_upload_lambda" {
  name              = "/aws/lambda/ai-assistant-dev-document-upload"
  retention_in_days = 14

  tags = {
    Name        = "ai-assistant-document-upload-lambda-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

resource "aws_cloudwatch_log_group" "kb_sync_monitor_lambda" {
  name              = "/aws/lambda/ai-assistant-dev-kb-sync-monitor"
  retention_in_days = 14

  tags = {
    Name        = "ai-assistant-kb-sync-monitor-lambda-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

resource "aws_cloudwatch_log_group" "monitoring_metrics_lambda" {
  name              = "/aws/lambda/ai-assistant-monitoring-metrics"
  retention_in_days = 30

  tags = {
    Name        = "ai-assistant-monitoring-metrics-lambda-logs"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# EventBridge Rules - ACTUAL DEPLOYED RESOURCES

# Knowledge Base Sync Monitor Schedule Rule
resource "aws_cloudwatch_event_rule" "kb_sync_monitor_schedule" {
  name                = "ai-assistant-dev-kb-sync-monitor-schedule"
  description         = "Trigger Knowledge Base sync monitoring every 5 minutes"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"

  tags = {
    Name        = "ai-assistant-kb-sync-monitor-schedule"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# EventBridge Target for KB Sync Monitor
resource "aws_cloudwatch_event_target" "kb_sync_monitor_target" {
  rule      = aws_cloudwatch_event_rule.kb_sync_monitor_schedule.name
  target_id = "KBSyncMonitorTarget"
  arn       = "arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-dev-kb-sync-monitor"
}

# Metrics Collection Schedule Rule
resource "aws_cloudwatch_event_rule" "metrics_collection" {
  name                = "ai-assistant-metrics-collection"
  description         = "Trigger metrics collection every 5 minutes"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"

  tags = {
    Name        = "ai-assistant-metrics-collection"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# EventBridge Target for Metrics Collection
resource "aws_cloudwatch_event_target" "metrics_collection_target" {
  rule      = aws_cloudwatch_event_rule.metrics_collection.name
  target_id = "MetricsCollectionTarget"
  arn       = "arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-monitoring-metrics"
}

# CloudWatch Dashboard for Knowledge Base Monitoring - ACTUAL DEPLOYED RESOURCES
resource "aws_cloudwatch_dashboard" "knowledge_base_dashboard" {
  dashboard_name = "ai-assistant-knowledge-base-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Bedrock", "InvocationLatency", "ModelId", "anthropic.claude-3-5-sonnet-20241022-v2:0"],
            [".", "InvocationThrottles", ".", "."],
            [".", "InvocationClientErrors", ".", "."],
            [".", "InvocationServerErrors", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "Bedrock Model Performance"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "ai-assistant-chat-endpoints"],
            [".", "Errors", ".", "."],
            [".", "Throttles", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "Chat Lambda Performance"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "ai-assistant-dev-document-management"],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "Document Management Lambda Performance"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "ai-assistant-dev-documents"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ThrottledRequests", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "DynamoDB Performance"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["AI-Assistant/KnowledgeBase", "QueryResponseTime"],
            [".", "QuerySuccessRate"],
            [".", "IngestionJobDuration"],
            [".", "DocumentProcessingErrors"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "Custom Knowledge Base Metrics"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AI-Assistant/KnowledgeBase", "IngestionJobsCompleted"],
            [".", "IngestionJobsFailed"],
            [".", "IngestionJobsInProgress"],
            [".", "IngestionJobSuccessRate"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "Knowledge Base Ingestion Jobs"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AI-Assistant/KnowledgeBase", "QueryResponseTime"],
            [".", "QueriesExecuted"],
            [".", "SourcesFoundPerQuery"],
            [".", "QuerySuccessRate"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "Query Performance Analytics"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 24
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/ai-assistant/admin-audit' | fields @timestamp, action, userId, details | sort @timestamp desc | limit 20"
          region  = "us-west-2"
          title   = "Recent Admin Actions"
          view    = "table"
        }
      }
    ]
  })
}

# CloudWatch Alarms for Knowledge Base Operations - ACTUAL DEPLOYED RESOURCES

# Alarm for High Bedrock Invocation Latency
resource "aws_cloudwatch_metric_alarm" "bedrock_high_latency" {
  alarm_name          = "ai-assistant-bedrock-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "InvocationLatency"
  namespace           = "AWS/Bedrock"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000" # 10 seconds in milliseconds
  alarm_description   = "This metric monitors Bedrock invocation latency"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ModelId = "anthropic.claude-3-5-sonnet-20241022-v2:0"
  }

  tags = {
    Name        = "ai-assistant-bedrock-latency-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Alarm for Bedrock Invocation Errors
resource "aws_cloudwatch_metric_alarm" "bedrock_errors" {
  alarm_name          = "ai-assistant-bedrock-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "InvocationServerErrors"
  namespace           = "AWS/Bedrock"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors Bedrock server errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ModelId = "anthropic.claude-3-5-sonnet-20241022-v2:0"
  }

  tags = {
    Name        = "ai-assistant-bedrock-errors-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Alarm for Chat Lambda Errors
resource "aws_cloudwatch_metric_alarm" "chat_lambda_errors" {
  alarm_name          = "ai-assistant-chat-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors chat lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = "ai-assistant-chat-endpoints"
  }

  tags = {
    Name        = "ai-assistant-chat-lambda-errors-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Alarm for Document Lambda Errors
resource "aws_cloudwatch_metric_alarm" "document_lambda_errors" {
  alarm_name          = "ai-assistant-document-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors document lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = "ai-assistant-dev-document-management"
  }

  tags = {
    Name        = "ai-assistant-document-lambda-errors-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Alarm for DynamoDB Throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  alarm_name          = "ai-assistant-dynamodb-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttling"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = "ai-assistant-dev-documents"
  }

  tags = {
    Name        = "ai-assistant-dynamodb-throttles-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Custom Metric Alarm for Knowledge Base Query Success Rate
resource "aws_cloudwatch_metric_alarm" "kb_query_success_rate" {
  alarm_name          = "ai-assistant-kb-query-success-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "QuerySuccessRate"
  namespace           = "AI-Assistant/KnowledgeBase"
  period              = "300"
  statistic           = "Average"
  threshold           = "90" # 90% success rate threshold
  alarm_description   = "This metric monitors Knowledge Base query success rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "ai-assistant-kb-success-rate-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Custom Metric Alarm for Knowledge Base Response Time
resource "aws_cloudwatch_metric_alarm" "kb_response_time" {
  alarm_name          = "ai-assistant-kb-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "QueryResponseTime"
  namespace           = "AI-Assistant/KnowledgeBase"
  period              = "300"
  statistic           = "Average"
  threshold           = "15000" # 15 seconds in milliseconds
  alarm_description   = "This metric monitors Knowledge Base query response time"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "ai-assistant-kb-response-time-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Knowledge Base Ingestion Failure Alarm
resource "aws_cloudwatch_metric_alarm" "kb_ingestion_failures" {
  alarm_name          = "ai-assistant-kb-ingestion-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "IngestionJobsFailed"
  namespace           = "AI-Assistant/KnowledgeBase"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors Knowledge Base ingestion job failures"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "ai-assistant-kb-ingestion-failures-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Knowledge Base Query Latency Alarm
resource "aws_cloudwatch_metric_alarm" "kb_query_latency" {
  alarm_name          = "ai-assistant-kb-query-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "QueryResponseTime"
  namespace           = "AI-Assistant/KnowledgeBase"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000" # 10 seconds in milliseconds
  alarm_description   = "This metric monitors Knowledge Base query latency for performance degradation"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "ai-assistant-kb-query-latency-alarm"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# Additional Deployed Alarms

# KB Sync Monitor Function Errors Alarm
resource "aws_cloudwatch_metric_alarm" "kb_monitor_function_errors" {
  alarm_name          = "ai-assistant-dev-kb-monitor-function-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors KB sync monitor lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "ai-assistant-dev-kb-sync-monitor"
  }

  tags = {
    Name        = "ai-assistant-dev-kb-monitor-function-errors"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# KB Ingestion Failure Rate Alarm (Alternative naming)
resource "aws_cloudwatch_metric_alarm" "kb_ingestion_failure_rate" {
  alarm_name          = "ai-assistant-dev-kb-ingestion-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "IngestionJobsFailed"
  namespace           = "AI-Assistant/KnowledgeBase"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors Knowledge Base ingestion failure rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "ai-assistant-dev-kb-ingestion-failure-rate"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# IAM Role for CloudWatch to publish to SNS - ACTUAL DEPLOYED RESOURCE
# ARN: arn:aws:iam::254539707041:role/ai-assistant-cloudwatch-sns-role
resource "aws_iam_role" "cloudwatch_sns_role" {
  name = "ai-assistant-cloudwatch-sns-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "ai-assistant-cloudwatch-sns-role"
    Environment = "dev"
    Project     = "ai-assistant"
  }
}

# IAM Policy for CloudWatch to publish to SNS
resource "aws_iam_role_policy" "cloudwatch_sns_policy" {
  name = "ai-assistant-cloudwatch-sns-policy"
  role = aws_iam_role.cloudwatch_sns_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}