// Theme Context Provider
// Manages application theme and styling

import { ThemeContextValue } from '@/types/components';
import React, { createContext, ReactNode, useContext, useEffect, useState } from 'react';

interface ThemeProviderProps {
  children: ReactNode;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('ai-assistant-theme') as 'light' | 'dark';
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Default to dark theme for modern look
      setTheme('dark');
    }
  }, []);

  // Update document class and localStorage when theme changes
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('ai-assistant-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const colors = {
    primary: theme === 'dark' ? '#8b5cf6' : '#7c3aed',
    secondary: theme === 'dark' ? '#ec4899' : '#db2777',
    background: theme === 'dark' ? '#0f172a' : '#ffffff',
    surface: theme === 'dark' ? '#1e293b' : '#f8fafc',
    text: theme === 'dark' ? '#f1f5f9' : '#0f172a',
    textSecondary: theme === 'dark' ? '#94a3b8' : '#64748b',
    border: theme === 'dark' ? '#334155' : '#e2e8f0',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6'
  };

  const spacing = {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem'
  };

  const breakpoints = {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px'
  };

  const contextValue: ThemeContextValue = {
    theme,
    toggleTheme,
    colors,
    spacing,
    breakpoints
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};