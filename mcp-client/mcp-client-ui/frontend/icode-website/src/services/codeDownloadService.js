// Code Download Service
// This service handles code file downloads and ZIP archive generation

import { makeApiCall, fetchBinaryData, ApiError } from './api';
import { getApiConfig } from '../config/apiConfig';

/**
 * Custom error class for code download errors
 */
export class CodeDownloadError extends Error {
  constructor(message, code, details = null) {
    super(message);
    this.name = 'CodeDownloadError';
    this.code = code;
    this.details = details;
  }
}

/**
 * Progress callback type for download operations
 * @callback ProgressCallback
 * @param {Object} progress - Progress information
 * @param {number} progress.loaded - Bytes loaded
 * @param {number} progress.total - Total bytes
 * @param {number} progress.percentage - Percentage complete (0-100)
 * @param {string} progress.status - Current status message
 */

/**
 * Fetch available code files for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Object>} - Object containing files array and metadata
 */
export const fetchAvailableCodeFiles = async (projectId) => {
  try {
    if (!projectId) {
      throw new CodeDownloadError('Project ID is required', 'INVALID_PROJECT_ID');
    }

    const response = await makeApiCall(`/api/code-download/${projectId}/files`, {
      method: 'GET'
    });

    // Validate response structure
    if (!response || typeof response !== 'object') {
      throw new CodeDownloadError('Invalid response format', 'INVALID_RESPONSE');
    }

    return {
      success: response.success || false,
      files: response.files || [],
      projectName: response.projectName || 'Unknown Project',
      generatedAt: response.generatedAt || new Date().toISOString(),
      zipDownloadUrl: response.zipDownloadUrl || null,
      totalFiles: response.files ? response.files.length : 0,
      totalSize: response.files ? response.files.reduce((sum, file) => sum + (file.fileSize || 0), 0) : 0
    };

  } catch (error) {
    if (error instanceof CodeDownloadError) {
      throw error;
    }

    if (error instanceof ApiError) {
      if (error.status === 404) {
        throw new CodeDownloadError('Project not found or no code files available', 'PROJECT_NOT_FOUND');
      }
      if (error.status === 403) {
        throw new CodeDownloadError('Access denied to project files', 'ACCESS_DENIED');
      }
      throw new CodeDownloadError(`API Error: ${error.message}`, 'API_ERROR', { status: error.status });
    }

    throw new CodeDownloadError(`Failed to fetch code files: ${error.message}`, 'FETCH_ERROR');
  }
};

/**
 * Download an individual code file
 * @param {string} projectId - The project identifier
 * @param {string} fileId - The file identifier
 * @param {ProgressCallback} onProgress - Progress callback function
 * @returns {Promise<Blob>} - The downloaded file as a Blob
 */
export const downloadIndividualFile = async (projectId, fileId, onProgress = null) => {
  try {
    if (!projectId || !fileId) {
      throw new CodeDownloadError('Project ID and File ID are required', 'INVALID_PARAMETERS');
    }

    // Create abort controller for cancellation support
    const controller = new AbortController();
    
    // Update progress
    if (onProgress) {
      onProgress({
        loaded: 0,
        total: 0,
        percentage: 0,
        status: 'Starting download...'
      });
    }

    const blob = await fetchBinaryData(`/api/code-download/${projectId}/file/${fileId}`, {
      method: 'GET',
      signal: controller.signal
    });

    // Update progress to completion
    if (onProgress) {
      onProgress({
        loaded: blob.size,
        total: blob.size,
        percentage: 100,
        status: 'Download complete'
      });
    }

    return blob;

  } catch (error) {
    if (error instanceof CodeDownloadError) {
      throw error;
    }

    if (error.name === 'AbortError') {
      throw new CodeDownloadError('Download cancelled', 'DOWNLOAD_CANCELLED');
    }

    throw new CodeDownloadError(`Failed to download file: ${error.message}`, 'DOWNLOAD_ERROR');
  }
};

/**
 * Download project as ZIP archive
 * @param {string} projectId - The project identifier
 * @param {ProgressCallback} onProgress - Progress callback function
 * @returns {Promise<Blob>} - The downloaded ZIP file as a Blob
 */
export const downloadProjectZip = async (projectId, onProgress = null) => {
  try {
    if (!projectId) {
      throw new CodeDownloadError('Project ID is required', 'INVALID_PROJECT_ID');
    }

    // Update progress
    if (onProgress) {
      onProgress({
        loaded: 0,
        total: 0,
        percentage: 0,
        status: 'Preparing ZIP archive...'
      });
    }

    // Use authenticated API call with binary response
    const blob = await fetchBinaryData(`/api/code-download/${projectId}/zip`, {
      method: 'GET'
    });

    // Update progress to completion
    if (onProgress) {
      onProgress({
        loaded: blob.size,
        total: blob.size,
        percentage: 100,
        status: 'ZIP download complete'
      });
    }

    return blob;

  } catch (error) {
    if (error instanceof CodeDownloadError) {
      throw error;
    }

    throw new CodeDownloadError(`Failed to download ZIP: ${error.message}`, 'ZIP_DOWNLOAD_ERROR');
  }
};

