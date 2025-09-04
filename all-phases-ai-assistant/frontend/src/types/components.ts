// TypeScript interfaces for React components
// These interfaces define props and state for React components

import { ReactNode } from 'react';
import {
    AuthenticationState,
    ChatMessage,
    DocumentMetadata,
    DocumentSource,
    KnowledgeBaseMetrics,
    UserRole
} from './api';

// Layout component interfaces
export interface LayoutProps {
  children: ReactNode;
  title?: string;
  showSidebar?: boolean;
  showHeader?: boolean;
}

export interface HeaderProps {
  user?: {
    email: string;
    role: UserRole;
  } | undefined;
  onLogout: () => void;
  showUserMenu?: boolean;
}

export interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  currentPath: string;
  userRole: UserRole;
}

export interface NavigationItem {
  path: string;
  label: string;
  icon?: string;
  roles: UserRole[];
  children?: NavigationItem[];
}

// Authentication component interfaces
export interface LoginFormProps {
  onLogin: (email: string, password: string) => Promise<void>;
  isLoading: boolean;
  error?: string;
}

export interface AuthGuardProps {
  children: ReactNode;
  requiredRole?: UserRole;
  fallback?: ReactNode;
}

export interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: UserRole;
  redirectTo?: string;
}

// Chat component interfaces
export interface ChatInterfaceProps {
  conversationId?: string | undefined;
  onNewConversation?: () => void;
  maxHeight?: string;
}

export interface ChatMessageProps {
  message: ChatMessage;
  isLoading?: boolean;
  showSources?: boolean;
  onSourceClick?: ((source: DocumentSource) => void) | undefined;
}

export interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  onSourceClick?: ((source: DocumentSource) => void) | undefined;
  onRetry?: ((messageId: string) => void) | undefined;
}

export interface SourceCitationProps {
  sources: DocumentSource[];
  onSourceClick?: ((source: DocumentSource) => void) | undefined;
  maxSources?: number;
  showConfidence?: boolean;
}

export interface TypingIndicatorProps {
  isVisible: boolean;
  text?: string;
}

// Document management component interfaces
export interface DocumentUploadProps {
  onUploadComplete: (documents: DocumentMetadata[]) => void;
  onUploadError: (error: string) => void;
  acceptedFileTypes?: string[];
  maxFileSize?: number;
  maxFiles?: number;
  showProgress?: boolean;
}

export interface DocumentListProps {
  documents: DocumentMetadata[];
  onDocumentSelect?: (document: DocumentMetadata) => void;
  onDocumentDelete?: (documentId: string) => void;
  onRefresh?: () => void;
  isLoading?: boolean;
  showActions?: boolean;
  userRole: UserRole;
}

export interface DocumentItemProps {
  document: DocumentMetadata;
  onSelect?: (document: DocumentMetadata) => void;
  onDelete?: (documentId: string) => void;
  showActions?: boolean;
  userRole: UserRole;
}

export interface DocumentStatusBadgeProps {
  status: DocumentMetadata['status'];
  knowledgeBaseStatus: DocumentMetadata['knowledgeBaseStatus'];
  size?: 'small' | 'medium' | 'large';
}

export interface FileUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  acceptedFileTypes: string[];
  maxFileSize: number;
  maxFiles: number;
  disabled?: boolean;
}

export interface UploadProgressProps {
  files: UploadingFile[];
  onCancel?: (fileId: string) => void;
  onRetry?: (fileId: string) => void;
}

export interface UploadingFile {
  id: string;
  file: File;
  progress: number;
  status: 'uploading' | 'processing' | 'complete' | 'error';
  error?: string;
}

// Admin component interfaces
export interface AdminDashboardProps {
  metrics: KnowledgeBaseMetrics;
  onRefresh: () => void;
  isLoading?: boolean;
}

export interface UserManagementProps {
  onUserRoleChange: (userId: string, newRole: UserRole) => void;
  onUserDelete: (userId: string) => void;
  currentUserRole: UserRole;
}

export interface KnowledgeBaseManagementProps {
  onSyncTrigger: () => void;
  onJobCancel: (jobId: string) => void;
  onJobRetry: (jobId: string) => void;
  isLoading?: boolean;
}

export interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
  icon?: string;
  color?: 'primary' | 'success' | 'warning' | 'error';
}

// Form component interfaces
export interface FormFieldProps {
  label: string;
  name: string;
  type?: 'text' | 'email' | 'password' | 'select' | 'textarea';
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
}

export interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  isLoading?: boolean;
  icon?: string;
  fullWidth?: boolean;
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'small' | 'medium' | 'large' | 'fullscreen';
  closeOnOverlayClick?: boolean;
  showCloseButton?: boolean;
}

export interface AlertProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  title?: string;
  onClose?: () => void;
  autoClose?: boolean;
  duration?: number;
}

// Table component interfaces
export interface TableProps<T = any> {
  data: T[];
  columns: TableColumn<T>[];
  onRowClick?: (row: T) => void;
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  isLoading?: boolean;
  emptyMessage?: string;
  pagination?: PaginationProps;
}

export interface TableColumn<T = any> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: any, row: T) => ReactNode;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange?: (itemsPerPage: number) => void;
  showItemsPerPage?: boolean;
}

// Search and filter component interfaces
export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: (query: string) => void;
  placeholder?: string;
  isLoading?: boolean;
  showFilters?: boolean;
  onFilterToggle?: () => void;
}

export interface FilterPanelProps {
  filters: FilterConfig[];
  values: Record<string, any>;
  onChange: (filterKey: string, value: any) => void;
  onReset: () => void;
  onApply: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export interface FilterConfig {
  key: string;
  label: string;
  type: 'text' | 'select' | 'date' | 'daterange' | 'multiselect';
  options?: { value: string; label: string }[];
  placeholder?: string;
}

// Loading and error component interfaces
export interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  text?: string;
}

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: any) => void;
}

export interface ErrorMessageProps {
  error: string | Error;
  onRetry?: () => void;
  showDetails?: boolean;
}

// Utility component interfaces
export interface TooltipProps {
  children: ReactNode;
  content: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
}

export interface ConfirmDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
}

// Context interfaces
export interface AuthContextValue {
  authState: AuthenticationState;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  isLoading: boolean;
  error?: string | undefined;
}

export interface ThemeContextValue {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  colors: Record<string, string>;
  spacing: Record<string, string>;
  breakpoints: Record<string, string>;
}

export interface NotificationContextValue {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  timestamp: string;
  autoClose?: boolean;
  duration?: number;
}

// Hook interfaces
export interface UseApiOptions {
  immediate?: boolean;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
  retries?: number;
  retryDelay?: number;
}

export interface UseApiResult<T = any> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  execute: (...args: any[]) => Promise<T>;
  reset: () => void;
}

export interface UsePaginationOptions {
  initialPage?: number;
  initialItemsPerPage?: number;
  totalItems: number;
}

export interface UsePaginationResult {
  currentPage: number;
  itemsPerPage: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  goToPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  setItemsPerPage: (itemsPerPage: number) => void;
}

// Route interfaces
export interface RouteConfig {
  path: string;
  component: React.ComponentType<any>;
  exact?: boolean;
  requiredRole?: UserRole;
  title?: string;
  showInNavigation?: boolean;
  icon?: string;
}

export interface BreadcrumbItem {
  label: string;
  path?: string;
  isActive?: boolean;
}