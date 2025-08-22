// Document title utility
import { getSiteName } from './contentLoader';

/**
 * Updates the document title with the site name
 * @param {string} pageTitle - Optional page-specific title
 */
export const updateDocumentTitle = (pageTitle = '') => {
  const siteName = getSiteName();
  
  if (pageTitle) {
    document.title = `${pageTitle} | ${siteName}`;
  } else {
    document.title = siteName;
  }
};

export default updateDocumentTitle;