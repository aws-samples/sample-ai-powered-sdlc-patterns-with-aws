// Custom hook for managing code download operations
// Provides state management and progress tracking for code downloads

import { useState, useCallback, useRef } from 'react';
import {
  fetchAvailableCodeFiles,
  downloadIndividualFile,
  downloadProjectZip,
  downloadSelectedFilesZip,
  triggerBlobDownload,
  getDownloadMetadata,
  CodeDownloadError
} from '../services/codeDownloadService';

/**
 * Custom hook for code download operations
 * @param {string} projectId - The project identifier
 * @returns {Object} - Hook state and methods
 */
export const useCodeDownload = (projectId) => {
  // State management
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [downloadProgress, setDownloadProgress] = useState(null);
  const [metadata, setMetadata] = useState(null);

  // Refs for cleanup
  const abortControllerRef = useRef(null);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Handle progress updates
   */
  const handleProgress = useCallback((progress) => {
    setDownloadProgress(progress);
  }, []);

  /**
   * Load available code files
   */
  const loadFiles = useCallback(async () => {
    if (!projectId) {
      setError('Project ID is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetchAvailableCodeFiles(projectId);
      
      if (response.success) {
        setFiles(response.files || []);
        setMetadata({
          projectName: response.projectName,
          generatedAt: response.generatedAt,
          totalFiles: response.totalFiles,
          totalSize: response.totalSize,
          zipDownloadUrl: response.zipDownloadUrl
        });
      } else {
        console.log('Failed to load code files');
      }
    } catch (err) {
      console.error('Error loading code files:', err);
      
      if (err instanceof CodeDownloadError) {
        switch (err.code) {
          case 'PROJECT_NOT_FOUND':
            setError('No code files found for this project. Generate a diagram first to create code files.');
            break;
          case 'ACCESS_DENIED':
            setError('You do not have permission to access these files.');
            break;
          case 'INVALID_PROJECT_ID':
            setError('Invalid project identifier.');
            break;
          default:
            setError(err.message);
        }
      } else {
        setError('Failed to load code files. Please try again.');
      }
      
      setFiles([]);
      setMetadata(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  /**
   * Download a single file
   */
  const downloadFile = useCallback(async (file) => {
    if (!projectId || !file) {
      setError('Invalid download parameters');
      return;
    }

    setError(null);
    setDownloadProgress({ percentage: 0, status: 'Starting download...' });

    try {
      // Use filename as fileId if no specific ID is provided
      const fileId = file.id || file.filename;
      
      const blob = await downloadIndividualFile(projectId, fileId, handleProgress);
      
      // Trigger download
      const filename = file.filename || `code-file-${Date.now()}.txt`;
      triggerBlobDownload(blob, filename);
      
      setDownloadProgress({ percentage: 100, status: 'Download complete' });
      
      // Clear progress after a delay
      setTimeout(() => setDownloadProgress(null), 2000);
      
    } catch (err) {
      console.error('Error downloading file:', err);
      
      if (err instanceof CodeDownloadError) {
        switch (err.code) {
          case 'FILE_NOT_FOUND':
            setError('File not found or has been removed.');
            break;
          case 'ACCESS_DENIED':
            setError('You do not have permission to download this file.');
            break;
          case 'DOWNLOAD_CANCELLED':
            setError('Download was cancelled.');
            break;
          default:
            setError(`Download failed: ${err.message}`);
        }
      } else {
        setError('Failed to download file. Please try again.');
      }
      
      setDownloadProgress(null);
    }
  }, [projectId, handleProgress]);

  /**
   * Download all files as ZIP
   */
  const downloadAllFiles = useCallback(async () => {
    if (!projectId) {
      setError('Project ID is required');
      return;
    }

    setError(null);
    setDownloadProgress({ percentage: 0, status: 'Preparing ZIP archive...' });

    try {
      const blob = await downloadProjectZip(projectId, handleProgress);
      
      // Generate filename
      const projectName = metadata?.projectName || 'generated-code';
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `${projectName}-${timestamp}.zip`;
      
      triggerBlobDownload(blob, filename);
      
      setDownloadProgress({ percentage: 100, status: 'ZIP download complete' });
      
      // Clear progress after a delay
      setTimeout(() => setDownloadProgress(null), 2000);
      
    } catch (err) {
      console.error('Error downloading ZIP:', err);
      
      if (err instanceof CodeDownloadError) {
        switch (err.code) {
          case 'PROJECT_NOT_FOUND':
            setError('Project not found or no files available for download.');
            break;
          case 'ACCESS_DENIED':
            setError('You do not have permission to download this project.');
            break;
          default:
            setError(`ZIP download failed: ${err.message}`);
        }
      } else {
        setError('Failed to download ZIP archive. Please try again.');
      }
      
      setDownloadProgress(null);
    }
  }, [projectId, metadata, handleProgress]);

  /**
   * Download selected files as ZIP
   */
  const downloadSelectedFiles = useCallback(async (selectedFiles) => {
    if (!projectId || !selectedFiles || selectedFiles.length === 0) {
      setError('No files selected for download');
      return;
    }

    setError(null);
    setDownloadProgress({ percentage: 0, status: 'Preparing selected files...' });

    try {
      // Extract file IDs
      const fileIds = selectedFiles.map(file => file.id || file.filename);
      
      const blob = await downloadSelectedFilesZip(projectId, fileIds, handleProgress);
      
      // Generate filename
      const projectName = metadata?.projectName || 'generated-code';
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `${projectName}-selected-${timestamp}.zip`;
      
      triggerBlobDownload(blob, filename);
      
      setDownloadProgress({ percentage: 100, status: 'Selected files download complete' });
      
      // Clear progress after a delay
      setTimeout(() => setDownloadProgress(null), 2000);
      
    } catch (err) {
      console.error('Error downloading selected files:', err);
      
      if (err instanceof CodeDownloadError) {
        switch (err.code) {
          case 'FILES_NOT_FOUND':
            setError('Some selected files were not found.');
            break;
          case 'ACCESS_DENIED':
            setError('You do not have permission to download the selected files.');
            break;
          default:
            setError(`Selected files download failed: ${err.message}`);
        }
      } else {
        setError('Failed to download selected files. Please try again.');
      }
      
      setDownloadProgress(null);
    }
  }, [projectId, metadata, handleProgress]);

  /**
   * Load download metadata
   */
  const loadMetadata = useCallback(async () => {
    if (!projectId) return;

    try {
      const meta = await getDownloadMetadata(projectId);
      setMetadata(meta);
    } catch (err) {
      console.warn('Failed to load download metadata:', err);
      // Don't set error for metadata failures as it's not critical
    }
  }, [projectId]);

  /**
   * Cancel ongoing download
   */
  const cancelDownload = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setDownloadProgress(null);
    setError('Download cancelled');
  }, []);

  /**
   * Reset all state
   */
  const reset = useCallback(() => {
    setFiles([]);
    setError(null);
    setDownloadProgress(null);
    setMetadata(null);
    setLoading(false);
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  return {
    // State
    files,
    loading,
    error,
    downloadProgress,
    metadata,
    
    // Actions
    loadFiles,
    downloadFile,
    downloadAllFiles,
    downloadSelectedFiles,
    loadMetadata,
    cancelDownload,
    clearError,
    reset,
    
    // Computed values
    hasFiles: files.length > 0,
    isDownloading: downloadProgress !== null,
    canDownload: !loading && !error && files.length > 0
  };
};

export default useCodeDownload;