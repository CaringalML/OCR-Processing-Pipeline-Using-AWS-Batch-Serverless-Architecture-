import { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
// Icons are now imported directly in components that use them

// Import components
import Dashboard from "./components/dashboard/Dashboard";
import UploadPage from "./components/upload/Upload";
import Inventory from "./components/inventory/Inventory";
import SearchPage from "./components/search/Search";
import RecycleBin from "./components/recycle/RecycleBin";
import DocumentEdit from "./components/edit/DocumentEdit";
import DocumentView from "./components/view/DocumentView";
import DocumentReader from "./components/reader/DocumentReader";
import EditHistory from "./components/history/EditHistory";
import Sidebar from "./components/common/Sidebar/Sidebar";
import Header from "./components/common/Header/Header";

// Authentication components
import SignUp from "./components/auth/SignUp";
import SignIn from "./components/auth/SignIn";
import VerifyEmail from "./components/auth/VerifyEmail";
import ProtectedRoute from "./components/common/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";

const AppContent = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  
  // Check if current route is auth page
  const isAuthPage = ['/signin', '/signup', '/verify-email'].includes(location.pathname);
  
  // Check if current route is the edit, view, reader, or history page (should be full-screen)
  const isEditPage = location.pathname.startsWith('/edit/');
  const isViewPage = location.pathname.startsWith('/view/');
  const isReaderPage = location.pathname.startsWith('/read/');
  const isHistoryPage = location.pathname.startsWith('/history/');

  // Auth pages (no sidebar/header)
  if (isAuthPage) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
        </Routes>
      </div>
    );
  }

  // Full-screen protected pages
  if (isEditPage || isViewPage || isReaderPage || isHistoryPage) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/edit/:fileId" element={<ProtectedRoute><DocumentEdit /></ProtectedRoute>} />
          <Route path="/view/:fileId" element={<ProtectedRoute><DocumentView /></ProtectedRoute>} />
          <Route path="/read/:fileId" element={<ProtectedRoute><DocumentReader /></ProtectedRoute>} />
          <Route path="/history/:fileId" element={<ProtectedRoute><EditHistory /></ProtectedRoute>} />
        </Routes>
      </div>
    );
  }

  // Main protected app with sidebar/header
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        <Sidebar 
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
        />
        
        <div className="lg:ml-64">
          <Header setSidebarOpen={setSidebarOpen} />
          
          <div className="p-6">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/inventory" element={<Inventory />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/recycle" element={<RecycleBin />} />
            </Routes>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
};

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