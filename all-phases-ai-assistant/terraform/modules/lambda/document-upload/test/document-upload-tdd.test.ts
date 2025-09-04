/**
 * RED Phase: Failing tests for document upload functionality
 * Following TDD approach from steering documents - tests against REAL AWS infrastructure
 */

import { BedrockAgentClient, ListIngestionJobsCommand } from '@aws-sdk/client-bedrock-agent';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { GetObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { fromIni } from '@aws-sdk/credential-providers';
import { APIGatewayProxyEvent, Context } from 'aws-lambda';

// Real AWS clients - NO MOCKING per steering documents
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

// Real AWS resource values from deployed infrastructure
const DOCUMENTS_BUCKET = 'ai-assistant-dev-documents-e5e9acfe';
const DOCUMENTS_TABLE = 'ai-assistant-dev-documents';
const KNOWLEDGE_BASE_ID = 'PQB7MB5ORO';
const DATA_SOURCE_ID = 'YUAUID9BJN';

describe('Document Upload TDD - RED Phase (Should Fail)', () => {
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

  describe('RED: Document Upload to S3 with Proper Metadata', () => {
    test('should upload PDF file to real S3 with correct metadata', async () => {
      // RED: This test will fail because handler doesn't exist yet
      const { handler } = await import('../src/index');
      
      const testPdfContent = createTestPdfContent();
      mockEvent.body = createMultipartFormData('test.pdf', 'application/pdf', testPdfContent);
      
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(200);
      const body = JSON.parse(result.body);
      expect(body.success).toBe(true);
      expect(body.documentId).toBeDefined();
      
      // Verify file was uploaded to real S3 with proper metadata
      const s3Key = `documents/test-user-id/${body.documentId}.pdf`;
      const getObjectResponse = await s3Client.send(new GetObjectCommand({
        Bucket: DOCUMENTS_BUCKET,
        Key: s3Key
      }));
      
      expect(getObjectResponse.ContentType).toBe('application/pdf');
      expect(getObjectResponse.Metadata?.['uploaded-by']).toBe('test-user-id');
      expect(getObjectResponse.Metadata?.['original-name']).toBe('test.pdf');
    });

    test('should upload DOCX file to real S3', async () => {
      // RED: This test will fail because handler doesn't exist yet
      const { handler } = await import('../src/index');
      
      const testDocxContent = createTestDocxContent();
      mockEvent.body = createMultipartFormData('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', testDocxContent);
      
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(200);
      const body = JSON.parse(result.body);
      
      // Verify file was uploaded to real S3
      const s3Key = `documents/test-user-id/${body.documentId}.docx`;
      const getObjectResponse = await s3Client.send(new GetObjectCommand({
        Bucket: DOCUMENTS_BUCKET,
        Key: s3Key
      }));
      
      expect(getObjectResponse.ContentType).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    });
  });

  describe('RED: Knowledge Base Sync Triggering', () => {
    test('should trigger Knowledge Base ingestion job after upload', async () => {
      // RED: This test will fail because handler doesn't exist yet
      const { handler } = await import('../src/index');
      
      const testTxtContent = 'This is a test document for Knowledge Base ingestion.';
      mockEvent.body = createMultipartFormData('test.txt', 'text/plain', testTxtContent);
      
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(200);
      
      // Verify ingestion job was started in real Bedrock Knowledge Base
      const ingestionJobs = await bedrockClient.send(new ListIngestionJobsCommand({
        knowledgeBaseId: KNOWLEDGE_BASE_ID,
        dataSourceId: DATA_SOURCE_ID,
        maxResults: 10
      }));
      
      expect(ingestionJobs.ingestionJobSummaries).toBeDefined();
      expect(ingestionJobs.ingestionJobSummaries!.length).toBeGreaterThan(0);
      
      // Most recent job should be in STARTING or IN_PROGRESS state
      const latestJob = ingestionJobs.ingestionJobSummaries![0];
      expect(['STARTING', 'IN_PROGRESS'].includes(latestJob.status!)).toBe(true);
    });
  });

  describe('RED: File Validation and Error Handling', () => {
    test('should reject files larger than 10MB', async () => {
      // RED: This test will fail because validation doesn't exist yet
      const { handler } = await import('../src/index');
      
      const largeContent = 'x'.repeat(11 * 1024 * 1024); // 11MB
      mockEvent.body = createMultipartFormData('large.pdf', 'application/pdf', largeContent);
      
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(400);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('File size exceeds 10MB limit');
    });

    test('should reject unsupported file types', async () => {
      // RED: This test will fail because validation doesn't exist yet
      const { handler } = await import('../src/index');
      
      const executableContent = 'fake executable content';
      mockEvent.body = createMultipartFormData('malware.exe', 'application/octet-stream', executableContent);
      
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(400);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('Unsupported file type');
    });

    test('should handle missing authorization', async () => {
      // RED: This test will fail because auth validation doesn't exist yet
      const { handler } = await import('../src/index');
      
      delete mockEvent.requestContext.authorizer;
      
      const result = await handler(mockEvent, mockContext);
      
      expect(result.statusCode).toBe(401);
      const body = JSON.parse(result.body);
      expect(body.error).toContain('Unauthorized');
    });
  });

  describe('RED: DynamoDB Metadata Storage', () => {
    test('should store document metadata in real DynamoDB', async () => {
      // RED: This test will fail because metadata storage doesn't exist yet
      const { handler } = await import('../src/index');
      
      const testPdfContent = createTestPdfContent();
      mockEvent.body = createMultipartFormData('test.pdf', 'application/pdf', testPdfContent);
      
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
      expect(dynamoResponse.Item!.fileName.S).toBe('test.pdf');
      expect(dynamoResponse.Item!.uploadedBy.S).toBe('test-user-id');
      expect(dynamoResponse.Item!.status.S).toBe('uploaded');
      expect(dynamoResponse.Item!.knowledgeBaseStatus.S).toBe('pending');
    });
  });
});

// Helper functions to create test file content
function createTestPdfContent(): string {
  return '%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF';
}

function createTestDocxContent(): string {
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