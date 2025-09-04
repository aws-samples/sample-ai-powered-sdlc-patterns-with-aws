// Source Citation Component
// Displays document sources with confidence scores and click handling

import { SourceCitationProps } from '@/types/components';
import { motion } from 'framer-motion';
import { ExternalLink, FileText } from 'lucide-react';
import React, { useState } from 'react';

export const SourceCitation: React.FC<SourceCitationProps> = ({
  sources,
  onSourceClick,
  maxSources = 3,
  showConfidence = true
}) => {
  const [showAll, setShowAll] = useState(false);
  
  if (!sources || sources.length === 0) {
    return null;
  }

  const displayedSources = showAll ? sources : sources.slice(0, maxSources);
  const hasMoreSources = sources.length > maxSources;

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400 bg-green-500/20';
    if (confidence >= 0.6) return 'text-yellow-400 bg-yellow-500/20';
    return 'text-orange-400 bg-orange-500/20';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-2"
    >
      {/* Sources Header */}
      <div className="flex items-center space-x-2">
        <FileText className="w-4 h-4 text-white/60" />
        <span className="text-sm font-medium text-white/80">
          Sources ({sources.length})
        </span>
      </div>

      {/* Source List */}
      <div className="space-y-2">
        {displayedSources.map((source, index) => (
          <motion.div
            key={`${source.documentId}-${index}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: index * 0.1 }}
            className={`p-3 bg-slate-600/30 backdrop-blur-sm border border-white/10 rounded-lg ${
              onSourceClick ? 'cursor-pointer hover:bg-slate-600/50 hover:border-white/20' : ''
            } transition-all duration-200`}
            onClick={() => onSourceClick?.(source)}
          >
            <div className="flex items-start justify-between space-x-3">
              {/* Source Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <h4 className="text-sm font-medium text-white truncate">
                    {source.fileName}
                  </h4>
                  {onSourceClick && (
                    <ExternalLink className="w-3 h-3 text-white/40 flex-shrink-0" />
                  )}
                </div>
                
                {/* Excerpt */}
                <p className="text-xs text-white/70 line-clamp-2 leading-relaxed">
                  {source.excerpt}
                </p>

                {/* Additional Info */}
                <div className="flex items-center space-x-3 mt-2">
                  {/* Page Number */}
                  {source.pageNumber && source.pageNumber > 0 && (
                    <span className="text-xs text-white/50 bg-slate-700/30 px-2 py-0.5 rounded">
                      Page {source.pageNumber}
                    </span>
                  )}

                  {/* Confidence Score */}
                  {showConfidence && source.confidence > 0 && (
                    <div className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      getConfidenceColor(source.confidence)
                    }`}>
                      {getConfidenceLabel(source.confidence)} ({Math.round(source.confidence * 100)}%)
                    </div>
                  )}

                  {/* Document Type Indicator */}
                  {source.s3Location && (
                    <span className="text-xs text-white/40">
                      📄 Document
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Show More/Less Button */}
      {hasMoreSources && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
        >
          {showAll 
            ? `Show less (${sources.length - maxSources} hidden)` 
            : `Show ${sources.length - maxSources} more source${sources.length - maxSources > 1 ? 's' : ''}`
          }
        </button>
      )}
    </motion.div>
  );
};