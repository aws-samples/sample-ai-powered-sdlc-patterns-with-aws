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

# Document Upload Lambda Function Terraform Configuration (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-document-upload (nodejs18.x)
# ACTUAL IAM ROLE: ai-assistant-lambda-document-execution-role

# Create a proper Lambda package structure
resource "null_resource" "create_lambda_package" {
  depends_on = [null_resource.build_lambda]
  
  provisioner "local-exec" {
    command = <<-EOT
      cd ${path.module}/..
      rm -rf lambda-package
      mkdir -p lambda-package
      cp dist/index.js lambda-package/
      cp -r node_modules lambda-package/
    EOT
  }

  triggers = {
    build_trigger = null_resource.build_lambda.id
  }
}

# Package the Lambda function
data "archive_file" "document_upload_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda-package"
  output_path = "${path.module}/../function.zip"
  depends_on  = [null_resource.create_lambda_package]
}

# Build the Lambda function
resource "null_resource" "build_lambda" {
  provisioner "local-exec" {
    command = "cd ${path.module}/.. && npm install && npm run build && npm prune --production"
  }

  triggers = {
    # Rebuild when source files change
    source_hash = filebase64sha256("${path.module}/../src/index.ts")
    package_json = filebase64sha256("${path.module}/../package.json")
  }
}

# Lambda function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-document-upload
# ACTUAL ROLE: arn:aws:iam::254539707041:role/ai-assistant-lambda-document-execution-role
resource "aws_lambda_function" "document_upload" {
  filename         = data.archive_file.document_upload_lambda.output_path
  function_name    = "ai-assistant-dev-document-upload"
  role            = "arn:aws:iam::254539707041:role/ai-assistant-lambda-document-execution-role"
  handler         = "index.handler"
  runtime         = "nodejs18.x"
  timeout         = 30
  memory_size     = 512

  source_code_hash = data.archive_file.document_upload_lambda.output_base64sha256

  environment {
    variables = {
      DOCUMENTS_BUCKET    = var.documents_bucket_name
      DOCUMENTS_TABLE     = var.documents_table_name
      KNOWLEDGE_BASE_ID   = var.knowledge_base_id
      DATA_SOURCE_ID      = var.data_source_id
    }
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-document-upload"
    Purpose     = "Document Upload to Knowledge Base"
    Environment = var.environment
  })

  depends_on = [
    null_resource.build_lambda,
    data.archive_file.document_upload_lambda
  ]
}

# CloudWatch Log Group (DOCUMENTATION ONLY)
# ACTUAL LOG GROUP: /aws/lambda/ai-assistant-dev-document-upload (retention: 14 days)
resource "aws_cloudwatch_log_group" "document_upload_logs" {
  name              = "/aws/lambda/ai-assistant-dev-document-upload"
  retention_in_days = 14

  tags = var.tags
}

# API Gateway Integration
resource "aws_api_gateway_integration" "document_upload" {
  rest_api_id = var.api_gateway_id
  resource_id = var.api_gateway_documents_resource_id
  http_method = aws_api_gateway_method.document_upload_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.document_upload.invoke_arn
}

# API Gateway Method
resource "aws_api_gateway_method" "document_upload_post" {
  rest_api_id   = var.api_gateway_id
  resource_id   = var.api_gateway_documents_resource_id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# API Gateway Method Response
resource "aws_api_gateway_method_response" "document_upload_200" {
  rest_api_id = var.api_gateway_id
  resource_id = var.api_gateway_documents_resource_id
  http_method = aws_api_gateway_method.document_upload_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

# API Gateway Integration Response
resource "aws_api_gateway_integration_response" "document_upload_200" {
  rest_api_id = var.api_gateway_id
  resource_id = var.api_gateway_documents_resource_id
  http_method = aws_api_gateway_method.document_upload_post.http_method
  status_code = aws_api_gateway_method_response.document_upload_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
  }

  depends_on = [aws_api_gateway_integration.document_upload]
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway-${var.project_name}-document-upload"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_upload.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}