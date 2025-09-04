// Document Upload Component
// Handles file upload with drag-and-drop and Knowledge Base sync status

import { FEATURE_FLAGS } from '@/config/aws-config';
import { documentApi } from '@/services/api';
import { DocumentMetadata, DocumentStatus, KnowledgeBaseStatus } from '@/types/api';
import { AnimatePresence, motion } from 'framer-motion';
import {
    AlertCircle,
    CheckCircle,
    Clock,
    File,
    FileIcon,
    FileText,
    Image,
    Upload,
    X
} from 'lucide-react';
import React, { useCallback, useRef, useState } from 'react';

interface DocumentUploadProps {
  onUploadComplete?: (documents: DocumentMetadata[]) => void;
  onUploadError?: (error: string) => void;
  className?: string;
}

interface UploadingFile {
  file: File;
  id: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
  documentMetadata?: DocumentMetadata;
}

const getFileIcon = (fileName: string) => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'pdf':
      return <FileText className="w-8 h-8 text-red-500" />;
    case 'docx':
    case 'doc':
      return <FileText className="w-8 h-8 text-blue-500" />;
    case 'txt':
    case 'md':
      return <FileIcon className="w-8 h-8 text-gray-500" />;
    case 'jpg':
    case 'jpeg':
    case 'png':
      return <Image className="w-8 h-8 text-green-500" />;
    default:
      return <File className="w-8 h-8 text-gray-400" />;
  }
};

const getStatusColor = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus) => {
  if (status === 'failed') return 'text-red-400';
  if (kbStatus === 'failed') return 'text-red-400';
  if (kbStatus === 'synced') return 'text-green-400';
  if (kbStatus === 'ingesting' || status === 'processing') return 'text-yellow-400';
  return 'text-gray-400';
};

const getStatusIcon = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus) => {
  if (status === 'failed' || kbStatus === 'failed') {
    return <AlertCircle className="w-4 h-4 text-red-400" />;
  }
  if (kbStatus === 'synced') {
    return <CheckCircle className="w-4 h-4 text-green-400" />;
  }
  if (kbStatus === 'ingesting' || status === 'processing') {
    return <Clock className="w-4 h-4 text-yellow-400 animate-spin" />;
  }
  return <Clock className="w-4 h-4 text-gray-400" />;
};

