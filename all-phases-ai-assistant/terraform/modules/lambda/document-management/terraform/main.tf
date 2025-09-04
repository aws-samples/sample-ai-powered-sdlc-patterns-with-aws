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

# Document Management Lambda Function Terraform Module (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-document-management (nodejs20.x)
# ACTUAL IAM ROLE: ai-assistant-lambda-document-execution-role

# Data source for current AWS caller identity
data "aws_caller_identity" "current" {}

# Archive the Lambda function code
data "archive_file" "document_management_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../dist"
  output_path = "${path.module}/../function.zip"
  
  depends_on = [null_resource.build_lambda]
}

# Build the Lambda function
resource "null_resource" "build_lambda" {
  provisioner "local-exec" {
    command = "cd ${path.module}/.. && npm install && npm run build"
  }

  triggers = {
    source_hash = filebase64sha256("${path.module}/../src/index.ts")
    package_hash = filebase64sha256("${path.module}/../package.json")
  }
}

# Lambda function for document management (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-document-management
# ACTUAL ROLE: arn:aws:iam::254539707041:role/ai-assistant-lambda-document-execution-role
resource "aws_lambda_function" "document_management" {
  filename         = data.archive_file.document_management_lambda.output_path
  function_name    = "ai-assistant-dev-document-management"
  role            = "arn:aws:iam::254539707041:role/ai-assistant-lambda-document-execution-role"
  handler         = "index.handler"
  runtime         = "nodejs20.x"
  timeout         = 30
  memory_size     = 512

  source_code_hash = data.archive_file.document_management_lambda.output_base64sha256

  environment {
    variables = {
      DOCUMENTS_BUCKET     = var.documents_bucket_name
      DOCUMENTS_TABLE      = var.documents_table_name
      KNOWLEDGE_BASE_ID    = var.knowledge_base_id
      DATA_SOURCE_ID       = var.data_source_id
    }
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-document-management"
    Purpose     = "Document Management API"
    Environment = var.environment
  })

  depends_on = [
    null_resource.build_lambda,
    data.archive_file.document_management_lambda
  ]
}

# CloudWatch Log Group for Lambda function (DOCUMENTATION ONLY)
# ACTUAL LOG GROUP: /aws/lambda/ai-assistant-dev-document-management (retention: 14 days)
resource "aws_cloudwatch_log_group" "document_management_logs" {
  name              = "/aws/lambda/ai-assistant-dev-document-management"
  retention_in_days = 14

  tags = var.tags
}

# API Gateway Method: GET /documents
resource "aws_api_gateway_method" "get_documents" {
  rest_api_id   = var.api_gateway_id
  resource_id   = var.api_gateway_documents_resource_id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.header.Authorization" = true
  }
}

# API Gateway Integration: GET /documents
resource "aws_api_gateway_integration" "get_documents" {
  rest_api_id = var.api_gateway_id
  resource_id = var.api_gateway_documents_resource_id
  http_method = aws_api_gateway_method.get_documents.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.document_management.invoke_arn
}

# API Gateway Method Response: GET /documents
resource "aws_api_gateway_method_response" "get_documents" {
  rest_api_id = var.api_gateway_id
  resource_id = var.api_gateway_documents_resource_id
  http_method = aws_api_gateway_method.get_documents.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway Integration Response: GET /documents
resource "aws_api_gateway_integration_response" "get_documents" {
  rest_api_id = var.api_gateway_id
  resource_id = var.api_gateway_documents_resource_id
  http_method = aws_api_gateway_method.get_documents.http_method
  status_code = aws_api_gateway_method_response.get_documents.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.get_documents]
}

# API Gateway Resource for /documents/{id}
resource "aws_api_gateway_resource" "documents_id" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_documents_resource_id
  path_part   = "{id}"
}

# API Gateway Method: DELETE /documents/{id}
resource "aws_api_gateway_method" "delete_document" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.documents_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.header.Authorization" = true
    "method.request.path.id" = true
  }
}

# API Gateway Integration: DELETE /documents/{id}
resource "aws_api_gateway_integration" "delete_document" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.delete_document.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.document_management.invoke_arn
}

# API Gateway Method Response: DELETE /documents/{id}
resource "aws_api_gateway_method_response" "delete_document" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.delete_document.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway Integration Response: DELETE /documents/{id}
resource "aws_api_gateway_integration_response" "delete_document" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.delete_document.http_method
  status_code = aws_api_gateway_method_response.delete_document.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.delete_document]
}

# API Gateway Resource for /documents/status
resource "aws_api_gateway_resource" "documents_status" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_documents_resource_id
  path_part   = "status"
}

# API Gateway Method: GET /documents/status
resource "aws_api_gateway_method" "get_documents_status" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.documents_status.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.header.Authorization" = true
  }
}

# API Gateway Integration: GET /documents/status
resource "aws_api_gateway_integration" "get_documents_status" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_status.id
  http_method = aws_api_gateway_method.get_documents_status.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.document_management.invoke_arn
}

# API Gateway Method Response: GET /documents/status
resource "aws_api_gateway_method_response" "get_documents_status" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_status.id
  http_method = aws_api_gateway_method.get_documents_status.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway Integration Response: GET /documents/status
resource "aws_api_gateway_integration_response" "get_documents_status" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_status.id
  http_method = aws_api_gateway_method.get_documents_status.http_method
  status_code = aws_api_gateway_method_response.get_documents_status.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.get_documents_status]
}

# CORS Method for /documents/{id}
resource "aws_api_gateway_method" "documents_id_options" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.documents_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# CORS Integration for /documents/{id}
resource "aws_api_gateway_integration" "documents_id_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_id_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# CORS Method Response for /documents/{id}
resource "aws_api_gateway_method_response" "documents_id_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_id_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# CORS Integration Response for /documents/{id}
resource "aws_api_gateway_integration_response" "documents_id_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_id_options.http_method
  status_code = aws_api_gateway_method_response.documents_id_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS Method for /documents/status
resource "aws_api_gateway_method" "documents_status_options" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.documents_status.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# CORS Integration for /documents/status
resource "aws_api_gateway_integration" "documents_status_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_status.id
  http_method = aws_api_gateway_method.documents_status_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# CORS Method Response for /documents/status
resource "aws_api_gateway_method_response" "documents_status_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_status.id
  http_method = aws_api_gateway_method.documents_status_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# CORS Integration Response for /documents/status
resource "aws_api_gateway_integration_response" "documents_status_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.documents_status.id
  http_method = aws_api_gateway_method.documents_status_options.http_method
  status_code = aws_api_gateway_method_response.documents_status_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda permission for API Gateway to invoke the function
resource "aws_lambda_permission" "api_gateway_invoke_document_management" {
  statement_id  = "AllowExecutionFromAPIGateway-${var.project_name}-document-management"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_management.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}