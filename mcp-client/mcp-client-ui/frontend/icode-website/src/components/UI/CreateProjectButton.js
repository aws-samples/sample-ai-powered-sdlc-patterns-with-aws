import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@cloudscape-design/components';

const CreateProjectButton = ({ variant = 'primary', size = 'normal', ...props }) => {
    const navigate = useNavigate();

    const handleCreateProject = () => {
        navigate('/create-project');
    };

    return (
        <Button
            variant={variant}
            size={size}
            onClick={handleCreateProject}
            iconName="add-plus"
            {...props}
        >
            Create New Project
        </Button>
    );
};

export default CreateProjectButton;