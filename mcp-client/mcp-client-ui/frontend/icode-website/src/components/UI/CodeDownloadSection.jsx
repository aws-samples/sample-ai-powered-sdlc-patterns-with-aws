import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  SpaceBetween
} from '@cloudscape-design/components';
import useCodeDownload from '../../hooks/useCodeDownload';
import DownloadProgress from './DownloadProgress';
import SimpleSwaggerViewer from './SimpleSwaggerViewer';
import { getApiConfig } from '../../config/apiConfig';
import './CodeDownloadSection.css';

// File type icons mapping
const FILE_TYPE_ICONS = {
  'yaml': 'file',
  'yml': 'file',
  'json': 'file',
  'py': 'file',
  'js': 'file',
  'jsx': 'file',
  'ts': 'file',
  'tsx': 'file',
  'html': 'file',
  'css': 'file',
  'md': 'file',
  'txt': 'file',
  'sh': 'file',
  'dockerfile': 'file',
  'tf': 'file',
  'default': 'file'
};

// File type colors for badges
const FILE_TYPE_COLORS = {
  'infrastructure': 'blue',
  'application': 'green',
  'config': 'orange',
  'documentation': 'grey',
  'default': 'grey'
};

// Language syntax highlighting classes
const LANGUAGE_CLASSES = {
  'yaml': 'language-yaml',
  'yml': 'language-yaml',
  'json': 'language-json',
  'python': 'language-python',
  'javascript': 'language-javascript',
  'typescript': 'language-typescript',
  'html': 'language-html',
  'css': 'language-css',
  'markdown': 'language-markdown',
  'bash': 'language-bash',
  'shell': 'language-bash',
  'terraform': 'language-hcl',
  'dockerfile': 'language-dockerfile'
};

