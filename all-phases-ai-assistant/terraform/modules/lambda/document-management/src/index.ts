/**
 * Document Management Lambda Function - RED Phase
 * Test-driven implementation for document management API endpoints
 */

import { BedrockAgentClient, GetIngestionJobCommand, ListIngestionJobsCommand } from '@aws-sdk/client-bedrock-agent';
import { DeleteItemCommand, DynamoDBClient, QueryCommand, ScanCommand } from '@aws-sdk/client-dynamodb';
import { DeleteObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import {
    createCORSConfigFromEnv,
    createErrorResponse,
    createSuccessResponse,
    extractOriginFromEvent,
    handleOPTIONSRequest
} from './cors-utils';

// AWS clients configured for us-west-2 region per steering guidelines
const s3Client = new S3Client({ 
  region: 'us-west-2'
});

const dynamoClient = new DynamoDBClient({ 
  region: 'us-west-2'
});

const bedrockClient = new BedrockAgentClient({ 
  region: 'us-west-2'
});

// Create CORS configuration from environment variables with custom methods for /documents endpoint
const corsConfig = {
  ...createCORSConfigFromEnv(),
  // Include POST method since /documents endpoint supports POST via document-upload Lambda
  allowedMethods: ['GET', 'POST', 'DELETE', 'OPTIONS']
};

// Document status types
type DocumentStatus = 'uploading' | 'uploaded' | 'processing' | 'ready' | 'failed';
type KnowledgeBaseStatus = 'pending' | 'ingesting' | 'synced' | 'failed';

interface DocumentRecord {
  documentId: string;
  fileName: string;
  originalName: string;
  contentType: string;
  fileSize: number;
  uploadedBy: string;
  uploadDate: string;
  s3Key: string;
  s3Bucket: string;
  status: DocumentStatus;
  knowledgeBaseStatus: KnowledgeBaseStatus;
  lastSyncDate?: string;
  ingestionJobId?: string;
  failureReason?: string;
  retryCount?: number;
}

interface IngestionJobInfo {
  jobId: string;
  status: string;
  startedAt?: Date;
  completedAt?: Date;
  statistics?: {
    numberOfDocumentsScanned?: number;
    numberOfNewDocumentsIndexed?: number;
    numberOfModifiedDocumentsIndexed?: number;
    numberOfDocumentsDeleted?: number;
    numberOfDocumentsFailed?: number;
  };
}

export const handler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  const startTime = Date.now();
  const requestId = context.awsRequestId;
  const requestOrigin = extractOriginFromEvent(event);
  
  console.log('Document management request received - VERSION 2.0:', {
    requestId,
    method: event.httpMethod,
    path: event.path,
    origin: requestOrigin,
    pathParameters: event.pathParameters,
    httpMethodType: typeof event.httpMethod,
    httpMethodValue: JSON.stringify(event.httpMethod),
    httpMethodLength: event.httpMethod?.length,
    httpMethodCharCodes: event.httpMethod ? Array.from(event.httpMethod).map(c => c.charCodeAt(0)) : null
  });

  try {
    // Handle CORS preflight - OPTIONS requests should not require authentication
    const isOptionsRequest = event.httpMethod === 'OPTIONS';
    console.log('Checking if OPTIONS request:', { 
      httpMethod: event.httpMethod, 
      isOptions: isOptionsRequest,
      requestId,
      comparison: `'${event.httpMethod}' === 'OPTIONS'`,
      strictEqual: event.httpMethod === 'OPTIONS',
      trimmedEqual: event.httpMethod?.trim() === 'OPTIONS',
      upperCaseEqual: event.httpMethod?.toUpperCase() === 'OPTIONS'
    });
    
    if (isOptionsRequest) {
      console.log('Handling OPTIONS preflight request:', { requestId, requestOrigin });
      return handleOPTIONSRequest(requestOrigin, corsConfig);
    }
    
    console.log('Not an OPTIONS request, proceeding with authorization check:', { requestId });

    // Validate authorization for all non-OPTIONS requests
    if (!event.requestContext?.authorizer?.claims?.sub) {
      console.warn('Authorization failed:', { requestId });
      return createErrorResponse(401, 'Unauthorized - missing user authentication', requestId, 'UNAUTHORIZED', requestOrigin, corsConfig);
    }

    const userId = event.requestContext.authorizer.claims.sub;
    const userRole = event.requestContext.authorizer.claims['custom:role'] || 'user';
    
    console.log('User authenticated:', { requestId, userId, userRole });

    // Route to appropriate handler based on HTTP method and path
    const method = event.httpMethod;
    const path = event.path;
    const pathParameters = event.pathParameters;

    if (method === 'GET' && path === '/documents') {
      return await handleListDocuments(userId, userRole, requestId, requestOrigin);
    } else if (method === 'DELETE' && pathParameters?.id) {
      return await handleDeleteDocument(pathParameters.id, userId, userRole, requestId, requestOrigin);
    } else if (method === 'GET' && path === '/documents/status') {
      return await handleDocumentProcessingStatus(userId, userRole, requestId, requestOrigin);
    } else {
      return createErrorResponse(404, 'Endpoint not found', requestId, 'NOT_FOUND', requestOrigin, corsConfig);
    }

  } catch (error) {
    console.error('Document management error:', { requestId, error });
    return createErrorResponse(500, 'Internal server error during document management', requestId, 'INTERNAL_ERROR', requestOrigin, corsConfig);
  }
};

