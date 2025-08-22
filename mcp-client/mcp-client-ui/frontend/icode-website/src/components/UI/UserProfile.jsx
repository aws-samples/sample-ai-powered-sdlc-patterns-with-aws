import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Badge,
  Button,
  Modal,
  Table,
  StatusIndicator
} from '@cloudscape-design/components';

export const UserProfile = ({ onClose }) => {
  const { userProfile, signOut, loading } = useAuth();
  const [showSignOutConfirm, setShowSignOutConfirm] = useState(false);

  const handleSignOut = async () => {
    const result = await signOut();
    if (result.success) {
      onClose?.();
    }
  };

  if (!userProfile) {
    return (
      <div className="user-profile">
        <div className="user-profile__loading">
          <LoadingSpinner size="medium" />
          <p>Loading profile...</p>
        </div>
      </div>
    );
  }



  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            onClose && (
              <Button
                variant="icon"
                iconName="close"
                onClick={onClose}
                ariaLabel="Close profile"
              />
            )
          }
        >
          {userProfile.firstName} {userProfile.lastName}
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        <Box>
          <SpaceBetween direction="vertical" size="xs">
            <Box variant="h3">@{userProfile.username}</Box>
            <Box color="text-body-secondary">{userProfile.email}</Box>
          </SpaceBetween>
        </Box>

      <Container header={<Header variant="h3">Account Status</Header>}>
        <SpaceBetween direction="vertical" size="s">
          <Box>
            <SpaceBetween direction="horizontal" size="s">
              <Box variant="span">Email Verification:</Box>
              <StatusIndicator type={userProfile.emailVerified ? 'success' : 'warning'}>
                {userProfile.emailVerified ? 'Verified' : 'Pending'}
              </StatusIndicator>
            </SpaceBetween>
          </Box>
        </SpaceBetween>
      </Container>

      <Container header={<Header variant="h3">Custom Attributes</Header>}>
        <Table
          columnDefinitions={[
            {
              id: 'name',
              header: 'Attribute name',
              cell: item => <code>{item.name}</code>
            },
            {
              id: 'value',
              header: 'Value',
              cell: item => <Badge color={item.value === 'Not assigned' ? 'grey' : 'blue'}>{item.value}</Badge>
            },
            {
              id: 'type',
              header: 'Type',
              cell: item => item.type
            }
          ]}
          items={[
            {
              name: 'custom:sdlc_role',
              value: userProfile.sdlcRole || 'Not assigned',
              type: 'String'
            }
          ]}
          variant="embedded"
        />
      </Container>



      <Box padding="l">
        <Button
          variant="primary"
          onClick={() => setShowSignOutConfirm(true)}
          disabled={loading}
          fullWidth
        >
          Sign Out
        </Button>
      </Box>

      <Modal
        visible={showSignOutConfirm}
        onDismiss={() => setShowSignOutConfirm(false)}
        header="Confirm Sign Out"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => setShowSignOutConfirm(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSignOut}
                disabled={loading}
                loading={loading}
              >
                Sign Out
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        Are you sure you want to sign out?
      </Modal>
      </SpaceBetween>
    </Container>
  );
};