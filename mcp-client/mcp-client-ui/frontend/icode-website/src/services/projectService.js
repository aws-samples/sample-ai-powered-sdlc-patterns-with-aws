// Project Service
// This service handles project-specific API operations

import { post, get, put, del, makeApiCall, ApiError } from './api';

/**
 * Validate project data before sending to API
 * @param {Object} projectData - The project data to validate
 * @returns {Object} - Validation result with isValid and errors
 */
export const validateProjectData = (projectData) => {
    const errors = [];

    // Required fields validation
    if (!projectData.name || !projectData.name.trim()) {
        errors.push('Project name is required');
    }

    if (!projectData.project_type) {
        errors.push('Project type is required');
    }

    if (!projectData.description || !projectData.description.trim()) {
        errors.push('Project description is required');
    }

    // Optional field validation
    if (projectData.description && projectData.description.length > 500) {
        errors.push('Project description must be less than 500 characters');
    }

    // Name length validation
    if (projectData.name && projectData.name.length > 100) {
        errors.push('Project name must be less than 100 characters');
    }

    return {
        isValid: errors.length === 0,
        errors
    };
};

/**
 * Format project data for API submission
 * @param {Object} projectData - Raw project data from form
 * @returns {Object} - Formatted project data
 */
export const formatProjectData = (projectData) => {
    return {
        name: projectData.name.trim(),
        type: projectData.type,
        description: projectData.description ? projectData.description.trim() : '',
        userRole: projectData.userRole,
        createdAt: new Date().toISOString(),
        status: 'active'
    };
};

/**
 * Fetch user's projects
 * @returns {Promise<Array>} - Array of user projects
 */
export const fetchMyProjects = async () => {
    try {
        console.log('Fetching user projects from API...');

        // Send GET request to my_projects endpoint
        const response = await get('myProjects');

        console.log('Projects fetched successfully:', response);

        // Ensure we return an array
        if (Array.isArray(response)) {
            return response;
        } else if (response && Array.isArray(response.data)) {
            return response.data;
        } else if (response && Array.isArray(response.projects)) {
            return response.projects;
        } else {
            // If response is not in expected format, return empty array
            console.warn('Unexpected API response format for projects:', response);
            return [];
        }

    } catch (error) {
        console.error('Error fetching projects:', error);

        // Handle different types of errors
        if (error instanceof ApiError) {
            // For 404 or empty results, return empty array instead of throwing
            if (error.status === 404) {
                console.log('No projects found (404), returning empty array');
                return [];
            }

            // For authentication errors, provide a more helpful message
            if (error.status === 401) {
                throw new Error('Authentication required. Please sign in to view your projects.');
            }

            // For other API errors, throw with user-friendly message
            throw new Error(getErrorMessage(error));
        }

        // For network or other errors, throw with generic message
        throw new Error('Unable to load projects. Please try again later.');
    }
};

/**
 * Fetch project details by project name
 * @param {string} projectName - URL-safe project name
 * @returns {Promise<Object>} - Project details
 */
export const fetchProjectDetails = async (projectName) => {
    try {
        console.log('Fetching project details for:', projectName);

        // For now, we'll simulate the API call with mock data
        // In a real implementation, this would make an actual API call
        const mockProjectData = {
            id: projectName,
            name: projectName.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            type: 'Web Application',
            description: 'This is a sample project description. In a real implementation, this data would come from your backend API.',
            userRole: 'Developer',
            createdAt: '2024-01-15T10:30:00Z',
            updatedAt: '2024-01-20T14:45:00Z',
            status: 'Active',
            technologies: ['React', 'Node.js', 'PostgreSQL'],
            repository: 'https://github.com/example/project',
            deploymentUrl: 'https://myproject.example.com'
        };

        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const data = mockProjectData;

        console.log('Project details fetched successfully:', data);

        // Return the project data
        if (data && typeof data === 'object') {
            return data;
        } else {
            throw new Error('Invalid project data received from server');
        }

    } catch (error) {
        console.error('Error fetching project details:', error);

        // Handle different types of errors
        if (error instanceof ApiError) {
            if (error.status === 404) {
                throw new Error('Project not found');
            }
            throw new Error(getErrorMessage(error));
        }

        // For network or other errors, throw with generic message
        throw new Error('Unable to load project details. Please try again later.');
    }
};

