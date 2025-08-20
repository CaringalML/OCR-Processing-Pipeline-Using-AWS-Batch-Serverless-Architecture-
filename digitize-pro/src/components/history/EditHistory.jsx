import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, User, FileText, ChevronRight, Minimize2, Maximize2, Info, RefreshCw } from 'lucide-react';
import documentService from '../../services/documentService';
import { LocalDateTime } from '../common/LocalTime';

const EditHistory = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [editHistory, setEditHistory] = useState([]);
  const [selectedEdit, setSelectedEdit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('side-by-side'); // 'side-by-side' or 'inline'

  useEffect(() => {
    fetchDocumentAndHistory();
  }, [fileId]);

  const fetchDocumentAndHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get document details with finalized=true to get edit history
      const doc = await documentService.getDocument(fileId, true);
      
      if (!doc) {
        setError('Document not found');
        return;
      }
      
      setDocument(doc);
      
      // Get edit history from finalizedResults
      const history = doc.finalizedResults?.editHistory || [];
      setEditHistory(history);
      
      // If history exists, select the most recent edit by default
      if (history.length > 0) {
        setSelectedEdit(history[0]);
      }
    } catch (err) {
      console.error('Error fetching document history:', err);
      setError('Failed to load edit history');
    } finally {
      setLoading(false);
    }
  };


  const getTextChangeSummary = (edit) => {
    const lengthChange = edit.text_length_change || 0;
    if (lengthChange > 0) {
      return <span className="text-green-600">+{lengthChange} characters</span>;
    } else if (lengthChange < 0) {
      return <span className="text-red-600">{lengthChange} characters</span>;
    } else {
      return <span className="text-gray-500">No length change</span>;
    }
  };

  const renderTextComparison = () => {
    if (!selectedEdit) return null;

    const previousText = selectedEdit.previous_text || '';
    const newText = selectedEdit.new_text || '';

    if (viewMode === 'side-by-side') {
      return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Previous Text */}
          <div className="flex flex-col">
            <div className="bg-red-50 border border-red-200 rounded-t-lg px-4 py-3">
              <h4 className="text-base font-semibold text-red-700">Previous Text</h4>
              <p className="text-sm text-red-600">{previousText.length} characters</p>
            </div>
            <div className="bg-red-50 border border-red-200 border-t-0 rounded-b-lg p-4 min-h-[400px] max-h-[600px] overflow-auto">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                {previousText || <span className="text-gray-400 italic">No previous text</span>}
              </pre>
            </div>
          </div>

          {/* New Text */}
          <div className="flex flex-col">
            <div className="bg-green-50 border border-green-200 rounded-t-lg px-4 py-3">
              <h4 className="text-base font-semibold text-green-700">New Text</h4>
              <p className="text-sm text-green-600">{newText.length} characters</p>
            </div>
            <div className="bg-green-50 border border-green-200 border-t-0 rounded-b-lg p-4 min-h-[400px] max-h-[600px] overflow-auto">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                {newText || <span className="text-gray-400 italic">No new text</span>}
              </pre>
            </div>
          </div>
        </div>
      );
    } else {
      // Inline view - show changes sequentially
      return (
        <div className="space-y-6">
          {/* Previous Text */}
          <div>
            <div className="bg-red-50 border border-red-200 rounded-lg">
              <div className="px-4 py-3 border-b border-red-200">
                <h4 className="text-base font-semibold text-red-700">Previous Text</h4>
                <p className="text-sm text-red-600">{previousText.length} characters</p>
              </div>
              <div className="p-4 max-h-[300px] overflow-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                  {previousText || <span className="text-gray-400 italic">No previous text</span>}
                </pre>
              </div>
            </div>
          </div>

          {/* Arrow indicating change */}
          <div className="flex justify-center">
            <div className="bg-gray-100 rounded-full p-3">
              <ChevronRight className="w-8 h-8 text-gray-600" />
            </div>
          </div>

          {/* New Text */}
          <div>
            <div className="bg-green-50 border border-green-200 rounded-lg">
              <div className="px-4 py-3 border-b border-green-200">
                <h4 className="text-base font-semibold text-green-700">New Text</h4>
                <p className="text-sm text-green-600">{newText.length} characters</p>
              </div>
              <div className="p-4 max-h-[300px] overflow-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                  {newText || <span className="text-gray-400 italic">No new text</span>}
                </pre>
              </div>
            </div>
          </div>
        </div>
      );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-green-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading edit history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Info className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Go Back"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Document Edit History</h1>
                <p className="text-sm text-gray-500">
                  {document?.fileName || 'Document'} • 
                  {editHistory.length} edit{editHistory.length !== 1 ? 's' : ''} available
                </p>
              </div>
            </div>
            
            {editHistory.length > 0 && selectedEdit && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setViewMode(viewMode === 'side-by-side' ? 'inline' : 'side-by-side')}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50"
                  title="Toggle view mode"
                >
                  {viewMode === 'side-by-side' ? (
                    <>
                      <Minimize2 className="w-4 h-4" />
                      <span>Inline View</span>
                    </>
                  ) : (
                    <>
                      <Maximize2 className="w-4 h-4" />
                      <span>Side by Side</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Individual Edit History View */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {editHistory.length > 0 && selectedEdit ? (
            <>
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Edit History - Text Comparison</h3>
                    <p className="text-sm text-gray-500">
                      Edit made on <LocalDateTime timestamp={selectedEdit.timestamp || selectedEdit.edit_timestamp} />
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Showing edit {editHistory.findIndex(e => e === selectedEdit) + 1} of {editHistory.length}
                    </p>
                  </div>
                  <div className="flex items-center space-x-3">
                    {/* Navigation buttons for multiple edits */}
                    {editHistory.length > 1 && (
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => {
                            const currentIndex = editHistory.findIndex(e => e === selectedEdit);
                            if (currentIndex > 0) {
                              setSelectedEdit(editHistory[currentIndex - 1]);
                            }
                          }}
                          disabled={editHistory.findIndex(e => e === selectedEdit) === 0}
                          className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          ← Previous
                        </button>
                        <button
                          onClick={() => {
                            const currentIndex = editHistory.findIndex(e => e === selectedEdit);
                            if (currentIndex < editHistory.length - 1) {
                              setSelectedEdit(editHistory[currentIndex + 1]);
                            }
                          }}
                          disabled={editHistory.findIndex(e => e === selectedEdit) === editHistory.length - 1}
                          className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Next →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Edit Details */}
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {selectedEdit.edit_reason && (
                    <div className="p-3 bg-blue-50 rounded-md">
                      <span className="text-sm font-medium text-blue-700">Edit Reason:</span>
                      <p className="text-sm text-blue-600 mt-1">{selectedEdit.edit_reason}</p>
                    </div>
                  )}
                  
                  <div className="p-3 bg-green-50 rounded-md">
                    <span className="text-sm font-medium text-green-700">Text Change:</span>
                    <div className="mt-1">
                      {getTextChangeSummary(selectedEdit)}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="p-6">
                {renderTextComparison()}
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <Clock className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-lg font-medium">No Edit History Available</p>
              <p className="text-sm mt-1">This document has no edit history to display</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EditHistory;