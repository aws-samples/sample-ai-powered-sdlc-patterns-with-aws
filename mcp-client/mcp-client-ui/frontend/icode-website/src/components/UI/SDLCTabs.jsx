import { useState, useEffect } from 'react';
import {
  Tabs,
  Box,
  Container,
  SpaceBetween,
  Header,
  Alert,
  ExpandableSection,
  Icon
} from '@cloudscape-design/components';
import PropTypes from 'prop-types';
import CodeDownloadSection from './CodeDownloadSection';
import DiagramDisplaySection from './DiagramDisplaySection';

import RequirementsSpecificationDisplay from './RequirementsSpecificationDisplay';
import JiraPanel from './JiraPanel';

const SDLCTabs = ({ 
  activeTabId, 
  onTabChange, 
  specifications = {}, 
  loading = false,
  error = null,
  conversationIds = {},
  projectName = null,
  codeGenerationTrigger = 0,
  jiraRefreshTrigger = 0,
  diagramRefreshTrigger = 0,

  onSendChatMessage
}) => {
  // SDLC phases configuration
  const SDLC_PHASES = [
    { 
      id: 'requirements', 
      label: 'Requirements',
      description: 'Gather and document project requirements'
    },
    { 
      id: 'design', 
      label: 'Design',
      description: 'Create system architecture and design specifications'
    },
    { 
      id: 'development', 
      label: 'Development',
      description: 'Plan development approach and implementation'
    },
    { 
      id: 'testing', 
      label: 'Testing',
      description: 'Define testing strategies and quality assurance'
    },
    { 
      id: 'deployment', 
      label: 'Deployment',
      description: 'Plan deployment and release strategies'
    },
    { 
      id: 'maintenance', 
      label: 'Maintenance',
      description: 'Define maintenance procedures and support processes'
    }
  ];

  const [localActiveTabId, setLocalActiveTabId] = useState(activeTabId || 'requirements');

  useEffect(() => {
    if (activeTabId && activeTabId !== localActiveTabId) {
      setLocalActiveTabId(activeTabId);
    }
  }, [activeTabId, localActiveTabId]);

  const handleTabChange = ({ detail }) => {
    const newTabId = detail.activeTabId;
    setLocalActiveTabId(newTabId);
    
    // Notify parent component of tab change
    if (onTabChange) {
      onTabChange({ detail: { activeTabId: newTabId } });
    }
  };

  const renderSpecificationContent = (phase) => {
    const specification = specifications[phase.id];
    const conversationId = conversationIds[phase.id];
    // Convert project name to project ID format (spaces to hyphens, lowercase)
    const normalizedProjectName = projectName ? projectName.toLowerCase().replace(/\s+/g, '-') : '';
    const codeProjectId = conversationId || normalizedProjectName;
    
    console.log('SDLCTabs: renderSpecificationContent called', {
      phaseId: phase.id,
      hasSpecification: !!specification,
      conversationId: conversationId,
      projectName: projectName,
      codeProjectId: codeProjectId
    });

    return (
      <SpaceBetween size="l">
        {/* Jira Panel - Show for all phases */}
        { codeProjectId && (
          <ExpandableSection
            headerText="Project Epics & Requirements"
            variant="default"
            defaultExpanded={phase.id === 'requirements'}
            headerDescription="View and manage project epics and Jira integration"
            key={`jira-panel-${codeProjectId}-${jiraRefreshTrigger}`}
          >
            <JiraPanel
              projectId={codeProjectId}
              autoLoad={true}
              externalRefreshTrigger={jiraRefreshTrigger}
              currentPhase={phase.id}
              onSendChatMessage={onSendChatMessage}
            />
          </ExpandableSection>
        )}


        
        {/* Diagram Display Section - Only for design phase */}
        {phase.id === 'design' && codeProjectId && (
          <DiagramDisplaySection
            projectId={codeProjectId}
            projectName={projectName || 'Architecture Project'}
            autoLoad={true}
            phase="design"
            key={`diagram-display-${codeProjectId}-${diagramRefreshTrigger}`}
            refreshTrigger={diagramRefreshTrigger}
          />
        )}
        
        {/* Code Download Section - Only for design phase */}
        {phase.id === 'design' && codeProjectId && (
          <CodeDownloadSection
            projectId={codeProjectId}
            projectName={projectName || 'Generated Architecture'}
            autoLoad={true}
            key={`code-download-${codeProjectId}-${codeGenerationTrigger}`}
            refreshTrigger={codeGenerationTrigger}
          />
        )}
        
        {/* Specification Display */}
        {specification && (
          <>
            {phase.id === 'requirements' ? (
              <RequirementsSpecificationDisplay 
                specification={specification} 
                conversationId={conversationId}
                projectName={projectName}
              />
            ) : (
              <Container
                header={
                  <Header variant="h3">
                    {specification.title || `${phase.label} Specification`}
                  </Header>
                }
              >
                <Box padding="l">
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                    {typeof specification.content === 'string' 
                      ? specification.content 
                      : JSON.stringify(specification.content, null, 2)
                    }
                  </div>
                </Box>
              </Container>
            )}
          </>
        )}
        

      </SpaceBetween>
    );
  };

  const tabs = SDLC_PHASES.map(phase => ({
    id: phase.id,
    label: phase.label,
    content: (
      <Box padding={{ top: 'l' }}>
        {renderSpecificationContent(phase)}
      </Box>
    )
  }));

  return (
    <Container>
      <Tabs
        activeTabId={localActiveTabId}
        onChange={handleTabChange}
        tabs={tabs}
        variant="default"
      />
    </Container>
  );
};



SDLCTabs.propTypes = {
  activeTabId: PropTypes.string,
  onTabChange: PropTypes.func,
  specifications: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  conversationIds: PropTypes.object,
  projectName: PropTypes.string,
  codeGenerationTrigger: PropTypes.number,
  jiraRefreshTrigger: PropTypes.number,
  diagramRefreshTrigger: PropTypes.number,
  pdfRefreshTrigger: PropTypes.number,
  onSendChatMessage: PropTypes.func
};

export default SDLCTabs;