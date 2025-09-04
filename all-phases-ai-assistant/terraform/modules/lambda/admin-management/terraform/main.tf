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

# Admin Management Lambda Function Terraform Configuration (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-admin-management (nodejs18.x)
# ACTUAL IAM ROLE: ai-assistant-lambda-admin-execution-role

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Create deployment package for Lambda function
resource "null_resource" "build_lambda" {
  triggers = {
    # Rebuild when source files change
    source_hash = filebase64sha256("${path.module}/../src/index.ts")
    package_hash = filebase64sha256("${path.module}/../package.json")
  }

  provisioner "local-exec" {
    command = <<-EOT
      cd ${path.module}/..
      npm ci --production
      npm run build
      zip -r function.zip dist/ node_modules/ package.json
    EOT
  }
}

# Lambda function for admin management (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-admin-management
# ACTUAL ROLE: arn:aws:iam::254539707041:role/ai-assistant-lambda-admin-execution-role
resource "aws_lambda_function" "admin_management" {
  filename         = "${path.module}/../function.zip"
  function_name    = "ai-assistant-dev-admin-management"
  role            = "arn:aws:iam::254539707041:role/ai-assistant-lambda-admin-execution-role"
  handler         = "dist/index.handler"
  runtime         = "nodejs18.x"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      KNOWLEDGE_BASE_ID    = var.knowledge_base_id
      DATA_SOURCE_ID       = var.data_source_id
      DOCUMENTS_TABLE      = var.documents_table_name
      LOG_LEVEL           = var.log_level
      AUDIT_LOG_GROUP      = var.audit_log_group_name
      METRICS_LOG_GROUP    = var.metrics_log_group_name
    }
  }

  depends_on = [null_resource.build_lambda]

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-admin-management"
    Function    = "Admin Management"
    Environment = var.environment
  })
}

# CloudWatch Log Group for Lambda function (DOCUMENTATION ONLY)
# ACTUAL LOG GROUP: /aws/lambda/ai-assistant-dev-admin-management (retention: 14 days)
resource "aws_cloudwatch_log_group" "admin_management_logs" {
  name              = "/aws/lambda/ai-assistant-dev-admin-management"
  retention_in_days = 14

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-admin-management-logs"
  })
}

# API Gateway resource for admin endpoints
resource "aws_api_gateway_resource" "admin" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "admin"
}

# API Gateway resource for admin proxy (catch-all)
resource "aws_api_gateway_resource" "admin_proxy" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.admin.id
  path_part   = "{proxy+}"
}

# API Gateway method for admin GET requests
resource "aws_api_gateway_method" "admin_get" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.admin_proxy.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.path.proxy" = true
  }
}

# API Gateway method for admin POST requests
resource "aws_api_gateway_method" "admin_post" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.admin_proxy.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.path.proxy" = true
  }
}

# API Gateway method for admin OPTIONS (CORS)
resource "aws_api_gateway_method" "admin_options" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.admin_proxy.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway integration for admin GET requests
resource "aws_api_gateway_integration" "admin_get_integration" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.admin_management.invoke_arn

  request_parameters = {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }
}

# API Gateway integration for admin POST requests
resource "aws_api_gateway_integration" "admin_post_integration" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.admin_management.invoke_arn

  request_parameters = {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }
}

# API Gateway integration for admin OPTIONS (CORS)
resource "aws_api_gateway_integration" "admin_options_integration" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_options.http_method

  type = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# API Gateway method response for admin GET
resource "aws_api_gateway_method_response" "admin_get_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway method response for admin POST
resource "aws_api_gateway_method_response" "admin_post_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway method response for admin OPTIONS
resource "aws_api_gateway_method_response" "admin_options_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# API Gateway integration response for admin GET
resource "aws_api_gateway_integration_response" "admin_get_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_get.http_method
  status_code = aws_api_gateway_method_response.admin_get_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

# API Gateway integration response for admin POST
resource "aws_api_gateway_integration_response" "admin_post_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_post.http_method
  status_code = aws_api_gateway_method_response.admin_post_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

# API Gateway integration response for admin OPTIONS
resource "aws_api_gateway_integration_response" "admin_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.admin_proxy.id
  http_method = aws_api_gateway_method.admin_options.http_method
  status_code = aws_api_gateway_method_response.admin_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda permission for API Gateway to invoke admin function
resource "aws_lambda_permission" "admin_api_gateway_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway-${var.project_name}-admin-management"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.admin_management.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}