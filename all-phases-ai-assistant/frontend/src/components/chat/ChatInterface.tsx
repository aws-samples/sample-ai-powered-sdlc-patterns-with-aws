// Chat Interface Component
// Main chat interface with message display and input

import { API_CONFIG } from '@/config/aws-config';
import { useAuth } from '@/contexts/AuthContext';
import { ChatMessage, DocumentSource } from '@/types/api';
import { ChatInterfaceProps } from '@/types/components';
import { chatRateLimiter, createSecureErrorMessage, getSecureAuthToken, sanitizeInput, validateMessage } from '@/utils/security';
import { motion } from 'framer-motion';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChatInput } from './ChatInput';
import { MessageList } from './MessageList';
import { TypingIndicator } from './TypingIndicator';

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  conversationId,
  onNewConversation,
  maxHeight = '600px'
}) => {
  const { authState } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages are added
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load conversation history if conversationId is provided
  useEffect(() => {
    if (conversationId) {
      loadConversationHistory(conversationId);
    }
  }, [conversationId]);

  const loadConversationHistory = async (convId: string) => {
    try {
      setIsLoading(true);
      
      // Get ID token from authState or fallback to localStorage (API Gateway requires ID token, not access token)
      let idToken = authState.idToken;
      if (!idToken) {
        // Look for Cognito ID token in localStorage
        const tokenKey = Object.keys(localStorage).find(key => 
          key.includes('CognitoIdentityServiceProvider') && key.includes('idToken')
        );
        idToken = tokenKey ? localStorage.getItem(tokenKey) || undefined : undefined;
      }

      if (!idToken) {
        throw new Error('No ID token available');
      }

      const response = await fetch(`${API_CONFIG.baseURL}/chat/history/${convId}`, {
        headers: {
          'Authorization': idToken,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load conversation history');
      }

      const data = await response.json();
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Error loading conversation history:', err);
      setError('Failed to load conversation history');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (messageText: string) => {
    // Enhanced input validation and sanitization
    const validation = validateMessage(messageText);
    if (!validation.isValid) {
      setError(validation.error || 'Invalid message');
      return;
    }

    // Rate limiting check
    const userId = authState.user?.sub || 'anonymous';
    if (!chatRateLimiter.isAllowed(userId)) {
      setError('Too many messages. Please wait a moment before sending another message.');
      return;
    }

    // Sanitize input
    const sanitizedMessage = sanitizeInput(messageText);
    
    const userMessage: ChatMessage = {
      messageId: `user-${Date.now()}`,
      type: 'user',
      content: sanitizedMessage,
      timestamp: new Date().toISOString()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // Securely get authentication token
      const idToken = getSecureAuthToken(authState);
      if (!idToken) {
        throw new Error('Authentication required - please log in again');
      }

      const response = await fetch(`${API_CONFIG.baseURL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Authorization': idToken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question: sanitizedMessage,
          userId: authState.user?.sub || 'anonymous',
          conversationId: conversationId,
          includeSourceDetails: true,
          enableStreaming: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get AI response');
      }

      const data = await response.json();
      
      const assistantMessage: ChatMessage = {
        messageId: `assistant-${Date.now()}`,
        type: 'assistant',
        content: data.answer,
        timestamp: data.timestamp,
        sources: data.sources,
        modelUsed: data.modelUsed
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      // Secure error handling - don't expose sensitive information
      console.error('Chat error occurred:', { timestamp: new Date().toISOString() });
      
      const secureErrorMessage = createSecureErrorMessage(err);
      setError(secureErrorMessage);
      
      // Add error message to chat
      const assistantErrorMessage: ChatMessage = {
        messageId: `error-${Date.now()}`,
        type: 'assistant',
        content: secureErrorMessage,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, assistantErrorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = async (messageId: string) => {
    const messageIndex = messages.findIndex(m => m.messageId === messageId);
    if (messageIndex === -1) return;

    const userMessageIndex = messageIndex - 1;
    const userMessageObj = messages[userMessageIndex];
    if (userMessageIndex >= 0 && userMessageObj && userMessageObj.type === 'user') {
      const userMessage = userMessageObj.content;
      
      // Remove the failed assistant message
      setMessages(prev => prev.filter(m => m.messageId !== messageId));
      
      // Retry the request
      await handleSendMessage(userMessage);
    }
  };

  const handleSourceClick = (source: DocumentSource) => {
    // Handle source click - could open document viewer, navigate to document, etc.
    console.log('Source clicked:', source);
    
    // For now, just show an alert with source info
    // In a real implementation, this would open a document viewer or navigate to the document
    alert(`Document: ${source.fileName}\nConfidence: ${Math.round(source.confidence * 100)}%\nExcerpt: ${source.excerpt.substring(0, 100)}...`);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col bg-slate-800/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl"
      style={{ height: maxHeight }}
    >
      {/* Chat Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div>
          <h2 className="text-lg font-semibold text-white">AI Assistant</h2>
          <p className="text-sm text-white/60">
            {conversationId ? 'Continuing conversation' : 'Ask me anything about your documents'}
          </p>
        </div>
        {onNewConversation && (
          <button
            onClick={onNewConversation}
            className="px-3 py-1.5 text-sm bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg transition-colors"
          >
            New Chat
          </button>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-3">
                <div className="w-16 h-16 mx-auto bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white">Start a conversation</h3>
                  <p className="text-white/60">Ask questions about your uploaded documents</p>
                </div>
              </div>
            </div>
          )}

          <MessageList
            messages={messages}
            isLoading={false}
            onRetry={handleRetry}
            onSourceClick={handleSourceClick}
          />

          {/* Typing Indicator */}
          <TypingIndicator isVisible={isLoading} />

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg"
            >
              <p className="text-red-300 text-sm">{error}</p>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Chat Input */}
      <div className="border-t border-white/10">
        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          placeholder="Ask a question about your documents..."
          maxLength={500}
        />
      </div>
    </motion.div>
  );
};