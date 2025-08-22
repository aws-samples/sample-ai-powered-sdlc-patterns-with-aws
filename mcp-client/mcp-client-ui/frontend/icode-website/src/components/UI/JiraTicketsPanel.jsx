/**
 * Jira Tickets Panel Component
 * 
 * Displays Jira tickets in a beautiful CloudScape panel for the requirements phase
 */

import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Badge,
  Link,
  Alert,
  Spinner,
  TextContent,
  Button,
  Icon,
  Cards,
  CollectionPreferences,
  Pagination,
  StatusIndicator,
  ProgressBar
} from '@cloudscape-design/components';
import { getJiraTickets, getJiraMetadata } from '../../services/jiraService';
import './JiraTicketsPanel.css';

const JiraTicketsPanel = ({ projectId, refreshTrigger = 0 }) => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState({ total_tickets: 0 });
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [pageSize, setPageSize] = useState(6);

  // Fetch tickets data
  const fetchTickets = async () => {
    if (!projectId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const [ticketsData, metadataData] = await Promise.all([
        getJiraTickets(projectId),
        getJiraMetadata(projectId)
      ]);
      
      setTickets(ticketsData);
      setMetadata(metadataData);
    } catch (err) {
      console.error('Error fetching Jira tickets:', err);
      setError('Failed to load Jira tickets');
    } finally {
      setLoading(false);
    }
  };

  // Fetch data on component mount and when refresh trigger changes
  useEffect(() => {
    fetchTickets();
  }, [projectId, refreshTrigger]);

  // Get badge variant based on ticket status
  const getStatusBadgeVariant = (status) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'new':
      case 'to do':
        return 'blue';
      case 'in progress':
      case 'active':
      case 'doing':
        return 'green';
      case 'done':
      case 'closed':
      case 'resolved':
        return 'grey';
      case 'blocked':
        return 'red';
      default:
        return 'blue';
    }
  };

  // Get issue type icon and color
  const getIssueTypeInfo = (issueType) => {
    switch (issueType?.toLowerCase()) {
      case 'epic':
        return { iconName: 'folder', color: '#6B46C1' };
      case 'story':
      case 'user story':
        return { iconName: 'file', color: '#059669' };
      case 'task':
        return { iconName: 'status-positive', color: '#0891B2' };
      case 'bug':
        return { iconName: 'status-negative', color: '#DC2626' };
      case 'new feature':
      case 'feature':
        return { iconName: 'add-plus', color: '#D97706' };
      case 'improvement':
        return { iconName: 'settings', color: '#7C3AED' };
      default:
        return { iconName: 'ticket', color: '#6B7280' };
    }
  };

  // Paginate tickets
  const paginatedTickets = tickets.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  // Loading state
  if (loading) {
    return (
      <SpaceBetween size="l">
        <Header 
          variant="h3"
          description="Fetching your Jira tickets..."
        >
          <SpaceBetween direction="horizontal" size="xs" alignItems="center">
            <Icon name="status-in-progress" />
            <span>Jira Tickets</span>
          </SpaceBetween>
        </Header>
        <Box textAlign="center" padding="xl">
          <SpaceBetween size="l" alignItems="center">
            <div className="jira-loading-animation">
              <Spinner size="large" />
            </div>
            <TextContent>
              <h3>Loading tickets...</h3>
              <p>Connecting to Jira and fetching your project tickets</p>
            </TextContent>
            <ProgressBar value={75} variant="flash" />
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    );
  }

  // Error state
  if (error) {
    return (
      <SpaceBetween size="l">
        <Header 
          variant="h3"
          description="Unable to load tickets"
        >
          <SpaceBetween direction="horizontal" size="xs" alignItems="center">
            <Icon name="status-negative" variant="error" />
            <span>Jira Tickets</span>
          </SpaceBetween>
        </Header>
        <Alert 
          type="error" 
          header="Connection Failed"
        >
          <SpaceBetween size="m">
            <div className="error-message">{error}</div>
            <div className="error-actions">
              <Button 
                onClick={fetchTickets} 
                iconName="refresh"
                variant="primary"
              >
                Retry Connection
              </Button>
            </div>
          </SpaceBetween>
        </Alert>
      </SpaceBetween>
    );
  }

  // Empty state
  if (!tickets || tickets.length === 0) {
    return (
      <SpaceBetween size="l">
        <Header 
          variant="h3"
          description="Ready to create tickets"
          actions={
            <Button 
              onClick={fetchTickets} 
              iconName="refresh"
              variant="icon"
              ariaLabel="Refresh tickets"
            />
          }
        >
          <SpaceBetween direction="horizontal" size="xs" alignItems="center">
            <Icon name="ticket" />
            <span>Jira Tickets</span>
          </SpaceBetween>
        </Header>
        <Box textAlign="center" padding="xl">
          <SpaceBetween size="l" alignItems="center">
            <div className="empty-state-icon">
              <Icon name="ticket" size="large" variant="subtle" />
            </div>
            <TextContent>
              <h3>No tickets created yet</h3>
              <p className="empty-description">
                Tickets will appear here automatically when created through the chat interface.
              </p>
              <div className="empty-suggestions">
                <Badge color="blue">💡 Try asking: "Create Jira tickets for this project"</Badge>
              </div>
            </TextContent>
            <Button 
              onClick={fetchTickets}
              iconName="refresh"
              variant="normal"
            >
              Check for tickets
            </Button>
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    );
  }

  // Main render with Cards component
  return (
    <SpaceBetween size="l">
      <Header 
        variant="h3"
        description={
          <SpaceBetween direction="horizontal" size="s" alignItems="center">
            <span>{metadata.total_tickets} ticket{metadata.total_tickets !== 1 ? 's' : ''} found</span>
            <StatusIndicator type="success">Active</StatusIndicator>
          </SpaceBetween>
        }
        actions={
          <SpaceBetween direction="horizontal" size="s">
            <Badge color="green">{tickets.length} loaded</Badge>
            <Button 
              onClick={fetchTickets} 
              iconName="refresh"
              variant="icon"
              ariaLabel="Refresh tickets"
              loading={loading}
            />
          </SpaceBetween>
        }
      >
        <SpaceBetween direction="horizontal" size="xs" alignItems="center">
          <Icon name="ticket" />
          <span>Jira Tickets</span>
        </SpaceBetween>
      </Header>
      
      <div className="jira-tickets-grid">
        <Cards
          cardDefinition={{
            header: (ticket) => {
              const typeInfo = getIssueTypeInfo(ticket.issue_type);
              return (
                <div className="ticket-card-header">
                  <SpaceBetween direction="horizontal" size="s" alignItems="center">
                    <div className="ticket-type-icon" style={{ color: typeInfo.color }}>
                      <Icon name={typeInfo.iconName} />
                    </div>
                    <Link 
                      href={ticket.url} 
                      external
                      fontSize="body-s"
                      fontWeight="bold"
                      className="ticket-key-link"
                    >
                      {ticket.key}
                    </Link>
                    <StatusIndicator 
                      type={ticket.status?.toLowerCase() === 'done' ? 'success' : 
                            ticket.status?.toLowerCase() === 'in progress' ? 'in-progress' : 
                            'pending'}
                    >
                      {ticket.status || 'Open'}
                    </StatusIndicator>
                  </SpaceBetween>
                </div>
              );
            },
            sections: [
              {
                id: "summary",
                content: (ticket) => (
                  <div className="ticket-summary">
                    <TextContent>
                      <p className="summary-text">
                        {ticket.summary || 'No summary available'}
                      </p>
                    </TextContent>
                  </div>
                )
              },
              {
                id: "metadata",
                content: (ticket) => {
                  const typeInfo = getIssueTypeInfo(ticket.issue_type);
                  return (
                    <div className="ticket-metadata">
                      <SpaceBetween direction="horizontal" size="s" alignItems="center">
                        <Badge 
                          color="grey"
                          className="type-badge"
                          style={{ 
                            backgroundColor: typeInfo.color + '15', 
                            color: typeInfo.color,
                            border: `1px solid ${typeInfo.color}30`
                          }}
                        >
                          {ticket.issue_type || 'Task'}
                        </Badge>
                        {ticket.created_at && (
                          <div className="ticket-date">
                            <Icon name="calendar" size="small" />
                            <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                          </div>
                        )}
                      </SpaceBetween>
                    </div>
                  );
                }
              }
            ]
          }}
          items={paginatedTickets}
          loadingText="Loading tickets..."
          empty={
            <Box textAlign="center" padding="xl">
              <SpaceBetween size="l" alignItems="center">
                <Icon name="ticket" size="large" variant="subtle" />
                <TextContent>
                  <h3>No tickets to display</h3>
                  <p>Tickets will appear here when created.</p>
                </TextContent>
              </SpaceBetween>
            </Box>
          }
          cardsPerRow={[
            { cards: 1 },
            { minWidth: 600, cards: 2 },
            { minWidth: 900, cards: 3 }
          ]}
        />
      </div>
      
      {tickets.length > pageSize && (
        <Pagination
          currentPageIndex={currentPageIndex}
          pagesCount={Math.ceil(tickets.length / pageSize)}
          onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
        />
      )}
    </SpaceBetween>
  );
};

export default JiraTicketsPanel;