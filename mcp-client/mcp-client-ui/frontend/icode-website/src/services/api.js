// Core API Service
// This service handles HTTP communication with the backend API

import { getApiConfig, getApiUrl, getApiHeaders, getApiTimeout } from '../config/apiConfig';
import authService from './authService';

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(message, status, response) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.response = response;
  }
}

/**
 * Generic API request function with error handling, timeout, and automatic token refresh
 * @param {string} url - The API endpoint URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @param {boolean} requireAuth - Whether authentication is required for this request
 * @param {boolean} isRetry - Whether this is a retry attempt after token refresh
 * @returns {Promise<Object>} - The API response data
 */
export const apiRequest = async (url, options = {}, requireAuth = true, isRetry = false) => {
  const timeout = getApiTimeout();
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    // Ensure URL has the base URL if it's a relative path
    const config = getApiConfig();
    const fullUrl = url.startsWith('http') ? url : `${config.baseUrl}${url}`;
    
    // Start with default headers
    const headers = {
      ...getApiHeaders(),
      ...options.headers
    };
    
    // Add authentication headers if required and available
    if (requireAuth) {
      try {
        // Add access token for general authentication
        const authHeader = await authService.getAuthHeader();
        if (authHeader) {
          headers.Authorization = authHeader;
        }
        
        // Add ID token for Amazon Q Business authentication
        const idToken = await authService.getIdToken();
        if (idToken) {
          headers['x-id-token'] = idToken;
        }
      } catch (error) {
        console.warn('Failed to get auth headers:', error);
        // Continue without auth headers - let the server handle the 401
      }
    }
    
    // Make the API request
    const response = await fetch(fullUrl, {
      ...options,
      headers,
      signal: controller.signal
    });
    
    // Clear timeout
    clearTimeout(timeoutId);
    
    // Parse response
    let data;
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }
    
    // Handle HTTP errors
    if (!response.ok) {
      const errorMessage = data?.message || data?.error || `HTTP ${response.status}: ${response.statusText}`;
      
      // Handle authentication errors specifically
      if (response.status === 401 && requireAuth && !isRetry) {
        console.warn('Authentication failed - attempting token refresh');
        
        try {
          // Try to refresh the token
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            console.log('Attempting to refresh expired token...');
            
            const refreshResponse = await fetch(`${getApiConfig().baseUrl}/api/auth/refresh`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                refresh_token: refreshToken
              })
            });
            
            if (refreshResponse.ok) {
              const refreshData = await refreshResponse.json();
              
              // Update stored tokens
              localStorage.setItem('access_token', refreshData.access_token);
              if (refreshData.refresh_token) {
                localStorage.setItem('refresh_token', refreshData.refresh_token);
              }
              
              console.log('Token refreshed successfully, retrying original request...');
              
              // Retry the original request with the new token
              return await apiRequest(url, options, requireAuth, true);
            } else {
              console.error('Token refresh failed:', refreshResponse.status);
              // Token refresh failed, sign out the user
              await authService.signOut();
              throw new ApiError('Session expired. Please sign in again.', 401, data);
            }
          } else {
            console.warn('No refresh token available');
            // No refresh token, sign out the user
            await authService.signOut();
            throw new ApiError('Session expired. Please sign in again.', 401, data);
          }
        } catch (refreshError) {
          console.error('Error during token refresh:', refreshError);
          // Token refresh failed, sign out the user
          await authService.signOut();
          throw new ApiError('Session expired. Please sign in again.', 401, data);
        }
      }
      
      throw new ApiError(errorMessage, response.status, data);
    }
    
    return data;
    
  } catch (error) {
    clearTimeout(timeoutId);
    
    // Handle different types of errors
    if (error.name === 'AbortError') {
      throw new ApiError('Request timeout', 408, null);
    }
    
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Network or other errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new ApiError('Network error - unable to connect to server', 0, null);
    }
    
    throw new ApiError(error.message || 'Unknown error occurred', 0, null);
  }
};



