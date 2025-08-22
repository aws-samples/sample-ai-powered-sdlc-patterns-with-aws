import React from 'react';
import {
  Container,
  Header,
  Box,
  SpaceBetween,
  ColumnLayout,
  Badge,
  TextContent
} from '@cloudscape-design/components';


/**
 * Component to display requirements specification in a formatted, readable way
 */
const RequirementsSpecificationDisplay = ({ specification, conversationId, projectName }) => {
  if (!specification || !specification.content) {
    return null;
  }

  const content = specification.content;

  // Helper function to render a list of items
  const renderList = (items, title) => {
    if (!items || !Array.isArray(items) || items.length === 0) {
      return null;
    }

    return (
      <Box margin={{ bottom: 'm' }}>
        <Header variant="h4">{title}</Header>
        <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
          {items.map((item, index) => (
            <li key={index} style={{ marginBottom: '8px' }}>
              {typeof item === 'string' ? item : JSON.stringify(item)}
            </li>
          ))}
        </ul>
      </Box>
    );
  };

  // Helper function to render requirements with priorities
  const renderRequirements = (requirements, title) => {
    if (!requirements || !Array.isArray(requirements) || requirements.length === 0) {
      return null;
    }

    return (
      <Box margin={{ bottom: 'm' }}>
        <Header variant="h4">{title}</Header>
        <SpaceBetween size="s">
          {requirements.map((req, index) => (
            <Box key={index} padding="s" style={{ 
              border: '1px solid #e9ecef', 
              borderRadius: '4px',
              backgroundColor: '#f8f9fa'
            }}>
              <SpaceBetween size="xs" direction="horizontal">
                <TextContent>
                  <strong>REQ-{String(index + 1).padStart(3, '0')}</strong>
                </TextContent>
                {req.priority && (
                  <Badge color={
                    req.priority.toLowerCase() === 'high' ? 'red' :
                    req.priority.toLowerCase() === 'medium' ? 'blue' : 'grey'
                  }>
                    {req.priority}
                  </Badge>
                )}
              </SpaceBetween>
              <Box margin={{ top: 'xs' }}>
                <TextContent>
                  {typeof req === 'string' ? req : req.description || req.requirement || JSON.stringify(req)}
                </TextContent>
              </Box>
            </Box>
          ))}
        </SpaceBetween>
      </Box>
    );
  };

  // Helper function to render text content
  const renderTextContent = (text, title) => {
    if (!text) return null;
    
    return (
      <Box margin={{ bottom: 'm' }}>
        <Header variant="h4">{title}</Header>
        <TextContent>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
            {text}
          </div>
        </TextContent>
      </Box>
    );
  };

  return (
    <Container
      header={
        <Header 
          variant="h2"
          description={content.summary || 'Software Requirements Specification'}

        >
          {specification.title || 'Requirements Specification'}
        </Header>
      }
    >
      <SpaceBetween size="l">
        {/* Project Overview */}
        {content.overview && renderTextContent(content.overview, 'Project Overview')}
        
        {/* Project Scope */}
        {content.project_scope && renderTextContent(content.project_scope, 'Project Scope')}
        
        {/* Target Users */}
        {content.target_users && renderList(content.target_users, 'Target Users')}
        
        {/* Two-column layout for requirements */}
        <ColumnLayout columns={2} variant="text-grid">
          <div>
            {/* Functional Requirements */}
            {content.functional_requirements && 
              renderRequirements(content.functional_requirements, 'Functional Requirements')}
          </div>
          <div>
            {/* Non-Functional Requirements */}
            {content.non_functional_requirements && 
              renderRequirements(content.non_functional_requirements, 'Non-Functional Requirements')}
          </div>
        </ColumnLayout>
        
        {/* System Requirements */}
        {content.system_requirements && (
          <Box>
            <Header variant="h4">System Requirements</Header>
            <ColumnLayout columns={2} variant="text-grid">
              <div>
                {content.system_requirements.hardware && 
                  renderList(content.system_requirements.hardware, 'Hardware Requirements')}
              </div>
              <div>
                {content.system_requirements.software && 
                  renderList(content.system_requirements.software, 'Software Requirements')}
              </div>
            </ColumnLayout>
          </Box>
        )}
        
        {/* Constraints */}
        {content.constraints && renderList(content.constraints, 'Constraints')}
        
        {/* Assumptions */}
        {content.assumptions && renderList(content.assumptions, 'Assumptions')}
        
        {/* Dependencies */}
        {content.dependencies && renderList(content.dependencies, 'Dependencies')}
        
        {/* Success Criteria */}
        {content.success_criteria && renderList(content.success_criteria, 'Success Criteria')}
        
        {/* Acceptance Criteria */}
        {content.acceptance_criteria && renderList(content.acceptance_criteria, 'Acceptance Criteria')}
        
        {/* Risk Assessment */}
        {content.risk_assessment && (
          <Box>
            <Header variant="h4">Risk Assessment</Header>
            {content.risk_assessment.risks && renderList(content.risk_assessment.risks, 'Identified Risks')}
            {content.risk_assessment.mitigation_strategies && 
              renderList(content.risk_assessment.mitigation_strategies, 'Mitigation Strategies')}
          </Box>
        )}
        
        {/* Timeline */}
        {content.timeline && (
          <Box>
            <Header variant="h4">Project Timeline</Header>
            {content.timeline.phases && (
              <SpaceBetween size="s">
                {content.timeline.phases.map((phase, index) => (
                  <Box key={index} padding="s" style={{ 
                    border: '1px solid #e9ecef', 
                    borderRadius: '4px' 
                  }}>
                    <SpaceBetween size="xs">
                      <TextContent>
                        <strong>{phase.name || `Phase ${index + 1}`}</strong>
                      </TextContent>
                      <TextContent>
                        Duration: {phase.duration || 'TBD'}
                      </TextContent>
                      {phase.deliverables && (
                        <TextContent>
                          Deliverables: {Array.isArray(phase.deliverables) 
                            ? phase.deliverables.join(', ') 
                            : phase.deliverables}
                        </TextContent>
                      )}
                    </SpaceBetween>
                  </Box>
                ))}
              </SpaceBetween>
            )}
          </Box>
        )}
        
        {/* Metadata */}
        {specification.metadata && (
          <Box>
            <Header variant="h4">Document Information</Header>
            <ColumnLayout columns={3} variant="text-grid">
              <TextContent>
                <strong>Version:</strong> {specification.version || '1.0'}
              </TextContent>
              <TextContent>
                <strong>Status:</strong> {specification.status || 'Draft'}
              </TextContent>
              <TextContent>
                <strong>Generated:</strong> {
                  specification.generated_at 
                    ? new Date(specification.generated_at).toLocaleDateString()
                    : 'N/A'
                }
              </TextContent>
            </ColumnLayout>
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
};

export default RequirementsSpecificationDisplay;