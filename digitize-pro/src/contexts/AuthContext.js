/**
 * Authentication Context Provider
 * Provides authentication state and methods throughout the app
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import authService from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  // Initialize authentication state
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setLoading(true);
        const currentUser = await authService.loadCurrentUser();
        
        if (currentUser) {
          setUser(currentUser);
          setIsAuthenticated(true);
        } else {
          setUser(null);
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
        setInitialized(true);
      }
    };

    initializeAuth();
  }, []);

  // Sign up function
  const signUp = async (userData) => {
    try {
      setLoading(true);
      const result = await authService.signUp(userData);
      return result;
    } catch (error) {
      console.error('Signup error:', error);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  // Verify email function
  const verifyEmail = async (verificationData) => {
    try {
      setLoading(true);
      const result = await authService.verifyEmail(verificationData);
      return result;
    } catch (error) {
      console.error('Verification error:', error);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  // Resend verification code
  const resendVerificationCode = async (email) => {
    try {
      const result = await authService.resendVerificationCode(email);
      return result;
    } catch (error) {
      console.error('Resend code error:', error);
      return { success: false, error: error.message };
    }
  };

  // Sign in function
  const signIn = async (credentials) => {
    try {
      setLoading(true);
      const result = await authService.signIn(credentials);
      
      if (result.success && result.user) {
        setUser(result.user);
        setIsAuthenticated(true);
      }
      
      return result;
    } catch (error) {
      console.error('Signin error:', error);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  // Sign out function
  const signOut = async () => {
    try {
      setLoading(true);
      const result = await authService.signOut();
      
      if (result.success) {
        setUser(null);
        setIsAuthenticated(false);
      }
      
      return result;
    } catch (error) {
      console.error('Signout error:', error);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  // Get access token
  const getAccessToken = async () => {
    try {
      return await authService.getAccessToken();
    } catch (error) {
      console.error('Get token error:', error);
      return null;
    }
  };

  // Refresh user data
  const refreshUser = async () => {
    try {
      const currentUser = await authService.loadCurrentUser();
      if (currentUser) {
        setUser(currentUser);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
      return currentUser;
    } catch (error) {
      console.error('Refresh user error:', error);
      setUser(null);
      setIsAuthenticated(false);
      return null;
    }
  };

  // Check if user has permission for a feature (can be extended later)
  const hasPermission = (permission) => {
    // For now, all authenticated users have all permissions
    // This can be extended later for role-based access
    return isAuthenticated;
  };

  const value = {
    // State
    user,
    isAuthenticated,
    loading,
    initialized,

    // Methods
    signUp,
    verifyEmail,
    resendVerificationCode,
    signIn,
    signOut,
    getAccessToken,
    refreshUser,
    hasPermission,

    // Helper getters
    userEmail: user?.email || '',
    userName: user?.name || '',
    userOrganization: user?.organization || '',
    userId: user?.userId || ''
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;