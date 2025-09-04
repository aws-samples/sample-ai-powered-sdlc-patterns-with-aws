// Admin Management Lambda Handler
// Handles Knowledge Base administration endpoints

import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { z } from 'zod';
import {
    cancelIngestionJob,
    getKnowledgeBaseMetrics,
    getKnowledgeBaseStatus,
    listIngestionJobs,
    logAdminAction,
    retryIngestionJob,
    startDataSourceSync
} from './admin-service';
import {
    createCORSConfigFromEnv,
    createErrorResponse,
    createSuccessResponse,
    extractOriginFromEvent,
    handleOPTIONSRequest
} from './cors-utils';

// Enhanced validation schemas for admin operations
const AdminRequestSchema = z.object({
  body: z.string().nullable(),
  headers: z.record(z.string(), z.string()).optional(),
  httpMethod: z.enum(['GET', 'POST', 'OPTIONS']),
  path: z.string(),
  pathParameters: z.record(z.string(), z.string()).nullable(),
  queryStringParameters: z.record(z.string(), z.string()).nullable(),
  requestContext: z.object({
    requestId: z.string(),
    authorizer: z.object({
      claims: z.object({
        'cognito:groups': z.string().optional(),
        'cognito:username': z.string().optional(),
        email: z.string().email().optional(),
        sub: z.string().optional()
      }).optional()
    }).optional()
  })
});

// Create CORS configuration from environment variables
const corsConfig = createCORSConfigFromEnv();

/**
 * Extract user information from Cognito JWT token
 */
function extractUserInfo(event: APIGatewayProxyEvent): { userId: string; userRole: string } {
  const claims = event.requestContext.authorizer?.claims;
  
  if (!claims) {
    throw new Error('No authorization claims found');
  }
  
  const userId = claims.sub || claims['cognito:username'] || 'unknown';
  const userRole = claims['custom:role'] || 'user';
  
  return { userId, userRole };
}

/**
 * Validate admin permissions with enhanced security
 */
function validateAdminAccess(event: APIGatewayProxyEvent): { userId: string; userRole: string } {
  const claims = event.requestContext?.authorizer?.claims;
  
  if (!claims) {
    throw new Error('No authorization claims found');
  }
  
  // Check if user has admin role in Cognito groups
  const groups = claims['cognito:groups'];
  if (!groups || !groups.includes('admin')) {
    throw new Error('Admin access required - insufficient permissions');
  }
  
  const userId = claims['cognito:username'] || claims.sub || 'unknown';
  const email = claims.email;
  
  // Additional validation
  if (!userId || userId === 'unknown') {
    throw new Error('Invalid user identification');
  }
  
  return {
    userId,
    userRole: 'admin'
  };
}

/**
 * Main Lambda handler for admin management endpoints
 */
