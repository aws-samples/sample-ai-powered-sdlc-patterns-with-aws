// Ingestion Jobs Component
// Displays and manages Knowledge Base ingestion jobs

import { API_CONFIG } from '@/config/aws-config';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import {
    Activity,
    AlertCircle,
    CheckCircle,
    Clock,
    FileText,
    Play,
    RefreshCw,
    TrendingUp,
    XCircle
} from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface IngestionJobSummary {
  ingestionJobId: string;
  status: 'STARTING' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED' | 'STOPPING' | 'STOPPED';
  startedAt: string;
  updatedAt: string;
  description?: string;
  failureReasons?: string[];
  statistics?: {
    numberOfDocumentsScanned?: number;
    numberOfNewDocumentsIndexed?: number;
    numberOfModifiedDocumentsIndexed?: number;
    numberOfDocumentsDeleted?: number;
    numberOfDocumentsFailed?: number;
  };
}

interface IngestionJobsProps {
  onJobStart?: () => void;
}

export const IngestionJobs: React.FC<IngestionJobsProps> = ({ onJobStart }) => {
  const { authState } = useAuth();
  const [jobs, setJobs] = useState<IngestionJobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchJobs = async () => {
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

      const url = statusFilter === 'all' 
        ? `${API_CONFIG.baseURL}/admin/knowledge-base/ingestion-jobs`
        : `${API_CONFIG.baseURL}/admin/knowledge-base/ingestion-jobs?status=${statusFilter}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': idToken,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.status}`);
      }

      const result = await response.json();
      const jobsData = result.data?.data || result.data || result;
      const jobs = Array.isArray(jobsData) ? jobsData : [];
      
      // Sort jobs by startedAt timestamp descending (newest first)
      const sortedJobs = [...jobs].sort((a: IngestionJobSummary, b: IngestionJobSummary) => {
        // Parse dates and handle potential parsing issues
        const dateA = new Date(a.startedAt);
        const dateB = new Date(b.startedAt);
        
        // Check for invalid dates
        if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
          console.warn('Invalid date found in ingestion jobs:', { a: a.startedAt, b: b.startedAt });
          return 0; // Keep original order if dates are invalid
        }
        
        // Sort descending (newest first)
        return dateB.getTime() - dateA.getTime();
      });
      
      console.log('Sorted jobs by startedAt:', sortedJobs.map(job => ({ 
        id: job.ingestionJobId, 
        startedAt: job.startedAt,
        parsed: new Date(job.startedAt).toISOString()
      })));
      
      setJobs(sortedJobs);
      
    } catch (err: any) {
      console.error('Error fetching ingestion jobs:', err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const startSync = async () => {
    try {
      setStarting(true);
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
        `${API_CONFIG.baseURL}/admin/knowledge-base/sync`,
        {
          method: 'POST',
          headers: {
            'Authorization': idToken,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `Failed to start sync: ${response.status}`);
      }

      const result = await response.json();
      console.log('Sync started:', result);
      
      // Refresh jobs list
      await fetchJobs();
      onJobStart?.();
      
    } catch (err: any) {
      console.error('Error starting sync:', err);
      setError(err.message);
    } finally {
      setStarting(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchJobs();
  };

  useEffect(() => {
    fetchJobs();
  }, [statusFilter]);

  // Auto-refresh every 10 seconds for active jobs
  useEffect(() => {
    const hasActiveJobs = jobs.some(job => 
      ['STARTING', 'IN_PROGRESS'].includes(job.status)
    );
    
    if (hasActiveJobs) {
      const interval = setInterval(fetchJobs, 10000);
      return () => clearInterval(interval);
    }
    
    return undefined;
  }, [jobs]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETE':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'IN_PROGRESS':
        return <Activity className="w-4 h-4 text-yellow-400 animate-pulse" />;
      case 'STARTING':
        return <Clock className="w-4 h-4 text-yellow-400" />;
      case 'FAILED':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'STOPPED':
      case 'STOPPING':
        return <XCircle className="w-4 h-4 text-gray-400" />;
      default:
        return <Activity className="w-4 h-4 text-blue-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETE':
        return 'text-green-400 bg-green-400/10 border-green-400/20';
      case 'IN_PROGRESS':
      case 'STARTING':
        return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
      case 'FAILED':
        return 'text-red-400 bg-red-400/10 border-red-400/20';
      case 'STOPPED':
      case 'STOPPING':
        return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
      default:
        return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
    }
  };

  const formatDuration = (startTime: string, endTime: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const duration = end.getTime() - start.getTime();
    const minutes = Math.floor(duration / 60000);
    const seconds = Math.floor((duration % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  const getJobProgress = (job: IngestionJobSummary) => {
    if (!job.statistics) return null;
    
    const total = (job.statistics.numberOfDocumentsScanned || 0);
    const processed = (job.statistics.numberOfNewDocumentsIndexed || 0) + 
                     (job.statistics.numberOfModifiedDocumentsIndexed || 0) +
                     (job.statistics.numberOfDocumentsFailed || 0);
    
    if (total === 0) return null;
    return Math.round((processed / total) * 100);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-3">
          <TrendingUp className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Ingestion Jobs</h3>
        </div>
        
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center space-y-3 sm:space-y-0 sm:space-x-3">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-0"
          >
            <option value="all">All Status</option>
            <option value="COMPLETE">Complete</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="FAILED">Failed</option>
            <option value="STARTING">Starting</option>
          </select>
          
          <div className="flex space-x-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              <RefreshCw className={`w-4 h-4 text-white ${refreshing ? 'animate-spin' : ''}`} />
            </button>
            
            <button
              onClick={startSync}
              disabled={starting}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap"
            >
              <Play className={`w-4 h-4 text-white ${starting ? 'animate-pulse' : ''}`} />
              <span className="text-white font-medium">
                {starting ? 'Starting...' : 'Start Sync'}
              </span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-center space-x-2 text-red-400">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
          <span className="ml-2 text-white/60">Loading jobs...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-8 text-white/60">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No ingestion jobs found</p>
          {statusFilter !== 'all' && (
            <p className="text-sm mt-1">Try changing the status filter</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const progress = getJobProgress(job);
            
            return (
              <motion.div
                key={job.ingestionJobId}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-gray-700/30 rounded-lg p-4 border border-gray-600/30 hover:bg-gray-700/40 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 space-y-2 sm:space-y-0">
                  <div className="flex items-center space-x-3 min-w-0">
                    {getStatusIcon(job.status)}
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-sm text-white truncate">
                        {job.ingestionJobId}
                      </div>
                      {job.description && (
                        <div className="text-xs text-white/60 mt-1 truncate">
                          {job.description}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(job.status)} flex-shrink-0`}>
                    {job.status}
                  </div>
                </div>

                {/* Progress Bar for Active Jobs */}
                {progress !== null && ['IN_PROGRESS', 'STARTING'].includes(job.status) && (
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-white/60 mb-1">
                      <span>Progress</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-600/50 rounded-full h-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-white/60">Started</div>
                    <div className="text-white">
                      {new Date(job.startedAt).toLocaleString()}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-white/60">Updated</div>
                    <div className="text-white">
                      {new Date(job.updatedAt).toLocaleString()}
                    </div>
                  </div>
                  
                  {job.status === 'COMPLETE' && (
                    <div>
                      <div className="text-white/60">Duration</div>
                      <div className="text-white">
                        {formatDuration(job.startedAt, job.updatedAt)}
                      </div>
                    </div>
                  )}
                </div>

                {job.statistics && (
                  <div className="mt-3 pt-3 border-t border-gray-600/30">
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
                      <div className="text-center">
                        <div className="text-white/60">Scanned</div>
                        <div className="text-white font-medium">
                          {job.statistics.numberOfDocumentsScanned || 0}
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-white/60">New</div>
                        <div className="text-green-400 font-medium">
                          {job.statistics.numberOfNewDocumentsIndexed || 0}
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-white/60">Modified</div>
                        <div className="text-yellow-400 font-medium">
                          {job.statistics.numberOfModifiedDocumentsIndexed || 0}
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-white/60">Deleted</div>
                        <div className="text-red-400 font-medium">
                          {job.statistics.numberOfDocumentsDeleted || 0}
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-white/60">Failed</div>
                        <div className="text-red-400 font-medium">
                          {job.statistics.numberOfDocumentsFailed || 0}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {job.failureReasons && job.failureReasons.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-600/30">
                    <div className="text-xs text-white/60 mb-2">Failure Reasons:</div>
                    <div className="space-y-1">
                      {job.failureReasons.map((reason, index) => (
                        <div key={index} className="text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">
                          {reason}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};