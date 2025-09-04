// Modern Loading Spinner Component
// Provides animated loading indicators with different sizes and styles

import { LoadingSpinnerProps } from '@/types/components';
import { motion } from 'framer-motion';
import React from 'react';

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  color = 'purple',
  text
}) => {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8',
    large: 'w-12 h-12'
  };

  const colorClasses = {
    purple: 'border-purple-400/30 border-t-purple-400',
    white: 'border-white/30 border-t-white',
    blue: 'border-blue-400/30 border-t-blue-400',
    green: 'border-green-400/30 border-t-green-400'
  };

  const textSizeClasses = {
    small: 'text-sm',
    medium: 'text-base',
    large: 'text-lg'
  };

  return (
    <div className="flex flex-col items-center justify-center space-y-3">
      <motion.div
        className={`${sizeClasses[size]} border-2 ${colorClasses[color as keyof typeof colorClasses] || colorClasses.purple} rounded-full animate-spin`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      />
      
      {text && (
        <motion.p
          className={`${textSizeClasses[size]} text-white/70 font-medium`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
        >
          {text}
        </motion.p>
      )}
    </div>
  );
};