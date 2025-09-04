// Knowledge Base Metrics Component
// Displays comprehensive metrics and analytics for the Knowledge Base

import { API_CONFIG } from '@/config/aws-config';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import {
    Activity,
    AlertTriangle,
    BarChart3,
    CheckCircle,
    Clock,
    FileText,
    MessageCircle,
    RefreshCw,
    TrendingUp,
    Users
} from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface KnowledgeBaseMetrics {
  totalDocuments: number;
  totalQueries: number;
  averageResponseTime: number;
  successRate: number;
  documentsProcessedToday: number;
  queriesProcessedToday: number;
  activeUsers: number;
  failedIngestions: number;
  storageUsed: string;
  lastUpdated: string;
  queryTrends: {
    period: string;
    count: number;
  }[];
  documentTrends: {
    period: string;
    count: number;
  }[];
}

interface KnowledgeBaseMetricsProps {
  onRefresh?: () => void;
}

export const KnowledgeBaseMetrics: React.FC<KnowledgeBaseMetricsProps> = ({ onRefresh }) => {
  const { authState } = useAuth();
  const [metrics, setMetrics] = useState<KnowledgeBaseMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMetrics = async () => {
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
        `${API_CONFIG.baseURL}/admin/knowledge-base/metrics`,
        {
          method: 'GET',
          headers: {
            'Authorization': idToken,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.status}`);
      }

      const result = await response.json();
      setMetrics(result.data?.data || result.data);
      
    } catch (err: any) {
      console.error('Error fetching Knowledge Base metrics:', err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchMetrics();
    onRefresh?.();
  };

  useEffect(() => {
    fetchMetrics();
    
    // Set up auto-refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatNumber = (num: number | undefined | null): string => {
    if (num === undefined || num === null || isNaN(num)) return '0';
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const formatResponseTime = (ms: number | undefined | null): string => {
    if (ms === undefined || ms === null || isNaN(ms)) return '0ms';
    if (ms >= 1000) {
      return (ms / 1000).toFixed(1) + 's';
    }
    return ms.toFixed(0) + 'ms';
  };

  if (loading) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center space-x-3 mb-4">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Base Metrics</h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
          <span className="ml-2 text-white/60">Loading metrics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-6 h-6 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">Knowledge Base Metrics</h3>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 text-white ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="flex items-center space-x-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>Error loading metrics: {error}</span>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center space-x-3 mb-4">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Base Metrics</h3>
        </div>
        <div className="text-white/60">No metrics data available</div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Base Metrics</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 text-white ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Documents */}
        <div className="bg-gray-700/30 rounded-lg p-4 border border-gray-600/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm">Total Documents</p>
              <p className="text-2xl font-bold text-white">{formatNumber(metrics.totalDocuments)}</p>
              <p className="text-green-400 text-xs">+{formatNumber(metrics.documentsProcessedToday)} today</p>
            </div>
            <FileText className="w-8 h-8 text-blue-400" />
          </div>
        </div>

        {/* Total Queries */}
        <div className="bg-gray-700/30 rounded-lg p-4 border border-gray-600/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm">Total Queries</p>
              <p className="text-2xl font-bold text-white">{formatNumber(metrics.totalQueries)}</p>
              <p className="text-green-400 text-xs">+{formatNumber(metrics.queriesProcessedToday)} today</p>
            </div>
            <MessageCircle className="w-8 h-8 text-green-400" />
          </div>
        </div>

        {/* Average Response Time */}
        <div className="bg-gray-700/30 rounded-lg p-4 border border-gray-600/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm">Avg Response Time</p>
              <p className="text-2xl font-bold text-white">{formatResponseTime(metrics.averageResponseTime)}</p>
              <p className="text-yellow-400 text-xs">Last 24h</p>
            </div>
            <Clock className="w-8 h-8 text-yellow-400" />
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-gray-700/30 rounded-lg p-4 border border-gray-600/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm">Success Rate</p>
              <p className="text-2xl font-bold text-white">{(metrics.successRate || 0).toFixed(1)}%</p>
              <p className="text-green-400 text-xs">Last 24h</p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Active Users */}
        <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600/30">
          <div className="flex items-center space-x-3">
            <Users className="w-5 h-5 text-purple-400" />
            <div>
              <p className="text-white/60 text-xs">Active Users</p>
              <p className="text-lg font-semibold text-white">{formatNumber(metrics.activeUsers)}</p>
            </div>
          </div>
        </div>

        {/* Failed Ingestions */}
        <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600/30">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <div>
              <p className="text-white/60 text-xs">Failed Ingestions</p>
              <p className="text-lg font-semibold text-white">{formatNumber(metrics.failedIngestions)}</p>
            </div>
          </div>
        </div>

        {/* Storage Used */}
        <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600/30">
          <div className="flex items-center space-x-3">
            <Activity className="w-5 h-5 text-cyan-400" />
            <div>
              <p className="text-white/60 text-xs">Storage Used</p>
              <p className="text-lg font-semibold text-white">{metrics.storageUsed || 'N/A'}</p>
            </div>
          </div>
        </div>

        {/* Last Updated */}
        <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600/30">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-white/60 text-xs">Last Updated</p>
              <p className="text-sm font-medium text-white">
                {metrics.lastUpdated ? new Date(metrics.lastUpdated).toLocaleTimeString() : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Trends Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Query Trends */}
        <div className="bg-gray-700/20 rounded-lg p-4 border border-gray-600/20">
          <h4 className="text-white font-medium mb-3 flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span>Query Trends (7 days)</span>
          </h4>
          <div className="space-y-2">
            {(metrics.queryTrends || []).map((trend, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <span className="text-white/60">{trend.period || 'N/A'}</span>
                <span className="text-white font-medium">{formatNumber(trend.count)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Document Trends */}
        <div className="bg-gray-700/20 rounded-lg p-4 border border-gray-600/20">
          <h4 className="text-white font-medium mb-3 flex items-center space-x-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span>Document Trends (7 days)</span>
          </h4>
          <div className="space-y-2">
            {(metrics.documentTrends || []).map((trend, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <span className="text-white/60">{trend.period || 'N/A'}</span>
                <span className="text-white font-medium">{formatNumber(trend.count)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
};