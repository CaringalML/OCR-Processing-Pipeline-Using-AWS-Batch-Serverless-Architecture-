const API_BASE_URL = process.env.REACT_APP_API_GATEWAY_URL;

/**
 * Document Service - Handles document operations with API Gateway
 */
class DocumentService {
  /**
   * Get all processed documents (from both short and long batch)
   * @param {Object} params - Query parameters
   * @param {string} params.fileId - Specific file ID to retrieve
   * @param {number} params.limit - Number of results to return
   * @param {string} params.status - Filter by processing status
   * @param {boolean} params.finalized - Filter by finalized status
   * @returns {Promise<Object>} List of processed documents
   */
  async getProcessedDocuments(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.fileId) queryParams.append('fileId', params.fileId);
      if (params.limit) queryParams.append('limit', params.limit);
      if (params.status) queryParams.append('status', params.status);
      if (params.finalized !== undefined) queryParams.append('finalized', params.finalized);

      const url = `${API_BASE_URL}/batch/processed${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching processed documents:', error);
      throw error;
    }
  }

  /**
   * Get all documents from /batch/processed (for upload queue)
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} List of all processed documents
   */
  async getAllProcessedDocuments(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.fileId) queryParams.append('fileId', params.fileId);
      if (params.limit) queryParams.append('limit', params.limit);
      if (params.status) queryParams.append('status', params.status);

      const url = `${API_BASE_URL}/batch/processed${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching all processed documents:', error);
      throw error;
    }
  }

  /**
   * Get a specific processed document by ID
   * @param {string} fileId - The file ID
   * @param {boolean} finalized - Whether to fetch finalized version
   * @returns {Promise<Object>} Document details
   */
  async getDocument(fileId, finalized = false) {
    try {
      // Build the URL with appropriate query parameters
      const queryParams = new URLSearchParams();
      queryParams.append('fileId', fileId);
      if (finalized) {
        queryParams.append('finalized', 'true');
      }
      
      const url = `${API_BASE_URL}/batch/processed?${queryParams.toString()}`;
      console.log('Fetching document from:', url);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch document: ${response.statusText}`);
      }

      const data = await response.json();
      
      // API returns document directly when querying by fileId
      if (data.fileId) {
        return data;
      }
      
      // Fallback if API returns wrapped in files array
      return data.files && data.files.length > 0 ? data.files[0] : null;
    } catch (error) {
      console.error('Error fetching document:', error);
      throw error;
    }
  }

  /**
   * Edit OCR results for a document
   * @param {string} fileId - The file ID
   * @param {Object} updates - The updates to apply
   * @returns {Promise<Object>} Updated document
   */
  async editOCRResults(fileId, updates) {
    try {
      const response = await fetch(`${API_BASE_URL}/batch/processed/edit?fileId=${fileId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error(`Failed to update OCR results: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating OCR results:', error);
      throw error;
    }
  }

  /**
   * Finalize a document
   * @param {string} fileId - The file ID
   * @param {Object} data - Data containing selected text and other finalization details
   * @returns {Promise<Object>} Finalized document
   */
  async finalizeDocument(fileId, data) {
    try {
      const requestBody = {
        textSource: data.textSource || 'refined', // 'formatted' or 'refined'
        notes: data.notes || ''
      };

      // Add edited text if provided
      if (data.editedText) {
        requestBody.editedText = data.editedText;
        if (!requestBody.notes) {
          requestBody.notes = 'User edited text before finalization';
        }
      }

      console.log('Sending finalization request:', {
        url: `${API_BASE_URL}/batch/processed/finalize/${fileId}`,
        body: requestBody
      });

      const response = await fetch(`${API_BASE_URL}/batch/processed/finalize/${fileId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`Failed to finalize document: ${response.statusText} - ${errorData}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error finalizing document:', error);
      throw error;
    }
  }

  /**
   * Edit a finalized document
   * @param {string} fileId - The file ID
   * @param {Object} data - Edit data containing edited text and reason
   * @returns {Promise<Object>} Edit result
   */
  async editFinalizedDocument(fileId, data) {
    try {
      const requestBody = {
        finalizedText: data.finalizedText, // Required: the new text content
        editReason: data.editReason, // Required: reason for the edit
        preserveHistory: data.preserveHistory !== false // Default to true
      };

      console.log('Sending finalized document edit request:', {
        url: `${API_BASE_URL}/finalized/edit/${fileId}`,
        body: requestBody
      });

      const response = await fetch(`${API_BASE_URL}/finalized/edit/${fileId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`Failed to edit finalized document: ${response.statusText} - ${errorData}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error editing finalized document:', error);
      throw error;
    }
  }

  /**
   * Delete a document (soft delete to recycle bin)
   * @param {string} fileId - The file ID
   * @returns {Promise<Object>} Deletion result
   */
  async deleteDocument(fileId) {
    try {
      const response = await fetch(`${API_BASE_URL}/batch/delete/${fileId}`, {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete document: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  }

  /**
   * Permanently delete a document
   * @param {string} fileId - The file ID
   * @returns {Promise<Object>} Deletion result
   */
  async permanentlyDeleteDocument(fileId) {
    try {
      const response = await fetch(`${API_BASE_URL}/batch/delete/${fileId}?permanent=true`, {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to permanently delete document: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error permanently deleting document:', error);
      throw error;
    }
  }

  /**
   * Get recycle bin contents
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Recycle bin items
   */
  async getRecycleBin(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.limit) queryParams.append('limit', params.limit);
      if (params.fileId) queryParams.append('fileId', params.fileId);

      const url = `${API_BASE_URL}/batch/recycle-bin${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch recycle bin: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching recycle bin:', error);
      throw error;
    }
  }

  /**
   * Restore a document from recycle bin
   * @param {string} fileId - The file ID
   * @returns {Promise<Object>} Restoration result
   */
  async restoreDocument(fileId) {
    try {
      const response = await fetch(`${API_BASE_URL}/batch/restore/${fileId}`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to restore document: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error restoring document:', error);
      throw error;
    }
  }

  /**
   * Get processed invoices
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Processed invoices
   */
  async getProcessedInvoices(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.fileId) queryParams.append('fileId', params.fileId);
      if (params.vendorName) queryParams.append('vendorName', params.vendorName);
      if (params.invoiceNumber) queryParams.append('invoiceNumber', params.invoiceNumber);

      const url = `${API_BASE_URL}/short-batch/invoices/processed${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch invoices: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching invoices:', error);
      throw error;
    }
  }

  /**
   * Download a document
   * @param {string} fileId - The file ID
   * @param {string} cloudFrontUrl - The CloudFront URL if available
   * @returns {Promise<Blob>} Document file
   */
  async downloadDocument(fileId, cloudFrontUrl) {
    try {
      // If CloudFront URL is available, use it directly
      if (cloudFrontUrl) {
        const response = await fetch(cloudFrontUrl);
        if (!response.ok) {
          throw new Error(`Failed to download document: ${response.statusText}`);
        }
        return await response.blob();
      }

      // Otherwise, use the API endpoint
      const response = await fetch(`${API_BASE_URL}/documents/${fileId}/download`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Failed to download document: ${response.statusText}`);
      }

      return await response.blob();
    } catch (error) {
      console.error('Error downloading document:', error);
      throw error;
    }
  }

  /**
   * Format date for display
   * @param {string} isoDate - ISO date string
   * @returns {string} Formatted date
   */
  formatDate(isoDate) {
    if (!isoDate) return '';
    
    const date = new Date(isoDate);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }

  /**
   * Get processing status color
   * @param {string} status - Processing status
   * @returns {string} CSS color class
   */
  getStatusColor(status) {
    const statusColors = {
      'uploaded': 'text-blue-600 bg-blue-50',
      'queued': 'text-yellow-600 bg-yellow-50',
      'processing': 'text-orange-600 bg-orange-50',
      'processed': 'text-green-600 bg-green-50',
      'completed': 'text-green-600 bg-green-50',
      'failed': 'text-red-600 bg-red-50',
    };
    
    return statusColors[status] || 'text-gray-600 bg-gray-50';
  }
}

// Export singleton instance
const documentService = new DocumentService();
export default documentService;

// Also export the class for testing
export { DocumentService };