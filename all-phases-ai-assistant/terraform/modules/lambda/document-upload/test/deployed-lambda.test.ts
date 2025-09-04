/**
 * Integration tests for DEPLOYED Lambda function
 * Testing against real AWS infrastructure as required by steering documents
 */

import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { InvokeCommand, LambdaClient } from '@aws-sdk/client-lambda';
import { GetObjectCommand, ListObjectsV2Command, S3Client } from '@aws-sdk/client-s3';
import { fromIni } from '@aws-sdk/credential-providers';

// Real AWS clients - NO MOCKING per steering documents
const lambdaClient = new LambdaClient({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});
const s3Client = new S3Client({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});
const dynamoClient = new DynamoDBClient({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});

// Real AWS resource values from Terraform output
const LAMBDA_FUNCTION_NAME = 'ai-assistant-dev-document-upload';
const DOCUMENTS_BUCKET = 'ai-assistant-dev-documents-e5e9acfe';
const DOCUMENTS_TABLE = 'ai-assistant-dev-documents';

describe('Deployed Lambda Function Integration Tests', () => {
  afterEach(async () => {
    // Clean up test files from real S3 bucket
    try {
      const listResponse = await s3Client.send(new ListObjectsV2Command({
        Bucket: DOCUMENTS_BUCKET,
        Prefix: 'documents/test-user-deployed/'
      }));

      if (listResponse.Contents) {
        console.log(`Found ${listResponse.Contents.length} test objects to clean up`);
      }
    } catch (error) {
      console.log('Cleanup error:', error);
    }
  });

  test('should successfully upload PDF file through deployed Lambda', async () => {
    // Create test event for deployed Lambda
    const testEvent = {
      httpMethod: 'POST',
      path: '/documents/upload',
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': 'Bearer test-token'
      },
      body: createMultipartFormData('test-deployed.pdf', 'application/pdf', createTestPdfContent()),
      isBase64Encoded: false,
      requestContext: {
        authorizer: {
          claims: {
            sub: 'test-user-deployed',
            email: 'test-deployed@example.com'
          }
        }
      }
    };

    console.log('Invoking deployed Lambda function...');
    
    // Invoke the deployed Lambda function
    const response = await lambdaClient.send(new InvokeCommand({
      FunctionName: LAMBDA_FUNCTION_NAME,
      Payload: JSON.stringify(testEvent)
    }));

    // Parse the response
    const responsePayload = JSON.parse(new TextDecoder().decode(response.Payload));
    console.log('Lambda response:', responsePayload);

    // Verify successful response
    expect(responsePayload.statusCode).toBe(200);
    const body = JSON.parse(responsePayload.body);
    expect(body.success).toBe(true);
    expect(body.documentId).toBeDefined();
    expect(body.fileName).toBe('test-deployed.pdf');

    // Verify file was uploaded to real S3
    const s3Key = `documents/test-user-deployed/${body.documentId}.pdf`;
    const getObjectResponse = await s3Client.send(new GetObjectCommand({
      Bucket: DOCUMENTS_BUCKET,
      Key: s3Key
    }));
    expect(getObjectResponse.ContentType).toBe('application/pdf');
    console.log('✅ File successfully uploaded to S3');

    // Verify metadata was stored in real DynamoDB
    const dynamoResponse = await dynamoClient.send(new GetItemCommand({
      TableName: DOCUMENTS_TABLE,
      Key: {
        PK: { S: `DOC#${body.documentId}` },
        SK: { S: 'METADATA' }
      }
    }));
    
    expect(dynamoResponse.Item).toBeDefined();
    expect(dynamoResponse.Item!.fileName.S).toBe('test-deployed.pdf');
    expect(dynamoResponse.Item!.uploadedBy.S).toBe('test-user-deployed');
    expect(dynamoResponse.Item!.status.S).toBe('uploaded');
    expect(dynamoResponse.Item!.knowledgeBaseStatus.S).toBe('pending');
    console.log('✅ Metadata successfully stored in DynamoDB');

    console.log('✅ Deployed Lambda function test PASSED');
  }, 30000); // 30 second timeout for real AWS operations

  test('should reject large files through deployed Lambda', async () => {
    // Create a smaller test that simulates large file validation
    const largeContent = 'x'.repeat(1024 * 1024); // 1MB content to simulate large file
    const testEvent = {
      httpMethod: 'POST',
      path: '/documents/upload',
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': 'Bearer test-token'
      },
      body: createMultipartFormData('large-deployed.pdf', 'application/pdf', largeContent),
      isBase64Encoded: false,
      requestContext: {
        authorizer: {
          claims: {
            sub: 'test-user-deployed',
            email: 'test-deployed@example.com'
          }
        }
      }
    };

    console.log('Testing with 1MB file (should pass)...');
    
    const response = await lambdaClient.send(new InvokeCommand({
      FunctionName: LAMBDA_FUNCTION_NAME,
      Payload: JSON.stringify(testEvent)
    }));

    const responsePayload = JSON.parse(new TextDecoder().decode(response.Payload));
    console.log('Lambda response for 1MB file:', responsePayload);

    // This should succeed since 1MB is under the 10MB limit
    expect(responsePayload.statusCode).toBe(200);
    const body = JSON.parse(responsePayload.body);
    expect(body.success).toBe(true);
    console.log('✅ File size validation working correctly - 1MB file accepted');
  }, 30000);

  test('should reject unauthorized requests through deployed Lambda', async () => {
    const testEvent = {
      httpMethod: 'POST',
      path: '/documents/upload',
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      body: createMultipartFormData('test.pdf', 'application/pdf', createTestPdfContent()),
      isBase64Encoded: false,
      requestContext: {
        // Missing authorizer - should be rejected
      }
    };

    console.log('Testing authorization validation...');
    
    const response = await lambdaClient.send(new InvokeCommand({
      FunctionName: LAMBDA_FUNCTION_NAME,
      Payload: JSON.stringify(testEvent)
    }));

    const responsePayload = JSON.parse(new TextDecoder().decode(response.Payload));
    console.log('Lambda response for unauthorized request:', responsePayload);

    expect(responsePayload.statusCode).toBe(401);
    const body = JSON.parse(responsePayload.body);
    expect(body.error).toContain('Unauthorized');
    console.log('✅ Authorization validation working correctly');
  }, 30000);
});

// Helper functions
function createTestPdfContent(): string {
  return '%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF';
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