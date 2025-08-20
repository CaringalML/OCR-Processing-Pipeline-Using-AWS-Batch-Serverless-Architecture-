import React, { useState, useRef, useEffect } from 'react';
import { Upload as UploadIcon, FileText, Search, X, CheckCircle, AlertCircle, Edit, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import uploadService from '../../services/uploadService';
import { useDocuments } from '../../hooks/useDocuments';
import documentService from '../../services/documentService';

const Upload = () => {
  const navigate = useNavigate();
  const [showMetadataForm, setShowMetadataForm] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [allProcessedDocuments, setAllProcessedDocuments] = useState([]);
  const [loadingProcessed, setLoadingProcessed] = useState(false);
  const fileInputRef = useRef(null);
  const { documents, fetchDocuments } = useDocuments();
  const [metadata, setMetadata] = useState({
    title: "",
    author: "",
    publication: "",
    date: "",
    page: "",
    tags: "",
    description: "",
    subject: "",
    language: "English",
    type: "Document",
    rights: "",
    collection: ""
  });

  // Fetch all processed documents from /batch/processed
  useEffect(() => {
    const fetchAllProcessed = async () => {
      try {
        setLoadingProcessed(true);
        console.log('Fetching all processed documents...');
        const data = await documentService.getAllProcessedDocuments();
        console.log('Received data:', data);
        
        // Handle different response structures
        if (data) {
          if (Array.isArray(data)) {
            setAllProcessedDocuments(data);
          } else if (data.files && Array.isArray(data.files)) {
            setAllProcessedDocuments(data.files);
          } else if (data.items && Array.isArray(data.items)) {
            setAllProcessedDocuments(data.items);
          } else if (data.documents && Array.isArray(data.documents)) {
            setAllProcessedDocuments(data.documents);
          } else {
            console.warn('Unexpected data structure:', data);
            setAllProcessedDocuments([]);
          }
        } else {
          setAllProcessedDocuments([]);
        }
      } catch (error) {
        console.error('Error fetching processed documents:', error);
        setUploadError(`Failed to load processed documents: ${error.message}`);
      } finally {
        setLoadingProcessed(false);
      }
    };

    fetchAllProcessed();
    // Refresh every 30 seconds
    const interval = setInterval(fetchAllProcessed, 30000);
    return () => clearInterval(interval);
  }, []);

  // Combine upload queue and processed documents, avoiding duplicates
  const getAllDocuments = () => {
    // Get all fileIds from processed documents API
    const processedFileIds = allProcessedDocuments.map(doc => doc.fileId);
    
    // Filter upload queue to exclude completed items that are already in processed documents
    // Keep only pending, uploading, and failed items from upload queue
    const activeUploadQueue = uploadQueue.filter(f => 
      f.status !== 'completed' || !processedFileIds.includes(f.fileId)
    );
    
    // Map processed documents to display format
    const processedDocs = allProcessedDocuments.map(doc => ({
      id: doc.fileId,
      fileId: doc.fileId,
      name: doc.fileName || doc.file_name || doc.original_filename || 'Unknown file',
      size: doc.fileSize || doc.file_size || 'Unknown size',
      status: doc.processingStatus || doc.processing_status || "pending",
      processingType: doc.processingType || 'unknown',
      pages: doc.metadata?.page || doc.ocrResults?.pages || doc.pages || 'N/A',
      extractedText: doc.ocrResults?.refinedText || doc.ocrResults?.extractedText || doc.extractedText || 'No text extracted yet',
      formattedText: doc.ocrResults?.formattedText || doc.formattedText || '',
      refinedText: doc.ocrResults?.refinedText || doc.refinedText || '',
      cloudFrontUrl: doc.cloudFrontUrl,
      uploadDate: doc.uploadTimestamp || doc.upload_timestamp,
      processedAt: doc.ocrResults?.processedAt || null,
      processingDuration: doc.ocrResults?.processingDuration || null,
      languageDetection: doc.ocrResults?.languageDetection || null,
      ocrResults: doc.ocrResults,
      metadata: doc.metadata,
      finalized: doc.finalized || false,
      finalizedText: doc.finalizedText || null,
      qualityScore: doc.textAnalysis?.qualityAssessment?.confidence_score || null,
      isFromProcessed: true
    }));
    
    return [...activeUploadQueue, ...processedDocs];
  };
  
  const allDocuments = getAllDocuments();

  // Handle file selection
  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    handleFiles(files);
  };

  // Handle file drop
  const handleDrop = (event) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer.files);
    handleFiles(files);
  };

  // Process selected files
  const handleFiles = (files) => {
    const validFiles = files.filter(file => {
      // Validate file type
      if (!uploadService.validateFileType(file)) {
        setUploadError(`Invalid file type: ${file.name}. Supported: PDF, TIFF, JPG, PNG`);
        return false;
      }
      // Validate file size (500MB limit)
      if (!uploadService.validateFileSize(file, 500)) {
        setUploadError(`File too large: ${file.name}. Maximum size is 500MB`);
        return false;
      }
      return true;
    });

    if (validFiles.length > 0) {
      setUploadError(null);
      // Add files to upload queue
      const newFiles = validFiles.map(file => ({
        id: Date.now() + Math.random(),
        file,
        name: file.name,
        size: uploadService.formatFileSize(file.size),
        status: 'pending',
        progress: 0,
        metadata: { ...metadata }
      }));
      setUploadQueue(prev => [...prev, ...newFiles]);
      // Automatically show metadata form when files are added
      setShowMetadataForm(true);
    }
  };

  // Upload files in queue
  const uploadFiles = async () => {
    setUploading(true);
    setUploadError(null);

    for (let item of uploadQueue.filter(f => f.status === 'pending')) {
      try {
        // Update status to uploading
        setUploadQueue(prev => prev.map(f => 
          f.id === item.id ? { ...f, status: 'uploading' } : f
        ));

        // Upload the file with metadata
        const result = await uploadService.uploadDocument(item.file, item.metadata);
        
        // Update status to completed
        setUploadQueue(prev => prev.map(f => 
          f.id === item.id ? { 
            ...f, 
            status: 'completed',
            fileId: result.files?.[0]?.file_id,
            routing: result.files?.[0]?.routing,
            progress: 100 
          } : f
        ));

        // Refresh documents list to show newly uploaded files
        await fetchDocuments();
      } catch (error) {
        console.error('Upload failed:', error);
        // Update status to failed
        setUploadQueue(prev => prev.map(f => 
          f.id === item.id ? { ...f, status: 'failed', error: error.message } : f
        ));
      }
    }

    setUploading(false);
  };

  // Remove file from queue
  const removeFromQueue = (id) => {
    setUploadQueue(prev => prev.filter(f => f.id !== id));
  };

  // Clear completed uploads
  const clearCompleted = () => {
    setUploadQueue(prev => prev.filter(f => f.status !== 'completed'));
  };

  // Clear all pending files from queue
  const clearAllPending = () => {
    setUploadQueue(prev => prev.filter(f => f.status !== 'pending'));
  };

  // Get progress percentage based on processing status
  const getProgressPercentage = (status) => {
    const statusProgress = {
      'pending': 0,
      'uploading': 10,
      'uploaded': 20,
      'queued': 30,
      'processing': 50,
      'downloading': 40,
      'processing_ocr': 60,
      'assessing_quality': 70,
      'refining_text': 80,
      'saving_results': 90,
      'processed': 100,
      'completed': 100,
      'failed': 0,
      'finalized': 100
    };
    return statusProgress[status] || 0;
  };

  // Get status display text
  const getStatusDisplay = (status) => {
    const statusDisplay = {
      'pending': 'Pending',
      'uploading': 'Uploading...',
      'uploaded': 'Uploaded',
      'queued': 'In Queue',
      'processing': 'Processing',
      'downloading': 'Downloading',
      'processing_ocr': 'OCR Processing',
      'assessing_quality': 'Quality Check',
      'refining_text': 'Refining Text',
      'saving_results': 'Saving',
      'processed': 'Processed',
      'completed': 'Completed',
      'failed': 'Failed',
      'finalized': 'Finalized'
    };
    return statusDisplay[status] || status;
  };

  // Refresh processed documents
  const refreshDocuments = async () => {
    try {
      setLoadingProcessed(true);
      console.log('Manually refreshing processed documents...');
      const data = await documentService.getAllProcessedDocuments();
      console.log('Received data:', data);
      
      // Handle different response structures
      if (data) {
        if (Array.isArray(data)) {
          setAllProcessedDocuments(data);
        } else if (data.files && Array.isArray(data.files)) {
          setAllProcessedDocuments(data.files);
        } else if (data.items && Array.isArray(data.items)) {
          setAllProcessedDocuments(data.items);
        } else if (data.documents && Array.isArray(data.documents)) {
          setAllProcessedDocuments(data.documents);
        } else {
          console.warn('Unexpected data structure:', data);
          setAllProcessedDocuments([]);
        }
      } else {
        setAllProcessedDocuments([]);
      }
    } catch (error) {
      console.error('Error refreshing documents:', error);
      setUploadError(`Failed to refresh documents: ${error.message}`);
    } finally {
      setLoadingProcessed(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
      </div>

      {/* Upload Area */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-8">
          <div 
            className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-green-400 hover:bg-green-50 transition-colors cursor-pointer"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.tiff,.tif,.jpg,.jpeg,.png"
              onChange={handleFileSelect}
              className="hidden"
            />
            <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Drag and drop your files here</h3>
            <p className="text-gray-500 mb-4">or click to browse and select files</p>
            <div className="flex justify-center space-x-4">
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                Choose Files
              </button>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMetadataForm(!showMetadataForm);
                }}
                className="border border-green-600 text-green-600 px-6 py-2 rounded-lg hover:bg-green-50 transition-colors"
              >
                {showMetadataForm ? 'Hide' : uploadQueue.filter(f => f.status === 'pending').length > 0 ? 'Edit' : 'Add'} Metadata
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-4">Supported formats: PDF, TIFF, JPG, PNG • Maximum file size: 500MB</p>
          </div>

          {/* Upload Action Bar - Always visible when there are pending files */}
          {uploadQueue.filter(f => f.status === 'pending').length > 0 && !showMetadataForm && (
            <div className="mt-6 flex justify-end">
              <div className="flex space-x-3">
                <button 
                  onClick={clearAllPending}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={uploadFiles}
                  disabled={uploading}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {uploading ? 'Uploading...' : `Upload ${uploadQueue.filter(f => f.status === 'pending').length} File${uploadQueue.filter(f => f.status === 'pending').length > 1 ? 's' : ''}`}
                </button>
              </div>
            </div>
          )}

          {/* Metadata Form */}
          {showMetadataForm && (
            <div className="mt-8 p-6 bg-gray-50 rounded-lg border border-gray-200">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">
                Document Metadata {uploadQueue.filter(f => f.status === 'pending').length > 0 && `(${uploadQueue.filter(f => f.status === 'pending').length} files ready)`}
              </h4>
              <p className="text-sm text-gray-600 mb-6">Add metadata to improve searchability and organization of your documents. This metadata will be applied to all files in the queue.</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Title</label>
                  <input
                    type="text"
                    value={metadata.title}
                    onChange={(e) => setMetadata({...metadata, title: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Document title or headline"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Author/Creator</label>
                  <input
                    type="text"
                    value={metadata.author}
                    onChange={(e) => setMetadata({...metadata, author: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Author, photographer, or creator"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Publication</label>
                  <input
                    type="text"
                    value={metadata.publication}
                    onChange={(e) => setMetadata({...metadata, publication: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Newspaper, journal, or publication name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                  <input
                    type="text"
                    value={metadata.date}
                    onChange={(e) => setMetadata({...metadata, date: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="YYYY-MM-DD or just YYYY"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Page Number</label>
                  <input
                    type="text"
                    value={metadata.page}
                    onChange={(e) => setMetadata({...metadata, page: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Page number or range (e.g., 1, 5-10)"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Tags</label>
                  <input
                    type="text"
                    value={metadata.tags}
                    onChange={(e) => setMetadata({...metadata, tags: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Comma-separated tags (e.g., historical, important, archived)"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Collection</label>
                  <select
                    value={metadata.collection}
                    onChange={(e) => setMetadata({...metadata, collection: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="">Select a collection</option>
                    <option value="historical-newspapers">Historical Newspapers</option>
                    <option value="university-records">University Records</option>
                    <option value="manuscripts">Manuscripts</option>
                    <option value="photographs">Photographs</option>
                    <option value="government-documents">Government Documents</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Document Type</label>
                  <select
                    value={metadata.type}
                    onChange={(e) => setMetadata({...metadata, type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="Document">Document</option>
                    <option value="Newspaper">Newspaper</option>
                    <option value="Letter">Letter</option>
                    <option value="Photograph">Photograph</option>
                    <option value="Manuscript">Manuscript</option>
                    <option value="Report">Report</option>
                    <option value="Map">Map</option>
                  </select>
                </div>
              </div>
              
              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={metadata.description}
                  onChange={(e) => setMetadata({...metadata, description: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Brief description of the document content and significance"
                />
              </div>
              
              <div className="flex justify-between mt-6">
                <div className="space-x-2">
                  <button 
                    onClick={() => {
                      setMetadata({
                        title: "", author: "", publication: "", date: "", page: "", tags: "", description: "",
                        subject: "", language: "English", type: "Document", rights: "", collection: ""
                      });
                    }}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Clear Metadata
                  </button>
                  <button 
                    onClick={clearAllPending}
                    className="px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    Clear Files
                  </button>
                </div>
                <button 
                  onClick={uploadFiles}
                  disabled={uploading || uploadQueue.filter(f => f.status === 'pending').length === 0}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {uploading ? 'Uploading...' : `Upload Files (${uploadQueue.filter(f => f.status === 'pending').length})`}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {uploadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center justify-between">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            <span>{uploadError}</span>
          </div>
          <button onClick={() => setUploadError(null)}>
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Upload Queue */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-semibold text-gray-900">Upload Queue ({allDocuments.length} files)</h2>
            <button 
              onClick={refreshDocuments}
              disabled={loadingProcessed}
              className={`
                relative p-2 rounded-full border border-gray-300 bg-white
                hover:bg-gray-50 hover:border-gray-400 
                focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500
                transition-all duration-200
                ${loadingProcessed ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
              `}
              title="Refresh documents"
              aria-label="Refresh"
            >
              <RefreshCw 
                className={`
                  w-4 h-4 text-gray-600 
                  ${loadingProcessed ? 'animate-spin' : 'hover:text-gray-800'}
                `} 
                strokeWidth={2}
              />
            </button>
          </div>
          <div className="space-x-2">
            {uploadQueue.some(f => f.status === 'completed') && (
              <button 
                onClick={clearCompleted}
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Clear Completed
              </button>
            )}
          </div>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {/* Unified Document List */}
            {allDocuments.map((item) => {
              const progress = getProgressPercentage(item.status);
              const isUploaded = item.status === 'uploaded';
              const isProcessing = ['uploading', 'queued', 'processing', 'downloading', 
                                   'processing_ocr', 'assessing_quality', 'refining_text', 'saving_results'].includes(item.status);
              const isCompleted = ['completed', 'processed', 'finalized'].includes(item.status);
              const isFailed = item.status === 'failed';
              
              return (
                <div 
                  key={item.id}
                  className={`relative overflow-hidden rounded-lg border transition-all ${
                    item.status === 'pending' ? 'bg-gray-50 border-gray-200' :
                    isUploaded ? 'bg-indigo-50 border-indigo-200' :
                    isProcessing ? 'bg-blue-50 border-blue-200' :
                    isCompleted ? (item.finalized ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200') :
                    isFailed ? 'bg-red-50 border-red-200' :
                    'bg-gray-50 border-gray-200'
                  } ${item.isFromProcessed ? 'cursor-pointer hover:shadow-md' : ''}`}
                  onClick={() => item.isFromProcessed && navigate(`/edit/${item.fileId}`)}
                >
                  {/* Progress Bar */}
                  {(isProcessing || isUploaded) && (
                    <div className="absolute top-0 left-0 w-full h-1 bg-gray-200">
                      <div 
                        className="h-full bg-blue-500 transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  )}
                  
                  <div className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <div className="flex flex-col items-center">
                          <FileText className={`w-8 h-8 ${
                            item.status === 'pending' ? 'text-gray-600' :
                            isUploaded ? 'text-indigo-600' :
                            isProcessing ? 'text-blue-600' :
                            isCompleted ? (item.finalized ? 'text-green-600' : 'text-yellow-600') :
                            isFailed ? 'text-red-600' :
                            'text-gray-600'
                          }`} />
                          {item.qualityScore && (
                            <span className={`text-xs mt-1 font-semibold ${
                              item.qualityScore >= 80 ? 'text-green-600' :
                              item.qualityScore >= 60 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {item.qualityScore}%
                            </span>
                          )}
                        </div>
                        
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <p className="font-medium text-gray-900">{item.name}</p>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              item.status === 'pending' ? 'bg-gray-100 text-gray-800' :
                              isUploaded ? 'bg-indigo-100 text-indigo-800' :
                              isProcessing ? 'bg-blue-100 text-blue-800' :
                              isCompleted ? 'bg-green-100 text-green-800' :
                              isFailed ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {getStatusDisplay(item.status)}
                            </span>
                            {item.processingType && item.processingType !== 'unknown' && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                {item.processingType}
                              </span>
                            )}
                            {item.finalized && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                ✓ Finalized
                              </span>
                            )}
                          </div>
                          
                          <div className="text-sm text-gray-600 mt-1">
                            <span className="inline-flex items-center space-x-3">
                              <span>📄 {item.size}</span>
                              {item.pages !== 'N/A' && <span>📃 Page {item.pages}</span>}
                              {item.languageDetection && (
                                <span>🌐 {item.languageDetection.detected_language} ({Math.round(item.languageDetection.confidence * 100)}%)</span>
                              )}
                            </span>
                          </div>
                          
                          {item.processingDuration && (
                            <p className="text-xs text-gray-500 mt-1">
                              ⏱️ Processed in {item.processingDuration}
                              {item.processedAt && ` at ${new Date(item.processedAt).toLocaleTimeString()}`}
                            </p>
                          )}
                          
                          {/* Progress text for processing items */}
                          {(isProcessing || isUploaded) && (
                            <p className={`text-xs mt-1 font-medium ${isUploaded ? 'text-indigo-600' : 'text-blue-600'}`}>
                              {progress}% - {getStatusDisplay(item.status)}
                            </p>
                          )}
                          
                          {/* Error message for failed items */}
                          {isFailed && item.error && (
                            <p className="text-xs text-red-600 mt-1">
                              Error: {item.error}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {isCompleted && (
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        )}
                        {isFailed && (
                          <AlertCircle className="w-5 h-5 text-red-600" />
                        )}
                        {item.isFromProcessed && (
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/edit/${item.fileId}`);
                            }}
                            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-white/50 rounded-lg transition-colors"
                            title="Edit Document"
                          >
                            <Edit className="w-5 h-5" />
                          </button>
                        )}
                        {!item.isFromProcessed && (
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFromQueue(item.id);
                            }}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
            
            {/* Loading indicator */}
            {loadingProcessed && allDocuments.length === 0 && (
              <div className="p-4 text-center text-gray-500">
                <div className="spinner mx-auto mb-2"></div>
                <p className="text-sm">Loading processed documents...</p>
              </div>
            )}
            
            {/* No documents message */}
            {!loadingProcessed && allDocuments.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-600 font-medium">No documents in queue</p>
                <p className="text-sm text-gray-400 mt-1">Upload documents above or check the API connection</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;