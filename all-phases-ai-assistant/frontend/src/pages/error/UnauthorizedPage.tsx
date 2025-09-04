// Unauthorized Access Page
// Displays when user doesn't have required permissions

import { useAuth } from '@/components/auth/AuthContext';
import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { ArrowLeft, Home, Shield } from 'lucide-react';
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export const UnauthorizedPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { authState } = useAuth();

  const handleGoBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(ROUTES.HOME);
    }
  };

  const handleGoHome = () => {
    navigate(ROUTES.HOME);
  };

  const attemptedPath = (location.state as any)?.from || 'this resource';

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-4">
      <div className="max-w-md w-full text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200 }}
          className="mb-8"
        >
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-orange-500/20 border border-orange-500/30">
            <Shield className="w-10 h-10 text-orange-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="space-y-6"
        >
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              Access Denied
            </h1>
            <p className="text-white/60">
              You don't have permission to access {attemptedPath}. 
              {authState.user?.['custom:role'] === 'user' && 
                ' This resource requires administrator privileges.'
              }
            </p>
          </div>

          {authState.user && (
            <div className="bg-white/10 border border-white/20 rounded-lg p-4 text-left">
              <h3 className="text-white font-semibold mb-2">Your Account</h3>
              <div className="space-y-1 text-sm text-white/70">
                <p><span className="font-medium">Email:</span> {authState.user.email}</p>
                <p><span className="font-medium">Role:</span> {authState.user['custom:role']}</p>
                {authState.user['custom:department'] && (
                  <p><span className="font-medium">Department:</span> {authState.user['custom:department']}</p>
                )}
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <motion.button
              onClick={handleGoBack}
              className="flex items-center justify-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold rounded-xl transition-all duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Go Back</span>
            </motion.button>

            <motion.button
              onClick={handleGoHome}
              className="flex items-center justify-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-xl shadow-lg transition-all duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Home className="w-4 h-4" />
              <span>Go Home</span>
            </motion.button>
          </div>

          <p className="text-white/40 text-sm">
            If you believe you should have access to this resource, please contact your administrator.
          </p>
        </motion.div>
      </div>
    </div>
  );
};