import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, Upload as UploadIcon, Package, Trash2, Search, X, FileText } from "lucide-react";

const Sidebar = ({ sidebarOpen, setSidebarOpen }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const navigationItems = [
    { id: "dashboard", label: "Dashboard", icon: Home, path: "/dashboard" },
    { id: "upload", label: "Upload", icon: UploadIcon, path: "/upload" },
    { id: "inventory", label: "Inventory", icon: Package, path: "/inventory" },
    { id: "recycle", label: "Recycle Bin", icon: Trash2, path: "/recycle" },
    { id: "search", label: "Search", icon: Search, path: "/search" },
  ];

  const handleNavigation = (path) => {
    navigate(path);
    setSidebarOpen(false);
  };

  return (
    <>
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="fixed inset-0 bg-black bg-opacity-25" onClick={() => setSidebarOpen(false)}></div>
        </div>
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 lg:translate-x-0`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold text-gray-900">DigitizePro</h1>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 rounded-md hover:bg-gray-100"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-2">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.id}
                onClick={() => handleNavigation(item.path)}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  isActive
                    ? 'bg-green-100 text-green-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.label}
              </button>
            );
          })}
        </nav>

      </div>
    </>
  );
};

export default Sidebar;