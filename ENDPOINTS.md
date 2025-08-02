# API Endpoints Documentation

This document provides comprehensive documentation for all available API endpoints in the OCR processing system.

## Base URL Structure
```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/long-batch/
```

---

## Processing Endpoints

### 1. Long Batch Processing
**Endpoint:** `POST /long-batch`

**Purpose:** Process large, complex files using AWS Batch for heavy computational tasks.

**Request:**
```json
{
  "fileId": "uuid-of-uploaded-file"
}
```

**Response (Success - 202 Accepted):**
```json
{
  "message": "Job submitted successfully",
  "fileId": "uuid-of-uploaded-file",
  "jobId": "aws-batch-job-id",
  "jobName": "job-name",
  "estimatedTime": "5-15 minutes",
  "status": "submitted"
}
```

**Processing Details:**
- **Time:** 5-15 minutes
- **File Size:** No limit (handles large files)
- **Architecture:** Event-driven with AWS Batch
- **Use Case:** Complex documents, large files, heavy processing

---

### 2. Short Batch Processing
**Endpoint:** `POST /short-batch`

**Purpose:** Process small, simple files quickly using AWS Lambda for fast turnaround.

**Request:**
```json
{
  "fileId": "uuid-of-uploaded-file"
}
```

**Response (Success - 202 Accepted):**
```json
{
  "message": "File queued for short batch processing",
  "fileId": "uuid-of-uploaded-file",
  "messageId": "sqs-message-id",
  "status": "queued",
  "estimatedProcessingTime": "10-30 seconds",
  "checkStatusUrl": "/processed?fileId=uuid-of-uploaded-file"
}
```

**Response (File Too Large - 400):**
```json
{
  "error": "File too large for short batch processing",
  "maxSizeMB": 10,
  "fileSizeMB": 15.2,
  "suggestion": "Please use the regular batch processing endpoint for large files"
}
```

**Processing Details:**
- **Time:** 10-30 seconds
- **File Size:** 10MB maximum
- **Architecture:** Asynchronous SQS + Lambda with short polling
- **Use Case:** Small documents, quick processing

---

## File Management Endpoints

### 3. File Upload
**Endpoint:** `POST /upload`

**Request:** Multipart form data with file

**Response:**
```json
{
  "message": "File uploaded successfully",
  "fileId": "generated-uuid",
  "fileName": "document.pdf",
  "fileSize": 1024000,
  "uploadTime": "2024-01-01T12:00:00Z"
}
```

---

### 4. Get Processed Results
**Endpoint:** `GET /processed?fileId={fileId}`

**Response:**
```json
{
  "fileId": "uuid",
  "fileName": "document.pdf",
  "processingStatus": "completed",
  "rawText": "Extracted text content...",
  "refinedText": "Cleaned and refined text...",
  "entities": [...],
  "keyPhrases": [...],
  "sentiment": {...},
  "processingTime": 25.5
}
```

---

### 5. Search Documents
**Endpoint:** `GET /search?query={search-term}&limit={number}`

**Response:**
```json
{
  "results": [
    {
      "fileId": "uuid",
      "fileName": "document.pdf",
      "relevanceScore": 0.95,
      "matchedText": "...highlighted text..."
    }
  ]
}
```

---

### 6. Edit OCR Results
**Endpoint:** `PUT /edit`

**Request:**
```json
{
  "fileId": "uuid-of-file",
  "editedText": "Manually corrected text content..."
}
```

---

### 7. Delete File
**Endpoint:** `DELETE /delete/{fileId}`

**Response:**
```json
{
  "message": "File moved to recycle bin successfully",
  "fileId": "uuid-of-file",
  "deletedAt": "2024-01-01T12:00:00Z"
}
```

---

### 8. Recycle Bin Operations
**List:** `GET /recycle-bin`
**Restore:** `POST /restore/{fileId}`

---

## Architecture Comparison

| Feature | Long Batch | Short Batch |
|---------|------------|-------------|
| **Processing Engine** | AWS Batch | AWS Lambda |
| **File Size Limit** | No limit | 10MB max |
| **Processing Time** | 5-15 minutes | 10-30 seconds |
| **Queue Type** | SQS Long Polling | SQS Short Polling |
| **Use Case** | Complex/Large files | Simple/Small files |

---

## Common Response Codes

- **200** - Success
- **202** - Accepted (processing started)
- **400** - Bad Request
- **404** - Not Found
- **500** - Internal Server Error

---

## Processing Status Values

- `uploaded` - File uploaded, not processed
- `queued` - Submitted for processing
- `processing` - Currently being processed
- `completed` - Processing finished successfully
- `failed` - Processing failed

---

## Example Usage

### Short Batch (Quick Processing)
```javascript
// 1. Upload file
const uploadResponse = await fetch('/upload', {
  method: 'POST',
  body: formData
});
const { fileId } = await uploadResponse.json();

// 2. Process with short batch
const processResponse = await fetch('/short-batch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fileId })
});

// 3. Check results after ~20 seconds
setTimeout(async () => {
  const results = await fetch(`/processed?fileId=${fileId}`);
  const data = await results.json();
  console.log('Processing completed:', data);
}, 20000);
```

### Long Batch (Complex Processing)
```javascript
// Process large/complex files
const processResponse = await fetch('/long-batch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fileId })
});

// Check periodically (every 2-3 minutes)
const checkStatus = setInterval(async () => {
  const results = await fetch(`/processed?fileId=${fileId}`);
  const data = await results.json();
  
  if (data.processingStatus === 'completed') {
    clearInterval(checkStatus);
    console.log('Processing completed:', data);
  }
}, 120000);
```