/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS infrastructure deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# Knowledge Base Sync Monitor Lambda Function Terraform Module (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-kb-sync-monitor (nodejs18.x)
# ACTUAL IAM ROLE: ai-assistant-lambda-kb-monitor-execution-role

# Build the Lambda function
resource "null_resource" "build_function" {
  provisioner "local-exec" {
    command = "cd ${path.module}/.. && npm install && npm run build && npm run package"
  }

  triggers = {
    source_hash = filebase64sha256("${path.module}/../src/index.ts")
    package_hash = filebase64sha256("${path.module}/../package.json")
  }
}

# Lambda function for Knowledge Base sync monitoring (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-kb-sync-monitor
# ACTUAL ROLE: arn:aws:iam::254539707041:role/ai-assistant-lambda-kb-monitor-execution-role
resource "aws_lambda_function" "kb_sync_monitor" {
  filename         = "${path.module}/../function.zip"
  function_name    = "ai-assistant-dev-kb-sync-monitor"
  role            = "arn:aws:iam::254539707041:role/ai-assistant-lambda-kb-monitor-execution-role"
  handler         = "dist/index.handler"
  runtime         = "nodejs18.x"
  timeout         = 300 # 5 minutes
  memory_size     = 512

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = var.knowledge_base_id
      DATA_SOURCE_ID    = var.data_source_id
      DOCUMENTS_TABLE   = var.documents_table_name
    }
  }

  depends_on = [null_resource.build_function]

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-kb-sync-monitor"
    Purpose     = "Knowledge Base Synchronization Monitoring"
    Environment = var.environment
  })
}

# CloudWatch Log Group for the Lambda function (DOCUMENTATION ONLY)
# ACTUAL LOG GROUP: /aws/lambda/ai-assistant-dev-kb-sync-monitor (retention: 14 days)
resource "aws_cloudwatch_log_group" "kb_sync_monitor_logs" {
  name              = "/aws/lambda/ai-assistant-dev-kb-sync-monitor"
  retention_in_days = 14

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-kb-sync-monitor-logs"
  })
}

# EventBridge rule to trigger the monitoring function every 5 minutes (DOCUMENTATION ONLY)
# ACTUAL RULE: ai-assistant-dev-kb-sync-monitor-schedule (rate(5 minutes))
resource "aws_cloudwatch_event_rule" "kb_sync_monitor_schedule" {
  name                = "ai-assistant-dev-kb-sync-monitor-schedule"
  description         = "Trigger Knowledge Base sync monitoring every 5 minutes"
  schedule_expression = "rate(5 minutes)"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-kb-sync-monitor-schedule"
  })
}

# EventBridge target to invoke the Lambda function
resource "aws_cloudwatch_event_target" "kb_sync_monitor_target" {
  rule      = aws_cloudwatch_event_rule.kb_sync_monitor_schedule.name
  target_id = "KBSyncMonitorTarget"
  arn       = aws_lambda_function.kb_sync_monitor.arn
}

# Permission for EventBridge to invoke the Lambda function
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kb_sync_monitor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.kb_sync_monitor_schedule.arn
}

# CloudWatch Dashboard for Knowledge Base monitoring
resource "aws_cloudwatch_dashboard" "kb_monitoring" {
  dashboard_name = "${var.project_name}-${var.environment}-knowledge-base-monitoring"

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
            ["AI-Assistant/KnowledgeBase", "IngestionJobsCompleted"],
            [".", "IngestionJobsFailed"],
            [".", "IngestionJobsInProgress"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Knowledge Base Ingestion Jobs"
          period  = 300
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
            ["AI-Assistant/KnowledgeBase", "IngestionSuccessRate"]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Ingestion Success Rate"
          period = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
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
            ["AI-Assistant/KnowledgeBase", "DocumentsUpdated"]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Documents Updated"
          period = 300
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
            ["AI-Assistant/KnowledgeBase", "IngestionJobDuration"]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Ingestion Job Duration (seconds)"
          period = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${aws_lambda_function.kb_sync_monitor.function_name}'\n| fields @timestamp, @message\n| filter @message like /Knowledge Base sync monitoring/\n| sort @timestamp desc\n| limit 100"
          region  = var.aws_region
          title   = "Recent Monitoring Activity"
        }
      }
    ]
  })


}

# CloudWatch Alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "ingestion_failure_rate" {
  alarm_name          = "${var.project_name}-${var.environment}-kb-ingestion-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "IngestionJobsFailed"
  namespace           = "AI-Assistant/KnowledgeBase"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "This metric monitors Knowledge Base ingestion job failures"
  alarm_actions       = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-kb-ingestion-failure-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "monitoring_function_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-kb-monitor-function-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors Knowledge Base monitoring function errors"
  alarm_actions       = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.kb_sync_monitor.function_name
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-kb-monitor-function-errors"
  })
}