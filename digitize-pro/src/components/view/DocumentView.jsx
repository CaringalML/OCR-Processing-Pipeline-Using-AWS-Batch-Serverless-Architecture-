import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, FileText, Clock, Eye, Copy, Edit, Save, X, Search, ChevronDown, ChevronUp } from 'lucide-react';
import Zoom from 'react-medium-image-zoom';
import 'react-medium-image-zoom/dist/styles.css';
import documentService from '../../services/documentService';
import uploadService from '../../services/uploadService';
import { LocalDateTime, LocalDateTimeFull } from '../common/LocalTime';

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
  const [pdfViewerError, setPdfViewerError] = useState(false);
  const [magnifyEnabled, setMagnifyEnabled] = useState(false);
  const [magnifyLevel, setMagnifyLevel] = useState(2);
  const [showDetailedMetadata, setShowDetailedMetadata] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [copyStatus, setCopyStatus] = useState('idle'); // 'idle', 'copying', 'copied', 'error'
  const [showFullEditHistory, setShowFullEditHistory] = useState(false);

  // Detect file type from filename or URL
  const getFileType = () => {
    const fileName = document?.fileName || document?.original_filename || document?.file_name || '';
    const url = document?.cloudFrontUrl || '';
    
    // Check file extension
    const extension = fileName.toLowerCase().split('.').pop();
    if (extension === 'pdf') return 'pdf';
    
    // Check URL path
    if (url.toLowerCase().includes('.pdf')) return 'pdf';
    
    // Default to image for other formats
    return 'image';
  };

  // Load document data
  useEffect(() => {
    const loadDocument = async () => {
      try {
        setLoading(true);
        setError(null);
        setPdfViewerError(false);

        console.log('Fetching document for view with fileId:', fileId);
        // Since we're viewing from inventory, we want to fetch the finalized version
        const docData = await documentService.getDocument(fileId, true);
        console.log('Document data received for view:', docData);
        
        if (docData) {
          console.log('Document data loaded in view:', docData);
          console.log('CloudFront URL:', docData.cloudFrontUrl);
          console.log('File name:', docData.fileName || docData.original_filename || docData.file_name);
          
          // Check file type manually for logging
          const fileName = docData.fileName || docData.original_filename || docData.file_name || '';
          const url = docData.cloudFrontUrl || '';
          const extension = fileName.toLowerCase().split('.').pop();
          const fileType = (extension === 'pdf' || url.toLowerCase().includes('.pdf')) ? 'pdf' : 'image';
          console.log('File type detected:', fileType);
          
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
      const a = window.document.createElement('a');
      a.href = url;
      a.download = document.fileName || document.original_filename || document.file_name || 'document';
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download document');
    }
  };

  // Copy text to clipboard
  const handleCopyText = async () => {
    setCopyStatus('copying');
    try {
      const textToCopy = getFinalizedText();
      await navigator.clipboard.writeText(textToCopy);
      setCopyStatus('copied');
      // Reset to idle after 2 seconds
      setTimeout(() => setCopyStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to copy text:', error);
      setCopyStatus('error');
      // Reset to idle after 3 seconds
      setTimeout(() => setCopyStatus('idle'), 3000);
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

  // Magnification controls
  const [magnifyPosition, setMagnifyPosition] = useState({ x: 0, y: 0 });
  const [showMagnifier, setShowMagnifier] = useState(false);

  const toggleMagnify = () => {
    setMagnifyEnabled(!magnifyEnabled);
    setShowMagnifier(false);
  };

  const increaseMagnify = () => {
    setMagnifyLevel(prev => Math.min(prev + 0.5, 10));
  };

  const decreaseMagnify = () => {
    setMagnifyLevel(prev => Math.max(prev - 0.5, 1));
  };

  const handleMouseMove = (e) => {
    if (!magnifyEnabled) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const img = e.currentTarget.querySelector('img');
    if (!img) return;
    
    const imgRect = img.getBoundingClientRect();
    const x = e.clientX - imgRect.left;
    const y = e.clientY - imgRect.top;
    
    // Ensure cursor is within image bounds
    if (x < 0 || y < 0 || x > imgRect.width || y > imgRect.height) {
      setShowMagnifier(false);
      return;
    }
    
    // Calculate exact percentage position on the image for perfect magnification
    const xPercent = Math.max(0, Math.min(100, (x / imgRect.width) * 100));
    const yPercent = Math.max(0, Math.min(100, (y / imgRect.height) * 100));
    
    // Enhanced magnifier positioning with proper viewport boundary checking
    const magnifierWidth = 220;
    const magnifierHeight = 150;
    const offset = 15;
    
    // Start with default positioning relative to container
    let magnifierX = e.clientX - rect.left + offset;
    let magnifierY = e.clientY - rect.top - magnifierHeight - offset;
    
    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Calculate absolute position of magnifier in viewport
    const absoluteMagnifierLeft = rect.left + magnifierX;
    const absoluteMagnifierRight = absoluteMagnifierLeft + magnifierWidth;
    const absoluteMagnifierTop = rect.top + magnifierY;
    
    // Check right edge - if magnifier goes off viewport right, move to left of cursor
    if (absoluteMagnifierRight > viewportWidth) {
      magnifierX = e.clientX - rect.left - magnifierWidth - offset;
    }
    
    // Check left edge - if magnifier goes off viewport left, move to right of cursor
    if (rect.left + magnifierX < 0) {
      magnifierX = e.clientX - rect.left + offset;
      // If still off left edge, clamp to viewport
      if (rect.left + magnifierX < 0) {
        magnifierX = -rect.left + 10;
      }
    }
    
    // Check top edge - if magnifier goes above viewport, move below cursor
    if (absoluteMagnifierTop < 0) {
      magnifierY = e.clientY - rect.top + offset;
    }
    
    // Recalculate after Y adjustment and check bottom edge
    const newAbsoluteBottom = rect.top + magnifierY + magnifierHeight;
    if (newAbsoluteBottom > viewportHeight) {
      magnifierY = e.clientY - rect.top - magnifierHeight - offset;
      // If still goes below, clamp to viewport
      if (rect.top + magnifierY + magnifierHeight > viewportHeight) {
        magnifierY = (viewportHeight - rect.top - magnifierHeight - 10);
      }
    }
    
    // Ensure final position is within container bounds
    magnifierX = Math.max(0, Math.min(magnifierX, rect.width - magnifierWidth));
    magnifierY = Math.max(0, Math.min(magnifierY, rect.height - magnifierHeight));
    
    setMagnifyPosition({ 
      x: magnifierX, 
      y: magnifierY,
      xPercent, 
      yPercent,
      imgWidth: imgRect.width,
      imgHeight: imgRect.height
    });
    setShowMagnifier(true);
  };

  const handleMouseLeave = () => {
    setShowMagnifier(false);
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
        editReason: editReason
      };

      const result = await documentService.editFinalizedDocument(fileId, editData);
      
      console.log('Edit successful:', result);
      
      // Refresh the full document from server to get updated metadata and edit history
      try {
        const refreshedDocument = await documentService.getDocument(fileId, true);
        setDocument(refreshedDocument);
        console.log('Document refreshed after edit:', refreshedDocument);
      } catch (refreshError) {
        console.warn('Could not refresh document after edit:', refreshError);
        // Fallback: update just the finalized text
        const updatedDocument = {
          ...document,
          finalizedResults: {
            ...document.finalizedResults,
            finalizedText: editableText
          }
        };
        setDocument(updatedDocument);
      }
      
      // Reset edit state
      setIsEditing(false);
      setEditableText('');
      setEditReason('');
      
      setSuccessMessage(`Document updated successfully! ${result.message || ''}`);
      // Auto-hide success message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
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
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md border border-blue-200 transition-all"
                  title="Edit Document"
                >
                  <Edit className="w-4 h-4" />
                  <span>Edit</span>
                </button>
              )}
              
              {getFileType() === 'pdf' && document.cloudFrontUrl && (
                <button 
                  onClick={() => window.open(document.cloudFrontUrl, '_blank')}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-700 hover:bg-gray-50 rounded-md border border-gray-200 transition-all"
                  title="Open PDF in New Tab"
                >
                  <Eye className="w-4 h-4" />
                  <span>View PDF</span>
                </button>
              )}
              
              {/* Only show magnification controls for images, not PDFs */}
              {getFileType() === 'image' && (
                <div className="flex items-center gap-2">
                  {/* Custom Magnifier Toggle */}
                  <button 
                    onClick={toggleMagnify}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md border transition-all ${
                      magnifyEnabled 
                        ? 'text-white bg-green-600 border-green-700 shadow-md' 
                        : 'text-gray-600 bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                    title={magnifyEnabled ? 'Disable Magnifier' : 'Enable Cursor Magnifier'}
                  >
                    <Search className="w-4 h-4" />
                    <span>
                      {magnifyEnabled ? `${magnifyLevel}x` : 'Magnify'}
                    </span>
                  </button>
                  
                  {/* Zoom Controls */}
                  {magnifyEnabled && (
                    <div className="flex items-center border border-gray-300 rounded-md bg-white">
                      <button
                        onClick={decreaseMagnify}
                        disabled={magnifyLevel <= 1}
                        className="px-2 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-50 rounded-l-md"
                        title="Decrease zoom"
                      >
                        <span className="text-sm font-bold">−</span>
                      </button>
                      <div className="px-2 py-1 text-xs font-semibold text-gray-700 border-x border-gray-200">
                        {magnifyLevel}x
                      </div>
                      <button
                        onClick={increaseMagnify}
                        disabled={magnifyLevel >= 10}
                        className="px-2 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-50 rounded-r-md"
                        title="Increase zoom"
                      >
                        <span className="text-sm font-bold">+</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              <button 
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-700 hover:bg-gray-50 rounded-md border border-gray-200 transition-all"
                title={getFileType() === 'pdf' ? 'Download PDF' : 'Download Original'}
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">{successMessage}</p>
              </div>
            </div>
            <div className="ml-auto pl-3">
              <div className="-mx-1.5 -my-1.5">
                <button
                  onClick={() => setSuccessMessage('')}
                  className="inline-flex bg-green-50 rounded-md p-1.5 text-green-500 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-green-50 focus:ring-green-600"
                >
                  <span className="sr-only">Dismiss</span>
                  <svg className="h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[80vh]">
          {/* Document Image - Fixed Height */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-full">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {getFileType() === 'pdf' ? 'Original PDF Document' : 'Scanned Document'}
              </h2>
              <p className="text-sm text-gray-500">
                {document.ocrResults?.languageDetection?.detected_language || 'Language not detected'} • 
                Processing: {document.ocrResults?.processingDuration || 'Unknown'} • 
                Quality: {(document.finalizedResults?.textAnalysis?.qualityAssessment?.confidence_score || 
                          document.textAnalysis?.qualityAssessment?.confidence_score || 'N/A')}%
              </p>
            </div>
            <div className="flex-1 p-4">
              {document.cloudFrontUrl ? (
                <div className="bg-gray-100 rounded-lg h-full min-h-96">
                  {getFileType() === 'pdf' ? (
                    // PDF Viewer
                    !pdfViewerError ? (
                      <div className="w-full h-full rounded-lg overflow-hidden min-h-96">
                        <iframe
                          src={`${document.cloudFrontUrl}#view=FitH&toolbar=0&navpanes=0`}
                          className="w-full h-full border-0 rounded-lg"
                          title={document.fileName || document.original_filename || 'PDF Document'}
                          onLoad={() => {
                            // PDF loaded successfully in iframe
                            console.log('PDF viewer loaded successfully');
                          }}
                          onError={() => setPdfViewerError(true)}
                        />
                      </div>
                    ) : (
                      // PDF Fallback View
                      <div className="flex items-center justify-center h-full min-h-96 text-center text-gray-500">
                        <div>
                          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                          <p className="font-medium">PDF Preview</p>
                          <p className="text-sm mb-4">This PDF document is ready to view or download</p>
                          <div className="space-y-2">
                            <button 
                              onClick={() => window.open(document.cloudFrontUrl, '_blank')}
                              className="w-full inline-flex items-center justify-center px-4 py-2 border border-green-300 rounded-md shadow-sm text-sm font-medium text-green-700 bg-green-50 hover:bg-green-100"
                            >
                              <Eye className="w-4 h-4 mr-2" />
                              Open PDF in New Tab
                            </button>
                            <button 
                              onClick={handleDownload}
                              className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download PDF
                            </button>
                          </div>
                        </div>
                      </div>
                    )
                  ) : (
                    // Image Viewer with Dual Zoom Options
                    <div 
                      className={`relative flex items-center justify-center rounded-lg h-full min-h-96 ${
                        magnifyEnabled ? 'cursor-none' : ''
                      }`}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={handleMouseLeave}
                    >
                      <Zoom>
                        <img 
                          src={document.cloudFrontUrl}
                          alt={document.fileName || document.original_filename || 'Document'}
                          className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                          style={{ 
                            cursor: magnifyEnabled ? 'none' : 'zoom-in',
                            userSelect: 'none'
                          }}
                          onError={(e) => {
                            e.target.style.display = 'none';
                            const fallbackDiv = e.target.parentNode.querySelector('.fallback-content');
                            if (fallbackDiv) fallbackDiv.style.display = 'block';
                          }}
                        />
                      </Zoom>
                      
                      {/* E-commerce Style Magnifier - Fast and Smooth */}
                      {magnifyEnabled && showMagnifier && magnifyPosition.xPercent !== undefined && (
                        <div
                          className="absolute pointer-events-none border-2 border-blue-400 shadow-xl rounded-lg overflow-hidden z-50 bg-white"
                          style={{
                            left: magnifyPosition.x,
                            top: magnifyPosition.y,
                            width: '220px',
                            height: '150px',
                          }}
                        >
                          <div
                            className="w-full h-full relative"
                            style={{
                              backgroundImage: `url(${document.cloudFrontUrl})`,
                              backgroundSize: `${magnifyLevel * 100}%`,
                              backgroundPosition: `${magnifyPosition.xPercent}% ${magnifyPosition.yPercent}%`,
                              backgroundRepeat: 'no-repeat',
                              imageRendering: 'pixelated'
                            }}
                          >
                            <div className="absolute top-1 right-1 bg-black bg-opacity-60 text-white text-xs px-1.5 py-0.5 rounded">
                              {magnifyLevel}x
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <div className="fallback-content text-center text-gray-500 hidden">
                        <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p>Unable to load document preview</p>
                        <p className="text-sm">The document image is not available</p>
                        <button 
                          onClick={handleDownload}
                          className="mt-3 inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Download Original
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center bg-gray-100 rounded-lg h-full min-h-96">
                  <div className="text-center text-gray-500">
                    <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p>Document preview not available</p>
                    <p className="text-sm">The document could not be loaded</p>
                    <button 
                      onClick={handleDownload}
                      className="mt-3 inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download Original
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Document Information - Scrollable Panel */}
          <div className="space-y-6 h-full overflow-y-auto">
            {/* Metadata */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Document Information</h2>
              </div>
              <div className="p-4">
                {/* Compact Summary View */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 rounded-lg border border-blue-200">
                  {/* Essential Publication Info - Always Visible */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center">
                      <FileText className="w-4 h-4 mr-2 text-blue-600" />
                      <h3 className="text-sm font-semibold text-gray-800">Document Information</h3>
                    </div>
                    <button
                      onClick={() => setShowDetailedMetadata(!showDetailedMetadata)}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-100 rounded transition-colors"
                    >
                      {showDetailedMetadata ? (
                        <React.Fragment>
                          <ChevronUp className="w-3 h-3" />
                          Show Less
                        </React.Fragment>
                      ) : (
                        <React.Fragment>
                          <ChevronDown className="w-3 h-3" />
                          Show More
                        </React.Fragment>
                      )}
                    </button>
                  </div>

                  {/* Essential Info - Always Shown */}
                  <div className="space-y-1.5 text-xs">
                    {document.metadata?.title && (
                      <div className="flex">
                        <span className="font-medium text-gray-600 w-16">Title:</span>
                        <span className="text-gray-900 flex-1">{document.metadata.title}</span>
                      </div>
                    )}
                    {document.metadata?.author && (
                      <div className="flex">
                        <span className="font-medium text-gray-600 w-16">Author:</span>
                        <span className="text-gray-900 flex-1">{document.metadata.author}</span>
                      </div>
                    )}
                    {document.metadata?.date && (
                      <div className="flex">
                        <span className="font-medium text-gray-600 w-16">Date:</span>
                        <span className="text-gray-900 flex-1">{document.metadata.date}</span>
                      </div>
                    )}
                    <div className="flex">
                      <span className="font-medium text-gray-600 w-16">File:</span>
                      <span className="text-gray-900 flex-1">{document.fileName || document.original_filename || document.file_name || 'Unknown'} • {document.fileSize || uploadService.formatFileSize(document.file_size || 0)} • {getFileType().toUpperCase()}</span>
                    </div>
                  </div>

                  {/* Detailed Info - Collapsible */}
                  {showDetailedMetadata && (
                    <div className="mt-4 pt-3 border-t border-blue-200">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {/* Publication Metadata */}
                        {document.metadata?.publication && (
                          <div>
                            <span className="font-medium text-gray-600">Publication:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.publication}</p>
                          </div>
                        )}
                        {document.metadata?.page && (
                          <div>
                            <span className="font-medium text-gray-600">Page:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.page}</p>
                          </div>
                        )}
                        {document.metadata?.collection && (
                          <div>
                            <span className="font-medium text-gray-600">Collection:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.collection}</p>
                          </div>
                        )}
                        {document.metadata?.documentType && (
                          <div>
                            <span className="font-medium text-gray-600">Document Type:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.documentType}</p>
                          </div>
                        )}
                        {document.metadata?.subject && (
                          <div>
                            <span className="font-medium text-gray-600">Subject:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.subject}</p>
                          </div>
                        )}
                        {document.metadata?.language && (
                          <div>
                            <span className="font-medium text-gray-600">Language:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.language}</p>
                          </div>
                        )}
                        {document.metadata?.rights && (
                          <div>
                            <span className="font-medium text-gray-600">Rights:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.rights}</p>
                          </div>
                        )}
                        {document.processingType && (
                          <div>
                            <span className="font-medium text-gray-600">Processing:</span>
                            <p className="text-gray-900 mt-0.5">{document.processingType}</p>
                          </div>
                        )}
                        {(document.finalizedResults?.languageDetection || document.ocrResults?.languageDetection) && (
                          <div>
                            <span className="font-medium text-gray-600">Detected Language:</span>
                            <p className="text-gray-900 mt-0.5">
                              {(document.finalizedResults?.languageDetection?.detected_language || 
                                document.ocrResults?.languageDetection?.detected_language)}
                            </p>
                          </div>
                        )}
                        {document.ocrResults?.pages && (
                          <div>
                            <span className="font-medium text-gray-600">Pages:</span>
                            <p className="text-gray-900 mt-0.5">{document.ocrResults.pages}</p>
                          </div>
                        )}
                        {document.ocrResults?.processingDuration && (
                          <div>
                            <span className="font-medium text-gray-600">Processing Time:</span>
                            <p className="text-gray-900 mt-0.5">{document.ocrResults.processingDuration}</p>
                          </div>
                        )}
                        {(document.finalizedResults?.textAnalysis?.qualityAssessment?.confidence_score || 
                          document.textAnalysis?.qualityAssessment?.confidence_score) && (
                          <div>
                            <span className="font-medium text-gray-600">OCR Quality:</span>
                            <p className="text-gray-900 mt-0.5">
                              {(document.finalizedResults?.textAnalysis?.qualityAssessment?.confidence_score || 
                                document.textAnalysis?.qualityAssessment?.confidence_score)}%
                            </p>
                          </div>
                        )}
                        
                        {/* Description - Full Width */}
                        {document.metadata?.description && (
                          <div className="sm:col-span-2">
                            <span className="font-medium text-gray-600">Description:</span>
                            <p className="text-gray-900 mt-0.5">{document.metadata.description}</p>
                          </div>
                        )}
                        
                        {/* Tags - Full Width */}
                        {document.metadata?.tags && document.metadata.tags.length > 0 && (
                          <div className="sm:col-span-2">
                            <span className="font-medium text-gray-600">Tags:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {(Array.isArray(document.metadata.tags) ? document.metadata.tags : document.metadata.tags.split(',')).map((tag, index) => (
                                <span key={index} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                  {tag.trim()}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Entities - Full Width */}
                        {(document.ocrResults?.entityAnalysis?.entities || document.finalizedResults?.entityAnalysis?.entities) && (
                          <div className="sm:col-span-2">
                            <span className="font-medium text-gray-600">Detected Entities:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {(() => {
                                // Use finalized results entities if available, otherwise use OCR results
                                const entities = document.finalizedResults?.entityAnalysis?.entities || 
                                                document.ocrResults?.entityAnalysis?.entities || [];
                                
                                return (
                                  <>
                                    {entities.slice(0, 10).map((entity, index) => (
                                      <span key={index} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                        {entity}
                                      </span>
                                    ))}
                                    {entities.length > 10 && (
                                      <span className="text-xs text-gray-500 px-1.5 py-0.5">
                                        +{entities.length - 10} more
                                      </span>
                                    )}
                                  </>
                                );
                              })()}
                            </div>
                            {document.finalizedResults?.entityAnalysis?.entities && (
                              <p className="text-xs text-gray-500 mt-1">
                                From finalized document analysis
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Processing Information */}
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Processing Details</h3>
                  <div className="space-y-2 text-xs text-gray-600">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-3 h-3" />
                      <span>Uploaded: <LocalDateTimeFull timestamp={document.uploadTimestamp} /></span>
                    </div>
                    {document.ocrResults?.processedAt && (
                      <div className="flex items-center space-x-2">
                        <Clock className="w-3 h-3" />
                        <span>Processed: <LocalDateTimeFull timestamp={document.ocrResults.processedAt} /></span>
                      </div>
                    )}
                    {document.finalizedResults?.finalizedTimestamp && (
                      <div className="flex items-center space-x-2">
                        <Clock className="w-3 h-3" />
                        <span>Finalized: <LocalDateTimeFull timestamp={document.finalizedResults.finalizedTimestamp} /></span>
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

            {/* Edit History */}
            {document.finalizedResults?.editHistory && document.finalizedResults.editHistory.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900">Edit History</h2>
                      <p className="text-sm text-gray-500">
                        {document.finalizedResults.editHistory.length} edit{document.finalizedResults.editHistory.length !== 1 ? 's' : ''} made to this document
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        History entries are automatically removed after 30 days
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowFullEditHistory(!showFullEditHistory)}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-100 rounded transition-colors"
                      >
                        {showFullEditHistory ? (
                          <React.Fragment>
                            <ChevronUp className="w-3 h-3" />
                            Hide
                          </React.Fragment>
                        ) : (
                          <React.Fragment>
                            <ChevronDown className="w-3 h-3" />
                            Show
                          </React.Fragment>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
                {showFullEditHistory && (
                  <div className="p-4">
                    <div className="space-y-4">
                      {document.finalizedResults.editHistory.slice().reverse().map((edit, index) => (
                        <div 
                          key={index} 
                          onClick={() => navigate(`/history/${fileId}`)}
                          className="bg-gray-50 rounded-lg p-3 border border-gray-200 cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-colors"
                          title="Click to view detailed edit history with text comparison"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                Edit #{document.finalizedResults.editHistory.length - index}
                              </span>
                            </div>
                            <span className="text-xs text-gray-500">
                              <LocalDateTime timestamp={edit.timestamp} />
                            </span>
                          </div>
                          
                          {edit.edit_reason && (
                            <div className="mb-2">
                              <span className="text-xs font-medium text-gray-700">Reason: </span>
                              <span className="text-xs text-gray-600">{edit.edit_reason}</span>
                            </div>
                          )}
                          
                          {edit.text_length_change !== undefined && (
                            <div className="text-xs text-gray-500">
                              Text length change: 
                              <span className={`ml-1 font-medium ${edit.text_length_change > 0 ? 'text-green-600' : edit.text_length_change < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                                {edit.text_length_change > 0 ? '+' : ''}{edit.text_length_change} characters
                              </span>
                            </div>
                          )}
                          
                          <div className="mt-2 text-xs text-blue-600">
                            Click to view detailed comparison →
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

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
                        disabled={copyStatus === 'copying'}
                        className={`flex items-center space-x-1 text-sm transition-colors ${
                          copyStatus === 'copied' ? 'text-green-600' : 
                          copyStatus === 'error' ? 'text-red-600' : 
                          'text-gray-600 hover:text-gray-700'
                        }`}
                      >
                        {copyStatus === 'copying' ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        ) : copyStatus === 'copied' ? (
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                        <span>
                          {copyStatus === 'copying' ? 'Copying...' : 
                           copyStatus === 'copied' ? 'Copied!' : 
                           copyStatus === 'error' ? 'Failed' : 'Copy'}
                        </span>
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
                        className="w-full h-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm modern-scrollbar"
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
                  <React.Fragment>
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
                  </React.Fragment>
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