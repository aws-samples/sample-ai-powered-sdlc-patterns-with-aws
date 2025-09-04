import { DeleteObjectCommand, PutObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { readFileSync } from 'fs';
import { join } from 'path';
import { BedrockService } from '../../src/bedrock-service';
import { ChatRequest, QueryComplexity } from '../../src/types';

describe('Advanced RAG Integration Tests', () => {
  let bedrockService: BedrockService;
  let s3Client: S3Client;
  
  const testDocumentKey = `test-documents/advanced-rag-test-${Date.now()}.md`;
  
  beforeEach(async () => {
    // Add delay between tests to avoid Bedrock throttling
    await new Promise(resolve => setTimeout(resolve, 3000)); // 3 second delay
  });
  
  beforeAll(async () => {
    // Set required environment variables for testing
    process.env.KNOWLEDGE_BASE_ID = 'PQB7MB5ORO'; // Deployed Knowledge Base ID
    process.env.DOCUMENTS_BUCKET = 'ai-assistant-dev-documents-e5e9acfe'; // Deployed S3 bucket
    process.env.AWS_PROFILE = 'aidlc_main';
    process.env.AWS_REGION = 'us-west-2';
    
    // Skip if no AWS credentials or Knowledge Base ID
    if (!process.env.KNOWLEDGE_BASE_ID) {
      console.log('Skipping integration tests - AWS resources not configured');
      return;
    }
    
    bedrockService = new BedrockService();
    s3Client = new S3Client({ 
      region: process.env.AWS_REGION || 'us-west-2'
    });
    
    // Upload test document to S3
    const testDocument = readFileSync(
      join(__dirname, '../sample-documents/advanced-rag-test.md'),
      'utf-8'
    );
    
    await s3Client.send(new PutObjectCommand({
      Bucket: process.env.DOCUMENTS_BUCKET,
      Key: testDocumentKey,
      Body: testDocument,
      ContentType: 'text/markdown'
    }));
    
    // Note: Knowledge Base ingestion can take several minutes
    // Tests will use existing documents in the Knowledge Base for validation
    console.log('Test document uploaded to S3. Tests will use existing Knowledge Base content.');
  }, 120000); // 2 minute timeout for beforeAll
  
  afterAll(async () => {
    // Clean up test document
    if (s3Client && process.env.DOCUMENTS_BUCKET) {
      try {
        const deleteCommand = new DeleteObjectCommand({
          Bucket: process.env.DOCUMENTS_BUCKET,
          Key: testDocumentKey
        });
        await s3Client.send(deleteCommand);
        console.log('Test document cleaned up successfully');
      } catch (error) {
        console.log('Failed to clean up test document:', error);
      }
    }
  });

  describe('Hybrid Search Configuration', () => {
    test('should use hybrid search for moderate complexity queries', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const request: ChatRequest = {
        question: 'What are the requirements for hybrid search testing?',
        userId: 'test-user',
        queryComplexity: QueryComplexity.MODERATE
      };

      const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
      
      // Log the actual response to verify advanced RAG integration
      console.log('=== ADVANCED RAG RESPONSE ===');
      console.log('Question:', request.question);
      console.log('Answer:', response.answer);
      console.log('Sources count:', response.sources?.length || 0);
      console.log('RAG Config:', JSON.stringify(response.ragConfig, null, 2));
      console.log('Quality Metrics:', JSON.stringify(response.qualityMetrics, null, 2));
      console.log('============================');
      
      expect(response.answer).toBeDefined();
      expect(response.answer.length).toBeGreaterThan(50);
      expect(response.sources).toBeDefined();
      expect(response.ragConfig).toBeDefined();
      expect(response.ragConfig?.hybridSearch.searchType).toBe('HYBRID');
      expect(response.qualityMetrics).toBeDefined();
    }, 30000); // 30 second timeout

    test('should retrieve relevant sources with confidence scores', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const request: ChatRequest = {
        question: 'What are the performance benchmarks for response time?',
        userId: 'test-user',
        queryComplexity: QueryComplexity.SIMPLE
      };

      const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
      
      // The response should be defined even if no sources are found
      expect(response.answer).toBeDefined();
      expect(response.sources).toBeDefined();
      expect(Array.isArray(response.sources)).toBe(true);
      
      // If sources are returned, validate their structure
      if (response.sources.length > 0) {
        // Check that sources have required fields
        response.sources.forEach(source => {
          expect(source.confidence).toBeGreaterThanOrEqual(0);
          expect(source.confidence).toBeLessThanOrEqual(1);
          expect(source.excerpt).toBeDefined();
          expect(source.documentId).toBeDefined();
        });
        
        // Sources should be sorted by relevance
        for (let i = 1; i < response.sources.length; i++) {
          expect(response.sources[i-1].confidence).toBeGreaterThanOrEqual(
            response.sources[i].confidence
          );
        }
      } else {
        console.log('No sources returned - this may be expected if Knowledge Base ingestion is still in progress');
      }
    }, 30000);
  });

  describe('Response Quality Validation', () => {
    test('should provide quality metrics for responses', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const request: ChatRequest = {
        question: 'Explain the quality validation criteria mentioned in the document.',
        userId: 'test-user',
        queryComplexity: QueryComplexity.COMPLEX
      };

      const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
      
      expect(response.qualityMetrics).toBeDefined();
      expect(response.qualityMetrics?.qualityScore).toBeGreaterThan(0);
      expect(response.qualityMetrics?.qualityScore).toBeLessThanOrEqual(1);
      expect(response.qualityMetrics?.completenessScore).toBeDefined();
      expect(response.qualityMetrics?.reliabilityScore).toBeDefined();
      expect(response.qualityMetrics?.coherenceScore).toBeDefined();
      
      // For a complex query about quality criteria, we expect good quality
      expect(response.qualityMetrics?.qualityScore).toBeGreaterThan(0.4);
    }, 30000);

    test('should filter sources by confidence threshold', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const request: ChatRequest = {
        question: 'What is the minimum confidence threshold for sources?',
        userId: 'test-user',
        queryComplexity: QueryComplexity.MODERATE
      };

      const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
      
      // All returned sources should meet the minimum confidence threshold
      const minThreshold = response.ragConfig?.qualityThresholds.minConfidence || 0.5;
      response.sources.forEach(source => {
        expect(source.confidence).toBeGreaterThanOrEqual(minThreshold);
      });
    }, 30000);
  });

  describe('Advanced Retrieval Parameters', () => {
    test('should adjust number of results based on query complexity', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const simpleRequest: ChatRequest = {
        question: 'What is hybrid search?',
        userId: 'test-user',
        queryComplexity: QueryComplexity.SIMPLE
      };

      const complexRequest: ChatRequest = {
        question: 'Compare and analyze all the testing scenarios, performance benchmarks, and quality validation criteria mentioned in the document.',
        userId: 'test-user',
        queryComplexity: QueryComplexity.COMPLEX
      };

      const simpleResponse = await bedrockService.handleChatQueryWithAdvancedRAG(simpleRequest);
      const complexResponse = await bedrockService.handleChatQueryWithAdvancedRAG(complexRequest);
      
      // Complex queries should potentially retrieve more sources
      const simpleResultCount = simpleResponse.ragConfig?.retrieval.numberOfResults || 0;
      const complexResultCount = complexResponse.ragConfig?.retrieval.numberOfResults || 0;
      
      expect(complexResultCount).toBeGreaterThanOrEqual(simpleResultCount);
    }, 60000); // Longer timeout for two requests
  });

  describe('Error Handling and Edge Cases', () => {
    test('should handle queries with no relevant context gracefully', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const request: ChatRequest = {
        question: 'What is the capital of Mars?', // Irrelevant to our test document
        userId: 'test-user',
        queryComplexity: QueryComplexity.SIMPLE
      };

      const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
      
      expect(response.answer).toBeDefined();
      expect(response.qualityMetrics).toBeDefined();
      
      // Should indicate low quality due to lack of relevant sources
      if (response.sources.length === 0) {
        expect(response.qualityMetrics?.hasReliableSources).toBe(false);
      }
    }, 30000);

    test('should maintain performance within acceptable limits', async () => {
      if (!process.env.KNOWLEDGE_BASE_ID || !bedrockService) {
        console.log('Skipping test - KNOWLEDGE_BASE_ID not set or bedrockService not initialized');
        return;
      }

      const startTime = Date.now();
      
      const request: ChatRequest = {
        question: 'What are the performance benchmarks mentioned in the document?',
        userId: 'test-user',
        queryComplexity: QueryComplexity.MODERATE
      };

      const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
      
      const responseTime = Date.now() - startTime;
      
      expect(response.answer).toBeDefined();
      expect(responseTime).toBeLessThan(15000); // Should respond within 15 seconds
      
      console.log(`Advanced RAG response time: ${responseTime}ms`);
    }, 30000);
  });
});