import React, { useState, useEffect, useCallback } from 'react';
import { Trash2, RefreshCw } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import uploadService from '../../services/uploadService';

const RecycleBin = () => {
  const { loadRecycleBin, restoreDocument, permanentlyDeleteDocument } = useDocuments(false);
  const [deletedItems, setDeletedItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedItems, setSelectedItems] = useState([]);
  const [error, setError] = useState(null);

  // Load recycle bin contents
  useEffect(() => {
    loadRecycleBinData();
  }, [loadRecycleBinData]);

  const loadRecycleBinData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await loadRecycleBin();
      setDeletedItems(data.files || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading recycle bin:', err);
    } finally {
      setLoading(false);
    }
  }, [loadRecycleBin]);

  const handleSelectItem = (fileId) => {
    setSelectedItems(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const handleSelectAll = () => {
    if (selectedItems.length === deletedItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(deletedItems.map(item => item.fileId));
    }
  };

  const handleRestore = async (fileId) => {
    try {
      await restoreDocument(fileId);
      setDeletedItems(prev => prev.filter(item => item.fileId !== fileId));
      setSelectedItems(prev => prev.filter(id => id !== fileId));
    } catch (err) {
      setError(err.message);
    }
  };

  const handlePermanentDelete = async (fileId) => {
    if (window.confirm('Are you sure you want to permanently delete this item? This cannot be undone.')) {
      try {
        await permanentlyDeleteDocument(fileId);
        setDeletedItems(prev => prev.filter(item => item.fileId !== fileId));
        setSelectedItems(prev => prev.filter(id => id !== fileId));
      } catch (err) {
        setError(err.message);
      }
    }
  };

  const handleRestoreSelected = async () => {
    for (const fileId of selectedItems) {
      await handleRestore(fileId);
    }
  };

  const handleEmptyBin = async () => {
    if (window.confirm('Are you sure you want to permanently delete all items in the recycle bin? This cannot be undone.')) {
      for (const item of deletedItems) {
        await handlePermanentDelete(item.fileId);
      }
    }
  };

  const getTimeAgo = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffDays = Math.floor(diffMs / 86400000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return 'Less than an hour ago';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Recycle Bin</h1>
        <div className="flex space-x-3">
          <button 
            onClick={loadRecycleBinData}
            disabled={loading}
            className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button 
            onClick={handleEmptyBin}
            disabled={deletedItems.length === 0}
            className="border border-red-300 text-red-700 px-4 py-2 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            Empty Bin
          </button>
          <button 
            onClick={handleRestoreSelected}
            disabled={selectedItems.length === 0}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            Restore Selected ({selectedItems.length})
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Deleted Items</h2>
              <p className="text-sm text-gray-500 mt-1">
                {deletedItems.length} item(s) • Items are permanently deleted after 30 days
              </p>
            </div>
            {deletedItems.length > 0 && (
              <label className="flex items-center">
                <input 
                  type="checkbox" 
                  checked={selectedItems.length === deletedItems.length && deletedItems.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
                />
                <span className="ml-2 text-sm text-gray-600">Select all</span>
              </label>
            )}
          </div>
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">Error: {error}</p>
            </div>
          )}
        </div>
        <div className="p-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="spinner mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading deleted items...</p>
            </div>
          ) : deletedItems.length > 0 ? (
            <div className="space-y-4">
              {deletedItems.map((item) => (
                <div key={item.fileId} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
                  <div className="flex items-center space-x-4">
                    <input 
                      type="checkbox" 
                      checked={selectedItems.includes(item.fileId)}
                      onChange={() => handleSelectItem(item.fileId)}
                      className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
                    />
                    <Trash2 className="w-8 h-8 text-red-400" />
                    <div>
                      <p className="font-medium text-gray-900">
                        {item.file_name || item.original_filename || 'Unknown file'}
                      </p>
                      <p className="text-sm text-gray-500">
                        Deleted {getTimeAgo(item.deleted_timestamp || item.upload_timestamp)} • {uploadService.formatFileSize(item.file_size || 0)}
                      </p>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button 
                      onClick={() => handleRestore(item.fileId)}
                      className="text-green-600 hover:text-green-700 text-sm font-medium"
                    >
                      Restore
                    </button>
                    <button 
                      onClick={() => handlePermanentDelete(item.fileId)}
                      className="text-red-600 hover:text-red-700 text-sm font-medium"
                    >
                      Delete Forever
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Trash2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Recycle bin is empty</p>
              <p className="text-sm text-gray-400 mt-1">Deleted files will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecycleBin;