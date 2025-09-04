// Test for source citation extraction from RetrieveAndGenerate response
import { RetrieveAndGenerateCommandOutput } from '@aws-sdk/client-bedrock-agent-runtime';
import { BedrockService } from '../src/bedrock-service';

describe('Source Citation Extraction', () => {
  let bedrockService: BedrockService;

  beforeEach(() => {
    bedrockService = new BedrockService();
  });

  test('should extract sources correctly from RetrieveAndGenerate response', () => {
    // Mock response from Bedrock RetrieveAndGenerate API
    const mockResponse: RetrieveAndGenerateCommandOutput = {
      output: {
        text: 'This is a test response from the AI assistant.'
      },
      citations: [
        {
          generatedResponsePart: {
            textResponsePart: {
              text: 'test response',
              span: {
                start: 10,
                end: 23
              }
            }
          },
          retrievedReferences: [
            {
              content: {
                text: 'This is the source content that was retrieved from the document.'
              },
              location: {
                type: 'S3',
                s3Location: {
                  uri: 's3://test-bucket/documents/test-document.pdf'
                }
              },
              metadata: {
                score: '0.85',
                page: '5'
              }
            }
          ]
        }
      ],
      sessionId: 'test-session-123',
      $metadata: {
        httpStatusCode: 200,
        requestId: 'test-request-id'
      }
    };

    // Use reflection to access private method for testing
    const extractSources = (bedrockService as any).extractSources.bind(bedrockService);
    const sources = extractSources(mockResponse);

    expect(sources).toHaveLength(1);
    expect(sources[0]).toEqual({
      documentId: 's3://test-bucket/documents/test-document.pdf',
      fileName: 'test-document',
      excerpt: 'This is the source content that was retrieved from the document.',
      confidence: 0.85,
      s3Location: 's3://test-bucket/documents/test-document.pdf',
      pageNumber: 5
    });
  });

  test('should handle missing citations gracefully', () => {
    const mockResponse: RetrieveAndGenerateCommandOutput = {
      output: {
        text: 'This is a response without citations.'
      },
      sessionId: 'test-session-456',
      $metadata: {
        httpStatusCode: 200,
        requestId: 'test-request-id-2'
      }
    };

    const extractSources = (bedrockService as any).extractSources.bind(bedrockService);
    const sources = extractSources(mockResponse);

    expect(sources).toHaveLength(0);
  });

  test('should handle multiple citations and references', () => {
    const mockResponse: RetrieveAndGenerateCommandOutput = {
      output: {
        text: 'Response with multiple sources.'
      },
      citations: [
        {
          generatedResponsePart: {
            textResponsePart: {
              text: 'first citation',
              span: { start: 0, end: 14 }
            }
          },
          retrievedReferences: [
            {
              content: { text: 'First source content' },
              location: {
                type: 'S3',
                s3Location: { uri: 's3://bucket/doc1.pdf' }
              },
              metadata: { score: '0.9' }
            },
            {
              content: { text: 'Second source content' },
              location: {
                type: 'S3',
                s3Location: { uri: 's3://bucket/doc2.pdf' }
              },
              metadata: { score: '0.7' }
            }
          ]
        }
      ],
      sessionId: 'test-session-789',
      $metadata: {
        httpStatusCode: 200,
        requestId: 'test-request-id-3'
      }
    };

    const extractSources = (bedrockService as any).extractSources.bind(bedrockService);
    const sources = extractSources(mockResponse);

    expect(sources).toHaveLength(2);
    expect(sources[0].fileName).toBe('doc1');
    expect(sources[1].fileName).toBe('doc2');
    expect(sources[0].confidence).toBe(0.9);
    expect(sources[1].confidence).toBe(0.7);
  });

  test('should handle missing metadata gracefully', () => {
    const mockResponse: RetrieveAndGenerateCommandOutput = {
      output: {
        text: 'Response with minimal metadata.'
      },
      citations: [
        {
          generatedResponsePart: {
            textResponsePart: {
              text: 'citation',
              span: { start: 0, end: 8 }
            }
          },
          retrievedReferences: [
            {
              content: { text: 'Source without metadata' },
              location: {
                type: 'S3',
                s3Location: { uri: 's3://bucket/unknown.txt' }
              }
              // No metadata field
            }
          ]
        }
      ],
      sessionId: 'test-session-000',
      $metadata: {
        httpStatusCode: 200,
        requestId: 'test-request-id-4'
      }
    };

    const extractSources = (bedrockService as any).extractSources.bind(bedrockService);
    const sources = extractSources(mockResponse);

    expect(sources).toHaveLength(1);
    expect(sources[0].confidence).toBe(0.0);
    expect(sources[0].pageNumber).toBeUndefined();
    expect(sources[0].fileName).toBe('unknown');
  });
});