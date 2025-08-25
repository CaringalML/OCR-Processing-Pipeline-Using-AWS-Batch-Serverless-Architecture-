import React, { useState, useEffect, useCallback } from 'react';
import { Trash2, RefreshCw } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import uploadService from '../../services/uploadService';
import { LocalTimeRelative } from '../common/LocalTime';

const RecycleBin = () => {
  const { loadRecycleBin, restoreDocument, permanentlyDeleteDocument } = useDocuments(false);
  const [deletedItems, setDeletedItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedItems, setSelectedItems] = useState([]);
  const [error, setError] = useState(null);
  const [restoring, setRestoring] = useState(false);
  const [showEmptyBinConfirm, setShowEmptyBinConfirm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteFileInfo] = useState({ fileId: null, fileName: '' });

  const loadRecycleBinData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await loadRecycleBin();
      setDeletedItems(data.items || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading recycle bin:', err);
    } finally {
      setLoading(false);
    }
  }, [loadRecycleBin]);

  // Load recycle bin contents
  useEffect(() => {
    loadRecycleBinData();
  }, [loadRecycleBinData]);

  const handleSelectItem = (fileId) => {
    setSelectedItems(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };


  const handlePermanentDelete = async () => {
    setShowDeleteConfirm(false);
    const { fileId } = deleteFileInfo;
    
    try {
      console.log('Starting permanent delete for fileId:', fileId);
      const result = await permanentlyDeleteDocument(fileId);
      console.log('Permanent delete successful:', result);
      setDeletedItems(prev => prev.filter(item => item.fileId !== fileId));
      setSelectedItems(prev => prev.filter(id => id !== fileId));
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error('Permanent delete failed:', err);
      setError(err.message);
    }
  };

  const handleRestoreSelected = async () => {
    try {
      setRestoring(true);
      setError(null);
      for (const fileId of selectedItems) {
        await restoreDocument(fileId);
        setDeletedItems(prev => prev.filter(item => item.fileId !== fileId));
        setSelectedItems(prev => prev.filter(id => id !== fileId));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRestoring(false);
    }
  };

  const handleEmptyBin = async () => {
    // First, select all items to show user which items will be deleted
    setSelectedItems(deletedItems.map(item => item.fileId));
    
    // Add a small delay to allow the UI to update and show the selected checkboxes
    setTimeout(() => {
      setShowEmptyBinConfirm(true);
    }, 100);
  };

  const confirmEmptyBin = async () => {
    setShowEmptyBinConfirm(false);
    await deleteAllItems();
  };

  const deleteAllItems = async () => {
    try {
      for (const item of deletedItems) {
        console.log('Starting permanent delete for fileId:', item.fileId);
        const result = await permanentlyDeleteDocument(item.fileId);
        console.log('Permanent delete successful:', result);
      }
      setDeletedItems([]);
      setSelectedItems([]);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error('Empty bin failed:', err);
      setError(err.message);
    }
  };

  // Removed getTimeAgo function - using LocalTimeRelative component instead

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Recycle Bin</h1>
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
            <div className="flex space-x-3">
              {selectedItems.length > 0 && (
                <button 
                  onClick={handleRestoreSelected}
                  disabled={restoring}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {restoring && <RefreshCw className="w-4 h-4 animate-spin" />}
                  <span>
                    {restoring ? 'Restoring...' : `Restore Selected (${selectedItems.length})`}
                  </span>
                </button>
              )}
              {deletedItems.length > 0 && (
                <button 
                  onClick={handleEmptyBin}
                  className="border border-red-300 text-red-700 px-4 py-2 rounded-lg hover:bg-red-50 transition-colors"
                >
                  Empty Bin
                </button>
              )}
            </div>
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
                <div 
                  key={item.fileId} 
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSelectItem(item.fileId)}
                >
                  <div className="flex items-center space-x-4">
                    <input 
                      type="checkbox" 
                      checked={selectedItems.includes(item.fileId)}
                      onChange={() => handleSelectItem(item.fileId)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
                    />
                    <Trash2 className="w-8 h-8 text-red-400" />
                    <div>
                      <p className="font-medium text-gray-900">
                        {item.metadata?.filename || item.file_name || item.original_filename || 'Unknown file'}
                      </p>
                      <p className="text-sm text-gray-500">
                        Deleted <LocalTimeRelative timestamp={item.deletedAt || item.deleted_timestamp || item.upload_timestamp} /> • {uploadService.formatFileSize(item.metadata?.filesize || item.file_size || 0)}
                      </p>
                    </div>
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

      {/* Empty Bin Confirmation Modal */}
      {showEmptyBinConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <Trash2 className="h-6 w-6 text-red-600" />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Empty Recycle Bin
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  Are you sure you want to permanently delete <span className="font-medium text-gray-900">all {deletedItems.length} item{deletedItems.length > 1 ? 's' : ''}</span> from the recycle bin?
                </p>
                <p className="text-sm text-red-600 bg-red-50 rounded-md p-3 mb-4">
                  <span className="font-medium">Warning:</span> This action cannot be undone. All items will be permanently deleted and cannot be restored.
                </p>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowEmptyBinConfirm(false);
                    setSelectedItems([]); // Deselect all items
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmEmptyBin}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  Empty Recycle Bin
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Individual Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <Trash2 className="h-6 w-6 text-red-600" />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Permanently Delete
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  Are you sure you want to permanently delete <span className="font-medium text-gray-900">"{deleteFileInfo.fileName}"</span>?
                </p>
                <p className="text-sm text-red-600 bg-red-50 rounded-md p-3 mb-4">
                  <span className="font-medium">Warning:</span> This action cannot be undone. The item will be permanently deleted and cannot be restored.
                </p>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handlePermanentDelete}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  Delete Permanently
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecycleBin;