import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Menu, Bell, User, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';

const Header = ({ setSidebarOpen }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { signOut, userEmail, userName } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);
  
  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getPageTitle = () => {
    const path = location.pathname;
    switch (path) {
      case '/dashboard':
        return 'Dashboard';
      case '/upload':
        return 'Upload Documents';
      case '/inventory':
        return 'Document Inventory';
      case '/search':
        return 'Search Archive';
      case '/recycle':
        return 'Recycle Bin';
      default:
        return 'DigitizePro';
    }
  };

  const handleSignOut = async () => {
    try {
      const result = await signOut();
      if (result.success) {
        navigate('/signin');
      }
    } catch (error) {
      console.error('Sign out error:', error);
    }
  };

  return (
    <div className="bg-white shadow-sm border-b border-gray-200">
      <div className="flex items-center justify-between h-16 px-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="w-5 h-5 text-gray-500" />
          </button>
          <div className="hidden sm:block">
            <h2 className="text-lg font-semibold text-gray-900">{getPageTitle()}</h2>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Notifications */}
          <div className="relative">
            <Bell className="w-6 h-6 text-gray-400 hover:text-gray-600 cursor-pointer" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-xs text-white flex items-center justify-center"></span>
          </div>

          {/* User Menu */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="hidden md:block text-left">
                <div className="text-sm font-medium text-gray-900">
                  {userName || 'User'}
                </div>
                <div className="text-xs text-gray-500 truncate max-w-32">
                  {userEmail}
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>

            {/* User Dropdown Menu */}
            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
                <div className="py-1">
                  {/* User Info Section */}
                  <div className="px-4 py-2 border-b border-gray-100">
                    <div className="text-sm font-medium text-gray-900">
                      {userName || 'User'}
                    </div>
                    <div className="text-sm text-gray-500 truncate">
                      {userEmail}
                    </div>
                  </div>
                  
                  {/* Menu Items */}
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      // Add profile page navigation here later
                    }}
                    className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <User className="w-4 h-4 mr-3" />
                    Profile Settings
                  </button>
                  
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      handleSignOut();
                    }}
                    className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <LogOut className="w-4 h-4 mr-3" />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;