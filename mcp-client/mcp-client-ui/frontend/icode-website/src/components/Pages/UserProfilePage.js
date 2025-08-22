import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  ColumnLayout,
  StatusIndicator,
  Badge,
  TextContent,
  Button,
  Modal,
  Form,
  FormField,
  Input,
  Select,
  Alert,
  Spinner
} from '@cloudscape-design/components';

const SDLC_ROLES = [
  {
    value: 'requirements-analyst',
    label: 'Requirements Analyst',
    description: 'Specializes in gathering, analyzing, and documenting business requirements'
  },
  {
    value: 'system-architect',
    label: 'System Architect',
    description: 'Designs system architecture and technical solutions'
  },
  {
    value: 'software-developer',
    label: 'Software Developer',
    description: 'Develops and implements software solutions'
  },
  {
    value: 'qa-engineer',
    label: 'QA Engineer',
    description: 'Ensures quality through testing and validation processes'
  },
  {
    value: 'devops-engineer',
    label: 'DevOps Engineer',
    description: 'Manages deployment, infrastructure, and CI/CD processes'
  },
  {
    value: 'maintenance-specialist',
    label: 'Maintenance Specialist',
    description: 'Handles ongoing maintenance, support, and system optimization'
  }
].map(role => ({ ...role, text: role.label }));

