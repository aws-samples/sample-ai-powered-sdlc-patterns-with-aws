// API Configuration
// This file manages API endpoints and settings

const API_CONFIG = {
    development: {
        baseUrl: '',
        endpoints: {
            api: '/api',
            myProjects: '/api/projects',
            projectDetails: '/project',
            chatbox: '/chatbox',
            sdlc: '/api/sdlc',
            createProject: '/api/projects/create',
            validateProjectName: '/api/projects/validate-name',
            projectTypes: '/api/projects/types',
            codeDownloadFiles: '/api/code-download/{projectId}/files',
            codeDownloadFile: '/api/code-download/{projectId}/file/{fileId}',
            codeDownloadZip: '/api/code-download/{projectId}/zip',
            codeDownloadSelectedZip: '/api/code-download/{projectId}/zip-selected',
            codeDownloadMetadata: '/api/code-download/{projectId}/metadata',
            authSignup: '/api/auth/signup',
            authLogin: '/api/auth/login',
            authRefresh: '/api/auth/refresh'
        },
        timeout: 300000, // 300 seconds (5 minutes) for long-running operations
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    },
    production: {
        // In production container, use relative URLs since frontend and backend are served from same domain
        baseUrl: process.env.REACT_APP_API_BASE_URL || '',
        endpoints: {
            api: '/api',
            myProjects: '/api/projects',
            projectDetails: '/project',
            chatbox: '/chatbox',
            sdlc: '/api/sdlc',
            createProject: '/api/projects/create',
            validateProjectName: '/api/projects/validate-name',
            projectTypes: '/api/projects/types',
            codeDownloadFiles: '/api/code-download/{projectId}/files',
            codeDownloadFile: '/api/code-download/{projectId}/file/{fileId}',
            codeDownloadZip: '/api/code-download/{projectId}/zip',
            codeDownloadSelectedZip: '/api/code-download/{projectId}/zip-selected',
            codeDownloadMetadata: '/api/code-download/{projectId}/metadata',
            authSignup: '/api/auth/signup',
            authConfirmSignup: '/api/auth/confirm-signup',
            authResendConfirmation: '/api/auth/resend-confirmation',
            authLogin: '/api/auth/login',
            authRefresh: '/api/auth/refresh'
        },
        timeout: 300000, // 300 seconds (5 minutes) for production long-running operations
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    }
};

// Get current environment
const getCurrentEnvironment = () => {
    if (process.env.NODE_ENV === 'production') {
        return 'production';
    }
    return 'development';
};

// Get configuration for current environment
export const getApiConfig = () => {
    const env = getCurrentEnvironment();
    return API_CONFIG[env];
};

// Get full URL for an endpoint
export const getApiUrl = (endpoint) => {
    const config = getApiConfig();
    return `${config.baseUrl}${config.endpoints[endpoint]}`;
};

// Get API headers for requests
export const getApiHeaders = () => {
    const config = getApiConfig();
    return config.headers;
};

// Get API timeout
export const getApiTimeout = () => {
    const config = getApiConfig();
    return config.timeout;
};

// Export default configuration
export default API_CONFIG;