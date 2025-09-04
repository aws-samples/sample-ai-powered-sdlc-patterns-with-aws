// Admin Dashboard Component
// Main administrative dashboard with Knowledge Base management

import { motion } from 'framer-motion';
import {
    AlertTriangle,
    BarChart3,
    CheckCircle,
    Database,
    RefreshCw,
    Settings,
    TrendingUp
} from 'lucide-react';
import React, { useState } from 'react';

// Import admin components
import { IngestionJobs } from './IngestionJobs';
import { KnowledgeBaseMetrics } from './KnowledgeBaseMetrics';
import { KnowledgeBaseStatus } from './KnowledgeBaseStatus';

interface AdminDashboardProps {
  className?: string;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ className = '' }) => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const handleGlobalRefresh = () => {
    setRefreshKey(prev => prev + 1);
    setLastRefresh(new Date());
  };

  const handleJobStart = () => {
    // Refresh all components when a new job starts
    setTimeout(() => {
      setRefreshKey(prev => prev + 1);
    }, 2000); // Give the job a moment to start
  };

  return (
    <div className={`w-full max-w-none ${className}`}>
      {/* Dashboard Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-3">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 shadow-lg">
              <BarChart3 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">Admin Dashboard</h1>
              <p className="text-white/60">Knowledge Base Management & Analytics</p>
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
              <span className="text-white font-medium">Refresh All</span>
            </button>
          </div>
        </div>
      </motion.div>

      {/* Dashboard Grid */}
      <div className="space-y-6">
        {/* Top Row - Status and Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          {/* Knowledge Base Status - Takes 2 columns on large screens */}
          <div className="lg:col-span-2">
            <KnowledgeBaseStatus 
              key={`status-${refreshKey}`}
              onRefresh={() => setLastRefresh(new Date())}
            />
          </div>
          
          {/* Quick Actions Panel */}
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
            <div className="flex items-center space-x-3 mb-4">
              <Settings className="w-6 h-6 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Quick Actions</h3>
            </div>
            
            <div className="space-y-3">
              <button className="w-full flex items-center justify-between p-3 bg-gray-700/30 hover:bg-gray-700/50 rounded-lg transition-colors border border-gray-600/30">
                <div className="flex items-center space-x-3">
                  <Database className="w-4 h-4 text-blue-400" />
                  <span className="text-white text-sm">Manage Data Sources</span>
                </div>
                <span className="text-white/60">→</span>
              </button>
              
              <button className="w-full flex items-center justify-between p-3 bg-gray-700/30 hover:bg-gray-700/50 rounded-lg transition-colors border border-gray-600/30">
                <div className="flex items-center space-x-3">
                  <TrendingUp className="w-4 h-4 text-green-400" />
                  <span className="text-white text-sm">View Analytics</span>
                </div>
                <span className="text-white/60">→</span>
              </button>
              
              <button className="w-full flex items-center justify-between p-3 bg-gray-700/30 hover:bg-gray-700/50 rounded-lg transition-colors border border-gray-600/30">
                <div className="flex items-center space-x-3">
                  <AlertTriangle className="w-4 h-4 text-yellow-400" />
                  <span className="text-white text-sm">System Health</span>
                </div>
                <span className="text-white/60">→</span>
              </button>
              
              <button className="w-full flex items-center justify-between p-3 bg-gray-700/30 hover:bg-gray-700/50 rounded-lg transition-colors border border-gray-600/30">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-white text-sm">Audit Logs</span>
                </div>
                <span className="text-white/60">→</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* Middle Row - Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <KnowledgeBaseMetrics 
            key={`metrics-${refreshKey}`}
            onRefresh={() => setLastRefresh(new Date())}
          />
        </motion.div>

        {/* Bottom Row - Ingestion Jobs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <IngestionJobs 
            key={`jobs-${refreshKey}`}
            onJobStart={handleJobStart}
          />
        </motion.div>
      </div>

      {/* Footer Info */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-8 text-center"
      >
        <div className="inline-flex items-center space-x-2 px-4 py-2 bg-gray-800/30 rounded-lg border border-gray-700/30">
          <Database className="w-4 h-4 text-blue-400" />
          <span className="text-white/60 text-sm">
            Powered by Amazon Bedrock Knowledge Base
          </span>
        </div>
      </motion.div>
    </div>
  );
};