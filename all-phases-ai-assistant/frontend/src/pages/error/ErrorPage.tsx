// Generic Error Page
// Displays for general application errors

import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { AlertTriangle, Home, RefreshCw } from 'lucide-react';
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export const ErrorPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const error = (location.state as any)?.error;
  const errorMessage = (location.state as any)?.message || 'An unexpected error occurred';

  const handleRetry = () => {
    window.location.reload();
  };

  const handleGoHome = () => {
    navigate(ROUTES.HOME);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-4">
      <div className="max-w-md w-full text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200 }}
          className="mb-8"
        >
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-500/20 border border-red-500/30">
            <AlertTriangle className="w-10 h-10 text-red-400" />
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
              Something went wrong
            </h1>
            <p className="text-white/60">
              {errorMessage}
            </p>
          </div>

          {error && process.env.NODE_ENV === 'development' && (
            <div className="text-left bg-black/20 border border-red-500/30 rounded-lg p-4 text-sm text-red-200 font-mono">
              <div className="font-bold mb-2">Error Details:</div>
              <div className="whitespace-pre-wrap break-all">
                {error.toString()}
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <motion.button
              onClick={handleRetry}
              className="flex items-center justify-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-xl shadow-lg transition-all duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <RefreshCw className="w-4 h-4" />
              <span>Try Again</span>
            </motion.button>

            <motion.button
              onClick={handleGoHome}
              className="flex items-center justify-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold rounded-xl transition-all duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Home className="w-4 h-4" />
              <span>Go Home</span>
            </motion.button>
          </div>

          <p className="text-white/40 text-sm">
            If the problem persists, please contact support.
          </p>
        </motion.div>
      </div>
    </div>
  );
};