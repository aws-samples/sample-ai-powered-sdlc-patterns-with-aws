import React from 'react';
import { Container } from '@cloudscape-design/components';

/**
 * A consistent container for all sections on the home page
 * This ensures all sections have the same width and padding
 */
const SectionContainer = ({ children, header, variant }) => {
  return (
    <Container
      header={header}
      variant={variant}
    >
      {children}
    </Container>
  );
};

export default SectionContainer;