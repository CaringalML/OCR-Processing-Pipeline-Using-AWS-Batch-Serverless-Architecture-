import { useState, useCallback } from 'react';
import uploadService from '../services/uploadService';

/**
 * Custom hook for handling file uploads
 */
const useUpload = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  /**
   * Upload a single file with smart routing
   */
  const uploadFile = useCallback(async (file, metadata = {}) => {
    setUploading(true);
    setUploadError(null);
    setUploadProgress(0);

    try {
      // Validate file
      if (!uploadService.validateFileType(file)) {
        throw new Error(`Invalid file type: ${file.name}. Supported formats: PDF, TIFF, JPG, PNG`);
      }

      if (!uploadService.validateFileSize(file, 500)) {
        throw new Error(`File too large: ${file.name}. Maximum size is 500MB`);
      }

      // Upload file
      const result = await uploadService.uploadDocument(
        file,
        metadata,
        (progress) => setUploadProgress(progress)
      );

      setUploadResult(result);
      setUploadProgress(100);
      return result;
    } catch (error) {
      setUploadError(error.message);
      throw error;
    } finally {
      setUploading(false);
    }
  }, []);

  /**
   * Upload multiple files
   */
  const uploadMultipleFiles = useCallback(async (files, metadata = {}) => {
    const results = [];
    const errors = [];

    for (const file of files) {
      try {
        const result = await uploadFile(file, metadata);
        results.push(result);
      } catch (error) {
        errors.push({ file: file.name, error: error.message });
      }
    }

    return { results, errors };
  }, [uploadFile]);

  /**
   * Force upload to short-batch (Claude AI)
   */
  const uploadToShortBatch = useCallback(async (file, metadata = {}) => {
    setUploading(true);
    setUploadError(null);

    try {
      const result = await uploadService.uploadShortBatch(file, metadata);
      setUploadResult(result);
      return result;
    } catch (error) {
      setUploadError(error.message);
      throw error;
    } finally {
      setUploading(false);
    }
  }, []);

  /**
   * Force upload to long-batch (AWS Batch)
   */
  const uploadToLongBatch = useCallback(async (file, metadata = {}) => {
    setUploading(true);
    setUploadError(null);

    try {
      const result = await uploadService.uploadLongBatch(file, metadata);
      setUploadResult(result);
      return result;
    } catch (error) {
      setUploadError(error.message);
      throw error;
    } finally {
      setUploading(false);
    }
  }, []);

  /**
   * Upload invoice for specialized processing
   */
  const uploadInvoice = useCallback(async (file, metadata = {}) => {
    setUploading(true);
    setUploadError(null);

    try {
      const result = await uploadService.uploadInvoice(file, metadata);
      setUploadResult(result);
      return result;
    } catch (error) {
      setUploadError(error.message);
      throw error;
    } finally {
      setUploading(false);
    }
  }, []);

  /**
   * Reset upload state
   */
  const resetUpload = useCallback(() => {
    setUploading(false);
    setUploadProgress(0);
    setUploadError(null);
    setUploadResult(null);
  }, []);

  /**
   * Validate file before upload
   */
  const validateFile = useCallback((file) => {
    const errors = [];

    if (!uploadService.validateFileType(file)) {
      errors.push('Invalid file type');
    }

    if (!uploadService.validateFileSize(file, 500)) {
      errors.push('File size exceeds 500MB');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }, []);

  return {
    // State
    uploading,
    uploadProgress,
    uploadError,
    uploadResult,
    
    // Methods
    uploadFile,
    uploadMultipleFiles,
    uploadToShortBatch,
    uploadToLongBatch,
    uploadInvoice,
    resetUpload,
    validateFile,
    
    // Utilities
    formatFileSize: uploadService.formatFileSize
  };
};

export default useUpload;