/**
 * Custom hook for managing Jira data
 * 
 * Provides functionality to fetch and refresh Jira tickets and epics
 */

import { useState, useEffect, useCallback } from 'react';
import { getAllJiraData, getJiraMetadata } from '../services/jiraService';

export const useJiraData = (projectId) => {
  const [jiraData, setJiraData] = useState({
    tickets: [],
    epics: [],
    total_tickets: 0,
    total_epics: 0,
    last_updated: null
  });
  const [metadata, setMetadata] = useState({
    has_tickets: false,
    has_epics: false,
    total_tickets: 0,
    total_epics: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all Jira data
  const fetchJiraData = useCallback(async () => {
    if (!projectId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const [allData, metadataData] = await Promise.all([
        getAllJiraData(projectId),
        getJiraMetadata(projectId)
      ]);
      
      setJiraData(allData);
      setMetadata(metadataData);
    } catch (err) {
      console.error('Error fetching Jira data:', err);
      setError('Failed to load Jira data');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Refresh data
  const refreshJiraData = useCallback(() => {
    fetchJiraData();
  }, [fetchJiraData]);

  // Check if there's any Jira data
  const hasJiraData = metadata.has_tickets || metadata.has_epics;

  // Fetch data on mount and when projectId changes
  useEffect(() => {
    fetchJiraData();
  }, [fetchJiraData]);

  return {
    jiraData,
    metadata,
    loading,
    error,
    hasJiraData,
    refreshJiraData
  };
};

export default useJiraData;