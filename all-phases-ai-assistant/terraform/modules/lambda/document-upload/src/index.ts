/**
 * Document Upload Lambda Function - REFACTOR Phase
 * Optimized implementation with improved error handling and logging
 */

import { BedrockAgentClient, StartIngestionJobCommand } from '@aws-sdk/client-bedrock-agent';
import { DynamoDBClient, PutItemCommand } from '@aws-sdk/client-dynamodb';
import { PutObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { v4 as uuidv4 } from 'uuid';
import {
    createCORSConfigFromEnv,
    createErrorResponse,
    createSuccessResponse,
    extractOriginFromEvent,
    handleOPTIONSRequest
} from './cors-utils';

// AWS clients with proper region and profile configuration
const s3Client = new S3Client({ 
  region: process.env.AWS_REGION || 'us-west-2'
});

const dynamoClient = new DynamoDBClient({ 
  region: process.env.AWS_REGION || 'us-west-2'
});

const bedrockClient = new BedrockAgentClient({ 
  region: process.env.AWS_REGION || 'us-west-2'
});

const lambdaClient = new LambdaClient({ 
  region: process.env.AWS_REGION || 'us-west-2'
});

// Create CORS configuration from environment variables
const corsConfig = createCORSConfigFromEnv();

// Configuration constants
const SUPPORTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown'
] as const;

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB (Lambda payload limit is 6MB)
const SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'] as const;

// Enhanced error types for better error handling
enum DocumentUploadError {
  UNAUTHORIZED = 'UNAUTHORIZED',
  INVALID_FILE_TYPE = 'INVALID_FILE_TYPE',
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  INVALID_MULTIPART = 'INVALID_MULTIPART',
  S3_UPLOAD_FAILED = 'S3_UPLOAD_FAILED',
  DYNAMODB_ERROR = 'DYNAMODB_ERROR',
  KNOWLEDGE_BASE_ERROR = 'KNOWLEDGE_BASE_ERROR'
}

interface DocumentMetadata {
  documentId: string;
  fileName: string;
  originalName: string;
  contentType: string;
  fileSize: number;
  uploadedBy: string;
  uploadDate: string;
  s3Key: string;
  s3Bucket: string;
  status: 'uploading' | 'uploaded' | 'processing' | 'ready' | 'failed';
  knowledgeBaseStatus: 'pending' | 'ingesting' | 'synced' | 'failed';
}

