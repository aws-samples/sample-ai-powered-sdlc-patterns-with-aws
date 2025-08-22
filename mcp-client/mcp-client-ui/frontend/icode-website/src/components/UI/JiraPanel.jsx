/**
 * Jira Panel Component
 * 
 * Combined panel that displays both Jira tickets and epics for the requirements phase
 */

import { useState, useEffect } from 'react';
import {
  Tabs,
  Box,
  Button,
  Alert,
  Container,
  Header,
  SpaceBetween,
  Badge,
  Icon
} from '@cloudscape-design/components';
import JiraTicketsPanel from './JiraTicketsPanel';
import EpicsPanel from './EpicsPanel';
import { getJiraMetadata } from '../../services/jiraService';
import './JiraPanel.css';

// Extract base project ID from conversation ID
const extractBaseProjectId = (conversationId) => {
  if (!conversationId) return conversationId;
  
  // Pattern: phase_projectId_timestamp
  // Example: requirements_any-company-reads2_20250729_141040
  const parts = conversationId.split('_');
  if (parts.length >= 3) {
    // Remove the first part (phase) and last two parts (date and time)
    const baseProjectId = parts.slice(1, -2).join('_');
    // Extracted base project ID
    return baseProjectId;
  }
  
  // Could not extract base project ID, using as-is
  return conversationId;
};

const JiraPanel = ({ projectId, autoLoad = true, externalRefreshTrigger = 0, currentPhase = 'requirements', onSendChatMessage }) => {
  const [activeTabId, setActiveTabId] = useState('epics');
  const [metadata, setMetadata] = useState({
    has_tickets: false,
    has_epics: false,
    total_tickets: 0,
    total_epics: 0
  });
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch metadata to determine what to show
  const fetchMetadata = async () => {
    if (!projectId) return;

    // Extract base project ID for Jira data lookup
    const baseProjectId = extractBaseProjectId(projectId);

    try {
      setLoading(true);
      setError(null);
      // Fetching metadata for project
      const metadataData = await getJiraMetadata(baseProjectId, true); // Bust cache on refresh
      console.log(`🔄 JiraPanel: Received metadata:`, metadataData);
      setMetadata(metadataData);

      // Auto-select the tab with data, preferring epics
      if (metadataData.has_epics) {
        // Setting active tab to epics
        setActiveTabId('epics');
      } else if (metadataData.has_tickets) {
        // Setting active tab to tickets
        setActiveTabId('tickets');
      } else {
        console.log(`🔄 JiraPanel: No epics or tickets found`);
      }
    } catch (err) {
      console.error('Error fetching Jira metadata:', err);
      setError('Failed to load Jira data');
    } finally {
      setLoading(false);
    }
  };

  // Fetch metadata when component mounts or projectId changes (like diagrams)
  useEffect(() => {
    if (autoLoad && projectId) {
      fetchMetadata();
    }
  }, [projectId, autoLoad]);

  // Also fetch when external refresh trigger changes (for automatic refresh)
  useEffect(() => {
    if (externalRefreshTrigger > 0) {
      // External refresh trigger changed - refreshing data
      
      // Add a small delay to ensure backend has saved the data
      setTimeout(() => {
        fetchMetadata();
      }, 1000);
      
      // Also update internal refresh trigger to refresh child components
      setRefreshTrigger(prev => {
        const newTrigger = prev + 1;
        // Updating internal refresh trigger
        return newTrigger;
      });
    }
  }, [externalRefreshTrigger]);

  // Remove auto-refresh polling - we'll fetch on demand like diagrams

  // Refresh all data (manual refresh button)
  const handleRefresh = () => {
    console.log('🔄 JiraPanel: Manual refresh triggered');
    setRefreshTrigger(prev => prev + 1);
    fetchMetadata();
  };

  // Don't render if no Jira data exists
  if (!loading && !error && !metadata.has_tickets && !metadata.has_epics) {
    return null;
  }

  // Error state
  if (error) {
    return (
      <SpaceBetween size="l">
        <Header 
          variant="h3"
          description="Unable to load Jira data"
        >
          Jira Integration
        </Header>
        <Alert 
          type="error" 
          header="Connection Error"
        >
          <SpaceBetween size="s">
            <div>{error}</div>
            <Button 
              onClick={handleRefresh} 
              iconName="refresh"
              variant="primary"
              size="small"
            >
              Retry Connection
            </Button>
          </SpaceBetween>
        </Alert>
      </SpaceBetween>
    );
  }

  // Prepare tabs
  const tabs = [];

  // Add Epics tab if epics exist
  if (metadata.has_epics || loading) {
    tabs.push({
      id: 'epics',
      label: (
        <SpaceBetween direction="horizontal" size="xs" alignItems="center">
          <Icon name="folder" />
          <span>Epics</span>
        </SpaceBetween>
      ),
      badge: metadata.total_epics > 0 ? { 
        color: 'blue', 
        children: metadata.total_epics 
      } : undefined,
      content: (
        <EpicsPanel
          projectId={extractBaseProjectId(projectId)}
          refreshTrigger={refreshTrigger}
          currentPhase={currentPhase}
          onSendChatMessage={onSendChatMessage}
        />
      )
    });
  }

  // Add Tickets tab if tickets exist
  if (metadata.has_tickets || loading) {
    tabs.push({
      id: 'tickets',
      label: (
        <SpaceBetween direction="horizontal" size="xs" alignItems="center">
          <Icon name="ticket" />
          <span>Tickets</span>
        </SpaceBetween>
      ),
      badge: metadata.total_tickets > 0 ? { 
        color: 'green', 
        children: metadata.total_tickets 
      } : undefined,
      content: (
        <JiraTicketsPanel
          projectId={extractBaseProjectId(projectId)}
          refreshTrigger={refreshTrigger}
        />
      )
    });
  }

  // If no tabs, don't render
  if (tabs.length === 0) {
    return null;
  }

  // Single tab - render directly without tabs
  if (tabs.length === 1) {
    return (
      <div className="jira-panel-single">
        {tabs[0].content}
      </div>
    );
  }

  // Multiple tabs - render with tab interface
  return (
    <SpaceBetween size="l">
      <Header
        variant="h3"
        description={
          <SpaceBetween direction="horizontal" size="s" alignItems="center">
            <span>Project requirements and planning</span>
            <Badge color="blue">
              {metadata.total_epics + metadata.total_tickets} items
            </Badge>
          </SpaceBetween>
        }
        actions={
          <SpaceBetween direction="horizontal" size="s">
            <Button
              onClick={handleRefresh}
              iconName="refresh"
              variant="icon"
              ariaLabel="Refresh all Jira data"
              loading={loading}
            />
          </SpaceBetween>
        }
      >
        Jira Integration
      </Header>
      
      <div className="jira-panel-tabs">
        <Tabs
          activeTabId={activeTabId}
          onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
          tabs={tabs.map(tab => ({
            id: tab.id,
            label: tab.label,
            badge: tab.badge,
            content: (
              <Box padding={{ top: 'm' }}>
                {tab.content}
              </Box>
            )
          }))}
          variant="default"
        />
      </div>
    </SpaceBetween>
  );
};

export default JiraPanel;