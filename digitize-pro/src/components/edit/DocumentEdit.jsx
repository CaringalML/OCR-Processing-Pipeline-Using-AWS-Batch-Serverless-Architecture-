import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Download, RefreshCw, Eye, EyeOff, Undo, Redo, CheckCircle, FileText, Code, X } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import documentService from '../../services/documentService';
import uploadService from '../../services/uploadService';

const DocumentEdit = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  const { documents } = useDocuments();
  
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [editedText, setEditedText] = useState('');
  const [originalText, setOriginalText] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [editHistory, setEditHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [selectedTextType, setSelectedTextType] = useState('refined'); // 'formatted' or 'refined'
  const [finalizing, setFinalizing] = useState(false);
  const [textareaRef, setTextareaRef] = useState(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Load document data
  useEffect(() => {
    const loadDocument = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch from API to get latest data
        console.log('Fetching document with fileId:', fileId);
        const docData = await documentService.getDocument(fileId);
        console.log('Document data received:', docData);
        
        if (docData) {
          setDocument(docData);
          
          // Determine which text to show initially
          const formattedText = docData.ocrResults?.formattedText || '';
          const refinedText = docData.ocrResults?.refinedText || '';
          const extractedText = docData.ocrResults?.extractedText || '';
          
          let textToEdit = '';
          // If document is finalized, show the finalized text
          if (docData.finalized && docData.finalizedText) {
            textToEdit = docData.finalizedText;
            setSelectedTextType(docData.selectedTextType || 'refined');
          } else {
            // Prioritize refined text, then formatted, then extracted
            if (refinedText) {
              textToEdit = refinedText;
              setSelectedTextType('refined');
            } else if (formattedText) {
              textToEdit = formattedText;
              setSelectedTextType('formatted');
            } else {
              textToEdit = extractedText;
              setSelectedTextType('refined');
            }
          }
          
          setEditedText(textToEdit);
          setOriginalText(textToEdit);
          initializeHistory(textToEdit);
        } else {
          console.error('No document found for fileId:', fileId);
          setError('Document not found');
        }
      } catch (err) {
        setError(err.message);
        console.error('Error loading document:', err);
      } finally {
        setLoading(false);
      }
    };

    if (fileId) {
      loadDocument();
    }
  }, [fileId, documents]);

  // Initialize edit history
  const initializeHistory = (text) => {
    setEditHistory([text]);
    setHistoryIndex(0);
  };





  // Track changes
  useEffect(() => {
    setHasChanges(editedText !== originalText);
  }, [editedText, originalText]);

  // Handle text change with history
  const handleTextChange = (newText) => {
    setEditedText(newText);
    
    // Add to history if significant change
    if (newText !== editHistory[historyIndex]) {
      const newHistory = editHistory.slice(0, historyIndex + 1);
      newHistory.push(newText);
      setEditHistory(newHistory);
      setHistoryIndex(newHistory.length - 1);
    }
  };

  // Undo functionality
  const handleUndo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setEditedText(editHistory[newIndex]);
    }
  };

  // Redo functionality
  const handleRedo = () => {
    if (historyIndex < editHistory.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setEditedText(editHistory[newIndex]);
    }
  };

  // Save changes
  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const updateData = {
        userEdited: true,
        editTimestamp: new Date().toISOString()
      };

      // Save to the selected text type field
      if (selectedTextType === 'formatted') {
        updateData.formattedText = editedText;
      } else {
        updateData.refinedText = editedText;
      }

      await documentService.editOCRResults(fileId, updateData);

      setOriginalText(editedText);
      setHasChanges(false);
      
      // Show success message
      alert('Document saved successfully!');
    } catch (err) {
      setError(err.message);
      console.error('Save error:', err);
    } finally {
      setSaving(false);
    }
  };

  // Finalize document
  const handleFinalize = async () => {
    try {
      setFinalizing(true);
      setError(null);

      // Prepare finalization data
      const finalizationData = {
        textSource: selectedTextType,
        finalizedBy: 'user', // Could be replaced with actual user identification
        notes: hasChanges ? 'User edited text before finalization' : 'Used original text without editing'
      };

      // If user made changes, include the edited text
      if (hasChanges) {
        finalizationData.editedText = editedText;
        finalizationData.originalText = originalText;
      }

      console.log('Finalizing document:', {
        fileId,
        finalizationData
      });

      // Call the actual finalization API
      console.log('About to call finalization API with data:', finalizationData);
      const result = await documentService.finalizeDocument(fileId, finalizationData);
      
      console.log('Finalization successful:', result);
      
      // Show success message in custom modal
      setSuccessMessage('Document finalized and moved to inventory!');
      setShowSuccessModal(true);
      
      // Auto-navigate after 2 seconds
      setTimeout(() => {
        navigate('/inventory');
      }, 2000);
    } catch (err) {
      setError(err.message);
      console.error('Finalize error details:', {
        message: err.message,
        stack: err.stack,
        name: err.name,
        error: err
      });
      
      // More user-friendly error messages
      let errorMessage = 'Failed to finalize document. ';
      if (err.message.includes('404')) {
        errorMessage += 'Document not found or already finalized.';
      } else if (err.message.includes('400')) {
        errorMessage += 'Invalid request. Please check if the document has been processed.';
      } else if (err.message.includes('500')) {
        errorMessage += 'Server error. Please try again later.';
      } else if (err.message.includes('Failed to fetch')) {
        errorMessage += 'Network error. Please check your connection and try again.';
      } else {
        errorMessage += err.message;
      }
      
      alert(`${errorMessage}\n\nDEBUG: ${err.message}`);
    } finally {
      setFinalizing(false);
    }
  };

  // Switch between formatted and refined text
  const handleTextTypeSwitch = (type) => {
    if (type === selectedTextType) return;
    
    if (hasChanges && !window.confirm('You have unsaved changes. Switch text type anyway?')) {
      return;
    }

    setSelectedTextType(type);
    const newText = type === 'formatted' 
      ? (document.ocrResults?.formattedText || '') 
      : (document.ocrResults?.refinedText || document.ocrResults?.extractedText || '');
    
    setEditedText(newText);
    setOriginalText(newText);
    initializeHistory(newText);
    setHasChanges(false);
  };

  // Reset to original
  const handleReset = () => {
    if (window.confirm('Are you sure you want to discard all changes?')) {
      setEditedText(originalText);
      initializeHistory(originalText);
    }
  };

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
            onClick={() => navigate('/upload')}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
          >
            Back to Upload Queue
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
            onClick={() => navigate('/upload')}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
          >
            Back to Upload Queue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => navigate('/upload')}
                className="text-gray-600 hover:text-gray-900 flex items-center space-x-2"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Back to Upload Queue</span>
              </button>
              <div className="h-6 w-px bg-gray-300"></div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {document.metadata?.title || document.fileName || document.original_filename || document.file_name || 'Untitled Document'}
                </h1>
                <p className="text-sm text-gray-500">
                  {document.fileSize || uploadService.formatFileSize(document.file_size || 0)} • {document.processingType || 'Unknown processing'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              {/* Undo/Redo */}
              <button 
                onClick={handleUndo}
                disabled={historyIndex <= 0}
                className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Undo"
              >
                <Undo className="w-4 h-4" />
              </button>
              <button 
                onClick={handleRedo}
                disabled={historyIndex >= editHistory.length - 1}
                className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Redo"
              >
                <Redo className="w-4 h-4" />
              </button>
              
              <div className="h-6 w-px bg-gray-300"></div>
              
              
              {/* Preview Toggle */}
              <button 
                onClick={() => setShowPreview(!showPreview)}
                className="p-2 text-gray-400 hover:text-gray-600"
                title={showPreview ? "Hide Preview" : "Show Preview"}
              >
                {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
              
              {/* Download */}
              <button 
                onClick={handleDownload}
                className="p-2 text-gray-400 hover:text-gray-600"
                title="Download Original"
              >
                <Download className="w-4 h-4" />
              </button>
              
              {/* Reset */}
              {hasChanges && (
                <button 
                  onClick={handleReset}
                  className="border border-gray-300 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-50"
                >
                  Reset
                </button>
              )}
              
              
              {/* Finalize - only show if not finalized */}
              {!document?.finalized && (
                <button 
                  onClick={handleFinalize}
                  disabled={finalizing}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  title="Finalize document and save to server permanently"
                >
                  {finalizing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  <span>{finalizing ? 'Finalizing...' : 'Finalize Document'}</span>
                </button>
              )}
              
              
              {/* Already finalized message */}
              {document?.finalized && (
                <div className="flex items-center space-x-2 text-green-600">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">Document Finalized</span>
                  <button 
                    onClick={() => navigate('/upload')}
                    className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm hover:bg-green-200"
                  >
                    View in Upload Queue
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-8rem)]">
          {/* Document Viewer */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Original Document</h2>
              <p className="text-sm text-gray-500">
                {document.ocrResults?.languageDetection?.detected_language || 'Language not detected'} • 
                Processing: {document.ocrResults?.processingDuration || 'Unknown'} • 
                Confidence: {document.textAnalysis?.qualityAssessment?.confidence_score || 'N/A'}%
              </p>
            </div>
            <div className="flex-1 p-4 overflow-hidden">
              {document.cloudFrontUrl ? (
                <div className="h-full flex items-center justify-center bg-gray-100 rounded-lg">
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
                    <p className="text-sm">The document may be processing or the preview is unavailable</p>
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center bg-gray-100 rounded-lg">
                  <div className="text-center text-gray-500">
                    <p>Document preview not available</p>
                    <p className="text-sm">The document is still being processed</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Text Editor */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {showPreview ? 'Text Preview' : 'OCR Text Editor'}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {editedText.length} characters • {editedText.split(/\s+/).filter(w => w.length > 0).length} words
                    {hasChanges && <span className="text-orange-600 ml-2">• Unsaved changes</span>}
                    {document?.finalized && <span className="text-green-600 ml-2">• Document Finalized</span>}
                  </p>
                </div>
                
                {/* OCR Quality Assessment */}
                {document.textAnalysis?.qualityAssessment && (
                  <div className="text-sm flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      document.textAnalysis.qualityAssessment.assessment === 'excellent' ? 'bg-green-100 text-green-800' :
                      document.textAnalysis.qualityAssessment.assessment === 'good' ? 'bg-blue-100 text-blue-800' :
                      document.textAnalysis.qualityAssessment.assessment === 'fair' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-orange-100 text-orange-800'
                    }`}>
                      OCR Quality: {document.textAnalysis.qualityAssessment.assessment.charAt(0).toUpperCase() + document.textAnalysis.qualityAssessment.assessment.slice(1)}
                    </span>
                    <span className="text-xs text-gray-500">
                      Confidence: {document.textAnalysis.qualityAssessment.confidence_score}%
                    </span>
                  </div>
                )}
              </div>
              
              {/* Text Type Selector */}
              {document?.ocrResults && (document.ocrResults.formattedText || document.ocrResults.refinedText) && (
                <div className="mt-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700">Select Text Version:</span>
                    <button
                      onClick={() => handleTextTypeSwitch('formatted')}
                      disabled={!document.ocrResults.formattedText}
                      className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center space-x-1 ${
                        selectedTextType === 'formatted' 
                          ? 'bg-blue-100 text-blue-700 border border-blue-300' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-300'
                      } ${!document.ocrResults.formattedText ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title="Direct OCR extraction with formatting preserved"
                    >
                      <Code className="w-3 h-3" />
                      <span>Formatted Text</span>
                    </button>
                    <button
                      onClick={() => handleTextTypeSwitch('refined')}
                      disabled={!document.ocrResults.refinedText && !document.ocrResults.extractedText}
                      className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center space-x-1 ${
                        selectedTextType === 'refined' 
                          ? 'bg-blue-100 text-blue-700 border border-blue-300' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-300'
                      } ${!document.ocrResults.refinedText && !document.ocrResults.extractedText ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title="AI-enhanced version with improved grammar and clarity"
                    >
                      <FileText className="w-3 h-3" />
                      <span>Refined Text (AI Enhanced)</span>
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 ml-1">
                    {selectedTextType === 'formatted' 
                      ? '📝 Showing original OCR text with preserved formatting' 
                      : '✨ Showing AI-refined text with enhanced grammar and readability (powered by Claude AI)'}
                  </p>
                </div>
              )}
            </div>

            
            <div className="flex-1 p-4">
              {showPreview ? (
                <div className="h-full overflow-y-auto bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="prose max-w-none">
                    {editedText.split('\n').map((paragraph, index) => (
                      <p key={index} className="mb-3 text-gray-900">
                        {paragraph || <span className="text-gray-400">Empty line</span>}
                      </p>
                    ))}
                  </div>
                </div>
              ) : (
                <textarea
                  ref={setTextareaRef}
                  value={editedText}
                  onChange={(e) => handleTextChange(e.target.value)}
                  disabled={document?.finalized}
                  className={`w-full h-full p-4 border rounded-lg font-mono text-sm resize-none ${
                    document?.finalized 
                      ? 'border-gray-200 bg-gray-50 text-gray-700 cursor-not-allowed' 
                      : 'border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent'
                  }`}
                  placeholder={document?.finalized ? "Document is finalized and cannot be edited" : "OCR extracted text will appear here..."}
                  spellCheck={!document?.finalized}
                />
              )}
            </div>

            {/* Entity Analysis */}
            {document.ocrResults?.entityAnalysis?.entities && document.ocrResults.entityAnalysis.entities.length > 0 && (
              <div className="p-4 border-t border-gray-200 bg-gray-50">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Detected Entities</h3>
                <div className="flex flex-wrap gap-2">
                  {document.ocrResults.entityAnalysis.entities.slice(0, 6).map((entity, index) => (
                    <span 
                      key={index}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {entity}
                    </span>
                  ))}
                  {document.ocrResults.entityAnalysis.entities.length > 6 && (
                    <span className="text-xs text-gray-500">
                      +{document.ocrResults.entityAnalysis.entities.length - 6} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quality Assessment Issues */}
        {document.textAnalysis?.qualityAssessment?.issues && document.textAnalysis.qualityAssessment.issues.length > 0 && (
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-yellow-800 mb-2">OCR Quality Issues Detected</h3>
            <ul className="text-sm text-yellow-700 space-y-1">
              {document.textAnalysis.qualityAssessment.issues.map((issue, index) => (
                <li key={index} className="flex items-start">
                  <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 mx-4 max-w-md w-full shadow-xl text-center">
            <div className="flex justify-center mb-4">
              <CheckCircle className="w-16 h-16 text-green-500" />
            </div>
            
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Success!</h3>
            
            <p className="text-gray-600 mb-4">{successMessage}</p>
            
            <div className="flex items-center justify-center text-sm text-gray-500">
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
              <span>Redirecting to inventory...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentEdit;