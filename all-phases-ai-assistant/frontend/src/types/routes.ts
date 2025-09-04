// Route configuration and authentication guard types
// Defines the routing structure and access control for the React application

import { UserRole } from './api';

// Route path constants
export const ROUTES = {
  // Public routes
  LOGIN: '/login',
  LOGOUT: '/logout',
  CALLBACK: '/callback',
  
  // Protected routes
  HOME: '/',
  DASHBOARD: '/dashboard',
  
  // Chat routes
  CHAT: '/chat',
  CHAT_NEW: '/chat/new',
  CHAT_CONVERSATION: '/chat/:conversationId',
  
  // Document routes
  DOCUMENTS: '/documents',
  DOCUMENTS_UPLOAD: '/documents/upload',
  DOCUMENTS_VIEW: '/documents/:documentId',
  
  // Admin routes
  ADMIN: '/admin',
  ADMIN_DASHBOARD: '/admin/dashboard',
  ADMIN_USERS: '/admin/users',
  ADMIN_KNOWLEDGE_BASE: '/admin/knowledge-base',
  ADMIN_METRICS: '/admin/metrics',
  ADMIN_SETTINGS: '/admin/settings',
  
  // User profile routes
  PROFILE: '/profile',
  SETTINGS: '/settings',
  
  // Error routes
  NOT_FOUND: '/404',
  UNAUTHORIZED: '/unauthorized',
  ERROR: '/error'
} as const;

// Route metadata interface
export interface RouteMetadata {
  path: string;
  title: string;
  description?: string;
  requiredRole?: UserRole;
  requiresAuth: boolean;
  showInNavigation: boolean;
  navigationLabel?: string;
  navigationIcon?: string;
  navigationOrder?: number;
  parentRoute?: string;
  breadcrumbs?: BreadcrumbConfig[];
  seoTitle?: string;
  seoDescription?: string;
}

export interface BreadcrumbConfig {
  label: string;
  path?: string;
  dynamic?: boolean;
}

// Navigation structure
export interface NavigationGroup {
  id: string;
  label: string;
  icon?: string;
  order: number;
  requiredRole?: UserRole;
  routes: string[];
}

// Route configuration with metadata
export const ROUTE_CONFIG: Record<string, RouteMetadata> = {
  [ROUTES.LOGIN]: {
    path: ROUTES.LOGIN,
    title: 'Login',
    description: 'Sign in to your account',
    requiresAuth: false,
    showInNavigation: false,
    seoTitle: 'Login - AI Assistant',
    seoDescription: 'Sign in to access your AI-powered development assistant'
  },
  
  [ROUTES.HOME]: {
    path: ROUTES.HOME,
    title: 'Home',
    description: 'AI Assistant Dashboard',
    requiresAuth: true,
    showInNavigation: true,
    navigationLabel: 'Home',
    navigationIcon: 'home',
    navigationOrder: 1,
    seoTitle: 'AI Assistant - Development Team Knowledge Base',
    seoDescription: 'Access your team\'s knowledge base with AI-powered assistance'
  },
  
  [ROUTES.CHAT]: {
    path: ROUTES.CHAT,
    title: 'Chat',
    description: 'Chat with AI Assistant',
    requiresAuth: true,
    showInNavigation: true,
    navigationLabel: 'Chat',
    navigationIcon: 'chat',
    navigationOrder: 2,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Chat' }
    ],
    seoTitle: 'Chat - AI Assistant',
    seoDescription: 'Ask questions about your team\'s documentation and get instant AI-powered answers'
  },
  
  [ROUTES.CHAT_CONVERSATION]: {
    path: ROUTES.CHAT_CONVERSATION,
    title: 'Conversation',
    description: 'View conversation history',
    requiresAuth: true,
    showInNavigation: false,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Chat', path: ROUTES.CHAT },
      { label: 'Conversation', dynamic: true }
    ]
  },
  
  [ROUTES.DOCUMENTS]: {
    path: ROUTES.DOCUMENTS,
    title: 'Documents',
    description: 'Manage team documents',
    requiresAuth: true,
    showInNavigation: true,
    navigationLabel: 'Documents',
    navigationIcon: 'documents',
    navigationOrder: 3,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Documents' }
    ],
    seoTitle: 'Documents - AI Assistant',
    seoDescription: 'Upload and manage your team\'s documentation for AI-powered search'
  },
  
  [ROUTES.DOCUMENTS_UPLOAD]: {
    path: ROUTES.DOCUMENTS_UPLOAD,
    title: 'Upload Documents',
    description: 'Upload new documents to the knowledge base',
    requiresAuth: true,
    showInNavigation: false,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Documents', path: ROUTES.DOCUMENTS },
      { label: 'Upload' }
    ]
  },
  
  [ROUTES.DOCUMENTS_VIEW]: {
    path: ROUTES.DOCUMENTS_VIEW,
    title: 'View Document',
    description: 'View document details',
    requiresAuth: true,
    showInNavigation: false,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Documents', path: ROUTES.DOCUMENTS },
      { label: 'Document', dynamic: true }
    ]
  },
  
  [ROUTES.ADMIN]: {
    path: ROUTES.ADMIN,
    title: 'Administration',
    description: 'System administration',
    requiredRole: 'admin',
    requiresAuth: true,
    showInNavigation: true,
    navigationLabel: 'Admin',
    navigationIcon: 'admin',
    navigationOrder: 10,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Administration' }
    ],
    seoTitle: 'Administration - AI Assistant',
    seoDescription: 'Manage users, knowledge base, and system settings'
  },
  
  [ROUTES.ADMIN_DASHBOARD]: {
    path: ROUTES.ADMIN_DASHBOARD,
    title: 'Admin Dashboard',
    description: 'System overview and metrics',
    requiredRole: 'admin',
    requiresAuth: true,
    showInNavigation: false,
    parentRoute: ROUTES.ADMIN,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Administration', path: ROUTES.ADMIN },
      { label: 'Dashboard' }
    ]
  },
  
  [ROUTES.ADMIN_USERS]: {
    path: ROUTES.ADMIN_USERS,
    title: 'User Management',
    description: 'Manage user accounts and permissions',
    requiredRole: 'admin',
    requiresAuth: true,
    showInNavigation: false,
    parentRoute: ROUTES.ADMIN,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Administration', path: ROUTES.ADMIN },
      { label: 'Users' }
    ]
  },
  
  [ROUTES.ADMIN_KNOWLEDGE_BASE]: {
    path: ROUTES.ADMIN_KNOWLEDGE_BASE,
    title: 'Knowledge Base Management',
    description: 'Manage knowledge base and document processing',
    requiredRole: 'admin',
    requiresAuth: true,
    showInNavigation: false,
    parentRoute: ROUTES.ADMIN,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Administration', path: ROUTES.ADMIN },
      { label: 'Knowledge Base' }
    ]
  },
  
  [ROUTES.PROFILE]: {
    path: ROUTES.PROFILE,
    title: 'Profile',
    description: 'User profile and settings',
    requiresAuth: true,
    showInNavigation: false,
    breadcrumbs: [
      { label: 'Home', path: ROUTES.HOME },
      { label: 'Profile' }
    ]
  },
  
  [ROUTES.UNAUTHORIZED]: {
    path: ROUTES.UNAUTHORIZED,
    title: 'Unauthorized',
    description: 'Access denied',
    requiresAuth: false,
    showInNavigation: false,
    seoTitle: 'Unauthorized - AI Assistant',
    seoDescription: 'You do not have permission to access this resource'
  },
  
  [ROUTES.NOT_FOUND]: {
    path: ROUTES.NOT_FOUND,
    title: 'Page Not Found',
    description: 'The requested page could not be found',
    requiresAuth: false,
    showInNavigation: false,
    seoTitle: '404 - Page Not Found',
    seoDescription: 'The page you are looking for does not exist'
  }
};

