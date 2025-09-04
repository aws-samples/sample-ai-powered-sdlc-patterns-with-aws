import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { BedrockService } from './bedrock-service';
import {
    createCORSConfigFromEnv,
    createErrorResponse,
    createSuccessResponse,
    extractOriginFromEvent,
    handleOPTIONSRequest
} from './cors-utils';
import { BedrockError } from './types';
import {
    APIGatewayEventSchema,
    ChatRequest,
    sanitizeInput,
    validateChatRequest
} from './validation';

const bedrockService = new BedrockService();

// Create CORS configuration from environment variables
const corsConfig = createCORSConfigFromEnv();

export const handler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  // Extract origin for CORS handling
  const requestOrigin = extractOriginFromEvent(event);
  
  // Log only non-sensitive request metadata
  console.log('Chat handler invoked:', {
    httpMethod: event.httpMethod,
    path: event.path,
    requestId: context.awsRequestId,
    origin: requestOrigin,
    userAgent: event.headers?.['User-Agent']?.substring(0, 100) || 'unknown'
  });
  
  try {
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
      return handleOPTIONSRequest(requestOrigin, corsConfig);
    }

    // Validate HTTP method
    if (event.httpMethod !== 'POST') {
      return createErrorResponse(405, 'Method not allowed', context.awsRequestId, 'METHOD_NOT_ALLOWED', requestOrigin, corsConfig);
    }

    // Validate API Gateway event structure
    try {
      APIGatewayEventSchema.parse(event);
    } catch (error) {
      return createErrorResponse(400, 'Invalid request structure', context.awsRequestId, 'INVALID_REQUEST', requestOrigin, corsConfig);
    }

    // Validate request size
    if (event.body && event.body.length > 10000) {
      return createErrorResponse(413, 'Request body too large', context.awsRequestId, 'PAYLOAD_TOO_LARGE', requestOrigin, corsConfig);
    }
    
    // Parse request body
    let requestBody;
    try {
      requestBody = JSON.parse(event.body || '{}');
    } catch (error) {
      return createErrorResponse(400, 'Invalid JSON in request body', context.awsRequestId, 'INVALID_JSON', requestOrigin, corsConfig);
    }
    
    // Validate and sanitize request
    let chatRequest: ChatRequest;
    try {
      chatRequest = validateChatRequest(requestBody);
      // Additional sanitization
      chatRequest.question = sanitizeInput(chatRequest.question);
    } catch (error) {
      return createErrorResponse(400, error instanceof Error ? error.message : 'Validation failed', context.awsRequestId, 'VALIDATION_ERROR', requestOrigin, corsConfig);
    }
    
    // chatRequest is already validated and sanitized above
    
    // Validate environment variables
    if (!process.env.KNOWLEDGE_BASE_ID) {
      console.error('KNOWLEDGE_BASE_ID environment variable is not set');
      return createErrorResponse(
        500,
        'Knowledge Base is not configured. Please ensure the Knowledge Base is deployed.',
        context.awsRequestId,
        'CONFIGURATION_ERROR',
        requestOrigin,
        corsConfig
      );
    }

    // Process chat request with advanced RAG if enabled
    const useAdvancedRAG = process.env.ENABLE_ADVANCED_RAG === 'true' || requestBody.useAdvancedRAG;
    const response = useAdvancedRAG 
      ? await bedrockService.handleChatQueryWithAdvancedRAG(chatRequest)
      : await bedrockService.handleChatQuery(chatRequest);
    
    return createSuccessResponse(response, 200, requestOrigin, corsConfig);
    
  } catch (error) {
    const bedrockError = error as BedrockError;
    const statusCode = bedrockError.statusCode || 500;
    
    // Log error details server-side only (no sensitive info)
    console.error('Chat handler error:', {
      code: bedrockError.code,
      statusCode,
      requestId: context.awsRequestId,
      timestamp: new Date().toISOString()
    });
    
    // Return generic error message to client with proper CORS headers
    return createErrorResponse(
      statusCode,
      bedrockError.message || 'An unexpected error occurred while processing your request',
      context.awsRequestId,
      bedrockError.code,
      requestOrigin,
      corsConfig
    );
  }
};