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

# API Gateway REST API for AI Assistant
# This module documents the deployed API Gateway with Cognito authorizer integration
# Actual API Gateway ID: jpt8wzkowd

# Data source for current AWS caller identity
data "aws_caller_identity" "current" {}

# API Gateway REST API - DEPLOYED CONFIGURATION
# Actual deployed API Gateway ID: jpt8wzkowd
# Name: ai-assistant-api
# Root Resource ID: 44jglfjt1l
resource "aws_api_gateway_rest_api" "ai_assistant" {
  name        = "ai-assistant-api"  # Actual deployed name
  description = "AI Assistant API Gateway with Cognito authentication"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  # CORS configuration - matches deployed settings
  binary_media_types = ["application/octet-stream", "image/*"]

  tags = {
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "AI-Assistant"
  }
}

# Cognito User Pool Authorizer - DEPLOYED CONFIGURATION
# Actual deployed authorizer ID: z8gap2
# Name: ai-assistant-cognito-authorizer
resource "aws_api_gateway_authorizer" "cognito_authorizer" {
  name                   = "ai-assistant-cognito-authorizer"  # Actual deployed name
  rest_api_id           = "jpt8wzkowd"  # Actual API Gateway ID
  type                  = "COGNITO_USER_POOLS"
  provider_arns         = ["arn:aws:cognito-idp:us-west-2:254539707041:userpool/us-west-2_FLJTm8Xt8"]  # Actual User Pool ARN
  identity_source       = "method.request.header.Authorization"
}

# API Gateway Resources - DEPLOYED CONFIGURATION
# Root Resource ID: 44jglfjt1l

# /chat resource - ID: 4ymylk
resource "aws_api_gateway_resource" "chat" {
  rest_api_id = "jpt8wzkowd"  # Actual API Gateway ID
  parent_id   = "44jglfjt1l"  # Actual root resource ID
  path_part   = "chat"
}

# /chat/ask resource - ID: drpsmy
resource "aws_api_gateway_resource" "chat_ask" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "4ymylk"  # chat resource ID
  path_part   = "ask"
}

# /chat/stream resource - ID: mummfa
resource "aws_api_gateway_resource" "chat_stream" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "4ymylk"  # chat resource ID
  path_part   = "stream"
}

# /chat/history resource - ID: 4r974g
resource "aws_api_gateway_resource" "chat_history" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "4ymylk"  # chat resource ID
  path_part   = "history"
}

# /chat/history/{conversationId} resource - ID: g6ezh6
resource "aws_api_gateway_resource" "chat_history_id" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "4r974g"  # chat/history resource ID
  path_part   = "{conversationId}"
}

# /documents resource - ID: w4weo7
resource "aws_api_gateway_resource" "documents" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "44jglfjt1l"  # root resource ID
  path_part   = "documents"
}

# /documents/status resource - ID: 1zvznt
resource "aws_api_gateway_resource" "documents_status" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "w4weo7"  # documents resource ID
  path_part   = "status"
}

# /documents/{id} resource - ID: 5ixqhj
resource "aws_api_gateway_resource" "documents_id" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "w4weo7"  # documents resource ID
  path_part   = "{id}"
}

# /upload resource - ID: 6ixqhj
resource "aws_api_gateway_resource" "upload" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "44jglfjt1l"  # root resource ID
  path_part   = "upload"
}

# /admin resource - ID: kkolty
resource "aws_api_gateway_resource" "admin" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "44jglfjt1l"  # root resource ID
  path_part   = "admin"
}

# /admin/{proxy+} resource - ID: ng6vfm
resource "aws_api_gateway_resource" "admin_proxy" {
  rest_api_id = "jpt8wzkowd"
  parent_id   = "kkolty"  # admin resource ID
  path_part   = "{proxy+}"
}

# CORS Configuration - DEPLOYED SETTINGS
# Current CloudFront domain: dq9tlzfsf1veq.cloudfront.net

# CORS Method for /chat - OPTIONS method
resource "aws_api_gateway_method" "chat_options" {
  rest_api_id   = "jpt8wzkowd"
  resource_id   = "4ymylk"  # chat resource ID
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# CORS Integration for /chat
resource "aws_api_gateway_integration" "chat_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "4ymylk"  # chat resource ID
  http_method = "OPTIONS"
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# CORS Method Response for /chat
resource "aws_api_gateway_method_response" "chat_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "4ymylk"  # chat resource ID
  http_method = "OPTIONS"
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# CORS Integration Response for /chat
resource "aws_api_gateway_integration_response" "chat_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "4ymylk"  # chat resource ID
  http_method = "OPTIONS"
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'https://dq9tlzfsf1veq.cloudfront.net'"  # Actual CloudFront domain
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}

