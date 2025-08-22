import React from 'react';
import { AppLayout as CloudscapeAppLayout } from '@cloudscape-design/components';

const AppLayout = ({ 
  children, 
  navigation, 
  navigationOpen = false,
  onNavigationChange,
  breadcrumbs,
  notifications
}) => {
  return (
    <CloudscapeAppLayout
      navigation={navigation}
      navigationOpen={navigationOpen}
      onNavigationChange={onNavigationChange}
      breadcrumbs={breadcrumbs}
      notifications={notifications}
      content={children}
      toolsHide={true}
      navigationHide={true} // Hide sidebar navigation for simple layout
    />
  );
};

export default AppLayout;