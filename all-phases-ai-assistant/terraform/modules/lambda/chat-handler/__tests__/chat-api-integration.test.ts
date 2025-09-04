/**
 * Integration tests for Chat API endpoints
 * Tests against real AWS infrastructure following TDD principles
 */

import { APIGatewayProxyEvent, Context } from 'aws-lambda';
import { BedrockService } from '../src/bedrock-service';
import { chatApiHandler } from '../src/chat-api-handler';
import { ConversationService } from '../src/conversation-service';

// Test configuration
const TEST_USER_ID = 'test-user-123';
const TEST_KNOWLEDGE_BASE_ID = 'PQB7MB5ORO'; // Deployed Knowledge Base ID
const TEST_DOCUMENTS_TABLE = 'ai-assistant-dev-documents'; // Deployed DynamoDB table

describe('Chat API Integration Tests', () => {
  let conversationService: ConversationService;
  let bedrockService: BedrockService;
  let testConversationId: string;

  beforeAll(async () => {
    // Set required environment variables for testing
    process.env.KNOWLEDGE_BASE_ID = TEST_KNOWLEDGE_BASE_ID;
    process.env.DOCUMENTS_TABLE = TEST_DOCUMENTS_TABLE;
    process.env.AWS_PROFILE = 'aidlc_main';
    process.env.AWS_REGION = 'us-west-2';
    
    // Ensure we have required environment variables
    expect(process.env.KNOWLEDGE_BASE_ID).toBeDefined();
    expect(process.env.DOCUMENTS_TABLE).toBeDefined();
    
    conversationService = new ConversationService();
    bedrockService = new BedrockService();
  });

  beforeEach(async () => {
    // Create a test conversation for each test
    testConversationId = await conversationService.createConversation(TEST_USER_ID);
    
    // Add delay to avoid Bedrock throttling
    await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
  });

  afterEach(async () => {
    // Clean up test conversation
    if (testConversationId) {
      try {
        await conversationService.deleteConversation(testConversationId);
      } catch (error) {
        console.warn('Failed to clean up test conversation:', error);
      }
    }
  });

  describe('POST /chat/ask', () => {
    test('should handle chat request with Knowledge Base integration', async () => {
      // RED: Test that we can ask a question and get a response with sources
      const event: APIGatewayProxyEvent = {
        httpMethod: 'POST',
        resource: '/chat/ask',
        path: '/chat/ask',
        body: JSON.stringify({
          question: 'What is AWS Lambda?',
          userId: TEST_USER_ID,
          queryComplexity: 'moderate'
        }),
        headers: {
          'Content-Type': 'application/json'
        },
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: null,
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(200);
      
      const responseBody = JSON.parse(result.body);
      
      // Log the actual response to verify Knowledge Base integration
      console.log('=== CHAT RESPONSE ===');
      console.log('Answer:', responseBody.answer);
      console.log('Sources count:', responseBody.sources?.length || 0);
      console.log('Sources:', JSON.stringify(responseBody.sources, null, 2));
      console.log('Model used:', responseBody.modelUsed);
      console.log('Conversation ID:', responseBody.conversationId);
      console.log('====================');
      
      expect(responseBody.answer).toBeDefined();
      expect(responseBody.answer).not.toBe('');
      expect(responseBody.sources).toBeDefined();
      expect(Array.isArray(responseBody.sources)).toBe(true);
      expect(responseBody.conversationId).toBeDefined();
      expect(responseBody.timestamp).toBeDefined();
      expect(responseBody.modelUsed).toBeDefined();
    });

    test('should create new conversation when conversationId not provided', async () => {
      const event: APIGatewayProxyEvent = {
        httpMethod: 'POST',
        resource: '/chat/ask',
        path: '/chat/ask',
        body: JSON.stringify({
          question: 'Test question without conversation ID',
          userId: TEST_USER_ID
        }),
        headers: {
          'Content-Type': 'application/json'
        },
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: null,
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      // Debug: Log the actual response if it's not 200
      if (result.statusCode !== 200) {
        console.error('Unexpected status code:', result.statusCode);
        console.error('Response body:', result.body);
      }

      expect(result.statusCode).toBe(200);
      
      const responseBody = JSON.parse(result.body);
      
      // Log the actual response to verify Knowledge Base integration
      console.log('=== NEW CONVERSATION RESPONSE ===');
      console.log('Answer:', responseBody.answer);
      console.log('Sources count:', responseBody.sources?.length || 0);
      console.log('Model used:', responseBody.modelUsed);
      console.log('Conversation ID:', responseBody.conversationId);
      console.log('================================');
      
      expect(responseBody.conversationId).toBeDefined();
      expect(responseBody.conversationId).not.toBe(testConversationId);
      
      // Clean up the created conversation
      await conversationService.deleteConversation(responseBody.conversationId);
    });

    test('should validate request body and return 400 for invalid requests', async () => {
      const event: APIGatewayProxyEvent = {
        httpMethod: 'POST',
        resource: '/chat/ask',
        path: '/chat/ask',
        body: JSON.stringify({
          // Missing required fields
          question: '',
          userId: ''
        }),
        headers: {
          'Content-Type': 'application/json'
        },
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: null,
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(400);
      
      const responseBody = JSON.parse(result.body);
      expect(responseBody.error).toBeDefined();
      expect(responseBody.error.code).toBe('VALIDATION_ERROR');
    });
  });

  describe('GET /chat/conversations', () => {
    test('should return user conversations', async () => {
      // Add a message to the test conversation
      await conversationService.addMessage(
        testConversationId,
        'user',
        'Test message'
      );

      const event: APIGatewayProxyEvent = {
        httpMethod: 'GET',
        resource: '/chat/conversations',
        path: '/chat/conversations',
        body: null,
        headers: {},
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: null,
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(200);
      
      const responseBody = JSON.parse(result.body);
      expect(responseBody.conversations).toBeDefined();
      expect(Array.isArray(responseBody.conversations)).toBe(true);
      expect(responseBody.totalConversations).toBeDefined();
      
      // Should include our test conversation
      const testConv = responseBody.conversations.find(
        (conv: any) => conv.conversationId === testConversationId
      );
      expect(testConv).toBeDefined();
    });
  });

  describe('GET /chat/history/{conversationId}', () => {
    test('should return conversation history', async () => {
      // Add some messages to the conversation
      await conversationService.addMessage(
        testConversationId,
        'user',
        'First message'
      );
      await conversationService.addMessage(
        testConversationId,
        'assistant',
        'First response'
      );

      const event: APIGatewayProxyEvent = {
        httpMethod: 'GET',
        resource: '/chat/history/{conversationId}',
        path: `/chat/history/${testConversationId}`,
        body: null,
        headers: {},
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: {
          conversationId: testConversationId
        },
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(200);
      
      const responseBody = JSON.parse(result.body);
      expect(responseBody.conversationId).toBe(testConversationId);
      expect(responseBody.messages).toBeDefined();
      expect(Array.isArray(responseBody.messages)).toBe(true);
      expect(responseBody.messages.length).toBe(2);
      expect(responseBody.totalMessages).toBe(2);
    });

    test('should return 404 for non-existent conversation', async () => {
      const nonExistentId = 'non-existent-conversation-id';
      
      const event: APIGatewayProxyEvent = {
        httpMethod: 'GET',
        resource: '/chat/history/{conversationId}',
        path: `/chat/history/${nonExistentId}`,
        body: null,
        headers: {},
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: {
          conversationId: nonExistentId
        },
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(404);
      
      const responseBody = JSON.parse(result.body);
      expect(responseBody.error).toBeDefined();
      expect(responseBody.error.code).toBe('CONVERSATION_NOT_FOUND');
    });
  });

  describe('DELETE /chat/conversations/{conversationId}', () => {
    test('should delete conversation successfully', async () => {
      // Add a message to ensure conversation exists
      await conversationService.addMessage(
        testConversationId,
        'user',
        'Test message for deletion'
      );

      const event: APIGatewayProxyEvent = {
        httpMethod: 'DELETE',
        resource: '/chat/conversations/{conversationId}',
        path: `/chat/conversations/${testConversationId}`,
        body: null,
        headers: {},
        requestContext: {
          authorizer: {
            claims: {
              sub: TEST_USER_ID
            }
          }
        } as any,
        pathParameters: {
          conversationId: testConversationId
        },
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(200);
      
      const responseBody = JSON.parse(result.body);
      expect(responseBody.message).toBe('Conversation deleted successfully');
      expect(responseBody.conversationId).toBe(testConversationId);

      // Verify conversation is actually deleted
      const deletedConversation = await conversationService.getConversation(testConversationId);
      expect(deletedConversation).toBeNull();
      
      // Clear testConversationId so afterEach doesn't try to delete it again
      testConversationId = '';
    });
  });

  describe('CORS handling', () => {
    test('should handle OPTIONS requests correctly', async () => {
      const event: APIGatewayProxyEvent = {
        httpMethod: 'OPTIONS',
        resource: '/chat/ask',
        path: '/chat/ask',
        body: null,
        headers: {},
        requestContext: {} as any,
        pathParameters: null,
        queryStringParameters: null,
        multiValueHeaders: {},
        multiValueQueryStringParameters: null,
        stageVariables: null,
        isBase64Encoded: false
      };

      const context: Context = {
        callbackWaitsForEmptyEventLoop: false,
        functionName: 'test-function',
        functionVersion: '1',
        invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test',
        memoryLimitInMB: '1024',
        awsRequestId: 'test-request-id',
        logGroupName: '/aws/lambda/test',
        logStreamName: 'test-stream',
        getRemainingTimeInMillis: () => 30000,
        done: () => {},
        fail: () => {},
        succeed: () => {}
      };

      const result = await chatApiHandler(event, context);

      expect(result.statusCode).toBe(200);
      expect(result.headers).toBeDefined();
      if (result.headers) {
        expect(result.headers['Access-Control-Allow-Origin']).toBe('*');
        expect(result.headers['Access-Control-Allow-Methods']).toBeDefined();
        expect(result.headers['Access-Control-Allow-Headers']).toBeDefined();
      }
    });
  });
});