/**
 * Handle GET /documents - List user documents with Knowledge Base sync status
 * Requirements: US-005 (Document Management), US-005a (Document Viewing)
 */
async function handleListDocuments(
  userId: string, 
  userRole: string, 
  requestId: string,
  requestOrigin?: string
): Promise<APIGatewayProxyResult> {
  try {
    console.log('Listing documents for user:', { requestId, userId, userRole });

    let documents: DocumentRecord[] = [];

    if (userRole === 'admin') {
      // Admins can see all documents
      documents = await getAllDocuments(requestId);
    } else {
      // Regular users can only see their own documents
      documents = await getUserDocuments(userId, requestId);
    }

    // Enrich documents with current Knowledge Base sync status
    const enrichedDocuments = await enrichDocumentsWithSyncStatus(documents, requestId);

    const processingTime = Date.now() - Date.now();
    
    console.log('Documents listed successfully:', { 
      requestId, 
      documentCount: enrichedDocuments.length,
      processingTime: `${processingTime}ms`
    });

    return createSuccessResponse({
      documents: enrichedDocuments,
      totalCount: enrichedDocuments.length,
      userRole,
      timestamp: new Date().toISOString(),
      processingTime: `${processingTime}ms`
    }, 200, requestOrigin, corsConfig);

  } catch (error) {
    console.error('Error listing documents:', { requestId, error });
    return createErrorResponse(500, 'Failed to retrieve documents', requestId, 'RETRIEVAL_ERROR', requestOrigin, corsConfig);
  }
}

/**
 * Handle DELETE /documents/{id} - Delete document with Knowledge Base cleanup
 * Requirements: US-005 (Document Management)
 */
async function handleDeleteDocument(
  documentId: string,
  userId: string,
  userRole: string,
  requestId: string,
  requestOrigin?: string
): Promise<APIGatewayProxyResult> {
  try {
    console.log('Deleting document:', { requestId, documentId, userId, userRole });

    // Get document metadata to verify ownership and get S3 details
    const document = await getDocumentById(documentId, requestId);
    
    if (!document) {
      return createErrorResponse(404, 'Document not found', requestId, 'NOT_FOUND', requestOrigin, corsConfig);
    }

    // Check permissions - users can only delete their own documents, admins can delete any
    if (userRole !== 'admin' && document.uploadedBy !== userId) {
      console.warn('Permission denied for document deletion:', { 
        requestId, 
        documentId, 
        documentOwner: document.uploadedBy, 
        requestingUser: userId 
      });
      return createErrorResponse(403, 'Permission denied - you can only delete your own documents', requestId, 'FORBIDDEN', requestOrigin, corsConfig);
    }

    // Delete from S3 first
    try {
      await s3Client.send(new DeleteObjectCommand({
        Bucket: document.s3Bucket,
        Key: document.s3Key
      }));
      console.log('Document deleted from S3:', { requestId, documentId, s3Key: document.s3Key });
    } catch (s3Error) {
      console.error('S3 deletion failed:', { requestId, documentId, error: s3Error });
      return createErrorResponse(500, 'Failed to delete document from storage', requestId, 'S3_ERROR', requestOrigin, corsConfig);
    }

    // Delete metadata from DynamoDB
    try {
      await dynamoClient.send(new DeleteItemCommand({
        TableName: process.env.DOCUMENTS_TABLE!,
        Key: {
          PK: { S: `DOC#${documentId}` },
          SK: { S: 'METADATA' }
        }
      }));
      console.log('Document metadata deleted from DynamoDB:', { requestId, documentId });
    } catch (dynamoError) {
      console.error('DynamoDB deletion failed:', { requestId, documentId, error: dynamoError });
      return createErrorResponse(500, 'Failed to delete document metadata', requestId, 'DYNAMODB_ERROR', requestOrigin, corsConfig);
    }

    // Note: Knowledge Base cleanup happens automatically during next sync
    // The document will be removed from the vector index when the data source is synchronized

    const processingTime = Date.now() - Date.now();
    
    console.log('Document deleted successfully:', { 
      requestId, 
      documentId,
      processingTime: `${processingTime}ms`
    });

    return createSuccessResponse({
      message: 'Document deleted successfully',
      documentId,
      fileName: document.fileName,
      knowledgeBaseCleanup: 'Will be removed from Knowledge Base during next sync',
      timestamp: new Date().toISOString(),
      processingTime: `${processingTime}ms`
    }, 200, requestOrigin, corsConfig);

  } catch (error) {
    console.error('Error deleting document:', { requestId, documentId, error });
    return createErrorResponse(500, 'Failed to delete document', requestId, 'DELETE_ERROR', requestOrigin, corsConfig);
  }
}