const CodeDownloadSection = ({
  projectId,
  generatedFiles = [],
  projectName = 'Generated Code',
  loading: externalLoading = false,
  error: externalError = null,
  onDownloadFile = null,
  onDownloadSelected = null,
  onDownloadAll = null,
  className = '',
  autoLoad = true,
  refreshTrigger = 0
}) => {
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [previewFile, setPreviewFile] = useState(null);
  const [isPreviewModalVisible, setIsPreviewModalVisible] = useState(false);
  const [autoRefreshing, setAutoRefreshing] = useState(false);
  const [swaggerSpec, setSwaggerSpec] = useState(null);
  const [showSwagger, setShowSwagger] = useState(false);

  // Use the code download hook
  const {
    files: hookFiles,
    loading: hookLoading,
    error: hookError,
    downloadProgress,
    metadata,
    loadFiles,
    downloadFile,
    downloadAllFiles,
    downloadSelectedFiles,
    clearError,
    cancelDownload,
    hasFiles,
    isDownloading
  } = useCodeDownload(projectId);

  // Determine which data source to use
  const files = generatedFiles.length > 0 ? generatedFiles : hookFiles;
  const loading = externalLoading || hookLoading;
  const error = externalError || hookError;
  const displayProjectName = projectName !== 'Generated Code' ? projectName : (metadata?.projectName || projectName);

  // Load files on mount if projectId is provided and autoLoad is true
  useEffect(() => {
    console.log('CodeDownloadSection useEffect triggered:', {
      projectId,
      autoLoad,
      externalLoading,
      generatedFilesLength: generatedFiles.length,
      refreshTrigger,
      shouldLoad: projectId && autoLoad && !externalLoading && generatedFiles.length === 0
    });

    if (projectId && autoLoad && !externalLoading && generatedFiles.length === 0) {
      console.log('CodeDownloadSection: Loading files for project:', projectId);
      loadFiles();
    }
  }, [projectId, autoLoad, externalLoading, generatedFiles.length, loadFiles]);

  // Refresh files when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger > 0 && projectId && autoLoad) {
      console.log('CodeDownloadSection: Auto-refreshing files due to trigger:', refreshTrigger);
      setAutoRefreshing(true);
      loadFiles().finally(() => {
        // Show auto-refresh indicator briefly
        setTimeout(() => setAutoRefreshing(false), 2000);
      });
    }
  }, [refreshTrigger, projectId, autoLoad, loadFiles]);

  // Reset selected files when files change
  useEffect(() => {
    setSelectedFiles(new Set());
  }, [files]);

  // Handle file selection
  const handleFileSelection = (filename, checked) => {
    const newSelected = new Set(selectedFiles);
    if (checked) {
      newSelected.add(filename);
    } else {
      newSelected.delete(filename);
    }
    setSelectedFiles(newSelected);
  };

  // Handle select all/none
  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedFiles(new Set(generatedFiles.map(file => file.filename)));
    } else {
      setSelectedFiles(new Set());
    }
  };

  // Handle file preview
  const handlePreviewFile = (file) => {
    setPreviewFile(file);
    setIsPreviewModalVisible(true);
  };

  // Get file extension
  const getFileExtension = (filename) => {
    return filename.split('.').pop().toLowerCase();
  };

  // Get file type icon
  const getFileTypeIcon = (filename) => {
    const ext = getFileExtension(filename);
    return FILE_TYPE_ICONS[ext] || FILE_TYPE_ICONS.default;
  };

  // Get file type color
  const getFileTypeColor = (fileType) => {
    return FILE_TYPE_COLORS[fileType] || FILE_TYPE_COLORS.default;
  };

  // Get language class for syntax highlighting
  const getLanguageClass = (language) => {
    return LANGUAGE_CLASSES[language?.toLowerCase()] || '';
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Handle download actions
  const handleDownloadFile = async (file) => {
    if (onDownloadFile) {
      onDownloadFile(file);
    } else if (projectId) {
      await downloadFile(file);
    }
  };

  const handleDownloadSelected = async () => {
    const selectedFileObjects = files.filter(file =>
      selectedFiles.has(file.filename)
    );

    if (onDownloadSelected) {
      onDownloadSelected(selectedFileObjects);
    } else if (projectId) {
      await downloadSelectedFiles(selectedFileObjects);
    }
  };

  const handleDownloadAll = async () => {
    if (onDownloadAll) {
      onDownloadAll(files);
    } else if (projectId) {
      await downloadAllFiles();
    }
  };

  // Handle error dismissal
  const handleDismissError = () => {
    clearError();
  };

  // Check if a file is a JSON API specification
  const isJsonApiSpec = (file) => {
    console.log('Checking if file is API spec:', file.filename, 'has content:', !!file.content);

    if (!file.filename) return false;

    const isJsonFile = file.filename.toLowerCase().endsWith('.json');
    if (!isJsonFile) return false;

    // For now, show Swagger button for all JSON files
    // We'll validate the content when the user clicks the button
    console.log('JSON file detected:', file.filename);
    return true;

    // TODO: Uncomment this when we have proper content loading
    /*
    if (!file.content) return false;
    
    try {
      const content = typeof file.content === 'string' ? JSON.parse(file.content) : file.content;
      
      // Check for OpenAPI indicators
      if (content.openapi || content.swagger) return true;
      
      // Check for common API spec structure
      if (content.info && content.paths) return true;
      
      return false;
    } catch (error) {
      return false;
    }
    */
  };

  // Handle viewing file in Swagger
  const handleViewInSwagger = async (file) => {

    try {
      // Import authService to get proper auth header
      const authService = await import('../../services/authService');
      
      // Get proper auth header like the working download does
      const authHeader = await authService.default.getAuthHeader();
      
      // Check if user is authenticated
      if (!authHeader) {
        alert('Please log in to view API specifications.');
        return;
      }
      
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };
      
      headers.Authorization = authHeader;

      // Try multiple project ID formats to handle different naming conventions
      let response;
      let lastError;
      
      // List of project ID variations to try
      const projectIdVariations = [
        projectId, // Original project ID
        projectId.toLowerCase().replace(/\s+/g, '-'), // Convert spaces to hyphens
        projectId.replace(/\s+/g, '-'), // Convert spaces to hyphens (preserve case)
        projectId.toLowerCase().replace(/[^a-z0-9]/g, '-'), // More aggressive normalization
      ];
      
      // Remove duplicates
      const uniqueProjectIds = [...new Set(projectIdVariations)];
      console.log('Trying project ID variations:', uniqueProjectIds);
      
      for (const tryProjectId of uniqueProjectIds) {
        try {
          const apiConfig = getApiConfig();
          const apiUrl = `${apiConfig.baseUrl}/api/code-download/${tryProjectId}/file/${encodeURIComponent(file.filename)}`;
          
          response = await fetch(apiUrl, {
            method: 'GET',
            headers: headers
          });
          
          if (response.ok) {
            break;
          } else {
            lastError = new Error(`Failed to load file: ${response.status} ${response.statusText}`);
          }
        } catch (error) {
          lastError = error;
        }
      }

      if (!response || !response.ok) {
        // Handle specific error cases
        if (response && response.status === 401) {
          alert('Authentication required. Please log in and try again.');
          return;
        } else if (response && response.status === 403) {
          alert('Access denied. You do not have permission to view this file.');
          return;
        } else if (response && response.status === 404) {
          alert('File not found. The API specification may have been moved or deleted.');
          return;
        }
        throw lastError || new Error('Failed to load file from all project ID variations');
      }

      // Get the file content as text (the endpoint returns the file content directly)
      const fileContent = await response.text();
      console.log('File content type:', response.headers.get('content-type'));
      console.log('File content preview:', fileContent.substring(0, 200));
      
      let specData;
      try {
        specData = JSON.parse(fileContent);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Response content:', fileContent.substring(0, 500));
        
        // Check if it's an HTML error page
        if (fileContent.trim().startsWith('<!DOCTYPE') || fileContent.trim().startsWith('<html')) {
          throw new Error('Server returned an HTML error page instead of the JSON file. Please check if you have access to this project.');
        } else {
          throw new Error(`The file "${file.filename}" is not valid JSON. Parse error: ${parseError.message}`);
        }
      }

      // Validate it's an OpenAPI spec
      const isValidApiSpec = specData.openapi || specData.swagger || 
                            (specData.info && specData.paths);
      
      if (!isValidApiSpec) {
        alert('This JSON file does not appear to be a valid OpenAPI/Swagger specification.');
        return;
      }

      console.log('Successfully loaded OpenAPI spec with proper auth');
      setSwaggerSpec({
        content: specData,
        title: specData.info?.title || file.filename,
        version: specData.info?.version || '1.0.0'
      });
      setShowSwagger(true);

    } catch (error) {
      console.error('Error loading OpenAPI spec:', error);
      alert(`Error loading API specification: ${error.message}`);
    }
  };

  // Handle closing Swagger viewer
  const handleCloseSwagger = () => {
    setShowSwagger(false);
    setSwaggerSpec(null);
  };

  // Debug logging
  console.log('CodeDownloadSection Debug:', {
    projectId,
    loading,
    filesLength: files.length,
    error,
    hasFiles: files.length > 0,
    shouldRender: loading || files.length > 0,
    files: files.map(f => ({ filename: f.filename, hasContent: !!f.content, downloadUrl: f.downloadUrl }))
  });

  // Don't render if no files and not loading
  if (!loading && (!files || files.length === 0)) {
    console.log('CodeDownloadSection: Not rendering - no files and not loading');
  }

  const allSelected = files.length > 0 && selectedFiles.size === files.length;
  const someSelected = selectedFiles.size > 0 && selectedFiles.size < files.length;

  return (
    <div className={`code-download-section ${className}`}>
      <div className="container">
        {/* Header */}
        <div className="header">
          <h3>Generated Code Files</h3>
          <p>Download the generated architecture code files for {displayProjectName}</p>
          <div className="actions">
            {autoRefreshing && (
              <span className="badge badge-blue" style={{ marginRight: '8px' }}>
                🔄 Auto-refreshing...
              </span>
            )}
            <div style={{ 
              display: 'flex', 
              alignItems: 'baseline', 
              gap: '8px',
              height: '32px'
            }}>
              <Button
                variant="normal"
                onClick={handleDownloadSelected}
                disabled={selectedFiles.size === 0 || loading || isDownloading}
                iconName="download"
              >
                Download Selected ({selectedFiles.size})
              </Button>
              <Button
                variant="primary"
                onClick={handleDownloadAll}
                disabled={files.length === 0 || loading || isDownloading}
                iconName="download"
              >
                Download All
              </Button>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="alert alert-error">
            <div className="alert-content">
              <h4>Code Download Error</h4>
              <p>{error}</p>
            </div>
            <button
              className="alert-dismiss"
              onClick={handleDismissError}
              type="button"
            >
              ×
            </button>
          </div>
        )}

        {/* Download Progress */}
        {downloadProgress && (
          <DownloadProgress
            progress={downloadProgress}
            onCancel={cancelDownload}
            showCancel={true}
          />
        )}

        {/* Loading State */}
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Generating code files...</p>
          </div>
        )}

        {/* Files List */}
        {!loading && files.length > 0 && (
          <div className="files-section">
            {/* Select All Checkbox */}
            <div className="select-all">
              <label>
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={input => {
                    if (input) input.indeterminate = someSelected;
                  }}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  disabled={isDownloading}
                />
                Select all files ({files.length})
              </label>
            </div>

            {/* Swagger Viewer Section */}
            {showSwagger && swaggerSpec && (
              <SimpleSwaggerViewer
                spec={swaggerSpec.content}
                title={swaggerSpec.title}
                version={swaggerSpec.version}
                onClose={handleCloseSwagger}
              />
            )}

            {/* Files Grid */}
            <div className="files-grid">
              {files.map((file, index) => (
                <div key={file.filename || index} className="code-file-item">
                  <div className="file-row">
                    {/* Selection Checkbox */}
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.filename)}
                      onChange={(e) => handleFileSelection(file.filename, e.target.checked)}
                      disabled={isDownloading}
                    />

                    {/* File Icon */}
                    <span className="file-icon">📄</span>

                    {/* File Info */}
                    <div className="file-info">
                      <div className="file-name-row">
                        <strong>{file.filename}</strong>
                        {file.fileType && (
                          <span className={`badge badge-${getFileTypeColor(file.fileType)}`}>
                            {file.fileType}
                          </span>
                        )}
                        {file.language && (
                          <span className="badge badge-grey">
                            {file.language}
                          </span>
                        )}
                      </div>

                      <div className="file-details">
                        {file.description && (
                          <span className="description">{file.description}</span>
                        )}
                        {file.fileSize > 0 && (
                          <span className="file-size">{formatFileSize(file.fileSize)}</span>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="action-buttons">
                      <SpaceBetween direction="horizontal" size="xs">
                        <Button
                          variant="normal"
                          size="small"
                          onClick={() => handlePreviewFile(file)}
                          disabled={isDownloading}
                          iconName="view"
                        >
                          Preview
                        </Button>
                        {isJsonApiSpec(file) && (
                          <Button
                            variant="normal"
                            size="small"
                            onClick={() => handleViewInSwagger(file)}
                            disabled={isDownloading}
                            iconName="settings"
                            title="View API specification in Swagger UI"
                          >
                            Swagger
                          </Button>
                        )}
                        <Button
                          variant="primary"
                          size="small"
                          onClick={() => handleDownloadFile(file)}
                          disabled={isDownloading}
                          iconName="download"
                          loading={isDownloading}
                        >
                          {isDownloading ? 'Downloading...' : 'Download'}
                        </Button>
                      </SpaceBetween>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* File Preview Modal */}
      {isPreviewModalVisible && previewFile && (
        <div className="modal-overlay" onClick={() => setIsPreviewModalVisible(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{previewFile.filename}</h3>
              <button
                className="modal-close"
                onClick={() => setIsPreviewModalVisible(false)}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              {/* File Metadata */}
              <div className="file-metadata">
                <div className="metadata-item">
                  <strong>File Type:</strong> {previewFile.fileType || 'Unknown'}
                </div>
                <div className="metadata-item">
                  <strong>Language:</strong> {previewFile.language || 'Unknown'}
                </div>
                <div className="metadata-item">
                  <strong>Size:</strong> {previewFile.fileSize ? `${previewFile.fileSize} bytes` : 'Unknown'}
                </div>
              </div>

              {/* File Description */}
              {previewFile.description && (
                <div className="file-description">
                  <strong>Description:</strong>
                  <p>{previewFile.description}</p>
                </div>
              )}

              {/* Dependencies */}
              {previewFile.dependencies && previewFile.dependencies.length > 0 && (
                <div className="dependencies">
                  <strong>Dependencies:</strong>
                  <div className="dependencies-list">
                    {previewFile.dependencies.map((dep, index) => (
                      <span key={index} className="badge badge-blue">{dep}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Code Content */}
              <div className="code-section">
                <h4>File Content</h4>
                <div className="code-preview">
                  <pre className={`code-content ${getLanguageClass(previewFile.language)}`}>
                    <code>{previewFile.content}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}


    </div>
  );
};



// PropTypes
CodeDownloadSection.propTypes = {
  projectId: PropTypes.string,
  generatedFiles: PropTypes.arrayOf(
    PropTypes.shape({
      filename: PropTypes.string.isRequired,
      content: PropTypes.string.isRequired,
      fileType: PropTypes.string,
      language: PropTypes.string,
      description: PropTypes.string,
      dependencies: PropTypes.arrayOf(PropTypes.string),
      downloadUrl: PropTypes.string,
      fileSize: PropTypes.number
    })
  ),
  projectName: PropTypes.string,
  loading: PropTypes.bool,
  error: PropTypes.string,
  onDownloadFile: PropTypes.func,
  onDownloadSelected: PropTypes.func,
  onDownloadAll: PropTypes.func,
  className: PropTypes.string,
  autoLoad: PropTypes.bool,
  refreshTrigger: PropTypes.number
};

export default CodeDownloadSection;