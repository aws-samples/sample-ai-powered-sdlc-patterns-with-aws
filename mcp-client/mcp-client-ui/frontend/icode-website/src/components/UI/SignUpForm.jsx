import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';

export const SignUpForm = ({ onSuccess, onSwitchToSignIn }) => {
  const { signUp, confirmSignUp, loading, error, clearError } = useAuth();
  const [step, setStep] = useState('signup'); // 'signup' or 'confirm'
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: ''
  });
  const [confirmationCode, setConfirmationCode] = useState('');
  const [formErrors, setFormErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear field error when user starts typing
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
    
    // Clear auth error
    if (error) {
      clearError();
    }
  };

  const handleConfirmationCodeChange = (e) => {
    setConfirmationCode(e.target.value);
    if (error) {
      clearError();
    }
  };

  const validateSignUpForm = () => {
    const errors = {};
    
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      errors.username = 'Username must be at least 3 characters';
    }
    
    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }
    
    if (!formData.firstName.trim()) {
      errors.firstName = 'First name is required';
    }
    
    if (!formData.lastName.trim()) {
      errors.lastName = 'Last name is required';
    }
    
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(formData.password)) {
      errors.password = 'Password must contain uppercase, lowercase, number, and special character';
    }
    
    if (!formData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSignUpSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateSignUpForm()) {
      return;
    }
    
    const result = await signUp(
      formData.username,
      formData.password,
      formData.email,
      formData.firstName,
      formData.lastName
    );
    
    if (result.success) {
      if (result.needsConfirmation) {
        setStep('confirm');
      } else {
        onSuccess?.();
      }
    }
  };

  const handleConfirmSubmit = async (e) => {
    e.preventDefault();
    
    if (!confirmationCode.trim()) {
      setFormErrors({ confirmationCode: 'Confirmation code is required' });
      return;
    }
    
    const result = await confirmSignUp(formData.username, confirmationCode);
    
    if (result.success) {
      onSuccess?.();
    }
  };

  const handleResendCode = async () => {
    const result = await (formData.username);
    if (result.success) {
      // Show success message (you might want to add a toast notification)
      console.log('Confirmation code resent successfully');
    }
  };

  const getErrorMessage = (error, code) => {
    switch (code) {
      case 'UsernameExistsException':
        return 'An account with this username already exists.';
      case 'InvalidParameterException':
        return 'Please check your input and try again.';
      case 'InvalidPasswordException':
        return 'Password does not meet requirements.';
      case 'CodeMismatchException':
        return 'Invalid confirmation code. Please try again.';
      case 'ExpiredCodeException':
        return 'Confirmation code has expired. Please request a new one.';
      case 'LimitExceededException':
        return 'Too many attempts. Please try again later.';
      default:
        return error || 'An error occurred. Please try again.';
    }
  };

  if (step === 'confirm') {
    return (
      <div className="signup-form">
        <div className="signup-form__header">
          <h2>Confirm Your Account</h2>
          <p>We've sent a confirmation code to {formData.email}</p>
        </div>

        <form onSubmit={handleConfirmSubmit} className="signup-form__form">
          <div className="form-group">
            <label htmlFor="confirmationCode" className="form-label">
              Confirmation Code
            </label>
            <input
              type="text"
              id="confirmationCode"
              name="confirmationCode"
              value={confirmationCode}
              onChange={handleConfirmationCodeChange}
              className={`form-input ${formErrors.confirmationCode ? 'form-input--error' : ''}`}
              placeholder="Enter 6-digit code"
              disabled={loading}
              maxLength={6}
            />
            {formErrors.confirmationCode && (
              <span className="form-error">{formErrors.confirmationCode}</span>
            )}
          </div>

          {error && (
            <div className="form-error-message">
              {getErrorMessage(error)}
            </div>
          )}

          <button
            type="submit"
            className="btn btn--primary btn--full-width"
            disabled={loading}
          >
            {loading ? (
              <>
                <LoadingSpinner size="small" />
                <span>Confirming...</span>
              </>
            ) : (
              'Confirm Account'
            )}
          </button>

          <button
            type="button"
            className="btn btn--secondary btn--full-width"
            onClick={handleResendCode}
            disabled={loading}
          >
            Resend Code
          </button>
        </form>

      </div>
    );
  }

  return (
    <div className="signup-form">
      <div className="signup-form__header">
        <h2>Create Your iCode Account</h2>
        <p>Join the platform and start building amazing projects</p>
      </div>

      <form onSubmit={handleSignUpSubmit} className="signup-form__form">
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="firstName" className="form-label">
              First Name
            </label>
            <input
              type="text"
              id="firstName"
              name="firstName"
              value={formData.firstName}
              onChange={handleInputChange}
              className={`form-input ${formErrors.firstName ? 'form-input--error' : ''}`}
              placeholder="First name"
              disabled={loading}
            />
            {formErrors.firstName && (
              <span className="form-error">{formErrors.firstName}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="lastName" className="form-label">
              Last Name
            </label>
            <input
              type="text"
              id="lastName"
              name="lastName"
              value={formData.lastName}
              onChange={handleInputChange}
              className={`form-input ${formErrors.lastName ? 'form-input--error' : ''}`}
              placeholder="Last name"
              disabled={loading}
            />
            {formErrors.lastName && (
              <span className="form-error">{formErrors.lastName}</span>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="username" className="form-label">
            Username
          </label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleInputChange}
            className={`form-input ${formErrors.username ? 'form-input--error' : ''}`}
            placeholder="Choose a username"
            disabled={loading}
            autoComplete="username"
          />
          {formErrors.username && (
            <span className="form-error">{formErrors.username}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="email" className="form-label">
            Email Address
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            className={`form-input ${formErrors.email ? 'form-input--error' : ''}`}
            placeholder="Enter your email"
            disabled={loading}
            autoComplete="email"
          />
          {formErrors.email && (
            <span className="form-error">{formErrors.email}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="password" className="form-label">
            Password
          </label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            className={`form-input ${formErrors.password ? 'form-input--error' : ''}`}
            placeholder="Create a strong password"
            disabled={loading}
            autoComplete="new-password"
          />
          {formErrors.password && (
            <span className="form-error">{formErrors.password}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword" className="form-label">
            Confirm Password
          </label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleInputChange}
            className={`form-input ${formErrors.confirmPassword ? 'form-input--error' : ''}`}
            placeholder="Confirm your password"
            disabled={loading}
            autoComplete="new-password"
          />
          {formErrors.confirmPassword && (
            <span className="form-error">{formErrors.confirmPassword}</span>
          )}
        </div>

        {error && (
          <div className="form-error-message">
            {getErrorMessage(error)}
          </div>
        )}

        <button
          type="submit"
          className="btn btn--primary btn--full-width"
          disabled={loading}
        >
          {loading ? (
            <>
              <LoadingSpinner size="small" />
              <span>Creating Account...</span>
            </>
          ) : (
            'Create Account'
          )}
        </button>
      </form>

      <div className="signup-form__footer">
        <p>
          Already have an account?{' '}
          <button
            type="button"
            className="link-button"
            onClick={onSwitchToSignIn}
            disabled={loading}
          >
            Sign In
          </button>
        </p>
      </div>

      <style jsx>{`
        .signup-form {
          max-width: 500px;
          margin: 0 auto;
          padding: 2rem;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .signup-form__header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .signup-form__header h2 {
          margin: 0 0 0.5rem 0;
          color: #1a1a1a;
          font-size: 1.5rem;
          font-weight: 600;
        }

        .signup-form__header p {
          margin: 0;
          color: #666;
          font-size: 0.9rem;
        }

        .signup-form__form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .form-label {
          font-weight: 500;
          color: #333;
          font-size: 0.9rem;
        }

        .form-input {
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .form-input:focus {
          outline: none;
          border-color: #007bff;
          box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }

        .form-input--error {
          border-color: #dc3545;
        }

        .form-input--error:focus {
          border-color: #dc3545;
          box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.25);
        }

        .form-input:disabled {
          background-color: #f8f9fa;
          cursor: not-allowed;
        }

        .form-error {
          color: #dc3545;
          font-size: 0.8rem;
          margin-top: 0.25rem;
        }

        .form-error-message {
          padding: 0.75rem;
          background-color: #f8d7da;
          border: 1px solid #f5c6cb;
          border-radius: 4px;
          color: #721c24;
          font-size: 0.9rem;
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 4px;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s, transform 0.1s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .btn:hover:not(:disabled) {
          transform: translateY(-1px);
        }

        .btn:disabled {
          cursor: not-allowed;
          opacity: 0.6;
        }

        .btn--primary {
          background-color: #007bff;
          color: white;
        }

        .btn--primary:hover:not(:disabled) {
          background-color: #0056b3;
        }

        .btn--secondary {
          background-color: #6c757d;
          color: white;
        }

        .btn--secondary:hover:not(:disabled) {
          background-color: #545b62;
        }

        .btn--full-width {
          width: 100%;
        }

        .signup-form__footer {
          text-align: center;
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #eee;
        }

        .signup-form__footer p {
          margin: 0;
          color: #666;
          font-size: 0.9rem;
        }

        .link-button {
          background: none;
          border: none;
          color: #007bff;
          cursor: pointer;
          text-decoration: underline;
          font-size: inherit;
        }

        .link-button:hover:not(:disabled) {
          color: #0056b3;
        }

        .link-button:disabled {
          color: #6c757d;
          cursor: not-allowed;
        }

        @media (max-width: 600px) {
          .form-row {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};