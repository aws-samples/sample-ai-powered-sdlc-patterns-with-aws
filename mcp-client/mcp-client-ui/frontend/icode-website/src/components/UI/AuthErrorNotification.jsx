import React, { useEffect, useState } from 'react';
import { Alert, Box } from '@cloudscape-design/components';
import { useAuth } from '../../contexts/AuthContext';

const AuthErrorNotification = () => {
  const { error, clearError, isAuthenticated } = useAuth();
  const [showError, setShowError] = useState(false);

  useEffect(() => {
    // Show error notification when there's an auth error and user is not authenticated
    if (error && !isAuthenticated) {
      setShowError(true);
      
      // Auto-hide after 10 seconds
      const timer = setTimeout(() => {
        setShowError(false);
        clearError();
      }, 10000);

      return () => clearTimeout(timer);
    } else {
      setShowError(false);
    }
  }, [error, isAuthenticated, clearError]);

  if (!showError || !error) {
    return null;
  }

  return (
    <Box position="fixed" top="20px" right="20px" zIndex={1000} maxWidth="400px">
      <Alert
        type="error"
        dismissible
        onDismiss={() => {
          setShowError(false);
          clearError();
        }}
        header="Authentication Error"
      >
        {error}
      </Alert>
    </Box>
  );
};

export default AuthErrorNotification;