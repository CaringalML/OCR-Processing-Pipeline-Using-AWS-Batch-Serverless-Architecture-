import React, { useState, useEffect } from 'react';
import { Upload as UploadIcon, Search, Package, Trash2, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatsCard from './StatsCard/StatsCard';
import { useDocuments } from '../../hooks/useDocuments';
import { LocalTimeRelative } from '../common/LocalTime';

const Dashboard = () => {
  const navigate = useNavigate();
  const { documents, loading, fetchDocuments } = useDocuments(false); // Don't auto-load
  const [stats, setStats] = useState([
    { label: "Total Documents", value: "0", change: "+0%", trend: "up" },
    { label: "Processing Queue", value: "0", change: "0%", trend: "neutral" },
    { label: "Storage Used", value: "0 MB", change: "+0%", trend: "up" },
    { label: "Completed", value: "0", change: "+0%", trend: "up" },
    { label: "Failed", value: "0", change: "0%", trend: "down" },
    { label: "Invoice Processing", value: "0", change: "+0%", trend: "up" },
  ]);
  const [recentActivity, setRecentActivity] = useState([]);

  // Fetch all documents on component mount
  useEffect(() => {
    fetchDocuments({ includeAll: true, limit: 50 });
  }, [fetchDocuments]);

  // Calculate stats from real data
  useEffect(() => {
    if (documents.length > 0) {
      const totalDocuments = documents.length;
      const processingQueue = documents.filter(d => 
        d.processingStatus === 'processing' || d.processingStatus === 'queued'
      ).length;
      const completed = documents.filter(d => 
        d.processingStatus === 'completed' || d.processingStatus === 'processed' || d.processingStatus === 'finalized'
      ).length;
      const failed = documents.filter(d => 
        d.processingStatus === 'failed'
      ).length;
      const invoiceProcessing = documents.filter(d => 
        d.processingType === 'invoice'
      ).length;
      
      // Calculate total storage used
      const totalBytes = documents.reduce((total, doc) => {
        // Parse fileSize like "363KB", "123KB", "39.1KB", "132KB"
        const sizeStr = doc.fileSize || '0';
        let bytes = 0;
        if (sizeStr.includes('KB')) {
          bytes = parseFloat(sizeStr.replace('KB', '')) * 1024;
        } else if (sizeStr.includes('MB')) {
          bytes = parseFloat(sizeStr.replace('MB', '')) * 1024 * 1024;
        } else if (sizeStr.includes('GB')) {
          bytes = parseFloat(sizeStr.replace('GB', '')) * 1024 * 1024 * 1024;
        } else {
          bytes = parseFloat(sizeStr) || 0;
        }
        return total + bytes;
      }, 0);
      const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);
      const storageDisplay = totalMB > 1024 ? 
        `${(totalMB / 1024).toFixed(1)} GB` : 
        `${totalMB} MB`;

      setStats([
        { label: "Total Documents", value: totalDocuments.toString(), change: "+100%", trend: "up" },
        { label: "Processing Queue", value: processingQueue.toString(), change: processingQueue > 0 ? "+10%" : "0%", trend: processingQueue > 0 ? "neutral" : "down" },
        { label: "Storage Used", value: storageDisplay, change: "+15%", trend: "up" },
        { label: "Completed", value: completed.toString(), change: "+20%", trend: "up" },
        { label: "Failed", value: failed.toString(), change: failed > 0 ? `+${((failed/totalDocuments)*100).toFixed(0)}%` : "0%", trend: failed > 0 ? "up" : "down" },
        { label: "Invoice Processing", value: invoiceProcessing.toString(), change: invoiceProcessing > 0 ? "+15%" : "0%", trend: invoiceProcessing > 0 ? "up" : "neutral" },
      ]);

      // Create recent activity from documents
      const activity = documents
        .sort((a, b) => new Date(b.uploadTimestamp) - new Date(a.uploadTimestamp))
        .slice(0, 8)
        .map(doc => ({
          action: getActionText(doc.processingStatus, doc.processingType),
          file: doc.fileName || doc.original_filename || 'Unknown file',
          timestamp: doc.uploadTimestamp,
          status: mapStatus(doc.processingStatus),
          type: doc.processingType || 'standard',
          size: doc.fileSize || null,
          finalized: doc.processingStatus === 'finalized'
        }));
      
      setRecentActivity(activity);
    }
  }, [documents]);

  // Helper functions
  const getActionText = (status, type) => {
    const typePrefix = type === 'invoice' ? 'Invoice' : 
                       type === 'short-batch' ? 'Quick scan' : 
                       type === 'long-batch' ? 'Full OCR' : 'Document';
    
    switch (status) {
      case 'uploaded': return `${typePrefix} uploaded`;
      case 'processing': return `${typePrefix} in progress`;
      case 'processed': case 'completed': return `${typePrefix} completed`;
      case 'finalized': return `${typePrefix} ready`;
      case 'queued': return `${typePrefix} waiting`;
      case 'failed': return `${typePrefix} error`;
      default: return `${typePrefix} uploaded`;
    }
  };


  const mapStatus = (status) => {
    switch (status) {
      case 'processing': case 'queued': return 'processing';
      case 'processed': case 'completed': case 'finalized': return 'completed';
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
        {stats.map((stat, index) => (
          <StatsCard 
            key={index}
            label={stat.label}
            value={stat.value}
            change={stat.change}
            trend={stat.trend}
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
              <div className="space-y-2">
                {recentActivity.map((activity, index) => (
                <div key={index} className={`flex items-start space-x-3 p-3 rounded-lg transition-colors ${
                  activity.status === 'processing' ? 'bg-yellow-50 hover:bg-yellow-100' : 'hover:bg-gray-50'
                }`}>
                  <div className="flex-shrink-0 mt-0.5">
                    {activity.status === 'completed' ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : activity.status === 'processing' ? (
                      <Clock className="w-5 h-5 text-yellow-500 animate-pulse" />
                    ) : activity.status === 'failed' ? (
                      <AlertCircle className="w-5 h-5 text-red-500" />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <p className="text-sm font-medium text-gray-900">
                            {activity.action}
                          </p>
                          {activity.type === 'invoice' && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                              Invoice
                            </span>
                          )}
                          {activity.type === 'short-batch' && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              Short Process
                            </span>
                          )}
                          {activity.type === 'long-batch' && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                              Long Process
                            </span>
                          )}
                          {activity.finalized ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                              Finalized
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                              Not Finalized
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <p className="text-sm text-gray-600 truncate">{activity.file}</p>
                          {activity.size && (
                            <span className="text-xs text-gray-400">({activity.size})</span>
                          )}
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 ml-3 flex-shrink-0 text-right min-w-[80px]">
                        <div className="font-medium">
                          <LocalTimeRelative timestamp={activity.timestamp} />
                        </div>
                      </div>
                    </div>
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
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors group"
              >
                <UploadIcon className="w-8 h-8 text-gray-400 group-hover:text-green-500 mx-auto mb-2 transition-colors" />
                <p className="text-sm font-medium text-gray-600 group-hover:text-green-700">Upload Documents</p>
              </button>
              <button 
                onClick={() => navigate('/search')}
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors group"
              >
                <Search className="w-8 h-8 text-gray-400 group-hover:text-blue-500 mx-auto mb-2 transition-colors" />
                <p className="text-sm font-medium text-gray-600 group-hover:text-blue-700">Search Archive</p>
              </button>
              <button 
                onClick={() => navigate('/inventory')}
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-400 hover:bg-purple-50 transition-colors group"
              >
                <Package className="w-8 h-8 text-gray-400 group-hover:text-purple-500 mx-auto mb-2 transition-colors" />
                <p className="text-sm font-medium text-gray-600 group-hover:text-purple-700">View Inventory</p>
              </button>
              <button 
                onClick={() => navigate('/recycle')}
                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-red-400 hover:bg-red-50 transition-colors group"
              >
                <Trash2 className="w-8 h-8 text-gray-400 group-hover:text-red-500 mx-auto mb-2 transition-colors" />
                <p className="text-sm font-medium text-gray-600 group-hover:text-red-700">Recycle Bin</p>
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
          <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Quick Scans:</span>
              <span className="font-medium text-blue-600">{documents.filter(d => d.processingType === 'short-batch').length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Full OCR:</span>
              <span className="font-medium text-orange-600">{documents.filter(d => d.processingType === 'long-batch').length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Invoices:</span>
              <span className="font-medium text-purple-600">{documents.filter(d => d.processingType === 'invoice').length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Errors:</span>
              <span className="font-medium text-red-600">{documents.filter(d => d.processingStatus === 'failed').length}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;