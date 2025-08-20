import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Calendar, User, Tag, FileText, Clock, Eye, Copy, Edit, Save, X } from 'lucide-react';
import documentService from '../../services/documentService';
import uploadService from '../../services/uploadService';

const DocumentView = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showFullText, setShowFullText] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editableText, setEditableText] = useState('');
  const [editReason, setEditReason] = useState('');
  const [saving, setSaving] = useState(false);

  // Load document data
  useEffect(() => {
    const loadDocument = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log('Fetching document for view with fileId:', fileId);
        // Since we're viewing from inventory, we want to fetch the finalized version
        const docData = await documentService.getDocument(fileId, true);
        console.log('Document data received for view:', docData);
        
        if (docData) {
          setDocument(docData);
        } else {
          console.error('No document found for fileId:', fileId);
          setError('Document not found');
        }
      } catch (err) {
        setError(err.message);
        console.error('Error loading document for view:', err);
      } finally {
        setLoading(false);
      }
    };

    if (fileId) {
      loadDocument();
    }
  }, [fileId]);

  // Download document
  const handleDownload = async () => {
    try {
      const blob = await documentService.downloadDocument(document.fileId, document.cloudFrontUrl);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = document.fileName || document.original_filename || document.file_name || 'document';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download document');
    }
  };

  // Copy text to clipboard
  const handleCopyText = async () => {
    try {
      const textToCopy = getFinalizedText();
      await navigator.clipboard.writeText(textToCopy);
      alert('Text copied to clipboard!');
    } catch (error) {
      console.error('Failed to copy text:', error);
      alert('Failed to copy text to clipboard');
    }
  };

  // Get finalized text
  const getFinalizedText = () => {
    if (document?.finalizedResults?.finalizedText) {
      return document.finalizedResults.finalizedText;
    }
    if (document?.finalizedText) {
      return document.finalizedText;
    }
    return document?.ocrResults?.refinedText || document?.ocrResults?.formattedText || document?.ocrResults?.extractedText || 'No text available';
  };

  // Start editing
  const handleStartEdit = () => {
    const currentText = getFinalizedText();
    setEditableText(currentText);
    setEditReason('');
    setIsEditing(true);
  };

  // Cancel editing
  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditableText('');
    setEditReason('');
  };

  // Save edit
  const handleSaveEdit = async () => {
    if (!editableText.trim()) {
      alert('Please enter the finalized text.');
      return;
    }
    
    if (!editReason.trim()) {
      alert('Please provide a reason for the edit.');
      return;
    }

    try {
      setSaving(true);
      
      const editData = {
        finalizedText: editableText,
        editReason: editReason,
        editedBy: 'user'
      };

      const result = await documentService.editFinalizedDocument(fileId, editData);
      
      console.log('Edit successful:', result);
      
      // Update the document in state to reflect the changes
      const updatedDocument = {
        ...document,
        finalizedResults: {
          ...document.finalizedResults,
          finalizedText: editableText
        }
      };
      setDocument(updatedDocument);
      
      // Reset edit state
      setIsEditing(false);
      setEditableText('');
      setEditReason('');
      
      alert(`Document updated successfully! ${result.message || ''}`);
    } catch (err) {
      console.error('Edit error:', err);
      
      let errorMessage = 'Failed to edit document. ';
      if (err.message.includes('404')) {
        errorMessage += 'Document not found or no longer available.';
      } else if (err.message.includes('400')) {
        errorMessage += 'Invalid edit request.';
      } else if (err.message.includes('500')) {
        errorMessage += 'Server error. Please try again later.';
      } else if (err.message.includes('Failed to fetch')) {
        errorMessage += 'Network error. Please check your connection and try again.';
      } else {
        errorMessage += err.message;
      }
      
      alert(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <button 
            onClick={() => navigate('/inventory')}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
          >
            Back to Inventory
          </button>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Document not found</p>
          <button 
            onClick={() => navigate('/inventory')}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
          >
            Back to Inventory
          </button>
        </div>
      </div>
    );
  }

  const finalizedText = getFinalizedText();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => navigate('/inventory')}
                className="text-gray-600 hover:text-gray-900 flex items-center space-x-2"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Back to Inventory</span>
              </button>
              <div className="h-6 w-px bg-gray-300"></div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {document.metadata?.title || document.fileName || document.original_filename || document.file_name || 'Untitled Document'}
                </h1>
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                    ✓ Finalized
                  </span>
                  <span>{document.fileSize || uploadService.formatFileSize(document.file_size || 0)}</span>
                  <span>•</span>
                  <span>{document.processingType || 'Unknown processing'}</span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              {!isEditing && (
                <button 
                  onClick={handleStartEdit}
                  className="p-2 text-gray-400 hover:text-gray-600"
                  title="Edit Document"
                >
                  <Edit className="w-4 h-4" />
                </button>
              )}
              
              <button 
                onClick={handleCopyText}
                className="p-2 text-gray-400 hover:text-gray-600"
                title="Copy Text"
              >
                <Copy className="w-4 h-4" />
              </button>
              
              <button 
                onClick={handleDownload}
                className="p-2 text-gray-400 hover:text-gray-600"
                title="Download Original"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Document Image */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Scanned Document</h2>
              <p className="text-sm text-gray-500">
                {document.ocrResults?.languageDetection?.detected_language || 'Language not detected'} • 
                Processing: {document.ocrResults?.processingDuration || 'Unknown'} • 
                Quality: {document.textAnalysis?.qualityAssessment?.confidence_score || 'N/A'}%
              </p>
            </div>
            <div className="p-4">
              {document.cloudFrontUrl ? (
                <div className="flex items-center justify-center bg-gray-100 rounded-lg min-h-96">
                  <img 
                    src={document.cloudFrontUrl}
                    alt={document.fileName || document.original_filename || 'Document'}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'block';
                    }}
                  />
                  <div className="text-center text-gray-500 hidden">
                    <p>Unable to load document preview</p>
                    <p className="text-sm">The document image is not available</p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center bg-gray-100 rounded-lg min-h-96">
                  <div className="text-center text-gray-500">
                    <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p>Document preview not available</p>
                    <p className="text-sm">The document image could not be loaded</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Document Information */}
          <div className="space-y-6">
            {/* Metadata */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Document Information</h2>
              </div>
              <div className="p-4 space-y-4">
                {document.metadata && (
                  <div className="grid grid-cols-1 gap-3">
                    {document.metadata.title && (
                      <div>
                        <label className="text-sm font-medium text-gray-700">Title</label>
                        <p className="text-sm text-gray-900">{document.metadata.title}</p>
                      </div>
                    )}
                    {document.metadata.author && (
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-700">Author:</span>
                        <span className="text-sm text-gray-900">{document.metadata.author}</span>
                      </div>
                    )}
                    {document.metadata.publication && (
                      <div>
                        <label className="text-sm font-medium text-gray-700">Publication</label>
                        <p className="text-sm text-gray-900">{document.metadata.publication}</p>
                      </div>
                    )}
                    {document.metadata.date && (
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-700">Date:</span>
                        <span className="text-sm text-gray-900">{document.metadata.date}</span>
                      </div>
                    )}
                    {document.metadata.page && (
                      <div>
                        <label className="text-sm font-medium text-gray-700">Page</label>
                        <p className="text-sm text-gray-900">{document.metadata.page}</p>
                      </div>
                    )}
                    {document.metadata.tags && document.metadata.tags.length > 0 && (
                      <div className="flex items-start space-x-2">
                        <Tag className="w-4 h-4 text-gray-400 mt-0.5" />
                        <div>
                          <span className="text-sm text-gray-700">Tags:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {(Array.isArray(document.metadata.tags) ? document.metadata.tags : document.metadata.tags.split(',')).map((tag, index) => (
                              <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                {tag.trim()}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    {document.metadata.description && (
                      <div>
                        <label className="text-sm font-medium text-gray-700">Description</label>
                        <p className="text-sm text-gray-900">{document.metadata.description}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Processing Information */}
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Processing Details</h3>
                  <div className="space-y-2 text-xs text-gray-600">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-3 h-3" />
                      <span>Uploaded: {new Date(document.uploadTimestamp).toLocaleString()}</span>
                    </div>
                    {document.ocrResults?.processedAt && (
                      <div className="flex items-center space-x-2">
                        <Clock className="w-3 h-3" />
                        <span>Processed: {new Date(document.ocrResults.processedAt).toLocaleString()}</span>
                      </div>
                    )}
                    {document.finalizedResults?.finalizedTimestamp && (
                      <div className="flex items-center space-x-2">
                        <Clock className="w-3 h-3" />
                        <span>Finalized: {new Date(document.finalizedResults.finalizedTimestamp).toLocaleString()}</span>
                      </div>
                    )}
                    {document.finalizedResults?.textSource && (
                      <div>
                        <span>Source: {document.finalizedResults.textSource === 'formatted' ? 'Formatted Text' : 'Refined Text (AI Enhanced)'}</span>
                      </div>
                    )}
                    {document.finalizedResults?.wasEditedBeforeFinalization && (
                      <div className="text-blue-600">
                        <span>• Text was edited by user before finalization</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Finalized Text */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {isEditing ? 'Edit Document' : 'Finalized Text'}
                  </h2>
                  {!isEditing && (
                    <div className="flex items-center space-x-2">
                      <button 
                        onClick={() => setShowFullText(!showFullText)}
                        className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
                      >
                        <Eye className="w-4 h-4" />
                        <span>{showFullText ? 'Show Less' : 'Show More'}</span>
                      </button>
                      <button 
                        onClick={handleCopyText}
                        className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-700"
                      >
                        <Copy className="w-4 h-4" />
                        <span>Copy</span>
                      </button>
                    </div>
                  )}
                </div>
                <p className="text-sm text-gray-500">
                  {isEditing ? 'Make changes to the document text and provide a reason for the edit' : `${finalizedText.length} characters • ${finalizedText.split(/\s+/).filter(w => w.length > 0).length} words`}
                </p>
              </div>
              <div className="p-4">
                {isEditing ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Edit Reason <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={editReason}
                        onChange={(e) => setEditReason(e.target.value)}
                        placeholder="Describe why you're making this edit..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={saving}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Document Text <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        value={editableText}
                        onChange={(e) => setEditableText(e.target.value)}
                        className="w-full h-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        disabled={saving}
                      />
                    </div>
                    <div className="flex items-center justify-end space-x-3">
                      <button
                        onClick={handleCancelEdit}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        disabled={saving}
                      >
                        <X className="w-4 h-4 inline mr-1" />
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveEdit}
                        className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                        disabled={saving || !editableText.trim() || !editReason.trim()}
                      >
                        <Save className="w-4 h-4 inline mr-1" />
                        {saving ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className={`text-sm text-gray-700 whitespace-pre-wrap ${showFullText ? '' : 'line-clamp-6'}`}>
                      {finalizedText}
                    </div>
                    {!showFullText && finalizedText.length > 300 && (
                      <div className="mt-2">
                        <button 
                          onClick={() => setShowFullText(true)}
                          className="text-blue-600 hover:text-blue-700 text-sm"
                        >
                          Show full text...
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentView;