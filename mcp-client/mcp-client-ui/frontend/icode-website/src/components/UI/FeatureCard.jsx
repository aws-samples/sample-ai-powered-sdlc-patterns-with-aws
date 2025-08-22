import React from 'react';
import { Container, Header, Box, Link } from '@cloudscape-design/components';

const FeatureCard = ({ title, description, icon, href }) => {
  const cardContent = (
    <Container
      header={
        <Header variant="h3">
          {icon && <Box display="inline" marginRight="s">{icon}</Box>}
          {title}
        </Header>
      }
    >
      <Box variant="p">
        {description}
      </Box>
    </Container>
  );

  if (href) {
    return (
      <Link href={href} external={href.startsWith('http')}>
        <Box className="feature-card-hover">
          {cardContent}
        </Box>
      </Link>
    );
  }

  return cardContent;
};

export default FeatureCard;