# CORS setup for /documents
resource "aws_api_gateway_method" "documents_options" {
  rest_api_id   = "jpt8wzkowd"
  resource_id   = "w4weo7"  # documents resource ID
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "documents_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "w4weo7"  # documents resource ID
  http_method = "OPTIONS"
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "documents_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "w4weo7"  # documents resource ID
  http_method = "OPTIONS"
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "documents_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "w4weo7"  # documents resource ID
  http_method = "OPTIONS"
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"  # Updated to match deployed methods
    "method.response.header.Access-Control-Allow-Origin"  = "'https://dq9tlzfsf1veq.cloudfront.net'"  # Actual CloudFront domain
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}

# CORS setup for /upload
resource "aws_api_gateway_method" "upload_options" {
  rest_api_id   = "jpt8wzkowd"
  resource_id   = "6ixqhj"  # upload resource ID
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "upload_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "6ixqhj"  # upload resource ID
  http_method = "OPTIONS"
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "upload_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "6ixqhj"  # upload resource ID
  http_method = "OPTIONS"
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "upload_options" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "6ixqhj"  # upload resource ID
  http_method = "OPTIONS"
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'https://dq9tlzfsf1veq.cloudfront.net'"  # Actual CloudFront domain
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}

# Admin CORS is handled by the admin Lambda module

# Lambda Integrations - DEPLOYED CONFIGURATION
# These integrations connect API Gateway methods to actual Lambda functions

# Chat endpoints integration - ai-assistant-chat-endpoints
resource "aws_api_gateway_integration" "chat_ask_lambda" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "drpsmy"  # /chat/ask resource ID
  http_method = "POST"
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-chat-endpoints/invocations"
}

resource "aws_api_gateway_integration" "chat_stream_lambda" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "mummfa"  # /chat/stream resource ID
  http_method = "POST"
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-chat-endpoints/invocations"
}

# Document management integration - ai-assistant-dev-document-management
resource "aws_api_gateway_integration" "documents_lambda" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "w4weo7"  # /documents resource ID
  http_method = "GET"
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-dev-document-management/invocations"
}

# Document upload integration - ai-assistant-dev-document-upload
resource "aws_api_gateway_integration" "upload_lambda" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "6ixqhj"  # /upload resource ID
  http_method = "POST"
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-dev-document-upload/invocations"
}

# Admin management integration - ai-assistant-dev-admin-management
resource "aws_api_gateway_integration" "admin_lambda" {
  rest_api_id = "jpt8wzkowd"
  resource_id = "ng6vfm"  # /admin/{proxy+} resource ID
  http_method = "ANY"
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:254539707041:function:ai-assistant-dev-admin-management/invocations"
}

# API Gateway Deployment - DEPLOYED CONFIGURATION
resource "aws_api_gateway_deployment" "ai_assistant" {
  rest_api_id = "jpt8wzkowd"  # Actual API Gateway ID
  stage_name  = "dev"         # Actual deployed stage

  # Note: In actual deployment, this would reference all methods and integrations
  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage - DEPLOYED CONFIGURATION
# Actual stage name: dev
# Invoke URL: https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev
resource "aws_api_gateway_stage" "ai_assistant" {
  deployment_id = "deployment-id"  # Placeholder - actual deployment managed via AWS CLI
  rest_api_id   = "jpt8wzkowd"     # Actual API Gateway ID
  stage_name    = "dev"            # Actual stage name

  # Enable CloudWatch logging - matches deployed configuration
  access_log_settings {
    destination_arn = "arn:aws:logs:us-west-2:254539707041:log-group:/aws/apigateway/ai-assistant"
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  # Enable X-Ray tracing
  xray_tracing_enabled = true

  tags = {
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "AI-Assistant"
  }
}

# Request Validator for input validation - DEPLOYED CONFIGURATION
resource "aws_api_gateway_request_validator" "ai_assistant" {
  name                        = "ai-assistant-request-validator"  # Actual deployed name
  rest_api_id                = "jpt8wzkowd"                      # Actual API Gateway ID
  validate_request_body       = true
  validate_request_parameters = true
}

# CloudWatch Log Group for API Gateway - DEPLOYED CONFIGURATION
# Actual log group: /aws/apigateway/ai-assistant
# Retention: 14 days
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/ai-assistant"  # Actual log group name
  retention_in_days = 14  # Actual retention setting

  tags = {
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "AI-Assistant"
  }
}

# API Gateway Account (for CloudWatch logging) - DEPLOYED CONFIGURATION
resource "aws_api_gateway_account" "ai_assistant" {
  cloudwatch_role_arn = "arn:aws:iam::254539707041:role/ai-assistant-api-gateway-cloudwatch-role"  # Actual role ARN
}

# IAM Role for API Gateway CloudWatch logging - DEPLOYED CONFIGURATION
# Actual role: ai-assistant-api-gateway-cloudwatch-role
resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "ai-assistant-api-gateway-cloudwatch-role"  # Actual deployed role name

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

  tags = {
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "AI-Assistant"
  }
}

# IAM Policy Attachment for API Gateway CloudWatch logging - DEPLOYED CONFIGURATION
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = "ai-assistant-api-gateway-cloudwatch-role"  # Actual role name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}