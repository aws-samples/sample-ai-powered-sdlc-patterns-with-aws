import { getApiConfig } from '../config/apiConfig';

class AuthService {
  constructor() {
    this.currentUser = null;
    this.authListeners = [];
    this.tokenRefreshTimer = null;
    this.initializeAuth();
  }

  // Initialize authentication state
  async initializeAuth() {
    try {
      const token = localStorage.getItem('access_token');
      const userInfo = localStorage.getItem('user_info');

      if (token && userInfo) {
        this.currentUser = JSON.parse(userInfo);
        this.setupTokenRefresh();
        this.notifyAuthListeners({ isAuthenticated: true, user: this.currentUser });
      } else {
        this.currentUser = null;
        this.notifyAuthListeners({ isAuthenticated: false, user: null });
      }
    } catch (error) {
      console.log('No authenticated user found');
      this.currentUser = null;
      this.notifyAuthListeners({ isAuthenticated: false, user: null });
    }
  }

  // Sign in user
  async signIn(username, password) {
    try {
      const response = await fetch(`${getApiConfig().baseUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          password: password
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Store tokens and user info
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('id_token', data.id_token || '');
        localStorage.setItem('user_info', JSON.stringify(data.user));
        

        this.currentUser = data.user;
        this.setupTokenRefresh();
        this.notifyAuthListeners({ isAuthenticated: true, user: this.currentUser });

        return {
          success: true,
          user: data.user,
          tokens: {
            accessToken: data.access_token,
            idToken: data.id_token,
            refreshToken: data.refresh_token,
            amazonqToken: data.amazonq_token
          }
        };
      } else {
        return {
          success: false,
          error: data.detail || 'Sign in failed',
          code: data.error || 'AuthenticationError'
        };
      }
    } catch (error) {
      console.error('Sign in error:', error);
      return {
        success: false,
        error: error.message || 'Network error. Please check if the backend server is running.',
        code: 'NetworkError'
      };
    }
  }

  // Sign up new user
  async signUp(userData) {
    try {
      const response = await fetch(`${getApiConfig().baseUrl}/api/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData)
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          message: data.message || 'Account created successfully. Please check your email for confirmation.',
          userSub: data.userSub
        };
      } else {
        return {
          success: false,
          error: data.detail || data.message || 'Sign up failed',
          code: data.error || 'SignUpError'
        };
      }
    } catch (error) {
      console.error('Sign up error:', error);
      return {
        success: false,
        error: error.message || 'Network error. Please check if the backend server is running.',
        code: 'NetworkError'
      };
    }
  }


  // Sign out user - comprehensive approach
  async signOut() {
    try {
      console.log('AuthService: Starting comprehensive sign out...');

      // First, clear all cookies aggressively
      console.log('AuthService: Clearing all cookies...');
      this.clearAllCookies();

      // Clear all localStorage data (not just auth keys)
      console.log('AuthService: Clearing all localStorage...');
      try {
        localStorage.clear();
        console.log('localStorage cleared completely');
      } catch (e) {
        console.warn('Could not clear localStorage:', e);
        // Fallback to removing specific keys
        const authKeys = [
          'access_token', 'refresh_token', 'id_token', 'user_info', 'amazonq_token',
          'auth_state', 'auth_nonce', 'auth_code_verifier', 'auth_session',
          'CognitoIdentityServiceProvider', 'amplify-authenticator-authState'
        ];
        authKeys.forEach(key => {
          localStorage.removeItem(key);
          // Removed localStorage item
        });
      }

      // Clear all sessionStorage data
      console.log('AuthService: Clearing all sessionStorage...');
      try {
        sessionStorage.clear();
        console.log('sessionStorage cleared completely');
      } catch (e) {
        console.warn('Could not clear sessionStorage:', e);
      }

      // Clear any IndexedDB data related to auth
      console.log('AuthService: Clearing IndexedDB auth data...');
      try {
        if ('indexedDB' in window) {
          // Clear common auth-related IndexedDB stores
          const authDatabases = ['amplify', 'aws-amplify', 'cognito'];
          authDatabases.forEach(dbName => {
            const deleteReq = indexedDB.deleteDatabase(dbName);
            deleteReq.onsuccess = () => {};
            deleteReq.onerror = () => {};
          });
        }
      } catch (e) {
        console.warn('Could not clear IndexedDB:', e);
      }

      // Reset internal state
      console.log('AuthService: Resetting internal state...');
      this.currentUser = null;
      this.clearTokenRefresh();
      this.notifyAuthListeners({ isAuthenticated: false, user: null });

      // Clear any AWS Amplify or Cognito specific storage if present
      if (window.AWS && window.AWS.config) {
        console.log('Clearing AWS credentials');
        window.AWS.config.credentials = null;
      }

      // Clear any Amplify Auth cache
      if (window.amplify && window.amplify.Auth) {
        try {
          console.log('Clearing Amplify Auth cache');
          await window.amplify.Auth.signOut({ global: true });
        } catch (e) {
          console.warn('Could not clear Amplify Auth:', e);
        }
      }

      console.log('AuthService: Sign out completed successfully');
      return { success: true };
    } catch (error) {
      console.error('Sign out error:', error);
      return {
        success: false,
        error: error.message || 'Sign out failed'
      };
    }
  }

  // Helper method to clear all cookies aggressively
  clearAllCookies() {
    console.log('Starting aggressive cookie clearing...');

    // Get all cookies
    const cookies = document.cookie.split(';');
    // Clear all cookies

    // Clear each cookie with multiple strategies
    cookies.forEach(cookie => {
      const eqPos = cookie.indexOf('=');
      const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();

      if (!name) return; // Skip empty cookie names

      // Multiple path and domain combinations to ensure complete removal
      const paths = ['/', '/api', '/auth', '/oauth', '/login', '/logout'];
      const currentHostname = window.location.hostname;

      // Strategy 1: Clear for current domain with various paths
      paths.forEach(path => {
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};SameSite=None;Secure`;
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path}`;
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=${currentHostname}`;
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=${currentHostname};SameSite=None;Secure`;
      });

      // Strategy 2: Clear for root domain and subdomains
      const domainParts = currentHostname.split('.');
      if (domainParts.length >= 2) {
        const mainDomain = domainParts.slice(-2).join('.');

        paths.forEach(path => {
          // With dot prefix for subdomain coverage
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=.${mainDomain}`;
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=.${mainDomain};SameSite=None;Secure`;
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=.${currentHostname}`;
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=.${currentHostname};SameSite=None;Secure`;

          // Without dot prefix
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=${mainDomain}`;
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=${mainDomain};SameSite=None;Secure`;
        });
      }

      // Strategy 3: Clear with localhost variations (for development)
      if (currentHostname === 'localhost' || currentHostname === '127.0.0.1') {
        paths.forEach(path => {
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=localhost`;
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=127.0.0.1`;
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path};domain=.localhost`;
        });
      }
    });

    // Verify cookies are cleared
    setTimeout(() => {
      const remainingCookies = document.cookie.split(';').filter(c => c.trim());
      // Verify cookies are cleared
    }, 100);

    console.log('Cookie clearing completed');
  }

  // Get current user
  async getCurrentUser() {
    try {
      if (this.currentUser) {
        return this.currentUser;
      }

      const userInfo = localStorage.getItem('user_info');
      if (userInfo) {
        this.currentUser = JSON.parse(userInfo);
        return this.currentUser;
      }

      return null;
    } catch (error) {
      console.log('No current user:', error);
      return null;
    }
  }

  // Get current session with tokens
  async getCurrentSession() {
    try {
      const accessToken = localStorage.getItem('access_token');
      const idToken = localStorage.getItem('id_token');
      const refreshToken = localStorage.getItem('refresh_token');

      if (!accessToken) {
        return { isValid: false, tokens: null };
      }

      return {
        isValid: true,
        tokens: {
          accessToken,
          idToken,
          refreshToken
        }
      };
    } catch (error) {
      console.error('Get session error:', error);
      return { isValid: false, tokens: null };
    }
  }

  // Get user groups from token
  async getUserGroups() {
    try {
      const user = await this.getCurrentUser();
      return user?.groups || [];
    } catch (error) {
      console.error('Get user groups error:', error);
      return [];
    }
  }

  // Get user profile information
  async getUserProfile() {
    try {
      const authHeader = await this.getAuthHeader();
      if (!authHeader) return null;

      const response = await fetch(`${getApiConfig().baseUrl}/api/auth/profile`, {
        method: 'GET',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const profileData = await response.json();
        return {
          username: profileData.username,
          email: profileData.email,
          firstName: profileData.firstName || profileData.username || 'User',
          lastName: profileData.lastName || '',
          sdlcRole: profileData.sdlcRole || '',

          groups: profileData.groups || [],
          emailVerified: profileData.emailVerified !== false
        };
      } else {
        console.error('Failed to fetch user profile:', response.status);
        return null;
      }
    } catch (error) {
      console.error('Get user profile error:', error);
      return null;
    }
  }

  // Check if user is authenticated
  async isAuthenticated() {
    try {
      const session = await this.getCurrentSession();
      return session.isValid;
    } catch (error) {
      return false;
    }
  }

  // Check if user has specific group
  async hasGroup(groupName) {
    try {
      const groups = await this.getUserGroups();
      return groups.includes(groupName);
    } catch (error) {
      return false;
    }
  }

  // Setup automatic token refresh
  setupTokenRefresh() {
    this.clearTokenRefresh();

    // Refresh token every 50 minutes (tokens expire in 60 minutes)
    this.tokenRefreshTimer = setInterval(async () => {
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          console.log('No refresh token available, signing out');
          await this.signOut();
          return;
        }

        console.log('Attempting scheduled token refresh...');
        const response = await fetch(`${getApiConfig().baseUrl}/api/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            refresh_token: refreshToken
          })
        });

        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('access_token', data.access_token);
          if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
          }
          console.log('Scheduled token refresh successful');
        } else {
          console.error('Scheduled token refresh failed:', response.status);
          // Don't immediately sign out on scheduled refresh failure
          // The API service will handle individual request failures
          console.log('Will retry on next API request');
        }
      } catch (error) {
        console.error('Scheduled token refresh error:', error);
        // Don't immediately sign out on network errors during scheduled refresh
        console.log('Will retry on next API request');
      }
    }, 50 * 60 * 1000); // 50 minutes
  }

  // Clear token refresh timer
  clearTokenRefresh() {
    if (this.tokenRefreshTimer) {
      clearInterval(this.tokenRefreshTimer);
      this.tokenRefreshTimer = null;
    }
  }

  // Add authentication state listener
  addAuthListener(callback) {
    this.authListeners.push(callback);
    return () => {
      this.authListeners = this.authListeners.filter(listener => listener !== callback);
    };
  }

  // Notify all auth listeners
  notifyAuthListeners(authState) {
    this.authListeners.forEach(callback => {
      try {
        callback(authState);
      } catch (error) {
        console.error('Auth listener error:', error);
      }
    });
  }

  // Get authorization header for API requests
  async getAuthHeader() {
    try {
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        return `Bearer ${accessToken}`;
      }
      return null;
    } catch (error) {
      console.error('Get auth header error:', error);
      return null;
    }
  }

  // Get ID token for Amazon Q Business authentication
  async getIdToken() {
    try {
      const idToken = localStorage.getItem('id_token');
      return idToken;
    } catch (error) {
      console.error('Get ID token error:', error);
      return null;
    }
  }

  // Get Amazon Q token
  async getAmazonQToken() {
    try {
      const amazonqToken = localStorage.getItem('amazonq_token');
      return amazonqToken;
    } catch (error) {
      console.error('Get Amazon Q token error:', error);
      return null;
    }
  }

  // Cleanup on app unmount
  cleanup() {
    this.clearTokenRefresh();
    this.authListeners = [];
  }
}

// Create singleton instance
const authService = new AuthService();

export default authService;