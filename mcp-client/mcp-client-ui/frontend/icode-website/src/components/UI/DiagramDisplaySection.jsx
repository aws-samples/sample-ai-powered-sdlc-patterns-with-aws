import { useState, useEffect } from 'react';
import {
  Header,
  Box,
  SpaceBetween,
  Alert,
  Spinner,
  Badge,
  Button,
  Grid
} from '@cloudscape-design/components';
import PropTypes from 'prop-types';
import { fetchProjectDiagrams } from '../../services/diagramService';
import { fetchBinaryData } from '../../services/api';

// Custom hook to fetch authenticated diagram as blob URL
const useAuthenticatedDiagram = (diagramUrl, projectId) => {
  const [blobUrl, setBlobUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!diagramUrl) return;

    const fetchDiagram = async () => {
      setLoading(true);
      setError(null);

      try {
        // Convert diagram URL to API endpoint
        let apiEndpoint = diagramUrl;

        if (diagramUrl.startsWith('/diagrams/')) {
          // Convert old static URLs to S3 serving URLs
          const filename = diagramUrl.replace('/diagrams/', '');
          apiEndpoint = `/api/diagrams/${projectId}/serve/${filename}`;
        } else if (diagramUrl.startsWith('/api/diagrams/')) {
          // Already an API endpoint
          apiEndpoint = diagramUrl;
        }

        console.log('🎨 Fetching authenticated diagram:', apiEndpoint);

        // Fetch binary data with authentication
        const blob = await fetchBinaryData(apiEndpoint, {
          method: 'GET'
        });

        if (blob instanceof Blob) {
          // Create blob URL for display
          const url = URL.createObjectURL(blob);
          setBlobUrl(url);
        } else {
          throw new Error('Invalid response format');
        }
      } catch (err) {
        console.error('🎨 Failed to fetch authenticated diagram:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDiagram();

    // Cleanup blob URL on unmount
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [diagramUrl, projectId]);

  return { blobUrl, loading, error };
};

// Note: All diagrams are now served through authenticated S3 endpoints

// Component to display authenticated diagrams
const AuthenticatedDiagramImage = ({ diagramUrl, projectId, alt }) => {
  const { blobUrl, loading, error } = useAuthenticatedDiagram(diagramUrl, projectId);

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        style={{ height: '200px' }}
      >
        <Spinner size="large" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        style={{
          width: '100%',
          height: '200px',
          border: '2px dashed #ccc',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
          fontStyle: 'italic',
          backgroundColor: '#f9f9f9'
        }}
      >
        Failed to load diagram: {error}
      </Box>
    );
  }

  if (!blobUrl) {
    return (
      <Box
        style={{
          width: '100%',
          height: '200px',
          border: '2px dashed #ccc',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
          fontStyle: 'italic'
        }}
      >
        No diagram available
      </Box>
    );
  }

  return (
    <Box>
      <img
        src={blobUrl}
        alt={alt}
        style={{
          width: '100%',
          height: 'auto',
          maxHeight: '400px',
          objectFit: 'contain',
          backgroundColor: 'transparent'
        }}
        onLoad={() => {
          // Diagram loaded successfully
        }}
      />
    </Box>
  );
};

