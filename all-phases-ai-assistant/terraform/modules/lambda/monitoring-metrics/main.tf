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

# Lambda Function for Custom Metrics Collection and Audit Logging (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-monitoring-metrics (nodejs18.x)
# ACTUAL IAM ROLE: ai-assistant-monitoring-metrics-role

# Lambda function for metrics collection (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-monitoring-metrics
# ACTUAL ROLE: arn:aws:iam::254539707041:role/ai-assistant-monitoring-metrics-role
resource "aws_lambda_function" "monitoring_metrics" {
  filename         = "${path.module}/monitoring-metrics.zip"
  function_name    = "ai-assistant-monitoring-metrics"
  role            = "arn:aws:iam::254539707041:role/ai-assistant-monitoring-metrics-role"
  handler         = "index.handler"
  runtime         = "nodejs18.x"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = var.knowledge_base_id
      METRICS_LOG_GROUP = var.metrics_log_group_name
      AUDIT_LOG_GROUP   = var.audit_log_group_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.monitoring_metrics_policy,
    aws_cloudwatch_log_group.monitoring_metrics_logs,
    data.archive_file.monitoring_metrics_zip
  ]

  tags = {
    Name        = "${var.project_name}-monitoring-metrics"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for the monitoring Lambda (DOCUMENTATION ONLY)
# ACTUAL LOG GROUP: /aws/lambda/ai-assistant-monitoring-metrics (retention: 30 days)
resource "aws_cloudwatch_log_group" "monitoring_metrics_logs" {
  name              = "/aws/lambda/ai-assistant-monitoring-metrics"
  retention_in_days = 30

  tags = {
    Name        = "${var.project_name}-monitoring-metrics-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Role for the monitoring Lambda (DOCUMENTATION ONLY)
# ACTUAL ROLE: ai-assistant-monitoring-metrics-role
resource "aws_iam_role" "monitoring_metrics_role" {
  name = "ai-assistant-monitoring-metrics-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-monitoring-metrics-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for the monitoring Lambda
resource "aws_iam_role_policy" "monitoring_metrics_policy" {
  name = "${var.project_name}-monitoring-metrics-policy"
  role = aws_iam_role.monitoring_metrics_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-monitoring-metrics*",
          "arn:aws:logs:${var.aws_region}:*:log-group:${var.metrics_log_group_name}*",
          "arn:aws:logs:${var.aws_region}:*:log-group:${var.audit_log_group_name}*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListIngestionJobs",
          "bedrock:GetIngestionJob",
          "bedrock:ListDataSources",
          "bedrock:GetKnowledgeBase",
          "bedrock:DescribeKnowledgeBase"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:*:knowledge-base/${var.knowledge_base_id}",
          "arn:aws:bedrock:${var.aws_region}:*:knowledge-base/${var.knowledge_base_id}/*"
        ]
      }
    ]
  })
}

# Attach basic execution policy
resource "aws_iam_role_policy_attachment" "monitoring_metrics_policy" {
  role       = aws_iam_role.monitoring_metrics_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# EventBridge rule to trigger metrics collection every 5 minutes (DOCUMENTATION ONLY)
# ACTUAL RULE: ai-assistant-metrics-collection (rate(5 minutes))
resource "aws_cloudwatch_event_rule" "metrics_collection_schedule" {
  name                = "ai-assistant-metrics-collection"
  description         = "Trigger metrics collection every 5 minutes"
  schedule_expression = "rate(5 minutes)"

  tags = {
    Name        = "${var.project_name}-metrics-collection"
    Environment = var.environment
    Project     = var.project_name
  }
}

# EventBridge target for the metrics Lambda
resource "aws_cloudwatch_event_target" "metrics_collection_target" {
  rule      = aws_cloudwatch_event_rule.metrics_collection_schedule.name
  target_id = "MetricsCollectionTarget"
  arn       = aws_lambda_function.monitoring_metrics.arn
}

# Permission for EventBridge to invoke the Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.monitoring_metrics.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.metrics_collection_schedule.arn
}

# Create the Lambda deployment package
data "archive_file" "monitoring_metrics_zip" {
  type        = "zip"
  output_path = "${path.module}/monitoring-metrics.zip"
  source {
    content  = file("${path.module}/index.js")
    filename = "index.js"
  }
  source {
    content  = file("${path.module}/package.json")
    filename = "package.json"
  }
}