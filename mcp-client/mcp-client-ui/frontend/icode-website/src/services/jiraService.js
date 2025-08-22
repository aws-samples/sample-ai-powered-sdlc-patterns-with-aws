/**
 * Jira Service
 * 
 * Handles API calls for Jira tickets and epics
 */

import { apiRequest } from './api';

/**
 * Get all Jira tickets for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Array>} Array of Jira tickets
 */
export const getJiraTickets = async (projectId) => {
  try {
    const response = await apiRequest(`/api/jira/${projectId}/tickets`, {
      method: 'GET'
    });
    return response || [];
  } catch (error) {
    console.error('Error fetching Jira tickets:', error);
    return [];
  }
};

/**
 * Get all epics for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Array>} Array of epics
 */
export const getEpics = async (projectId, bustCache = false) => {
  try {
    const url = bustCache 
      ? `/api/jira/${projectId}/epics?t=${Date.now()}`
      : `/api/jira/${projectId}/epics`;
    
    const response = await apiRequest(url, {
      method: 'GET'
    });
    return response || [];
  } catch (error) {
    console.error('Error fetching epics:', error);
    return [];
  }
};

/**
 * Get all Jira data (tickets and epics) for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Object>} Object containing tickets and epics
 */
export const getAllJiraData = async (projectId) => {
  try {
    const response = await apiRequest(`/api/jira/${projectId}/all`, {
      method: 'GET'
    });
    return response || { tickets: [], epics: [], total_tickets: 0, total_epics: 0 };
  } catch (error) {
    console.error('Error fetching all Jira data:', error);
    return { tickets: [], epics: [], total_tickets: 0, total_epics: 0 };
  }
};

/**
 * Get Jira metadata for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Object>} Metadata about Jira data
 */
export const getJiraMetadata = async (projectId, bustCache = false) => {
  try {
    const url = bustCache 
      ? `/api/jira/${projectId}/metadata?t=${Date.now()}`
      : `/api/jira/${projectId}/metadata`;
    
    const response = await apiRequest(url, {
      method: 'GET'
    });
    return response || { has_tickets: false, has_epics: false, total_tickets: 0, total_epics: 0 };
  } catch (error) {
    console.error('Error fetching Jira metadata:', error);
    return { has_tickets: false, has_epics: false, total_tickets: 0, total_epics: 0 };
  }
};

/**
 * Check if project has any Jira data
 * @param {string} projectId - The project identifier
 * @returns {Promise<boolean>} True if project has tickets or epics
 */
export const hasJiraData = async (projectId) => {
  try {
    const metadata = await getJiraMetadata(projectId);
    return metadata.has_tickets || metadata.has_epics;
  } catch (error) {
    console.error('Error checking Jira data:', error);
    return false;
  }
};