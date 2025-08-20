import { useState, useEffect, useCallback } from 'react';
import documentService from '../services/documentService';
import uploadService from '../services/uploadService';

export const useDocuments = (autoLoad = true) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(false);

  // Fetch documents from API
  const fetchDocuments = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await documentService.getProcessedDocuments(params);
      setDocuments(data.files || []);
      setHasMore(data.hasMore || false);
      return data;
      
    } catch (err) {
      setError(err.message || 'Failed to fetch documents');
      console.error('Error fetching documents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Upload document with smart routing
  const uploadDocument = useCallback(async (file, metadata = {}, onProgress = null) => {
    try {
      setError(null);
      
      // Upload to API Gateway with smart routing
      const result = await uploadService.uploadDocument(file, metadata, onProgress);
      
      // Refresh documents list after upload
      await fetchDocuments();
      
      return result;
      
    } catch (err) {
      setError(err.message || 'Failed to upload document');
      throw err;
    }
  }, [fetchDocuments]);

  // Delete document (soft delete to recycle bin)
  const deleteDocument = useCallback(async (fileId) => {
    try {
      setError(null);
      
      const result = await documentService.deleteDocument(fileId);
      
      // Remove from local state
      setDocuments(prev => prev.filter(doc => doc.fileId !== fileId));
      
      return result;
      
    } catch (err) {
      setError(err.message || 'Failed to delete document');
      throw err;
    }
  }, []);

  // Edit OCR results
  const updateDocument = useCallback(async (fileId, updates) => {
    try {
      setError(null);
      
      const result = await documentService.editOCRResults(fileId, updates);
      
      // Update local state
      setDocuments(prev => 
        prev.map(doc => 
          doc.fileId === fileId ? { ...doc, ...result } : doc
        )
      );
      
      return result;
      
    } catch (err) {
      setError(err.message || 'Failed to update document');
      throw err;
    }
  }, []);

  // Restore document from recycle bin
  const restoreDocument = useCallback(async (fileId) => {
    try {
      setError(null);
      
      const result = await documentService.restoreDocument(fileId);
      
      // Refresh documents list
      await fetchDocuments();
      
      return result;
      
    } catch (err) {
      setError(err.message || 'Failed to restore document');
      throw err;
    }
  }, [fetchDocuments]);

  // Load recycle bin contents
  const loadRecycleBin = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await documentService.getRecycleBin(params);
      return data;
      
    } catch (err) {
      setError(err.message || 'Failed to load recycle bin');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Get a single document by ID
  const getDocument = useCallback(async (fileId) => {
    try {
      setLoading(true);
      setError(null);
      
      const document = await documentService.getDocument(fileId);
      return document;
      
    } catch (err) {
      setError(err.message || 'Failed to get document');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (autoLoad) {
      fetchDocuments();
    }
  }, [autoLoad, fetchDocuments]);

  return {
    documents,
    loading,
    error,
    hasMore,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    updateDocument,
    getDocument,
    restoreDocument,
    loadRecycleBin,
    formatDate: documentService.formatDate,
    getStatusColor: documentService.getStatusColor
  };
};