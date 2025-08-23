import React, { useState, useEffect } from 'react';
import { FileText, Download, Eye, Edit, Trash2, Calendar, User, Tag, CheckSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDocuments } from '../../hooks/useDocuments';
import uploadService from '../../services/uploadService';
import documentService from '../../services/documentService';
import LocalTime, { LocalDateShort, LocalDateTime } from '../common/LocalTime';

const Inventory = () => {
  const navigate = useNavigate();
  const { loading, deleteDocument } = useDocuments();
  const [documents, setDocuments] = useState([]);
  const [filteredDocuments, setFilteredDocuments] = useState([]);
  const [loadingFinalized, setLoadingFinalized] = useState(false);
  const [filters, setFilters] = useState({
    processing_type: 'all',
    dateRange: 'all',
    status: 'all',
    search: ''
  });
  const [selectedDocuments, setSelectedDocuments] = useState(new Set());
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'table'
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteFileInfo, setDeleteFileInfo] = useState({ fileIds: [], fileNames: [], isBulk: false });

  // Fetch only finalized documents for inventory
  useEffect(() => {
    const fetchFinalizedDocuments = async () => {
      try {
        setLoadingFinalized(true);
        console.log('Fetching finalized documents...');
        
        // Use documentService to get finalized documents
        const data = await documentService.getProcessedDocuments({ finalized: true });
        console.log('Finalized documents received:', data);
        
        // Handle different response structures
        if (data) {
          if (Array.isArray(data)) {
            setDocuments(data);
          } else if (data.files && Array.isArray(data.files)) {
            setDocuments(data.files);
          } else if (data.items && Array.isArray(data.items)) {
            setDocuments(data.items);
          } else if (data.documents && Array.isArray(data.documents)) {
            setDocuments(data.documents);
          } else {
            console.warn('Unexpected finalized data structure:', data);
            setDocuments([]);
          }
        } else {
          setDocuments([]);
        }
      } catch (error) {
        console.error('Error fetching finalized documents:', error);
        setDocuments([]);
      } finally {
        setLoadingFinalized(false);
      }
    };

    fetchFinalizedDocuments();
    // Refresh every 60 seconds
    const interval = setInterval(fetchFinalizedDocuments, 60000);
    return () => clearInterval(interval);
  }, []);

  // Filter documents
  useEffect(() => {
    let filtered = documents;
    
    // Filter by processing type
    if (filters.processing_type !== 'all') {
      filtered = filtered.filter(doc => getProcessingType(doc) === filters.processing_type);
    }
    
    // Filter by status
    if (filters.status !== 'all') {
      filtered = filtered.filter(doc => getProcessingStatus(doc) === filters.status);
    }
    
    // Filter by date range
    if (filters.dateRange !== 'all') {
      const now = new Date();
      const cutoff = new Date();
      switch (filters.dateRange) {
        case '30days':
          cutoff.setDate(now.getDate() - 30);
          break;
        case '6months':
          cutoff.setMonth(now.getMonth() - 6);
          break;
        case '1year':
          cutoff.setFullYear(now.getFullYear() - 1);
          break;
        default:
          break;
      }
      filtered = filtered.filter(doc => new Date(getUploadTimestamp(doc)) >= cutoff);
    }
    
    // Filter by search text
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(doc => {
        const tags = doc.metadata?.tags || '';
        const tagsString = Array.isArray(tags) ? tags.join(' ') : tags;
        
        return getFileName(doc).toLowerCase().includes(searchLower) ||
               (doc.metadata?.title || '').toLowerCase().includes(searchLower) ||
               (doc.metadata?.author || '').toLowerCase().includes(searchLower) ||
               tagsString.toLowerCase().includes(searchLower);
      });
    }
    
    // Sort by upload date (newest first)
    filtered.sort((a, b) => new Date(getUploadTimestamp(b)) - new Date(getUploadTimestamp(a)));
    
    setFilteredDocuments(filtered);
  }, [documents, filters]);

  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({ ...prev, [filterType]: value }));
  };

  const handleDocumentSelect = (fileId) => {
    setSelectedDocuments(prev => {
      const newSelected = new Set(prev);
      if (newSelected.has(fileId)) {
        newSelected.delete(fileId);
      } else {
        newSelected.add(fileId);
      }
      return newSelected;
    });
  };

  const handleSelectAll = () => {
    if (selectedDocuments.size === filteredDocuments.length) {
      // If all are selected, deselect all
      setSelectedDocuments(new Set());
    } else {
      // Otherwise select all filtered documents
      const allFileIds = filteredDocuments.map(doc => doc.fileId || doc.file_id);
      setSelectedDocuments(new Set(allFileIds));
    }
  };

  const showBulkDeleteConfirmation = () => {
    if (selectedDocuments.size === 0) return;

    const selectedFiles = filteredDocuments.filter(doc => 
      selectedDocuments.has(doc.fileId || doc.file_id)
    );

    const fileNames = selectedFiles.map(doc => getFileName(doc));
    const fileIds = selectedFiles.map(doc => doc.fileId || doc.file_id);
    
    setDeleteFileInfo({ fileIds, fileNames, isBulk: true });
    setShowDeleteConfirm(true);
  };

  const handleBulkDelete = async () => {
    setShowDeleteConfirm(false);
    const { fileIds } = deleteFileInfo;

    try {
      // Delete all selected documents (moves to recycle bin)
      const deletePromises = fileIds.map(fileId => 
        documentService.deleteDocument(fileId)
      );
      
      await Promise.all(deletePromises);
      
      // Remove from local state
      const deletedIds = new Set(fileIds);
      setDocuments(prev => 
        prev.filter(doc => !deletedIds.has(doc.fileId || doc.file_id))
      );
      
      // Clear selection
      setSelectedDocuments(new Set());
      
      console.log(`✓ ${fileIds.length} document${fileIds.length > 1 ? 's' : ''} moved to recycle bin`);
    } catch (error) {
      console.error('Error deleting documents:', error);
      alert(`Failed to delete documents: ${error.message}`);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const fileId = doc.fileId;
      const cloudFrontUrl = doc.cloudFrontUrl;
      const blob = await documentService.downloadDocument(fileId, cloudFrontUrl);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = getFileName(doc);
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download document');
    }
  };

  const showDeleteConfirmation = (fileId, fileName) => {
    setDeleteFileInfo({ fileIds: [fileId], fileNames: [fileName], isBulk: false });
    setShowDeleteConfirm(true);
  };

  const handleDelete = async () => {
    setShowDeleteConfirm(false);
    const { fileIds } = deleteFileInfo;
    const fileId = fileIds[0];
    
    try {
      await deleteDocument(fileId);
      setSelectedDocuments(prev => prev.filter(id => id !== fileId));
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete document');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
      case 'processed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'uploaded':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Remove formatDate function - using LocalTime component instead

  const formatFileSize = (size) => {
    if (!size) return '0 Bytes';
    
    // If size is already a string (like "123KB"), return as is
    if (typeof size === 'string') {
      return size;
    }
    
    // If size is a number, format it
    return uploadService.formatFileSize(size);
  };

  const getProcessingStatus = (doc) => {
    return doc.processingStatus || doc.processing_status || 'Unknown';
  };

  const getProcessingType = (doc) => {
    return doc.processingType || doc.processing_type || 'Unknown';
  };

  const getFileName = (doc) => {
    return doc.fileName || doc.file_name || doc.original_filename || 'Untitled';
  };

  const getFileSize = (doc) => {
    return doc.fileSize || doc.file_size || 0;
  };

  const getUploadTimestamp = (doc) => {
    return doc.uploadTimestamp || doc.upload_timestamp;
  };

  const getFinalizedText = (doc) => {
    // For finalized documents, get the finalizedText
    if (doc.finalizedResults?.finalizedText) {
      return doc.finalizedResults.finalizedText;
    }
    if (doc.finalizedText) {
      return doc.finalizedText;
    }
    // Fallback to OCR results
    return doc.ocrResults?.refinedText || doc.ocrResults?.formattedText || doc.ocrResults?.extractedText || 'No text available';
  };

  const getTextPreview = (text, maxLength = 150) => {
    if (!text) return 'No text available';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Finalized Document Inventory</h1>
          <p className="text-sm text-gray-600 mt-1">
            {filteredDocuments.length} finalized document(s) • Ready for use
          </p>
        </div>
        <div>
          <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors">
            Export Data
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="Search by filename, title, author, tags..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Processing Type</label>
            <select 
              value={filters.processing_type}
              onChange={(e) => handleFilterChange('processing_type', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="all">All Types</option>
              <option value="short-batch">Short Batch (Lambda)</option>
              <option value="long-batch">Long Batch (AWS Batch)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select 
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="all">All Statuses</option>
              <option value="uploaded">Uploaded</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
            <select 
              value={filters.dateRange}
              onChange={(e) => handleFilterChange('dateRange', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="all">All Dates</option>
              <option value="30days">Last 30 days</option>
              <option value="6months">Last 6 months</option>
              <option value="1year">Last Year</option>
            </select>
          </div>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Documents</h2>
            <div className="flex items-center space-x-4">
              {filteredDocuments.length > 0 && (
                <label className="flex items-center space-x-2 text-sm text-gray-600">
                  <input 
                    type="checkbox" 
                    checked={selectedDocuments.size > 0 && selectedDocuments.size === filteredDocuments.length}
                    onChange={handleSelectAll}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" 
                  />
                  <span>Select all</span>
                </label>
              )}
              
              {selectedDocuments.size > 0 && (
                <button 
                  onClick={showBulkDeleteConfirmation}
                  className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Move {selectedDocuments.size} to Recycle Bin
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="divide-y divide-gray-200 max-h-[70vh] overflow-y-auto modern-scrollbar">
          {(loading || loadingFinalized) ? (
            <div className="p-8 text-center">
              <div className="spinner mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading finalized documents...</p>
            </div>
          ) : filteredDocuments.length > 0 ? (
            filteredDocuments.map((doc) => (
              <div key={doc.fileId} className="p-6 hover:bg-blue-50 cursor-pointer transition-colors border-l-4 border-transparent hover:border-blue-400">
                <div className="flex items-start justify-between">
                  <div 
                    className="flex items-start space-x-4 flex-1"
                    onClick={() => navigate(`/view/${doc.fileId}`)}
                  >
                    <div onClick={(e) => e.stopPropagation()}>
                      <input 
                        type="checkbox" 
                        checked={selectedDocuments.has(doc.fileId || doc.file_id)}
                        onChange={() => handleDocumentSelect(doc.fileId || doc.file_id)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-1" 
                      />
                    </div>
                    <FileText className="w-10 h-10 text-gray-400 mt-1" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-medium text-gray-900 truncate">
                          {doc.metadata?.title || getFileName(doc)}
                        </h3>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✓ Finalized
                        </span>
                        {doc.finalizedResults?.textSource && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                            {doc.finalizedResults.textSource === 'formatted' ? 'Formatted Text' : 'Refined Text'}
                          </span>
                        )}
                      </div>
                      
                      <div className="text-sm text-gray-600 space-y-1">
                        <div className="flex items-center space-x-4">
                          <span>📁 {getFileName(doc)}</span>
                          <span>📏 {formatFileSize(getFileSize(doc))}</span>
                          <span>⚙️ {getProcessingType(doc).replace('-', ' ')}</span>
                        </div>
                        
                        {doc.metadata && (
                          <div className="flex items-center space-x-4 text-xs">
                            {doc.metadata.author && (
                              <span className="flex items-center space-x-1">
                                <User className="w-3 h-3" />
                                <span>{doc.metadata.author}</span>
                              </span>
                            )}
                            {doc.metadata.date && (
                              <span className="flex items-center space-x-1">
                                <Calendar className="w-3 h-3" />
                                <span>{doc.metadata.date}</span>
                              </span>
                            )}
                            {doc.metadata.tags && (
                              <span className="flex items-center space-x-1">
                                <Tag className="w-3 h-3" />
                                <span>{Array.isArray(doc.metadata.tags) ? doc.metadata.tags.join(', ') : doc.metadata.tags}</span>
                              </span>
                            )}
                          </div>
                        )}
                        
                        <div className="text-xs text-gray-500">
                          Uploaded: <LocalDateTime timestamp={getUploadTimestamp(doc)} />
                          {doc.ocrResults?.pages && ` • ${doc.ocrResults.pages} pages`}
                          {doc.finalizedResults?.finalizedTimestamp && (
                            <> • Finalized: <LocalDateTime timestamp={doc.finalizedResults.finalizedTimestamp} /></>
                          )}
                          {doc.finalizedResults?.wasEditedBeforeFinalization && (
                            <span className="text-blue-600"> • User Edited</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4" onClick={(e) => e.stopPropagation()}>
                    <button 
                      onClick={() => navigate(`/view/${doc.fileId}`)}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View Document"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => handleDownload(doc)}
                      className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No finalized documents found</p>
              <p className="text-sm text-gray-400 mt-1">
                {filters.search || filters.status !== 'all' || filters.processing_type !== 'all' || filters.dateRange !== 'all'
                  ? 'Try adjusting your filters'
                  : 'Finalize documents in the Upload Queue to see them here'
                }
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-amber-100">
                  <Trash2 className="h-6 w-6 text-amber-600" />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Move to Recycle Bin
                </h3>
                {deleteFileInfo.isBulk ? (
                  <>
                    <p className="text-sm text-gray-500 mb-4">
                      Are you sure you want to move <span className="font-medium text-gray-900">{deleteFileInfo.fileIds.length} document{deleteFileInfo.fileIds.length > 1 ? 's' : ''}</span> to the recycle bin?
                    </p>
                    {deleteFileInfo.fileNames.length <= 3 ? (
                      <div className="text-sm text-gray-600 bg-gray-50 rounded-md p-3 mb-4 max-h-20 overflow-y-auto">
                        {deleteFileInfo.fileNames.map((name, index) => (
                          <div key={index} className="truncate">• {name}</div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-600 bg-gray-50 rounded-md p-3 mb-4 max-h-20 overflow-y-auto">
                        {deleteFileInfo.fileNames.slice(0, 2).map((name, index) => (
                          <div key={index} className="truncate">• {name}</div>
                        ))}
                        <div className="text-gray-500 mt-1">... and {deleteFileInfo.fileNames.length - 2} more</div>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-gray-500 mb-4">
                    Are you sure you want to move <span className="font-medium text-gray-900">"{deleteFileInfo.fileNames[0]}"</span> to the recycle bin?
                  </p>
                )}
                <p className="text-sm text-amber-600 bg-amber-50 rounded-md p-3 mb-4">
                  <span className="font-medium">Note:</span> Documents can be restored from the recycle bin within 30 days.
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
                  onClick={deleteFileInfo.isBulk ? handleBulkDelete : handleDelete}
                  className="px-4 py-2 text-sm font-medium text-white bg-amber-600 border border-transparent rounded-md hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
                >
                  Move to Recycle Bin
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Inventory;