// Navigation groups for sidebar organization
export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    id: 'main',
    label: 'Main',
    order: 1,
    routes: [ROUTES.HOME, ROUTES.CHAT, ROUTES.DOCUMENTS]
  },
  {
    id: 'admin',
    label: 'Administration',
    icon: 'admin',
    order: 10,
    requiredRole: 'admin',
    routes: [ROUTES.ADMIN]
  }
];

// Route access control utilities
export const isRouteAccessible = (
  route: string, 
  userRole?: UserRole, 
  isAuthenticated: boolean = false
): boolean => {
  const config = ROUTE_CONFIG[route];
  if (!config) return false;
  
  // Check authentication requirement
  if (config.requiresAuth && !isAuthenticated) {
    return false;
  }
  
  // Check role requirement
  if (config.requiredRole && config.requiredRole !== userRole) {
    return false;
  }
  
  return true;
};

export const getNavigationRoutes = (
  userRole?: UserRole, 
  isAuthenticated: boolean = false
): RouteMetadata[] => {
  return Object.values(ROUTE_CONFIG)
    .filter(config => 
      config.showInNavigation && 
      isRouteAccessible(config.path, userRole, isAuthenticated)
    )
    .sort((a, b) => (a.navigationOrder || 999) - (b.navigationOrder || 999));
};

export const getBreadcrumbs = (
  currentRoute: string,
  params?: Record<string, string>
): BreadcrumbConfig[] => {
  const config = ROUTE_CONFIG[currentRoute];
  if (!config || !config.breadcrumbs) return [];
  
  return config.breadcrumbs.map(breadcrumb => {
    if (breadcrumb.dynamic && params) {
      // Handle dynamic breadcrumb labels based on route parameters
      return {
        ...breadcrumb,
        label: getDynamicBreadcrumbLabel(currentRoute, breadcrumb.label, params)
      };
    }
    return breadcrumb;
  });
};

const getDynamicBreadcrumbLabel = (
  route: string,
  defaultLabel: string,
  params: Record<string, string>
): string => {
  // Custom logic for dynamic breadcrumb labels
  switch (route) {
    case ROUTES.CHAT_CONVERSATION:
      return params.conversationId ? `Conversation ${params.conversationId.slice(0, 8)}...` : defaultLabel;
    case ROUTES.DOCUMENTS_VIEW:
      return params.documentId ? `Document ${params.documentId.slice(0, 8)}...` : defaultLabel;
    default:
      return defaultLabel;
  }
};

// Route parameter validation
export const validateRouteParams = (
  route: string,
  params: Record<string, string>
): boolean => {
  // Add validation logic for route parameters
  switch (route) {
    case ROUTES.CHAT_CONVERSATION:
      return !!params.conversationId && params.conversationId.length > 0;
    case ROUTES.DOCUMENTS_VIEW:
      return !!params.documentId && params.documentId.length > 0;
    default:
      return true;
  }
};

// Default redirect routes
export const DEFAULT_ROUTES = {
  AUTHENTICATED: ROUTES.HOME,
  UNAUTHENTICATED: ROUTES.LOGIN,
  UNAUTHORIZED: ROUTES.UNAUTHORIZED,
  ERROR: ROUTES.ERROR
} as const;