const UserProfilePage = () => {
  const { user, userProfile, loading } = useAuth();
  const [showEditModal, setShowEditModal] = useState(false);
  const [editFormData, setEditFormData] = useState({
    firstName: '',
    lastName: '',
    sdlcRole: ''
  });
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateError, setUpdateError] = useState('');
  const [updateSuccess, setUpdateSuccess] = useState('');

  useEffect(() => {
    if (userProfile) {
      setEditFormData({
        firstName: userProfile.firstName || '',
        lastName: userProfile.lastName || '',
        sdlcRole: userProfile.sdlcRole || ''
      });
    }
  }, [userProfile]);

  const handleEditInputChange = (field, value) => {
    setEditFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleUpdateProfile = async () => {
    setIsUpdating(true);
    setUpdateError('');
    setUpdateSuccess('');

    try {
      // This would call an API to update the user profile
      // For now, we'll simulate the update
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setUpdateSuccess('Profile updated successfully!');
      setShowEditModal(false);
      
      // In a real implementation, you'd refresh the user profile data here
    } catch (error) {
      setUpdateError(error.message || 'Failed to update profile');
    } finally {
      setIsUpdating(false);
    }
  };

  const getRoleInfo = (roleValue) => {
    return SDLC_ROLES.find(role => role.value === roleValue);
  };

  const getStatusColor = (groups) => {
    if (groups?.includes('admins')) return 'success';
    if (groups?.includes('developers')) return 'info';
    if (groups?.includes('qa-team')) return 'warning';
    return 'grey';
  };

  const getStatusText = (groups) => {
    if (groups?.includes('admins')) return 'Administrator';
    if (groups?.includes('developers')) return 'Developer';
    if (groups?.includes('qa-team')) return 'QA Team';
    return 'User';
  };

  if (loading) {
    return (
      <Container>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: "m" }}>Loading profile...</Box>
        </Box>
      </Container>
    );
  }

  if (!user || !userProfile) {
    return (
      <Container>
        <Alert type="error">
          Unable to load user profile. Please try refreshing the page.
        </Alert>
      </Container>
    );
  }

  const roleInfo = getRoleInfo(userProfile.sdlcRole);

  return (
    <Container>
      <SpaceBetween size="l">
        <Header
          variant="h1"
          actions={
            <Button
              variant="primary"
              onClick={() => setShowEditModal(true)}
            >
              Edit Profile
            </Button>
          }
        >
          User Profile
        </Header>

        {updateSuccess && (
          <Alert 
            type="success" 
            dismissible 
            onDismiss={() => setUpdateSuccess('')}
          >
            {updateSuccess}
          </Alert>
        )}

        <ColumnLayout columns={2} variant="text-grid">
          <SpaceBetween size="l">
            <Box>
              <Box variant="h2" padding={{ bottom: "s" }}>Personal Information</Box>
              <SpaceBetween size="m">
                <Box>
                  <Box variant="strong">Full Name</Box>
                  <Box>{userProfile.firstName} {userProfile.lastName}</Box>
                </Box>
                <Box>
                  <Box variant="strong">Username</Box>
                  <Box>{user.username}</Box>
                </Box>
                <Box>
                  <Box variant="strong">Email</Box>
                  <Box>{user.email}</Box>
                  <StatusIndicator type={userProfile.emailVerified ? "success" : "warning"}>
                    {userProfile.emailVerified ? "Verified" : "Not Verified"}
                  </StatusIndicator>
                </Box>

              </SpaceBetween>
            </Box>
          </SpaceBetween>

          <SpaceBetween size="l">
            <Box>
              <Box variant="h2" padding={{ bottom: "s" }}>Professional Information</Box>
              <SpaceBetween size="m">
                <Box>
                  <Box variant="strong">SDLC Specialization</Box>
                  {roleInfo ? (
                    <SpaceBetween size="xs">
                      <Badge color="blue">{roleInfo.label}</Badge>
                      <Box variant="small">{roleInfo.description}</Box>
                    </SpaceBetween>
                  ) : (
                    <Box variant="small" color="text-status-inactive">Not specified</Box>
                  )}
                </Box>
                <Box>
                  <Box variant="strong">Account Status</Box>
                  <StatusIndicator type={getStatusColor(userProfile.groups)}>
                    {getStatusText(userProfile.groups)}
                  </StatusIndicator>
                </Box>
                <Box>
                  <Box variant="strong">User Groups</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    {userProfile.groups?.map(group => (
                      <Badge key={group} color="grey">{group}</Badge>
                    )) || <Box variant="small" color="text-status-inactive">No groups assigned</Box>}
                  </SpaceBetween>
                </Box>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </ColumnLayout>

        <Box>
          <Box variant="h2" padding={{ bottom: "s" }}>Account Activity</Box>
          <TextContent>
            <p>Your account was created and you have admin privileges to create and manage projects on the platform.</p>
            <p>As a <strong>{roleInfo?.label || 'team member'}</strong>, you can contribute to projects in your area of expertise.</p>
          </TextContent>
        </Box>
      </SpaceBetween>

      <Modal
        onDismiss={() => setShowEditModal(false)}
        visible={showEditModal}
        header="Edit Profile"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button 
                variant="link" 
                onClick={() => setShowEditModal(false)}
                disabled={isUpdating}
              >
                Cancel
              </Button>
              <Button 
                variant="primary" 
                onClick={handleUpdateProfile}
                loading={isUpdating}
              >
                Save Changes
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <Form>
          <SpaceBetween size="l">
            {updateError && (
              <Alert type="error" dismissible onDismiss={() => setUpdateError('')}>
                {updateError}
              </Alert>
            )}

            <ColumnLayout columns={2}>
              <FormField label="First Name">
                <Input
                  value={editFormData.firstName}
                  onChange={({ detail }) => handleEditInputChange('firstName', detail.value)}
                  placeholder="Enter your first name"
                  disabled={isUpdating}
                />
              </FormField>

              <FormField label="Last Name">
                <Input
                  value={editFormData.lastName}
                  onChange={({ detail }) => handleEditInputChange('lastName', detail.value)}
                  placeholder="Enter your last name"
                  disabled={isUpdating}
                />
              </FormField>
            </ColumnLayout>

            <FormField 
              label="SDLC Specialization"
              description="Select your primary area of expertise"
            >
              <Select
                selectedOption={editFormData.sdlcRole ? { 
                  value: editFormData.sdlcRole, 
                  label: SDLC_ROLES.find(r => r.value === editFormData.sdlcRole)?.label 
                } : null}
                onChange={({ detail }) => handleEditInputChange('sdlcRole', detail.selectedOption.value)}
                options={SDLC_ROLES}
                placeholder="Select your specialization"
                disabled={isUpdating}
              />
            </FormField>

          </SpaceBetween>
        </Form>
      </Modal>
    </Container>
  );
};

export default UserProfilePage;