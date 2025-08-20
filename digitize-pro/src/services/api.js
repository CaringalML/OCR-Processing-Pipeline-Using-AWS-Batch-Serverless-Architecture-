import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth tokens
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const apiEndpoints = {
  // Authentication
  login: '/auth/login',
  logout: '/auth/logout',
  refresh: '/auth/refresh',

  // Documents
  documents: '/documents',
  uploadDocument: '/documents/upload',
  processDocument: (id) => `/documents/${id}/process`,
  downloadDocument: (id) => `/documents/${id}/download`,
  deleteDocument: (id) => `/documents/${id}`,

  // Collections
  collections: '/collections',
  createCollection: '/collections',
  updateCollection: (id) => `/collections/${id}`,
  deleteCollection: (id) => `/collections/${id}`,

  // Search
  search: '/search',
  advancedSearch: '/search/advanced',
  suggestions: '/search/suggestions',

  // OCR
  ocrProcess: '/ocr/process',
  ocrStatus: (jobId) => `/ocr/status/${jobId}`,
  ocrText: (documentId) => `/ocr/text/${documentId}`,

  // Upload
  uploadStatus: (uploadId) => `/upload/status/${uploadId}`,
  uploadCancel: (uploadId) => `/upload/cancel/${uploadId}`,

  // Statistics
  stats: '/stats',
  activityFeed: '/stats/activity',
  storageInfo: '/stats/storage',

  // Recycle Bin
  recycleBin: '/recycle',
  restoreItem: (id) => `/recycle/${id}/restore`,
  permanentDelete: (id) => `/recycle/${id}/permanent`,
};

// Generic API methods
export const apiMethods = {
  // GET request
  get: async (url, config = {}) => {
    try {
      const response = await api.get(url, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // POST request
  post: async (url, data = {}, config = {}) => {
    try {
      const response = await api.post(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // PUT request
  put: async (url, data = {}, config = {}) => {
    try {
      const response = await api.put(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // DELETE request
  delete: async (url, config = {}) => {
    try {
      const response = await api.delete(url, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // File upload with progress
  uploadFile: async (url, file, onProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    };

    try {
      const response = await api.post(url, formData, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};

export default api;