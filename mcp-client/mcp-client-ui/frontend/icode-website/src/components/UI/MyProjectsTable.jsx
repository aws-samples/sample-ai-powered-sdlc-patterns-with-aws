import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Header,
  Spinner,
  Alert,
  Box,
  Link,
  SpaceBetween,
  Button,
  Modal
} from '@cloudscape-design/components';
import SectionContainer from './SectionContainer';
import { fetchMyProjects } from '../../services/projectService';
import { projectNameToUrl } from '../../utils/urlUtils';
import CreateProjectButton from './CreateProjectButton';
import { useAuth } from '../../contexts/AuthContext';
import { LoginForm } from './LoginForm';

const MyProjectsTable = () => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAuth();

  useEffect(() => {
    // Only fetch projects if user is authenticated
    if (!isAuthenticated || authLoading) {
      return;
    }

    const loadProjects = async () => {
      try {
        setLoading(true);
        setError(null);
        const projectsData = await fetchMyProjects();
        setProjects(projectsData || []);
      } catch (err) {
        setError(err.message || 'Failed to load projects');
        setProjects([]);
      } finally {
        setLoading(false);
      }
    };

    loadProjects();
  }, [isAuthenticated, authLoading]);

  // Show sign-in prompt if user is not authenticated
  if (!isAuthenticated && !authLoading) {
    return (
      <>
        <SectionContainer
          header={
            <Header 
              variant="h2" 
              description="Sign in to view and manage your projects"
            >
              My Projects
            </Header>
          }
        >
          <Box textAlign="center" padding="l">
            <SpaceBetween direction="vertical" size="m">
              <Box variant="awsui-key-label" color="text-body-secondary">
                🔒 Authentication Required
              </Box>
              <Box variant="p" color="text-body-secondary">
                Sign in to access your projects, create new ones, and collaborate with your team using AWS generative AI tools.
              </Box>
              <SpaceBetween direction="horizontal" size="s">
                <Button 
                  variant="primary" 
                  onClick={() => setShowLoginModal(true)}
                >
                  Sign In
                </Button>
                <Button 
                  variant="normal" 
                  onClick={() => navigate('/signup')}
                >
                  Create Account
                </Button>
              </SpaceBetween>
              <Box variant="small" color="text-body-secondary">
                Already have an account? Use the "Sign In" button above or the navigation menu.
              </Box>
            </SpaceBetween>
          </Box>
        </SectionContainer>

        {/* Login Modal */}
        <Modal
          visible={showLoginModal}
          onDismiss={() => setShowLoginModal(false)}
          header="Sign In to iCode"
          closeAriaLabel="Close modal"
          size="medium"
        >
          <LoginForm 
            onSuccess={() => {
              setShowLoginModal(false);
              // The LoginForm already handles page refresh, but we can close the modal first
            }}
          />
        </Modal>
      </>
    );
  }

  // Don't render anything if auth is still loading
  if (authLoading) {
    return null;
  }

  // Don't render anything if loading initially
  if (loading) {
    return (
      <SectionContainer>
        <Box textAlign="center" padding="l">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>
            Loading your projects...
          </Box>
        </Box>
      </SectionContainer>
    );
  }

  // Don't render anything if there are no projects and no error
  if (!error && projects.length === 0) {
    return null;
  }

  // Show error state
  if (error) {
    return (
      <SectionContainer>
        <Alert type="error" header="Unable to load projects">
          {error}
        </Alert>
      </SectionContainer>
    );
  }

  const handleProjectClick = (projectName) => {
    const urlSafeName = projectNameToUrl(projectName);
    if (urlSafeName) {
      navigate(`/project/${urlSafeName}`);
    }
  };

  const columnDefinitions = [
    {
      id: 'name',
      header: 'Project Name',
      cell: item => {
        const projectName = item.name || 'Untitled Project';
        return (
          <Link
            onFollow={(event) => {
              event.preventDefault();
              handleProjectClick(projectName);
            }}
            href={`/project/${projectNameToUrl(projectName)}`}
          >
            {projectName}
          </Link>
        );
      },
      sortingField: 'name'
    },
    {
      id: 'type',
      header: 'Type',
      cell: item => item.type || 'Not specified',
      sortingField: 'type'
    },
    {
      id: 'createdAt',
      header: 'Created',
      cell: item => {
        if (!item.createdAt) return 'Unknown';
        try {
          return new Date(item.createdAt).toLocaleDateString();
        } catch {
          return 'Unknown';
        }
      },
      sortingField: 'createdAt'
    },
    {
      id: 'status',
      header: 'Status',
      cell: item => item.status || 'Active',
      sortingField: 'status'
    }
  ];

  return (
    <>
      <SectionContainer
        header={
          <Header 
            variant="h2" 
            description="Your recently created projects"
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  onClick={() => navigate('/projects')}
                >
                  View All Projects
                </Button>
                <CreateProjectButton />
              </SpaceBetween>
            }
          >
            My Projects
          </Header>
        }
      >
        <Table
          columnDefinitions={columnDefinitions}
          items={projects}
          sortingDisabled={false}
          variant="container"
          empty={
            <Box textAlign="center" color="inherit">
              <SpaceBetween size="m">
                <Box variant="strong" textAlign="center" color="inherit">
                  No projects found
                </Box>
                <Box variant="p" padding={{ bottom: 's' }} color="inherit">
                  You haven't created any projects yet. Get started by creating your first project!
                </Box>
                <CreateProjectButton />
              </SpaceBetween>
            </Box>
          }
        />
      </SectionContainer>

      {/* Login Modal */}
      <Modal
        visible={showLoginModal}
        onDismiss={() => setShowLoginModal(false)}
        header="Sign In to iCode"
        closeAriaLabel="Close modal"
        size="medium"
      >
        <LoginForm 
          onSuccess={() => {
            setShowLoginModal(false);
            // The LoginForm already handles page refresh, but we can close the modal first
          }}
        />
      </Modal>
    </>
  );
};

export default MyProjectsTable;