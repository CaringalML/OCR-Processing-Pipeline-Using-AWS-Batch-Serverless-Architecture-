/**
 * Authentication service for Cognito integration
 * Handles user signup, signin, verification, and token management
 */

import { Amplify } from 'aws-amplify';
import { signUp, signIn, confirmSignUp, signOut, getCurrentUser, fetchAuthSession, resendSignUpCode } from '@aws-amplify/auth';

// Configure Amplify for Cognito
const configureAmplify = () => {
  // These values will be populated from Terraform outputs or environment variables
  const cognitoConfig = {
    Auth: {
      Cognito: {
        userPoolId: process.env.REACT_APP_USER_POOL_ID || 'us-east-1_CHANGEME',
        userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || 'CHANGEME',
        region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
        signUpVerificationMethod: 'code',
        loginWith: {
          email: true
        }
      }
    }
  };

  Amplify.configure(cognitoConfig);
};

// Initialize Amplify
configureAmplify();

class AuthService {
  constructor() {
    this.user = null;
    this.isAuthenticated = false;
    this.loading = false;
  }

  /**
   * Sign up a new user
   */
  async signUp({ email, password, name, organization = '' }) {
    try {
      const { user, nextStep } = await signUp({
        username: email,
        password,
        options: {
          userAttributes: {
            email: email,
            name: name,
            'custom:organization': organization
          }
        }
      });

      return {
        success: true,
        user: user,
        nextStep: nextStep,
        message: 'Registration successful! Please check your email for verification code.'
      };
    } catch (error) {
      console.error('Signup error:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  /**
   * Verify email with confirmation code
   */
  async verifyEmail({ email, code }) {
    try {
      const { nextStep } = await confirmSignUp({
        username: email,
        confirmationCode: code
      });

      return {
        success: true,
        nextStep: nextStep,
        message: 'Email verified successfully! You can now sign in.'
      };
    } catch (error) {
      console.error('Verification error:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  /**
   * Resend verification code
   */
  async resendVerificationCode(email) {
    try {
      await resendSignUpCode({
        username: email
      });

      return {
        success: true,
        message: 'Verification code sent to your email.'
      };
    } catch (error) {
      console.error('Resend code error:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  /**
   * Sign in user
   */
  async signIn({ email, password }) {
    try {
      const { isSignedIn, nextStep } = await signIn({
        username: email,
        password
      });

      if (isSignedIn) {
        await this.loadCurrentUser();
        return {
          success: true,
          user: this.user,
          message: 'Signed in successfully!'
        };
      } else {
        return {
          success: false,
          nextStep: nextStep,
          error: 'Additional verification required'
        };
      }
    } catch (error) {
      console.error('Signin error:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  /**
   * Sign out user
   */
  async signOut() {
    try {
      await signOut();
      this.user = null;
      this.isAuthenticated = false;
      
      return {
        success: true,
        message: 'Signed out successfully!'
      };
    } catch (error) {
      console.error('Signout error:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  /**
   * Get current authenticated user
   */
  async loadCurrentUser() {
    try {
      this.loading = true;
      const user = await getCurrentUser();
      
      if (user) {
        this.user = {
          userId: user.userId,
          username: user.username,
          email: user.signInDetails?.loginId || user.username,
          name: user.name || ''
        };
        this.isAuthenticated = true;
      }
      
      return this.user;
    } catch (error) {
      console.error('Load user error:', error);
      this.user = null;
      this.isAuthenticated = false;
      return null;
    } finally {
      this.loading = false;
    }
  }

  /**
   * Get current session and tokens
   */
  async getSession() {
    try {
      const session = await fetchAuthSession();
      return {
        accessToken: session.tokens?.accessToken?.toString(),
        idToken: session.tokens?.idToken?.toString(),
        refreshToken: session.tokens?.refreshToken?.toString()
      };
    } catch (error) {
      console.error('Get session error:', error);
      return null;
    }
  }

  /**
   * Get access token for API requests
   */
  async getAccessToken() {
    try {
      const session = await this.getSession();
      return session?.accessToken;
    } catch (error) {
      console.error('Get access token error:', error);
      return null;
    }
  }

  /**
   * Check if user is authenticated
   */
  async isUserAuthenticated() {
    try {
      await this.loadCurrentUser();
      return this.isAuthenticated;
    } catch (error) {
      return false;
    }
  }

  /**
   * Format error messages for display
   */
  formatError(error) {
    if (error.name === 'UserNotConfirmedException') {
      return 'Please verify your email address before signing in.';
    } else if (error.name === 'NotAuthorizedException') {
      return 'Invalid email or password.';
    } else if (error.name === 'UserNotFoundException') {
      return 'No account found with this email address.';
    } else if (error.name === 'InvalidPasswordException') {
      return 'Password must be at least 8 characters with uppercase, lowercase, numbers, and symbols.';
    } else if (error.name === 'UsernameExistsException') {
      return 'An account with this email already exists.';
    } else if (error.name === 'CodeMismatchException') {
      return 'Invalid verification code.';
    } else if (error.name === 'ExpiredCodeException') {
      return 'Verification code has expired. Please request a new one.';
    } else if (error.name === 'LimitExceededException') {
      return 'Too many requests. Please try again later.';
    } else if (error.name === 'TooManyRequestsException') {
      return 'Too many requests. Please try again later.';
    } else if (error.message) {
      return error.message;
    } else {
      return 'An unexpected error occurred. Please try again.';
    }
  }

  /**
   * Get current user info
   */
  getCurrentUser() {
    return this.user;
  }

  /**
   * Check authentication status
   */
  getAuthStatus() {
    return {
      isAuthenticated: this.isAuthenticated,
      user: this.user,
      loading: this.loading
    };
  }
}

// Create singleton instance
const authService = new AuthService();

export default authService;