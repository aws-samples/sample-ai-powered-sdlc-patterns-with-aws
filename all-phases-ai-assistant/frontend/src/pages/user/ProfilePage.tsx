// User Profile Page
// Displays user information and account settings

import { useAuth } from '@/components/auth/AuthContext';
import { motion } from 'framer-motion';
import { Calendar, Mail, Settings, Shield, User } from 'lucide-react';
import React from 'react';

export const ProfilePage: React.FC = () => {
  const { authState } = useAuth();

  if (!authState.user) {
    return (
      <div className="max-w-2xl mx-auto text-center">
        <p className="text-white/60">User information not available</p>
      </div>
    );
  }

  const userInfo = [
    {
      label: 'Email Address',
      value: authState.user.email,
      icon: Mail,
      verified: authState.user.email_verified
    },
    {
      label: 'User ID',
      value: authState.user.sub,
      icon: User
    },
    {
      label: 'Username',
      value: authState.user['cognito:username'],
      icon: User
    },
    {
      label: 'Role',
      value: authState.user['custom:role'],
      icon: Shield,
      badge: true
    }
  ];

  if (authState.user['custom:department']) {
    userInfo.push({
      label: 'Department',
      value: authState.user['custom:department'],
      icon: Settings
    });
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center space-y-4"
      >
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 shadow-lg">
          <User className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white">User Profile</h1>
        <p className="text-white/60">Manage your account information and preferences</p>
      </motion.div>

      {/* Profile Information */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl p-8"
      >
        <h2 className="text-xl font-semibold text-white mb-6">Account Information</h2>
        
        <div className="space-y-6">
          {userInfo.map((info, index) => (
            <motion.div
              key={info.label}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + index * 0.1, duration: 0.5 }}
              className="flex items-center justify-between py-4 border-b border-white/10 last:border-b-0"
            >
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/10">
                  <info.icon className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-white/60">{info.label}</p>
                  <div className="flex items-center space-x-2">
                    <p className="text-white font-medium">{info.value}</p>
                    {info.verified && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-300 border border-green-500/30">
                        Verified
                      </span>
                    )}
                    {info.badge && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30 capitalize">
                        {info.value}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Session Information */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.6 }}
        className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl p-8"
      >
        <h2 className="text-xl font-semibold text-white mb-6">Session Information</h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/10">
                <Calendar className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-white/60">Session Expires</p>
                <p className="text-white font-medium">
                  {authState.expiresAt 
                    ? new Date(authState.expiresAt).toLocaleString()
                    : 'Unknown'
                  }
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/10">
                <Shield className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-white/60">Authentication Status</p>
                <div className="flex items-center space-x-2">
                  <p className="text-white font-medium">Active</p>
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-300 border border-green-500/30">
                    Authenticated
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.6 }}
        className="flex flex-col sm:flex-row gap-4 justify-center"
      >
        <motion.button
          onClick={() => window.location.href = '/logout'}
          className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl shadow-lg transition-all duration-200"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          Sign Out
        </motion.button>
      </motion.div>
    </div>
  );
};