// Notification Context Provider
// Manages toast notifications and alerts

import { Notification, NotificationContextValue } from '@/types/components';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from 'lucide-react';
import React, { createContext, ReactNode, useCallback, useContext, useState } from 'react';

interface NotificationProviderProps {
  children: ReactNode;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

export const useNotification = (): NotificationContextValue => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const timestamp = new Date().toISOString();
    
    const newNotification: Notification = {
      id,
      timestamp,
      autoClose: notification.autoClose !== false,
      duration: notification.duration || 5000,
      ...notification
    };

    setNotifications(prev => [...prev, newNotification]);

    // Auto-remove notification if autoClose is enabled
    if (newNotification.autoClose) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5" />;
      case 'error':
        return <AlertCircle className="w-5 h-5" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5" />;
      case 'info':
        return <Info className="w-5 h-5" />;
      default:
        return <Info className="w-5 h-5" />;
    }
  };

  const getColors = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return 'bg-green-500/20 border-green-500/30 text-green-200';
      case 'error':
        return 'bg-red-500/20 border-red-500/30 text-red-200';
      case 'warning':
        return 'bg-yellow-500/20 border-yellow-500/30 text-yellow-200';
      case 'info':
        return 'bg-blue-500/20 border-blue-500/30 text-blue-200';
      default:
        return 'bg-gray-500/20 border-gray-500/30 text-gray-200';
    }
  };

  const contextValue: NotificationContextValue = {
    notifications,
    addNotification,
    removeNotification,
    clearNotifications
  };

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
      
      {/* Notification Container */}
      <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
        <AnimatePresence>
          {notifications.map((notification) => (
            <motion.div
              key={notification.id}
              initial={{ opacity: 0, x: 300, scale: 0.8 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 300, scale: 0.8 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className={`backdrop-blur-xl border rounded-xl p-4 shadow-lg ${getColors(notification.type)}`}
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getIcon(notification.type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  {notification.title && (
                    <h4 className="font-semibold text-sm mb-1">
                      {notification.title}
                    </h4>
                  )}
                  <p className="text-sm opacity-90">
                    {notification.message}
                  </p>
                </div>
                
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </NotificationContext.Provider>
  );
};