/**
 * GET request
 * @param {string} endpoint - API endpoint name from config
 * @param {Object} options - Additional fetch options
 * @param {boolean} requireAuth - Whether authentication is required
 * @returns {Promise<Object>} - The API response data
 */
export const get = async (endpoint, options = {}, requireAuth = true) => {
  const url = getApiUrl(endpoint);
  
  return apiRequest(url, {
    method: 'GET',
    ...options
  }, requireAuth);
};

/**
 * POST request
 * @param {string} endpoint - API endpoint name from config
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @param {boolean} requireAuth - Whether authentication is required
 * @returns {Promise<Object>} - The API response data
 */
export const post = async (endpoint, data = {}, options = {}, requireAuth = true) => {
  const url = getApiUrl(endpoint);
  
  return apiRequest(url, {
    method: 'POST',
    body: JSON.stringify(data),
    ...options
  }, requireAuth);
};

/**
 * PUT request
 * @param {string} endpoint - API endpoint name from config
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @param {boolean} requireAuth - Whether authentication is required
 * @returns {Promise<Object>} - The API response data
 */
export const put = async (endpoint, data = {}, options = {}, requireAuth = true) => {
  const url = getApiUrl(endpoint);
  
  return apiRequest(url, {
    method: 'PUT',
    body: JSON.stringify(data),
    ...options
  }, requireAuth);
};

/**
 * DELETE request
 * @param {string} endpoint - API endpoint name from config
 * @param {Object} options - Additional fetch options
 * @param {boolean} requireAuth - Whether authentication is required
 * @returns {Promise<Object>} - The API response data
 */
export const del = async (endpoint, options = {}, requireAuth = true) => {
  const url = getApiUrl(endpoint);
  
  return apiRequest(url, {
    method: 'DELETE',
    ...options
  }, requireAuth);
};

/**
 * Generic API call function for direct endpoint usage
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Fetch options
 * @param {boolean} requireAuth - Whether authentication is required
 * @returns {Promise<Object>} - The API response data
 */
export const makeApiCall = async (endpoint, options = {}, requireAuth = true) => {
  const config = getApiConfig();
  const url = `${config.baseUrl}${endpoint}`;
  
  return apiRequest(url, options, requireAuth);
};

/**
 * Fetch binary data (like images) with authentication
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Fetch options
 * @param {boolean} requireAuth - Whether authentication is required
 * @returns {Promise<Blob>} - The binary response as a Blob
 */
export const fetchBinaryData = async (endpoint, options = {}, requireAuth = true) => {
  const timeout = getApiTimeout();
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const config = getApiConfig();
    const url = `${config.baseUrl}${endpoint}`;
    
    // Start with default headers
    const headers = {
      ...getApiHeaders(),
      ...options.headers
    };
    
    // Remove Content-Type for binary requests
    delete headers['Content-Type'];
    
    // Add authentication headers if required and available
    if (requireAuth) {
      try {
        // Add access token for general authentication
        const authHeader = await authService.getAuthHeader();
        if (authHeader) {
          headers.Authorization = authHeader;
        }
        
        // Add ID token for Amazon Q Business authentication
        const idToken = await authService.getIdToken();
        if (idToken) {
          headers['x-id-token'] = idToken;
        }
      } catch (error) {
        console.warn('Failed to get auth headers:', error);
      }
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      // Try to get error message from response
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      
      throw new ApiError(errorMessage, response.status, null);
    }
    
    // Return the response as a blob
    return await response.blob();
    
  } catch (error) {
    clearTimeout(timeoutId);
    
    // Handle different types of errors
    if (error.name === 'AbortError') {
      throw new ApiError('Request timeout', 408, null);
    }
    
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Network or other errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new ApiError('Network error - unable to connect to server', 0, null);
    }
    
    throw new ApiError(error.message || 'Unknown error occurred', 0, null);
  }
};



// Export all functions as default object
export default {
  get,
  post,
  put,
  del,
  makeApiCall,
  fetchBinaryData,
  ApiError
};