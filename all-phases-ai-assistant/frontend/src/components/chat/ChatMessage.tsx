// Chat Message Component
// Individual message display with user/assistant styling and source citations

import { ChatMessageProps } from '@/types/components';
import { motion } from 'framer-motion';
import { Bot, RefreshCw, User } from 'lucide-react';
import React from 'react';
import { SourceCitation } from './SourceCitation';

export const ChatMessageComponent: React.FC<ChatMessageProps & { onRetry?: (() => void) | undefined }> = ({
  message,
  isLoading = false,
  showSources = true,
  onSourceClick,
  onRetry
}) => {
  const isUser = message.type === 'user';
  const isError = message.content.includes('error') || message.content.includes('apologize');

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser 
            ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
            : isError
            ? 'bg-gradient-to-r from-red-500 to-orange-500'
            : 'bg-gradient-to-r from-purple-500 to-pink-500'
        }`}>
          {isUser ? (
            <User className="w-4 h-4 text-white" />
          ) : (
            <Bot className="w-4 h-4 text-white" />
          )}
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Message Bubble */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
            className={`relative px-4 py-3 rounded-2xl max-w-full ${
              isUser
                ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                : isError
                ? 'bg-red-500/20 border border-red-500/30 text-red-300'
                : 'bg-slate-700/50 backdrop-blur-sm border border-white/10 text-white'
            }`}
          >
            {/* Loading indicator for assistant messages */}
            {isLoading && !isUser && (
              <div className="flex items-center space-x-2 mb-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm text-white/60">AI is thinking...</span>
              </div>
            )}

            {/* Message Text */}
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap break-words m-0">
                {message.content}
              </p>
            </div>

            {/* Model Used Badge (for assistant messages) */}
            {!isUser && message.modelUsed && (
              <div className="mt-2 inline-flex items-center px-2 py-1 bg-white/10 rounded-full">
                <span className="text-xs text-white/60">
                  {message.modelUsed.includes('opus') ? 'Claude Opus 4.1' :
                   message.modelUsed.includes('3-7-sonnet') ? 'Claude 3.7 Sonnet' :
                   message.modelUsed.includes('3-5-sonnet') ? 'Claude 3.5 Sonnet v2' :
                   'Claude'}
                </span>
              </div>
            )}

            {/* Retry Button for Error Messages */}
            {isError && onRetry && (
              <button
                onClick={onRetry}
                className="mt-2 inline-flex items-center space-x-1 px-2 py-1 bg-red-500/20 hover:bg-red-500/30 rounded-lg transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                <span className="text-xs">Retry</span>
              </button>
            )}
          </motion.div>

          {/* Source Citations (for assistant messages) */}
          {!isUser && showSources && message.sources && message.sources.length > 0 && (
            <div className="mt-2 max-w-full">
              <SourceCitation
                sources={message.sources}
                onSourceClick={onSourceClick}
                maxSources={3}
                showConfidence={true}
              />
            </div>
          )}

          {/* Timestamp */}
          <div className={`mt-1 text-xs text-white/40 ${isUser ? 'text-right' : 'text-left'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>
        </div>
      </div>
    </div>
  );
};