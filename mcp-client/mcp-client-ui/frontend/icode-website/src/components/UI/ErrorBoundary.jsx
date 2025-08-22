import React from 'react';
import { Alert, Box } from '@cloudscape-design/components';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Box padding="l">
          <Alert
            type="error"
            header="Something went wrong"
            action={{
              text: 'Reload page',
              onClick: () => window.location.reload()
            }}
          >
            We're sorry, but something unexpected happened. Please try reloading the page.
          </Alert>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;