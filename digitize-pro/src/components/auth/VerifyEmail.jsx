/**
 * Email Verification Component
 * Handles email verification with 6-digit code input and resend functionality
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Mail, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';

const VerifyEmail = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { verifyEmail, resendVerificationCode, loading } = useAuth();
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [email, setEmail] = useState('');
  const [resendCooldown, setResendCooldown] = useState(0);
  const codeRefs = useRef([]);

  // Get email from location state or redirect
  useEffect(() => {
    const emailFromState = location.state?.email;
    if (emailFromState) {
      setEmail(emailFromState);
    } else {
      // No email provided, redirect to signup
      navigate('/signup');
    }

    // Show welcome message if coming from signup
    if (location.state?.fromSignup) {
      setMessage({
        type: 'success',
        text: 'Account created successfully! Please check your email for the verification code.'
      });
    }
  }, [location.state, navigate]);

  // Handle code input changes
  const handleCodeChange = (index, value) => {
    // Only allow single digits
    if (value.length > 1) return;
    
    // Update code array
    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    // Auto-focus next input
    if (value && index < 5) {
      codeRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all fields are filled
    if (newCode.every(digit => digit !== '') && newCode.join('').length === 6) {
      handleSubmit(newCode.join(''));
    }
  };

  // Handle backspace
  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      codeRefs.current[index - 1]?.focus();
    }
  };

  // Handle paste
  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    
    if (pastedData.length === 6) {
      const newCode = pastedData.split('');
      setCode(newCode);
      handleSubmit(pastedData);
    }
  };

  // Submit verification
  const handleSubmit = async (codeString = code.join('')) => {
    if (codeString.length !== 6) {
      setMessage({
        type: 'error',
        text: 'Please enter a complete 6-digit verification code.'
      });
      return;
    }

    try {
      setSubmitLoading(true);
      setMessage({ type: '', text: '' });

      const result = await verifyEmail({
        email: email,
        code: codeString
      });

      if (result.success) {
        setMessage({
          type: 'success',
          text: result.message
        });

        // Navigate to signin after short delay
        setTimeout(() => {
          navigate('/signin', {
            state: {
              email: email,
              message: 'Email verified successfully! You can now sign in.',
              messageType: 'success'
            }
          });
        }, 2000);
      } else {
        setMessage({
          type: 'error',
          text: result.error
        });
        
        // Clear code on error
        setCode(['', '', '', '', '', '']);
        codeRefs.current[0]?.focus();
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'An unexpected error occurred. Please try again.'
      });
    } finally {
      setSubmitLoading(false);
    }
  };

  // Resend verification code
  const handleResend = async () => {
    if (resendCooldown > 0) return;

    try {
      setResendLoading(true);
      setMessage({ type: '', text: '' });

      const result = await resendVerificationCode(email);

      if (result.success) {
        setMessage({
          type: 'success',
          text: result.message
        });

        // Start cooldown
        setResendCooldown(60);
        const countdown = setInterval(() => {
          setResendCooldown(prev => {
            if (prev <= 1) {
              clearInterval(countdown);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } else {
        setMessage({
          type: 'error',
          text: result.error
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Failed to resend code. Please try again.'
      });
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Back Button */}
        <div className="flex justify-start mb-4">
          <Link
            to="/signup"
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Sign Up
          </Link>
        </div>

        {/* Logo */}
        <div className="flex justify-center">
          <div className="bg-blue-600 rounded-lg p-3">
            <Mail className="h-8 w-8 text-white" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Verify Your Email
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          We've sent a 6-digit verification code to
          <br />
          <span className="font-medium text-gray-900">{email}</span>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* Alert Messages */}
          {message.text && (
            <div className={`mb-6 p-4 rounded-md ${
              message.type === 'error' 
                ? 'bg-red-50 border border-red-200' 
                : 'bg-green-50 border border-green-200'
            }`}>
              <div className="flex">
                <div className="flex-shrink-0">
                  {message.type === 'error' ? (
                    <AlertCircle className="h-5 w-5 text-red-400" />
                  ) : (
                    <CheckCircle className="h-5 w-5 text-green-400" />
                  )}
                </div>
                <div className="ml-3">
                  <div className={`text-sm font-medium ${
                    message.type === 'error' ? 'text-red-800' : 'text-green-800'
                  }`}>
                    {message.text}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Verification Code Input */}
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 text-center mb-4">
                Enter Verification Code
              </label>
              <div className="flex justify-center space-x-3">
                {code.map((digit, index) => (
                  <input
                    key={index}
                    ref={el => codeRefs.current[index] = el}
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]"
                    maxLength="1"
                    value={digit}
                    onChange={e => handleCodeChange(index, e.target.value.replace(/\D/g, ''))}
                    onKeyDown={e => handleKeyDown(index, e)}
                    onPaste={handlePaste}
                    className="w-12 h-12 text-center text-xl font-semibold border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={submitLoading || loading}
                  />
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <div>
              <button
                type="button"
                onClick={() => handleSubmit()}
                disabled={submitLoading || loading || code.some(digit => !digit)}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitLoading || loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Verifying...
                  </>
                ) : (
                  'Verify Email'
                )}
              </button>
            </div>

            {/* Resend Code */}
            <div className="text-center">
              <p className="text-sm text-gray-600">
                Didn't receive the code?{' '}
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendLoading || resendCooldown > 0}
                  className="font-medium text-blue-600 hover:text-blue-500 disabled:text-gray-400 disabled:cursor-not-allowed"
                >
                  {resendLoading ? (
                    'Sending...'
                  ) : resendCooldown > 0 ? (
                    `Resend in ${resendCooldown}s`
                  ) : (
                    'Resend Code'
                  )}
                </button>
              </p>
            </div>

            {/* Help Text */}
            <div className="text-center">
              <p className="text-xs text-gray-500">
                Check your spam folder if you don't see the email.
                <br />
                The code expires in 24 hours.
              </p>
            </div>

            {/* Additional Links */}
            <div className="text-center space-y-2">
              <div className="text-sm">
                <Link
                  to="/signin"
                  className="font-medium text-blue-600 hover:text-blue-500"
                >
                  Already verified? Sign in
                </Link>
              </div>
              <div className="text-sm">
                <Link
                  to="/signup"
                  className="font-medium text-blue-600 hover:text-blue-500"
                >
                  Use different email address
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;