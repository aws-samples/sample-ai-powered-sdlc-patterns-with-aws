// Chat Input Component
// Text input with send button and character limit

import { ChatInputProps } from '@/types/components';
import { motion } from 'framer-motion';
import { Send } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  disabled = false,
  placeholder = "Type your message...",
  maxLength = 500
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const remainingChars = maxLength - message.length;
  const isNearLimit = remainingChars <= 50;
  const isOverLimit = remainingChars < 0;

  return (
    <form onSubmit={handleSubmit} className="p-4">
      <div className="relative">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          className={`w-full resize-none bg-slate-700/50 backdrop-blur-sm border ${
            isOverLimit 
              ? 'border-red-500/50 focus:border-red-500' 
              : 'border-white/20 focus:border-purple-500/50'
          } rounded-xl px-4 py-3 pr-12 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition-all duration-200`}
          style={{ 
            minHeight: '52px',
            maxHeight: '120px'
          }}
          maxLength={maxLength + 50} // Allow slight overflow for better UX
        />

        {/* Send Button */}
        <motion.button
          type="submit"
          disabled={!message.trim() || isLoading || disabled || isOverLimit}
          className={`absolute right-2 bottom-2 p-2 rounded-lg transition-all duration-200 ${
            !message.trim() || isLoading || disabled || isOverLimit
              ? 'bg-slate-600/50 text-white/30 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 shadow-lg'
          }`}
          whileHover={!message.trim() || isLoading || disabled || isOverLimit ? {} : { scale: 1.05 }}
          whileTap={!message.trim() || isLoading || disabled || isOverLimit ? {} : { scale: 0.95 }}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </motion.button>

        {/* Character Counter */}
        {(isNearLimit || isOverLimit) && (
          <div className={`absolute -top-6 right-0 text-xs ${
            isOverLimit ? 'text-red-400' : 'text-yellow-400'
          }`}>
            {remainingChars} characters {isOverLimit ? 'over limit' : 'remaining'}
          </div>
        )}
      </div>

      {/* Help Text */}
      <div className="mt-2 text-xs text-white/40">
        Press Enter to send, Shift+Enter for new line
      </div>
    </form>
  );
};