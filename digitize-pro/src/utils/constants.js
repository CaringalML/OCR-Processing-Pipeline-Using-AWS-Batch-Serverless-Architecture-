// Application Constants
export const APP_NAME = process.env.REACT_APP_APP_NAME || 'DigitizePro';
export const VERSION = process.env.REACT_APP_VERSION || '1.0.0';
export const ENVIRONMENT = process.env.REACT_APP_ENVIRONMENT || 'development';

// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_GATEWAY_URL || 'http://localhost:3001/api';
export const API_VERSION = process.env.REACT_APP_API_VERSION || 'v1';

// AWS Configuration
export const AWS_REGION = process.env.REACT_APP_AWS_REGION || 'us-east-1';
export const S3_BUCKET_NAME = process.env.REACT_APP_S3_BUCKET_NAME || 'digitize-pro-documents';

// Feature Flags
export const FEATURES = {
  ANALYTICS: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  DEBUG: process.env.REACT_APP_ENABLE_DEBUG === 'true',
  OCR: process.env.REACT_APP_ENABLE_OCR === 'true',
};

// Upload Configuration
export const MAX_FILE_SIZE = parseInt(process.env.REACT_APP_MAX_FILE_SIZE) || 500 * 1024 * 1024; // 500MB default
export const ALLOWED_FILE_TYPES = process.env.REACT_APP_ALLOWED_FILE_TYPES?.split(',') || ['pdf', 'tiff', 'jpg', 'jpeg', 'png'];

// Pagination
export const DEFAULT_PAGE_SIZE = parseInt(process.env.REACT_APP_DEFAULT_PAGE_SIZE) || 20;
export const MAX_PAGE_SIZE = parseInt(process.env.REACT_APP_MAX_PAGE_SIZE) || 100;

// Document Types
export const DOCUMENT_TYPES = [
  'Document',
  'Newspaper',
  'Letter',
  'Photograph',
  'Manuscript',
  'Report',
  'Book',
  'Map'
];

// Supported File Types (MIME types)
export const SUPPORTED_FILE_TYPES = [
  'application/pdf',
  'image/tiff',
  'image/jpeg',
  'image/png'
];

// Collections
export const COLLECTIONS = [
  { id: 'historical-newspapers', name: 'Historical Newspapers' },
  { id: 'university-records', name: 'University Records' },
  { id: 'manuscripts', name: 'Manuscripts' },
  { id: 'photographs', name: 'Photographs' },
  { id: 'government-documents', name: 'Government Documents' }
];

// Upload Status
export const UPLOAD_STATUS = {
  PENDING: 'pending',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

// OCR Status
export const OCR_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

// AWS S3 Storage Classes
export const S3_STORAGE_CLASSES = {
  STANDARD: 'STANDARD',
  REDUCED_REDUNDANCY: 'REDUCED_REDUNDANCY',
  STANDARD_IA: 'STANDARD_IA',
  ONEZONE_IA: 'ONEZONE_IA',
  INTELLIGENT_TIERING: 'INTELLIGENT_TIERING',
  GLACIER: 'GLACIER',
  DEEP_ARCHIVE: 'DEEP_ARCHIVE'
};

// API Endpoints (now using environment variable)
export const API_ENDPOINTS = {
  // Base URL from environment
  BASE: API_BASE_URL,
  
  // Authentication
  AUTH: {
    LOGIN: `${API_BASE_URL}/auth/login`,
    LOGOUT: `${API_BASE_URL}/auth/logout`,
    REFRESH: `${API_BASE_URL}/auth/refresh`,
  },
  
  // Documents
  DOCUMENTS: {
    LIST: `${API_BASE_URL}/documents`,
    UPLOAD: `${API_BASE_URL}/documents/upload`,
    PROCESS: (id) => `${API_BASE_URL}/documents/${id}/process`,
    DOWNLOAD: (id) => `${API_BASE_URL}/documents/${id}/download`,
    DELETE: (id) => `${API_BASE_URL}/documents/${id}`,
    UPDATE: (id) => `${API_BASE_URL}/documents/${id}`,
  },
  
  // Collections
  COLLECTIONS: {
    LIST: `${API_BASE_URL}/collections`,
    CREATE: `${API_BASE_URL}/collections`,
    UPDATE: (id) => `${API_BASE_URL}/collections/${id}`,
    DELETE: (id) => `${API_BASE_URL}/collections/${id}`,
  },
  
  // Search
  SEARCH: {
    BASIC: `${API_BASE_URL}/search`,
    ADVANCED: `${API_BASE_URL}/search/advanced`,
    SUGGESTIONS: `${API_BASE_URL}/search/suggestions`,
  },
  
  // OCR
  OCR: {
    PROCESS: `${API_BASE_URL}/ocr/process`,
    STATUS: (jobId) => `${API_BASE_URL}/ocr/status/${jobId}`,
    TEXT: (documentId) => `${API_BASE_URL}/ocr/text/${documentId}`,
  },
  
  // Upload Management
  UPLOAD: {
    STATUS: (uploadId) => `${API_BASE_URL}/upload/status/${uploadId}`,
    CANCEL: (uploadId) => `${API_BASE_URL}/upload/cancel/${uploadId}`,
  },
  
  // Statistics & Analytics
  STATS: {
    DASHBOARD: `${API_BASE_URL}/stats`,
    ACTIVITY: `${API_BASE_URL}/stats/activity`,
    STORAGE: `${API_BASE_URL}/stats/storage`,
  },
  
  // Recycle Bin
  RECYCLE: {
    LIST: `${API_BASE_URL}/recycle`,
    RESTORE: (id) => `${API_BASE_URL}/recycle/${id}/restore`,
    PERMANENT_DELETE: (id) => `${API_BASE_URL}/recycle/${id}/permanent`,
  }
};