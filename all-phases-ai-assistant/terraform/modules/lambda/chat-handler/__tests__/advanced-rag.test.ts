import { AdvancedRAGConfig } from '../src/advanced-rag-config';
import { BedrockService } from '../src/bedrock-service';
import { ChatRequest, QueryComplexity } from '../src/types';

describe('Advanced RAG Configuration', () => {
  let bedrockService: BedrockService;
  let ragConfig: AdvancedRAGConfig;

  beforeEach(() => {
    bedrockService = new BedrockService();
    ragConfig = new AdvancedRAGConfig();
  });

  describe('Hybrid Search Configuration', () => {
    test('should configure hybrid search with semantic and keyword weights', async () => {
      const config = ragConfig.getHybridSearchConfig('moderate');
      
      expect(config.searchType).toBe('HYBRID');
      expect(config.semanticWeight).toBeGreaterThan(0);
      expect(config.keywordWeight).toBeGreaterThan(0);
      expect(config.semanticWeight + config.keywordWeight).toBe(1.0);
    });

    test('should adjust search weights based on query complexity', async () => {
      const simpleConfig = ragConfig.getHybridSearchConfig('simple');
      const complexConfig = ragConfig.getHybridSearchConfig('complex');
      
      // Complex queries should favor semantic search more
      expect(complexConfig.semanticWeight).toBeGreaterThan(simpleConfig.semanticWeight);
      expect(complexConfig.keywordWeight).toBeLessThan(simpleConfig.keywordWeight);
    });
  });

  describe('Retrieval Parameters', () => {
    test('should configure number of results based on query complexity', async () => {
      const simpleParams = ragConfig.getRetrievalParams('simple');
      const complexParams = ragConfig.getRetrievalParams('complex');
      
      expect(simpleParams.numberOfResults).toBeLessThanOrEqual(complexParams.numberOfResults);
      expect(simpleParams.numberOfResults).toBeGreaterThan(0);
      expect(complexParams.numberOfResults).toBeLessThanOrEqual(10);
    });

    test('should set appropriate confidence thresholds', async () => {
      const params = ragConfig.getRetrievalParams('moderate');
      
      expect(params.confidenceThreshold).toBeGreaterThan(0);
      expect(params.confidenceThreshold).toBeLessThan(1);
    });
  });

  describe('Source Citation Extraction', () => {
    test('should extract comprehensive source information', async () => {
      const mockResponse: any = {
        output: { text: 'Test response' },
        sessionId: 'test-session',
        $metadata: {},
        citations: [{
          generatedResponsePart: {
            textResponsePart: {
              text: 'Test citation',
              span: { start: 0, end: 10 }
            }
          },
          retrievedReferences: [{
            content: { text: 'Source content excerpt' },
            location: {
              type: 'S3',
              s3Location: { uri: 's3://bucket/document.pdf' }
            },
            metadata: {
              'x-amz-bedrock-kb-source-uri': 'document.pdf',
              score: '0.85',
              'x-amz-bedrock-kb-chunk-id': 'chunk-123'
            }
          }]
        }]
      };

      const sources = ragConfig.extractEnhancedSources(mockResponse);
      
      expect(sources).toHaveLength(1);
      expect(sources[0]).toMatchObject({
        documentId: expect.any(String),
        fileName: 'document.pdf',
        excerpt: 'Source content excerpt',
        confidence: 0.85,
        chunkId: 'chunk-123',
        relevanceScore: expect.any(Number)
      });
    });

    test('should handle missing citation metadata gracefully', async () => {
      const mockResponse: any = {
        output: { text: 'Test response' },
        sessionId: 'test-session',
        $metadata: {},
        citations: [{
          retrievedReferences: [{
            content: { text: 'Source content' },
            location: {
              type: 'S3'
            },
            metadata: {}
          }]
        }]
      };

      const sources = ragConfig.extractEnhancedSources(mockResponse);
      
      expect(sources).toHaveLength(1);
      expect(sources[0].fileName).toBe('Unknown');
      expect(sources[0].confidence).toBe(0);
    });
  });

  describe('Relevance Filtering', () => {
    test('should filter sources by confidence threshold', async () => {
      const sources = [
        { confidence: 0.9, excerpt: 'High confidence source' },
        { confidence: 0.5, excerpt: 'Medium confidence source' },
        { confidence: 0.2, excerpt: 'Low confidence source' }
      ];

      const filtered = ragConfig.filterByRelevance(sources, 0.6);
      
      expect(filtered).toHaveLength(1);
      expect(filtered[0].confidence).toBe(0.9);
    });

    test('should maintain source order by confidence', async () => {
      const sources = [
        { confidence: 0.5, excerpt: 'Medium' },
        { confidence: 0.9, excerpt: 'High' },
        { confidence: 0.7, excerpt: 'Good' }
      ];

      const sorted = ragConfig.sortByRelevance(sources);
      
      expect(sorted[0].confidence).toBe(0.9);
      expect(sorted[1].confidence).toBe(0.7);
      expect(sorted[2].confidence).toBe(0.5);
    });
  });

  describe('Response Quality Validation', () => {
    test('should validate response completeness', async () => {
      const completeResponse = {
        answer: 'This is a comprehensive answer with detailed information.',
        sources: [
          { confidence: 0.8, excerpt: 'Supporting evidence' }
        ]
      };

      const quality = ragConfig.validateResponseQuality(completeResponse);
      
      expect(quality.isComplete).toBe(true);
      expect(quality.hasReliableSources).toBe(true);
      expect(quality.qualityScore).toBeGreaterThan(0.5);
    });

    test('should detect low-quality responses', async () => {
      const poorResponse = {
        answer: 'No information found.',
        sources: []
      };

      const quality = ragConfig.validateResponseQuality(poorResponse);
      
      expect(quality.isComplete).toBe(false);
      expect(quality.hasReliableSources).toBe(false);
      expect(quality.qualityScore).toBeLessThan(0.5);
    });
  });

  describe('Integration with Knowledge Base', () => {
    test('should apply advanced configuration to RetrieveAndGenerate', async () => {
      const request: ChatRequest = {
        question: 'What are the best practices for AWS Lambda?',
        userId: 'test-user',
        queryComplexity: QueryComplexity.MODERATE
      };

      // This test requires real AWS infrastructure
      if (process.env.KNOWLEDGE_BASE_ID) {
        const response = await bedrockService.handleChatQueryWithAdvancedRAG(request);
        
        expect(response.answer).toBeDefined();
        expect(Array.isArray(response.sources)).toBe(true);
        expect(response.ragConfig).toBeDefined();
        expect(response.qualityMetrics).toBeDefined();
      } else {
        console.log('Skipping integration test - KNOWLEDGE_BASE_ID not set');
      }
    });
  });
});