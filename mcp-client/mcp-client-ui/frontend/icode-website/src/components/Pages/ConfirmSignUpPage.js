import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import authService from '../../services/authService';
import {
    Container,
    Header,
    Form,
    FormField,
    Input,
    Button,
    SpaceBetween,
    Alert,
    Box,
    TextContent,
    Spinner
} from '@cloudscape-design/components';

const ConfirmSignUpPage = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const [confirmationCode, setConfirmationCode] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isResending, setIsResending] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Get username and email from navigation state
    const username = location.state?.username || '';
    const email = location.state?.email || '';

    useEffect(() => {
        // Redirect to sign-up if no username provided
        if (!username) {
            navigate('/signup');
        }
    }, [username, navigate]);

    const handleConfirmation = async (e) => {
        e.preventDefault();

        if (!confirmationCode.trim()) {
            setError('Please enter the confirmation code');
            return;
        }

        setIsSubmitting(true);
        setError('');
        setSuccess('');

        try {
            const result = await authService.confirmSignUp(username, confirmationCode.trim());

            if (result.success) {
                setSuccess('Account confirmed successfully! Redirecting to login...');
                setTimeout(() => {
                    navigate('/login', {
                        state: {
                            message: 'Account confirmed! Please sign in with your credentials.',
                            username: username
                        }
                    });
                }, 2000);
            } else {
                setError(result.error || 'Confirmation failed. Please try again.');
            }
        } catch (error) {
            console.error('Confirmation error:', error);
            setError(error.message || 'An unexpected error occurred. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleResendCode = async () => {
        setIsResending(true);
        setError('');
        setSuccess('');

        try {
            const result = await authService.resendConfirmationCode(username);

            if (result.success) {
                setSuccess('Confirmation code sent! Please check your email.');
            } else {
                setError(result.error || 'Failed to resend code. Please try again.');
            }
        } catch (error) {
            console.error('Resend code error:', error);
            setError(error.message || 'Failed to resend code. Please try again.');
        } finally {
            setIsResending(false);
        }
    };

    if (!username) {
        return (
            <Container>
                <Box textAlign="center" padding="xxl">
                    <Spinner size="large" />
                    <Box variant="p" padding={{ top: "m" }}>Redirecting...</Box>
                </Box>
            </Container>
        );
    }

    return (
        <Container>
            <SpaceBetween size="l">
                <Header
                    variant="h1"
                    description={`We've sent a confirmation code to ${email}. Please enter it below to verify your account.`}
                >
                    Confirm Your Account
                </Header>

                <Form
                    actions={
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button
                                variant="link"
                                onClick={handleResendCode}
                                loading={isResending}
                                disabled={isSubmitting}
                            >
                                Resend Code
                            </Button>
                            <Button
                                variant="primary"
                                loading={isSubmitting}
                                onClick={handleConfirmation}
                                disabled={!confirmationCode.trim()}
                            >
                                {isSubmitting ? 'Confirming...' : 'Confirm Account'}
                            </Button>
                        </SpaceBetween>
                    }
                >
                    <SpaceBetween size="l">
                        {error && (
                            <Alert
                                type="error"
                                dismissible
                                onDismiss={() => setError('')}
                            >
                                {error}
                            </Alert>
                        )}

                        {success && (
                            <Alert
                                type="success"
                                dismissible
                                onDismiss={() => setSuccess('')}
                            >
                                {success}
                            </Alert>
                        )}

                        <Box>
                            <TextContent>
                                <p><strong>Username:</strong> {username}</p>
                                <p><strong>Email:</strong> {email}</p>
                            </TextContent>
                        </Box>

                        <FormField
                            label="Confirmation Code"
                            constraintText="Enter the 6-digit code sent to your email"
                            description="Check your email inbox (and spam folder) for the confirmation code"
                        >
                            <Input
                                value={confirmationCode}
                                onChange={({ detail }) => setConfirmationCode(detail.value)}
                                placeholder="Enter 6-digit confirmation code"
                                disabled={isSubmitting}
                                autoComplete="one-time-code"
                                inputMode="numeric"
                                pattern="[0-9]*"
                                maxLength={6}
                            />
                        </FormField>

                        <Box>
                            <TextContent>
                                <h4>Didn't receive the code?</h4>
                                <ul>
                                    <li>Check your spam/junk folder</li>
                                    <li>Make sure the email address is correct</li>
                                    <li>Click "Resend Code" to get a new one</li>
                                    <li>Wait a few minutes for the email to arrive</li>
                                </ul>
                            </TextContent>
                        </Box>
                    </SpaceBetween>
                </Form>

                <Box textAlign="center" padding="m">
                    <TextContent>
                        <p>
                            Need to use a different email?{' '}
                            <Link to="/signup" style={{ color: '#0073bb', textDecoration: 'none' }}>
                                Create a new account
                            </Link>
                        </p>
                        <p>
                            Already confirmed?{' '}
                            <Link to="/login" style={{ color: '#0073bb', textDecoration: 'none' }}>
                                Sign in here
                            </Link>
                        </p>
                    </TextContent>
                </Box>
            </SpaceBetween>
        </Container>
    );
};

export default ConfirmSignUpPage;