import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';

export const LoginForm = ({ onSuccess, onSwitchToSignUp }) => {
  const { signIn, loading, error, clearError } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
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

  const validateForm = () => {
    const errors = {};
    
    if (!formData.username.trim()) {
      errors.username = 'Username or email is required';
    }
    
    if (!formData.password) {
      errors.password = 'Password is required';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    const result = await signIn(formData.username, formData.password);
    
    if (result.success) {
      onSuccess?.();
      
      // Refresh the page after successful login
      setTimeout(() => {
        window.location.reload();
      }, 100);
    }
    // Error handling is managed by the auth context
  };

  const getErrorMessage = (error, code) => {
    switch (code) {
      case 'UserNotConfirmedException':
        return 'Please check your email and confirm your account before signing in.';
      case 'NotAuthorizedException':
        return 'Invalid username or password. Please try again.';
      case 'UserNotFoundException':
        return 'No account found with this username or email.';
      case 'TooManyRequestsException':
        return 'Too many failed attempts. Please try again later.';
      case 'PasswordResetRequiredException':
        return 'Password reset is required. Please contact support.';
      default:
        return error || 'Sign in failed. Please try again.';
    }
  };

  return (
    <div className="login-form">
      <div className="login-form__header">
        <h2>Sign In</h2>
        <p>Access your projects and continue building</p>
      </div>

      <form onSubmit={handleSubmit} className="login-form__form">
        <div className="form-group">
          <label htmlFor="username" className="form-label">
            Username or Email
          </label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleInputChange}
            className={`form-input ${formErrors.username ? 'form-input--error' : ''}`}
            placeholder="Enter your username or email"
            disabled={loading}
            autoComplete="username"
          />
          {formErrors.username && (
            <span className="form-error">{formErrors.username}</span>
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
            placeholder="Enter your password"
            disabled={loading}
            autoComplete="current-password"
          />
          {formErrors.password && (
            <span className="form-error">{formErrors.password}</span>
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
              <span>Signing In...</span>
            </>
          ) : (
            'Sign In'
          )}
        </button>
      </form>

      <div className="login-form__footer">
        <p>
          Don't have an account?{' '}
          <a
            href="/signup"
            className="link-button"
            style={{ textDecoration: 'underline', color: '#007bff' }}
          >
            Sign Up
          </a>
        </p>
      </div>

      <style jsx>{`
        .login-form {
          max-width: 400px;
          margin: 0 auto;
          padding: 2rem;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .login-form__header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .login-form__header h2 {
          margin: 0 0 0.5rem 0;
          color: #1a1a1a;
          font-size: 1.5rem;
          font-weight: 600;
        }

        .login-form__header p {
          margin: 0;
          color: #666;
          font-size: 0.9rem;
        }

        .login-form__form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
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

        .btn--full-width {
          width: 100%;
        }

        .login-form__footer {
          text-align: center;
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #eee;
        }

        .login-form__footer p {
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
      `}</style>
    </div>
  );
};