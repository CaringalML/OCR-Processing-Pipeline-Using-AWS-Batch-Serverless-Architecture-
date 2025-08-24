import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  FileText, 
  Eye, 
  ZoomIn, 
  ZoomOut, 
  BookOpen,
  Hash,
  Tag,
  Globe,
  FileType,
  Info,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  MoreHorizontal
} from 'lucide-react';
import Zoom from 'react-medium-image-zoom';
import 'react-medium-image-zoom/dist/styles.css';
import documentService from '../../services/documentService';
import { LocalDateTime, LocalDateTimeFull } from '../common/LocalTime';

const DocumentReader = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pdfViewerError, setPdfViewerError] = useState(false);
  const [magnifyLevel, setMagnifyLevel] = useState(1);
  const [showMetadata, setShowMetadata] = useState(true);
  const [showEntities, setShowEntities] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [showFullText, setShowFullText] = useState(false);
  const [textCopied, setTextCopied] = useState(false);

  // Detect file type from filename or URL
  const getFileType = () => {
    const fileName = document?.fileName || document?.original_filename || document?.file_name || '';
    const url = document?.cloudFrontUrl || '';
    
    const extension = fileName.toLowerCase().split('.').pop();
    if (extension === 'pdf') return 'pdf';
    if (url.toLowerCase().includes('.pdf')) return 'pdf';
    
    return 'image';
  };

  // Load document data
  useEffect(() => {
    const loadDocument = async () => {
      try {
        setLoading(true);
        setError(null);
        setPdfViewerError(false);

        const docData = await documentService.getDocument(fileId, true);
        
        if (docData) {
          setDocument(docData);
        } else {
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
  }, [fileId]);



  // Get finalized text from document
  const getFinalizedText = () => {
    if (document?.finalizedResults?.finalizedText) {
      return document.finalizedResults.finalizedText;
    }
    if (document?.ocrResults?.refinedText) {
      return document.ocrResults.refinedText;
    }
    if (document?.ocrResults?.formattedText) {
      return document.ocrResults.formattedText;
    }
    if (document?.ocrResults?.extractedText) {
      return document.ocrResults.extractedText;
    }
    return '';
  };

  // Copy text to clipboard
  const copyTextToClipboard = async () => {
    const text = getFinalizedText();
    try {
      await navigator.clipboard.writeText(text);
      setTextCopied(true);
      setTimeout(() => setTextCopied(false), 2000); // Reset after 2 seconds
    } catch (error) {
      console.error('Failed to copy text:', error);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setTextCopied(true);
      setTimeout(() => setTextCopied(false), 2000);
    }
  };

  // Get preview text (first 300 characters)
  const getPreviewText = (text) => {
    if (text.length <= 300) return text;
    return text.substring(0, 300) + '...';
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 text-lg font-semibold mb-2">Error Loading Document</h2>
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 text-red-600 hover:text-red-700 underline"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const finalizedText = getFinalizedText();
  const fileType = getFileType();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="text-gray-600 hover:text-gray-900 flex items-center"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back
              </button>
              <div className="h-6 w-px bg-gray-300" />
              <h1 className="text-xl font-medium text-gray-900 flex items-center">
                <BookOpen className="w-5 h-5 mr-2 text-green-600" />
                {document?.fileName || document?.original_filename || 'Document Reader'}
              </h1>
            </div>
            
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Document Preview */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                    <FileType className="w-5 h-5 mr-2 text-green-600" />
                    Document Preview
                  </h2>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setMagnifyLevel(Math.max(0.5, magnifyLevel - 0.25))}
                      className="p-1 hover:bg-gray-100 rounded"
                      title="Zoom out"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-gray-600">{Math.round(magnifyLevel * 100)}%</span>
                    <button
                      onClick={() => setMagnifyLevel(Math.min(3, magnifyLevel + 0.25))}
                      className="p-1 hover:bg-gray-100 rounded"
                      title="Zoom in"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="p-4 bg-gray-50 max-h-[600px] overflow-auto">
                {document?.cloudFrontUrl ? (
                  fileType === 'pdf' ? (
                    <div className="bg-white rounded-lg p-4">
                      {!pdfViewerError ? (
                        <iframe
                          src={document.cloudFrontUrl}
                          className="w-full rounded-lg"
                          style={{ 
                            height: '600px',
                            transform: `scale(${magnifyLevel})`,
                            transformOrigin: 'top left',
                            width: `${100 / magnifyLevel}%`
                          }}
                          title="PDF Viewer"
                          onError={() => setPdfViewerError(true)}
                        />
                      ) : (
                        <div className="text-center py-12">
                          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                          <p className="text-gray-600">Unable to display PDF inline</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex justify-center">
                      <Zoom>
                        <img
                          src={document.cloudFrontUrl}
                          alt={document.fileName || 'Document'}
                          className="max-w-full h-auto rounded-lg shadow-lg"
                          style={{ 
                            transform: `scale(${magnifyLevel})`,
                            transformOrigin: 'center',
                            transition: 'transform 0.2s'
                          }}
                        />
                      </Zoom>
                    </div>
                  )
                ) : (
                  <div className="text-center py-12">
                    <Eye className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-600">No preview available</p>
                  </div>
                )}
              </div>
            </div>

            {/* OCR Text Content */}
            {finalizedText && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                      <FileText className="w-5 h-5 mr-2 text-green-600" />
                      Extracted Text
                    </h2>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={copyTextToClipboard}
                        className={`inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                          textCopied
                            ? 'text-green-700 bg-green-100 border border-green-300'
                            : 'text-gray-700 bg-gray-100 hover:bg-gray-200 border border-gray-300'
                        }`}
                        title="Copy text to clipboard"
                      >
                        {textCopied ? (
                          <>
                            <Check className="w-4 h-4 mr-1" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4 mr-1" />
                            Copy
                          </>
                        )}
                      </button>
                      {finalizedText.length > 300 && (
                        <button
                          onClick={() => setShowFullText(!showFullText)}
                          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors"
                        >
                          <MoreHorizontal className="w-4 h-4 mr-1" />
                          {showFullText ? 'Show Less' : 'Show More'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="p-6">
                  <div className="prose max-w-none text-gray-800 leading-relaxed">
                    {showFullText || finalizedText.length <= 300 
                      ? finalizedText 
                      : getPreviewText(finalizedText)
                    }
                  </div>
                  {!showFullText && finalizedText.length > 300 && (
                    <div className="mt-4 pt-4 border-t border-gray-200 text-center">
                      <button
                        onClick={() => setShowFullText(true)}
                        className="text-green-600 hover:text-green-700 text-sm font-medium"
                      >
                        Read full text ({finalizedText.length} characters) →
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Document Info */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <button
                  onClick={() => setShowMetadata(!showMetadata)}
                  className="w-full flex items-center justify-between text-left"
                >
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <Info className="w-5 h-5 mr-2 text-green-600" />
                    Document Information
                  </h3>
                  {showMetadata ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>
              
              {showMetadata && (
                <div className="p-4 space-y-3">
                  <div>
                    <span className="text-sm font-medium text-gray-500">File Name</span>
                    <p className="text-sm text-gray-900 mt-1">
                      {document?.fileName || document?.original_filename || 'Unknown'}
                    </p>
                  </div>
                  
                  {(document?.metadata?.date || document?.publication_date || document?.date || document?.publication_year) && (
                    <div>
                      <span className="text-sm font-medium text-gray-500">Publication Date</span>
                      <p className="text-sm text-gray-900 mt-1">
                        {document?.metadata?.date || document?.publication_date || document?.date || document?.publication_year}
                      </p>
                    </div>
                  )}

                  <div>
                    <span className="text-sm font-medium text-gray-500">File Size</span>
                    <p className="text-sm text-gray-900 mt-1">
                      {document?.fileSize || document?.file_size || 'Unknown'}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Entities */}
            {(document?.ocrResults?.entityAnalysis?.entities || document?.finalizedResults?.entityAnalysis?.entities) && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                  <button
                    onClick={() => setShowEntities(!showEntities)}
                    className="w-full flex items-center justify-between text-left"
                  >
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                      <Hash className="w-5 h-5 mr-2 text-green-600" />
                      Detected Entities
                    </h3>
                    {showEntities ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                </div>
                
                {showEntities && (
                  <div className="p-4">
                    <div className="flex flex-wrap gap-2">
                      {(document.finalizedResults?.entityAnalysis?.entities || 
                        document.ocrResults?.entityAnalysis?.entities || []).map((entity, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-50 text-green-700 border border-green-200"
                        >
                          <Tag className="w-3 h-3 mr-1" />
                          {entity}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Text Analysis */}
            {(document?.finalizedResults?.textAnalysis || document?.textAnalysis) && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                  <button
                    onClick={() => setShowAnalysis(!showAnalysis)}
                    className="w-full flex items-center justify-between text-left"
                  >
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                      <Globe className="w-5 h-5 mr-2 text-green-600" />
                      Text Analysis
                    </h3>
                    {showAnalysis ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                </div>
                
                {showAnalysis && (
                  <div className="p-4 space-y-3">
                    {document?.finalizedResults?.languageDetection?.detected_language && (
                      <div>
                        <span className="text-sm font-medium text-gray-500">Language</span>
                        <p className="text-sm text-gray-900 mt-1">
                          {document.finalizedResults.languageDetection.detected_language}
                          {document.finalizedResults.languageDetection.confidence && (
                            <span className="text-gray-500 ml-1">
                              ({Math.round(document.finalizedResults.languageDetection.confidence * 100)}% confidence)
                            </span>
                          )}
                        </p>
                      </div>
                    )}
                    
                    {(document?.finalizedResults?.textAnalysis?.qualityAssessment?.confidence_score || 
                      document?.textAnalysis?.qualityAssessment?.confidence_score) && (
                      <div>
                        <span className="text-sm font-medium text-gray-500">OCR Quality</span>
                        <div className="mt-1">
                          <div className="flex items-center">
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-green-600 h-2 rounded-full"
                                style={{ 
                                  width: `${document?.finalizedResults?.textAnalysis?.qualityAssessment?.confidence_score || 
                                          document?.textAnalysis?.qualityAssessment?.confidence_score}%` 
                                }}
                              />
                            </div>
                            <span className="ml-2 text-sm text-gray-600">
                              {document?.finalizedResults?.textAnalysis?.qualityAssessment?.confidence_score || 
                               document?.textAnalysis?.qualityAssessment?.confidence_score}%
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {(document?.finalizedResults?.textAnalysis?.refined_total_word_count || 
                      document?.textAnalysis?.refined_total_word_count) && (
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-sm font-medium text-gray-500">Words</span>
                          <p className="text-sm text-gray-900 mt-1">
                            {document?.finalizedResults?.textAnalysis?.refined_total_word_count || 
                             document?.textAnalysis?.refined_total_word_count}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-500">Characters</span>
                          <p className="text-sm text-gray-900 mt-1">
                            {document?.finalizedResults?.textAnalysis?.refined_total_character_count || 
                             document?.textAnalysis?.refined_total_character_count}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentReader;