import React from 'react';
import { TopNavigation } from '@cloudscape-design/components';
import { useAuth } from '../../contexts/AuthContext';
import { AuthModal, useAuthModal } from '../UI/AuthModal';
import { getSiteName, getSiteTagline, getNavigationItems } from '../../utils/contentLoader';

const AppNavigation = ({ currentPath = '/', onNavigate }) => {
  const { isAuthenticated, userProfile, loading, signOut } = useAuth();
  const { isOpen, openSignIn, openProfile, closeModal } = useAuthModal();

  // Update navigation items with active state based on current path
  const navigationItems = getNavigationItems().map(item => ({
    ...item,
    active: item.href === currentPath
  }));

  const handleNavigate = (event) => {
    console.log('Navigation event:', event);
    
    // Prevent default navigation for all events
    if (event.preventDefault) {
      event.preventDefault();
    }
    
    const href = event.detail ? event.detail.href : event.href;
    const id = event.detail ? event.detail.id : event.id;
    
    console.log('Navigation - href:', href, 'id:', id);
    
    // Handle special actions first
    if (id === 'signout') {
      console.log('Handling sign out');
      handleSignOut();
      return;
    }
    if (id === 'profile' || href === '#profile') {
      console.log('Handling profile');
      openProfile();
      return;
    }
    
    // Handle regular navigation
    if (onNavigate && href && !href.startsWith('#')) {
      onNavigate(href);
    }
  };

  const handleIdentityClick = (event) => {
    if (event.preventDefault) {
      event.preventDefault();
    }
    if (onNavigate) {
      onNavigate('/');
    }
  };

  const handleAuthClick = () => {
    if (isAuthenticated) {
      openProfile();
    } else {
      openSignIn();
    }
  };

  const handleSignOut = async () => {
    console.log('Sign out clicked - starting immediate cleanup');
    
    try {
      // Prevent default navigation to #signout
      if (window.location.hash === '#signout') {
        window.history.replaceState(null, '', window.location.pathname);
      }
      
      // Start the sign out process
      console.log('Calling signOut function...');
      const result = await signOut();
      console.log('Sign out result:', result);
      
    } catch (error) {
      console.error('Sign out error:', error);
    }
    
    // Always force a complete page reload regardless of the result
    // This ensures we start fresh even if the sign out process had issues
    console.log('Forcing page reload to complete sign out...');
    
    // Use multiple strategies to ensure the page reloads
    setTimeout(() => {
      // Strategy 1: Replace current location
      window.location.replace('/');
    }, 100);
    
    setTimeout(() => {
      // Strategy 2: Assign new location (fallback)
      window.location.assign('/');
    }, 200);
    
    setTimeout(() => {
      // Strategy 3: Hard reload (last resort)
      window.location.reload(true);
    }, 300);
  };

  // Create utilities array with navigation items and auth controls
  const utilities = [
    ...navigationItems.map(item => ({
      type: 'button',
      text: item.text,
      href: item.href,
      active: item.active,
      onClick: handleNavigate
    }))
  ];

  // Add authentication controls
  if (loading) {
    utilities.push({
      type: 'button',
      text: 'Loading...',
      disabled: true
    });
  } else if (isAuthenticated && userProfile) {
    const displayName = userProfile.firstName && userProfile.lastName 
      ? `${userProfile.firstName} ${userProfile.lastName}`.trim()
      : userProfile.firstName || userProfile.username || 'User';
    
    utilities.push({
      type: 'menu-dropdown',
      text: displayName,
      description: userProfile.groups?.join(', ') || 'No groups',
      iconName: 'user-profile',
      items: [
        {
          id: 'profile',
          text: 'Profile',
          href: '#profile'
        },
        {
          id: 'divider',
          type: 'divider'
        },
        {
          id: 'signout',
          text: 'Sign Out'
        }
      ],
      onItemClick: ({ detail }) => {
        console.log('Dropdown item clicked:', detail);
        if (detail.id === 'signout') {
          console.log('Sign out item clicked directly');
          handleSignOut();
        } else if (detail.id === 'profile') {
          console.log('Profile item clicked');
          openProfile();
        }
      }
    });
  } else {
    utilities.push(
      {
        type: 'button',
        text: 'Sign In',
        onClick: handleAuthClick
      },
      {
        type: 'button',
        text: 'Sign Up',
        variant: 'primary',
        onClick: () => {
          if (onNavigate) {
            onNavigate('/signup');
          }
        }
      }
    );
  }

  return (
    <>
      <TopNavigation
        identity={{
          href: '/',
          title: getSiteName(),
          logo: null, // We can update this later if needed
          alt: `${getSiteName()} logo`,
          onFollow: handleIdentityClick
        }}
        utilities={utilities}
        onFollow={handleNavigate}
      />
      <AuthModal
        isOpen={isOpen}
        onClose={closeModal}
        initialMode={isAuthenticated ? 'profile' : 'signin'}
      />
    </>
  );
};

export default AppNavigation;