export const handler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  const requestId = context.awsRequestId;
  const requestOrigin = extractOriginFromEvent(event);
  
  // Log only non-sensitive request metadata
  console.log('Admin management request:', {
    requestId,
    method: event.httpMethod,
    path: event.path,
    origin: requestOrigin,
    userAgent: event.headers?.['User-Agent']?.substring(0, 100) || 'unknown'
  });
  
  try {
    // Validate request structure first
    try {
      AdminRequestSchema.parse(event);
    } catch (error) {
      return createErrorResponse(400, 'Invalid request structure', requestId, 'INVALID_REQUEST', requestOrigin, corsConfig);
    }

    // Handle CORS preflight requests
    if (event.httpMethod === 'OPTIONS') {
      return handleOPTIONSRequest(requestOrigin, corsConfig);
    }

    // Validate HTTP method
    if (!['GET', 'POST'].includes(event.httpMethod)) {
      return createErrorResponse(405, 'Method not allowed', requestId, 'METHOD_NOT_ALLOWED', requestOrigin, corsConfig);
    }
    
    // Extract and validate user information with enhanced security
    const { userId, userRole } = validateAdminAccess(event);
    
    console.log('Admin request authorized:', { requestId, userId });
    
    // Extract additional request information for audit logging
    const sourceIp = event.requestContext?.identity?.sourceIp;
    const userAgent = event.headers?.['User-Agent'] || event.headers?.['user-agent'];
    
    // Route based on HTTP method and path
    const method = event.httpMethod;
    const pathParameters = event.pathParameters || {};
    const queryParameters = event.queryStringParameters || {};
    
    switch (method) {
      case 'GET':
        return await handleGetRequest(pathParameters, queryParameters, requestId, userId, sourceIp, userAgent, requestOrigin);
      case 'POST':
        return await handlePostRequest(pathParameters, event.body, requestId, userId, sourceIp, userAgent, requestOrigin);
      default:
        return createErrorResponse(405, 'Method not allowed', requestId, 'METHOD_NOT_ALLOWED', requestOrigin, corsConfig);
    }
    
  } catch (error: any) {
    // Log error details server-side only (no sensitive info)
    console.error('Admin management error:', {
      requestId,
      errorType: error.constructor.name,
      message: error.message,
      timestamp: new Date().toISOString()
    });
    
    if (error.message.includes('Admin access required') || error.message.includes('insufficient permissions')) {
      return createErrorResponse(403, 'Admin access required for this operation', requestId, 'FORBIDDEN', requestOrigin, corsConfig);
    }
    
    if (error.message === 'No authorization claims found' || error.message === 'Invalid user identification') {
      return createErrorResponse(401, 'Valid authentication required', requestId, 'UNAUTHORIZED', requestOrigin, corsConfig);
    }
    
    if (error.message === 'Invalid request structure') {
      return createErrorResponse(400, 'Invalid request format', requestId, 'BAD_REQUEST', requestOrigin, corsConfig);
    }
    
    // Generic error for unexpected issues
    return createErrorResponse(500, 'An error occurred processing the admin request', requestId, 'INTERNAL_ERROR', requestOrigin, corsConfig);
  }
};

/**
 * Handle GET requests for admin data retrieval
 */
async function handleGetRequest(
  pathParameters: { [key: string]: string | undefined },
  queryParameters: { [key: string]: string | undefined },
  requestId: string,
  userId?: string,
  sourceIp?: string,
  userAgent?: string,
  requestOrigin?: string
): Promise<APIGatewayProxyResult> {
  
  const resource = pathParameters.proxy || pathParameters.resource;
  
  switch (resource) {
    case 'knowledge-base/status':
      console.log('Getting Knowledge Base status:', { requestId });
      const status = await getKnowledgeBaseStatus();
      
      // Log admin action
      if (userId) {
        await logAdminAction(userId, 'GET_KNOWLEDGE_BASE_STATUS', { requestId }, sourceIp, userAgent);
      }
      
      return createSuccessResponse({
        data: status,
        requestId
      }, 200, requestOrigin, corsConfig);
      
    case 'knowledge-base/ingestion-jobs':
      console.log('Listing ingestion jobs:', { requestId, statusFilter: queryParameters.status });
      const jobs = await listIngestionJobs(queryParameters.status);
      
      // Log admin action
      if (userId) {
        await logAdminAction(userId, 'LIST_INGESTION_JOBS', { 
          requestId, 
          statusFilter: queryParameters.status,
          jobCount: jobs.length 
        }, sourceIp, userAgent);
      }
      
      return createSuccessResponse({
        data: jobs,
        count: jobs.length,
        requestId
      }, 200, requestOrigin, corsConfig);
      
    case 'knowledge-base/metrics':
      console.log('Getting Knowledge Base metrics:', { requestId });
      
      // Parse optional time range parameters
      let startTime: Date | undefined;
      let endTime: Date | undefined;
      
      if (queryParameters.startTime) {
        startTime = new Date(queryParameters.startTime);
      }
      if (queryParameters.endTime) {
        endTime = new Date(queryParameters.endTime);
      }
      
      const metrics = await getKnowledgeBaseMetrics(startTime, endTime);
      
      // Log admin action
      if (userId) {
        await logAdminAction(userId, 'GET_KNOWLEDGE_BASE_METRICS', { 
          requestId,
          startTime: startTime?.toISOString(),
          endTime: endTime?.toISOString()
        }, sourceIp, userAgent);
      }
      
      return createSuccessResponse({
        data: metrics,
        requestId
      }, 200, requestOrigin, corsConfig);
      
    default:
      // Check if it's an ingestion job detail request (pattern: knowledge-base/ingestion-jobs/{jobId})
      if (resource && resource.startsWith('knowledge-base/ingestion-jobs/')) {
        const jobId = resource.split('/')[2];
        if (jobId && !resource.includes('/retry') && !resource.includes('/cancel')) {
          console.log('Getting ingestion job details:', { requestId, jobId });
          // For now, return a message that individual job details are not yet implemented
          return createErrorResponse(501, 'Individual ingestion job details are not yet implemented. Use the list endpoint to see all jobs.', requestId, 'NOT_IMPLEMENTED', requestOrigin, corsConfig);
        }
      }
      
      return createErrorResponse(404, `Admin resource '${resource}' not found`, requestId, 'NOT_FOUND', requestOrigin, corsConfig);
  }
}

