// Documents Page Component
// Document management interface with upload and list functionality

import { DocumentDetails, DocumentList, DocumentUpload } from '@/components/documents';
import { DocumentMetadata } from '@/types/api';
import { motion } from 'framer-motion';
import { List, Plus, Upload as UploadIcon } from 'lucide-react';
import React, { useCallback, useState } from 'react';

type ViewMode = 'list' | 'upload';

export const DocumentsPage: React.FC = () => {

  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedDocument, setSelectedDocument] = useState<DocumentMetadata | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = useCallback((documents: DocumentMetadata[]) => {
    console.log('Upload completed:', documents);
    // Trigger refresh of document list
    setRefreshTrigger(prev => prev + 1);
    // Switch back to list view
    setViewMode('list');
  }, []);

  const handleUploadError = useCallback((error: string) => {
    console.error('Upload error:', error);
    // You could show a toast notification here
  }, []);

  const handleDocumentSelect = useCallback((document: DocumentMetadata) => {
    setSelectedDocument(document);
  }, []);

  const handleDocumentDelete = useCallback((documentId: string) => {
    console.log('Document deleted:', documentId);
    // Trigger refresh of document list
    setRefreshTrigger(prev => prev + 1);
    // Close details modal if the deleted document was selected
    if (selectedDocument?.documentId === documentId) {
      setSelectedDocument(null);
    }
  }, [selectedDocument]);

  const handleCloseDetails = useCallback(() => {
    setSelectedDocument(null);
  }, []);

  const handleRefreshList = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-white">Document Management</h1>
          <p className="text-white/60 mt-2">
            Upload and manage documents for the AI knowledge base
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center space-x-2 bg-gray-800/50 rounded-lg p-1 border border-gray-700">
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
              viewMode === 'list'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <List className="w-4 h-4" />
            <span>View Documents</span>
          </button>
          
          <button
            onClick={() => setViewMode('upload')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
              viewMode === 'upload'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <UploadIcon className="w-4 h-4" />
            <span>Upload Documents</span>
          </button>
        </div>
      </motion.div>

      {/* Content */}
      <motion.div
        key={viewMode}
        initial={{ opacity: 0, x: viewMode === 'upload' ? 20 : -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        className="min-h-[600px]"
      >
        {viewMode === 'upload' ? (
          <div className="max-w-4xl mx-auto">
            <DocumentUpload
              onUploadComplete={handleUploadComplete}
              onUploadError={handleUploadError}
            />
            
            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-8 p-6 bg-gray-800/30 rounded-lg border border-gray-700"
            >
              <h3 className="text-lg font-medium text-white mb-4">Upload Guidelines</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-300">
                <div>
                  <h4 className="font-medium text-white mb-2">Supported Formats</h4>
                  <ul className="space-y-1">
                    <li>• PDF documents (.pdf)</li>
                    <li>• Word documents (.docx)</li>
                    <li>• Text files (.txt)</li>
                    <li>• Markdown files (.md)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-white mb-2">Processing Info</h4>
                  <ul className="space-y-1">
                    <li>• Maximum file size: 10MB</li>
                    <li>• Processing time: 2-10 minutes</li>
                    <li>• Documents are automatically indexed for AI search</li>
                    <li>• You'll be notified when processing completes</li>
                  </ul>
                </div>
              </div>
            </motion.div>
          </div>
        ) : (
          <DocumentList
            onDocumentSelect={handleDocumentSelect}
            onDocumentDelete={handleDocumentDelete}
            refreshTrigger={refreshTrigger}
          />
        )}
      </motion.div>

      {/* Document Details Modal */}
      {selectedDocument && (
        <DocumentDetails
          document={selectedDocument}
          isOpen={!!selectedDocument}
          onClose={handleCloseDetails}
          onDelete={handleDocumentDelete}
          onRefresh={handleRefreshList}
        />
      )}

      {/* Quick Upload FAB (when in list view) */}
      {viewMode === 'list' && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setViewMode('upload')}
          className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition-colors z-40"
        >
          <Plus className="w-6 h-6" />
        </motion.button>
      )}
    </div>
  );
};