/**
 * Download selected files as ZIP archive
 * @param {string} projectId - The project identifier
 * @param {Array<string>} fileIds - Array of file identifiers to include
 * @param {ProgressCallback} onProgress - Progress callback function
 * @returns {Promise<Blob>} - The downloaded ZIP file as a Blob
 */
export const downloadSelectedFilesZip = async (projectId, fileIds, onProgress = null) => {
  try {
    if (!projectId || !fileIds || !Array.isArray(fileIds) || fileIds.length === 0) {
      throw new CodeDownloadError('Project ID and file IDs are required', 'INVALID_PARAMETERS');
    }

    // Update progress
    if (onProgress) {
      onProgress({
        loaded: 0,
        total: 0,
        percentage: 0,
        status: 'Preparing selected files...'
      });
    }

    // For POST requests with binary response, we need to use fetch with auth headers manually
    const config = getApiConfig();
    const url = `${config.baseUrl}/api/code-download/${projectId}/zip-selected`;
    
    // Get auth headers
    const authService = (await import('./authService')).default;
    const authHeader = await authService.getAuthHeader();
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/zip',
        ...(authHeader ? { 'Authorization': authHeader } : {})
      },
      body: JSON.stringify({ fileIds })
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new CodeDownloadError('Some selected files not found', 'FILES_NOT_FOUND');
      }
      if (response.status === 403) {
        throw new CodeDownloadError('Access denied to selected files', 'ACCESS_DENIED');
      }
      throw new CodeDownloadError(`Selected files download failed: ${response.statusText}`, 'DOWNLOAD_ERROR', { status: response.status });
    }

    // Get content length for progress tracking
    const contentLength = response.headers.get('content-length');
    const total = contentLength ? parseInt(contentLength, 10) : 0;

    if (onProgress) {
      onProgress({
        loaded: 0,
        total,
        percentage: 0,
        status: 'Downloading selected files...'
      });
    }

    // Read response with progress tracking
    const reader = response.body.getReader();
    const chunks = [];
    let loaded = 0;

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      chunks.push(value);
      loaded += value.length;
      
      if (onProgress) {
        const percentage = total > 0 ? Math.round((loaded / total) * 100) : 0;
        onProgress({
          loaded,
          total,
          percentage,
          status: `Downloaded ${formatBytes(loaded)}${total > 0 ? ` of ${formatBytes(total)}` : ''}`
        });
      }
    }

    // Combine chunks into blob
    const blob = new Blob(chunks, { type: 'application/zip' });
    
    if (onProgress) {
      onProgress({
        loaded,
        total: loaded,
        percentage: 100,
        status: 'Selected files download complete'
      });
    }

    return blob;

  } catch (error) {
    if (error instanceof CodeDownloadError) {
      throw error;
    }

    throw new CodeDownloadError(`Failed to download selected files: ${error.message}`, 'SELECTED_DOWNLOAD_ERROR');
  }
};

/**
 * Trigger download of a blob with a filename
 * @param {Blob} blob - The blob to download
 * @param {string} filename - The filename for the download
 */
export const triggerBlobDownload = (blob, filename) => {
  try {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    throw new CodeDownloadError(`Failed to trigger download: ${error.message}`, 'DOWNLOAD_TRIGGER_ERROR');
  }
};

/**
 * Get download metadata for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Object>} - Download metadata including file count and total size
 */
export const getDownloadMetadata = async (projectId) => {
  try {
    const response = await makeApiCall(`/api/code-download/${projectId}/metadata`, {
      method: 'GET'
    });

    return {
      projectId,
      projectName: response.projectName || 'Unknown Project',
      totalFiles: response.totalFiles || 0,
      totalSize: response.totalSize || 0,
      generatedAt: response.generatedAt || new Date().toISOString(),
      lastModified: response.lastModified || new Date().toISOString(),
      availableFormats: response.availableFormats || ['individual', 'zip']
    };

  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      throw new CodeDownloadError('Project metadata not found', 'METADATA_NOT_FOUND');
    }
    throw new CodeDownloadError(`Failed to get download metadata: ${error.message}`, 'METADATA_ERROR');
  }
};

/**
 * Format bytes to human readable string
 * @param {number} bytes - Number of bytes
 * @returns {string} - Formatted string (e.g., "1.5 MB")
 */
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Validate file ID format
 * @param {string} fileId - The file identifier
 * @returns {boolean} - True if valid
 */
export const isValidFileId = (fileId) => {
  return typeof fileId === 'string' && fileId.length > 0 && /^[a-zA-Z0-9._-]+$/.test(fileId);
};

/**
 * Validate project ID format
 * @param {string} projectId - The project identifier
 * @returns {boolean} - True if valid
 */
export const isValidProjectId = (projectId) => {
  return typeof projectId === 'string' && projectId.length > 0 && /^[a-zA-Z0-9._-]+$/.test(projectId);
};

// Export all functions
export default {
  fetchAvailableCodeFiles,
  downloadIndividualFile,
  downloadProjectZip,
  downloadSelectedFilesZip,
  triggerBlobDownload,
  getDownloadMetadata,
  isValidFileId,
  isValidProjectId,
  CodeDownloadError
};