const getStatusText = (status: DocumentStatus, kbStatus: KnowledgeBaseStatus) => {
  if (status === 'failed') return 'Upload failed';
  if (kbStatus === 'failed') return 'Processing failed';
  if (kbStatus === 'synced') return 'Ready for queries';
  if (kbStatus === 'ingesting') return 'Processing for AI...';
  if (status === 'processing') return 'Processing...';
  if (status === 'uploaded') return 'Uploaded, waiting for processing';
  return 'Uploading...';
};

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  onUploadError,
  className = ''
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > FEATURE_FLAGS.maxFileSize) {
      return `File size exceeds ${FEATURE_FLAGS.maxFileSize / (1024 * 1024)}MB limit`;
    }

    // Check file type
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!FEATURE_FLAGS.supportedFileTypes.includes(extension)) {
      return `File type ${extension} not supported. Supported types: ${FEATURE_FLAGS.supportedFileTypes.join(', ')}`;
    }

    return null;
  };

  const handleFiles = useCallback(async (files: FileList) => {
    const fileArray = Array.from(files);
    
    // Validate file count
    if (fileArray.length > FEATURE_FLAGS.maxFilesPerUpload) {
      onUploadError?.(`Maximum ${FEATURE_FLAGS.maxFilesPerUpload} files allowed per upload`);
      return;
    }

    // Validate each file
    const validFiles: File[] = [];
    for (const file of fileArray) {
      const error = validateFile(file);
      if (error) {
        onUploadError?.(error);
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length === 0) return;

    // Create uploading file entries
    const newUploadingFiles: UploadingFile[] = validFiles.map(file => ({
      file,
      id: `${encodeURIComponent(file.name)}-${Date.now()}-${Math.random()}`,
      progress: 0,
      status: 'uploading'
    }));

    setUploadingFiles(prev => [...prev, ...newUploadingFiles]);

    // Upload files
    const uploadPromises = newUploadingFiles.map(async (uploadingFile) => {
      try {
        const documentMetadata = await documentApi.uploadDocument(
          uploadingFile.file,
          (progress) => {
            setUploadingFiles(prev => 
              prev.map(f => 
                f.id === uploadingFile.id 
                  ? { ...f, progress }
                  : f
              )
            );
          }
        );

        // Update status to processing
        setUploadingFiles(prev => 
          prev.map(f => 
            f.id === uploadingFile.id 
              ? { 
                  ...f, 
                  status: 'processing', 
                  progress: 100,
                  documentMetadata 
                }
              : f
          )
        );

        // Poll for Knowledge Base sync status
        await pollKnowledgeBaseStatus(uploadingFile.id, documentMetadata.documentId);

        return documentMetadata;
      } catch (error) {
        console.error('Upload failed:', error);
        
        setUploadingFiles(prev => 
          prev.map(f => 
            f.id === uploadingFile.id 
              ? { 
                  ...f, 
                  status: 'error', 
                  error: error instanceof Error ? error.message : 'Upload failed'
                }
              : f
          )
        );
        
        onUploadError?.(error instanceof Error ? error.message : 'Upload failed');
        return null;
      }
    });

    try {
      const results = await Promise.allSettled(uploadPromises);
      const successfulUploads = results
        .filter((result): result is PromiseFulfilledResult<DocumentMetadata> => 
          result.status === 'fulfilled' && result.value !== null
        )
        .map(result => result.value);

      if (successfulUploads.length > 0) {
        onUploadComplete?.(successfulUploads);
      }
    } catch (error) {
      console.error('Upload batch failed:', error);
    }
  }, [onUploadComplete, onUploadError]);

  const pollKnowledgeBaseStatus = async (uploadId: string, documentId: string) => {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await documentApi.getProcessingStatus(documentId);
        
        setUploadingFiles(prev => 
          prev.map(f => {
            if (f.id === uploadId && f.documentMetadata) {
              return {
                ...f,
                documentMetadata: {
                  ...f.documentMetadata,
                  status: status.status as DocumentStatus,
                  knowledgeBaseStatus: status.knowledgeBaseStatus as KnowledgeBaseStatus,
                  processingErrors: status.processingErrors || [],
                  ...(status.lastSyncDate && { lastSyncDate: status.lastSyncDate })
                }
              };
            }
            return f;
          })
        );

        // Check if processing is complete
        if (status.knowledgeBaseStatus === 'synced' || status.knowledgeBaseStatus === 'failed') {
          setUploadingFiles(prev => 
            prev.map(f => 
              f.id === uploadId 
                ? { ...f, status: 'completed' }
                : f
            )
          );
          return;
        }

        // Continue polling if not complete and under max attempts
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          // Timeout - mark as completed but may still be processing
          setUploadingFiles(prev => 
            prev.map(f => 
              f.id === uploadId 
                ? { ...f, status: 'completed' }
                : f
            )
          );
        }
      } catch (error) {
        console.error('Failed to poll status:', error);
        // Continue polling on error, but don't fail the upload
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        }
      }
    };

    // Start polling after a short delay
    setTimeout(poll, 2000);
  };

  const removeUploadingFile = (id: string) => {
    setUploadingFiles(prev => prev.filter(f => f.id !== id));
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFiles(files);
    }
  }, [handleFiles]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFiles(files);
    }
    // Reset input value to allow selecting the same file again
    e.target.value = '';
  }, [handleFiles]);

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Upload Area */}
      <motion.div
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
          ${isDragOver 
            ? 'border-blue-400 bg-blue-500/10' 
            : 'border-gray-600 hover:border-gray-500'
          }
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={FEATURE_FLAGS.supportedFileTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="space-y-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-blue-500 to-cyan-500 shadow-lg">
            <Upload className="w-8 h-8 text-white" />
          </div>
          
          <div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Upload Documents
            </h3>
            <p className="text-gray-400 mb-4">
              Drag and drop files here, or click to browse
            </p>
            
            <motion.button
              onClick={openFileDialog}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Choose Files
            </motion.button>
          </div>

          <div className="text-sm text-gray-500 space-y-1">
            <p>Supported formats: {FEATURE_FLAGS.supportedFileTypes.join(', ')}</p>
            <p>Maximum file size: {FEATURE_FLAGS.maxFileSize / (1024 * 1024)}MB</p>
            <p>Maximum files per upload: {FEATURE_FLAGS.maxFilesPerUpload}</p>
          </div>
        </div>
      </motion.div>

      {/* Upload Progress */}
      <AnimatePresence>
        {uploadingFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-3"
          >
            <h4 className="text-lg font-medium text-white">Upload Progress</h4>
            
            {uploadingFiles.map((uploadingFile) => (
              <motion.div
                key={uploadingFile.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="bg-gray-800/50 rounded-lg p-4 border border-gray-700"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    {getFileIcon(uploadingFile.file.name)}
                    <div>
                      <p className="text-white font-medium truncate max-w-xs">
                        {uploadingFile.file.name}
                      </p>
                      <p className="text-sm text-gray-400">
                        {(uploadingFile.file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    {uploadingFile.documentMetadata && (
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(
                          uploadingFile.documentMetadata.status,
                          uploadingFile.documentMetadata.knowledgeBaseStatus
                        )}
                        <span className={`text-sm ${getStatusColor(
                          uploadingFile.documentMetadata.status,
                          uploadingFile.documentMetadata.knowledgeBaseStatus
                        )}`}>
                          {getStatusText(
                            uploadingFile.documentMetadata.status,
                            uploadingFile.documentMetadata.knowledgeBaseStatus
                          )}
                        </span>
                      </div>
                    )}
                    
                    {uploadingFile.status === 'completed' && (
                      <button
                        onClick={() => removeUploadingFile(uploadingFile.id)}
                        className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress Bar */}
                {uploadingFile.status === 'uploading' && (
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <motion.div
                      className="bg-blue-500 h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${uploadingFile.progress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                )}

                {/* Knowledge Base Processing Indicator */}
                {uploadingFile.documentMetadata && 
                 uploadingFile.documentMetadata.knowledgeBaseStatus === 'ingesting' && (
                  <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-yellow-400 animate-spin" />
                      <span className="text-sm text-yellow-400">
                        Processing document for AI search...
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      This may take a few minutes. You can continue using the app.
                    </p>
                  </div>
                )}

                {/* Error Display */}
                {uploadingFile.error && (
                  <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <AlertCircle className="w-4 h-4 text-red-400" />
                      <span className="text-sm text-red-400">
                        {uploadingFile.error}
                      </span>
                    </div>
                  </div>
                )}

                {/* Processing Errors */}
                {uploadingFile.documentMetadata?.processingErrors && 
                 uploadingFile.documentMetadata.processingErrors.length > 0 && (
                  <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <div className="flex items-center space-x-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-red-400" />
                      <span className="text-sm text-red-400 font-medium">
                        Processing Errors:
                      </span>
                    </div>
                    {uploadingFile.documentMetadata.processingErrors.map((error, index) => (
                      <p key={index} className="text-xs text-red-300 ml-6">
                        • {error}
                      </p>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};