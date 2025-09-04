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

# Chat Handler Lambda Function Terraform Configuration
# This documents the Lambda function for handling chat requests with RetrieveAndGenerate API
# ACTUAL DEPLOYED FUNCTION: ai-assistant-chat-endpoints (nodejs20.x)
# ACTUAL IAM ROLE: ai-assistant-lambda-chat-execution-role

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# Data source for current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Package the Lambda function code
data "archive_file" "chat_handler" {
  type        = "zip"
  output_path = "${path.module}/../function.zip"
  source_dir  = "${path.module}/../"
  depends_on  = [null_resource.build_lambda]
  
  excludes = [
    "src",
    "terraform",
    "tsconfig.json",
    "*.ts",
    "node_modules/@types",
    "node_modules/typescript",
    "node_modules/.bin",
    "*.md",
    ".git*"
  ]
}

# Build the Lambda function before packaging
resource "null_resource" "build_lambda" {
  triggers = {
    # Rebuild when source files change
    source_hash = filebase64sha256("${path.module}/../package.json")
    src_hash    = sha256(join("", [for f in fileset("${path.module}/../src", "**/*.ts") : filesha256("${path.module}/../src/${f}")]))
  }

  provisioner "local-exec" {
    command     = "npm ci && npm run build && npm ci --production"
    working_dir = "${path.module}/.."
  }
}

# IAM role for Lambda execution (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED ROLE: ai-assistant-lambda-chat-execution-role
resource "aws_iam_role" "chat_handler_role" {
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

  tags = {
    Environment = var.environment
    Application = "ai-assistant"
    Component   = "chat-handler"
  }
}

# CloudWatch Logs policy for Lambda (DOCUMENTATION ONLY)
resource "aws_iam_policy" "chat_handler_logging" {
  name        = "ai-assistant-lambda-chat-execution-role-logging"
  path        = "/"
  description = "IAM policy for logging from chat handler Lambda"

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
        Resource = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
      }
    ]
  })
}

# Data source for Bedrock policy document
data "aws_iam_policy_document" "chat_handler_bedrock" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      # Task 1: Claude 3.5 Haiku as primary model (reliable, cost-effective)
      "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
      # Task 1: Claude 3.5 Sonnet v2 as fallback (high quality, may have compatibility issues)
      "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
      # Additional fallback models
      "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
      "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0"
    ]
  }
  
  statement {
    effect = "Allow"
    actions = [
      "bedrock:RetrieveAndGenerate",
      "bedrock:Retrieve"
    ]
    resources = [
      "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
    ]
  }
}

# Bedrock permissions for Lambda (DOCUMENTATION ONLY)
resource "aws_iam_policy" "chat_handler_bedrock" {
  name        = "ai-assistant-lambda-chat-execution-role-bedrock"
  path        = "/"
  description = "IAM policy for Bedrock access from chat handler Lambda"
  policy      = data.aws_iam_policy_document.chat_handler_bedrock.json
}

# CloudWatch metrics permissions for Lambda (DOCUMENTATION ONLY)
resource "aws_iam_policy" "chat_handler_cloudwatch" {
  name        = "ai-assistant-lambda-chat-execution-role-cloudwatch"
  path        = "/"
  description = "IAM policy for CloudWatch metrics from chat handler Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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

# Attach policies to Lambda role
resource "aws_iam_role_policy_attachment" "chat_handler_logs" {
  role       = aws_iam_role.chat_handler_role.name
  policy_arn = aws_iam_policy.chat_handler_logging.arn
}

resource "aws_iam_role_policy_attachment" "chat_handler_bedrock" {
  role       = aws_iam_role.chat_handler_role.name
  policy_arn = aws_iam_policy.chat_handler_bedrock.arn
}

resource "aws_iam_role_policy_attachment" "chat_handler_cloudwatch" {
  role       = aws_iam_role.chat_handler_role.name
  policy_arn = aws_iam_policy.chat_handler_cloudwatch.arn
}

# CloudWatch Log Group for Lambda (DOCUMENTATION ONLY)
# ACTUAL LOG GROUP: /aws/lambda/ai-assistant-chat-endpoints (retention: 14 days)
resource "aws_cloudwatch_log_group" "chat_handler" {
  name              = "/aws/lambda/ai-assistant-chat-endpoints"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Application = "ai-assistant"
    Component   = "chat-handler"
  }
}

# Lambda function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-chat-endpoints
# RUNTIME: nodejs20.x
# ROLE: arn:aws:iam::254539707041:role/ai-assistant-lambda-chat-execution-role
resource "aws_lambda_function" "chat_handler" {
  filename         = data.archive_file.chat_handler.output_path
  function_name    = "ai-assistant-chat-endpoints"
  role             = aws_iam_role.chat_handler_role.arn
  handler          = "chat-endpoints.handler"
  source_code_hash = data.archive_file.chat_handler.output_base64sha256

  runtime     = "nodejs20.x"
  memory_size = 1024
  timeout     = 900  # 15 minutes - maximum allowed for Lambda

  environment {
    variables = {
      ENVIRONMENT         = var.environment
      KNOWLEDGE_BASE_ID   = var.knowledge_base_id
      DOCUMENTS_TABLE     = var.documents_table_name
      LOG_LEVEL           = var.log_level
      ENABLE_ADVANCED_RAG = var.enable_advanced_rag
      AWS_ACCOUNT_ID      = data.aws_caller_identity.current.account_id
      ALLOWED_ORIGINS     = var.cloudfront_url
    }
  }

  # Advanced logging configuration
  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "WARN"
    log_group             = aws_cloudwatch_log_group.chat_handler.name
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Application = "ai-assistant"
    Component   = "chat-handler"
  }

  # Ensure dependencies are ready
  depends_on = [
    aws_iam_role_policy_attachment.chat_handler_logs,
    aws_iam_role_policy_attachment.chat_handler_bedrock,
    aws_iam_role_policy_attachment.chat_handler_cloudwatch,
    aws_cloudwatch_log_group.chat_handler,
    data.archive_file.chat_handler
  ]
}