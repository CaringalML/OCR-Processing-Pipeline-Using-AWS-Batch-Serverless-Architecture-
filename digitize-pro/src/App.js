import { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
// Icons are now imported directly in components that use them

// Import components (you'll create these)
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

const AppContent = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  
  // Check if current route is the edit, view, reader, or history page (should be full-screen)
  const isEditPage = location.pathname.startsWith('/edit/');
  const isViewPage = location.pathname.startsWith('/view/');
  const isReaderPage = location.pathname.startsWith('/read/');
  const isHistoryPage = location.pathname.startsWith('/history/');

  if (isEditPage || isViewPage || isReaderPage || isHistoryPage) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/edit/:fileId" element={<DocumentEdit />} />
          <Route path="/view/:fileId" element={<DocumentView />} />
          <Route path="/read/:fileId" element={<DocumentReader />} />
          <Route path="/history/:fileId" element={<EditHistory />} />
        </Routes>
      </div>
    );
  }

  return (
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
  );
};

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;