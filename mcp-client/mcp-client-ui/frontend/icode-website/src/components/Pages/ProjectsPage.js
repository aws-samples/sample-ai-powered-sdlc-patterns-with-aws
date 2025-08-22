import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
    Container,
    Header,
    Table,
    Button,
    SpaceBetween,
    Alert,
    StatusIndicator,
    Box,
    TextFilter,
    Pagination,
    CollectionPreferences
} from '@cloudscape-design/components';
import { fetchMyProjects } from '../../services/projectService';
import CreateProjectButton from '../UI/CreateProjectButton';

const ProjectsPage = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [filteringText, setFilteringText] = useState('');
    const [currentPageIndex, setCurrentPageIndex] = useState(1);
    const [pageSize, setPageSize] = useState(10);

    // Check for success message from navigation state
    useEffect(() => {
        if (location.state?.message) {
            setSuccessMessage(location.state.message);
            // Clear the state to prevent showing message on refresh
            window.history.replaceState({}, document.title);
        }
    }, [location.state]);

    // Load projects on component mount
    useEffect(() => {
        loadProjects();
    }, []);

    const loadProjects = async () => {
        try {
            setLoading(true);
            setError('');
            const projectsData = await fetchMyProjects();
            setProjects(projectsData || []);
        } catch (err) {
            console.error('Error loading projects:', err);
            setError(err.message || 'Failed to load projects');
        } finally {
            setLoading(false);
        }
    };

    const handleProjectClick = (projectId) => {
        navigate(`/project/${projectId}`);
    };

    const handleRefresh = () => {
        loadProjects();
    };

    // Filter projects based on search text
    const filteredProjects = projects.filter(project =>
        project.name?.toLowerCase().includes(filteringText.toLowerCase()) ||
        project.description?.toLowerCase().includes(filteringText.toLowerCase()) ||
        project.project_type?.toLowerCase().includes(filteringText.toLowerCase())
    );

    // Paginate filtered projects
    const startIndex = (currentPageIndex - 1) * pageSize;
    const paginatedProjects = filteredProjects.slice(startIndex, startIndex + pageSize);

    const columnDefinitions = [
        {
            id: 'name',
            header: 'Project Name',
            cell: item => (
                <Button
                    variant="link"
                    onClick={() => handleProjectClick(item.project_id)}
                >
                    {item.name}
                </Button>
            ),
            sortingField: 'name',
            isRowHeader: true
        },
        {
            id: 'description',
            header: 'Description',
            cell: item => item.description || '-',
            sortingField: 'description'
        },
        {
            id: 'project_type',
            header: 'Type',
            cell: item => item.project_type || 'web',
            sortingField: 'project_type'
        },
        {
            id: 'status',
            header: 'Status',
            cell: item => (
                <StatusIndicator type={item.status === 'active' ? 'success' : 'stopped'}>
                    {item.status || 'active'}
                </StatusIndicator>
            ),
            sortingField: 'status'
        },
        {
            id: 'created_at',
            header: 'Created',
            cell: item => {
                if (item.created_at) {
                    return new Date(item.created_at).toLocaleDateString();
                }
                return '-';
            },
            sortingField: 'created_at'
        }
    ];

    return (
        <Container
            header={
                <Header
                    variant="h1"
                    description="Manage your development projects"
                    actions={
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button
                                iconName="refresh"
                                onClick={handleRefresh}
                                loading={loading}
                            >
                                Refresh
                            </Button>
                            <CreateProjectButton />
                        </SpaceBetween>
                    }
                >
                    My Projects
                </Header>
            }
        >
            <SpaceBetween direction="vertical" size="l">
                {successMessage && (
                    <Alert
                        type="success"
                        dismissible
                        onDismiss={() => setSuccessMessage('')}
                    >
                        {successMessage}
                    </Alert>
                )}

                {error && (
                    <Alert
                        type="error"
                        dismissible
                        onDismiss={() => setError('')}
                        action={
                            <Button onClick={handleRefresh}>
                                Try Again
                            </Button>
                        }
                    >
                        {error}
                    </Alert>
                )}

                <Table
                    columnDefinitions={columnDefinitions}
                    items={paginatedProjects}
                    loading={loading}
                    loadingText="Loading projects..."
                    empty={
                        <Box textAlign="center" color="inherit">
                            <SpaceBetween size="m">
                                <b>No projects found</b>
                                <p>You haven't created any projects yet.</p>
                                <CreateProjectButton />
                            </SpaceBetween>
                        </Box>
                    }
                    filter={
                        <TextFilter
                            filteringText={filteringText}
                            onChange={({ detail }) => setFilteringText(detail.filteringText)}
                            placeholder="Search projects..."
                        />
                    }
                    pagination={
                        <Pagination
                            currentPageIndex={currentPageIndex}
                            onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
                            pagesCount={Math.ceil(filteredProjects.length / pageSize)}
                        />
                    }
                    preferences={
                        <CollectionPreferences
                            title="Preferences"
                            confirmLabel="Confirm"
                            cancelLabel="Cancel"
                            preferences={{
                                pageSize: pageSize,
                                visibleContent: ['name', 'description', 'project_type', 'status', 'created_at']
                            }}
                            pageSizePreference={{
                                title: 'Page size',
                                options: [
                                    { value: 10, label: '10 projects' },
                                    { value: 20, label: '20 projects' },
                                    { value: 50, label: '50 projects' }
                                ]
                            }}
                            onConfirm={({ detail }) => {
                                setPageSize(detail.pageSize);
                                setCurrentPageIndex(1);
                            }}
                        />
                    }
                />
            </SpaceBetween>
        </Container>
    );
};

export default ProjectsPage;