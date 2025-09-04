import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { BedrockService } from './bedrock-service';
import { ConversationService } from './conversation-service';
import { StreamingService } from './streaming-service';
import {
    BedrockError,
    ChatApiRequest
} from './types';
import {
    ChatRequest,
    createValidationErrorResponse,
    validateChatRequest
} from './validation';

const bedrockService = new BedrockService();
const conversationService = new ConversationService();
const streamingService = new StreamingService();

export const chatApiHandler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  console.log('Chat API handler invoked:', JSON.stringify(event, null, 2));
  
  try {
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
      return createCorsResponse(200, '');
    }

    // Route based on path and method
    const path = event.resource;
    const method = event.httpMethod;

    switch (`${method} ${path}`) {
      case 'POST /chat/ask':
        return await handleChatAsk(event, context);
      case 'GET /chat/history/{conversationId}':
        return await handleGetConversationHistory(event, context);
      case 'GET /chat/conversations':
        return await handleGetUserConversations(event, context);
      case 'DELETE /chat/conversations/{conversationId}':
        return await handleDeleteConversation(event, context);
      case 'POST /chat/stream':
        return await handleStreamingChat(event, context);
      default:
        return createCorsResponse(404, JSON.stringify({
          error: {
            code: 'NOT_FOUND',
            message: 'Endpoint not found'
          }
        }));
    }

  } catch (error) {
    console.error('Error in chat API handler:', error);
    
    const bedrockError = error as BedrockError;
    const statusCode = bedrockError.statusCode || 500;
    
    return createCorsResponse(statusCode, JSON.stringify({
      error: {
        code: bedrockError.code || 'INTERNAL_ERROR',
        message: bedrockError.message || 'An unexpected error occurred',
        requestId: context.awsRequestId,
        timestamp: new Date().toISOString()
      }
    }));
  }
};

