/**
 * RED Phase: Tests against REAL AWS infrastructure
 * Following steering document requirements - NO MOCKING
 */

import { BedrockAgentClient, ListIngestionJobsCommand } from '@aws-sdk/client-bedrock-agent';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { GetObjectCommand, ListObjectsV2Command, S3Client } from '@aws-sdk/client-s3';
import { fromIni } from '@aws-sdk/credential-providers';
import { APIGatewayProxyEvent, Context } from 'aws-lambda';
import { handler } from '../src/index';

// Real AWS clients - NO MOCKING per steering documents
// Using aidlc_main profile as required by steering documents
const s3Client = new S3Client({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});

const dynamoClient = new DynamoDBClient({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});

const bedrockClient = new BedrockAgentClient({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});

// Real AWS resource values from Terraform output
const DOCUMENTS_BUCKET = 'ai-assistant-dev-documents-e5e9acfe';
const DOCUMENTS_TABLE = 'ai-assistant-dev-documents';
const KNOWLEDGE_BASE_ID = 'PQB7MB5ORO';
const DATA_SOURCE_ID = 'YUAUID9BJN';

describe('Document Upload Lambda - Real AWS Infrastructure Tests', () => {
  let mockEvent: APIGatewayProxyEvent;
  let mockContext: Context;

  beforeEach(() => {
    // Set environment variables for Lambda function
    process.env.DOCUMENTS_BUCKET = DOCUMENTS_BUCKET;
    process.env.DOCUMENTS_TABLE = DOCUMENTS_TABLE;
    process.env.KNOWLEDGE_BASE_ID = KNOWLEDGE_BASE_ID;
    process.env.DATA_SOURCE_ID = DATA_SOURCE_ID;
    process.env.AWS_REGION = 'us-west-2';

    mockEvent = {
      httpMethod: 'POST',
      path: '/documents/upload',
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': 'Bearer mock-jwt-token'
      },
      body: '',
      isBase64Encoded: false,
      requestContext: {
        authorizer: {
          claims: {
            sub: 'test-user-id',
            email: 'test@example.com'
          }
        }
      }
    } as any;

    mockContext = {
      awsRequestId: 'test-request-id',
      functionName: 'document-upload',
      getRemainingTimeInMillis: () => 30000
    } as any;
  });

  afterEach(async () => {
    // Clean up test files from real S3 bucket
    try {
      const listResponse = await s3Client.send(new ListObjectsV2Command({
        Bucket: DOCUMENTS_BUCKET,
        Prefix: 'documents/test-user-id/'
      }));

      if (listResponse.Contents) {
        // Note: In a real implementation, we'd delete test objects
        // For now, we'll leave them as they don't interfere with other tests
        console.log(`Found ${listResponse.Contents.length} test objects to clean up`);
      }
    } catch (error) {
      console.log('Cleanup error (expected in RED phase):', error);
    }
  });

  describe('RED Phase - File Validation Tests (Should Fail)', () => {
    test('should accept PDF files and upload to real S3', async () => {
      // Create a real test PDF file
      const testPdfContent = createTestPdfContent();
      mockEvent.body = createMultipartFormData('test.pdf', 'application/pdf', testPdfContent);
      
      // RED: This will fail because handler is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(200);
      const body = JSON.parse(result.body);
      expect(body.success).toBe(true);
      expect(body.documentId).toBeDefined();
      
      // Verify file was actually uploaded to real S3
      const s3Key = `documents/test-user-id/${body.documentId}.pdf`;
      const getObjectResponse = await s3Client.send(new GetObjectCommand({
        Bucket: DOCUMENTS_BUCKET,
        Key: s3Key
      }));
      expect(getObjectResponse.ContentType).toBe('application/pdf');
    });

    test('should accept DOCX files and store metadata in real DynamoDB', async () => {
      const testDocxContent = createTestDocxContent();
      mockEvent.body = createMultipartFormData('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', testDocxContent);
      
      // RED: This will fail because handler is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(200);
      const body = JSON.parse(result.body);
      
      // Verify metadata was stored in real DynamoDB
      const dynamoResponse = await dynamoClient.send(new GetItemCommand({
        TableName: DOCUMENTS_TABLE,
        Key: {
          PK: { S: `DOC#${body.documentId}` },
          SK: { S: 'METADATA' }
        }
      }));
      
      expect(dynamoResponse.Item).toBeDefined();
      expect(dynamoResponse.Item!.fileName.S).toBe('test.docx');
      expect(dynamoResponse.Item!.uploadedBy.S).toBe('test-user-id');
      expect(dynamoResponse.Item!.status.S).toBe('uploaded');
      expect(dynamoResponse.Item!.knowledgeBaseStatus.S).toBe('pending');
    });

    test('should trigger real Knowledge Base ingestion job', async () => {
      const testTxtContent = 'This is a test document for Knowledge Base ingestion.';
      mockEvent.body = createMultipartFormData('test.txt', 'text/plain', testTxtContent);
      
      // RED: This will fail because handler is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(200);
      
      // Verify ingestion job was started in real Bedrock Knowledge Base
      const ingestionJobs = await bedrockClient.send(new ListIngestionJobsCommand({
        knowledgeBaseId: KNOWLEDGE_BASE_ID,
        dataSourceId: DATA_SOURCE_ID,
        maxResults: 10
      }));
      
      // Should have at least one ingestion job
      expect(ingestionJobs.ingestionJobSummaries).toBeDefined();
      expect(ingestionJobs.ingestionJobSummaries!.length).toBeGreaterThan(0);
      
      // Most recent job should be in STARTING or IN_PROGRESS state
      const latestJob = ingestionJobs.ingestionJobSummaries![0];
      expect(['STARTING', 'IN_PROGRESS'].includes(latestJob.status!)).toBe(true);
    });

    test('should reject files larger than 10MB', async () => {
      // Create a file larger than 10MB
      const largeContent = 'x'.repeat(11 * 1024 * 1024); // 11MB
      mockEvent.body = createMultipartFormData('large.pdf', 'application/pdf', largeContent);
      
      // RED: This will fail because validation is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(400);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('File size exceeds 10MB limit');
    });

    test('should reject unsupported file types', async () => {
      const executableContent = 'fake executable content';
      mockEvent.body = createMultipartFormData('malware.exe', 'application/octet-stream', executableContent);
      
      // RED: This will fail because validation is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(400);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('Unsupported file type');
    });
  });

  describe('RED Phase - Error Handling Tests (Should Fail)', () => {
    test('should handle missing authorization', async () => {
      delete mockEvent.requestContext.authorizer;
      
      // RED: This will fail because auth validation is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(401);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('Unauthorized');
    });

    test('should handle malformed multipart data', async () => {
      mockEvent.body = 'invalid multipart data';
      
      // RED: This will fail because parsing is not implemented yet
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(400);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('Invalid file upload');
    });
  });
});

// Helper functions to create test file content
function createTestPdfContent(): string {
  // Minimal PDF header - enough to be recognized as PDF
  return '%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF';
}

function createTestDocxContent(): string {
  // Minimal DOCX content (ZIP file with basic structure)
  return 'PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00test docx content';
}

function createMultipartFormData(fileName: string, contentType: string, content: string): string {
  const boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW';
  
  return [
    `--${boundary}`,
    `Content-Disposition: form-data; name="file"; filename="${fileName}"`,
    `Content-Type: ${contentType}`,
    '',
    content,
    `--${boundary}--`
  ].join('\r\n');
}