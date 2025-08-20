import React from 'react';
import { useLocation } from 'react-router-dom';
import { Menu, Bell } from 'lucide-react';

const Header = ({ setSidebarOpen }) => {
  const location = useLocation();
  
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
          <div className="relative">
            <Bell className="w-6 h-6 text-gray-400 hover:text-gray-600 cursor-pointer" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-xs text-white flex items-center justify-center"></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;