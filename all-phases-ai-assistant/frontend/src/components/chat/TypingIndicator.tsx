// Typing Indicator Component
// Shows when AI is processing a response

import { TypingIndicatorProps } from '@/types/components';
import { AnimatePresence, motion } from 'framer-motion';
import { Bot } from 'lucide-react';
import React from 'react';

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isVisible,
  text = "AI is thinking..."
}) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="flex items-start space-x-3 mb-4"
        >
          {/* Avatar */}
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>

          {/* Typing Bubble */}
          <motion.div
            initial={{ scale: 0.95 }}
            animate={{ scale: 1 }}
            className="bg-slate-700/50 backdrop-blur-sm border border-white/10 rounded-2xl px-4 py-3"
          >
            <div className="flex items-center space-x-3">
              {/* Animated Dots */}
              <div className="flex space-x-1">
                <motion.div
                  className="w-2 h-2 bg-purple-400 rounded-full"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5]
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                />
                <motion.div
                  className="w-2 h-2 bg-purple-400 rounded-full"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5]
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: 0.2
                  }}
                />
                <motion.div
                  className="w-2 h-2 bg-purple-400 rounded-full"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5]
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: 0.4
                  }}
                />
              </div>

              {/* Text */}
              <span className="text-sm text-white/60">{text}</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};