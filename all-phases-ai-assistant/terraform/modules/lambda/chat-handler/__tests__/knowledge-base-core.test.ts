/**
 * Core Knowledge Base Integration Tests
 * Focused tests without metrics tracking to avoid credential issues
 */

import { BedrockService } from '../src/bedrock-service';
import { ChatRequest, QueryComplexity } from '../src/types';

// Set up environment variables for real AWS testing
process.env.AWS_REGION = 'us-west-2';
process.env.AWS_PROFILE = 'aidlc_main';
process.env.ENVIRONMENT = 'development';
process.env.KNOWLEDGE_BASE_ID = 'PQB7MB5ORO';
process.env.LOG_LEVEL = 'INFO';

describe('Knowledge Base Core Integration Tests', () => {
  let bedrockService: BedrockService;
  
  // Increase timeout for real AWS calls
  jest.setTimeout(120000);
  
  beforeEach(() => {
    bedrockService = new BedrockService();
  });

  afterEach(() => {
    // Clean up any pending operations
    jest.clearAllTimers();
  });

  test('should successfully integrate with Knowledge Base and return structured response', async () => {
    const chatRequest: ChatRequest = {
      question: 'What is AWS Lambda?',
      userId: 'test-user-123'
    };

    const response = await bedrockService.handleChatQuery(chatRequest);
    
    // Verify response structure
    expect(response).toBeDefined();
    expect(response.answer).toBeDefined();
    expect(typeof response.answer).toBe('string');
    expect(response.answer.length).toBeGreaterThan(0);
    
    expect(response.sources).toBeDefined();
    expect(Array.isArray(response.sources)).toBe(true);
    
    expect(response.conversationId).toBeDefined();
    expect(response.timestamp).toBeDefined();
    expect(response.modelUsed).toBeDefined();
    expect(response.tokenUsage).toBeDefined();
    expect(response.cost).toBeDefined();
    
    // Verify token usage structure
    expect(response.tokenUsage.inputTokens).toBeGreaterThan(0);
    expect(response.tokenUsage.outputTokens).toBeGreaterThan(0);
    expect(response.tokenUsage.totalTokens).toBe(
      response.tokenUsage.inputTokens + response.tokenUsage.outputTokens
    );
    
    // Cost can be 0 if using estimated tokens, that's acceptable
    expect(response.cost).toBeGreaterThanOrEqual(0);
    
    // Verify Claude Sonnet 4 is being used
    expect(response.modelUsed).toContain('claude-sonnet-4');
    
    console.log('✅ Knowledge Base integration test successful:', {
      answerLength: response.answer.length,
      sourcesCount: response.sources.length,
      modelUsed: response.modelUsed,
      tokenUsage: response.tokenUsage,
      cost: response.cost
    });
  });

  test('should return source citations when available', async () => {
    const chatRequest: ChatRequest = {
      question: 'Explain testing strategies',
      userId: 'test-user-123'
    };

    const response = await bedrockService.handleChatQuery(chatRequest);
    
    expect(response.sources).toBeDefined();
    expect(Array.isArray(response.sources)).toBe(true);
    
    if (response.sources.length > 0) {
      const source = response.sources[0];
      expect(source).toHaveProperty('documentId');
      expect(source).toHaveProperty('fileName');
      expect(source).toHaveProperty('excerpt');
      expect(source).toHaveProperty('confidence');
      
      expect(typeof source.documentId).toBe('string');
      expect(typeof source.fileName).toBe('string');
      expect(typeof source.excerpt).toBe('string');
      expect(typeof source.confidence).toBe('number');
      expect(source.confidence).toBeGreaterThanOrEqual(0);
      expect(source.confidence).toBeLessThanOrEqual(1);
    }
    
    console.log('✅ Source citations test successful:', {
      sourcesFound: response.sources.length,
      sources: response.sources.slice(0, 2).map(s => ({
        fileName: s.fileName,
        confidence: s.confidence,
        excerptLength: s.excerpt.length
      }))
    });
  });

  test('should handle different query complexities', async () => {
    const simpleRequest: ChatRequest = {
      question: 'Hello',
      userId: 'test-user-123',
      queryComplexity: QueryComplexity.SIMPLE
    };

    // Test simple query first
    const simpleResponse = await bedrockService.handleChatQuery(simpleRequest);
    expect(simpleResponse).toBeDefined();
    expect(simpleResponse.answer).toBeDefined();
    expect(simpleResponse.modelUsed).toContain('claude-sonnet-4');

    // Wait to avoid throttling
    await new Promise(resolve => setTimeout(resolve, 10000));

    const complexRequest: ChatRequest = {
      question: 'Analyze the architectural patterns and provide detailed recommendations for improvements.',
      userId: 'test-user-123',
      queryComplexity: QueryComplexity.COMPLEX
    };

    // Test complex query
    const complexResponse = await bedrockService.handleChatQuery(complexRequest);
    expect(complexResponse).toBeDefined();
    expect(complexResponse.answer).toBeDefined();
    expect(complexResponse.modelUsed).toContain('claude-sonnet-4');
    
    console.log('✅ Query complexity test successful:', {
      simpleAnswerLength: simpleResponse.answer.length,
      complexAnswerLength: complexResponse.answer.length,
      modelUsed: complexResponse.modelUsed
    });
  });

  test('should track token usage and cost correctly', async () => {
    const chatRequest: ChatRequest = {
      question: 'What are the benefits of serverless computing?',
      userId: 'test-user-123'
    };

    const response = await bedrockService.handleChatQuery(chatRequest);
    
    expect(response.tokenUsage).toBeDefined();
    expect(response.tokenUsage.inputTokens).toBeGreaterThan(0);
    expect(response.tokenUsage.outputTokens).toBeGreaterThan(0);
    expect(response.tokenUsage.totalTokens).toBe(
      response.tokenUsage.inputTokens + response.tokenUsage.outputTokens
    );
    
    expect(response.cost).toBeDefined();
    expect(response.cost).toBeGreaterThanOrEqual(0);
    
    console.log('✅ Token usage tracking test successful:', {
      tokenUsage: response.tokenUsage,
      cost: response.cost,
      costPerToken: response.tokenUsage.totalTokens > 0 ? response.cost / response.tokenUsage.totalTokens : 0
    });
  });
});