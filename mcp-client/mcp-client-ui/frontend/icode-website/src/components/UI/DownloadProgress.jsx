import React from 'react';
import PropTypes from 'prop-types';

/**
 * Download Progress Component
 * Displays progress information for download operations
 */
const DownloadProgress = ({ 
  progress, 
  onCancel = null, 
  className = '',
  showCancel = true,
  compact = false 
}) => {
  if (!progress) {
    return null;
  }

  const { percentage = 0, status = 'Downloading...', loaded = 0, total = 0 } = progress;

  // Format bytes to human readable string
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const progressBarStyle = {
    width: `${Math.min(100, Math.max(0, percentage))}%`
  };

  if (compact) {
    return (
      <div className={`download-progress-compact ${className}`}>
        <div className="progress-info">
          <span className="status-text">{status}</span>
          <span className="percentage">{Math.round(percentage)}%</span>
        </div>
        <div className="progress-bar-container">
          <div className="progress-bar" style={progressBarStyle}></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`download-progress ${className}`}>
      <div className="progress-header">
        <div className="progress-info">
          <h4>Download Progress</h4>
          <span className="status-text">{status}</span>
        </div>
        {showCancel && onCancel && (
          <button 
            className="btn btn-small btn-secondary"
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
        )}
      </div>

      <div className="progress-details">
        <div className="progress-bar-container">
          <div className="progress-bar" style={progressBarStyle}></div>
          <span className="progress-percentage">{Math.round(percentage)}%</span>
        </div>
        
        {total > 0 && (
          <div className="progress-stats">
            <span className="bytes-info">
              {formatBytes(loaded)} of {formatBytes(total)}
            </span>
          </div>
        )}
      </div>

      <style>{`
        .download-progress {
          background: #f8f9fa;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 16px;
          margin: 12px 0;
        }

        .download-progress-compact {
          background: #f8f9fa;
          border: 1px solid #e9ecef;
          border-radius: 4px;
          padding: 8px 12px;
          margin: 8px 0;
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .progress-info h4 {
          margin: 0 0 4px 0;
          font-size: 14px;
          font-weight: 600;
          color: #495057;
        }

        .progress-info .status-text {
          font-size: 12px;
          color: #6c757d;
        }

        .progress-compact .progress-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
        }

        .progress-compact .status-text {
          font-size: 12px;
          color: #6c757d;
        }

        .progress-compact .percentage {
          font-size: 12px;
          font-weight: 600;
          color: #495057;
        }

        .progress-bar-container {
          position: relative;
          background: #e9ecef;
          border-radius: 4px;
          height: 8px;
          overflow: hidden;
          margin-bottom: 8px;
        }

        .progress-bar {
          height: 100%;
          background: linear-gradient(90deg, #007bff, #0056b3);
          border-radius: 4px;
          transition: width 0.3s ease;
          position: relative;
        }

        .progress-bar::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.3),
            transparent
          );
          animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }

        .progress-percentage {
          position: absolute;
          right: 0;
          top: -20px;
          font-size: 12px;
          font-weight: 600;
          color: #495057;
        }

        .progress-stats {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .bytes-info {
          font-size: 12px;
          color: #6c757d;
        }

        .btn {
          padding: 4px 12px;
          border: 1px solid #ccc;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s ease;
        }

        .btn:hover {
          background: #f8f9fa;
          border-color: #adb5bd;
        }

        .btn-secondary {
          color: #6c757d;
          border-color: #6c757d;
        }

        .btn-secondary:hover {
          background: #6c757d;
          color: white;
        }

        .btn-small {
          padding: 2px 8px;
          font-size: 11px;
        }
      `}</style>
    </div>
  );
};

DownloadProgress.propTypes = {
  progress: PropTypes.shape({
    percentage: PropTypes.number,
    status: PropTypes.string,
    loaded: PropTypes.number,
    total: PropTypes.number
  }),
  onCancel: PropTypes.func,
  className: PropTypes.string,
  showCancel: PropTypes.bool,
  compact: PropTypes.bool
};

export default DownloadProgress;