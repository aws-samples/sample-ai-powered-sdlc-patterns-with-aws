import React, { useState, useEffect } from 'react';
import { LoginForm } from './LoginForm';
import { UserProfile } from './UserProfile';
import { useAuth } from '../../contexts/AuthContext';

export const AuthModal = ({ 
  isOpen, 
  onClose, 
  initialMode = 'signin', // 'signin', 'profile'
  showCloseButton = true 
}) => {
  const { isAuthenticated } = useAuth();
  const [mode, setMode] = useState(initialMode);

  // Reset mode when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setMode(isAuthenticated ? 'profile' : 'signin');
    }
  }, [isOpen, isAuthenticated]);

  // Close modal when user becomes authenticated (unless showing profile)
  useEffect(() => {
    if (isAuthenticated && mode !== 'profile' && isOpen) {
      onClose?.();
    }
  }, [isAuthenticated, mode, isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const handleSuccess = () => {
    if (mode === 'profile') {
      onClose?.();
    } else {
      // For signin/signup, either close or switch to profile
      onClose?.();
    }
  };

  const handleSwitchMode = (newMode) => {
    setMode(newMode);
  };

  const renderContent = () => {
    if (isAuthenticated && mode === 'profile') {
      return (
        <UserProfile onClose={handleSuccess} />
      );
    }

    // Only show login form - signup redirects to dedicated page
    return (
      <LoginForm
        onSuccess={handleSuccess}
      />
    );
  };

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        {showCloseButton && (
          <button
            className="auth-modal__close"
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        )}
        <div className="auth-modal__content">
          {renderContent()}
        </div>
      </div>

      <style jsx>{`
        .auth-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
          padding: 1rem;
          backdrop-filter: blur(2px);
        }

        .auth-modal {
          position: relative;
          background: white;
          border-radius: 8px;
          max-width: 500px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
          animation: modalSlideIn 0.3s ease-out;
        }

        @keyframes modalSlideIn {
          from {
            opacity: 0;
            transform: translateY(-20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }

        .auth-modal__close {
          position: absolute;
          top: 1rem;
          right: 1rem;
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          color: #666;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background-color 0.2s, color 0.2s;
          z-index: 10;
        }

        .auth-modal__close:hover {
          background: #f0f0f0;
          color: #333;
        }

        .auth-modal__content {
          padding: 0;
        }

        /* Responsive design */
        @media (max-width: 600px) {
          .auth-modal {
            margin: 0.5rem;
            max-width: none;
            width: calc(100% - 1rem);
          }
        }
      `}</style>
    </div>
  );
};

// Hook for managing auth modal state
export const useAuthModal = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState('signin');

  const openModal = (initialMode = 'signin') => {
    setMode(initialMode === 'signup' ? 'signin' : initialMode); // Redirect signup to signin
    setIsOpen(true);
  };

  const closeModal = () => {
    setIsOpen(false);
  };

  const switchMode = (newMode) => {
    setMode(newMode === 'signup' ? 'signin' : newMode); // Redirect signup to signin
  };

  return {
    isOpen,
    mode,
    openModal,
    closeModal,
    switchMode,
    // Convenience methods
    openSignIn: () => openModal('signin'),
    openProfile: () => openModal('profile')
  };
};