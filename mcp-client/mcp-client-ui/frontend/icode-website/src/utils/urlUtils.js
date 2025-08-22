/**
 * URL utility functions for handling project name conversions
 */

/**
 * Converts a project name to a URL-safe format
 * @param {string} projectName - The original project name
 * @returns {string} URL-safe project name
 */
export const projectNameToUrl = (projectName) => {
  try {
    if (!projectName || typeof projectName !== 'string') {
      return '';
    }
    
    return projectName
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '-') // Replace spaces with hyphens
      .replace(/[^a-z0-9-]/g, '') // Remove special characters except hyphens
      .replace(/-+/g, '-') // Replace multiple hyphens with single hyphen
      .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
  } catch (error) {
    console.error('Error converting project name to URL:', error);
    return '';
  }
};

/**
 * Converts a URL-safe project name back to display format
 * @param {string} urlProjectName - The URL-safe project name
 * @returns {string} Display format project name
 */
export const urlToProjectName = (urlProjectName) => {
  if (!urlProjectName || typeof urlProjectName !== 'string') {
    return '';
  }
  
  return urlProjectName
    .replace(/-/g, ' ') // Replace hyphens with spaces
    .replace(/\b\w/g, (char) => char.toUpperCase()); // Capitalize first letter of each word
};

/**
 * Validates if a URL project name is valid
 * @param {string} urlProjectName - The URL project name to validate
 * @returns {boolean} True if valid, false otherwise
 */
export const isValidUrlProjectName = (urlProjectName) => {
  if (!urlProjectName || typeof urlProjectName !== 'string') {
    return false;
  }
  
  // Check if it matches the expected URL-safe format
  const urlSafePattern = /^[a-z0-9]+(-[a-z0-9]+)*$/;
  return urlSafePattern.test(urlProjectName) && urlProjectName.length > 0;
};