import { getApiConfig } from '../config/apiConfig';
import { makeApiCall } from './api';

/**
 * Fetch existing diagrams for a project
 * @param {string} projectId - The project identifier
 * @returns {Promise<Object>} The diagrams response
 */
export const fetchProjectDiagrams = async (projectId) => {
  console.log('🎨 DiagramService: fetchProjectDiagrams called with projectId:', projectId);
  
  if (!projectId || typeof projectId !== 'string') {
    throw new Error('Project ID is required and must be a string');
  }

  try {
    const config = getApiConfig();
    const endpoint = `${config.endpoints.api}/diagrams/${projectId}/specification`;
    
    console.log('🎨 DiagramService: Making API call to:', endpoint);
    
    const response = await makeApiCall(endpoint, {
      method: 'GET'
    });

    console.log('🎨 DiagramService: API response:', response);

    return {
      success: response.success || false,
      diagrams: response.diagrams || [],
      totalDiagrams: response.total_diagrams || 0,
      projectId: response.project_id || projectId,
      message: response.message || 'Diagrams retrieved'
    };
  } catch (error) {
    console.error('🎨 DiagramService: Error fetching diagrams:', error);
    return {
      success: false,
      diagrams: [],
      totalDiagrams: 0,
      projectId: projectId,
      message: 'Failed to fetch diagrams',
      error: error.message
    };
  }
};

/**
 * List all diagrams for a project (raw format)
 * @param {string} projectId - The project identifier
 * @returns {Promise<Object>} The diagrams list response
 */
export const listProjectDiagrams = async (projectId) => {
  if (!projectId || typeof projectId !== 'string') {
    throw new Error('Project ID is required and must be a string');
  }

  try {
    const config = getApiConfig();
    const endpoint = `${config.endpoints.api}/diagrams/${projectId}/list`;
    
    const response = await makeApiCall(endpoint, {
      method: 'GET'
    });

    return {
      success: response.success || false,
      diagrams: response.diagrams || [],
      totalDiagrams: response.total_diagrams || 0,
      projectId: response.project_id || projectId,
      message: response.message || 'Diagrams listed'
    };
  } catch (error) {
    console.error('Diagram list service error:', error);
    return {
      success: false,
      diagrams: [],
      totalDiagrams: 0,
      projectId: projectId,
      message: 'Failed to list diagrams',
      error: error.message
    };
  }
};

/**
 * Delete a diagram from the project
 * @param {string} projectId - The project identifier
 * @param {string} diagramName - The diagram name
 * @param {string} format - The diagram format (default: png)
 * @returns {Promise<Object>} The deletion response
 */
export const deleteDiagram = async (projectId, diagramName, format = 'png') => {
  if (!projectId || typeof projectId !== 'string') {
    throw new Error('Project ID is required and must be a string');
  }
  
  if (!diagramName || typeof diagramName !== 'string') {
    throw new Error('Diagram name is required and must be a string');
  }

  try {
    const config = getApiConfig();
    const endpoint = `${config.endpoints.api}/diagrams/${projectId}/delete/${diagramName}?format=${format}`;
    
    const response = await makeApiCall(endpoint, {
      method: 'DELETE'
    });

    return {
      success: response.success || false,
      projectId: response.project_id || projectId,
      diagramName: response.diagram_name || diagramName,
      message: response.message || 'Diagram deleted'
    };
  } catch (error) {
    console.error('Diagram delete service error:', error);
    return {
      success: false,
      projectId: projectId,
      diagramName: diagramName,
      message: 'Failed to delete diagram',
      error: error.message
    };
  }
};