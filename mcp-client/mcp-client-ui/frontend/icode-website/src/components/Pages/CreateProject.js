import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container,
    Header,
    Form,
    FormField,
    Input,
    Textarea,
    Select,
    Button,
    SpaceBetween,
    Alert,
    StatusIndicator,
    Box
} from '@cloudscape-design/components';
import { createProject, validateProjectName, getProjectTypes } from '../../services/projectService';

const CreateProject = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        project_type: 'web',
        assigned_groups: ['Developers']
    });
    const [projectTypes, setProjectTypes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [nameValidation, setNameValidation] = useState({ checking: false, available: null, message: '' });
    const [errors, setErrors] = useState({});
    const [submitError, setSubmitError] = useState('');

    // Load project types on component mount
    useEffect(() => {
        const loadProjectTypes = async () => {
            try {
                console.log('Loading project types...');
                const types = await getProjectTypes();
                console.log('Project types loaded:', types);
                setProjectTypes(types);
            } catch (error) {
                console.error('Error loading project types:', error);
                // Set default types if API fails
                setProjectTypes([
                    { value: 'web', label: 'Web Application' },
                    { value: 'mobile', label: 'Mobile Application' },
                    { value: 'api', label: 'API/Backend Service' },
                    { value: 'desktop', label: 'Desktop Application' },
                    { value: 'data', label: 'Data Processing' },
                    { value: 'ml', label: 'Machine Learning' },
                    { value: 'other', label: 'Other' }
                ]);
            }
        };
        loadProjectTypes();
    }, []);

    // Validate project name with debouncing
    useEffect(() => {
        const validateName = async () => {
            if (!formData.name.trim()) {
                setNameValidation({ checking: false, available: null, message: '' });
                return;
            }

            setNameValidation({ checking: true, available: null, message: 'Checking availability...' });

            try {
                console.log('Validating project name:', formData.name);
                const result = await validateProjectName(formData.name);
                console.log('Validation result:', result);
                setNameValidation({
                    checking: false,
                    available: result.available,
                    message: result.message
                });
            } catch (error) {
                console.error('Name validation error:', error);
                setNameValidation({
                    checking: false,
                    available: false,
                    message: `Error checking name availability: ${error.message}`
                });
            }
        };

        const timeoutId = setTimeout(validateName, 500);
        return () => clearTimeout(timeoutId);
    }, [formData.name]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));

        // Clear field-specific error when user starts typing
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
        setSubmitError('');
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.name.trim()) {
            newErrors.name = 'Project name is required';
        } else if (formData.name.length > 100) {
            newErrors.name = 'Project name must be less than 100 characters';
        } else if (nameValidation.available === false) {
            newErrors.name = 'Project name is not available';
        }

        if (!formData.description.trim()) {
            newErrors.description = 'Project description is required';
        } else if (formData.description.length > 500) {
            newErrors.description = 'Project description must be less than 500 characters';
        }

        if (!formData.project_type) {
            newErrors.project_type = 'Project type is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        console.log('Form data before validation:', formData);
        
        if (!validateForm()) {
            console.log('Form validation failed');
            return;
        }

        if (nameValidation.checking) {
            setSubmitError('Please wait for name validation to complete');
            return;
        }

        if (nameValidation.available === false) {
            setSubmitError('Please choose a different project name');
            return;
        }

        setLoading(true);
        setSubmitError('');

        try {
            console.log('Submitting project data:', formData);
            const result = await createProject(formData);
            console.log('Project created:', result);
            
            // Navigate to project details or projects list
            navigate('/projects', { 
                state: { 
                    message: `Project "${result.metadata.name}" created successfully!`,
                    projectId: result.project_id
                }
            });
        } catch (error) {
            console.error('Error creating project:', error);
            setSubmitError(error.message || 'Failed to create project. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        navigate('/projects');
    };

    return (
        <Container
            header={
                <Header
                    variant="h1"
                    description="Set up a new project to start building your application"
                >
                    Create New Project
                </Header>
            }
        >
            <Form
                actions={
                    <SpaceBetween direction="horizontal" size="xs">
                        <Button
                            variant="link"
                            onClick={handleCancel}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            onClick={handleSubmit}
                            loading={loading}
                            disabled={nameValidation.checking || nameValidation.available === false}
                        >
                            Create Project
                        </Button>
                    </SpaceBetween>
                }
                errorText={submitError}
            >
                <SpaceBetween direction="vertical" size="l">
                    <FormField
                        label="Project Name"
                        description="Choose a unique name for your project"
                        errorText={errors.name}
                        constraintText="Maximum 100 characters"
                    >
                        <Input
                            value={formData.name}
                            onChange={({ detail }) => handleInputChange({ target: { name: 'name', value: detail.value } })}
                            placeholder="Enter project name"
                            disabled={loading}
                        />
                        {nameValidation.checking && (
                            <Box margin={{ top: 'xs' }}>
                                <StatusIndicator type="loading">
                                    {nameValidation.message}
                                </StatusIndicator>
                            </Box>
                        )}
                        {nameValidation.available === true && (
                            <Box margin={{ top: 'xs' }}>
                                <StatusIndicator type="success">
                                    Project name is available
                                </StatusIndicator>
                            </Box>
                        )}
                        {nameValidation.available === false && (
                            <Box margin={{ top: 'xs' }}>
                                <StatusIndicator type="error">
                                    {nameValidation.message}
                                </StatusIndicator>
                            </Box>
                        )}
                    </FormField>

                    <FormField
                        label="Project Description"
                        description="Describe what your project is about"
                        errorText={errors.description}
                        constraintText={`${formData.description.length}/500 characters`}
                    >
                        <Textarea
                            value={formData.description}
                            onChange={({ detail }) => handleInputChange({ target: { name: 'description', value: detail.value } })}
                            placeholder="Describe your project..."
                            rows={4}
                            disabled={loading}
                        />
                    </FormField>

                    <FormField
                        label="Project Type"
                        description="Select the type of project you're creating"
                        errorText={errors.project_type}
                    >
                        <Select
                            selectedOption={projectTypes.find(type => type.value === formData.project_type) || null}
                            onChange={({ detail }) => 
                                handleInputChange({ 
                                    target: { 
                                        name: 'project_type', 
                                        value: detail.selectedOption.value 
                                    } 
                                })
                            }
                            options={projectTypes}
                            placeholder="Choose a project type"
                            disabled={loading}
                        />
                    </FormField>
                </SpaceBetween>
            </Form>
        </Container>
    );
};

export default CreateProject;