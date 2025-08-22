// Content Loader Utility
// This file provides functions to load and access site content from the central content file

import siteContent from '../config/siteContent.json';

/**
 * Get the entire site content configuration
 * @returns {Object} The complete site content object
 */
export const getSiteContent = () => {
  return siteContent;
};

/**
 * Get site name
 * @returns {string} The site name
 */
export const getSiteName = () => {
  return siteContent.siteName;
};

/**
 * Get site tagline
 * @returns {string} The site tagline
 */
export const getSiteTagline = () => {
  return siteContent.siteTagline;
};

/**
 * Get navigation items
 * @returns {Array} Navigation items
 */
export const getNavigationItems = () => {
  return siteContent.navigation.items;
};

/**
 * Get footer links
 * @returns {Array} Footer links
 */
export const getFooterLinks = () => {
  return siteContent.footer.links;
};

/**
 * Get home page content
 * @returns {Object} Home page content
 */
export const getHomePageContent = () => {
  return siteContent.homePage;
};

/**
 * Get "How It Works" content
 * @returns {Object} How It Works content
 */
export const getHowItWorksContent = () => {
  return siteContent.howItWorks;
};

/**
 * Get About page content
 * @returns {Object} About page content
 */
export const getAboutPageContent = () => {
  return siteContent.aboutPage;
};

/**
 * Get content by path
 * @param {string} path - Dot notation path to the content (e.g., 'homePage.hero.title')
 * @returns {any} The content at the specified path or undefined if not found
 */
export const getContentByPath = (path) => {
  return path.split('.').reduce((obj, key) => {
    return obj && obj[key] !== undefined ? obj[key] : undefined;
  }, siteContent);
};

export default {
  getSiteContent,
  getSiteName,
  getSiteTagline,
  getNavigationItems,
  getFooterLinks,
  getHomePageContent,
  getHowItWorksContent,
  getAboutPageContent,
  getContentByPath
};