/**
 * Handle GET /documents/status - Get document processing status with ingestion job tracking
 * Requirements: US-005 (Document Management)
 */
async function handleDocumentProcessingStatus(
  userId: string,
  userRole: string,
  requestId: string,
  requestOrigin?: string
): Promise<APIGatewayProxyResult> {
  try {
    console.log('Getting document processing status:', { requestId, userId, userRole });

    // Get current ingestion jobs from Knowledge Base
    const ingestionJobs = await getCurrentIngestionJobs(requestId);
    
    // Get documents with processing status
    let documents: DocumentRecord[] = [];
    
    if (userRole === 'admin') {
      documents = await getAllDocuments(requestId);
    } else {
      documents = await getUserDocuments(userId, requestId);
    }

    // Filter to documents that are currently processing or recently processed
    const processingDocuments = documents.filter(doc => 
      doc.knowledgeBaseStatus === 'pending' || 
      doc.knowledgeBaseStatus === 'ingesting' ||
      (doc.knowledgeBaseStatus === 'failed' && doc.retryCount && doc.retryCount < 3)
    );

    // Create processing status summary
    const statusSummary = {
      totalDocuments: documents.length,
      pendingIngestion: documents.filter(d => d.knowledgeBaseStatus === 'pending').length,
      currentlyIngesting: documents.filter(d => d.knowledgeBaseStatus === 'ingesting').length,
      synced: documents.filter(d => d.knowledgeBaseStatus === 'synced').length,
      failed: documents.filter(d => d.knowledgeBaseStatus === 'failed').length,
      activeIngestionJobs: ingestionJobs.filter(j => j.status === 'IN_PROGRESS').length,
      completedIngestionJobs: ingestionJobs.filter(j => j.status === 'COMPLETE').length,
      failedIngestionJobs: ingestionJobs.filter(j => j.status === 'FAILED').length
    };

    const processingTime = Date.now() - Date.now();
    
    console.log('Document processing status retrieved:', { 
      requestId, 
      statusSummary,
      processingTime: `${processingTime}ms`
    });

    return createSuccessResponse({
      statusSummary,
      processingDocuments,
      ingestionJobs,
      userRole,
      timestamp: new Date().toISOString(),
      processingTime: `${processingTime}ms`
    }, 200, requestOrigin, corsConfig);

  } catch (error) {
    console.error('Error getting document processing status:', { requestId, error });
    return createErrorResponse(500, 'Failed to retrieve document processing status', requestId, 'STATUS_ERROR', requestOrigin, corsConfig);
  }
}

// Helper functions

async function getAllDocuments(requestId: string): Promise<DocumentRecord[]> {
  try {
    const response = await dynamoClient.send(new ScanCommand({
      TableName: process.env.DOCUMENTS_TABLE!,
      FilterExpression: 'SK = :sk AND begins_with(PK, :docPrefix)',
      ExpressionAttributeValues: {
        ':sk': { S: 'METADATA' },
        ':docPrefix': { S: 'DOC#' }
      }
    }));

    return response.Items?.map(item => mapDynamoItemToDocument(item)).filter((doc): doc is DocumentRecord => doc !== null) || [];
  } catch (error) {
    console.error('Error getting all documents:', { requestId, error });
    return [];
  }
}

async function getUserDocuments(userId: string, requestId: string): Promise<DocumentRecord[]> {
  try {
    const response = await dynamoClient.send(new QueryCommand({
      TableName: process.env.DOCUMENTS_TABLE!,
      IndexName: 'GSI1',
      KeyConditionExpression: 'GSI1PK = :userPK',
      ExpressionAttributeValues: {
        ':userPK': { S: `USER#${userId}` }
      }
    }));

    return response.Items?.map(item => mapDynamoItemToDocument(item)).filter((doc): doc is DocumentRecord => doc !== null) || [];
  } catch (error) {
    console.error('Error getting user documents:', { requestId, userId, error });
    return [];
  }
}

