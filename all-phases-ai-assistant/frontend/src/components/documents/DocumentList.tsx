// Document List Component
// Displays documents with Knowledge Base ingestion status and management actions

import { FEATURE_FLAGS } from '@/config/aws-config';
import { useAuth } from '@/contexts/AuthContext';
import { documentApi } from '@/services/api';
import {
    DocumentMetadata,
    DocumentStatus,
    FilterParams,
    KnowledgeBaseStatus,
    PaginationParams,
    SortParams
} from '@/types/api';
import { AnimatePresence, motion } from 'framer-motion';
import {
    AlertCircle,
    Calendar,
    CheckCircle,
    Clock,
    Eye,
    FileIcon,
    FileText,
    Filter,
    HardDrive,
    Image,
    MoreVertical,
    RefreshCw,
    Search,
    Trash2,
    User
} from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

interface DocumentListProps {
  onDocumentSelect?: (document: DocumentMetadata) => void;
  onDocumentDelete?: (documentId: string) => void;
  refreshTrigger?: number;
  className?: string;
}

interface DocumentListState {
  documents: DocumentMetadata[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  nextToken?: string;
  totalCount: number;
}

interface FilterState extends FilterParams {
  searchQuery: string;
}

const getFileIcon = (fileName: string, size: string = 'w-6 h-6') => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'pdf':
      return <FileText className={`${size} text-red-500`} />;
    case 'docx':
    case 'doc':
      return <FileText className={`${size} text-blue-500`} />;
    case 'txt':
    case 'md':
      return <FileIcon className={`${size} text-gray-500`} />;
    case 'jpg':
    case 'jpeg':
    case 'png':
      return <Image className={`${size} text-green-500`} />;
    default:
      return <FileIcon className={`${size} text-gray-400`} />;
  }
};

const getStatusBadge = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus) => {
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
        <AlertCircle className="w-3 h-3 mr-1" />
        Upload Failed
      </span>
    );
  }
  
  if (kbStatus === 'failed') {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
        <AlertCircle className="w-3 h-3 mr-1" />
        Processing Failed
      </span>
    );
  }
  
  if (kbStatus === 'synced') {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
        <CheckCircle className="w-3 h-3 mr-1" />
        Ready
      </span>
    );
  }
  
  if (kbStatus === 'ingesting' || status === 'processing') {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
        <Clock className="w-3 h-3 mr-1 animate-spin" />
        Processing
      </span>
    );
  }
  
  return (
    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-500/20 text-gray-400 border border-gray-500/30">
      <Clock className="w-3 h-3 mr-1" />
      Pending
    </span>
  );
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 1) return 'Today';
  if (diffDays === 2) return 'Yesterday';
  if (diffDays <= 7) return `${diffDays - 1} days ago`;
  
  return date.toLocaleDateString();
};

