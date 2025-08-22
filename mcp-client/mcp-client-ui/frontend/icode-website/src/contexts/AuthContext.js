import React, { createContext, useContext, useReducer, useEffect } from 'react';
import authService from '../services/authService';

// Auth state reducer
const authReducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_AUTHENTICATED':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        userProfile: action.payload.profile,
        loading: false,
        error: null
      };
    case 'SET_UNAUTHENTICATED':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        userProfile: null,
        loading: false,
        error: null
      };
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        loading: false
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null
      };
    default:
      return state;
  }
};

// Initial state
const initialState = {
  isAuthenticated: false,
  user: null,
  userProfile: null,
  loading: true,
  error: null
};

// Create context
const AuthContext = createContext();

// Auth provider component
export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize authentication state
  useEffect(() => {
    const initAuth = async () => {
      dispatch({ type: 'SET_LOADING', payload: true });

      try {
        const isAuth = await authService.isAuthenticated();

        if (isAuth) {
          const user = await authService.getCurrentUser();
          const profile = await authService.getUserProfile();

          dispatch({
            type: 'SET_AUTHENTICATED',
            payload: { user, profile }
          });
        } else {
          dispatch({ type: 'SET_UNAUTHENTICATED' });
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        dispatch({ type: 'SET_ERROR', payload: error.message });
        dispatch({ type: 'SET_UNAUTHENTICATED' });
      }
    };

    initAuth();

    // Listen for auth state changes
    const unsubscribe = authService.addAuthListener(async (authState) => {
      if (authState.isAuthenticated) {
        const profile = await authService.getUserProfile();
        dispatch({
          type: 'SET_AUTHENTICATED',
          payload: { user: authState.user, profile }
        });
      } else {
        dispatch({ type: 'SET_UNAUTHENTICATED' });
      }
    });

    return () => {
      unsubscribe();
      authService.cleanup();
    };
  }, []);

  // Sign in function
  const signIn = async (username, password) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'CLEAR_ERROR' });

    try {
      const result = await authService.signIn(username, password);

      if (result.success) {
        const profile = await authService.getUserProfile();
        dispatch({
          type: 'SET_AUTHENTICATED',
          payload: { user: result.user, profile }
        });
        return { success: true };
      } else {
        dispatch({ type: 'SET_ERROR', payload: result.error });
        dispatch({ type: 'SET_UNAUTHENTICATED' });
        return { success: false, error: result.error, code: result.code };
      }
    } catch (error) {
      const errorMessage = error.message || 'Sign in failed';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      dispatch({ type: 'SET_UNAUTHENTICATED' });
      return { success: false, error: errorMessage };
    }
  };




  // Sign out function - comprehensive cleanup
  const signOut = async () => {
    console.log('AuthContext: Starting comprehensive sign out...');
    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      // Call the auth service sign out
      console.log('AuthContext: Calling authService.signOut()...');
      const result = await authService.signOut();
      console.log('AuthContext: Auth service sign out result:', result);

      // Update context state immediately
      dispatch({ type: 'SET_UNAUTHENTICATED' });
      console.log('AuthContext: Dispatched SET_UNAUTHENTICATED');

      // Additional cleanup - clear any remaining browser storage
      console.log('AuthContext: Performing additional cleanup...');

      // Clear any remaining localStorage items that might have been missed
      Object.keys(localStorage).forEach(key => {
        if (key.toLowerCase().includes('auth') ||
          key.toLowerCase().includes('token') ||
          key.toLowerCase().includes('cognito') ||
          key.toLowerCase().includes('amplify')) {
          localStorage.removeItem(key);
          // Removed localStorage key
        }
      });

      // Clear any remaining sessionStorage items
      Object.keys(sessionStorage).forEach(key => {
        if (key.toLowerCase().includes('auth') ||
          key.toLowerCase().includes('token') ||
          key.toLowerCase().includes('cognito') ||
          key.toLowerCase().includes('amplify')) {
          sessionStorage.removeItem(key);
          // Removed sessionStorage key
        }
      });

      console.log('AuthContext: Sign out cleanup completed');
      return result;

    } catch (error) {
      console.error('AuthContext: Sign out error:', error);

      // Even on error, clear the auth state
      dispatch({ type: 'SET_UNAUTHENTICATED' });
      dispatch({ type: 'SET_ERROR', payload: error.message });
      dispatch({ type: 'SET_LOADING', payload: false });

      return { success: false, error: error.message };
    }
  };

  // Clear error function
  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  // Get auth header for API requests
  const getAuthHeader = async () => {
    return await authService.getAuthHeader();
  };

  // Check if user has specific group
  const hasGroup = async (groupName) => {
    return await authService.hasGroup(groupName);
  };

  // Handle token expiration (called by API service)
  const handleTokenExpiration = async () => {
    console.log('AuthContext: Handling token expiration');
    dispatch({ type: 'SET_ERROR', payload: 'Your session has expired. Please sign in again.' });
    dispatch({ type: 'SET_UNAUTHENTICATED' });
  };

  // Context value
  const value = {
    // State
    isAuthenticated: state.isAuthenticated,
    user: state.user,
    userProfile: state.userProfile,
    loading: state.loading,
    error: state.error,

    // Actions
    signIn,
    signOut,
    clearError,
    getAuthHeader,
    hasGroup,
    handleTokenExpiration
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;