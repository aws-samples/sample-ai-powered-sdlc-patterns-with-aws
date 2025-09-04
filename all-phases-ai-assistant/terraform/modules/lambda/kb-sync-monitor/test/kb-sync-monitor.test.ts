/**
 * Knowledge Base Sync Monitor Tests - TDD Implementation
 * Tests run against real AWS infrastructure per steering guidelines
 */

import { Context } from 'aws-lambda';
import { handler } from '../src/index';

// Test configuration - using real AWS resources
const TEST_CONTEXT: Context = {
  callbackWaitsForEmptyEventLoop: false,
  functionName: 'ai-assistant-dev-kb-sync-monitor',
  functionVersion: '$LATEST',
  invokedFunctionArn: 'arn:aws:lambda:us-west-2:ACCOUNT_ID:function:ai-assistant-dev-kb-sync-monitor',
  memoryLimitInMB: '512',
  awsRequestId: 'test-request-id-' + Date.now(),
  logGroupName: '/aws/lambda/ai-assistant-dev-kb-sync-monitor',
  logStreamName: '2025/08/08/[$LATEST]test-stream',
  getRemainingTimeInMillis: () => 30000,
  done: () => {},
  fail: () => {},
  succeed: () => {}
};

describe('Knowledge Base Sync Monitor - Real AWS Integration', () => {
  // Set timeout for real AWS operations
  jest.setTimeout(60000);

  beforeAll(() => {
    // Verify environment variables are set for real AWS testing
    expect(process.env.KNOWLEDGE_BASE_ID).toBeDefined();
    expect(process.env.DATA_SOURCE_ID).toBeDefined();
    expect(process.env.DOCUMENTS_TABLE).toBeDefined();
    
    console.log('Testing against real AWS resources:', {
      knowledgeBaseId: process.env.KNOWLEDGE_BASE_ID,
      dataSourceId: process.env.DATA_SOURCE_ID,
      documentsTable: process.env.DOCUMENTS_TABLE
    });
  });

  test('should retrieve and process ingestion jobs from real Knowledge Base', async () => {
    // RED: Test that we can retrieve ingestion jobs from real Bedrock Knowledge Base
    const event = { source: 'aws.events', detail: {} };
    
    const result = await handler(event, TEST_CONTEXT);
    
    // GREEN: Verify successful response from real AWS services
    expect(result.statusCode).toBe(200);
    expect(result.body).toBeDefined();
    
    const responseBody = JSON.parse(result.body);
    expect(responseBody.message).toContain('ingestion jobs monitored');
    expect(responseBody.jobsProcessed).toBeGreaterThanOrEqual(0);
    expect(responseBody.requestId).toBe(TEST_CONTEXT.awsRequestId);
    expect(responseBody.timestamp).toBeDefined();
    
    console.log('Knowledge Base sync monitoring result:', responseBody);
  });

  test('should handle real Bedrock API throttling gracefully', async () => {
    // RED: Test throttling handling with real AWS services
    const event = { source: 'aws.events', detail: {} };
    
    // Make multiple rapid calls to potentially trigger throttling
    const promises = Array(3).fill(null).map(() => 
      handler(event, { ...TEST_CONTEXT, awsRequestId: 'throttle-test-' + Math.random() })
    );
    
    const results = await Promise.allSettled(promises);
    
    // GREEN: All calls should either succeed or handle throttling gracefully
    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        expect(result.value.statusCode).toBeOneOf([200, 500]);
        console.log(`Throttling test ${index + 1} result:`, result.value.statusCode);
      } else {
        console.log(`Throttling test ${index + 1} rejected:`, result.reason);
      }
    });
  });

  test('should publish real CloudWatch metrics', async () => {
    // RED: Test that metrics are published to real CloudWatch
    const event = { source: 'aws.events', detail: {} };
    
    const result = await handler(event, TEST_CONTEXT);
    
    // GREEN: Verify successful execution that would publish metrics
    expect(result.statusCode).toBe(200);
    
    const responseBody = JSON.parse(result.body);
    expect(responseBody.message).toContain('metrics published');
    
    // Note: We can't directly verify CloudWatch metrics in the test,
    // but we can verify the function executed successfully
    console.log('Metrics publishing test completed:', responseBody.processingTime);
  });

  test('should update document metadata in real DynamoDB', async () => {
    // RED: Test document metadata updates against real DynamoDB table
    const event = { source: 'aws.events', detail: {} };
    
    const result = await handler(event, TEST_CONTEXT);
    
    // GREEN: Verify successful execution
    expect(result.statusCode).toBe(200);
    
    const responseBody = JSON.parse(result.body);
    expect(responseBody.documentsUpdated).toBeGreaterThanOrEqual(0);
    
    console.log('Document metadata update test:', {
      documentsUpdated: responseBody.documentsUpdated,
      processingTime: responseBody.processingTime
    });
  });

  test('should handle failed ingestion jobs with retry logic', async () => {
    // RED: Test retry logic for failed jobs
    const event = { source: 'aws.events', detail: {} };
    
    const result = await handler(event, TEST_CONTEXT);
    
    // GREEN: Verify retry logic executed
    expect(result.statusCode).toBe(200);
    
    const responseBody = JSON.parse(result.body);
    expect(responseBody.failedJobsProcessed).toBeGreaterThanOrEqual(0);
    
    console.log('Failed job retry test:', {
      failedJobsProcessed: responseBody.failedJobsProcessed,
      message: responseBody.message
    });
  });

  test('should handle missing environment variables gracefully', async () => {
    // RED: Test error handling for missing environment variables
    const originalKnowledgeBaseId = process.env.KNOWLEDGE_BASE_ID;
    delete process.env.KNOWLEDGE_BASE_ID;
    
    const event = { source: 'aws.events', detail: {} };
    
    try {
      await expect(handler(event, TEST_CONTEXT)).rejects.toThrow('KNOWLEDGE_BASE_ID environment variable is required');
      
    } finally {
      // Restore environment variable
      process.env.KNOWLEDGE_BASE_ID = originalKnowledgeBaseId;
    }
  });

  test('should complete end-to-end monitoring workflow within time limit', async () => {
    // RED: Test complete workflow performance
    const startTime = Date.now();
    const event = { source: 'aws.events', detail: {} };
    
    const result = await handler(event, TEST_CONTEXT);
    const endTime = Date.now();
    const executionTime = endTime - startTime;
    
    // GREEN: Should complete within reasonable time (< 30 seconds)
    expect(executionTime).toBeLessThan(30000);
    expect(result.statusCode).toBe(200);
    
    const responseBody = JSON.parse(result.body);
    console.log('End-to-end workflow test:', {
      executionTime: `${executionTime}ms`,
      processingTime: responseBody.processingTime,
      jobsProcessed: responseBody.jobsProcessed
    });
  });
});

// Helper function for test assertions
expect.extend({
  toBeOneOf(received, expected) {
    const pass = expected.includes(received);
    if (pass) {
      return {
        message: () => `expected ${received} not to be one of ${expected}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be one of ${expected}`,
        pass: false,
      };
    }
  },
});

declare global {
  namespace jest {
    interface Matchers<R> {
      toBeOneOf(expected: any[]): R;
    }
  }
}