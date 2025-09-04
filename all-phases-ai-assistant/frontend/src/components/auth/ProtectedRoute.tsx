// Protected Route Component
// Wraps routes that require specific roles or authentication

import { ProtectedRouteProps } from '@/types/components';
import { ROUTES } from '@/types/routes';
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  redirectTo = ROUTES.UNAUTHORIZED
}) => {
  const { authState, isLoading } = useAuth();
  const location = useLocation();

  // Don't render anything while loading
  if (isLoading) {
    return null;
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

  // Check role requirement
  if (requiredRole && authState.user?.['custom:role'] !== requiredRole) {
    return (
      <Navigate 
        to={redirectTo} 
        state={{ from: location.pathname }} 
        replace 
      />
    );
  }

  return <>{children}</>;
};