export const handler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  const startTime = Date.now();
  const requestId = context.awsRequestId;
  const requestOrigin = extractOriginFromEvent(event);
  
  console.log('Document upload request received:', {
    requestId,
    method: event.httpMethod,
    path: event.path,
    origin: requestOrigin
  });

  try {
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
      return handleOPTIONSRequest(requestOrigin, corsConfig);
    }

    // Validate authorization
    if (!event.requestContext?.authorizer?.claims?.sub) {
      console.warn('Authorization failed:', { requestId });
      return createErrorResponse(401, 'Unauthorized - missing user authentication', requestId, 'UNAUTHORIZED', requestOrigin, corsConfig);
    }

    const userId = event.requestContext.authorizer.claims.sub;
    console.log('User authenticated:', { requestId, userId });

    // Parse multipart form data with improved error handling
    const { fileName, contentType, fileBuffer } = await parseMultipartData(event.body || '');
    
    // Enhanced file validation
    if (!SUPPORTED_MIME_TYPES.includes(contentType as any)) {
      console.warn('Invalid file type:', { requestId, contentType, fileName });
      return createErrorResponse(400, 'Unsupported file type. Supported types: PDF, DOCX, TXT, MD', requestId, 'INVALID_FILE_TYPE', requestOrigin, corsConfig);
    }

    if (fileBuffer.length > MAX_FILE_SIZE) {
      console.warn('File too large:', { requestId, fileSize: fileBuffer.length, fileName });
      return createErrorResponse(400, 'File size exceeds 10MB limit', requestId, 'FILE_TOO_LARGE', requestOrigin, corsConfig);
    }

    console.log('File validation passed:', {
      requestId,
      fileName,
      contentType,
      fileSize: fileBuffer.length
    });

    // Generate document ID and S3 key
    const documentId = uuidv4();
    const fileExtension = getFileExtension(fileName, contentType);
    const s3Key = `documents/${userId}/${documentId}${fileExtension}`;
    const uploadDate = new Date().toISOString();

    console.log('Starting S3 upload:', { requestId, documentId, s3Key });

    // Upload to S3 (Knowledge Base data source) with enhanced error handling
    try {
      await s3Client.send(new PutObjectCommand({
        Bucket: process.env.DOCUMENTS_BUCKET!,
        Key: s3Key,
        Body: fileBuffer,
        ContentType: contentType,
        Metadata: {
          'uploaded-by': userId,
          'original-name': fileName,
          'file-size': fileBuffer.length.toString(),
          'document-id': documentId
        }
      }));
      console.log('S3 upload successful:', { requestId, documentId });
    } catch (s3Error) {
      console.error('S3 upload failed:', { requestId, error: s3Error });
      throw new Error('S3 upload failed');
    }

    // Store metadata in DynamoDB with enhanced error handling
    const metadata: DocumentMetadata = {
      documentId,
      fileName,
      originalName: fileName,
      contentType,
      fileSize: fileBuffer.length,
      uploadedBy: userId,
      uploadDate,
      s3Key,
      s3Bucket: process.env.DOCUMENTS_BUCKET!,
      status: 'uploaded',
      knowledgeBaseStatus: 'pending'
    };

    console.log('Storing metadata in DynamoDB:', { requestId, documentId });

    try {
      await dynamoClient.send(new PutItemCommand({
        TableName: process.env.DOCUMENTS_TABLE!,
        Item: {
          PK: { S: `DOC#${documentId}` },
          SK: { S: 'METADATA' },
          documentId: { S: documentId },
          fileName: { S: fileName },
          originalName: { S: fileName },
          contentType: { S: contentType },
          fileSize: { N: fileBuffer.length.toString() },
          uploadedBy: { S: userId },
          uploadDate: { S: uploadDate },
          s3Key: { S: s3Key },
          s3Bucket: { S: process.env.DOCUMENTS_BUCKET! },
          status: { S: 'uploaded' },
          knowledgeBaseStatus: { S: 'pending' },
          GSI1PK: { S: `USER#${userId}` },
          GSI1SK: { S: `DOC#${uploadDate}` }
        }
      }));
      console.log('DynamoDB metadata stored:', { requestId, documentId });
    } catch (dynamoError) {
      console.error('DynamoDB storage failed:', { requestId, error: dynamoError });
      throw new Error('DynamoDB error');
    }

    // Trigger Knowledge Base ingestion with enhanced error handling
    console.log('Triggering Knowledge Base ingestion:', { requestId, documentId });
    
    let ingestionJobStarted = false;
    try {
      await bedrockClient.send(new StartIngestionJobCommand({
        knowledgeBaseId: process.env.KNOWLEDGE_BASE_ID!,
        dataSourceId: process.env.DATA_SOURCE_ID!,
        description: `Ingestion job for document ${fileName} uploaded by ${userId}`
      }));
      console.log('Knowledge Base ingestion job started:', { requestId, documentId });
      ingestionJobStarted = true;
    } catch (ingestionError: any) {
      // Handle ongoing ingestion job conflict gracefully
      if (ingestionError.name === 'ConflictException') {
        console.log('Knowledge Base ingestion job already in progress, document will be processed in next sync', { requestId });
        // Update metadata to indicate sync will happen later
        await dynamoClient.send(new PutItemCommand({
          TableName: process.env.DOCUMENTS_TABLE!,
          Item: {
            PK: { S: `DOC#${documentId}` },
            SK: { S: 'METADATA' },
            documentId: { S: documentId },
            fileName: { S: fileName },
            originalName: { S: fileName },
            contentType: { S: contentType },
            fileSize: { N: fileBuffer.length.toString() },
            uploadedBy: { S: userId },
            uploadDate: { S: uploadDate },
            s3Key: { S: s3Key },
            s3Bucket: { S: process.env.DOCUMENTS_BUCKET! },
            status: { S: 'uploaded' },
            knowledgeBaseStatus: { S: 'pending' },
            GSI1PK: { S: `USER#${userId}` },
            GSI1SK: { S: `DOC#${uploadDate}` },
            syncNote: { S: 'Will be processed in next available ingestion job' }
          }
        }));
      } else {
        console.error('Knowledge Base ingestion failed:', { requestId, error: ingestionError });
        throw ingestionError;
      }
    }

    // Trigger sync monitor to check ingestion status (with delay to allow ingestion job to start)
    if (ingestionJobStarted) {
      try {
        console.log('Triggering KB sync monitor:', { requestId, documentId });
        
        // Invoke sync monitor asynchronously with a slight delay
        await lambdaClient.send(new InvokeCommand({
          FunctionName: process.env.KB_SYNC_MONITOR_FUNCTION || 'ai-assistant-dev-kb-sync-monitor',
          InvocationType: 'Event', // Async invocation
          Payload: JSON.stringify({
            source: 'document-upload',
            documentId,
            requestId,
            triggerDelay: 30000 // 30 second delay to allow ingestion job to start
          })
        }));
        
        console.log('KB sync monitor triggered successfully:', { requestId, documentId });
      } catch (syncError) {
        console.warn('Failed to trigger sync monitor (non-critical):', { requestId, error: syncError });
        // Don't fail the upload if sync monitor trigger fails
      }
    }

    const processingTime = Date.now() - startTime;
    console.log('Document upload completed successfully:', { 
      requestId, 
      documentId, 
      processingTime: `${processingTime}ms` 
    });

    return createSuccessResponse({
      documentId,
      fileName,
      fileSize: fileBuffer.length,
      status: 'uploaded',
      knowledgeBaseStatus: 'pending',
      message: 'Document uploaded successfully and Knowledge Base sync initiated',
      processingTime: `${processingTime}ms`
    }, 200, requestOrigin, corsConfig);

  } catch (error) {
    console.error('Document upload error:', error);
    
    // Handle specific error types
    if (error instanceof Error) {
      if (error.message.includes('Invalid file upload')) {
        return createErrorResponse(400, 'Invalid file upload format', requestId, 'INVALID_MULTIPART', requestOrigin, corsConfig);
      }
      
      if (error.message.includes('S3')) {
        return createErrorResponse(500, 'Upload failed - S3 error', requestId, 'S3_UPLOAD_FAILED', requestOrigin, corsConfig);
      }
      
      if (error.message.includes('DynamoDB')) {
        return createErrorResponse(500, 'Metadata storage failed - DynamoDB error', requestId, 'DYNAMODB_ERROR', requestOrigin, corsConfig);
      }
    }

    return createErrorResponse(500, 'An unexpected error occurred during document upload', requestId, 'INTERNAL_ERROR', requestOrigin, corsConfig);
  }
};

