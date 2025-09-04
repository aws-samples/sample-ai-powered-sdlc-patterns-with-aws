// Chat Page Component
// Main chat interface for AI assistant

import { ChatInterface } from '@/components/chat';
import { motion } from 'framer-motion';
import React, { useState } from 'react';

export const ChatPage: React.FC = () => {
  const [conversationId, setConversationId] = useState<string | undefined>();

  const handleNewConversation = () => {
    setConversationId(undefined);
  };



  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-2"
      >
        <h1 className="text-3xl font-bold text-white">AI Assistant Chat</h1>
        <p className="text-white/60">
          Ask questions about your uploaded documents and get intelligent responses with source citations
        </p>
      </motion.div>

      {/* Chat Interface */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <ChatInterface
          conversationId={conversationId}
          onNewConversation={handleNewConversation}
          maxHeight="70vh"
        />
      </motion.div>

      {/* Usage Tips */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-slate-800/30 backdrop-blur-sm border border-white/10 rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-3">Tips for better results:</h3>
        <ul className="space-y-2 text-white/70">
          <li className="flex items-start space-x-2">
            <span className="text-purple-400 mt-1">•</span>
            <span>Be specific in your questions to get more accurate answers</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-purple-400 mt-1">•</span>
            <span>Click on source citations to view the original documents</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-purple-400 mt-1">•</span>
            <span>Use follow-up questions to dive deeper into topics</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-purple-400 mt-1">•</span>
            <span>The AI uses different Claude models based on query complexity</span>
          </li>
        </ul>
      </motion.div>
    </div>
  );
};