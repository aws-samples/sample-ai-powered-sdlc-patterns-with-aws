import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Header, Button, SpaceBetween } from '@cloudscape-design/components';
import SectionContainer from './SectionContainer';

const HeroSection = ({ title, subtitle, actions = [] }) => {
  const navigate = useNavigate();

  const handleActionClick = (action) => {
    if (action.onClick) {
      action.onClick();
    } else if (action.href) {
      navigate(action.href);
    }
  };

  return (
    <SectionContainer>
      <Box padding="xxl" textAlign="center">
        <SpaceBetween direction="vertical" size="l">
          <Header
            variant="h1"
            description={subtitle}
          >
            {title}
          </Header>
          
          {actions.length > 0 && (
            <SpaceBetween direction="horizontal" size="m">
              {actions.map((action, index) => (
                <Button
                  key={index}
                  variant={action.variant || 'primary'}
                  onClick={() => handleActionClick(action)}
                  disabled={action.disabled}
                >
                  {action.text}
                </Button>
              ))}
            </SpaceBetween>
          )}
        </SpaceBetween>
      </Box>
    </SectionContainer>
  );
};

export default HeroSection;