// OAuth Callback Page
// Handles OAuth redirect and authentication completion

import { useAuth } from '@/components/auth/AuthContext';
import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { AlertCircle, Shield } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { Navigate, useLocation, useSearchParams } from 'react-router-dom';

export const CallbackPage: React.FC = () => {
  const { authState } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | undefined>();
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      try {
        // Check for OAuth error parameters
        const errorParam = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');
        
        if (errorParam) {
          setError(errorDescription || 'Authentication failed');
          setIsProcessing(false);
          return;
        }

        // Check for authorization code
        const code = searchParams.get('code');
        if (!code) {
          setError('No authorization code received');
          setIsProcessing(false);
          return;
        }

        // Let Amplify handle the OAuth callback
        // The AuthContext will automatically update when authentication completes
        setTimeout(() => {
          setIsProcessing(false);
        }, 3000);

      } catch (err: any) {
        console.error('Callback processing error:', err);
        setError(err.message || 'Authentication callback failed');
        setIsProcessing(false);
      }
    };

    processCallback();
  }, [searchParams]);

  // Redirect if authenticated
  if (authState.isAuthenticated) {
    const from = (location.state as any)?.from || ROUTES.HOME;
    return <Navigate to={from} replace />;
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center max-w-md mx-auto p-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
            className="mb-8"
          >
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-500/20 border border-red-500/30">
              <AlertCircle className="w-10 h-10 text-red-400" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="space-y-4"
          >
            <h1 className="text-3xl font-bold text-white">Authentication Failed</h1>
            <p className="text-white/60">{error}</p>
            
            <motion.button
              onClick={() => window.location.href = ROUTES.LOGIN}
              className="mt-6 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-xl shadow-lg transition-all duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Return to Login
            </motion.button>
          </motion.div>
        </div>
      </div>
    );
  }

  // Show processing state
  if (isProcessing) {
    return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, delay: 0.1 }}
          className="mb-8"
        >
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-purple-500/20 border border-purple-500/30">
            <Shield className="w-10 h-10 text-purple-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="space-y-4"
        >
          <h1 className="text-3xl font-bold text-white">Completing Authentication</h1>
          <p className="text-white/60 max-w-md mx-auto">
            Please wait while we securely complete your authentication...
          </p>

          <div className="flex items-center justify-center mt-8">
            <div className="w-8 h-8 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin"></div>
          </div>
        </motion.div>
      </div>
    </div>
    );
  }

  return null;
};