export const DocumentList: React.FC<DocumentListProps> = ({
  onDocumentSelect,
  onDocumentDelete,
  refreshTrigger,
  className = ''
}) => {
  const { authState } = useAuth();
  const user = authState.user;
  const [state, setState] = useState<DocumentListState>({
    documents: [],
    loading: true,
    error: null,
    hasMore: false,
    totalCount: 0
  });

  const [filters, setFilters] = useState<FilterState>({
    searchQuery: ''
  });

  const [sortParams] = useState<SortParams>({
    sortBy: 'uploadDate',
    sortOrder: 'desc'
  });

  const [showFilters, setShowFilters] = useState(false);
  const [actionMenuOpen, setActionMenuOpen] = useState<string | null>(null);

  const loadDocuments = useCallback(async (reset: boolean = false) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));

      const params: PaginationParams & FilterParams & SortParams = {
        limit: FEATURE_FLAGS.documentListPageSize,
        ...sortParams
      };

      // Add filters
      if (filters.status) params.status = filters.status;
      if (filters.knowledgeBaseStatus) params.knowledgeBaseStatus = filters.knowledgeBaseStatus;
      if (filters.uploadedBy) params.uploadedBy = filters.uploadedBy;
      if (filters.dateRange) params.dateRange = filters.dateRange;

      // Add pagination
      if (!reset && state.nextToken) {
        params.nextToken = state.nextToken;
      }

      const response = await documentApi.getDocuments(params);

      setState(prev => ({
        ...prev,
        documents: reset ? response.documents : [...prev.documents, ...response.documents],
        hasMore: response.hasMore,
        totalCount: response.totalCount,
        loading: false,
        ...(response.nextToken && { nextToken: response.nextToken })
      }));
    } catch (error) {
      console.error('Failed to load documents:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to load documents',
        loading: false
      }));
    }
  }, [filters, sortParams, state.nextToken]);

  // Filter documents by search query (client-side) and ensure proper sorting
  const filteredDocuments = state.documents
    .filter(doc => {
      if (!filters.searchQuery) return true;
      const query = filters.searchQuery.toLowerCase();
      return (
        doc.fileName.toLowerCase().includes(query) ||
        doc.originalName.toLowerCase().includes(query) ||
        doc.uploadedBy.toLowerCase().includes(query)
      );
    })
    .sort((a, b) => {
      // Ensure documents are sorted by upload date descending
      const dateA = new Date(a.uploadDate).getTime();
      const dateB = new Date(b.uploadDate).getTime();
      return dateB - dateA; // Descending order (newest first)
    });

  useEffect(() => {
    loadDocuments(true);
  }, [filters.status, filters.knowledgeBaseStatus, filters.uploadedBy, filters.dateRange, sortParams]);

  useEffect(() => {
    if (refreshTrigger) {
      loadDocuments(true);
    }
  }, [refreshTrigger, loadDocuments]);

  const handleSearch = useCallback((query: string) => {
    setFilters(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const handleFilterChange = useCallback((newFilters: Partial<FilterState>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);



  const handleDocumentAction = useCallback(async (action: string, document: DocumentMetadata) => {
    setActionMenuOpen(null);
    
    try {
      switch (action) {
        case 'view':
          onDocumentSelect?.(document);
          break;
          
        case 'delete':
          if (window.confirm(`Are you sure you want to delete "${document.fileName}"? This will also remove it from the Knowledge Base.`)) {
            await documentApi.deleteDocument(document.documentId);
            onDocumentDelete?.(document.documentId);
            loadDocuments(true);
          }
          break;
          
        case 'refresh':
          await documentApi.triggerSync(document.documentId);
          // Refresh the document list after a short delay
          setTimeout(() => loadDocuments(true), 1000);
          break;
          
        default:
          console.warn('Unknown action:', action);
      }
    } catch (error) {
      console.error('Document action failed:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Action failed'
      }));
    }
  }, [onDocumentSelect, onDocumentDelete, loadDocuments]);

  const handleLoadMore = useCallback(() => {
    if (state.hasMore && !state.loading) {
      loadDocuments(false);
    }
  }, [state.hasMore, state.loading, loadDocuments]);

  const canDeleteDocument = (document: DocumentMetadata): boolean => {
    return user?.['custom:role'] === 'admin' || document.uploadedBy === user?.sub;
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Documents</h2>
          <p className="text-gray-400">
            {state.totalCount} document{state.totalCount !== 1 ? 's' : ''} in knowledge base
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <Filter className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => loadDocuments(true)}
            disabled={state.loading}
            className="p-2 bg-gray-700 text-gray-300 hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${state.loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          placeholder="Search documents..."
          value={filters.searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-gray-800/50 rounded-lg p-4 border border-gray-700"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Upload Status
                </label>
                <select
                  value={filters.status || ''}
                  onChange={(e) => handleFilterChange({ 
                    status: e.target.value as DocumentStatus || undefined 
                  })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="uploading">Uploading</option>
                  <option value="uploaded">Uploaded</option>
                  <option value="processing">Processing</option>
                  <option value="ready">Ready</option>
                  <option value="failed">Failed</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Knowledge Base Status
                </label>
                <select
                  value={filters.knowledgeBaseStatus || ''}
                  onChange={(e) => handleFilterChange({ 
                    knowledgeBaseStatus: e.target.value as KnowledgeBaseStatus || undefined 
                  })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All KB Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="ingesting">Processing</option>
                  <option value="synced">Synced</option>
                  <option value="failed">Failed</option>
                </select>
              </div>

              {user?.['custom:role'] === 'admin' && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Uploaded By
                  </label>
                  <input
                    type="text"
                    placeholder="User ID or email"
                    value={filters.uploadedBy || ''}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value) {
                        handleFilterChange({ uploadedBy: value });
                      } else {
                        const { uploadedBy, ...rest } = filters;
                        setFilters(rest);
                      }
                    }}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Display */}
      {state.error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/10 border border-red-500/20 rounded-lg p-4"
        >
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{state.error}</span>
          </div>
        </motion.div>
      )}

      {/* Document List */}
      <div className="space-y-3">
        <AnimatePresence>
          {filteredDocuments.map((document, index) => (
            <motion.div
              key={document.documentId}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: index * 0.05 }}
              className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4 flex-1 min-w-0">
                  {getFileIcon(document.fileName)}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-1">
                      <h3 className="text-white font-medium truncate">
                        {document.originalName}
                      </h3>
                      {getStatusBadge(document.status, document.knowledgeBaseStatus)}
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-400">
                      <div className="flex items-center space-x-1">
                        <HardDrive className="w-4 h-4" />
                        <span>{formatFileSize(document.fileSize)}</span>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(document.uploadDate)}</span>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        <User className="w-4 h-4" />
                        <span className="truncate max-w-32">
                          {document.uploadedBy === user?.sub ? 'You' : document.uploadedBy}
                        </span>
                      </div>
                    </div>

                    {/* Processing Errors */}
                    {document.processingErrors && document.processingErrors.length > 0 && (
                      <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs">
                        <div className="flex items-center space-x-1 text-red-400 mb-1">
                          <AlertCircle className="w-3 h-3" />
                          <span className="font-medium">Processing Errors:</span>
                        </div>
                        {document.processingErrors.map((error, idx) => (
                          <p key={idx} className="text-red-300 ml-4">• {error}</p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions Menu */}
                <div className="relative">
                  <button
                    onClick={() => setActionMenuOpen(
                      actionMenuOpen === document.documentId ? null : document.documentId
                    )}
                    className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    <MoreVertical className="w-5 h-5" />
                  </button>

                  <AnimatePresence>
                    {actionMenuOpen === document.documentId && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="absolute right-0 top-full mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10"
                      >
                        <div className="py-1">
                          <button
                            onClick={() => handleDocumentAction('view', document)}
                            className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 hover:text-white flex items-center space-x-2"
                          >
                            <Eye className="w-4 h-4" />
                            <span>View Details</span>
                          </button>

                          {document.knowledgeBaseStatus !== 'synced' && (
                            <button
                              onClick={() => handleDocumentAction('refresh', document)}
                              className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 hover:text-white flex items-center space-x-2"
                            >
                              <RefreshCw className="w-4 h-4" />
                              <span>Retry Processing</span>
                            </button>
                          )}

                          {canDeleteDocument(document) && (
                            <button
                              onClick={() => handleDocumentAction('delete', document)}
                              className="w-full px-4 py-2 text-left text-red-400 hover:bg-red-500/10 hover:text-red-300 flex items-center space-x-2"
                            >
                              <Trash2 className="w-4 h-4" />
                              <span>Delete</span>
                            </button>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Empty State */}
        {!state.loading && filteredDocuments.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
          >
            <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-400 mb-2">
              {filters.searchQuery ? 'No matching documents' : 'No documents yet'}
            </h3>
            <p className="text-gray-500">
              {filters.searchQuery 
                ? 'Try adjusting your search or filters'
                : 'Upload your first document to get started'
              }
            </p>
          </motion.div>
        )}

        {/* Load More */}
        {state.hasMore && (
          <div className="text-center pt-4">
            <button
              onClick={handleLoadMore}
              disabled={state.loading}
              className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {state.loading ? 'Loading...' : 'Load More'}
            </button>
          </div>
        )}

        {/* Loading State */}
        {state.loading && state.documents.length === 0 && (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 animate-pulse">
                <div className="flex items-center space-x-4">
                  <div className="w-6 h-6 bg-gray-700 rounded"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-700 rounded w-1/3"></div>
                    <div className="h-3 bg-gray-700 rounded w-1/2"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};