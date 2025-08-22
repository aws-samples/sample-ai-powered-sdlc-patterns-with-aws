/**
 * Epics Panel Component
 * 
 * Displays epics and their features in a beautiful CloudScape panel for the requirements phase
 */

import { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Badge,
  Alert,
  Spinner,
  TextContent,
  Button,
  Icon,
  ExpandableSection,
  Cards,
  Pagination,
  StatusIndicator,
  ProgressBar
} from '@cloudscape-design/components';
import { getEpics, getJiraMetadata } from '../../services/jiraService';


const EpicsPanel = ({ projectId, refreshTrigger = 0, currentPhase = 'requirements', onSendChatMessage }) => {
  const [epics, setEpics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState({ total_epics: 0 });
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [pageSize, setPageSize] = useState(4);

  // Fetch epics data
  const fetchEpics = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      const [epicsData, metadataData] = await Promise.all([
        getEpics(projectId),
        getJiraMetadata(projectId)
      ]);

      setEpics(epicsData);
      setMetadata(metadataData);
    } catch (err) {
      console.error('Error fetching epics:', err);
      setError('Failed to load epics');
    } finally {
      setLoading(false);
    }
  };

  // Fetch data on component mount and when refresh trigger changes
  useEffect(() => {
    fetchEpics();
  }, [projectId, refreshTrigger]);

  // Show generating state when refresh trigger changes (indicates new epics being generated)
  useEffect(() => {
    if (refreshTrigger > 0) {
      setIsGenerating(true);
      // Clear generating state after a delay
      const timer = setTimeout(() => {
        setIsGenerating(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [refreshTrigger]);

  // Handler for generating design diagram
  const handleGenerateDesignDiagram = (epic) => {
    const epicName = epic.title || 'Epic';
    const message = `generate design diagram for the ${epicName}`;
    
    console.log('Sending to design phase chatbot:', message);
    
    // Send message to chat if callback is provided
    if (onSendChatMessage) {
      onSendChatMessage(message);
    } else {
      // Fallback: dispatch event for parent components to handle
      window.dispatchEvent(new CustomEvent('sendToChatbot', {
        detail: { message, phase: currentPhase, epic: epicName }
      }));
    }
  };

  // Handler for generating OpenAPI spec
  const handleGenerateOpenAPISpec = (epic) => {
    const epicName = epic.title || 'Epic';
    const message = `generate open api spec code file for ${epicName}`;
    
    console.log('Sending to design phase chatbot:', message);
    
    // Send message to chat if callback is provided
    if (onSendChatMessage) {
      onSendChatMessage(message);
    } else {
      // Fallback: dispatch event for parent components to handle
      window.dispatchEvent(new CustomEvent('sendToChatbot', {
        detail: { message, phase: currentPhase, epic: epicName }
      }));
    }
  };

  // Paginate epics
  const paginatedEpics = epics.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  // Loading state
  if (loading) {
    return (
      <Container
        header={
          <Header
            variant="h3"
            description={isGenerating ? "Generating new epics..." : "Fetching project epics..."}
          >
            <SpaceBetween direction="horizontal" size="xs" alignItems="center">
              <Icon name="status-in-progress" />
              <span>Project Epics</span>
            </SpaceBetween>
          </Header>
        }
      >
        <Box textAlign="center" padding="xl">
          <SpaceBetween size="l" alignItems="center">
            <Spinner size="large" />
            <TextContent>
              <h3>{isGenerating ? "📋 Generating epics..." : "Loading epics..."}</h3>
              <p>{isGenerating ? "Creating project structure and epic definitions from requirements" : "Gathering project structure and epic definitions"}</p>
            </TextContent>
            <ProgressBar value={isGenerating ? 80 : 60} variant={isGenerating ? "flash" : "normal"} />
          </SpaceBetween>
        </Box>
      </Container>
    );
  }

  // Error state
  if (error) {
    return (
      <Container
        header={
          <Header
            variant="h3"
            description="Unable to load epics"
          >
            <SpaceBetween direction="horizontal" size="xs" alignItems="center">
              <Icon name="status-negative" variant="error" />
              <span>Project Epics</span>
            </SpaceBetween>
          </Header>
        }
      >
        <Alert
          type="error"
          header="Connection Failed"
        >
          <SpaceBetween size="m">
            <div>{error}</div>
            <Button
              onClick={fetchEpics}
              iconName="refresh"
              variant="primary"
            >
              Retry Connection
            </Button>
          </SpaceBetween>
        </Alert>
      </Container>
    );
  }

  // Empty state
  if (!epics || epics.length === 0) {
    return (
      <Container
        header={
          <Header
            variant="h3"
            description="Ready to create epics"
            actions={
              <Button
                onClick={fetchEpics}
                iconName="refresh"
                variant="icon"
                ariaLabel="Refresh epics"
              />
            }
          >
            <SpaceBetween direction="horizontal" size="xs" alignItems="center">
              <Icon name="folder" />
              <span>Project Epics</span>
            </SpaceBetween>
          </Header>
        }
      >
        <Box textAlign="center" padding="xl">
          <SpaceBetween size="l" alignItems="center">
            <Icon name="folder" size="large" variant="subtle" />
            <TextContent>
              <h3>No epics defined yet</h3>
              <p>
                Epics will appear here automatically when generated through the chat interface.
              </p>
              <Badge color="blue">💡 Try asking: "Break down this project into epics and features"</Badge>
            </TextContent>
            <Button
              onClick={fetchEpics}
              iconName="refresh"
              variant="normal"
            >
              Check for epics
            </Button>
          </SpaceBetween>
        </Box>
      </Container>
    );
  }

  // Main render with Cards component
  return (
    <Container
      header={
        <Header
          variant="h3"
          description={
            <SpaceBetween direction="horizontal" size="s" alignItems="center">
              <span>{metadata.total_epics} epic{metadata.total_epics !== 1 ? 's' : ''} defined</span>
              {isGenerating ? (
                <StatusIndicator type="in-progress">Generating...</StatusIndicator>
              ) : (
                <StatusIndicator type="success">Active</StatusIndicator>
              )}
            </SpaceBetween>
          }
          actions={
            <Button
              onClick={fetchEpics}
              iconName="refresh"
              variant="icon"
              ariaLabel="Refresh epics"
              loading={loading || isGenerating}
            />
          }
        >
          <SpaceBetween direction="horizontal" size="xs" alignItems="center">
            <Icon name="folder" />
            <span>Project Epics</span>
            {isGenerating && <Spinner size="small" />}
          </SpaceBetween>
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Cards
          cardDefinition={{
            header: (epic, index) => (
              <SpaceBetween direction="horizontal" size="s" alignItems="center">
                <span>📋</span>
                <TextContent>
                  <h4>
                    {epic.title || `Epic ${index + 1}`}
                  </h4>
                </TextContent>
                <StatusIndicator type="success" />
              </SpaceBetween>
            ),
              sections: [
                {
                  id: "description",
                  content: (epic) => epic.description && (
                    <TextContent>
                      <p>
                        {epic.description}
                      </p>
                    </TextContent>
                  )
                },
                {
                  id: "features",
                  content: (epic) => epic.features && epic.features.length > 0 && (
                    <ExpandableSection
                      headerText={
                        <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                          <Icon name="list" size="small" />
                          <span>Features ({epic.features.length})</span>
                        </SpaceBetween>
                      }
                      variant="footer"
                      defaultExpanded={epic.features.length <= 3}
                    >
                      <Box padding={{ left: 's' }}>
                        <ul>
                          {epic.features.map((feature, featureIndex) => (
                            <li key={featureIndex} style={{ marginBottom: '4px' }}>
                              {feature}
                            </li>
                          ))}
                        </ul>
                      </Box>
                    </ExpandableSection>
                  )
                },
                {
                  id: "design-actions",
                  content: (epic, index) => currentPhase === 'design' && (
                    <Box>
                      <SpaceBetween direction="horizontal" size="s">
                        <Button
                          variant="normal"
                          iconName="share"
                          onClick={() => handleGenerateDesignDiagram(epic)}
                          ariaLabel={`Generate design diagram for ${epic.title || `Epic ${index + 1}`}`}
                        >
                          Generate Diagram
                        </Button>
                        <Button
                          variant="normal"
                          iconName="file"
                          onClick={() => handleGenerateOpenAPISpec(epic)}
                          ariaLabel={`Generate OpenAPI spec for ${epic.title || `Epic ${index + 1}`}`}
                        >
                          Generate API Spec
                        </Button>
                      </SpaceBetween>
                    </Box>
                  )
                },
                {
                  id: "metadata",
                  content: (epic) => (
                    <SpaceBetween direction="horizontal" size="s" alignItems="center">
                      <Badge color="blue">
                        Epic
                      </Badge>
                      {epic.created_at && (
                        <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                          <Icon name="calendar" size="small" />
                          <span>Created {new Date(epic.created_at).toLocaleDateString()}</span>
                        </SpaceBetween>
                      )}
                    </SpaceBetween>
                  )
                }
              ]
            }}
            items={paginatedEpics}
            loadingText="Loading epics..."
            empty={
              <Box textAlign="center" padding="xl">
                <SpaceBetween size="l" alignItems="center">
                  <Icon name="folder" size="large" variant="subtle" />
                  <TextContent>
                    <h3>No epics to display</h3>
                    <p>Epics will appear here when created.</p>
                  </TextContent>
                </SpaceBetween>
              </Box>
            }
            cardsPerRow={[
              { cards: 1 },
              { minWidth: 700, cards: 2 }
            ]}
          />

        {epics.length > pageSize && (
          <Pagination
            currentPageIndex={currentPageIndex}
            pagesCount={Math.ceil(epics.length / pageSize)}
            onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
          />
        )}
      </SpaceBetween>
    </Container>
  );
};

export default EpicsPanel;