const DiagramDisplaySection = ({
  projectId,
  projectName,
  autoLoad = true,
  refreshTrigger = 0
}) => {
  const [diagrams, setDiagrams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [autoRefreshing, setAutoRefreshing] = useState(false);

  // Load diagrams when component mounts or projectId changes
  useEffect(() => {
    if (autoLoad && projectId) {
      loadDiagrams();
    }
  }, [projectId, autoLoad]);

  // Auto-refresh diagrams when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger > 0 && projectId && autoLoad) {
      console.log('🖼️ DiagramDisplaySection: Auto-refreshing due to trigger:', refreshTrigger);
      setAutoRefreshing(true);
      loadDiagrams().finally(() => {
        // Show auto-refresh indicator briefly
        setTimeout(() => setAutoRefreshing(false), 2000);
      });
    }
  }, [refreshTrigger, projectId, autoLoad]);

  const loadDiagrams = async () => {
    if (!projectId) {
      console.log('DiagramDisplaySection: No project ID provided');
      return;
    }

    console.log('🎨 DiagramDisplaySection: Loading diagrams for project:', projectId);
    setLoading(true);
    setError(null);

    try {
      const response = await fetchProjectDiagrams(projectId);

      console.log('🎨 DiagramDisplaySection: API response:', response);

      if (response.success) {
        // Process diagram URLs

        setDiagrams(response.diagrams || []);
        setLastUpdated(new Date());
        console.log('🎨 DiagramDisplaySection: ✅ Loaded', response.diagrams?.length || 0, 'diagrams');
      } else {
        setError(response.message || 'Failed to load diagrams');
        setDiagrams([]);
        console.log('🎨 DiagramDisplaySection: ❌ Failed to load diagrams:', response.message);
      }
    } catch (err) {
      console.error('🎨 DiagramDisplaySection: 💥 Error loading diagrams:', err);
      setError('Failed to load diagrams');
      setDiagrams([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    console.log('🎨 DiagramDisplaySection: Manual refresh triggered');
    loadDiagrams();
  };

  const handleDownloadAction = async (actionId, diagram) => {
    try {
      switch (actionId) {
        case 'download-png':
          await downloadDiagram(diagram, 'png');
          break;
        default:
          console.warn('Unknown download action:', actionId);
      }
    } catch (error) {
      console.error('Download action failed:', error);
      // You could add a toast notification here
    }
  };

  const downloadDiagram = async (diagram) => {
    try {
      const downloadUrl = diagram.diagram_url;

      if (!downloadUrl) {
        throw new Error('PNG format not available');
      }

      // Convert to API endpoint if needed
      let apiEndpoint = downloadUrl;
      if (downloadUrl.startsWith('/diagrams/')) {
        const filename = downloadUrl.replace('/diagrams/', '');
        apiEndpoint = `/api/diagrams/${projectId}/serve/${filename}`;
      }

      console.log('📥 Downloading diagram:', apiEndpoint);

      // Fetch the diagram data
      const blob = await fetchBinaryData(apiEndpoint, { method: 'GET' });
      
      if (!(blob instanceof Blob)) {
        throw new Error('Invalid response format');
      }

      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Generate filename
      const diagramType = diagram.diagram_type || 'diagram';
      const timestamp = new Date().toISOString().slice(0, 10);
      const filename = `${projectName || projectId}_${diagramType}_${timestamp}.png`;
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Cleanup
      URL.revokeObjectURL(url);
      
      console.log('✅ Diagram downloaded successfully:', filename);
    } catch (error) {
      console.error('❌ Failed to download diagram:', error);
      throw error;
    }
  };

  const downloadBase64Diagram = (diagram) => {
    try {
      if (!diagram.diagram_data) {
        throw new Error('No diagram data available');
      }

      // Convert base64 to blob
      const byteCharacters = atob(diagram.diagram_data);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'image/png' });

      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Generate filename
      const diagramType = diagram.diagram_type || 'diagram';
      const timestamp = new Date().toISOString().slice(0, 10);
      const filename = `${projectName || projectId}_${diagramType}_${timestamp}.png`;
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Cleanup
      URL.revokeObjectURL(url);
      
      console.log('✅ Base64 diagram downloaded successfully:', filename);
    } catch (error) {
      console.error('❌ Failed to download base64 diagram:', error);
      throw error;
    }
  };



  const handleDownloadBase64 = (diagram) => {
    try {
      downloadBase64Diagram(diagram);
    } catch (error) {
      console.error('Download failed:', error);
      // You could add a toast notification here
    }
  };

  const handleDownloadAll = async () => {
    try {
      console.log('📥 Downloading all diagrams...');
      
      for (let i = 0; i < diagrams.length; i++) {
        const diagram = diagrams[i];
        
        if (diagram.diagram_url) {
          await downloadDiagram(diagram);
        } else if (diagram.diagram_data) {
          downloadBase64Diagram(diagram);
        }
        
        // Add small delay between downloads to avoid overwhelming the browser
        if (i < diagrams.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      console.log('✅ All diagrams downloaded successfully');
    } catch (error) {
      console.error('❌ Failed to download all diagrams:', error);
      // You could add a toast notification here
    }
  };

  // Don't render anything if no diagrams and not loading
  if (!loading && diagrams.length === 0 && !error) {
    return null;
  }

  return (
    <div style={{ padding: '0', margin: '0' }}>
      <SpaceBetween size="l">
        <Header
          variant="h3"
          description={`Architecture diagrams for ${projectName || projectId}`}
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              {autoRefreshing && (
                <Badge color="blue">
                  🔄 Auto-refreshing...
                </Badge>
              )}
              {diagrams.length > 0 && (
                <Button
                  variant="normal"
                  iconName="download"
                  onClick={handleDownloadAll}
                  disabled={loading}
                >
                  Download All
                </Button>
              )}
              <Button
                variant="normal"
                iconName="refresh"
                onClick={handleRefresh}
                loading={loading}
              >
                Refresh
              </Button>
            </SpaceBetween>
          }
        >
          Project Diagrams
        </Header>
        {/* Loading State */}
        {loading && (
          <Box textAlign="center" padding="l">
            <Spinner size="large" />
            <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>
              Loading diagrams...
            </Box>
          </Box>
        )}

        {/* Error State */}
        {error && (
          <Alert
            type="error"
            dismissible
            onDismiss={() => setError(null)}
            header="Failed to load diagrams"
            action={
              <Button onClick={handleRefresh} variant="primary">
                Retry
              </Button>
            }
          >
            {error}
          </Alert>
        )}

        {/* Success State with Diagrams */}
        {!loading && diagrams.length > 0 && (
          <SpaceBetween size="l">
            {/* Summary */}
            <Box>
              <SpaceBetween direction="horizontal" size="s" alignItems="center">
                <Badge color="blue">{diagrams.length} diagram{diagrams.length !== 1 ? 's' : ''}</Badge>
                {lastUpdated && (
                  <Box variant="small" color="text-body-secondary">
                    Last updated: {lastUpdated.toLocaleTimeString()}
                  </Box>
                )}
              </SpaceBetween>
            </Box>

            {/* Diagram Grid */}
            <Grid gridDefinition={diagrams.length === 1 ? [{ colspan: 12 }] : [{ colspan: 6 }, { colspan: 6 }]}>
              {diagrams.map((diagram, index) => (
                <Box key={index}>
                  <SpaceBetween size="s">
                    {/* Diagram Header */}
                    <Box>
                      <SpaceBetween direction="horizontal" size="s" alignItems="center">
                        <Box variant="h4">
                          {diagram.diagram_metadata?.title ||
                            `${diagram.diagram_type.charAt(0).toUpperCase() + diagram.diagram_type.slice(1)} Diagram`}
                        </Box>
                        <Badge color="grey">
                          {diagram.diagram_metadata?.format?.toUpperCase() || 'PNG'}
                        </Badge>
                        {diagram.diagram_metadata?.source && (
                          <Badge color={diagram.diagram_metadata.source === 'local' ? 'green' : 'blue'}>
                            {diagram.diagram_metadata.source}
                          </Badge>
                        )}
                      </SpaceBetween>

                      {diagram.diagram_metadata?.description && (
                        <Box variant="small" color="text-body-secondary" margin={{ top: 'xs' }}>
                          {diagram.diagram_metadata.description}
                        </Box>
                      )}
                    </Box>

                    {/* Authenticated Diagram Image */}
                    {diagram.diagram_url && (
                      <Box>
                        <SpaceBetween size="s">
                          <AuthenticatedDiagramImage
                            diagramUrl={diagram.diagram_url}
                            projectId={projectId}
                            alt={`${diagram.diagram_type} diagram`}
                          />
                          <Box textAlign="right">
                            <Button
                              variant="icon"
                              iconName="download"
                              ariaLabel="Download PNG"
                              onClick={() => handleDownloadAction('download-png', diagram)}
                            />
                          </Box>
                        </SpaceBetween>
                      </Box>
                    )}

                    {/* Base64 Image Fallback */}
                    {diagram.diagram_data && !diagram.diagram_url && (
                      <Box>
                        <SpaceBetween size="s">
                          <img
                            src={`data:image/png;base64,${diagram.diagram_data}`}
                            alt={`${diagram.diagram_type} diagram`}
                            style={{
                              width: '100%',
                              height: 'auto',
                              maxHeight: '400px',
                              objectFit: 'contain',
                              backgroundColor: 'transparent'
                            }}
                            onError={(e) => {
                              console.error('🎨 DiagramDisplaySection: Failed to load base64 diagram');
                              e.target.style.display = 'none';
                            }}
                          />
                          <Box textAlign="right">
                            <Button
                              variant="icon"
                              iconName="download"
                              ariaLabel="Download diagram"
                              onClick={() => handleDownloadBase64(diagram)}
                            />
                          </Box>
                        </SpaceBetween>
                      </Box>
                    )}
                  </SpaceBetween>
                </Box>
              ))}
            </Grid>
          </SpaceBetween>
        )}

        {/* Empty State */}
        {!loading && diagrams.length === 0 && !error && (
          <Box textAlign="center" padding="xl">
            <SpaceBetween size="m">
              <Box variant="h4" color="text-body-secondary">
                No diagrams found
              </Box>
              <Box variant="p" color="text-body-secondary">
                Generate diagrams by chatting about your architecture in the design phase.
              </Box>
              <Button onClick={handleRefresh} variant="primary">
                Check for diagrams
              </Button>
            </SpaceBetween>
          </Box>
        )}
      </SpaceBetween>
    </div>
  );
};

DiagramDisplaySection.propTypes = {
  projectId: PropTypes.string.isRequired,
  projectName: PropTypes.string,
  autoLoad: PropTypes.bool,
  refreshTrigger: PropTypes.number
};

export default DiagramDisplaySection;