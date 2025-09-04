// Header Component
// Top navigation bar with user menu, branding, and navigation links

import { HeaderProps } from '@/types/components';
import { AnimatePresence, motion } from 'framer-motion';
import { Brain, ChevronDown, LogOut, Settings, User } from 'lucide-react';
import React, { useState } from 'react';

export const Header: React.FC<HeaderProps> = ({ 
  user, 
  onLogout, 
  showUserMenu = true 
}) => {
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-10 backdrop-blur-xl bg-slate-900/80 border-b border-white/10 lg:left-64">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 shadow-lg">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AI Assistant</h1>
              <p className="text-xs text-white/60">Development Team Knowledge Base</p>
            </div>
          </div>



          {/* User Menu */}
          {showUserMenu && user && (
            <div className="relative">
              <motion.button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center space-x-3 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 transition-all duration-200"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="text-left hidden sm:block">
                  <p className="text-sm font-medium text-white">{user.email}</p>
                  <p className="text-xs text-white/60 capitalize">{user.role}</p>
                </div>
                <ChevronDown className={`w-4 h-4 text-white/60 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
              </motion.button>

              {/* Dropdown Menu */}
              <AnimatePresence>
                {userMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 mt-2 w-64 backdrop-blur-xl bg-slate-800/90 border border-white/20 rounded-xl shadow-2xl py-2"
                  >
                    {/* User Info */}
                    <div className="px-4 py-3 border-b border-white/10">
                      <p className="text-sm font-medium text-white">{user.email}</p>
                      <p className="text-xs text-white/60 capitalize">Role: {user.role}</p>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2">
                      <button
                        onClick={() => {
                          setUserMenuOpen(false);
                          // Navigate to profile
                          window.location.href = '/profile';
                        }}
                        className="w-full flex items-center space-x-3 px-4 py-2 text-left text-white/80 hover:text-white hover:bg-white/10 transition-all duration-200"
                      >
                        <User className="w-4 h-4" />
                        <span>Profile</span>
                      </button>

                      <button
                        onClick={() => {
                          setUserMenuOpen(false);
                          // Navigate to settings
                          window.location.href = '/settings';
                        }}
                        className="w-full flex items-center space-x-3 px-4 py-2 text-left text-white/80 hover:text-white hover:bg-white/10 transition-all duration-200"
                      >
                        <Settings className="w-4 h-4" />
                        <span>Settings</span>
                      </button>

                      <div className="border-t border-white/10 my-2"></div>

                      <button
                        onClick={() => {
                          setUserMenuOpen(false);
                          onLogout();
                        }}
                        className="w-full flex items-center space-x-3 px-4 py-2 text-left text-red-300 hover:text-red-200 hover:bg-red-500/10 transition-all duration-200"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};