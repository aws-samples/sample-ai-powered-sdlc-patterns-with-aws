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

# API Gateway integration for Chat Handler Lambda (DOCUMENTATION ONLY)
# This file documents the API Gateway resources for chat endpoints
# ACTUAL API GATEWAY: jpt8wzkowd (ai-assistant-api)

# /chat/ask resource
resource "aws_api_gateway_resource" "chat_ask" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_chat_resource_id
  path_part   = "ask"
}

# POST /chat/ask method
resource "aws_api_gateway_method" "chat_ask_post" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_ask.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_validator_id = aws_api_gateway_request_validator.chat_validator.id
  
  request_models = {
    "application/json" = aws_api_gateway_model.chat_request.name
  }
}

# POST /chat/ask integration
resource "aws_api_gateway_integration" "chat_ask_post" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.chat_handler.invoke_arn
  
  # Set timeout to maximum allowed (29 seconds)
  timeout_milliseconds = 29000
}

# OPTIONS /chat/ask method for CORS preflight
resource "aws_api_gateway_method" "chat_ask_options" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_ask.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS /chat/ask integration
resource "aws_api_gateway_integration" "chat_ask_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_options.http_method

  type                    = "MOCK"
  passthrough_behavior    = "NEVER"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# /chat/stream resource for streaming responses
resource "aws_api_gateway_resource" "chat_stream" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_chat_resource_id
  path_part   = "stream"
}

# POST /chat/stream method
resource "aws_api_gateway_method" "chat_stream_post" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_stream.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_validator_id = aws_api_gateway_request_validator.chat_validator.id
  
  request_models = {
    "application/json" = aws_api_gateway_model.chat_request.name
  }
}

# POST /chat/stream integration
resource "aws_api_gateway_integration" "chat_stream_post" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_stream.id
  http_method = aws_api_gateway_method.chat_stream_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.chat_handler.invoke_arn
}

# OPTIONS /chat/stream method for CORS preflight
resource "aws_api_gateway_method" "chat_stream_options" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_stream.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS /chat/stream integration
resource "aws_api_gateway_integration" "chat_stream_options" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_stream.id
  http_method = aws_api_gateway_method.chat_stream_options.http_method

  type                    = "MOCK"
  passthrough_behavior    = "NEVER"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# /chat/conversations resource
resource "aws_api_gateway_resource" "chat_conversations" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_chat_resource_id
  path_part   = "conversations"
}

# GET /chat/conversations method
resource "aws_api_gateway_method" "chat_conversations_get" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_conversations.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.querystring.limit" = false
  }
}

# GET /chat/conversations integration
resource "aws_api_gateway_integration" "chat_conversations_get" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_conversations.id
  http_method = aws_api_gateway_method.chat_conversations_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.chat_handler.invoke_arn
}

# /chat/conversations/{conversationId} resource
resource "aws_api_gateway_resource" "chat_conversation_id" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.chat_conversations.id
  path_part   = "{conversationId}"
}

# DELETE /chat/conversations/{conversationId} method
resource "aws_api_gateway_method" "chat_conversation_delete" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_conversation_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.path.conversationId" = true
  }
}

# DELETE /chat/conversations/{conversationId} integration
resource "aws_api_gateway_integration" "chat_conversation_delete" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_conversation_id.id
  http_method = aws_api_gateway_method.chat_conversation_delete.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.chat_handler.invoke_arn
}

# /chat/history/{conversationId} resource
resource "aws_api_gateway_resource" "chat_history" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_chat_resource_id
  path_part   = "history"
}

resource "aws_api_gateway_resource" "chat_history_id" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.chat_history.id
  path_part   = "{conversationId}"
}

# GET /chat/history/{conversationId} method
resource "aws_api_gateway_method" "chat_history_get" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.chat_history_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id

  request_parameters = {
    "method.request.path.conversationId" = true
    "method.request.querystring.limit"   = false
  }
}

# GET /chat/history/{conversationId} integration
resource "aws_api_gateway_integration" "chat_history_get" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_history_id.id
  http_method = aws_api_gateway_method.chat_history_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.chat_handler.invoke_arn
}

# Request validator for chat endpoints
resource "aws_api_gateway_request_validator" "chat_validator" {
  name                        = "${var.project_name}-chat-validator"
  rest_api_id                = var.api_gateway_id
  validate_request_body      = true
  validate_request_parameters = true
}

