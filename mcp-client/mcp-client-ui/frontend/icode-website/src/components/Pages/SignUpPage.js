import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import authService from '../../services/authService';
import {
  Container,
  Header,
  Form,
  FormField,
  Input,
  Select,
  Button,
  SpaceBetween,
  Alert,
  Box,
  TextContent,
  Grid,
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

const SignUpPage = () => {
  const navigate = useNavigate();
  const { loading } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    sdlcRole: ''
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    // Username validation
    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!emailRegex.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one uppercase letter, one lowercase letter, and one number';
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // First name validation
    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required';
    }

    // Last name validation
    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    }

    // SDLC role validation
    if (!formData.sdlcRole) {
      newErrors.sdlcRole = 'Please select your SDLC specialization';
    }



    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      const signUpData = {
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
        sdlcRole: formData.sdlcRole,
        // Assign admin role for now as requested
        userGroup: 'admins'
      };

      const result = await authService.signUp(signUpData);

      if (result.success) {
        // Navigate directly to login since users are auto-confirmed
        navigate('/login', {
          state: {
            message: 'Account created successfully! You can now sign in with your credentials.',
            username: formData.username
          }
        });
      } else {
        setErrors({
          submit: result.error || 'Sign up failed. Please try again.'
        });
      }
    } catch (error) {
      console.error('Sign up error:', error);
      setErrors({
        submit: error.message || 'An unexpected error occurred. Please try again.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedRole = SDLC_ROLES.find(role => role.value === formData.sdlcRole);

  if (loading) {
    return (
      <Container>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: "m" }}>Loading...</Box>
        </Box>
      </Container>
    );
  }

  return (
    <Container>
      <SpaceBetween size="l">
        <Header
          variant="h1"
          description="Join our SDLC platform and start collaborating with development teams"
        >
          Create Your Account
        </Header>

        <Form
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="primary"
                loading={isSubmitting}
                onClick={handleSubmit}
              >
                {isSubmitting ? 'Creating Account...' : 'Create Account'}
              </Button>
            </SpaceBetween>
          }
          errorText={errors.submit}
        >
          <SpaceBetween size="l">
            {errors.submit && (
              <Alert type="error" dismissible onDismiss={() => setErrors(prev => ({ ...prev, submit: '' }))}>
                {errors.submit}
              </Alert>
            )}

            <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
              <FormField
                label="First Name"
                errorText={errors.firstName}
                constraintText="Required"
              >
                <Input
                  value={formData.firstName}
                  onChange={({ detail }) => handleInputChange({ target: { name: 'firstName', value: detail.value } })}
                  placeholder="Enter your first name"
                  disabled={isSubmitting}
                  invalid={!!errors.firstName}
                />
              </FormField>

              <FormField
                label="Last Name"
                errorText={errors.lastName}
                constraintText="Required"
              >
                <Input
                  value={formData.lastName}
                  onChange={({ detail }) => handleInputChange({ target: { name: 'lastName', value: detail.value } })}
                  placeholder="Enter your last name"
                  disabled={isSubmitting}
                  invalid={!!errors.lastName}
                />
              </FormField>
            </Grid>

            <FormField
              label="Username"
              errorText={errors.username}
              constraintText="Required - At least 3 characters"
            >
              <Input
                value={formData.username}
                onChange={({ detail }) => handleInputChange({ target: { name: 'username', value: detail.value } })}
                placeholder="Choose a username"
                disabled={isSubmitting}
                invalid={!!errors.username}
              />
            </FormField>

            <FormField
              label="Email Address"
              errorText={errors.email}
              constraintText="Required - We'll use this for account verification"
            >
              <Input
                type="email"
                value={formData.email}
                onChange={({ detail }) => handleInputChange({ target: { name: 'email', value: detail.value } })}
                placeholder="Enter your email address"
                disabled={isSubmitting}
                invalid={!!errors.email}
              />
            </FormField>



            <FormField
              label="SDLC Specialization"
              errorText={errors.sdlcRole}
              constraintText="Required - Select your primary area of expertise"
              description={selectedRole ? selectedRole.description : "Choose the SDLC phase you specialize in"}
            >
              <Select
                selectedOption={formData.sdlcRole ? { value: formData.sdlcRole, label: SDLC_ROLES.find(r => r.value === formData.sdlcRole)?.label } : null}
                onChange={({ detail }) => handleInputChange({ target: { name: 'sdlcRole', value: detail.selectedOption.value } })}
                options={SDLC_ROLES}
                placeholder="Select your specialization"
                disabled={isSubmitting}
                invalid={!!errors.sdlcRole}
              />
            </FormField>

            <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
              <FormField
                label="Password"
                errorText={errors.password}
                constraintText="Required - At least 8 characters with uppercase, lowercase, and number"
              >
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={({ detail }) => handleInputChange({ target: { name: 'password', value: detail.value } })}
                  placeholder="Create a strong password"
                  disabled={isSubmitting}
                  invalid={!!errors.password}
                />
              </FormField>

              <FormField
                label="Confirm Password"
                errorText={errors.confirmPassword}
                constraintText="Required - Must match your password"
              >
                <Input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={({ detail }) => handleInputChange({ target: { name: 'confirmPassword', value: detail.value } })}
                  placeholder="Confirm your password"
                  disabled={isSubmitting}
                  invalid={!!errors.confirmPassword}
                />
              </FormField>
            </Grid>

            <Box>
              <TextContent>
                <h4>Password Requirements:</h4>
                <ul>
                  <li>At least 8 characters long</li>
                  <li>At least one uppercase letter</li>
                  <li>At least one lowercase letter</li>
                  <li>At least one number</li>
                </ul>
              </TextContent>
            </Box>
          </SpaceBetween>
        </Form>

        <Box textAlign="center" padding="m">
          <TextContent>
            <p>
              Already have an account?{' '}
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

export default SignUpPage;