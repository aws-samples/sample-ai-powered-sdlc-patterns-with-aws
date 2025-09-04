// Sidebar Navigation Component
// Left navigation panel with role-based menu items

import { NavigationItem, SidebarProps } from '@/types/components';
import { ROUTES } from '@/types/routes';
import {
    FileText,
    Home,
    Menu,
    MessageCircle,
    Settings,
    Shield,
    X
} from 'lucide-react';
import React from 'react';
import { Link } from 'react-router-dom';

export const Sidebar: React.FC<SidebarProps> = ({ 
  isOpen, 
  onToggle, 
  currentPath, 
  userRole 
}) => {
  const navigationItems: NavigationItem[] = [
    {
      path: ROUTES.HOME,
      label: 'Dashboard',
      icon: 'home',
      roles: ['admin', 'user']
    },
    {
      path: ROUTES.CHAT,
      label: 'Chat',
      icon: 'chat',
      roles: ['admin', 'user']
    },
    {
      path: ROUTES.DOCUMENTS,
      label: 'Documents',
      icon: 'documents',
      roles: ['admin', 'user']
    },
    {
      path: ROUTES.ADMIN_DASHBOARD,
      label: 'Administration',
      icon: 'admin',
      roles: ['admin']
    }
  ];

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'home':
        return <Home className="w-5 h-5" />;
      case 'chat':
        return <MessageCircle className="w-5 h-5" />;
      case 'documents':
        return <FileText className="w-5 h-5" />;
      case 'admin':
        return <Shield className="w-5 h-5" />;
      case 'settings':
        return <Settings className="w-5 h-5" />;
      default:
        return <Home className="w-5 h-5" />;
    }
  };

  const filteredItems = navigationItems.filter(item => 
    item.roles.includes(userRole)
  );

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={onToggle}
        className="lg:hidden fixed top-20 left-4 z-50 p-2 rounded-lg bg-white/10 backdrop-blur-xl border border-white/20 text-white"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-16 bottom-0 z-30 w-64 backdrop-blur-xl bg-slate-900/80 border-r border-white/10 transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:z-auto ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Close button for mobile */}
          <div className="lg:hidden flex justify-end p-4">
            <button
              onClick={onToggle}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6">
            <div className="space-y-2">
              {filteredItems.map((item) => {
                const isActive = currentPath === item.path || 
                  (item.path !== ROUTES.HOME && currentPath.startsWith(item.path));

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={onToggle}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                      isActive
                        ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg'
                        : 'text-white/70 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    {getIcon(item.icon || 'home')}
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-white/10">
            <div className="text-center">
              <p className="text-xs text-white/40">
                AI Assistant v1.0
              </p>
              <p className="text-xs text-white/40">
                Powered by Amazon Bedrock
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};