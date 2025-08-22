import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { initializeTheme } from './styles/theme';
import { AppNavigation } from './components/Navigation';
import { AppLayout, Footer } from './components/Layout';
import { HomePage, ProjectTemplatePage, AboutPage, SignUpPage, UserProfilePage } from './components/Pages';
import CreateProject from './components/Pages/CreateProject';
import ProjectsPage from './components/Pages/ProjectsPage';
import { ErrorBoundary, LoadingSpinner, TestComponent, AuthGuard } from './components/UI';
import AuthErrorNotification from './components/UI/AuthErrorNotification';
import { AuthProvider } from './contexts/AuthContext';
import { getSiteName, getFooterLinks } from './utils/contentLoader';
import { updateDocumentTitle } from './utils/documentTitle';
import './App.css';

function AppContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [navigationError, setNavigationError] = useState(null);
  
  // Update document title when location changes
  useEffect(() => {
    const pageTitles = {
      '/': '',
      '/about': 'About',
      '/services': 'Services',
      '/contact': 'Contact'
    };
    
    const pageTitle = pageTitles[location.pathname] || '';
    updateDocumentTitle(pageTitle);
  }, [location]);

  useEffect(() => {
    try {
      initializeTheme();
      // Update document title
      updateDocumentTitle();
      // Simulate initial loading
      const timer = setTimeout(() => {
        setIsLoading(false);
      }, 500);
      
      return () => clearTimeout(timer);
    } catch (error) {
      console.error('Error initializing app:', error);
      setNavigationError('Failed to initialize application');
      setIsLoading(false);
    }
  }, []);

  const handleNavigate = (href) => {
    try {
      setNavigationError(null);
      navigate(href);
    } catch (error) {
      console.error('Navigation error:', error);
      setNavigationError('Navigation failed');
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="large" text={`Loading ${getSiteName()}...`} />;
  }

  return (
    <ErrorBoundary>
      <AppNavigation 
        currentPath={location.pathname} 
        onNavigate={handleNavigate} 
      />
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route 
            path="/profile" 
            element={
              <AuthGuard requiredGroups={['developers', 'developers-mobile-app', 'developers-web-app', 'qa-team', 'admins']}>
                <UserProfilePage />
              </AuthGuard>
            } 
          />
          <Route path="/test" element={<TestComponent />} />
          <Route 
            path="/projects" 
            element={
              <AuthGuard requiredGroups={['developers', 'developers-mobile-app', 'developers-web-app', 'qa-team', 'admins']}>
                <ProjectsPage />
              </AuthGuard>
            } 
          />
          <Route 
            path="/create-project" 
            element={
              <AuthGuard requiredGroups={['developers', 'developers-mobile-app', 'developers-web-app', 'admins']}>
                <CreateProject />
              </AuthGuard>
            } 
          />
          <Route 
            path="/project/:projectName" 
            element={
              <AuthGuard requiredGroups={['developers', 'developers-mobile-app', 'developers-web-app', 'qa-team', 'admins']}>
                <ProjectTemplatePage />
              </AuthGuard>
            } 
          />

        </Routes>
        <Footer links={getFooterLinks()} />
      </AppLayout>
      
      {/* Global auth error notification */}
      <AuthErrorNotification />
    </ErrorBoundary>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
