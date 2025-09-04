// Authentication Guard Component
// Protects routes and redirects unauthenticated users to login

import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { AuthGuardProps } from '../../types/components';
import { ROUTES } from '../../types/routes';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const AuthGuard: React.FC<AuthGuardProps> = ({ 
  children, 
  requiredRole
}) => {
  const { authState, isLoading, refreshToken } = useAuth();
  const location = useLocation();

  // Check for token refresh on mount
  useEffect(() => {
    if (authState.isAuthenticated && authState.expiresAt) {
      const timeUntilExpiry = authState.expiresAt - Date.now();
      if (timeUntilExpiry <= 5 * 60 * 1000 && timeUntilExpiry > 0) {
        // Token expires in less than 5 minutes, refresh it
        refreshToken();
      }
    }
  }, [authState.isAuthenticated, authState.expiresAt, refreshToken]);

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-white/70 text-lg">Authenticating...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!authState.isAuthenticated) {
    return (
      <Navigate 
        to={ROUTES.LOGIN} 
        state={{ from: location.pathname }} 
        replace 
      />
    );
  }

  // Check role-based access
  if (requiredRole && authState.user?.['custom:role'] !== requiredRole) {
    return (
      <Navigate 
        to={ROUTES.UNAUTHORIZED} 
        state={{ from: location.pathname }} 
        replace 
      />
    );
  }

  // Render children if authenticated and authorized
  return <>{children}</>;
};