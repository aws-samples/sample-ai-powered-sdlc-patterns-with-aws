/**
 * Debug test for deployed Lambda function
 */

import { InvokeCommand, LambdaClient } from '@aws-sdk/client-lambda';
import { fromIni } from '@aws-sdk/credential-providers';

const lambdaClient = new LambdaClient({ 
  region: 'us-west-2',
  credentials: fromIni({ profile: 'aidlc_main' })
});

const LAMBDA_FUNCTION_NAME = 'ai-assistant-dev-document-upload';

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

function createTestPdfContent(): string {
  return '%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF';
}

describe('Debug Deployed Lambda Function', () => {
  test('should debug Lambda function response', async () => {
    // Create proper multipart form data
    const multipartBody = createMultipartFormData('test-debug.pdf', 'application/pdf', createTestPdfContent());
    
    const testEvent = {
      httpMethod: 'POST',
      path: '/documents/upload',
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': 'Bearer test-token'
      },
      body: multipartBody,
      isBase64Encoded: false,
      requestContext: {
        authorizer: {
          claims: {
            sub: 'debug-user',
            email: 'debug@example.com'
          }
        }
      }
    };

    console.log('Invoking Lambda with debug event...');
    
    const response = await lambdaClient.send(new InvokeCommand({
      FunctionName: LAMBDA_FUNCTION_NAME,
      Payload: JSON.stringify(testEvent),
      LogType: 'Tail'  // This will return logs in the response
    }));

    const responsePayload = JSON.parse(new TextDecoder().decode(response.Payload));
    console.log('Full Lambda response:', JSON.stringify(responsePayload, null, 2));
    
    // Check if there are any logs in the response
    if (response.LogResult) {
      const logs = Buffer.from(response.LogResult, 'base64').toString();
      console.log('Lambda logs:', logs);
    }
  }, 30000);
});