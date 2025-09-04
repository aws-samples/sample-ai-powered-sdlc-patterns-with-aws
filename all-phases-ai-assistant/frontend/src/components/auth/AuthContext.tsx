// Authentication Context Provider with AWS Amplify v6 integration
// Provides authentication state management and user session handling

import { fetchAuthSession, fetchUserAttributes, getCurrentUser, signIn, signOut } from 'aws-amplify/auth';
import React, { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { AuthenticationState, UserRole } from '../../types/api';
import { AuthContextValue } from '../../types/components';

interface AuthProviderProps {
  children: ReactNode;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthenticationState>({
    isAuthenticated: false,
    user: undefined,
    accessToken: undefined,
    idToken: undefined,
    refreshToken: undefined,
    expiresAt: undefined
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();

  // Initialize authentication state on mount
  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      setIsLoading(true);
      setError(undefined);

      const user = await getCurrentUser();
      const session = await fetchAuthSession();
      const userAttributes = await fetchUserAttributes();
      
      if (user && session.tokens) {
        setAuthState({
          isAuthenticated: true,
          user: {
            sub: userAttributes.sub || '',
            email: userAttributes.email || '',
            email_verified: userAttributes.email_verified === 'true',
            'custom:role': (userAttributes['custom:role'] as UserRole) || 'user',
            'custom:department': userAttributes['custom:department'],
            'cognito:username': user.username
          },
          accessToken: session.tokens.accessToken?.toString(),
          idToken: session.tokens.idToken?.toString(),
          refreshToken: 'refresh-token-available',
          expiresAt: session.tokens.accessToken?.payload.exp ? session.tokens.accessToken.payload.exp * 1000 : undefined
        });
      } else {
        setAuthState({
          isAuthenticated: false,
          user: undefined,
          accessToken: undefined,
          idToken: undefined,
          refreshToken: undefined,
          expiresAt: undefined
        });
      }
    } catch (error) {
      console.log('User not authenticated:', error);
      setAuthState({
        isAuthenticated: false,
        user: undefined,
        accessToken: undefined,
        idToken: undefined,
        refreshToken: undefined,
        expiresAt: undefined
      });
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string): Promise<void> => {
    try {
      setIsLoading(true);
      setError(undefined);

      const result = await signIn({
        username: email,
        password: password
      });
      
      if (result.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        throw new Error('New password required. Please contact your administrator.');
      }

      if (result.isSignedIn) {
        await checkAuthState();
      }
    } catch (error: any) {
      console.error('Login error:', error);
      
      let errorMessage = 'Login failed. Please try again.';
      
      if (error.name === 'UserNotConfirmedException') {
        errorMessage = 'Please verify your email address before signing in.';
      } else if (error.name === 'NotAuthorizedException') {
        errorMessage = 'Invalid email or password.';
      } else if (error.name === 'UserNotFoundException') {
        errorMessage = 'User not found. Please check your email address.';
      } else if (error.name === 'TooManyRequestsException') {
        errorMessage = 'Too many failed attempts. Please try again later.';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(undefined);

      await signOut();
      
      setAuthState({
        isAuthenticated: false,
        user: undefined,
        accessToken: undefined,
        idToken: undefined,
        refreshToken: undefined,
        expiresAt: undefined
      });
    } catch (error: any) {
      console.error('Logout error:', error);
      setError('Logout failed. Please try again.');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const refreshToken = async (): Promise<void> => {
    try {
      const session = await fetchAuthSession({ forceRefresh: true });
      
      if (session.tokens) {
        await checkAuthState();
      } else {
        // Session expired, force logout
        await logout();
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      await logout();
    }
  };

  // Auto-refresh token before expiration
  useEffect(() => {
    if (authState.isAuthenticated && authState.expiresAt) {
      const timeUntilExpiry = authState.expiresAt - Date.now();
      const refreshThreshold = 5 * 60 * 1000; // 5 minutes before expiry
      
      if (timeUntilExpiry > refreshThreshold) {
        const refreshTimer = setTimeout(() => {
          refreshToken();
        }, timeUntilExpiry - refreshThreshold);
        
        return () => clearTimeout(refreshTimer);
      } else if (timeUntilExpiry <= 0) {
        // Token already expired
        logout();
      }
    }
    return undefined;
  }, [authState.expiresAt, authState.isAuthenticated]);

  const contextValue: AuthContextValue = {
    authState,
    login,
    logout,
    refreshToken,
    isLoading,
    error
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};