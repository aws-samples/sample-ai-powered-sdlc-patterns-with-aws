// Message List Component
// Displays a list of chat messages with proper formatting

import { MessageListProps } from '@/types/components';
import { motion } from 'framer-motion';
import React from 'react';
import { ChatMessageComponent } from './ChatMessage';

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading = false,
  onSourceClick,
  onRetry
}) => {
  if (messages.length === 0 && !isLoading) {
    return null;
  }

  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <motion.div
          key={message.messageId}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ 
            duration: 0.3, 
            delay: index * 0.1 
          }}
        >
          <ChatMessageComponent
            message={message}
            showSources={true}
            onSourceClick={onSourceClick}
            onRetry={onRetry ? () => onRetry(message.messageId) : undefined}
          />
        </motion.div>
      ))}
    </div>
  );
};