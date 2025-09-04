// Conversation Page Component
// Individual conversation view with history

import { useAuth } from '@/components/auth/AuthContext';
import { ChatInterface } from '@/components/chat';
import { API_CONFIG } from '@/config/aws-config';
import { motion } from 'framer-motion';
import { ArrowLeft, Calendar, MessageCircle } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

interface ConversationInfo {
  conversationId: string;
  createdAt: string;
  lastActivity: string;
  totalMessages: number;
}

export const ConversationPage: React.FC = () => {
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const { authState } = useAuth();
  const [conversationInfo, setConversationInfo] = useState<ConversationInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (conversationId) {
      loadConversationInfo(conversationId);
    }
  }, [conversationId]);

  const loadConversationInfo = async (convId: string) => {
    try {
      setIsLoading(true);
      
      // Get access token from authState or fallback to localStorage
      let accessToken = authState.accessToken;
      if (!accessToken) {
        const tokenKey = Object.keys(localStorage).find(key => key.includes('accessToken'));
        accessToken = tokenKey ? localStorage.getItem(tokenKey) || undefined : undefined;
      }

      if (!accessToken) {
        throw new Error('No access token available');
      }

      const response = await fetch(`${API_CONFIG.baseURL}/chat/conversations/${convId}`, {
        headers: {
          'Authorization': accessToken,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load conversation info');
      }

      const data = await response.json();
      setConversationInfo(data);
    } catch (err) {
      console.error('Error loading conversation info:', err);
      setError('Failed to load conversation');
    } finally {
      setIsLoading(false);
    }
  };



  const handleBackToChat = () => {
    navigate('/chat');
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="text-white/60">Loading conversation...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !conversationId) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-red-500/20 rounded-2xl flex items-center justify-center">
            <MessageCircle className="w-8 h-8 text-red-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Conversation Not Found</h2>
            <p className="text-white/60 mt-2">{error || 'The requested conversation could not be found.'}</p>
          </div>
          <button
            onClick={handleBackToChat}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Chat</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center space-x-4">
          <button
            onClick={handleBackToChat}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">Conversation</h1>
            {conversationInfo && (
              <div className="flex items-center space-x-4 text-sm text-white/60 mt-1">
                <div className="flex items-center space-x-1">
                  <Calendar className="w-4 h-4" />
                  <span>Started {new Date(conversationInfo.createdAt).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <MessageCircle className="w-4 h-4" />
                  <span>{conversationInfo.totalMessages} messages</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Chat Interface */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <ChatInterface
          conversationId={conversationId}
          maxHeight="70vh"
        />
      </motion.div>
    </div>
  );
};