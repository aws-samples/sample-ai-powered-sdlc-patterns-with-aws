/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS IAM roles deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# IAM roles and policies for AI Assistant - DOCUMENTATION ONLY
# This module documents the current IAM roles deployed in AWS

# Data source for current AWS caller identity
data "aws_caller_identity" "current" {}

# ============================================================================
# LAMBDA EXECUTION ROLES - Documentation of actual deployed roles
# ============================================================================

# Lambda execution role for chat functions
# Actual deployed role: ai-assistant-lambda-chat-execution-role
resource "aws_iam_role" "lambda_chat_execution" {
  name = "ai-assistant-lambda-chat-execution-role"

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

  tags = var.tags
}

# Lambda execution role for document management functions
# Actual deployed role: ai-assistant-lambda-document-execution-role
resource "aws_iam_role" "lambda_document_execution" {
  name = "ai-assistant-lambda-document-execution-role"

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

  tags = var.tags
}

# Lambda execution role for admin functions
# Actual deployed role: ai-assistant-lambda-admin-execution-role
resource "aws_iam_role" "lambda_admin_execution" {
  name = "ai-assistant-lambda-admin-execution-role"

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

  tags = var.tags
}

# Lambda execution role for Knowledge Base sync monitor
# Actual deployed role: ai-assistant-lambda-kb-monitor-execution-role
resource "aws_iam_role" "lambda_kb_monitor_execution" {
  name = "ai-assistant-lambda-kb-monitor-execution-role"

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

  tags = var.tags
}

# Additional Lambda execution role for chat handler (separate from chat execution)
# Actual deployed role: ai-assistant-chat-handler-role
resource "aws_iam_role" "chat_handler_role" {
  name = "ai-assistant-chat-handler-role"

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

  tags = var.tags
}

# ============================================================================
# SERVICE ROLES - Documentation of actual deployed service roles
# ============================================================================

