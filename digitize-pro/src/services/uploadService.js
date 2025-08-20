// API methods integrated directly in service

const API_BASE_URL = process.env.REACT_APP_API_GATEWAY_URL;

/**
 * Upload Service - Handles document uploads to API Gateway
 */
class UploadService {
  /**
   * Upload a document with smart routing (auto-decides between short/long batch)
   * @param {File} file - The file to upload
   * @param {Object} metadata - Additional metadata for the document
   * @param {Function} onProgress - Progress callback
   * @returns {Promise<Object>} Upload response with file details and routing decision
   */
  async uploadDocument(file, metadata = {}, onProgress = null) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add ALL metadata fields if provided
    if (metadata.title) formData.append('title', metadata.title);
    if (metadata.author) formData.append('author', metadata.author);
    if (metadata.publication) formData.append('publication', metadata.publication);
    
    // Handle date field - can be YYYY-MM-DD or just YYYY
    if (metadata.date) {
      const dateValue = metadata.date.trim();
      // If it's just a year (4 digits), use as is
      if (/^\d{4}$/.test(dateValue)) {
        formData.append('year', dateValue);
        formData.append('date', dateValue);
      } else {
        // If it's a full date or other format, pass as is
        formData.append('date', dateValue);
        // Extract year if it's a valid date format
        const yearMatch = dateValue.match(/^(\d{4})/);
        if (yearMatch) {
          formData.append('year', yearMatch[1]);
        }
      }
    }
    
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.page) formData.append('page', metadata.page);
    if (metadata.tags) formData.append('tags', Array.isArray(metadata.tags) ? metadata.tags.join(',') : metadata.tags);
    if (metadata.priority) formData.append('priority', metadata.priority);
    
    // Add missing metadata fields
    if (metadata.subject) formData.append('subject', metadata.subject);
    if (metadata.language) formData.append('language', metadata.language);
    if (metadata.type) formData.append('document_type', metadata.type); // Map 'type' to 'document_type' (backend expects underscore)
    if (metadata.rights) formData.append('rights', metadata.rights);
    if (metadata.collection) formData.append('collection', metadata.collection);
    
    // Add any other metadata fields dynamically
    Object.keys(metadata).forEach(key => {
      const standardFields = ['title', 'author', 'publication', 'date', 'description', 'page', 'tags', 'priority', 'subject', 'language', 'type', 'rights', 'collection'];
      if (!standardFields.includes(key) && metadata[key]) {
        formData.append(key, metadata[key]);
      }
    });

    try {
      console.log('Uploading to:', `${API_BASE_URL}/batch/upload`);
      console.log('Form data fields:', Array.from(formData.keys()));
      console.log('Metadata being sent:', metadata);
      
      // Log all form data for debugging
      for (let [key, value] of formData.entries()) {
        if (key !== 'file') {
          console.log(`FormData ${key}:`, value);
        }
      }
      
      const response = await fetch(`${API_BASE_URL}/batch/upload`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - browser will set it with boundary
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        let errorMessage;
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
        } catch (parseError) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return {
        success: true,
        ...data
      };
    } catch (error) {
      console.error('Upload error details:', {
        message: error.message,
        name: error.name,
        stack: error.stack,
        apiUrl: `${API_BASE_URL}/batch/upload`
      });
      
      // Provide more user-friendly error messages
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Network error: Unable to connect to the server. Please check your internet connection and try again.');
      } else if (error.message.includes('NetworkError') || error.message.includes('ERR_NETWORK')) {
        throw new Error('Network error: Server may be unreachable. Please try again later.');
      } else if (error.message.includes('CORS')) {
        throw new Error('CORS error: Server configuration issue. Please contact support.');
      }
      
      throw error;
    }
  }

  /**
   * Force upload to short-batch processing (Claude AI)
   * @param {File} file - The file to upload (max 50MB)
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<Object>} Upload response
   */
  async uploadShortBatch(file, metadata = {}) {
    // Check file size (50MB limit for Lambda)
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    if (file.size > maxSize) {
      throw new Error(`File too large for short-batch processing. Maximum size is 50MB, your file is ${(file.size / (1024 * 1024)).toFixed(2)}MB`);
    }

    const formData = new FormData();
    formData.append('file', file);
    
    // Add metadata
    Object.keys(metadata).forEach(key => {
      if (metadata[key]) {
        formData.append(key, metadata[key]);
      }
    });

    try {
      const response = await fetch(`${API_BASE_URL}/short-batch/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Short-batch upload error:', error);
      throw error;
    }
  }

  /**
   * Force upload to long-batch processing (AWS Batch + Textract)
   * @param {File} file - The file to upload (no size limit)
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<Object>} Upload response
   */
  async uploadLongBatch(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add metadata
    Object.keys(metadata).forEach(key => {
      if (metadata[key]) {
        formData.append(key, metadata[key]);
      }
    });

    try {
      const response = await fetch(`${API_BASE_URL}/long-batch/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Long-batch upload error:', error);
      throw error;
    }
  }

  /**
   * Upload invoice for specialized processing
   * @param {File} file - Invoice file
   * @param {Object} metadata - Invoice metadata
   * @returns {Promise<Object>} Upload response
   */
  async uploadInvoice(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add invoice-specific metadata
    Object.keys(metadata).forEach(key => {
      if (metadata[key]) {
        formData.append(key, metadata[key]);
      }
    });

    try {
      const response = await fetch(`${API_BASE_URL}/short-batch/invoices/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Invoice upload failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Invoice upload error:', error);
      throw error;
    }
  }

  /**
   * Get upload status
   * @param {string} uploadId - The upload ID
   * @returns {Promise<Object>} Upload status
   */
  async getUploadStatus(uploadId) {
    try {
      const response = await fetch(`${API_BASE_URL}/upload/status/${uploadId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get upload status: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get upload status error:', error);
      throw error;
    }
  }

  /**
   * Cancel an upload
   * @param {string} uploadId - The upload ID to cancel
   * @returns {Promise<Object>} Cancellation result
   */
  async cancelUpload(uploadId) {
    try {
      const response = await fetch(`${API_BASE_URL}/upload/cancel/${uploadId}`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to cancel upload: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Cancel upload error:', error);
      throw error;
    }
  }

  /**
   * Format file size for display
   * @param {number} bytes - File size in bytes
   * @returns {string} Formatted file size
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Validate file type
   * @param {File} file - File to validate
   * @returns {boolean} True if valid
   */
  validateFileType(file) {
    const allowedTypes = ['pdf', 'tiff', 'tif', 'jpg', 'jpeg', 'png'];
    const fileExtension = file.name.split('.').pop().toLowerCase();
    return allowedTypes.includes(fileExtension);
  }

  /**
   * Validate file size
   * @param {File} file - File to validate
   * @param {number} maxSizeMB - Maximum size in MB
   * @returns {boolean} True if valid
   */
  validateFileSize(file, maxSizeMB = 500) {
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    return file.size <= maxSizeBytes;
  }
}

// Export singleton instance
const uploadService = new UploadService();
export default uploadService;

// Also export the class for testing
export { UploadService };