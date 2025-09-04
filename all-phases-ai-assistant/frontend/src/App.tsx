// Main React application component with routing and authentication
// Provides the core application structure with protected routes

import { Amplify } from 'aws-amplify';
import React, { useEffect } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';

// Configuration
import { AMPLIFY_CONFIG } from './config/aws-config';

// Context providers
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { ThemeProvider } from './contexts/ThemeContext';

// Components
import { AuthGuard } from './components/auth/AuthGuard';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Layout } from './components/layout/Layout';

// Pages
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage';
import { AdminKnowledgeBasePage } from './pages/admin/AdminKnowledgeBasePage';
import { AdminPage } from './pages/admin/AdminPage';
import { AdminUsersPage } from './pages/admin/AdminUsersPage';
import { CallbackPage } from './pages/auth/CallbackPage';
import { LoginPage } from './pages/auth/LoginPage';
import { LogoutPage } from './pages/auth/LogoutPage';
import { ChatPage } from './pages/chat/ChatPage';
import { ConversationPage } from './pages/chat/ConversationPage';
import { DocumentsPage } from './pages/documents/DocumentsPage';
import { DocumentUploadPage } from './pages/documents/DocumentUploadPage';
import { DocumentViewPage } from './pages/documents/DocumentViewPage';
import { ErrorPage } from './pages/error/ErrorPage';
import { NotFoundPage } from './pages/error/NotFoundPage';
import { UnauthorizedPage } from './pages/error/UnauthorizedPage';
import { HomePage } from './pages/HomePage';
import { ProfilePage } from './pages/user/ProfilePage';

// Route constants
import { ROUTES } from './types/routes';

// Styles
import './App.css';

// Configure AWS Amplify
Amplify.configure(AMPLIFY_CONFIG);

const App: React.FC = () => {
  useEffect(() => {
    // Set up global error handling
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection:', event.reason);
      // You could send this to a logging service
    };

    const handleError = (event: ErrorEvent) => {
      console.error('Global error:', event.error);
      // You could send this to a logging service
    };

    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    window.addEventListener('error', handleError);

    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      window.removeEventListener('error', handleError);
    };
  }, []);

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <NotificationProvider>
          <AuthProvider>
            <Router>
              <div className="app">
                <Routes>
                  {/* Public routes */}
                  <Route path={ROUTES.LOGIN} element={<LoginPage />} />
                  <Route path={ROUTES.CALLBACK} element={<CallbackPage />} />
                  <Route path={ROUTES.LOGOUT} element={<LogoutPage />} />
                  <Route path={ROUTES.UNAUTHORIZED} element={<UnauthorizedPage />} />
                  <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
                  <Route path={ROUTES.ERROR} element={<ErrorPage />} />

                  {/* Protected routes with layout */}
                  <Route
                    path="/*"
                    element={
                      <AuthGuard>
                        <Layout>
                          <Routes>
                            {/* Main application routes */}
                            <Route path={ROUTES.HOME} element={<HomePage />} />
                            
                            {/* Chat routes */}
                            <Route path={ROUTES.CHAT} element={<ChatPage />} />
                            <Route path={ROUTES.CHAT_NEW} element={<ChatPage />} />
                            <Route 
                              path={ROUTES.CHAT_CONVERSATION} 
                              element={<ConversationPage />} 
                            />
                            
                            {/* Document routes */}
                            <Route path={ROUTES.DOCUMENTS} element={<DocumentsPage />} />
                            <Route 
                              path={ROUTES.DOCUMENTS_UPLOAD} 
                              element={<DocumentUploadPage />} 
                            />
                            <Route 
                              path={ROUTES.DOCUMENTS_VIEW} 
                              element={<DocumentViewPage />} 
                            />
                            
                            {/* User profile routes */}
                            <Route path={ROUTES.PROFILE} element={<ProfilePage />} />
                            
                            {/* Admin routes - require admin role */}
                            <Route
                              path={ROUTES.ADMIN}
                              element={
                                <ProtectedRoute requiredRole="admin">
                                  <AdminPage />
                                </ProtectedRoute>
                              }
                            />
                            <Route
                              path={ROUTES.ADMIN_DASHBOARD}
                              element={
                                <ProtectedRoute requiredRole="admin">
                                  <AdminDashboardPage />
                                </ProtectedRoute>
                              }
                            />
                            <Route
                              path={ROUTES.ADMIN_USERS}
                              element={
                                <ProtectedRoute requiredRole="admin">
                                  <AdminUsersPage />
                                </ProtectedRoute>
                              }
                            />
                            <Route
                              path={ROUTES.ADMIN_KNOWLEDGE_BASE}
                              element={
                                <ProtectedRoute requiredRole="admin">
                                  <AdminKnowledgeBasePage />
                                </ProtectedRoute>
                              }
                            />
                            
                            {/* Default redirect to home */}
                            <Route path="/" element={<Navigate to={ROUTES.HOME} replace />} />
                            
                            {/* Catch all - redirect to 404 */}
                            <Route path="*" element={<Navigate to={ROUTES.NOT_FOUND} replace />} />
                          </Routes>
                        </Layout>
                      </AuthGuard>
                    }
                  />
                </Routes>
              </div>
            </Router>
          </AuthProvider>
        </NotificationProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;