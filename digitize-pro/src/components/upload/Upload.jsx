import React, { useState, useRef, useEffect } from 'react';
import { Upload as UploadIcon, FileText, Search, X, CheckCircle, AlertCircle, Edit, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import uploadService from '../../services/uploadService';
import { useDocuments } from '../../hooks/useDocuments';
import documentService from '../../services/documentService';
import LocalTime, { LocalTimeOnly, LocalDateTime, LocalTimeRelative } from '../common/LocalTime';

const Upload = () => {
  const navigate = useNavigate();
  const [showMetadataForm, setShowMetadataForm] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [allProcessedDocuments, setAllProcessedDocuments] = useState([]);
  const [loadingProcessed, setLoadingProcessed] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [detailedStatusCache, setDetailedStatusCache] = useState({});
  const fileInputRef = useRef(null);
  const { documents, fetchDocuments } = useDocuments();

  // Fetch detailed status for individual processing files
  // Note: Only long-batch files get detailed "In progress X%" statuses
  // Short-batch files just show generic "processing" status
  const fetchDetailedStatus = async (fileId) => {
    try {
      console.log(`Fetching detailed status for ${fileId}...`);
      const detailedData = await documentService.getDocument(fileId);
      console.log(`Detailed status response for ${fileId}:`, detailedData);
      
      if (detailedData && detailedData.processingStatus) {
        console.log(`Setting detailed status cache for ${fileId}:`, detailedData.processingStatus);
        setDetailedStatusCache(prev => ({
          ...prev,
          [fileId]: {
            status: detailedData.processingStatus,
            timestamp: Date.now()
          }
        }));
        return detailedData.processingStatus;
      }
    } catch (error) {
      console.error(`Failed to fetch detailed status for ${fileId}:`, error);
    }
    return null;
  };

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
        // Fetch documents with all statuses to include in-progress files
        const data = await documentService.getAllProcessedDocuments({ status: 'all' });
        console.log('Received data:', data);
        console.log('Processing status breakdown:', data && Array.isArray(data) ? 
          data.map(doc => ({fileId: doc.fileId, fileName: doc.fileName || doc.file_name, status: doc.processingStatus || doc.processing_status})) :
          data && data.files ? data.files.map(doc => ({fileId: doc.fileId, fileName: doc.fileName || doc.file_name, status: doc.processingStatus || doc.processing_status})) : 
          'No valid data structure'
        );
        
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

  // Fetch detailed status for processing files (only long-batch files get detailed progress)
  useEffect(() => {
    const fetchDetailedStatusForProcessingFiles = async () => {
      const processingFiles = allProcessedDocuments.filter(doc => 
        ((doc.processingStatus === 'processing' || doc.processing_status === 'processing') ||
         (doc.processingStatus === 'uploaded' || doc.processing_status === 'uploaded')) &&
        (doc.processingType === 'long-batch' || doc.processing_type === 'long-batch')
      );
      
      console.log('Processing files found for detailed status fetch:', processingFiles.map(doc => ({
        fileId: doc.fileId,
        fileName: doc.fileName || doc.file_name,
        status: doc.processingStatus || doc.processing_status,
        type: doc.processingType || doc.processing_type
      })));

      // Fetch detailed status for files that don't have recent cached status
      const now = Date.now();
      const cacheTimeout = 10000; // 10 seconds cache timeout

      for (const doc of processingFiles) {
        const fileId = doc.fileId;
        const cached = detailedStatusCache[fileId];
        
        // Fetch if not cached or cache is older than timeout
        if (!cached || (now - cached.timestamp) > cacheTimeout) {
          await fetchDetailedStatus(fileId);
        }
      }
    };

    if (allProcessedDocuments.length > 0) {
      fetchDetailedStatusForProcessingFiles();
    }
  }, [allProcessedDocuments, detailedStatusCache]);

  // Set up more frequent polling for long-batch files with detailed status
  useEffect(() => {
    const interval = setInterval(async () => {
      const filesWithDetailedStatus = Object.keys(detailedStatusCache).filter(fileId => {
        const cached = detailedStatusCache[fileId];
        // Only poll if it's showing "In progress" (which indicates long-batch processing)
        return cached && cached.status.includes('In progress');
      });

      if (filesWithDetailedStatus.length > 0) {
        console.log('Polling detailed status for', filesWithDetailedStatus.length, 'processing files');
        for (const fileId of filesWithDetailedStatus) {
          await fetchDetailedStatus(fileId);
        }
      }
    }, 5000); // Poll every 5 seconds for processing files

    return () => clearInterval(interval);
  }, [detailedStatusCache]);

  // Combine upload queue and processed documents, avoiding duplicates
  const getAllDocuments = () => {
    // Get all fileIds from processed documents API
    const processedFileIds = allProcessedDocuments.map(doc => doc.fileId);
    
    // Filter upload queue to exclude items that are already in processed documents
    // Keep only pending, uploading, and failed items from upload queue
    // Remove uploaded/completed items that already exist in backend API
    const activeUploadQueue = uploadQueue.filter(f => {
      // Always keep pending, uploading, and failed items (not yet in backend)
      if (['pending', 'uploading', 'failed'].includes(f.status)) {
        return true;
      }
      
      // For uploaded/completed items, only keep if not already in backend
      if (['uploaded', 'completed'].includes(f.status)) {
        return !processedFileIds.includes(f.fileId);
      }
      
      // Keep any other status for safety
      return true;
    });
    
    // Map processed documents to display format
    const processedDocs = allProcessedDocuments.map(doc => {
      const fileId = doc.fileId;
      const baseStatus = doc.processingStatus || doc.processing_status || "pending";
      
      // Use detailed status from cache if available for processing files
      const cachedStatus = detailedStatusCache[fileId];
      const finalStatus = ((baseStatus === 'processing' || baseStatus === 'uploaded') && cachedStatus) 
        ? cachedStatus.status 
        : baseStatus;

      return {
        id: doc.fileId,
        fileId: doc.fileId,
        name: doc.fileName || doc.file_name || doc.original_filename || 'Unknown file',
        size: doc.fileSize || doc.file_size || 'Unknown size',
        status: finalStatus,
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
      };
    });
    
    const combinedDocs = [...activeUploadQueue, ...processedDocs];
    
    // Sort by upload date/timestamp in descending order (latest first)
    return combinedDocs.sort((a, b) => {
      const aDate = new Date(a.uploadDate || a.uploadedAt || a.timestamp || 0);
      const bDate = new Date(b.uploadDate || b.uploadedAt || b.timestamp || 0);
      return bDate.getTime() - aDate.getTime();
    });
  };
  
  const allDocuments = getAllDocuments();
  
  // Calculate status counts for header display
  const getStatusCounts = () => {
    const counts = {
      attached: 0,      // pending files (selected but not uploaded)
      queued: 0,        // uploaded/processing files
      completed: 0,     // processed/completed files
      failed: 0         // failed files
    };
    
    allDocuments.forEach(item => {
      if (item.status === 'pending') {
        counts.attached++;
      } else if (['uploaded', 'processing', 'uploading'].includes(item.status) || 
                 (typeof item.status === 'string' && (
                   item.status.includes('In progress') || 
                   item.status.includes('Queued') ||
                   item.status.includes('Starting') ||
                   item.status.includes('Preparing') ||
                   item.status.includes('Pending - Waiting')
                 ))) {
        counts.queued++;
      } else if (['completed', 'processed', 'finalized'].includes(item.status)) {
        counts.completed++;
      } else if (item.status === 'failed') {
        counts.failed++;
      }
    });
    
    return counts;
  };
  
  const statusCounts = getStatusCounts();

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
      const newFiles = validFiles.map((file, index) => ({
        id: Date.now() + Math.random() + index, // Ensure unique IDs with slight time offset
        file,
        name: file.name,
        size: uploadService.formatFileSize(file.size),
        status: 'pending',
        progress: 0,
        metadata: { ...metadata },
        timestamp: Date.now() + index // Add timestamp for sorting, with slight offset for multiple files
      }));
      setUploadQueue(prev => [...newFiles, ...prev]); // New files at the beginning
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

        // Upload the file with current metadata state (not cached metadata from queue)
        console.log('Current metadata state:', metadata);
        const result = await uploadService.uploadDocument(item.file, metadata);
        
        // Update status to uploaded (matches backend processing_status)
        setUploadQueue(prev => prev.map(f => 
          f.id === item.id ? { 
            ...f, 
            status: 'uploaded',
            fileId: result.files?.[0]?.file_id,
            routing: result.files?.[0]?.routing,
            progress: 30,  // 30% for uploaded/queued state
            uploadedAt: Date.now()  // Track when uploaded for faster polling
          } : f
        ));

        // Refresh documents list to show newly uploaded files
        await fetchDocuments();
        
        // For short-batch files, start frequent polling for faster updates
        if (result.files?.[0]?.routing?.decision === 'short-batch') {
          // Poll every 3 seconds for the first 2 minutes after upload
          const fileId = result.files?.[0]?.file_id;
          let pollCount = 0;
          const maxPolls = 40; // 40 * 3 seconds = 2 minutes
          
          const fastPoll = setInterval(async () => {
            pollCount++;
            await fetchDocuments();
            
            // Stop fast polling after 2 minutes or if file is completed
            const currentFile = allProcessedDocuments.find(doc => doc.fileId === fileId);
            if (pollCount >= maxPolls || 
                (currentFile && ['completed', 'processed', 'failed'].includes(currentFile.processingStatus))) {
              clearInterval(fastPoll);
            }
          }, 3000);
        }
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
    // Handle "In progress X%" statuses from long-batch processing (supports decimal percentages)
    if (typeof status === 'string' && status.includes('In progress') && status.includes('%')) {
      const match = status.match(/In progress (\d+(?:\.\d+)?)%/);
      if (match) {
        return Math.round(parseFloat(match[1]));
      }
    }
    
    // Handle other detailed statuses from backend
    if (typeof status === 'string') {
      // Map detailed backend statuses to progress percentages
      if (status.includes('Queued for processing')) return 25;
      if (status.includes('Pending - Waiting for resources')) return 20;
      if (status.includes('Preparing...')) return 30;
      if (status.includes('Starting...')) return 35;
      if (status.includes('Processing initiated')) return 40;
      if (status.includes('Batch job submitted')) return 35;
    }
    
    // Based on actual backend statuses:
    // - uploaded: File uploaded, waiting to be processed
    // - processing: Currently being processed (generic status during processing)
    // - completed: Short-batch processing finished
    // - processed: Long-batch processing finished
    // - failed: Processing failed
    // - finalized: Document has been finalized by user
    const statusProgress = {
      'pending': 0,        // Local state before upload
      'uploading': 15,     // Local state during upload
      'uploaded': 30,      // File uploaded to S3, waiting in queue
      'processing': 60,    // Actively being processed (fallback for generic processing)
      'processed': 100,    // Long-batch completed
      'completed': 100,    // Short-batch completed
      'failed': 0,         // Processing failed
      'finalized': 100     // User finalized the document
    };
    return statusProgress[status] || 0;
  };

  // Get status display text
  const getStatusDisplay = (status) => {
    // Handle detailed "In progress" statuses from long-batch processing
    if (typeof status === 'string' && status.includes('In progress')) {
      // Return the full detailed status (e.g., "In progress 67% - Refining text")
      return status;
    }
    
    const statusDisplay = {
      'pending': 'Pending Upload',
      'uploading': 'Uploading...',
      'uploaded': 'In Queue',
      'processing': 'Processing...',
      'processed': 'Processed',     // Long-batch result
      'completed': 'Completed',      // Short-batch result
      'failed': 'Failed',
      'finalized': 'Finalized'
    };
    return statusDisplay[status] || status;
  };

  // Refresh processed documents with immediate feedback
  const refreshDocuments = async () => {
    try {
      setLoadingProcessed(true);
      console.log('Manually refreshing processed documents...');
      
      // Clear detailed status cache to force fresh fetches
      setDetailedStatusCache({});
      
      // Also trigger the useDocuments hook refresh for real-time updates
      await fetchDocuments();
      
      const data = await documentService.getAllProcessedDocuments({ status: 'all' });
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
      
      // Also refresh detailed status for long-batch processing files (including uploaded and processing)
      const processingFiles = data?.files?.filter(doc => 
        ((doc.processingStatus === 'processing' || doc.processing_status === 'processing') ||
         (doc.processingStatus === 'uploaded' || doc.processing_status === 'uploaded')) &&
        (doc.processingType === 'long-batch' || doc.processing_type === 'long-batch')
      ) || [];
      
      if (processingFiles.length > 0) {
        console.log('Refreshing detailed status for processing files...');
        for (const doc of processingFiles) {
          if (doc.fileId) {
            await fetchDetailedStatus(doc.fileId);
          }
        }
      }

      // Show brief success feedback
      console.log('✓ Documents refreshed successfully');
      setLastRefreshed(Date.now());
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
            <h2 className="text-lg font-semibold text-gray-900">Document Processing Hub</h2>
            <div className="flex items-center space-x-3 text-sm">
              {statusCounts.attached > 0 && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  📎 {statusCounts.attached} Attached
                </span>
              )}
              {statusCounts.queued > 0 && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                  ⏳ {statusCounts.queued} Queued/Processing
                </span>
              )}
              {statusCounts.completed > 0 && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  ✅ {statusCounts.completed} Completed
                </span>
              )}
              {statusCounts.failed > 0 && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  ❌ {statusCounts.failed} Failed
                </span>
              )}
              {allDocuments.length === 0 && (
                <span className="text-xs text-gray-500">No files</span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <button 
                onClick={refreshDocuments}
                disabled={loadingProcessed}
                className={`
                  relative p-2 rounded-full border transition-all duration-200
                  ${loadingProcessed 
                    ? 'border-blue-400 bg-blue-50 cursor-not-allowed' 
                    : 'border-gray-300 bg-white hover:bg-gray-50 hover:border-gray-400 cursor-pointer'
                  }
                  focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500
                `}
                title={lastRefreshed ? `Last refreshed: ${new Date(lastRefreshed).toLocaleString()}` : "Refresh documents"}
                aria-label="Refresh"
              >
                <RefreshCw 
                  className={`
                    w-4 h-4 transition-colors duration-200
                    ${loadingProcessed 
                      ? 'animate-spin text-blue-600' 
                      : 'text-gray-600 hover:text-gray-800'
                    }
                  `} 
                  strokeWidth={2}
                />
              </button>
              {lastRefreshed && !loadingProcessed && (
                <span className="text-xs text-gray-500">
                  Updated <LocalTimeOnly timestamp={lastRefreshed} />
                </span>
              )}
            </div>
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
          <div className="space-y-4 max-h-96 overflow-y-auto modern-scrollbar">
            {/* Unified Document List */}
            {allDocuments.map((item) => {
              const progress = getProgressPercentage(item.status);
              const isQueued = item.status === 'uploaded';
              const isProcessing = ['uploading', 'processing'].includes(item.status) || 
                                   (typeof item.status === 'string' && (
                                     item.status.includes('In progress') || 
                                     item.status.includes('Starting') ||
                                     item.status.includes('Preparing') ||
                                     item.status.includes('Queued for processing') ||
                                     item.status.includes('Pending - Waiting')
                                   ));
              const isCompleted = ['completed', 'processed', 'finalized'].includes(item.status);
              const isFailed = item.status === 'failed';
              const isShortBatch = item.processingType === 'short-batch' || item.routing?.decision === 'short-batch';
              const isLongBatch = item.processingType === 'long-batch' || item.routing?.decision === 'long-batch';
              const hasDetailedProgress = typeof item.status === 'string' && item.status.includes('In progress');
              
              return (
                <div 
                  key={item.id}
                  className={`relative overflow-hidden rounded-lg border transition-all ${
                    item.status === 'pending' ? 'bg-gray-50 border-gray-200' :
                    isQueued ? 'bg-amber-50 border-amber-200' :
                    isProcessing ? 'bg-blue-50 border-blue-200' :
                    isCompleted ? (item.finalized ? 'bg-green-50 border-green-200' : 'bg-emerald-50 border-emerald-200') :
                    isFailed ? 'bg-red-50 border-red-200' :
                    'bg-gray-50 border-gray-200'
                  } ${item.isFromProcessed ? 'cursor-pointer hover:shadow-md' : ''}`}
                  onClick={() => item.isFromProcessed && navigate(`/edit/${item.fileId}`)}
                >
                  {/* Progress Bar */}
                  {(isProcessing || isQueued) && (
                    <div className="absolute top-0 left-0 w-full h-1 bg-gray-200">
                      <div 
                        className={`h-full transition-all duration-500 ${
                          hasDetailedProgress ? 'bg-gradient-to-r from-blue-500 to-purple-500' : // Long-batch detailed progress
                          isLongBatch ? 'bg-blue-500' : // Long-batch simple progress  
                          isShortBatch ? 'bg-green-500' : // Short-batch progress
                          'bg-blue-500' // Default
                        }`}
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
                            isQueued ? 'text-amber-600' :
                            hasDetailedProgress ? 'text-purple-600' : // Long-batch detailed
                            isProcessing && isShortBatch ? 'text-green-600' : // Short-batch processing
                            isProcessing && isLongBatch ? 'text-blue-600' : // Long-batch simple processing
                            isProcessing ? 'text-blue-600' : // Default processing
                            isCompleted ? (item.finalized ? 'text-green-600' : 'text-emerald-600') :
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
                              isQueued ? 'bg-amber-100 text-amber-800' :
                              isProcessing ? 'bg-blue-100 text-blue-800' :
                              isCompleted ? 'bg-green-100 text-green-800' :
                              isFailed ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {hasDetailedProgress ? 'Processing' : getStatusDisplay(item.status)}
                            </span>
                            {(isShortBatch || isLongBatch) && (
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                isShortBatch ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                              }`}>
                                {isShortBatch ? '⚡ Fast' : '🔄 Comprehensive'}
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
                              {item.processedAt && (
                                <> at <LocalDateTime timestamp={item.processedAt} /></>
                              )}
                            </p>
                          )}
                          
                          {/* Progress text for processing items */}
                          {(isProcessing || isQueued) && (
                            <p className={`text-xs mt-1 font-medium ${
                              isQueued ? 'text-amber-600' : 
                              hasDetailedProgress ? 'text-purple-600' : // Long-batch detailed
                              isLongBatch ? 'text-blue-600' : // Long-batch simple
                              isShortBatch ? 'text-green-600' : // Short-batch
                              'text-blue-600' // Default
                            }`}>
                              {hasDetailedProgress ? (
                                // Show the full detailed status for long-batch processing (already includes percentage and description)
                                <>
                                  <span className="text-purple-600">🔄</span> {item.status}
                                </>
                              ) : (
                                // Show simple progress for other statuses
                                <>
                                  {isShortBatch && isProcessing && (
                                    <span className="text-green-600">⚡</span>
                                  )}
                                  {isLongBatch && isProcessing && !hasDetailedProgress && (
                                    <span className="text-blue-600">🔄</span>
                                  )}
                                  {progress}% - {getStatusDisplay(item.status)}
                                  {isShortBatch && item.status === 'uploaded' && (
                                    <span className="ml-1 text-gray-500">(~30 seconds)</span>
                                  )}
                                  {isLongBatch && item.status === 'uploaded' && (
                                    <span className="ml-1 text-gray-500">(~5-15 minutes)</span>
                                  )}
                                  {isShortBatch && item.status === 'processing' && (
                                    <span className="ml-1 text-gray-500">(finishing soon)</span>
                                  )}
                                </>
                              )}
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