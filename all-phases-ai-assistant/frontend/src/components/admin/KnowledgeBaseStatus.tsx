// Knowledge Base Status Component
// Displays Knowledge Base health and status information

import { API_CONFIG } from '@/config/aws-config';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import {
    Activity,
    AlertCircle,
    CheckCircle,
    Clock,
    Database,
    FileText,
    RefreshCw
} from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface KnowledgeBaseStatus {
  knowledgeBaseId: string;
  status: string;
  dataSourceStatus: string;
  lastSyncTime: string;
  documentCount: number;
  vectorIndexStatus: string;
  embeddingModel: string;
}

interface KnowledgeBaseStatusProps {
  onRefresh?: () => void;
}

export const KnowledgeBaseStatus: React.FC<KnowledgeBaseStatusProps> = ({ onRefresh }) => {
  const { authState } = useAuth();
  const [status, setStatus] = useState<KnowledgeBaseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async () => {
    try {
      setError(null);
      
      // Get ID token from authState or fallback to localStorage
      let idToken = authState.idToken;
      if (!idToken) {
        const tokenKey = Object.keys(localStorage).find(key => 
          key.includes('CognitoIdentityServiceProvider') && key.includes('idToken')
        );
        idToken = tokenKey ? localStorage.getItem(tokenKey) || undefined : undefined;
      }

      if (!idToken) {
        throw new Error('No authentication token found');
      }

      const response = await fetch(
        `${API_CONFIG.baseURL}/admin/knowledge-base/status`,
        {
          method: 'GET',
          headers: {
            'Authorization': idToken,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.status}`);
      }

      const result = await response.json();
      setStatus(result.data?.data || result.data);
      
    } catch (err: any) {
      console.error('Error fetching Knowledge Base status:', err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchStatus();
    onRefresh?.();
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const getStatusIcon = (statusValue: string) => {
    if (!statusValue || typeof statusValue !== 'string') return <Activity className="w-5 h-5 text-gray-400" />;
    switch (statusValue.toUpperCase()) {
      case 'ACTIVE':
      case 'AVAILABLE':
      case 'COMPLETE':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'CREATING':
      case 'UPDATING':
      case 'IN_PROGRESS':
        return <Clock className="w-5 h-5 text-yellow-400" />;
      case 'FAILED':
      case 'ERROR':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Activity className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (statusValue: string) => {
    if (!statusValue || typeof statusValue !== 'string') return 'text-gray-400';
    switch (statusValue.toUpperCase()) {
      case 'ACTIVE':
      case 'AVAILABLE':
      case 'COMPLETE':
        return 'text-green-400';
      case 'CREATING':
      case 'UPDATING':
      case 'IN_PROGRESS':
        return 'text-yellow-400';
      case 'FAILED':
      case 'ERROR':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center space-x-3 mb-4">
          <Database className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Base Status</h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
          <span className="ml-2 text-white/60">Loading status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center space-x-3 mb-4">
          <Database className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Base Status</h3>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ml-auto p-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 text-white ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="flex items-center space-x-2 text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Error loading status: {error}</span>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center space-x-3 mb-4">
          <Database className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Base Status</h3>
        </div>
        <div className="text-white/60">No status information available</div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50"
      data-testid="knowledge-base-status"
    >
      <div className="flex items-center space-x-3 mb-6">
        <Database className="w-6 h-6 text-blue-400" />
        <h3 className="text-lg font-semibold text-white">Knowledge Base Status</h3>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="ml-auto p-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 text-white ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Knowledge Base Status */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-white/60">Knowledge Base</span>
            <div className="flex items-center space-x-2">
              {getStatusIcon(status.status)}
              <span className={`font-medium ${getStatusColor(status.status)}`}>
                {status.status || 'Unknown'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-white/60">Data Source</span>
            <div className="flex items-center space-x-2">
              {getStatusIcon(status.dataSourceStatus)}
              <span className={`font-medium ${getStatusColor(status.dataSourceStatus)}`}>
                {status.dataSourceStatus || 'Unknown'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-white/60">Vector Index</span>
            <div className="flex items-center space-x-2">
              {getStatusIcon(status.vectorIndexStatus)}
              <span className={`font-medium ${getStatusColor(status.vectorIndexStatus)}`}>
                {status.vectorIndexStatus || 'Unknown'}
              </span>
            </div>
          </div>
        </div>

        {/* Metrics */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-white/60">Documents</span>
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-blue-400" />
              <span className="font-medium text-white">{status.documentCount || 0}</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-white/60">Last Sync</span>
            <span className="font-medium text-white">
              {status.lastSyncTime ? new Date(status.lastSyncTime).toLocaleString() : 'N/A'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-white/60">KB ID</span>
            <span className="font-mono text-sm text-white/80">
              {status.knowledgeBaseId || 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* Embedding Model Info */}
      <div className="mt-4 pt-4 border-t border-gray-700/50">
        <div className="flex items-center justify-between">
          <span className="text-white/60">Embedding Model</span>
          <span className="font-mono text-sm text-white/80">
            {status.embeddingModel && typeof status.embeddingModel === 'string' ? status.embeddingModel.split('/').pop() : 'N/A'}
          </span>
        </div>
      </div>
    </motion.div>
  );
};