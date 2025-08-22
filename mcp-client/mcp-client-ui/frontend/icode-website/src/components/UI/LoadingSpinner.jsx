import React from 'react';
import { Spinner, Box } from '@cloudscape-design/components';

const LoadingSpinner = ({ size = 'normal', text }) => {
  return (
    <Box textAlign="center" padding="xl">
      <Spinner size={size} />
      {text && (
        <Box variant="p" color="text-status-info" marginTop="s">
          {text}
        </Box>
      )}
    </Box>
  );
};

export default LoadingSpinner;