async function getDocumentById(documentId: string, requestId: string): Promise<DocumentRecord | null> {
  try {
    const response = await dynamoClient.send(new QueryCommand({
      TableName: process.env.DOCUMENTS_TABLE!,
      KeyConditionExpression: 'PK = :pk AND SK = :sk',
      ExpressionAttributeValues: {
        ':pk': { S: `DOC#${documentId}` },
        ':sk': { S: 'METADATA' }
      }
    }));

    if (response.Items && response.Items.length > 0) {
      return mapDynamoItemToDocument(response.Items[0]);
    }
    
    return null;
  } catch (error) {
    console.error('Error getting document by ID:', { requestId, documentId, error });
    return null;
  }
}

async function enrichDocumentsWithSyncStatus(
  documents: DocumentRecord[], 
  requestId: string
): Promise<DocumentRecord[]> {
  try {
    // Get current ingestion jobs to provide real-time status
    const ingestionJobs = await getCurrentIngestionJobs(requestId);
    
    return documents.map(doc => {
      // Find related ingestion job if exists
      const relatedJob = ingestionJobs.find(job => job.jobId === doc.ingestionJobId);
      
      if (relatedJob) {
        // Update status based on current job status
        return {
          ...doc,
          currentIngestionJob: {
            jobId: relatedJob.jobId,
            status: relatedJob.status,
            startedAt: relatedJob.startedAt,
            completedAt: relatedJob.completedAt,
            statistics: relatedJob.statistics
          }
        };
      }
      
      return doc;
    });
  } catch (error) {
    console.error('Error enriching documents with sync status:', { requestId, error });
    // Return documents without enrichment if there's an error
    return documents;
  }
}

async function getCurrentIngestionJobs(requestId: string): Promise<IngestionJobInfo[]> {
  try {
    const response = await bedrockClient.send(new ListIngestionJobsCommand({
      knowledgeBaseId: process.env.KNOWLEDGE_BASE_ID!,
      dataSourceId: process.env.DATA_SOURCE_ID!,
      maxResults: 50
    }));

    const jobs: IngestionJobInfo[] = [];
    
    if (response.ingestionJobSummaries) {
      for (const jobSummary of response.ingestionJobSummaries) {
        // Get detailed job information
        const jobDetail = await bedrockClient.send(new GetIngestionJobCommand({
          knowledgeBaseId: process.env.KNOWLEDGE_BASE_ID!,
          dataSourceId: process.env.DATA_SOURCE_ID!,
          ingestionJobId: jobSummary.ingestionJobId!
        }));

        jobs.push({
          jobId: jobSummary.ingestionJobId!,
          status: jobSummary.status!,
          startedAt: jobSummary.startedAt,
          completedAt: jobSummary.updatedAt,
          statistics: jobDetail.ingestionJob?.statistics
        });
      }
    }

    return jobs;
  } catch (error) {
    console.error('Error getting current ingestion jobs:', { requestId, error });
    return [];
  }
}

function mapDynamoItemToDocument(item: any): DocumentRecord | null {
  // Validate that this is actually a document record
  if (!item.PK?.S?.startsWith('DOC#') || !item.documentId?.S || !item.fileName?.S) {
    console.warn('Invalid document record found, skipping:', { 
      PK: item.PK?.S, 
      hasDocumentId: !!item.documentId?.S,
      hasFileName: !!item.fileName?.S 
    });
    return null;
  }

  // Validate required fields
  const documentId = item.documentId?.S;
  const fileName = item.fileName?.S;
  const uploadDate = item.uploadDate?.S;
  const uploadedBy = item.uploadedBy?.S;

  if (!documentId || !fileName || !uploadDate || !uploadedBy) {
    console.warn('Document record missing required fields, skipping:', { 
      documentId, fileName, uploadDate, uploadedBy 
    });
    return null;
  }

  return {
    documentId,
    fileName,
    originalName: item.originalName?.S || fileName,
    contentType: item.contentType?.S || 'application/octet-stream',
    fileSize: parseInt(item.fileSize?.N || '0'),
    uploadedBy,
    uploadDate,
    s3Key: item.s3Key?.S || '',
    s3Bucket: item.s3Bucket?.S || process.env.DOCUMENTS_BUCKET || '',
    status: (item.status?.S || 'unknown') as DocumentStatus,
    knowledgeBaseStatus: (item.knowledgeBaseStatus?.S || 'pending') as KnowledgeBaseStatus,
    lastSyncDate: item.lastSyncDate?.S,
    ingestionJobId: item.ingestionJobId?.S,
    failureReason: item.failureReason?.S,
    retryCount: item.retryCount?.N ? parseInt(item.retryCount.N) : undefined
  };
}