// Helper functions for better code organization

function validateAuthorization(event: APIGatewayProxyEvent): { isValid: boolean; userId?: string; reason?: string } {
  if (!event.requestContext?.authorizer?.claims?.sub) {
    return { isValid: false, reason: 'Missing user authentication in request context' };
  }
  
  const userId = event.requestContext.authorizer.claims.sub;
  if (!userId || typeof userId !== 'string') {
    return { isValid: false, reason: 'Invalid user ID in authentication claims' };
  }
  
  return { isValid: true, userId };
}

async function parseAndValidateFile(body: string, requestId: string): Promise<{
  fileName: string;
  contentType: string;
  fileBuffer: Buffer;
}> {
  // Parse multipart form data
  const fileData = await parseMultipartData(body);
  
  // Validate file type
  if (!SUPPORTED_MIME_TYPES.includes(fileData.contentType as any)) {
    console.warn('Unsupported file type:', { 
      requestId, 
      contentType: fileData.contentType,
      supportedTypes: SUPPORTED_MIME_TYPES 
    });
    throw new Error(`${DocumentUploadError.INVALID_FILE_TYPE}:Unsupported file type. Supported types: PDF, DOCX, TXT, MD`);
  }

  // Validate file size
  if (fileData.fileBuffer.length > MAX_FILE_SIZE) {
    console.warn('File too large:', { 
      requestId, 
      fileSize: fileData.fileBuffer.length, 
      maxSize: MAX_FILE_SIZE 
    });
    throw new Error(`${DocumentUploadError.FILE_TOO_LARGE}:File size exceeds 10MB limit`);
  }

  // Additional validation: check file extension matches content type
  const expectedExtension = getFileExtension(fileData.fileName, fileData.contentType);
  if (!SUPPORTED_EXTENSIONS.includes(expectedExtension as any)) {
    console.warn('File extension mismatch:', { 
      requestId, 
      fileName: fileData.fileName, 
      contentType: fileData.contentType,
      expectedExtension 
    });
  }

  return fileData;
}



function getFileExtension(fileName: string, contentType: string): string {
  // Extract extension from filename first
  const fileExt = fileName.split('.').pop()?.toLowerCase();
  if (fileExt) {
    return `.${fileExt}`;
  }
  
  // Fallback to content type mapping
  const typeMap: { [key: string]: string } = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'text/plain': '.txt',
    'text/markdown': '.md'
  };
  
  return typeMap[contentType] || '.bin';
}

async function parseMultipartData(body: string): Promise<{
  fileName: string;
  contentType: string;
  fileBuffer: Buffer;
}> {
  // Simple multipart parser for testing
  // In production, you'd use a more robust parser
  
  if (!body || !body.includes('Content-Disposition')) {
    throw new Error('Invalid file upload - missing multipart data');
  }

  // Extract boundary
  const boundaryMatch = body.match(/----WebKitFormBoundary[\w\d]+/);
  if (!boundaryMatch) {
    throw new Error('Invalid file upload - missing boundary');
  }

  // Extract filename
  const filenameMatch = body.match(/filename="([^"]+)"/);
  if (!filenameMatch) {
    throw new Error('Invalid file upload - missing filename');
  }
  const fileName = filenameMatch[1];

  // Extract content type
  const contentTypeMatch = body.match(/Content-Type:\s*([^\r\n]+)/);
  if (!contentTypeMatch) {
    throw new Error('Invalid file upload - missing content type');
  }
  const contentType = contentTypeMatch[1].trim();

  // Extract file content (simplified - assumes content is after double CRLF)
  const contentStart = body.indexOf('\r\n\r\n');
  const contentEnd = body.lastIndexOf(`\r\n--${boundaryMatch[0]}--`);
  
  if (contentStart === -1 || contentEnd === -1) {
    throw new Error('Invalid file upload - malformed content');
  }

  const fileContent = body.substring(contentStart + 4, contentEnd);
  const fileBuffer = Buffer.from(fileContent, 'binary');

  return {
    fileName,
    contentType,
    fileBuffer
  };
}