// Main Layout Component
// Provides the overall application layout with header, sidebar, and content area

import { useAuth } from '@/contexts/AuthContext';
import { LayoutProps } from '@/types/components';
import { motion } from 'framer-motion';
import React, { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  title,
  showSidebar = true,
  showHeader = true 
}) => {
  const { authState, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      // The AuthContext will handle redirecting to login
    } catch (error) {
      console.error('Logout failed:', error);
      // Fallback: force redirect to login
      window.location.href = '/login';
    }
  };

  if (!authState.isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      {showHeader && (
        <Header 
          user={authState.user ? {
            email: authState.user.email,
            role: authState.user['custom:role']
          } : undefined}
          onLogout={handleLogout}
          showUserMenu={true}
        />
      )}

      <div className="flex">
        {/* Sidebar */}
        {showSidebar && (
          <Sidebar
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(!sidebarOpen)}
            currentPath={window.location.pathname}
            userRole={authState.user?.['custom:role'] || 'user'}
          />
        )}

        {/* Main Content */}
        <main className={`flex-1 transition-all duration-300 ${showSidebar ? 'lg:ml-64' : ''} ${showHeader ? 'pt-16' : ''}`}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="p-6 min-h-screen"
          >
            {title && (
              <div className="mb-6">
                <h1 className="text-3xl font-bold text-white">{title}</h1>
              </div>
            )}
            <div className="w-full max-w-none">
              {children}
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  );
};