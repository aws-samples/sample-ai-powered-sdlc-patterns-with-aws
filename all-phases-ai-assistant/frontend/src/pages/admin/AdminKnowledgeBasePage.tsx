// Admin Knowledge Base Page Component
// Dedicated Knowledge Base management interface

import { IngestionJobs } from '@/components/admin/IngestionJobs';
import { KnowledgeBaseStatus } from '@/components/admin/KnowledgeBaseStatus';
import { motion } from 'framer-motion';
import { Database, RefreshCw } from 'lucide-react';
import React, { useState } from 'react';

export const AdminKnowledgeBasePage: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const handleGlobalRefresh = () => {
    setRefreshKey(prev => prev + 1);
    setLastRefresh(new Date());
  };

  const handleJobStart = () => {
    // Refresh components when a new job starts
    setTimeout(() => {
      setRefreshKey(prev => prev + 1);
    }, 2000);
  };

  return (
    <div className="w-full">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-3">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-violet-500 to-purple-500 shadow-lg">
              <Database className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">Knowledge Base Management</h1>
              <p className="text-white/60">Monitor and manage your Knowledge Base operations</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="text-right">
              <div className="text-xs text-white/60">Last Updated</div>
              <div className="text-sm text-white font-medium">
                {lastRefresh.toLocaleTimeString()}
              </div>
            </div>
            <button
              onClick={handleGlobalRefresh}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4 text-white" />
              <span className="text-white font-medium">Refresh</span>
            </button>
          </div>
        </div>
      </motion.div>

      {/* Content Grid */}
      <div className="space-y-6">
        {/* Knowledge Base Status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <KnowledgeBaseStatus 
            key={`status-${refreshKey}`}
            onRefresh={() => setLastRefresh(new Date())}
          />
        </motion.div>

        {/* Ingestion Jobs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <IngestionJobs 
            key={`jobs-${refreshKey}`}
            onJobStart={handleJobStart}
          />
        </motion.div>
      </div>
    </div>
  );
};