/**
 * Create a new project
 * @param {Object} projectData - Project creation data
 * @returns {Promise<Object>} - Created project response
 */
export const createProject = async (projectData) => {
    try {
        console.log('Creating new project:', projectData);

        // Validate project data
        const validation = validateProjectData(projectData);
        if (!validation.isValid) {
            throw new Error(validation.errors.join(', '));
        }

        // Format data for API
        const formattedData = {
            name: projectData.name.trim(),
            description: projectData.description ? projectData.description.trim() : '',
            project_type: projectData.project_type || 'web',
            assigned_groups: projectData.assigned_groups || ['Developers'],
            assigned_users: projectData.assigned_users || [],
            status: 'active'
        };

        // Send POST request to create project
        const response = await post('createProject', formattedData);

        console.log('Project created successfully:', response);
        return response;

    } catch (error) {
        console.error('Error creating project:', error);

        // Handle different types of errors
        if (error instanceof ApiError) {
            throw new Error(getErrorMessage(error));
        }

        // For validation or other errors, throw the original message
        throw error;
    }
};

/**
 * Validate project name availability
 * @param {string} projectName - Project name to validate
 * @returns {Promise<Object>} - Validation result
 */
export const validateProjectName = async (projectName) => {
    try {
        if (!projectName || !projectName.trim()) {
            return {
                available: false,
                message: 'Project name is required'
            };
        }

        console.log('Validating project name:', projectName);

        // Use makeApiCall for dynamic endpoint with parameter
        const response = await makeApiCall(`/api/projects/validate-name/${encodeURIComponent(projectName.trim())}`, {
            method: 'GET'
        }, true); // Require authentication

        console.log('Name validation result:', response);
        return response;

    } catch (error) {
        console.error('Error validating project name:', error);
        
        // Provide more detailed error information
        if (error instanceof ApiError) {
            return {
                available: false,
                message: `API Error (${error.status}): ${error.message}`
            };
        }
        
        return {
            available: false,
            message: `Error: ${error.message}`
        };
    }
};

/**
 * Get available project types
 * @returns {Promise<Array>} - Array of project types
 */
export const getProjectTypes = async () => {
    try {
        console.log('Fetching project types...');

        const response = await makeApiCall('/api/projects/types', {
            method: 'GET'
        }, true);

        console.log('Project types fetched:', response);
        return response.project_types || [];

    } catch (error) {
        console.error('Error fetching project types:', error);
        // Return default types if API fails
        return [
            { value: 'web', label: 'Web Application' },
            { value: 'mobile', label: 'Mobile Application' },
            { value: 'api', label: 'API/Backend Service' },
            { value: 'desktop', label: 'Desktop Application' },
            { value: 'data', label: 'Data Processing' },
            { value: 'ml', label: 'Machine Learning' },
            { value: 'other', label: 'Other' }
        ];
    }
};



/**
 * Get user-friendly error message based on API error
 * @param {ApiError} error - API error object
 * @returns {string} - User-friendly error message
 */
const getErrorMessage = (error) => {
    switch (error.status) {
        case 400:
            return 'Invalid project data. Please check your input and try again.';
        case 401:
            return 'Authentication required. Please log in and try again.';
        case 403:
            return 'You do not have permission to perform this action.';
        case 404:
            return 'Project not found.';
        case 409:
            return 'A project with this name already exists.';
        case 429:
            return 'Too many requests. Please wait a moment and try again.';
        case 500:
            return 'Server error. Please try again later.';
        case 0:
            return 'Unable to connect to server. Please check your internet connection.';
        case 408:
            return 'Request timeout. Please try again.';
        default:
            return 'An unexpected error occurred. Please try again.';
    }
};

// Export all functions
export default {
    fetchMyProjects,
    fetchProjectDetails,
    createProject,
    validateProjectName,
    getProjectTypes,
    validateProjectData,
    formatProjectData
};