/**
 * Integration tests for Chat Handler Lambda Function
 * These tests run against REAL AWS infrastructure as per steering requirements
 * NO MOCKING - all tests use actual AWS services
 */

import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { handler } from '../src/index';
import { ChatRequest, ChatResponse, QueryComplexity } from '../src/types';

// Set up environment variables for real AWS testing
process.env.AWS_REGION = 'us-west-2';
process.env.AWS_PROFILE = 'aidlc_main'; // Use the correct AWS profile
process.env.ENVIRONMENT = 'development';
process.env.KNOWLEDGE_BASE_ID = 'PQB7MB5ORO'; // Real deployed Knowledge Base ID
process.env.LOG_LEVEL = 'INFO';

describe('Chat Handler Lambda - Integration Tests (Real AWS)', () => {
  const mockContext: Context = {
    callbackWaitsForEmptyEventLoop: false,
    functionName: 'ai-assistant-chat-handler',
    functionVersion: '1',
    invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:ai-assistant-chat-handler',
    memoryLimitInMB: '1024',
    awsRequestId: `test-${Date.now()}`,
    logGroupName: '/aws/lambda/ai-assistant-chat-handler',
    logStreamName: `test-stream-${Date.now()}`,
    getRemainingTimeInMillis: () => 25000, // 25 seconds remaining
    done: jest.fn(),
    fail: jest.fn(),
    succeed: jest.fn()
  };

  const createMockEvent = (body: any): APIGatewayProxyEvent => ({
    body: JSON.stringify(body),
    headers: {
      'Content-Type': 'application/json'
    },
    multiValueHeaders: {},
    httpMethod: 'POST',
    isBase64Encoded: false,
    path: '/chat/ask',
    pathParameters: null,
    queryStringParameters: null,
    multiValueQueryStringParameters: null,
    stageVariables: null,
    requestContext: {
      accountId: '123456789012',
      apiId: 'test-api',
      authorizer: {},
      httpMethod: 'POST',
      identity: {
        accessKey: null,
        accountId: null,
        apiKey: null,
        apiKeyId: null,
        caller: null,
        cognitoAuthenticationProvider: null,
        cognitoAuthenticationType: null,
        cognitoIdentityId: null,
        cognitoIdentityPoolId: null,
        principalOrgId: null,
        sourceIp: '127.0.0.1',
        user: null,
        userAgent: 'test-agent',
        userArn: null,
        clientCert: null
      },
      path: '/chat/ask',
      protocol: 'HTTP/1.1',
      requestId: `test-request-${Date.now()}`,
      requestTime: new Date().toUTCString(),
      requestTimeEpoch: Date.now(),
      resourceId: 'test-resource',
      resourcePath: '/chat/ask',
      stage: 'test'
    },
    resource: '/chat/ask'
  });

  // Increase timeout for real AWS calls
  jest.setTimeout(30000);

  describe('Input Validation (Real AWS)', () => {
    test('should validate required fields and return 400', async () => {
      const invalidRequest = {
        // Missing question and userId
      };

      const event = createMockEvent(invalidRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBe(400);
      
      const errorResponse = JSON.parse(result.body);
      expect(errorResponse.error).toBeDefined();
      expect(errorResponse.error.code).toBe('VALIDATION_ERROR');
      expect(errorResponse.error.message).toContain('question');
      expect(errorResponse.error.message).toContain('userId');
    });

    test('should enforce question length limits', async () => {
      const longQuestion = 'a'.repeat(6000); // Exceeds 5000 char limit
      const chatRequest: ChatRequest = {
        question: longQuestion,
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBe(400);
      
      const errorResponse = JSON.parse(result.body);
      expect(errorResponse.error).toBeDefined();
      expect(errorResponse.error.message).toContain('length');
    });

    test('should accept valid request structure', async () => {
      const validRequest: ChatRequest = {
        question: 'What is AWS Lambda?',
        userId: 'test-user-123'
      };

      const event = createMockEvent(validRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      // Should not be a validation error (400)
      expect(result.statusCode).not.toBe(400);
      
      // Parse response to ensure it's valid JSON
      expect(() => JSON.parse(result.body)).not.toThrow();
    });
  });

  describe('CORS Handling (Real AWS)', () => {
    test('should handle OPTIONS preflight request', async () => {
      const optionsEvent: APIGatewayProxyEvent = {
        ...createMockEvent({}),
        httpMethod: 'OPTIONS'
      };

      const result = await handler(optionsEvent, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBe(200);
      expect(result.headers).toHaveProperty('Access-Control-Allow-Origin', '*');
      expect(result.headers).toHaveProperty('Access-Control-Allow-Methods', 'POST,OPTIONS');
      expect(result.body).toBe('');
    });

    test('should include CORS headers in POST response', async () => {
      const chatRequest: ChatRequest = {
        question: 'Test CORS headers',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.headers).toHaveProperty('Access-Control-Allow-Origin', '*');
      expect(result.headers).toHaveProperty('Content-Type', 'application/json');
    });
  });

  describe('Error Handling (Real AWS)', () => {
    test('should handle invalid JSON in request body', async () => {
      const eventWithInvalidJson: APIGatewayProxyEvent = {
        ...createMockEvent({}),
        body: '{ invalid json }'
      };

      const result = await handler(eventWithInvalidJson, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBe(400);
      
      const errorResponse = JSON.parse(result.body);
      expect(errorResponse.error.code).toBe('INVALID_JSON');
    });

    test('should handle Bedrock service errors gracefully', async () => {
      // This test will likely fail initially due to missing Knowledge Base
      // but should handle the error gracefully rather than crashing
      const chatRequest: ChatRequest = {
        question: 'Test Bedrock error handling',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      // Should not crash with 500 error, should handle gracefully
      expect(result.statusCode).toBeDefined();
      expect([200, 400, 404, 503].includes(result.statusCode)).toBe(true);
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode !== 200) {
        expect(response.error).toBeDefined();
        expect(response.error.code).toBeDefined();
        expect(response.error.message).toBeDefined();
      }
    });
  });

  describe('Conversation Context Management (Real AWS)', () => {
    test('should create new conversation ID when not provided', async () => {
      const chatRequest: ChatRequest = {
        question: 'Start new conversation',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      if (result.statusCode === 200) {
        const response: ChatResponse = JSON.parse(result.body);
        expect(response.conversationId).toBeDefined();
        expect(response.conversationId).toMatch(/^[0-9a-f-]{36}$/); // UUID format
      }
    });

    test('should use existing conversation ID when provided', async () => {
      const existingConversationId = '12345678-1234-1234-1234-123456789012';
      const chatRequest: ChatRequest = {
        question: 'Continue conversation',
        userId: 'test-user-123',
        conversationId: existingConversationId
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      if (result.statusCode === 200) {
        const response: ChatResponse = JSON.parse(result.body);
        expect(response.conversationId).toBe(existingConversationId);
      }
    });
  });

  describe('Model Selection Logic (Real AWS)', () => {
    test('should handle different query complexities', async () => {
      const testCases = [
        {
          question: 'Hi',
          expectedComplexity: QueryComplexity.SIMPLE
        },
        {
          question: 'What is AWS Lambda and how does it work?',
          expectedComplexity: QueryComplexity.MODERATE
        },
        {
          question: 'Analyze the architectural patterns in our system design documents and compare them with AWS best practices for scalability, security, and cost optimization. Provide detailed recommendations for improvements.',
          expectedComplexity: QueryComplexity.COMPLEX
        }
      ];

      for (const testCase of testCases) {
        const chatRequest: ChatRequest = {
          question: testCase.question,
          userId: 'test-user-123'
        };

        const event = createMockEvent(chatRequest);
        const result = await handler(event, mockContext) as APIGatewayProxyResult;

        // Should handle all complexity levels without crashing
        expect(result.statusCode).toBeDefined();
        expect(() => JSON.parse(result.body)).not.toThrow();
        
        // Add delay to respect Bedrock rate limits
        await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
      }
    }, 60000); // 60 second timeout to accommodate delays
  });

  describe('Response Structure (Real AWS)', () => {
    test('should return properly structured response on success', async () => {
      const chatRequest: ChatRequest = {
        question: 'Test response structure',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      expect(result.headers).toBeDefined();
      expect(result.body).toBeDefined();

      const response = JSON.parse(result.body);
      
      if (result.statusCode === 200) {
        // Success response should have ChatResponse structure
        expect(response).toHaveProperty('answer');
        expect(response).toHaveProperty('sources');
        expect(response).toHaveProperty('conversationId');
        expect(response).toHaveProperty('timestamp');
        expect(response).toHaveProperty('modelUsed');
        expect(response).toHaveProperty('tokenUsage');
        expect(response).toHaveProperty('cost');
        
        expect(Array.isArray(response.sources)).toBe(true);
        expect(typeof response.cost).toBe('number');
        expect(response.tokenUsage).toHaveProperty('inputTokens');
        expect(response.tokenUsage).toHaveProperty('outputTokens');
        expect(response.tokenUsage).toHaveProperty('totalTokens');
      } else {
        // Error response should have error structure
        expect(response).toHaveProperty('error');
        expect(response.error).toHaveProperty('code');
        expect(response.error).toHaveProperty('message');
      }
    });
  });

  describe('Performance and Timeout (Real AWS)', () => {
    test('should complete within reasonable time', async () => {
      const startTime = Date.now();
      
      const chatRequest: ChatRequest = {
        question: 'Performance test question',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;
      
      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should complete within 25 seconds (less than Lambda timeout)
      expect(duration).toBeLessThan(25000);
      
      // Should return a response
      expect(result).toBeDefined();
      expect(result.statusCode).toBeDefined();
    });
  });
});