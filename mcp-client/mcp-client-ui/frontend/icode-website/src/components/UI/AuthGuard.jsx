import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LoginForm } from './LoginForm';
import { SignUpForm } from './SignUpForm';
import LoadingSpinner from './LoadingSpinner';

export const AuthGuard = ({ 
  children, 
  requiredGroups = [], 
  fallbackComponent = null,
  showAuthModal = true 
}) => {
  const { isAuthenticated, userProfile, loading } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('signin'); // 'signin' or 'signup'

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="auth-guard__loading">
        <LoadingSpinner size="large" text="Checking authentication..." />
      </div>
    );
  }

  // If not authenticated, show authentication forms or fallback
  if (!isAuthenticated) {
    if (fallbackComponent) {
      return fallbackComponent;
    }

    if (!showAuthModal) {
      return (
        <div className="auth-guard__prompt">
          <div className="auth-prompt">
            <h2>Authentication Required</h2>
            <p>Please sign in to access this content.</p>
            <button
              className="btn btn--primary"
              onClick={() => setShowAuth(true)}
            >
              Sign In
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="auth-guard__modal">
        <div className="auth-modal">
          <div className="auth-modal__content">
            {authMode === 'signin' ? (
              <LoginForm
                onSuccess={() => setShowAuth(false)}
                onSwitchToSignUp={() => setAuthMode('signup')}
              />
            ) : (
              <SignUpForm
                onSuccess={() => setShowAuth(false)}
                onSwitchToSignIn={() => setAuthMode('signin')}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  // Check group requirements
  if (requiredGroups.length > 0) {
    const hasRequiredGroup = requiredGroups.some(group => 
      userProfile?.groups?.includes(group)
    );

    if (!hasRequiredGroup) {
      return (
        <div className="auth-guard__access-denied">
          <div className="access-denied">
            <div className="access-denied__icon">🔒</div>
            <h2>Access Denied</h2>
            <p>
              You don't have permission to access this content. 
              Required groups: {requiredGroups.join(', ')}
            </p>
            <p>
              Your current groups: {userProfile?.groups?.join(', ') || 'None'}
            </p>
            <p>Please contact your administrator for access.</p>
          </div>
        </div>
      );
    }
  }

  // User is authenticated and has required permissions
  return children;
};

// Higher-order component for protecting routes
export const withAuthGuard = (Component, options = {}) => {
  return function AuthGuardedComponent(props) {
    return (
      <AuthGuard {...options}>
        <Component {...props} />
      </AuthGuard>
    );
  };
};

// Hook for checking specific permissions
export const useAuthGuard = () => {
  const { isAuthenticated, userProfile } = useAuth();

  const checkAccess = async (requiredGroups = []) => {
    if (!isAuthenticated) {
      return { hasAccess: false, reason: 'not_authenticated' };
    }

    if (requiredGroups.length === 0) {
      return { hasAccess: true };
    }

    const hasRequiredGroup = requiredGroups.some(group => 
      userProfile?.groups?.includes(group)
    );

    if (!hasRequiredGroup) {
      return { 
        hasAccess: false, 
        reason: 'insufficient_permissions',
        requiredGroups,
        userGroups: userProfile?.groups || []
      };
    }

    return { hasAccess: true };
  };

  const requireAuth = (callback, requiredGroups = []) => {
    return async (...args) => {
      const access = await checkAccess(requiredGroups);
      
      if (!access.hasAccess) {
        console.warn('Access denied:', access.reason);
        return null;
      }

      return callback(...args);
    };
  };

  return {
    checkAccess,
    requireAuth,
    isAuthenticated,
    userGroups: userProfile?.groups || []
  };
};

// Add styles
const styles = `
  .auth-guard__loading {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 200px;
    padding: 2rem;
  }

  .auth-guard__prompt {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
    padding: 2rem;
  }

  .auth-prompt {
    text-align: center;
    max-width: 400px;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .auth-prompt h2 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.5rem;
  }

  .auth-prompt p {
    margin: 0 0 2rem 0;
    color: #666;
    line-height: 1.5;
  }

  .auth-guard__modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    padding: 1rem;
  }

  .auth-modal {
    background: white;
    border-radius: 8px;
    max-width: 500px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }

  .auth-modal__content {
    padding: 0;
  }

  .auth-guard__access-denied {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
    padding: 2rem;
  }

  .access-denied {
    text-align: center;
    max-width: 500px;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .access-denied__icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .access-denied h2 {
    margin: 0 0 1rem 0;
    color: #dc3545;
    font-size: 1.5rem;
  }

  .access-denied p {
    margin: 0 0 1rem 0;
    color: #666;
    line-height: 1.5;
  }

  .access-denied p:last-child {
    margin-bottom: 0;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s, transform 0.1s;
  }

  .btn:hover {
    transform: translateY(-1px);
  }

  .btn--primary {
    background-color: #007bff;
    color: white;
  }

  .btn--primary:hover {
    background-color: #0056b3;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);
}