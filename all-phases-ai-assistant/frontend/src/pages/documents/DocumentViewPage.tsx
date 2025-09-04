// Document View Page Component
// Individual document viewer

import { motion } from 'framer-motion';
import { Eye } from 'lucide-react';
import React from 'react';

export const DocumentViewPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto text-center space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="space-y-4"
      >
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-500 shadow-lg">
          <Eye className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white">Document View</h1>
        <p className="text-white/60">This page will be implemented in a future task</p>
      </motion.div>
    </div>
  );
};