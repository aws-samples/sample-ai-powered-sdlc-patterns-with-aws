import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
    Container,
    Header,
    SpaceBetween,
    Box,
    TextContent
} from '@cloudscape-design/components';
import { LoginForm } from '../UI/LoginForm';

const LoginPage = () => {
    const navigate = useNavigate();
    const { isAuthenticated, loading } = useAuth();

    // Redirect if already authenticated
    React.useEffect(() => {
        if (isAuthenticated && !loading) {
            navigate('/');
        }
    }, [isAuthenticated, loading, navigate]);

    if (loading) {
        return (
            <Container>
                <Box textAlign="center" padding="xxl">
                    <Box variant="p">Loading...</Box>
                </Box>
            </Container>
        );
    }

    if (isAuthenticated) {
        return null; // Will redirect via useEffect
    }

    return (
        <Container>
            <SpaceBetween size="l">
                <Header
                    variant="h1"
                    description="Sign in to access your projects and collaborate with your team"
                >
                    Sign In
                </Header>

                <Box display="flex" justifyContent="center">
                    <LoginForm
                        onSuccess={() => {
                            // Redirect to home page after successful login
                            navigate('/');
                        }}
                    />
                </Box>

                <Box textAlign="center" padding="m">
                    <TextContent>
                        <p>
                            Don't have an account?{' '}
                            <Link to="/signup" style={{ color: '#0073bb', textDecoration: 'none' }}>
                                Create one here
                            </Link>
                        </p>
                    </TextContent>
                </Box>
            </SpaceBetween>
        </Container>
    );
};

export default LoginPage;