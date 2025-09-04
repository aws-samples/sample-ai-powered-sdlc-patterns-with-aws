// Logout Page Component
// Handles user logout and displays confirmation

import { useAuth } from '@/components/auth/AuthContext';
import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { CheckCircle, LogOut } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';

export const LogoutPage: React.FC = () => {
  const { authState, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutComplete, setLogoutComplete] = useState(false);

  useEffect(() => {
    const performLogout = async () => {
      if (authState.isAuthenticated && !isLoggingOut && !logoutComplete) {
        setIsLoggingOut(true);
        try {
          await logout();
          setLogoutComplete(true);
          
          // Redirect after a brief delay to show success message
          setTimeout(() => {
            window.location.href = ROUTES.LOGIN;
          }, 2000);
        } catch (error) {
          console.error('Logout error:', error);
          // Even if logout fails, redirect to login
          setTimeout(() => {
            window.location.href = ROUTES.LOGIN;
          }, 1000);
        }
      }
    };

    performLogout();
  }, [authState.isAuthenticated, logout, isLoggingOut, logoutComplete]);

  // If not authenticated, redirect to login
  if (!authState.isAuthenticated && !isLoggingOut && !logoutComplete) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, delay: 0.1 }}
          className="mb-8"
        >
          {logoutComplete ? (
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-500/20 border border-green-500/30">
              <CheckCircle className="w-10 h-10 text-green-400" />
            </div>
          ) : (
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-purple-500/20 border border-purple-500/30">
              <LogOut className="w-10 h-10 text-purple-400" />
            </div>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="space-y-4"
        >
          <h1 className="text-3xl font-bold text-white">
            {logoutComplete ? 'Logged Out Successfully' : 'Signing Out...'}
          </h1>
          
          <p className="text-white/60 max-w-md mx-auto">
            {logoutComplete 
              ? 'You have been securely logged out. Redirecting to login page...'
              : 'Please wait while we securely sign you out of your account.'
            }
          </p>

          {!logoutComplete && (
            <div className="flex items-center justify-center mt-8">
              <div className="w-8 h-8 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin"></div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};