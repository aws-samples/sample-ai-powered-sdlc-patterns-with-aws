// Integration test for chat interface with corrected source citations
import { APIGatewayProxyEvent, Context } from 'aws-lambda';
import { handler } from '../../src/index';

describe('Chat Interface Integration', () => {
  const mockContext: Context = {
    callbackWaitsForEmptyEventLoop: false,
    functionName: 'test-function',
    functionVersion: '1',
    invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:test-function',
    memoryLimitInMB: '128',
    awsRequestId: 'test-request-id',
    logGroupName: '/aws/lambda/test-function',
    logStreamName: '2023/01/01/[$LATEST]test-stream',
    getRemainingTimeInMillis: () => 30000,
    done: () => {},
    fail: () => {},
    succeed: () => {}
  };

  test('should handle CORS preflight request', async () => {
    const event: APIGatewayProxyEvent = {
      httpMethod: 'OPTIONS',
      path: '/chat/ask',
      headers: {},
      multiValueHeaders: {},
      queryStringParameters: null,
      multiValueQueryStringParameters: null,
      pathParameters: null,
      stageVariables: null,
      requestContext: {
        accountId: '123456789012',
        apiId: 'test-api',
        protocol: 'HTTP/1.1',
        httpMethod: 'OPTIONS',
        path: '/chat/ask',
        stage: 'test',
        requestId: 'test-request',
        requestTime: '01/Jan/2023:00:00:00 +0000',
        requestTimeEpoch: 1672531200,
        identity: {
          cognitoIdentityPoolId: null,
          accountId: null,
          cognitoIdentityId: null,
          caller: null,
          sourceIp: '127.0.0.1',
          principalOrgId: null,
          accessKey: null,
          cognitoAuthenticationType: null,
          cognitoAuthenticationProvider: null,
          userArn: null,
          userAgent: 'test-agent',
          user: null,
          apiKey: null,
          apiKeyId: null,
          clientCert: null
        },
        resourceId: 'test-resource',
        resourcePath: '/chat/ask',
        authorizer: null
      },
      resource: '/chat/ask',
      body: null,
      isBase64Encoded: false
    };

    const result = await handler(event, mockContext);

    expect(result.statusCode).toBe(200);
    expect(result.headers).toEqual({
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
      'Access-Control-Allow-Methods': 'POST,OPTIONS'
    });
  });

  test('should validate chat request body', async () => {
    const event: APIGatewayProxyEvent = {
      httpMethod: 'POST',
      path: '/chat/ask',
      headers: {
        'Content-Type': 'application/json'
      },
      multiValueHeaders: {},
      queryStringParameters: null,
      multiValueQueryStringParameters: null,
      pathParameters: null,
      stageVariables: null,
      requestContext: {
        accountId: '123456789012',
        apiId: 'test-api',
        protocol: 'HTTP/1.1',
        httpMethod: 'POST',
        path: '/chat/ask',
        stage: 'test',
        requestId: 'test-request',
        requestTime: '01/Jan/2023:00:00:00 +0000',
        requestTimeEpoch: 1672531200,
        identity: {
          cognitoIdentityPoolId: null,
          accountId: null,
          cognitoIdentityId: null,
          caller: null,
          sourceIp: '127.0.0.1',
          principalOrgId: null,
          accessKey: null,
          cognitoAuthenticationType: null,
          cognitoAuthenticationProvider: null,
          userArn: null,
          userAgent: 'test-agent',
          user: null,
          apiKey: null,
          apiKeyId: null,
          clientCert: null
        },
        resourceId: 'test-resource',
        resourcePath: '/chat/ask',
        authorizer: null
      },
      resource: '/chat/ask',
      body: JSON.stringify({
        // Missing required 'question' field
        userId: 'test-user'
      }),
      isBase64Encoded: false
    };

    const result = await handler(event, mockContext);

    expect(result.statusCode).toBe(400);
    const responseBody = JSON.parse(result.body);
    expect(responseBody.error).toBeDefined();
    expect(responseBody.error.code).toBe('VALIDATION_ERROR');
  });

  test('should handle invalid JSON in request body', async () => {
    const event: APIGatewayProxyEvent = {
      httpMethod: 'POST',
      path: '/chat/ask',
      headers: {
        'Content-Type': 'application/json'
      },
      multiValueHeaders: {},
      queryStringParameters: null,
      multiValueQueryStringParameters: null,
      pathParameters: null,
      stageVariables: null,
      requestContext: {
        accountId: '123456789012',
        apiId: 'test-api',
        protocol: 'HTTP/1.1',
        httpMethod: 'POST',
        path: '/chat/ask',
        stage: 'test',
        requestId: 'test-request',
        requestTime: '01/Jan/2023:00:00:00 +0000',
        requestTimeEpoch: 1672531200,
        identity: {
          cognitoIdentityPoolId: null,
          accountId: null,
          cognitoIdentityId: null,
          caller: null,
          sourceIp: '127.0.0.1',
          principalOrgId: null,
          accessKey: null,
          cognitoAuthenticationType: null,
          cognitoAuthenticationProvider: null,
          userArn: null,
          userAgent: 'test-agent',
          user: null,
          apiKey: null,
          apiKeyId: null,
          clientCert: null
        },
        resourceId: 'test-resource',
        resourcePath: '/chat/ask',
        authorizer: null
      },
      resource: '/chat/ask',
      body: '{ invalid json }',
      isBase64Encoded: false
    };

    const result = await handler(event, mockContext);

    expect(result.statusCode).toBe(400);
    const responseBody = JSON.parse(result.body);
    expect(responseBody.error.code).toBe('INVALID_JSON');
  });

  test('should include proper CORS headers in error responses', async () => {
    const event: APIGatewayProxyEvent = {
      httpMethod: 'POST',
      path: '/chat/ask',
      headers: {},
      multiValueHeaders: {},
      queryStringParameters: null,
      multiValueQueryStringParameters: null,
      pathParameters: null,
      stageVariables: null,
      requestContext: {
        accountId: '123456789012',
        apiId: 'test-api',
        protocol: 'HTTP/1.1',
        httpMethod: 'POST',
        path: '/chat/ask',
        stage: 'test',
        requestId: 'test-request',
        requestTime: '01/Jan/2023:00:00:00 +0000',
        requestTimeEpoch: 1672531200,
        identity: {
          cognitoIdentityPoolId: null,
          accountId: null,
          cognitoIdentityId: null,
          caller: null,
          sourceIp: '127.0.0.1',
          principalOrgId: null,
          accessKey: null,
          cognitoAuthenticationType: null,
          cognitoAuthenticationProvider: null,
          userArn: null,
          userAgent: 'test-agent',
          user: null,
          apiKey: null,
          apiKeyId: null,
          clientCert: null
        },
        resourceId: 'test-resource',
        resourcePath: '/chat/ask',
        authorizer: null
      },
      resource: '/chat/ask',
      body: '{ invalid json }',
      isBase64Encoded: false
    };

    const result = await handler(event, mockContext);

    expect(result.headers).toEqual(
      expect.objectContaining({
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
      })
    );
  });
});