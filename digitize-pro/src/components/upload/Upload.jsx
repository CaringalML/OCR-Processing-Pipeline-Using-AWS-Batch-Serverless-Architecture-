import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Upload as UploadIcon, FileText, X, CheckCircle, AlertCircle, Edit, RefreshCw, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import uploadService from '../../services/uploadService';
import { useDocuments } from '../../hooks/useDocuments';
import documentService from '../../services/documentService';
import { LocalTimeOnly, LocalDateTime } from '../common/LocalTime';
import ModernDatePicker from '../common/ModernDatePicker';

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
  const [deleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteFileInfo, setDeleteFileInfo] = useState({ fileId: null, fileName: '', isFinalized: false });
  const [deploymentInfo, setDeploymentInfo] = useState({ mode: null, longBatchAvailable: null, maxFileSize: null });
  const fileInputRef = useRef(null);
  useDocuments();

  // Fetch detailed status for individual processing files
  // Note: Only long-batch files get detailed "In progress X%" statuses
  // Short-batch files just show generic "processing" status
  const fetchDetailedStatus = useCallback(async (fileId) => {
    try {
      const detailedData = await documentService.getDocument(fileId);
      
      if (detailedData && detailedData.processingStatus) {
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
  }, []);

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
        // Fetch documents with all statuses to include in-progress files
        const data = await documentService.getAllProcessedDocuments({ status: 'all' });
        
        // Handle different response structures
        if (data) {
          let newDocuments = [];
          if (Array.isArray(data)) {
            newDocuments = data;
          } else if (data.files && Array.isArray(data.files)) {
            newDocuments = data.files;
          } else if (data.items && Array.isArray(data.items)) {
            newDocuments = data.items;
          } else if (data.documents && Array.isArray(data.documents)) {
            newDocuments = data.documents;
          } else {
            console.warn('Unexpected data structure:', data);
            newDocuments = [];
          }
          
          // Filter out soft-deleted files that might still be returned by the backend
          const activeDocuments = newDocuments.filter(doc => {
            // Check for various deletion indicators that the backend might return
            return !doc.deleted && 
                   !doc.isDeleted && 
                   !doc.deleted_timestamp &&
                   !doc.deletedAt &&
                   doc.processingStatus !== 'deleted' &&
                   doc.processing_status !== 'deleted';
          });
          
          // CRITICAL: Preserve any files that are currently showing "deleting" status
          setAllProcessedDocuments(prev => {
            const result = [...activeDocuments];
            
            // Find any files in previous state that had "deleting" status
            const deletingFiles = prev.filter(doc => doc.status === 'deleting');
            
            if (deletingFiles.length > 0) {
              // For each deleting file, check if it still exists in backend
              for (const deletingFile of deletingFiles) {
                const stillInBackend = activeDocuments.some(doc => doc.fileId === deletingFile.fileId);
                if (stillInBackend) {
                  // File still exists in backend, replace with deleting version
                  const index = result.findIndex(doc => doc.fileId === deletingFile.fileId);
                  if (index !== -1) {
                    result[index] = deletingFile; // Keep the deleting status
                  }
                }
              }
            }
            
            return result;
          });
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
  }, [allProcessedDocuments, detailedStatusCache, fetchDetailedStatus]);

  // Set up more frequent polling for long-batch files with detailed status
  useEffect(() => {
    const interval = setInterval(async () => {
      const filesWithDetailedStatus = Object.keys(detailedStatusCache).filter(fileId => {
        const cached = detailedStatusCache[fileId];
        // Only poll if it's showing "In progress" (which indicates long-batch processing)
        return cached && cached.status.includes('In progress');
      });

      if (filesWithDetailedStatus.length > 0) {
        for (const fileId of filesWithDetailedStatus) {
          await fetchDetailedStatus(fileId);
        }
      }
    }, 5000); // Poll every 5 seconds for processing files

    return () => clearInterval(interval);
  }, [detailedStatusCache, fetchDetailedStatus]);

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
    
    // Map processed documents to display format, including files being deleted with special status
    const processedDocs = allProcessedDocuments.map(doc => {
      const fileId = doc.fileId;
      const baseStatus = doc.processingStatus || doc.processing_status || "pending";
      
      // Show deleting status if file status is 'deleting'
      if (doc.status === 'deleting') {
        return {
          id: doc.fileId,
          fileId: doc.fileId,
          name: doc.fileName || doc.file_name || doc.original_filename || 'Unknown file',
          size: doc.fileSize || doc.file_size || 'Unknown size',
          status: 'deleting',
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
          isFromProcessed: true,
          isDeleting: true
        };
      }
      
      // Use detailed status from cache if available for processing files
      // BUT NEVER override "deleting" status - this was the bug!
      const cachedStatus = detailedStatusCache[fileId];
      let finalStatus;
      if (doc.status === 'deleting') {
        // Always preserve deleting status - never override it
        finalStatus = 'deleting';
      } else if ((baseStatus === 'processing' || baseStatus === 'uploaded') && cachedStatus) {
        finalStatus = cachedStatus.status;
      } else {
        finalStatus = baseStatus;
      }

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
      failed: 0,        // failed files
      deleting: 0       // files being deleted
    };
    
    allDocuments.forEach(item => {
      if (item.status === 'deleting') {
        counts.deleting++;
      } else if (item.status === 'pending') {
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
      // Validate file size based on deployment mode
      const maxSizeMB = deploymentInfo.mode === 'short-batch' ? 
        (parseFloat(deploymentInfo.maxFileSize) / 1024) || 0.3 :  // Convert KB to MB, default to 0.3MB (300KB)
        500;  // Full deployment allows 500MB
        
      if (!uploadService.validateFileSize(file, maxSizeMB)) {
        const currentSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        if (deploymentInfo.mode === 'short-batch') {
          setUploadError(`File too large: ${file.name} (${currentSizeMB}MB). Maximum size in short-batch mode is ${deploymentInfo.maxFileSize || '300KB'}. Contact administrator to enable large file processing.`);
        } else {
          setUploadError(`File too large: ${file.name} (${currentSizeMB}MB). Maximum size is ${maxSizeMB}MB`);
        }
        return false;
      }
      
      // Warn about TIFF files
      const fileExtension = file.name.split('.').pop().toLowerCase();
      if (fileExtension === 'tiff' || fileExtension === 'tif') {
        console.warn(`⚠️ TIFF file detected: ${file.name} - TIFF files are typically large and may take longer to process`);
        // Optionally show a toast or notification to user
        setTimeout(() => {
          setUploadError(`Note: TIFF file "${file.name}" may take longer to process due to larger file size`);
          // Clear the warning after 5 seconds
          setTimeout(() => setUploadError(null), 5000);
        }, 100);
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
        const result = await uploadService.uploadDocument(item.file, metadata);
        
        // Extract and store deployment info from the response
        if (result.deployment_info) {
          setDeploymentInfo({
            mode: result.deployment_info.mode,
            longBatchAvailable: result.deployment_info.long_batch_available,
            maxFileSize: result.deployment_info.max_file_size
          });
        }
        
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

        // Skip fetchDocuments() - we have our own state management
        // await fetchDocuments();
        
        // For short-batch files, start frequent polling for faster updates
        if (result.files?.[0]?.routing?.decision === 'short-batch') {
          // Poll every 3 seconds for the first 2 minutes after upload
          const fileId = result.files?.[0]?.file_id;
          let pollCount = 0;
          const maxPolls = 40; // 40 * 3 seconds = 2 minutes
          
          const fastPoll = setInterval(async () => {
            pollCount++;
            
            // Lightweight check - only get this specific file's status
            try {
              const data = await documentService.getAllProcessedDocuments({ status: 'all' });
              const backendFiles = data?.files || data?.items || data?.documents || data || [];
              const currentFile = backendFiles.find(doc => doc.fileId === fileId);
              
              if (currentFile) {
                // Update only this specific file in our state - but preserve deleting status
                setAllProcessedDocuments(prev => prev.map(doc => {
                  if (doc.fileId === fileId) {
                    // CRITICAL: Don't override deleting status during fast polling
                    if (doc.status === 'deleting') {
                      return doc; // Keep as-is
                    }
                    return { ...doc, ...currentFile };
                  }
                  return doc;
                }));
              }
              
              // Stop fast polling if file is completed or max polls reached
              if (pollCount >= maxPolls || 
                  (currentFile && ['completed', 'processed', 'failed'].includes(currentFile.processingStatus || currentFile.processing_status))) {
                clearInterval(fastPoll);
              }
            } catch (error) {
              console.error(`❌ Fast poll error for file ${fileId}:`, error);
              // Continue polling on error
            }
          }, 3000);
        }
      } catch (error) {
        console.error('Upload failed:', error);
        
        // Check if this is a deployment mode error (large file processing unavailable)
        const isDeploymentModeError = error.message.includes('Large file processing unavailable') || 
                                     error.message.includes('deployment only supports files') ||
                                     error.message.includes('Long-batch processing unavailable');
        
        // Update status to failed
        setUploadQueue(prev => prev.map(f => 
          f.id === item.id ? { 
            ...f, 
            status: 'failed', 
            error: error.message,
            isDeploymentError: isDeploymentModeError
          } : f
        ));
        
        // Set a more prominent error message for deployment mode issues
        if (isDeploymentModeError) {
          setUploadError(error.message);
        }
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
      'finalized': 100,    // User finalized the document
      'deleting': 0        // File being deleted
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
      'finalized': 'Finalized',
      'deleting': 'Deleting...'
    };
    return statusDisplay[status] || status;
  };

  // Refresh processed documents with immediate feedback
  const refreshDocuments = async () => {
    try {
      setLoadingProcessed(true);
      
      // Clear detailed status cache to force fresh fetches
      setDetailedStatusCache({});
      
      // Skip fetchDocuments() - we have our own state management
      // await fetchDocuments();
      
      const data = await documentService.getAllProcessedDocuments({ status: 'all' });
      
      // Handle different response structures and simply use fresh backend data
      if (data) {
        let newDocuments = [];
        if (Array.isArray(data)) {
          newDocuments = data;
        } else if (data.files && Array.isArray(data.files)) {
          newDocuments = data.files;
        } else if (data.items && Array.isArray(data.items)) {
          newDocuments = data.items;
        } else if (data.documents && Array.isArray(data.documents)) {
          newDocuments = data.documents;
        } else {
          console.warn('Unexpected data structure:', data);
          newDocuments = [];
        }
        
        // Filter out soft-deleted files that might still be returned by the backend
        const activeDocuments = newDocuments.filter(doc => {
          // Check for various deletion indicators that the backend might return
          return !doc.deleted && 
                 !doc.isDeleted && 
                 !doc.deleted_timestamp &&
                 !doc.deletedAt &&
                 doc.processingStatus !== 'deleted' &&
                 doc.processing_status !== 'deleted';
        });
        
        // CRITICAL: Preserve any files that are currently showing "deleting" status
        setAllProcessedDocuments(prev => {
          const result = [...activeDocuments];
          
          // Find any files in previous state that had "deleting" status
          const deletingFiles = prev.filter(doc => doc.status === 'deleting');
          
          if (deletingFiles.length > 0) {
            // For each deleting file, check if it still exists in backend
            for (const deletingFile of deletingFiles) {
              const stillInBackend = activeDocuments.some(doc => doc.fileId === deletingFile.fileId);
              if (stillInBackend) {
                // File still exists in backend, replace with deleting version
                const index = result.findIndex(doc => doc.fileId === deletingFile.fileId);
                if (index !== -1) {
                  result[index] = deletingFile; // Keep the deleting status
                }
              }
            }
          }
          
          return result;
        });
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
        for (const doc of processingFiles) {
          if (doc.fileId) {
            await fetchDetailedStatus(doc.fileId);
          }
        }
      }

      setLastRefreshed(Date.now());
    } catch (error) {
      console.error('Error refreshing documents:', error);
      setUploadError(`Failed to refresh documents: ${error.message}`);
    } finally {
      setLoadingProcessed(false);
    }
  };

  // Full refresh - simply gets fresh data from backend

  const showDeleteConfirmation = (fileId, fileName) => {
    // Find the document to check if it's finalized
    const document = allProcessedDocuments.find(doc => doc.fileId === fileId);
    const isFinalized = document?.finalized || false;
    
    setDeleteFileInfo({ fileId, fileName, isFinalized });
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = async () => {
    const { fileId, isFinalized } = deleteFileInfo;
    setShowDeleteConfirm(false);

    try {
      // Show deleting status immediately
      setAllProcessedDocuments(prev => prev.map(doc => {
        if (doc.fileId === fileId) {
          return { ...doc, status: 'deleting' };
        }
        return doc;
      }));
      
      if (isFinalized) {
        // Finalized documents go to recycle bin
        await documentService.deleteDocument(fileId);
      } else {
        // Non-finalized documents are permanently deleted
        await documentService.permanentlyDeleteDocument(fileId);
      }
      
      // Show deleting progress and auto-refresh when complete
      const handleDeletionProgress = async () => {
        
        // Show progress indicators for better UX
        let progressStep = 1;
        const totalSteps = 5;
        
        const updateProgress = () => {
          setAllProcessedDocuments(prev => prev.map(doc => {
            if (doc.fileId === fileId && doc.status === 'deleting') {
              return { 
                ...doc, 
                status: 'deleting',
                deletionProgress: Math.min(100, (progressStep / totalSteps) * 100)
              };
            }
            return doc;
          }));
          progressStep++;
        };
        
        // Progress simulation while backend processes
        const progressInterval = setInterval(() => {
          if (progressStep <= totalSteps) {
            updateProgress();
          } else {
            clearInterval(progressInterval);
          }
        }, 1000); // Update progress every second
        
        // Wait for a reasonable time for backend processing
        await new Promise(resolve => setTimeout(resolve, 6000)); // 6 seconds total
        
        // Clear progress and refresh
        clearInterval(progressInterval);
        
        // CRITICAL: For deletion refresh, completely bypass all preservation logic
        try {
          setLoadingProcessed(true);
          const data = await documentService.getAllProcessedDocuments({ status: 'all' });
          
          let newDocuments = [];
          if (Array.isArray(data)) {
            newDocuments = data;
          } else if (data && data.files && Array.isArray(data.files)) {
            newDocuments = data.files;
          } else if (data && data.items && Array.isArray(data.items)) {
            newDocuments = data.items;
          } else if (data && data.documents && Array.isArray(data.documents)) {
            newDocuments = data.documents;
          }
          
          setAllProcessedDocuments(newDocuments.filter(doc => 
            !doc.deleted && !doc.isDeleted && !doc.deleted_timestamp && !doc.deletedAt
          ));
        } catch (error) {
          console.error('❌ Post-deletion refresh failed:', error);
          // Fallback to regular refresh
          await refreshDocuments();
        } finally {
          setLoadingProcessed(false);
        }
      };
      
      handleDeletionProgress();
      
    } catch (error) {
      console.error('Error deleting document:', error);
      setUploadError(`Failed to delete document: ${error.message}`);
      
      // Reset the document back to its original state on error
      const originalDoc = allProcessedDocuments.find(doc => doc.fileId === fileId);
      if (originalDoc) {
        setAllProcessedDocuments(prev => prev.map(doc => {
          if (doc.fileId === fileId) {
            return { ...originalDoc, status: originalDoc.processingStatus || originalDoc.processing_status || 'processed' };
          }
          return doc;
        }));
      }
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
                {showMetadataForm ? 'Hide' : (() => {
                  // Check if any metadata fields have content
                  const hasMetadata = metadata.title || metadata.author || metadata.publication || 
                                    metadata.date || metadata.page || metadata.tags || metadata.description || 
                                    metadata.subject || (metadata.language && metadata.language !== 'English') || 
                                    (metadata.type && metadata.type !== 'Document') || metadata.rights || metadata.collection;
                  return hasMetadata ? 'Edit' : 'Add';
                })()} Metadata
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-4">
              Supported formats: PDF, TIFF, JPG, PNG • Maximum file size: 
              {deploymentInfo.mode === 'short-batch' ? 
                ` ${deploymentInfo.maxFileSize || '300KB'} (short-batch mode)` :
                deploymentInfo.mode === 'full' ?
                ' 500MB (full deployment)' :
                ' 500MB'
              }
              {deploymentInfo.mode === 'short-batch' && (
                <span className="text-amber-600"> ⚠️ Large file processing disabled</span>
              )}
            </p>
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
                  <ModernDatePicker
                    value={metadata.date}
                    onChange={(date) => setMetadata({...metadata, date: date})}
                    placeholder="Select publication date"
                    className="w-full"
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

      {/* Deployment Mode Info Banner */}
      {deploymentInfo.mode === 'short-batch' && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg flex items-center justify-between">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 mr-2 text-amber-600" />
            <div>
              <p className="font-medium">Limited Deployment Mode</p>
              <p className="text-sm text-amber-700">
                Large file processing is disabled. Files over {deploymentInfo.maxFileSize || '300KB'} will be rejected. 
                Contact your administrator to enable full deployment mode for unlimited file processing.
              </p>
            </div>
          </div>
        </div>
      )}

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
              {statusCounts.deleting > 0 && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  🗑️ {statusCounts.deleting} Deleting
                </span>
              )}
              {allDocuments.length === 0 && (
                <span className="text-xs text-gray-500">No files</span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <button 
                onClick={refreshDocuments}
                disabled={loadingProcessed || deleting}
                className={`
                  relative p-2 rounded-full border transition-all duration-200
                  ${(loadingProcessed || deleting)
                    ? 'border-blue-400 bg-blue-50 cursor-not-allowed opacity-50' 
                    : 'border-gray-300 bg-white hover:bg-gray-50 hover:border-gray-400 cursor-pointer'
                  }
                  focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500
                `}
                title={
                  deleting 
                    ? "Refresh disabled during deletion"
                    : loadingProcessed 
                      ? "Refreshing..." 
                      : lastRefreshed 
                        ? `Last refreshed: ${new Date(lastRefreshed).toLocaleString()}` 
                        : "Refresh documents"
                }
                aria-label="Refresh"
              >
                <RefreshCw 
                  className={`
                    w-4 h-4 transition-colors duration-200
                    ${(loadingProcessed || deleting)
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
          <div className="flex items-center space-x-2">
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
              const isDeleting = item.status === 'deleting';
              const isShortBatch = item.processingType === 'short-batch' || item.routing?.decision === 'short-batch';
              const isLongBatch = item.processingType === 'long-batch' || item.routing?.decision === 'long-batch';
              const hasDetailedProgress = typeof item.status === 'string' && item.status.includes('In progress');
              
              return (
                <div 
                  key={item.id}
                  className={`relative overflow-hidden rounded-lg border transition-all duration-300 ${
                    isDeleting ? 'bg-red-50 border-red-300 opacity-90 transform scale-[0.99]' :
                    item.status === 'pending' ? 'bg-gray-50 border-gray-200' :
                    isQueued ? 'bg-amber-50 border-amber-200' :
                    isProcessing ? 'bg-blue-50 border-blue-200' :
                    isCompleted ? (item.finalized ? 'bg-green-50 border-green-200' : 'bg-emerald-50 border-emerald-200') :
                    isFailed ? 'bg-red-50 border-red-200' :
                    'bg-gray-50 border-gray-200'
                  } ${item.isFromProcessed && !isDeleting ? 'cursor-pointer hover:shadow-md' : ''}`}
                  onClick={(e) => {
                    // Don't navigate if clicking on interactive elements
                    const isInteractive = e.target.closest('input[type="checkbox"]') || 
                                        e.target.closest('button');
                    if (item.isFromProcessed && !isInteractive) {
                      navigate(`/edit/${item.fileId}`);
                    }
                  }}
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
                  
                  {/* Deleting Progress Bar */}
                  {isDeleting && (
                    <div className="absolute top-0 left-0 w-full h-1 bg-red-200 overflow-hidden">
                      <div 
                        className="h-full bg-red-500 transition-all duration-1000 ease-out"
                        style={{ 
                          width: `${item.deletionProgress || 0}%`
                        }}
                      />
                    </div>
                  )}
                  
                  <div className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <div className="flex flex-col items-center">
                          {isDeleting ? (
                            <div className="relative">
                              <FileText className="w-8 h-8 text-red-400 opacity-50" />
                              <div className="absolute inset-0 flex items-center justify-center">
                                <Trash2 className="w-5 h-5 text-red-600 animate-pulse" />
                              </div>
                            </div>
                          ) : (
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
                          )
                        }
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
                            <p className={`font-medium ${isDeleting ? 'text-red-800 line-through opacity-75' : 'text-gray-900'}`}>
                              {item.name}
                            </p>
                            <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium ${
                              isDeleting ? 'bg-red-100 text-red-800' :
                              item.status === 'pending' ? 'bg-gray-100 text-gray-800' :
                              isQueued ? 'bg-amber-100 text-amber-800' :
                              isProcessing ? 'bg-blue-100 text-blue-800' :
                              isCompleted ? 'bg-green-100 text-green-800' :
                              isFailed ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {isDeleting && (
                                <RefreshCw className="w-3 h-3 animate-spin" />
                              )}
                              <span>{hasDetailedProgress ? 'Processing' : getStatusDisplay(item.status)}</span>
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
                            <div className={`text-xs mt-1 p-2 rounded ${
                              item.isDeploymentError ? 'bg-amber-50 border border-amber-200' : ''
                            }`}>
                              {item.isDeploymentError ? (
                                <div className="space-y-1">
                                  <p className="text-amber-800 font-medium">⚠️ Deployment Limitation</p>
                                  <p className="text-amber-700">{item.error}</p>
                                  <p className="text-amber-600 text-xs">Contact your administrator to enable large file processing.</p>
                                </div>
                              ) : (
                                <p className="text-red-600">Error: {item.error}</p>
                              )}
                            </div>
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
                          <>
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
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                showDeleteConfirmation(item.fileId, item.name);
                              }}
                              disabled={isDeleting}
                              className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Delete Document"
                            >
                              {isDeleting ? (
                                <RefreshCw className="w-5 h-5 animate-spin" />
                              ) : (
                                <Trash2 className="w-5 h-5" />
                              )}
                            </button>
                          </>
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
                <p className="text-sm text-gray-400 mt-1">Upload documents above or check your internet connection</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
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
                  Delete Document
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  Are you sure you want to delete <span className="font-medium text-gray-900">"{deleteFileInfo.fileName}"</span>?
                </p>
                {deleteFileInfo.isFinalized ? (
                  <p className="text-sm text-amber-600 bg-amber-50 rounded-md p-3 mb-4">
                    <span className="font-medium">Note:</span> This document will be moved to the recycle bin and can be restored later.
                  </p>
                ) : (
                  <p className="text-sm text-red-600 bg-red-50 rounded-md p-3 mb-4">
                    <span className="font-medium">Warning:</span> This action cannot be undone. The document will be permanently deleted.
                  </p>
                )}
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
                  onClick={handleConfirmDelete}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  {deleteFileInfo.isFinalized ? 'Move to Recycle Bin' : 'Delete Permanently'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Upload;