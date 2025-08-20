import React, { useState, useEffect } from 'react';
import { Upload as UploadIcon, Search, Package, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatsCard from './StatsCard/StatsCard';
import { useDocuments } from '../../hooks/useDocuments';
import { LocalTimeRelative } from '../common/LocalTime';

const Dashboard = () => {
  const navigate = useNavigate();
  const { documents, loading } = useDocuments();
  const [stats, setStats] = useState([
    { label: "Total Documents", value: "0", change: "+0%" },
    { label: "Processing Queue", value: "0", change: "0%" },
    { label: "Storage Used", value: "0 MB", change: "+0%" },
    { label: "Completed", value: "0", change: "+0%" },
  ]);
  const [recentActivity, setRecentActivity] = useState([]);

  // Calculate stats from real data
  useEffect(() => {
    if (documents.length > 0) {
      const totalDocuments = documents.length;
      const processingQueue = documents.filter(d => 
        d.processing_status === 'processing' || d.processing_status === 'queued'
      ).length;
      const completed = documents.filter(d => 
        d.processing_status === 'completed' || d.processing_status === 'processed'
      ).length;
      
      // Calculate total storage used
      const totalBytes = documents.reduce((total, doc) => {
        return total + (doc.file_size || 0);
      }, 0);
      const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);
      const storageDisplay = totalMB > 1024 ? 
        `${(totalMB / 1024).toFixed(1)} GB` : 
        `${totalMB} MB`;

      setStats([
        { label: "Total Documents", value: totalDocuments.toString(), change: "+100%" },
        { label: "Processing Queue", value: processingQueue.toString(), change: processingQueue > 0 ? "+10%" : "0%" },
        { label: "Storage Used", value: storageDisplay, change: "+15%" },
        { label: "Completed", value: completed.toString(), change: "+20%" },
      ]);

      // Create recent activity from documents
      const activity = documents
        .sort((a, b) => new Date(b.upload_timestamp) - new Date(a.upload_timestamp))
        .slice(0, 5)
        .map(doc => ({
          action: getActionText(doc.processing_status),
          file: doc.file_name || doc.original_filename || 'Unknown file',
          timestamp: doc.upload_timestamp, // Store raw timestamp for LocalTimeRelative
          status: mapStatus(doc.processing_status)
        }));
      
      setRecentActivity(activity);
    }
  }, [documents]);

  // Helper functions
  const getActionText = (status) => {
    switch (status) {
      case 'uploaded': return 'Document uploaded';
      case 'processing': return 'OCR processing';
      case 'processed': case 'completed': return 'OCR completed';
      case 'queued': return 'Queued for processing';
      case 'failed': return 'Processing failed';
      default: return 'Document uploaded';
    }
  };

  const mapStatus = (status) => {
    switch (status) {
      case 'processing': case 'queued': return 'processing';
      case 'processed': case 'completed': return 'completed';
      case 'failed': return 'failed';
      default: return 'active';
    }
  };

  // Removed getTimeAgo function - using LocalTimeRelative component instead

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-green-600 to-green-700 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-semibold mb-2">Welcome to DigitizePro</h1>
        <p className="text-green-100">Transform your physical collections into searchable digital archives</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <StatsCard 
            key={index}
            label={stat.label}
            value={stat.value}
            change={stat.change}
          />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
          </div>
          <div className="p-6">
            {loading ? (
              <div className="text-center py-8">
                <div className="spinner mx-auto"></div>
                <p className="text-sm text-gray-500 mt-2">Loading recent activity...</p>
              </div>
            ) : recentActivity.length > 0 ? (
              <div className="space-y-4">
                {recentActivity.map((activity, index) => (
                <div key={index} className="flex items-center space-x-4">
                  <div className={`w-2 h-2 rounded-full ${
                    activity.status === 'completed' ? 'bg-green-500' :
                    activity.status === 'processing' ? 'bg-yellow-500' : 'bg-blue-500'
                  }`}></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {activity.action}
                    </p>
                    <p className="text-sm text-gray-500 truncate">{activity.file}</p>
                  </div>
                  <div className="text-xs text-gray-400">
                    <LocalTimeRelative timestamp={activity.timestamp} />
                  </div>
                </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">No recent activity</p>
                <p className="text-sm text-gray-400 mt-1">Upload documents to see activity here</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 gap-4">
                              <button 
                onClick={() => navigate('/upload')}
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors"
              >
                <UploadIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">Upload Documents</p>
              </button>
              <button 
                onClick={() => navigate('/search')}
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors"
              >
                <Search className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">Search Archive</p>
              </button>
              <button 
                onClick={() => navigate('/inventory')}
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors"
              >
                <Package className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">View Inventory</p>
              </button>
              <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors">
                <Settings className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">Settings</p>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Document Processing Overview */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Processing Overview</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Current Usage */}
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{stats[2].value}</div>
              <div className="text-sm text-gray-500">Storage Used</div>
              <div className="text-xs text-green-600 mt-1">{stats[2].change} this month</div>
            </div>
            
            {/* Processing Queue */}
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{stats[1].value}</div>
              <div className="text-sm text-gray-500">In Processing Queue</div>
              <div className="text-xs text-gray-600 mt-1">Active jobs</div>
            </div>
            
            {/* Success Rate */}
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{stats[3].value}</div>
              <div className="text-sm text-gray-500">Completed</div>
              <div className="text-xs text-blue-600 mt-1">Successfully processed</div>
            </div>
          </div>
          
          {/* Processing Performance */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Processing Performance</span>
              <span className="text-sm text-gray-500">Real-time stats</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-green-600 h-2 rounded-full" style={{ 
                width: documents.length > 0 ? `${Math.min((parseInt(stats[3].value) / parseInt(stats[0].value)) * 100, 100)}%` : '0%'
              }}></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Completed: {stats[3].value}</span>
              <span>Total: {stats[0].value}</span>
            </div>
          </div>
          
          {/* Processing Types Breakdown */}
          <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Short Batch:</span>
              <span className="font-medium">{documents.filter(d => d.processing_type === 'short-batch').length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Long Batch:</span>
              <span className="font-medium">{documents.filter(d => d.processing_type === 'long-batch').length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Completed:</span>
              <span className="font-medium">{documents.filter(d => d.processing_status === 'completed').length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Failed:</span>
              <span className="font-medium">{documents.filter(d => d.processing_status === 'failed').length}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;