# API Gateway CloudWatch role for logging
# Actual deployed role: ai-assistant-api-gateway-cloudwatch-role
resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "ai-assistant-api-gateway-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Bedrock Knowledge Base service role
# Actual deployed role: ai-assistant-dev-bedrock-kb-role
resource "aws_iam_role" "bedrock_kb_service" {
  name = "ai-assistant-dev-bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# ============================================================================
# MONITORING ROLES - Documentation of actual deployed monitoring roles
# ============================================================================

# Monitoring metrics role for CloudWatch metrics collection
# Actual deployed role: ai-assistant-monitoring-metrics-role
resource "aws_iam_role" "monitoring_metrics" {
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

  tags = var.tags
}

# CloudWatch SNS role for notifications
# Actual deployed role: ai-assistant-cloudwatch-sns-role
resource "aws_iam_role" "cloudwatch_sns" {
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

  tags = var.tags
}

# ============================================================================
# POLICY ATTACHMENTS - Documentation of actual deployed policy attachments
# ============================================================================

# Basic Lambda execution policy attachment for chat role
resource "aws_iam_role_policy_attachment" "lambda_chat_basic_execution" {
  role       = aws_iam_role.lambda_chat_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy attachment for document role
resource "aws_iam_role_policy_attachment" "lambda_document_basic_execution" {
  role       = aws_iam_role.lambda_document_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy attachment for admin role
resource "aws_iam_role_policy_attachment" "lambda_admin_basic_execution" {
  role       = aws_iam_role.lambda_admin_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy attachment for KB monitor role
resource "aws_iam_role_policy_attachment" "lambda_kb_monitor_basic_execution" {
  role       = aws_iam_role.lambda_kb_monitor_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy attachment for chat handler role
resource "aws_iam_role_policy_attachment" "chat_handler_basic_execution" {
  role       = aws_iam_role.chat_handler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy attachment for monitoring metrics role
resource "aws_iam_role_policy_attachment" "monitoring_metrics_basic_execution" {
  role       = aws_iam_role.monitoring_metrics.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# API Gateway CloudWatch policy attachment
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch_logs" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# ============================================================================
# INLINE POLICIES - Documentation of actual deployed inline policies
# ============================================================================

# Bedrock Knowledge Base policy for chat functions
resource "aws_iam_role_policy" "lambda_chat_bedrock_kb" {
  name = "ai-assistant-lambda-chat-bedrock-kb-policy"
  role = aws_iam_role.lambda_chat_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:RetrieveAndGenerate",
          "bedrock:Retrieve"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListKnowledgeBases",
          "bedrock:GetKnowledgeBase"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# S3 and DynamoDB policy for document management functions
resource "aws_iam_role_policy" "lambda_document_storage" {
  name = "ai-assistant-lambda-document-storage-policy"
  role = aws_iam_role.lambda_document_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.documents_bucket_arn,
          "${var.documents_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.documents_table_arn,
          "${var.documents_table_arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:StartIngestionJob",
          "bedrock:GetIngestionJob",
          "bedrock:ListIngestionJobs",
          "bedrock:GetDataSource"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
        ]
      }
    ]
  })
}

# Admin policy for Knowledge Base management
resource "aws_iam_role_policy" "lambda_admin_bedrock_kb" {
  name = "ai-assistant-lambda-admin-bedrock-kb-policy"
  role = aws_iam_role.lambda_admin_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agent:GetKnowledgeBase",
          "bedrock-agent:ListKnowledgeBases",
          "bedrock-agent:GetDataSource",
          "bedrock-agent:ListDataSources",
          "bedrock-agent:ListIngestionJobs",
          "bedrock-agent:GetIngestionJob",
          "bedrock-agent:StartIngestionJob",
          "bedrock-agent:StopIngestionJob",
          "bedrock:GetKnowledgeBase",
          "bedrock:ListKnowledgeBases",
          "bedrock:GetDataSource",
          "bedrock:ListDataSources",
          "bedrock:ListIngestionJobs",
          "bedrock:GetIngestionJob",
          "bedrock:StartIngestionJob",
          "bedrock:StopIngestionJob",
          "bedrock:RetrieveAndGenerate",
          "bedrock:Retrieve",
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.documents_bucket_arn,
          "${var.documents_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.documents_table_arn,
          "${var.documents_table_arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Logs policy for chat Lambda function
resource "aws_iam_role_policy" "lambda_cloudwatch_logs" {
  name = "ai-assistant-lambda-cloudwatch-logs-policy"
  role = aws_iam_role.lambda_chat_execution.id

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
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# CloudWatch Logs policy for document Lambda function
resource "aws_iam_role_policy" "lambda_document_cloudwatch_logs" {
  name = "ai-assistant-lambda-document-cloudwatch-logs-policy"
  role = aws_iam_role.lambda_document_execution.id

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
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# CloudWatch Logs policy for admin Lambda function
resource "aws_iam_role_policy" "lambda_admin_cloudwatch_logs" {
  name = "ai-assistant-lambda-admin-cloudwatch-logs-policy"
  role = aws_iam_role.lambda_admin_execution.id

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
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# Knowledge Base monitoring policy for sync monitor function
resource "aws_iam_role_policy" "lambda_kb_monitor_bedrock" {
  name = "ai-assistant-lambda-kb-monitor-bedrock-policy"
  role = aws_iam_role.lambda_kb_monitor_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListIngestionJobs",
          "bedrock:GetIngestionJob",
          "bedrock:StartIngestionJob",
          "bedrock:GetDataSource",
          "bedrock:GetKnowledgeBase"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.documents_table_arn,
          "${var.documents_table_arn}/index/*"
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
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}
# ============================================================================
# ADDITIONAL ROLE POLICIES - Documentation of policies for additional roles
# ============================================================================

# Chat handler role Bedrock policy
resource "aws_iam_role_policy" "chat_handler_bedrock" {
  name = "ai-assistant-chat-handler-bedrock-policy"
  role = aws_iam_role.chat_handler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:RetrieveAndGenerate",
          "bedrock:Retrieve"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# Bedrock Knowledge Base service role policy
resource "aws_iam_role_policy" "bedrock_kb_service_policy" {
  name = "ai-assistant-bedrock-kb-service-policy"
  role = aws_iam_role.bedrock_kb_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.documents_bucket_arn,
          "${var.documents_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      }
    ]
  })
}

# Monitoring metrics role policy
resource "aws_iam_role_policy" "monitoring_metrics_policy" {
  name = "ai-assistant-monitoring-metrics-policy"
  role = aws_iam_role.monitoring_metrics.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# CloudWatch SNS role policy
resource "aws_iam_role_policy" "cloudwatch_sns_policy" {
  name = "ai-assistant-cloudwatch-sns-policy"
  role = aws_iam_role.cloudwatch_sns.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "arn:aws:sns:${var.aws_region}:${data.aws_caller_identity.current.account_id}:ai-assistant-alerts"
      }
    ]
  })
}