/**
 * Handle POST requests for admin actions
 */
async function handlePostRequest(
  pathParameters: { [key: string]: string | undefined },
  body: string | null,
  requestId: string,
  userId?: string,
  sourceIp?: string,
  userAgent?: string,
  requestOrigin?: string
): Promise<APIGatewayProxyResult> {
  
  const resource = pathParameters.proxy || pathParameters.resource;
  
  switch (resource) {
    case 'knowledge-base/sync':
      console.log('Starting Knowledge Base sync:', { requestId });
      const syncResult = await startDataSourceSync();
      
      // Log admin action
      if (userId) {
        await logAdminAction(userId, 'START_KNOWLEDGE_BASE_SYNC', { 
          requestId,
          ingestionJobId: syncResult.ingestionJobId,
          status: syncResult.status
        }, sourceIp, userAgent);
      }
      
      return createSuccessResponse({
        message: 'Data source synchronization started',
        data: syncResult,
        requestId
      }, 200, requestOrigin, corsConfig);
      
    default:
      // Check for ingestion job actions (pattern: knowledge-base/ingestion-jobs/{jobId}/{action})
      if (resource && resource.startsWith('knowledge-base/ingestion-jobs/')) {
        const pathParts = resource.split('/');
        if (pathParts.length === 4) {
          const jobId = pathParts[2];
          const action = pathParts[3];
          
          if (action === 'retry') {
            console.log('Retrying ingestion job:', { requestId, jobId });
            const retryResult = await retryIngestionJob(jobId);
            
            // Log admin action
            if (userId) {
              await logAdminAction(userId, 'RETRY_INGESTION_JOB', { 
                requestId,
                originalJobId: jobId,
                newJobId: retryResult.ingestionJobId,
                status: retryResult.status
              }, sourceIp, userAgent);
            }
            
            return createSuccessResponse({
              message: 'Ingestion job retry initiated',
              data: retryResult,
              requestId
            }, 200, requestOrigin, corsConfig);
          } else if (action === 'cancel') {
            console.log('Canceling ingestion job:', { requestId, jobId });
            const cancelResult = await cancelIngestionJob(jobId);
            
            // Log admin action
            if (userId) {
              await logAdminAction(userId, 'CANCEL_INGESTION_JOB', { 
                requestId,
                jobId,
                status: cancelResult.status
              }, sourceIp, userAgent);
            }
            
            return createSuccessResponse({
              message: 'Ingestion job cancellation initiated',
              data: cancelResult,
              requestId
            }, 200, requestOrigin, corsConfig);
          }
        }
      }
      
      return createErrorResponse(404, `Admin action '${resource}' not found`, requestId, 'NOT_FOUND', requestOrigin, corsConfig);
  }
}