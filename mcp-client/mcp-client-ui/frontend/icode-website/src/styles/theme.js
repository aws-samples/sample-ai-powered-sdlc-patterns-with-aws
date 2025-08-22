// Cloudscape theme configuration
import { THEME_CONFIG } from '../utils/constants';

export const cloudscapeTheme = {
  mode: THEME_CONFIG.defaultMode,
  // Custom theme tokens for ICODE branding
  tokens: {
    // Brand colors that complement Cloudscape
    colorBrandPrimary: '#0073bb',
    colorBrandSecondary: '#232f3e',
    // Custom spacing tokens
    spaceXs: THEME_CONFIG.spacing.xs,
    spaceS: THEME_CONFIG.spacing.s,
    spaceM: THEME_CONFIG.spacing.m,
    spaceL: THEME_CONFIG.spacing.l,
    spaceXl: THEME_CONFIG.spacing.xl,
    spaceXxl: THEME_CONFIG.spacing.xxl,
  }
};

// Theme utility functions
export const applyTheme = (mode = 'light') => {
  // Validate theme mode
  if (!THEME_CONFIG.supportedModes.includes(mode)) {
    console.warn(`Unsupported theme mode: ${mode}. Falling back to ${THEME_CONFIG.defaultMode}`);
    mode = THEME_CONFIG.defaultMode;
  }
  
  // Apply theme mode to document
  document.documentElement.setAttribute('data-theme', mode);
  
  // Apply custom CSS properties for theme tokens
  const root = document.documentElement;
  Object.entries(cloudscapeTheme.tokens).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value);
  });
};

// Get current theme mode
export const getCurrentTheme = () => {
  return document.documentElement.getAttribute('data-theme') || THEME_CONFIG.defaultMode;
};

// Toggle theme mode
export const toggleTheme = () => {
  const currentMode = getCurrentTheme();
  const newMode = currentMode === 'light' ? 'dark' : 'light';
  applyTheme(newMode);
  return newMode;
};

// Initialize theme on app load
export const initializeTheme = () => {
  // Check for saved theme preference or default
  const savedTheme = localStorage.getItem('icode-theme') || cloudscapeTheme.mode;
  applyTheme(savedTheme);
  
  // Save theme preference
  localStorage.setItem('icode-theme', savedTheme);
};