async function handleChatAsk(
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> {
  // Parse and validate request
  const requestBody = parseRequestBody(event.body);
  let chatRequest: ChatRequest;
  try {
    chatRequest = validateChatRequest(requestBody);
  } catch (error) {
    return createValidationErrorResponse([error instanceof Error ? error.message : 'Validation failed']);
  }

  const apiRequest: ChatApiRequest = requestBody;
  
  // Get or create conversation
  let conversationId = apiRequest.conversationId || chatRequest.conversationId;
  if (!conversationId) {
    conversationId = await conversationService.createConversation(chatRequest.userId);
  }

  // Add user message to conversation history
  await conversationService.addMessage(
    conversationId,
    'user',
    chatRequest.question
  );

  // Update chat request with conversation ID
  chatRequest.conversationId = conversationId;

  // Process chat request
  const useAdvancedRAG = apiRequest.useAdvancedRAG || process.env.ENABLE_ADVANCED_RAG === 'true';
  const response = useAdvancedRAG 
    ? await bedrockService.handleChatQueryWithAdvancedRAG(chatRequest)
    : await bedrockService.handleChatQuery(chatRequest);

  // Add assistant response to conversation history
  await conversationService.addMessage(
    conversationId,
    'assistant',
    response.answer,
    response.sources
  );

  // Return response with conversation context
  const responseBody = {
    ...response,
    conversationId
  };

  return createCorsResponse(200, JSON.stringify(responseBody));
}

async function handleStreamingChat(
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> {
  // Parse and validate request
  const requestBody = parseRequestBody(event.body);
  let chatRequest: ChatRequest;
  try {
    chatRequest = validateChatRequest(requestBody);
  } catch (error) {
    return createValidationErrorResponse([error instanceof Error ? error.message : 'Validation failed']);
  }

  const apiRequest: ChatApiRequest = requestBody;
  
  // Get or create conversation
  let conversationId = apiRequest.conversationId;
  if (!conversationId) {
    conversationId = await conversationService.createConversation(apiRequest.userId);
  }

  // Add user message to conversation history
  await conversationService.addMessage(
    conversationId,
    'user',
    apiRequest.question
  );

  try {
    // Update chat request with conversation ID
    chatRequest.conversationId = conversationId;

    // Get sources from Knowledge Base (without generating response)
    const ragResponse = await bedrockService.handleChatQuery(chatRequest);
    
    // Use streaming service for response generation with available Claude model
    // Use the same model selection logic as bedrock-service for consistency
    const availableModel = 'anthropic.claude-3-5-sonnet-20241022-v2:0'; // Use direct model ID for on-demand support
    
    const streamingResponse = await streamingService.streamChatResponse(
      chatRequest,
      availableModel,
      ragResponse.sources
    );

    // Process the stream to get full response
    const fullResponse = await streamingService.processStreamingResponse(streamingResponse.stream);

    // Add assistant response to conversation history
    await conversationService.addMessage(
      conversationId,
      'assistant',
      fullResponse,
      streamingResponse.sources
    );

    const responseBody = {
      answer: fullResponse,
      sources: streamingResponse.sources,
      conversationId,
      timestamp: new Date().toISOString(),
      modelUsed: streamingResponse.modelUsed,
      streaming: true
    };

    return createCorsResponse(200, JSON.stringify(responseBody));

  } catch (error) {
    console.error('Streaming chat error:', error);
    
    // Fallback to non-streaming response
    // Use the validated chatRequest with updated conversationId

    const response = await bedrockService.handleChatQuery(chatRequest);
    
    // Add assistant response to conversation history
    await conversationService.addMessage(
      conversationId,
      'assistant',
      response.answer,
      response.sources
    );

    const responseBody = {
      ...response,
      conversationId,
      streaming: false,
      fallbackReason: 'Streaming not available, used standard response'
    };

    return createCorsResponse(200, JSON.stringify(responseBody));
  }
}

async function handleGetConversationHistory(
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> {
  const conversationId = event.pathParameters?.conversationId;
  const userId = event.requestContext.authorizer?.claims?.sub;
  
  if (!conversationId) {
    return createCorsResponse(400, JSON.stringify({
      error: {
        code: 'MISSING_CONVERSATION_ID',
        message: 'Conversation ID is required'
      }
    }));
  }

  if (!userId) {
    return createCorsResponse(401, JSON.stringify({
      error: {
        code: 'UNAUTHORIZED',
        message: 'User ID not found in token'
      }
    }));
  }

  // Get conversation and verify ownership
  const conversation = await conversationService.getConversation(conversationId);
  
  if (!conversation) {
    return createCorsResponse(404, JSON.stringify({
      error: {
        code: 'CONVERSATION_NOT_FOUND',
        message: 'Conversation not found'
      }
    }));
  }

  if (conversation.userId !== userId) {
    return createCorsResponse(403, JSON.stringify({
      error: {
        code: 'FORBIDDEN',
        message: 'Access denied to this conversation'
      }
    }));
  }

  // Get conversation history
  const limit = parseInt(event.queryStringParameters?.limit || '50');
  const messages = await conversationService.getConversationHistory(conversationId, limit);

  return createCorsResponse(200, JSON.stringify({
    conversationId,
    messages,
    totalMessages: messages.length
  }));
}

async function handleGetUserConversations(
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> {
  const userId = event.requestContext.authorizer?.claims?.sub;
  
  if (!userId) {
    return createCorsResponse(401, JSON.stringify({
      error: {
        code: 'UNAUTHORIZED',
        message: 'User ID not found in token'
      }
    }));
  }

  const limit = parseInt(event.queryStringParameters?.limit || '10');
  const conversations = await conversationService.getUserConversations(userId, limit);

  return createCorsResponse(200, JSON.stringify({
    conversations,
    totalConversations: conversations.length
  }));
}

async function handleDeleteConversation(
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> {
  const conversationId = event.pathParameters?.conversationId;
  const userId = event.requestContext.authorizer?.claims?.sub;
  
  if (!conversationId) {
    return createCorsResponse(400, JSON.stringify({
      error: {
        code: 'MISSING_CONVERSATION_ID',
        message: 'Conversation ID is required'
      }
    }));
  }

  if (!userId) {
    return createCorsResponse(401, JSON.stringify({
      error: {
        code: 'UNAUTHORIZED',
        message: 'User ID not found in token'
      }
    }));
  }

  // Get conversation and verify ownership
  const conversation = await conversationService.getConversation(conversationId);
  
  if (!conversation) {
    return createCorsResponse(404, JSON.stringify({
      error: {
        code: 'CONVERSATION_NOT_FOUND',
        message: 'Conversation not found'
      }
    }));
  }

  if (conversation.userId !== userId) {
    return createCorsResponse(403, JSON.stringify({
      error: {
        code: 'FORBIDDEN',
        message: 'Access denied to this conversation'
      }
    }));
  }

  // Delete conversation
  await conversationService.deleteConversation(conversationId);

  return createCorsResponse(200, JSON.stringify({
    message: 'Conversation deleted successfully',
    conversationId
  }));
}

function parseRequestBody(body: string | null): any {
  if (!body) {
    throw new Error('Request body is required');
  }

  try {
    return JSON.parse(body);
  } catch (error) {
    throw new Error('Invalid JSON in request body');
  }
}

function createCorsResponse(statusCode: number, body: string): APIGatewayProxyResult {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    },
    body
  };
}