# Request model for chat API
resource "aws_api_gateway_model" "chat_request" {
  rest_api_id  = var.api_gateway_id
  name         = "ChatRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Chat Request Schema"
    type      = "object"
    properties = {
      question = {
        type        = "string"
        minLength   = 1
        maxLength   = 5000
        description = "The user's question"
      }
      userId = {
        type        = "string"
        minLength   = 1
        description = "The user's ID"
      }
      conversationId = {
        type        = "string"
        description = "Optional conversation ID"
      }
      queryComplexity = {
        type = "string"
        enum = ["simple", "moderate", "complex"]
        description = "Optional query complexity classification"
      }
      useAdvancedRAG = {
        type        = "boolean"
        description = "Whether to use advanced RAG configuration"
      }
      enableStreaming = {
        type        = "boolean"
        description = "Whether to enable streaming responses"
      }
    }
    required = ["question", "userId"]
  })
}

# Lambda permissions for API Gateway (DOCUMENTATION ONLY)
resource "aws_lambda_permission" "chat_ask_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway-${var.project_name}-chat-ask"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chat_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# Lambda function reference (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-chat-endpoints
# This references the Lambda function defined in main.tf

# DynamoDB permissions for conversation management
resource "aws_iam_policy" "chat_handler_dynamodb" {
  name        = "${var.project_name}-chat-handler-dynamodb"
  path        = "/"
  description = "IAM policy for DynamoDB access from chat handler Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
      }
    ]
  })
}

# Attach DynamoDB policy to Lambda role
resource "aws_iam_role_policy_attachment" "chat_handler_dynamodb" {
  role       = aws_iam_role.chat_handler_role.name
  policy_arn = aws_iam_policy.chat_handler_dynamodb.arn
}

# Method responses for all endpoints
resource "aws_api_gateway_method_response" "chat_ask_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# Error method responses with CORS headers
resource "aws_api_gateway_method_response" "chat_ask_401" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "401"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "chat_ask_403" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "403"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "chat_ask_500" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "500"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# POST integration response for CORS
resource "aws_api_gateway_integration_response" "chat_ask_post_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = aws_api_gateway_method_response.chat_ask_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

# Error integration responses with CORS headers
resource "aws_api_gateway_integration_response" "chat_ask_401" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "401"
  selection_pattern = "401"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_method_response.chat_ask_401]
}

resource "aws_api_gateway_integration_response" "chat_ask_403" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "403"
  selection_pattern = "403"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_method_response.chat_ask_403]
}

resource "aws_api_gateway_integration_response" "chat_ask_500" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_post.http_method
  status_code = "500"
  selection_pattern = "5\\d{2}"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_method_response.chat_ask_500]
}

# OPTIONS method response for CORS preflight
resource "aws_api_gateway_method_response" "chat_ask_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Headers" = true
  }
}

# OPTIONS integration response for CORS preflight
resource "aws_api_gateway_integration_response" "chat_ask_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_ask.id
  http_method = aws_api_gateway_method.chat_ask_options.http_method
  status_code = aws_api_gateway_method_response.chat_ask_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
  }
}

resource "aws_api_gateway_method_response" "chat_stream_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_stream.id
  http_method = aws_api_gateway_method.chat_stream_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# POST integration response for CORS
resource "aws_api_gateway_integration_response" "chat_stream_post_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_stream.id
  http_method = aws_api_gateway_method.chat_stream_post.http_method
  status_code = aws_api_gateway_method_response.chat_stream_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

# OPTIONS method response for CORS preflight
resource "aws_api_gateway_method_response" "chat_stream_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_stream.id
  http_method = aws_api_gateway_method.chat_stream_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Headers" = true
  }
}

# OPTIONS integration response for CORS preflight
resource "aws_api_gateway_integration_response" "chat_stream_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_stream.id
  http_method = aws_api_gateway_method.chat_stream_options.http_method
  status_code = aws_api_gateway_method_response.chat_stream_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
  }
}

resource "aws_api_gateway_method_response" "chat_conversations_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_conversations.id
  http_method = aws_api_gateway_method.chat_conversations_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "chat_conversation_delete_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_conversation_id.id
  http_method = aws_api_gateway_method.chat_conversation_delete.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "chat_history_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.chat_history_id.id
  http_method = aws_api_gateway_method.chat_history_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}