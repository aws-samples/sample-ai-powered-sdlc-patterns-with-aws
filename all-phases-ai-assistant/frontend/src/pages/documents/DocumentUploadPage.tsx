// Document Upload Page Component
// Dedicated page for document upload functionality

import { DocumentUpload } from '@/components/documents';
import { DocumentMetadata } from '@/types/api';
import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { ArrowLeft, Upload } from 'lucide-react';
import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export const DocumentUploadPage: React.FC = () => {
  const navigate = useNavigate();

  const handleUploadComplete = useCallback((documents: DocumentMetadata[]) => {
    console.log('Upload completed:', documents);
    // Navigate back to documents list
    navigate(ROUTES.DOCUMENTS);
  }, [navigate]);

  const handleUploadError = useCallback((error: string) => {
    console.error('Upload error:', error);
    // You could show a toast notification here
  }, []);

  const handleBackToDocuments = () => {
    navigate(ROUTES.DOCUMENTS);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex items-center space-x-4"
      >
        <button
          onClick={handleBackToDocuments}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        
        <div>
          <h1 className="text-3xl font-bold text-white">Upload Documents</h1>
          <p className="text-white/60 mt-2">
            Add new documents to the AI knowledge base
          </p>
        </div>
      </motion.div>

      {/* Upload Component */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <DocumentUpload
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
        />
      </motion.div>

      {/* Information Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="bg-gray-800/30 rounded-lg border border-gray-700 p-6"
      >
        <div className="flex items-start space-x-4">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 shadow-lg flex-shrink-0">
            <Upload className="w-6 h-6 text-white" />
          </div>
          
          <div className="flex-1">
            <h3 className="text-lg font-medium text-white mb-3">
              How Document Processing Works
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-gray-300">
              <div>
                <h4 className="font-medium text-white mb-2">Upload Process</h4>
                <ol className="space-y-2 list-decimal list-inside">
                  <li>Select and upload your documents</li>
                  <li>Files are securely stored in AWS S3</li>
                  <li>Documents are queued for AI processing</li>
                  <li>Content is extracted and analyzed</li>
                </ol>
              </div>
              
              <div>
                <h4 className="font-medium text-white mb-2">AI Integration</h4>
                <ol className="space-y-2 list-decimal list-inside">
                  <li>Text is chunked for optimal search</li>
                  <li>Embeddings are generated using Titan</li>
                  <li>Content is indexed in Knowledge Base</li>
                  <li>Documents become searchable via AI chat</li>
                </ol>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full mt-2 flex-shrink-0"></div>
                <div>
                  <p className="text-blue-300 font-medium mb-1">Processing Time</p>
                  <p className="text-blue-200 text-sm">
                    Document processing typically takes 2-10 minutes depending on file size and complexity. 
                    You can continue using the application while processing happens in the background.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-yellow-400 rounded-full mt-2 flex-shrink-0"></div>
                <div>
                  <p className="text-yellow-300 font-medium mb-1">Best Practices</p>
                  <ul className="text-yellow-200 text-sm space-y-1">
                    <li>• Use descriptive file names for better organization</li>
                    <li>• Ensure documents contain clear, well-structured text</li>
                    <li>• Avoid uploading duplicate content</li>
                    <li>• Consider breaking large documents into smaller sections</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};