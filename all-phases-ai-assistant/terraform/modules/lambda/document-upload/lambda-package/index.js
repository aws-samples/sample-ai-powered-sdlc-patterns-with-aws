"use strict";
/**
 * Document Upload Lambda Function - REFACTOR Phase
 * Optimized implementation with improved error handling and logging
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.handler = void 0;
const client_bedrock_agent_1 = require("@aws-sdk/client-bedrock-agent");
const client_dynamodb_1 = require("@aws-sdk/client-dynamodb");
const client_s3_1 = require("@aws-sdk/client-s3");
const uuid_1 = require("uuid");
// AWS clients with proper region and profile configuration
const s3Client = new client_s3_1.S3Client({
    region: process.env.AWS_REGION || 'us-west-2'
});
const dynamoClient = new client_dynamodb_1.DynamoDBClient({
    region: process.env.AWS_REGION || 'us-west-2'
});
const bedrockClient = new client_bedrock_agent_1.BedrockAgentClient({
    region: process.env.AWS_REGION || 'us-west-2'
});
// Configuration constants
const SUPPORTED_MIME_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown'
];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'];
// Enhanced error types for better error handling
var DocumentUploadError;
(function (DocumentUploadError) {
    DocumentUploadError["UNAUTHORIZED"] = "UNAUTHORIZED";
    DocumentUploadError["INVALID_FILE_TYPE"] = "INVALID_FILE_TYPE";
    DocumentUploadError["FILE_TOO_LARGE"] = "FILE_TOO_LARGE";
    DocumentUploadError["INVALID_MULTIPART"] = "INVALID_MULTIPART";
    DocumentUploadError["S3_UPLOAD_FAILED"] = "S3_UPLOAD_FAILED";
    DocumentUploadError["DYNAMODB_ERROR"] = "DYNAMODB_ERROR";
    DocumentUploadError["KNOWLEDGE_BASE_ERROR"] = "KNOWLEDGE_BASE_ERROR";
})(DocumentUploadError || (DocumentUploadError = {}));
const handler = async (event, context) => {
    const startTime = Date.now();
    const requestId = context.awsRequestId;
    console.log('Document upload request received:', {
        requestId,
        method: event.httpMethod,
        path: event.path
    });
    try {
        // Validate authorization
        if (!event.requestContext?.authorizer?.claims?.sub) {
            console.warn('Authorization failed:', { requestId });
            return {
                statusCode: 401,
                headers: getCorsHeaders(),
                body: JSON.stringify({
                    error: 'Unauthorized - missing user authentication'
                })
            };
        }
        const userId = event.requestContext.authorizer.claims.sub;
        console.log('User authenticated:', { requestId, userId });
        // Parse multipart form data with improved error handling
        const { fileName, contentType, fileBuffer } = await parseMultipartData(event.body || '');
        // Enhanced file validation
        if (!SUPPORTED_MIME_TYPES.includes(contentType)) {
            console.warn('Invalid file type:', { requestId, contentType, fileName });
            return {
                statusCode: 400,
                headers: getCorsHeaders(),
                body: JSON.stringify({
                    success: false,
                    error: {
                        message: 'Unsupported file type. Supported types: PDF, DOCX, TXT, MD'
                    }
                })
            };
        }
        if (fileBuffer.length > MAX_FILE_SIZE) {
            console.warn('File too large:', { requestId, fileSize: fileBuffer.length, fileName });
            return {
                statusCode: 400,
                headers: getCorsHeaders(),
                body: JSON.stringify({
                    success: false,
                    error: {
                        message: 'File size exceeds 10MB limit'
                    }
                })
            };
        }
        console.log('File validation passed:', {
            requestId,
            fileName,
            contentType,
            fileSize: fileBuffer.length
        });
        // Generate document ID and S3 key
        const documentId = (0, uuid_1.v4)();
        const fileExtension = getFileExtension(fileName, contentType);
        const s3Key = `documents/${userId}/${documentId}${fileExtension}`;
        const uploadDate = new Date().toISOString();
        console.log('Starting S3 upload:', { requestId, documentId, s3Key });
        // Upload to S3 (Knowledge Base data source) with enhanced error handling
        try {
            await s3Client.send(new client_s3_1.PutObjectCommand({
                Bucket: process.env.DOCUMENTS_BUCKET,
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
        }
        catch (s3Error) {
            console.error('S3 upload failed:', { requestId, error: s3Error });
            throw new Error('S3 upload failed');
        }
        // Store metadata in DynamoDB with enhanced error handling
        const metadata = {
            documentId,
            fileName,
            originalName: fileName,
            contentType,
            fileSize: fileBuffer.length,
            uploadedBy: userId,
            uploadDate,
            s3Key,
            s3Bucket: process.env.DOCUMENTS_BUCKET,
            status: 'uploaded',
            knowledgeBaseStatus: 'pending'
        };
        console.log('Storing metadata in DynamoDB:', { requestId, documentId });
        try {
            await dynamoClient.send(new client_dynamodb_1.PutItemCommand({
                TableName: process.env.DOCUMENTS_TABLE,
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
                    s3Bucket: { S: process.env.DOCUMENTS_BUCKET },
                    status: { S: 'uploaded' },
                    knowledgeBaseStatus: { S: 'pending' },
                    GSI1PK: { S: `USER#${userId}` },
                    GSI1SK: { S: `DOC#${uploadDate}` }
                }
            }));
            console.log('DynamoDB metadata stored:', { requestId, documentId });
        }
        catch (dynamoError) {
            console.error('DynamoDB storage failed:', { requestId, error: dynamoError });
            throw new Error('DynamoDB error');
        }
        // Trigger Knowledge Base ingestion with enhanced error handling
        console.log('Triggering Knowledge Base ingestion:', { requestId, documentId });
        try {
            await bedrockClient.send(new client_bedrock_agent_1.StartIngestionJobCommand({
                knowledgeBaseId: process.env.KNOWLEDGE_BASE_ID,
                dataSourceId: process.env.DATA_SOURCE_ID,
                description: `Ingestion job for document ${fileName} uploaded by ${userId}`
            }));
            console.log('Knowledge Base ingestion job started:', { requestId, documentId });
        }
        catch (ingestionError) {
            // Handle ongoing ingestion job conflict gracefully
            if (ingestionError.name === 'ConflictException') {
                console.log('Knowledge Base ingestion job already in progress, document will be processed in next sync', { requestId });
                // Update metadata to indicate sync will happen later
                await dynamoClient.send(new client_dynamodb_1.PutItemCommand({
                    TableName: process.env.DOCUMENTS_TABLE,
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
                        s3Bucket: { S: process.env.DOCUMENTS_BUCKET },
                        status: { S: 'uploaded' },
                        knowledgeBaseStatus: { S: 'pending' },
                        GSI1PK: { S: `USER#${userId}` },
                        GSI1SK: { S: `DOC#${uploadDate}` },
                        syncNote: { S: 'Will be processed in next available ingestion job' }
                    }
                }));
            }
            else {
                console.error('Knowledge Base ingestion failed:', { requestId, error: ingestionError });
                throw ingestionError;
            }
        }
        const processingTime = Date.now() - startTime;
        console.log('Document upload completed successfully:', {
            requestId,
            documentId,
            processingTime: `${processingTime}ms`
        });
        return {
            statusCode: 200,
            headers: getCorsHeaders(),
            body: JSON.stringify({
                success: true,
                data: {
                    documentId,
                    fileName,
                    fileSize: fileBuffer.length,
                    status: 'uploaded',
                    knowledgeBaseStatus: 'pending',
                    message: 'Document uploaded successfully and Knowledge Base sync initiated',
                    processingTime: `${processingTime}ms`
                }
            })
        };
    }
    catch (error) {
        console.error('Document upload error:', error);
        // Handle specific error types
        if (error instanceof Error) {
            if (error.message.includes('Invalid file upload')) {
                return {
                    statusCode: 400,
                    headers: getCorsHeaders(),
                    body: JSON.stringify({
                        error: 'Invalid file upload format'
                    })
                };
            }
            if (error.message.includes('S3')) {
                return {
                    statusCode: 500,
                    headers: getCorsHeaders(),
                    body: JSON.stringify({
                        error: 'Upload failed - S3 error'
                    })
                };
            }
            if (error.message.includes('DynamoDB')) {
                return {
                    statusCode: 500,
                    headers: getCorsHeaders(),
                    body: JSON.stringify({
                        error: 'Metadata storage failed - DynamoDB error'
                    })
                };
            }
        }
        return {
            statusCode: 500,
            headers: getCorsHeaders(),
            body: JSON.stringify({
                success: false,
                error: {
                    message: 'Internal server error during document upload'
                }
            })
        };
    }
};
exports.handler = handler;
// Helper functions for better code organization
function validateAuthorization(event) {
    if (!event.requestContext?.authorizer?.claims?.sub) {
        return { isValid: false, reason: 'Missing user authentication in request context' };
    }
    const userId = event.requestContext.authorizer.claims.sub;
    if (!userId || typeof userId !== 'string') {
        return { isValid: false, reason: 'Invalid user ID in authentication claims' };
    }
    return { isValid: true, userId };
}
async function parseAndValidateFile(body, requestId) {
    // Parse multipart form data
    const fileData = await parseMultipartData(body);
    // Validate file type
    if (!SUPPORTED_MIME_TYPES.includes(fileData.contentType)) {
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
    if (!SUPPORTED_EXTENSIONS.includes(expectedExtension)) {
        console.warn('File extension mismatch:', {
            requestId,
            fileName: fileData.fileName,
            contentType: fileData.contentType,
            expectedExtension
        });
    }
    return fileData;
}
function createErrorResponse(statusCode, errorType, message) {
    return {
        statusCode,
        headers: getCorsHeaders(),
        body: JSON.stringify({
            error: message,
            errorType,
            timestamp: new Date().toISOString()
        })
    };
}
function createSuccessResponse(data) {
    return {
        statusCode: 200,
        headers: getCorsHeaders(),
        body: JSON.stringify({
            ...data,
            timestamp: new Date().toISOString()
        })
    };
}
function getCorsHeaders() {
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    };
}
function getFileExtension(fileName, contentType) {
    // Extract extension from filename first
    const fileExt = fileName.split('.').pop()?.toLowerCase();
    if (fileExt) {
        return `.${fileExt}`;
    }
    // Fallback to content type mapping
    const typeMap = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'text/markdown': '.md'
    };
    return typeMap[contentType] || '.bin';
}
async function parseMultipartData(body) {
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
//# sourceMappingURL=index.js.map