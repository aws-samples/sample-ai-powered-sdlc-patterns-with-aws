import React from 'react';
import { Box, Link, SpaceBetween } from '@cloudscape-design/components';

const Footer = ({ links = [], copyright }) => {
  return (
    <Box padding="l" textAlign="center">
      <SpaceBetween direction="vertical" size="m">
        {links.length > 0 && (
          <SpaceBetween direction="horizontal" size="l" alignItems="center">
            {links.map((link) => (
              <Link
                key={link.id}
                href={link.href}
                external={link.external}
                fontSize="body-s"
              >
                {link.text}
              </Link>
            ))}
          </SpaceBetween>
        )}
      </SpaceBetween>
    </Box>
  );
};

export default Footer;