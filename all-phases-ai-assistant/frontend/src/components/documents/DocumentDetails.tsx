// Document Details Modal Component
// Shows detailed information about a document including Knowledge Base status

import { useAuth } from '@/contexts/AuthContext';
import { documentApi } from '@/services/api';
import {
    DocumentMetadata,
    DocumentStatus,
    KnowledgeBaseIngestionJob,
    KnowledgeBaseStatus
} from '@/types/api';
import { AnimatePresence, motion } from 'framer-motion';
import {
    AlertCircle,
    Calendar,
    CheckCircle,
    Clock,
    Database,
    ExternalLink,
    FileText,
    HardDrive,
    RefreshCw,
    Trash2,
    User,
    X,
    Zap
} from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface DocumentDetailsProps {
  document: DocumentMetadata;
  isOpen: boolean;
  onClose: () => void;
  onDelete?: (documentId: string) => void;
  onRefresh?: () => void;
}

interface DocumentDetailsState {
  loading: boolean;
  error: string | null;
  ingestionJobs: KnowledgeBaseIngestionJob[];
  refreshingStatus: boolean;
}

const getStatusIcon = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus, size: string = 'w-5 h-5') => {
  if (status === 'failed' || kbStatus === 'failed') {
    return <AlertCircle className={`${size} text-red-400`} />;
  }
  if (kbStatus === 'synced') {
    return <CheckCircle className={`${size} text-green-400`} />;
  }
  if (kbStatus === 'ingesting' || status === 'processing') {
    return <Clock className={`${size} text-yellow-400 animate-spin`} />;
  }
  return <Clock className={`${size} text-gray-400`} />;
};

const getStatusText = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus) => {
  if (status === 'failed') return 'Upload failed';
  if (kbStatus === 'failed') return 'Processing failed';
  if (kbStatus === 'synced') return 'Ready for AI queries';
  if (kbStatus === 'ingesting') return 'Processing for AI search...';
  if (status === 'processing') return 'Processing document...';
  if (status === 'uploaded') return 'Uploaded, waiting for processing';
  return 'Uploading...';
};

