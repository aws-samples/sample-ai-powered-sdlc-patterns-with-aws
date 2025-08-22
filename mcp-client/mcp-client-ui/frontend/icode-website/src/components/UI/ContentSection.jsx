import React from 'react';
import { Header } from '@cloudscape-design/components';
import SectionContainer from './SectionContainer';

const ContentSection = ({ title, children, variant = 'default' }) => {
  const containerProps = {
    header: title ? <Header variant="h2">{title}</Header> : undefined,
    variant: variant === 'highlighted' ? 'stacked' : undefined
  };

  return (
    <SectionContainer {...containerProps}>
      {children}
    </SectionContainer>
  );
};

export default ContentSection;