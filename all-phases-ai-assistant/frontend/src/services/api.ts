// API service functions for document management
// Handles all HTTP requests to the backend API

import { API_CONFIG } from '@/config/aws-config';
import {
    ApiResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadRequest,
    DocumentUploadResponse,
    FilterParams,
    KnowledgeBaseIngestionJob,
    PaginationParams,
    SortParams
} from '@/types/api';

// Base API client configuration
class ApiClient {
  private baseURL: string;
  private timeout: number;

  constructor() {
    this.baseURL = API_CONFIG.baseURL;
    this.timeout = API_CONFIG.timeout;
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const { fetchAuthSession } = await import('aws-amplify/auth');
      const session = await fetchAuthSession();
      
      if (!session.tokens?.idToken) {
        throw new Error('No valid session found');
      }
      
      const token = session.tokens.idToken.toString();
      
      return {
        'Authorization': token,
        'Content-Type': 'application/json'
      };
    } catch (error) {
      console.error('Failed to get auth headers:', error);
      throw new Error('Authentication required');
    }
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const headers = await this.getAuthHeaders();

    const config: RequestInit = {
      ...options,
      headers: {
        ...headers,
        ...options.headers
      },
      signal: AbortSignal.timeout(this.timeout)
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timeout');
        }
        throw error;
      }
      
      throw new Error('Unknown API error');
    }
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    const url = params ? `${endpoint}?${new URLSearchParams(params)}` : endpoint;
    return this.request<T>(url, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const config: RequestInit = {
      method: 'POST'
    };
    
    if (data) {
      config.body = JSON.stringify(data);
    }
    
    return this.request<T>(endpoint, config);
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const config: RequestInit = {
      method: 'PUT'
    };
    
    if (data) {
      config.body = JSON.stringify(data);
    }
    
    return this.request<T>(endpoint, config);
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  async uploadFile(endpoint: string, file: File, onProgress?: (progress: number) => void): Promise<ApiResponse<any>> {
    const headers = await this.getAuthHeaders();
    delete headers['Content-Type']; // Let browser set content-type for FormData

    const formData = new FormData();
    // Ensure filename is properly encoded for multipart form data
    formData.append('file', file, encodeURIComponent(file.name));

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = (event.loaded / event.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            reject(new Error('Invalid response format'));
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'));
      });

      xhr.addEventListener('timeout', () => {
        reject(new Error('Upload timeout'));
      });

      xhr.timeout = this.timeout;
      xhr.open('POST', `${this.baseURL}${endpoint}`);
      
      // Set auth headers
      Object.entries(headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });

      xhr.send(formData);
    });
  }
}

// Create API client instance
const apiClient = new ApiClient();

// Document API functions
export const documentApi = {
  // Get list of documents with filtering and pagination
  async getDocuments(
    params?: PaginationParams & FilterParams & SortParams
  ): Promise<DocumentListResponse> {
    const queryParams: Record<string, string> = {};
    
    if (params?.limit) queryParams.limit = params.limit.toString();
    if (params?.nextToken) queryParams.nextToken = params.nextToken;
    if (params?.status) queryParams.status = params.status;
    if (params?.knowledgeBaseStatus) queryParams.knowledgeBaseStatus = params.knowledgeBaseStatus;
    if (params?.uploadedBy) queryParams.uploadedBy = params.uploadedBy;
    if (params?.sortBy) queryParams.sortBy = params.sortBy;
    if (params?.sortOrder) queryParams.sortOrder = params.sortOrder;
    if (params?.dateRange) {
      queryParams.startDate = params.dateRange.start;
      queryParams.endDate = params.dateRange.end;
    }

    const response = await apiClient.get<DocumentListResponse>('/documents', queryParams);
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch documents');
    }
    
    return response.data;
  },

  // Get single document metadata
  async getDocument(documentId: string): Promise<DocumentMetadata> {
    const response = await apiClient.get<DocumentMetadata>(`/documents/${documentId}`);
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to fetch document');
    }
    
    return response.data;
  },

  // Request upload URL for new document
  async requestUpload(request: DocumentUploadRequest): Promise<DocumentUploadResponse> {
    const response = await apiClient.post<DocumentUploadResponse>('/documents', request);
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to request upload URL');
    }
    
    return response.data;
  },

  // Upload file directly
  async uploadDocument(
    file: File, 
    onProgress?: (progress: number) => void
  ): Promise<DocumentMetadata> {
    const response = await apiClient.uploadFile('/documents', file, onProgress);
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to upload document');
    }
    
    return response.data;
  },

  // Delete document
  async deleteDocument(documentId: string): Promise<void> {
    const response = await apiClient.delete(`/documents/${documentId}`);
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to delete document');
    }
  },

  // Get document processing status
  async getProcessingStatus(documentId: string): Promise<{
    status: string;
    knowledgeBaseStatus: string;
    processingErrors?: string[];
    lastSyncDate?: string;
  }> {
    // TODO: Individual document status endpoint not implemented yet
    // For now, use the general status endpoint and filter results
    try {
      const response = await apiClient.get<{
        statusSummary: any;
        processingDocuments: any[];
        ingestionJobs: any[];
      }>('/documents/status');
      
      if (!response.success || !response.data) {
        throw new Error(response.error?.message || 'Failed to get processing status');
      }
      
      // Find the specific document in processing documents
      const document = response.data.processingDocuments.find(
        (doc: any) => doc.documentId === documentId
      );
      
      if (document) {
        return {
          status: document.status || 'unknown',
          knowledgeBaseStatus: document.knowledgeBaseStatus || 'unknown',
          ...(document.failureReason && { processingErrors: [document.failureReason] }),
          ...(document.lastSyncDate && { lastSyncDate: document.lastSyncDate })
        };
      }
      
      // If not found in processing documents, assume it's completed or not started
      return {
        status: 'uploaded',
        knowledgeBaseStatus: 'pending'
      };
      
    } catch (error) {
      console.error('Failed to get document processing status:', error);
      // Return default status to prevent UI errors
      return {
        status: 'uploaded',
        knowledgeBaseStatus: 'pending'
      };
    }
  },

  // Trigger manual Knowledge Base sync
  async triggerSync(documentId?: string): Promise<KnowledgeBaseIngestionJob> {
    const endpoint = documentId 
      ? `/documents/${documentId}/sync`
      : '/admin/knowledge-base/sync';
      
    const response = await apiClient.post<KnowledgeBaseIngestionJob>(endpoint);
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to trigger sync');
    }
    
    return response.data;
  }
};

// Knowledge Base API functions
export const knowledgeBaseApi = {
  // Get ingestion job status
  async getIngestionJob(jobId: string): Promise<KnowledgeBaseIngestionJob> {
    const response = await apiClient.get<KnowledgeBaseIngestionJob>(`/admin/knowledge-base/jobs/${jobId}`);
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get ingestion job');
    }
    
    return response.data;
  },

  // Get recent ingestion jobs
  async getRecentJobs(limit: number = 10): Promise<KnowledgeBaseIngestionJob[]> {
    const response = await apiClient.get<KnowledgeBaseIngestionJob[]>(
      '/admin/knowledge-base/jobs',
      { limit: limit.toString() }
    );
    
    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get ingestion jobs');
    }
    
    return response.data;
  }
};

// Export default API client for custom requests
export default apiClient;