const getStatusColor = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus) => {
  if (status === 'failed' || kbStatus === 'failed') return 'text-red-400';
  if (kbStatus === 'synced') return 'text-green-400';
  if (kbStatus === 'ingesting' || status === 'processing') return 'text-yellow-400';
  return 'text-gray-400';
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

const formatDuration = (startTime: string, endTime?: string): string => {
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffSecs = Math.floor((diffMs % (1000 * 60)) / 1000);
  
  if (diffMins > 0) {
    return `${diffMins}m ${diffSecs}s`;
  }
  return `${diffSecs}s`;
};

export const DocumentDetails: React.FC<DocumentDetailsProps> = ({
  document: initialDocument,
  isOpen,
  onClose,
  onDelete,
  onRefresh
}) => {
  const { authState } = useAuth();
  const user = authState.user;
  const [document, setDocument] = useState(initialDocument);
  const [state, setState] = useState<DocumentDetailsState>({
    loading: false,
    error: null,
    ingestionJobs: [],
    refreshingStatus: false
  });

  useEffect(() => {
    setDocument(initialDocument);
  }, [initialDocument]);

  useEffect(() => {
    if (isOpen && document.documentId) {
      loadIngestionJobs();
    }
  }, [isOpen, document.documentId]);

  const loadIngestionJobs = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      // TODO: Admin endpoints not implemented yet (Tasks 14-16)
      // For now, skip loading ingestion jobs to avoid CORS errors
      // const jobs = await knowledgeBaseApi.getRecentJobs(5);
      
      setState(prev => ({
        ...prev,
        ingestionJobs: [], // Empty array until admin endpoints are implemented
        loading: false
      }));
    } catch (error) {
      console.error('Failed to load ingestion jobs:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to load ingestion jobs',
        loading: false
      }));
    }
  };

  const refreshDocumentStatus = async () => {
    try {
      setState(prev => ({ ...prev, refreshingStatus: true }));
      
      const status = await documentApi.getProcessingStatus(document.documentId);
      
      setDocument(prev => ({
        ...prev,
        status: status.status as DocumentStatus,
        knowledgeBaseStatus: status.knowledgeBaseStatus as KnowledgeBaseStatus,
        processingErrors: status.processingErrors || [],
        ...(status.lastSyncDate && { lastSyncDate: status.lastSyncDate })
      }));
      
      // Reload ingestion jobs
      await loadIngestionJobs();
      
      setState(prev => ({ ...prev, refreshingStatus: false }));
    } catch (error) {
      console.error('Failed to refresh status:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to refresh status',
        refreshingStatus: false
      }));
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete "${document.fileName}"? This will also remove it from the Knowledge Base and cannot be undone.`)) {
      return;
    }

    try {
      await documentApi.deleteDocument(document.documentId);
      onDelete?.(document.documentId);
      onClose();
    } catch (error) {
      console.error('Failed to delete document:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to delete document'
      }));
    }
  };

  const handleRetryProcessing = async () => {
    try {
      await documentApi.triggerSync(document.documentId);
      
      // Refresh status after a short delay
      setTimeout(() => {
        refreshDocumentStatus();
        onRefresh?.();
      }, 1000);
    } catch (error) {
      console.error('Failed to retry processing:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to retry processing'
      }));
    }
  };

  const canDeleteDocument = (): boolean => {
    return user?.['custom:role'] === 'admin' || document.uploadedBy === user?.sub;
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="bg-gray-900 rounded-xl border border-gray-700 shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <div className="flex items-center space-x-3">
              <FileText className="w-6 h-6 text-blue-400" />
              <div>
                <h2 className="text-xl font-semibold text-white truncate">
                  {document.originalName}
                </h2>
                <p className="text-sm text-gray-400">Document Details</p>
              </div>
            </div>
            
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {/* Error Display */}
            {state.error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 bg-red-500/10 border border-red-500/20 rounded-lg p-4"
              >
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                  <span className="text-red-400">{state.error}</span>
                </div>
              </motion.div>
            )}

            {/* Status Section */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">Status</h3>
                <button
                  onClick={refreshDocumentStatus}
                  disabled={state.refreshingStatus}
                  className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${state.refreshingStatus ? 'animate-spin' : ''}`} />
                </button>
              </div>

              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center space-x-3 mb-3">
                  {getStatusIcon(document.status, document.knowledgeBaseStatus)}
                  <span className={`font-medium ${getStatusColor(document.status, document.knowledgeBaseStatus)}`}>
                    {getStatusText(document.status, document.knowledgeBaseStatus)}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Upload Status:</span>
                    <span className="ml-2 text-white capitalize">{document.status}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Knowledge Base:</span>
                    <span className="ml-2 text-white capitalize">{document.knowledgeBaseStatus}</span>
                  </div>
                </div>

                {document.lastSyncDate && (
                  <div className="mt-3 text-sm">
                    <span className="text-gray-400">Last Sync:</span>
                    <span className="ml-2 text-white">{formatDateTime(document.lastSyncDate)}</span>
                  </div>
                )}
              </div>

              {/* Processing Errors */}
              {document.processingErrors && document.processingErrors.length > 0 && (
                <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <AlertCircle className="w-5 h-5 text-red-400" />
                    <span className="text-red-400 font-medium">Processing Errors</span>
                  </div>
                  <div className="space-y-1">
                    {document.processingErrors.map((error, index) => (
                      <p key={index} className="text-sm text-red-300">
                        • {error}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* File Information */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-white mb-4">File Information</h3>
              
              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">File Name:</span>
                    <span className="text-white truncate">{document.fileName}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <HardDrive className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">Size:</span>
                    <span className="text-white">{formatFileSize(document.fileSize)}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">Uploaded:</span>
                    <span className="text-white">{formatDateTime(document.uploadDate)}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">Uploaded By:</span>
                    <span className="text-white">
                      {document.uploadedBy === user?.sub ? 'You' : document.uploadedBy}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Database className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">Content Type:</span>
                    <span className="text-white">{document.contentType}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <ExternalLink className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">Document ID:</span>
                    <span className="text-white font-mono text-xs truncate">{document.documentId}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Knowledge Base Processing */}
            {state.ingestionJobs.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-medium text-white mb-4">Recent Processing Jobs</h3>
                
                <div className="space-y-3">
                  {state.ingestionJobs.map((job) => (
                    <div key={job.jobId} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <Zap className="w-4 h-4 text-blue-400" />
                          <span className="text-white font-medium">Ingestion Job</span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            job.status === 'COMPLETE' ? 'bg-green-500/20 text-green-400' :
                            job.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                            job.status === 'IN_PROGRESS' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-gray-500/20 text-gray-400'
                          }`}>
                            {job.status}
                          </span>
                        </div>
                        <span className="text-xs text-gray-400 font-mono">
                          {job.jobId.slice(-8)}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-400">Started:</span>
                          <span className="ml-2 text-white">{formatDateTime(job.startedAt)}</span>
                        </div>
                        {job.completedAt && (
                          <div>
                            <span className="text-gray-400">Duration:</span>
                            <span className="ml-2 text-white">{formatDuration(job.startedAt, job.completedAt)}</span>
                          </div>
                        )}
                      </div>

                      {job.statistics && (
                        <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-gray-400">Scanned:</span>
                            <span className="ml-2 text-white">{job.statistics.numberOfDocumentsScanned}</span>
                          </div>
                          <div>
                            <span className="text-gray-400">Indexed:</span>
                            <span className="ml-2 text-white">{job.statistics.numberOfDocumentsIndexed}</span>
                          </div>
                          <div>
                            <span className="text-gray-400">Failed:</span>
                            <span className="ml-2 text-white">{job.statistics.numberOfDocumentsFailed}</span>
                          </div>
                        </div>
                      )}

                      {job.failureReasons && job.failureReasons.length > 0 && (
                        <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded">
                          <div className="text-sm text-red-400 font-medium mb-1">Failure Reasons:</div>
                          {job.failureReasons.map((reason, index) => (
                            <p key={index} className="text-xs text-red-300">• {reason}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between p-6 border-t border-gray-700">
            <div className="flex items-center space-x-3">
              {(document.knowledgeBaseStatus === 'failed' || document.status === 'failed') && (
                <button
                  onClick={handleRetryProcessing}
                  className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Retry Processing</span>
                </button>
              )}
            </div>

            <div className="flex items-center space-x-3">
              {canDeleteDocument() && (
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Delete</span>
                </button>
              )}
              
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};