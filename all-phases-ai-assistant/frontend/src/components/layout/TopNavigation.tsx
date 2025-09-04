// Top Navigation Component
// Horizontal navigation menu for main sections

import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { FileText, Home, MessageCircle, Shield } from 'lucide-react';
import React from 'react';

interface TopNavigationProps {
  currentPath: string;
  userRole: string;
}

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  roles: string[];
}

export const TopNavigation: React.FC<TopNavigationProps> = ({ 
  currentPath, 
  userRole 
}) => {
  const navigationItems: NavItem[] = [
    {
      path: ROUTES.HOME,
      label: 'Home',
      icon: <Home className="w-4 h-4" />,
      roles: ['admin', 'user']
    },
    {
      path: ROUTES.CHAT,
      label: 'Chat',
      icon: <MessageCircle className="w-4 h-4" />,
      roles: ['admin', 'user']
    },
    {
      path: ROUTES.DOCUMENTS,
      label: 'Documents',
      icon: <FileText className="w-4 h-4" />,
      roles: ['admin', 'user']
    },
    {
      path: ROUTES.ADMIN_DASHBOARD,
      label: 'Admin',
      icon: <Shield className="w-4 h-4" />,
      roles: ['admin']
    }
  ];

  const filteredItems = navigationItems.filter(item => 
    item.roles.includes(userRole)
  );

  return (
    <nav className="hidden md:flex items-center space-x-1">
      {filteredItems.map((item) => {
        const isActive = currentPath === item.path || 
          (item.path !== ROUTES.HOME && currentPath.startsWith(item.path));

        return (
          <motion.a
            key={item.path}
            href={item.path}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
              isActive
                ? 'bg-white/20 text-white shadow-lg'
                : 'text-white/70 hover:text-white hover:bg-white/10'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {item.icon}
            <span className="font-medium text-sm">{item.label}</span>
          </motion.a>
        );
      })}
    </nav>
  );
};