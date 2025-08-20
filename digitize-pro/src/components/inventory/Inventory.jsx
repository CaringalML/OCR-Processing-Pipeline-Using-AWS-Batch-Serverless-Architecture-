import React, { useState, useEffect } from 'react';
import { FileText, Download, Eye, Edit, Trash2, Calendar, User, Tag } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDocuments } from '../../hooks/useDocuments';
import uploadService from '../../services/uploadService';
import documentService from '../../services/documentService';

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
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'table'

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
    setSelectedDocuments(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const handleSelectAll = () => {
    if (selectedDocuments.length === filteredDocuments.length) {
      setSelectedDocuments([]);
    } else {
      setSelectedDocuments(filteredDocuments.map(doc => doc.fileId));
    }
  };

  const handleDownload = async (doc) => {
    try {
      const fileId = doc.fileId;
      const cloudFrontUrl = doc.cloudFrontUrl;
      const blob = await documentService.downloadDocument(fileId, cloudFrontUrl);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = getFileName(doc);
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download document');
    }
  };

  const handleDelete = async (fileId) => {
    if (window.confirm('Are you sure you want to delete this document? It will be moved to the recycle bin.')) {
      try {
        await deleteDocument(fileId);
        setSelectedDocuments(prev => prev.filter(id => id !== fileId));
      } catch (error) {
        console.error('Delete failed:', error);
        alert('Failed to delete document');
      }
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

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return 'Invalid date';
    }
  };

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
        <div className="flex space-x-3">
          {selectedDocuments.length > 0 && (
            <button 
              onClick={() => selectedDocuments.forEach(handleDelete)}
              className="border border-red-300 text-red-700 px-4 py-2 rounded-lg hover:bg-red-50 transition-colors"
            >
              Delete Selected ({selectedDocuments.length})
            </button>
          )}
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
            {filteredDocuments.length > 0 && (
              <label className="flex items-center">
                <input 
                  type="checkbox" 
                  checked={selectedDocuments.length === filteredDocuments.length && filteredDocuments.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
                />
                <span className="ml-2 text-sm text-gray-600">Select all</span>
              </label>
            )}
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {(loading || loadingFinalized) ? (
            <div className="p-8 text-center">
              <div className="spinner mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading finalized documents...</p>
            </div>
          ) : filteredDocuments.length > 0 ? (
            filteredDocuments.map((doc) => (
              <div key={doc.fileId} className="p-6 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    <input 
                      type="checkbox" 
                      checked={selectedDocuments.includes(doc.fileId)}
                      onChange={() => handleDocumentSelect(doc.fileId)}
                      className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500 mt-1" 
                    />
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
                          Uploaded: {formatDate(getUploadTimestamp(doc))}
                          {doc.ocrResults?.pages && ` • ${doc.ocrResults.pages} pages`}
                          {doc.finalizedResults?.finalizedTimestamp && (
                            ` • Finalized: ${formatDate(doc.finalizedResults.finalizedTimestamp)}`
                          )}
                          {doc.finalizedResults?.wasEditedBeforeFinalization && (
                            <span className="text-blue-600"> • User Edited</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
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
                    <button 
                      onClick={() => handleDelete(doc.fileId)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
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
    </div>
  );
};

export default Inventory;