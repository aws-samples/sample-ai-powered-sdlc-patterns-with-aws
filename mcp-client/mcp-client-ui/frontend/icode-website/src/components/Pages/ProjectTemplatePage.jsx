import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  Box,
  SpaceBetween,
  Spinner,
  Alert,
  BreadcrumbGroup,
  Badge,
  Grid
} from '@cloudscape-design/components';
import { fetchProjectDetails } from '../../services/projectService';
import { urlToProjectName } from '../../utils/urlUtils';
import { SDLCTabs, PhaseSpecificChatBox } from '../UI';

const ProjectTemplatePage = () => {
  const { projectName } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTabId, setActiveTabId] = useState('requirements');
  const [specifications, setSpecifications] = useState({});
  const [conversationIds, setConversationIds] = useState({});
  const [specificationsLoading, setSpecificationsLoading] = useState(false);
  const [specificationsError, setSpecificationsError] = useState(null);
  const [codeGenerationTrigger, setCodeGenerationTrigger] = useState(0);
  const [jiraRefreshTrigger, setJiraRefreshTrigger] = useState(0);
  const [diagramRefreshTrigger, setDiagramRefreshTrigger] = useState(0);
  const [pdfRefreshTrigger, setPdfRefreshTrigger] = useState(0);
  const chatRef = useRef(null);

  // Convert URL parameter back to display name
  const displayName = urlToProjectName(projectName);

  const handleTabChange = ({ detail }) => {
    setActiveTabId(detail.activeTabId);
    // Only load specification if we don't already have one for this phase
    if (!specifications[detail.activeTabId]) {
      loadPhaseSpecification(detail.activeTabId);
    }
  };

  const handleSpecificationUpdate = (phase, specification) => {
    setSpecifications(prev => ({
      ...prev,
      [phase]: specification
    }));
  };

  const handleConversationIdUpdate = (phase, conversationId) => {
    setConversationIds(prev => ({
      ...prev,
      [phase]: conversationId
    }));
  };

  const handleCodeGenerated = (phase, conversationId) => {
    // Trigger a refresh of the code download section by incrementing the trigger
    setCodeGenerationTrigger(prev => prev + 1);
  };

  const handleJiraDataUpdated = (phase, conversationId) => {
    // Trigger a refresh of the Jira panel by incrementing the trigger
    setJiraRefreshTrigger(prev => prev + 1);
  };

  const handleDiagramGenerated = (phase, conversationId) => {
    // Trigger a refresh of the diagram section by incrementing the trigger
    setDiagramRefreshTrigger(prev => prev + 1);
  };

  const handlePdfGenerated = (phase, conversationId) => {
    // Trigger a refresh of the PDF section by incrementing the trigger
    setPdfRefreshTrigger(prev => prev + 1);
  };

  // Handler to send message to chat
  const handleSendChatMessage = (message) => {
    console.log('Sending message to chat:', message);
    if (chatRef.current && chatRef.current.sendMessage) {
      chatRef.current.sendMessage(message);
    } else {
      console.warn('Chat ref not available, cannot send message:', message);
    }
  };

  const loadPhaseSpecification = async (phase) => {
    // Check if we already have a specification for this phase
    if (specifications[phase]) {
      return; // Don't overwrite existing specifications
    }

    setSpecificationsLoading(true);
    setSpecificationsError(null);
    
    try {
      await new Promise(resolve => setTimeout(resolve, 300));
            
    } catch (err) {
      setSpecificationsError(`Failed to load ${phase} specification`);
    } finally {
      setSpecificationsLoading(false);
    }
  };

  useEffect(() => {
    const loadProjectDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const projectData = await fetchProjectDetails(projectName);
        setProject(projectData);
        
        // Load initial specification for the default tab
        loadPhaseSpecification(activeTabId);
      } catch (err) {
        setError(err.message || 'Failed to load project details');
        setProject(null);
      } finally {
        setLoading(false);
      }
    };

    if (projectName) {
      loadProjectDetails();
    }
  }, [projectName]);

  const breadcrumbItems = [
    {
      text: 'Home',
      href: '/'
    },
    {
      text: 'My Projects',
      href: '/'
    },
    {
      text: displayName,
      href: `/project/${projectName}`
    }
  ];

  const handleBreadcrumbClick = (event, item) => {
    event.preventDefault();
    navigate(item.href);
  };

  if (loading) {
    return (
      <Box textAlign="center" padding="xl">
        <Spinner size="large" />
        <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>
          Loading project details...
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <SpaceBetween size="m">
        <BreadcrumbGroup
          items={breadcrumbItems}
          onFollow={handleBreadcrumbClick}
        />
        <Alert type="error" header="Unable to load project">
          {error}
        </Alert>
      </SpaceBetween>
    );
  }

  if (!project) {
    return (
      <SpaceBetween size="m">
        <BreadcrumbGroup
          items={breadcrumbItems}
          onFollow={handleBreadcrumbClick}
        />
        <Alert type="warning" header="Project not found">
          The project "{displayName}" could not be found.
        </Alert>
      </SpaceBetween>
    );
  }

  const getStatusVariant = (status) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'success';
      case 'draft':
        return 'warning';
      case 'completed':
        return 'info';
      case 'archived':
        return 'grey';
      default:
        return 'info';
    }
  };





  return (
    <SpaceBetween size="l">
      <BreadcrumbGroup
        items={breadcrumbItems}
        onFollow={handleBreadcrumbClick}
      />

      <Header
        variant="h1"
        description={project.description || 'No description provided'}
        actions={
          <Badge color={getStatusVariant(project.status)}>
            {project.status || 'Active'}
          </Badge>
        }
      >
        {project.name || displayName}
      </Header>

      {/* Two-column layout: Project details on left, Chat on right */}
      <Grid gridDefinition={[{ colspan: 7 }, { colspan: 5 }]}>
        {/* Left column - Project Details */}
        <SpaceBetween size="l">
          <SDLCTabs
            activeTabId={activeTabId}
            onTabChange={handleTabChange}
            specifications={specifications}
            conversationIds={conversationIds}
            projectName={projectName}
            loading={specificationsLoading}
            error={specificationsError}
            codeGenerationTrigger={codeGenerationTrigger}
            jiraRefreshTrigger={jiraRefreshTrigger}
            diagramRefreshTrigger={diagramRefreshTrigger}
            pdfRefreshTrigger={pdfRefreshTrigger}
            onSendChatMessage={handleSendChatMessage}
          />


        </SpaceBetween>

        {/* Right column - Phase-Specific Chat Box */}
        <PhaseSpecificChatBox 
          ref={chatRef}
          phase={activeTabId}
          projectName={projectName}
          onSpecificationUpdate={handleSpecificationUpdate}
          onConversationIdUpdate={handleConversationIdUpdate}
          onCodeGenerated={handleCodeGenerated}
          onJiraDataUpdated={handleJiraDataUpdated}
          onDiagramGenerated={handleDiagramGenerated}
          onPdfGenerated={handlePdfGenerated}
        />
      </Grid>
    </SpaceBetween>
  );
};

export default ProjectTemplatePage;