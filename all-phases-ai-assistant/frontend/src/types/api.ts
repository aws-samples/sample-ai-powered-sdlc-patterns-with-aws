// TypeScript interfaces for Knowledge Base API responses
// These interfaces define the structure of data returned from AWS services

// Base API Response structure
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    requestId?: string;
  };
  timestamp: string;
}

// Document-related interfaces
export interface DocumentMetadata {
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
  processingErrors?: string[];
  lastSyncDate?: string;
}

export type DocumentStatus = 'uploading' | 'uploaded' | 'processing' | 'ready' | 'failed';
export type KnowledgeBaseStatus = 'pending' | 'ingesting' | 'synced' | 'failed';

export interface DocumentUploadRequest {
  fileName: string;
  contentType: string;
  fileSize: number;
}

export interface DocumentUploadResponse {
  documentId: string;
  uploadUrl: string;
  status: DocumentStatus;
  expiresIn: number;
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
  totalCount: number;
  hasMore: boolean;
  nextToken?: string;
}

// Chat-related interfaces
export interface ChatMessage {
  messageId: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: DocumentSource[];
  modelUsed?: string;
}

export interface DocumentSource {
  documentId: string;
  fileName: string;
  excerpt: string;
  confidence: number;
  s3Location?: string;
  pageNumber?: number;
  chunkId?: string;
}

export interface ChatRequest {
  question: string;
  conversationId?: string;
  maxResults?: number;
  includeSourceDetails?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: DocumentSource[];
  conversationId: string;
  timestamp: string;
  modelUsed: string;
  tokenUsage?: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  processingTime?: number;
}

export interface ConversationHistory {
  conversationId: string;
  userId: string;
  messages: ChatMessage[];
  createdAt: string;
  lastActivity: string;
  totalMessages: number;
}

// Knowledge Base specific interfaces
export interface KnowledgeBaseIngestionJob {
  jobId: string;
  knowledgeBaseId: string;
  dataSourceId: string;
  status: IngestionJobStatus;
  startedAt: string;
  completedAt?: string;
  failureReasons?: string[];
  statistics?: {
    numberOfDocumentsScanned: number;
    numberOfDocumentsIndexed: number;
    numberOfDocumentsFailed: number;
  };
}

export type IngestionJobStatus = 
  | 'STARTING' 
  | 'IN_PROGRESS' 
  | 'COMPLETE' 
  | 'FAILED' 
  | 'STOPPING' 
  | 'STOPPED';

export interface KnowledgeBaseMetrics {
  totalDocuments: number;
  documentsReady: number;
  documentsProcessing: number;
  documentsFailed: number;
  lastSyncDate?: string;
  averageProcessingTime?: number;
  storageUsed?: number;
}

// Authentication interfaces
export interface CognitoUser {
  sub: string;
  email: string;
  email_verified: boolean;
  'custom:role': UserRole;
  'custom:department'?: string | undefined;
  'cognito:username': string;
}

export type UserRole = 'admin' | 'user';

export interface AuthenticationState {
  isAuthenticated: boolean;
  user?: CognitoUser | undefined;
  accessToken?: string | undefined;
  idToken?: string | undefined;
  refreshToken?: string | undefined;
  expiresAt?: number | undefined;
}

// Error interfaces
export interface KnowledgeBaseError {
  type: KnowledgeBaseErrorType;
  message: string;
  requestId?: string;
  timestamp: string;
  retryable: boolean;
}

export enum KnowledgeBaseErrorType {
  KNOWLEDGE_BASE_NOT_FOUND = 'KNOWLEDGE_BASE_NOT_FOUND',
  RETRIEVAL_FAILED = 'RETRIEVAL_FAILED',
  GENERATION_FAILED = 'GENERATION_FAILED',
  INSUFFICIENT_CONTEXT = 'INSUFFICIENT_CONTEXT',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  DOCUMENT_PROCESSING_FAILED = 'DOCUMENT_PROCESSING_FAILED',
  AUTHENTICATION_FAILED = 'AUTHENTICATION_FAILED',
  AUTHORIZATION_FAILED = 'AUTHORIZATION_FAILED',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INTERNAL_ERROR = 'INTERNAL_ERROR'
}

// Admin interfaces
export interface AdminDashboardData {
  knowledgeBaseMetrics: KnowledgeBaseMetrics;
  recentIngestionJobs: KnowledgeBaseIngestionJob[];
  userActivity: {
    totalUsers: number;
    activeUsers: number;
    totalQueries: number;
    averageResponseTime: number;
  };
  systemHealth: {
    knowledgeBaseStatus: 'healthy' | 'degraded' | 'unhealthy';
    apiGatewayStatus: 'healthy' | 'degraded' | 'unhealthy';
    lambdaStatus: 'healthy' | 'degraded' | 'unhealthy';
  };
}

export interface UserManagementData {
  users: CognitoUser[];
  totalCount: number;
  hasMore: boolean;
  nextToken?: string;
}

// Configuration interfaces
export interface FrontendConfig {
  aws_region: string;
  cognito_user_pool_id: string;
  cognito_user_pool_client_id: string;
  cognito_user_pool_domain: string;
  api_gateway_url: string;
  cloudfront_url: string;
  environment: string;
  project_name: string;
}

// Utility types
export interface PaginationParams {
  limit?: number;
  nextToken?: string;
}

export interface SortParams {
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface FilterParams {
  status?: DocumentStatus;
  knowledgeBaseStatus?: KnowledgeBaseStatus;
  uploadedBy?: string;
  dateRange?: {
    start: string;
    end: string;
  };
}

// API endpoint types
export type ApiEndpoint = 
  | '/api/documents'
  | '/api/documents/upload'
  | '/api/documents/{id}'
  | '/api/chat/ask'
  | '/api/chat/history'
  | '/api/admin/knowledge-base/status'
  | '/api/admin/knowledge-base/sync'
  | '/api/admin/users'
  | '/api/admin/metrics';

// HTTP method types
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// Request configuration
export interface RequestConfig {
  method: HttpMethod;
  endpoint: ApiEndpoint;
  data?: any;
  params?: Record<string, string>;
  headers?: Record<string, string>;
  timeout?: number;
}

// WebSocket message types for real-time updates
export interface WebSocketMessage {
  type: WebSocketMessageType;
  data: any;
  timestamp: string;
}

export enum WebSocketMessageType {
  DOCUMENT_PROCESSING_UPDATE = 'DOCUMENT_PROCESSING_UPDATE',
  INGESTION_JOB_UPDATE = 'INGESTION_JOB_UPDATE',
  CHAT_RESPONSE_CHUNK = 'CHAT_RESPONSE_CHUNK',
  SYSTEM_NOTIFICATION = 'SYSTEM_NOTIFICATION'
}