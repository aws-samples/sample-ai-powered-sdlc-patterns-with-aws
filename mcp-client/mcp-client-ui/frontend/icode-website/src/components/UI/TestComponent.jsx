import React, { useState } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Grid,
  Box,
  Alert
} from '@cloudscape-design/components';
import SDLCTabs from './SDLCTabs';
import PhaseSpecificChatBox from './PhaseSpecificChatBox';

const TestComponent = () => {
  const [activeTabId, setActiveTabId] = useState('requirements');
  const [specifications, setSpecifications] = useState({});
  const [conversationIds, setConversationIds] = useState({});
  const [error, setError] = useState(null);

  const handleTabChange = ({ detail }) => {
    setActiveTabId(detail.activeTabId);
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

  return (
    <Container
      header={
        <Header variant="h1">
          SDLC Integration Platform Test
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        {error && (
          <Alert type="error" dismissible onDismiss={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Grid gridDefinition={[{ colspan: 8 }, { colspan: 4 }]}>
          {/* Left side - Specification Canvas */}
          <SDLCTabs
            activeTabId={activeTabId}
            onTabChange={handleTabChange}
            specifications={specifications}
            conversationIds={conversationIds}
            projectName="Test Project"
          />

          {/* Right side - Phase-specific ChatBox */}
          <PhaseSpecificChatBox
            phase={activeTabId}
            projectName="Test Project"
            onSpecificationUpdate={handleSpecificationUpdate}
            onConversationIdUpdate={handleConversationIdUpdate}
          />
        </Grid>

        {/* Debug Information */}
        <Container>
          <Header variant="h3">Debug Information</Header>
          <SpaceBetween direction="vertical" size="s">
            <Box>
              <strong>Active Phase:</strong> {activeTabId}
            </Box>
            <Box>
              <strong>Conversation IDs:</strong> {JSON.stringify(conversationIds, null, 2)}
            </Box>
            <Box>
              <strong>Specifications:</strong> {Object.keys(specifications).length} loaded
            </Box>
            {Object.keys(specifications).map(phase => (
              <Box key={phase}>
                <strong>{phase}:</strong> {specifications[phase]?.title || 'No title'}
              </Box>
            ))}
          </SpaceBetween>
        </Container>
      </SpaceBetween>
    </Container>
  );
};

export default TestComponent;