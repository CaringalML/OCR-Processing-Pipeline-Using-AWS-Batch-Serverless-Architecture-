# API Endpoints Documentation

This document provides comprehensive documentation for all available API endpoints in the OCR processing system with unified API architecture.

## Base URL Structure
```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/v1/
```

**Current Stage:** `v1` (production deployment)

## ✅ CONFIRMED WORKING ENDPOINTS

### **Unified Batch Processing Endpoint**
**GET** `/v1/batch/processed` - ✅ **TESTED & WORKING**
- Combines files from both Claude AI (short-batch) and AWS Textract (long-batch)
- Supports `?fileId=` parameter for specific file retrieval
- Returns unified response format for all processing types

---

# API Architecture Overview

## Three-Tier Endpoint Structure

### 1. **Unified Endpoints** (Combines both batch types)
- **Purpose:** Access all processed files regardless of processing method
- **Base Path:** `/`
- **Use Case:** When you want to work with all processed documents together

### 2. **Long-Batch Endpoints** (AWS Batch + Textract)
- **Purpose:** Heavy processing for complex documents
- **Base Path:** `/long-batch/`
- **Processing:** AWS Batch → Textract → Comprehend
- **Use Case:** Large files, complex documents, detailed analysis

### 3. **Short-Batch Endpoints** (Lambda + Claude AI)  
- **Purpose:** Fast processing with Claude AI OCR
- **Base Path:** `/short-batch/`
- **Processing:** Lambda → Claude Sonnet 4 → Analysis
- **Use Case:** Quick processing, high-quality OCR, small to medium files

---

# Unified Endpoints (All Batch Types)

## Smart Upload
**Endpoint:** `POST /upload`

**Purpose:** Intelligent file upload with automatic routing based on file size and complexity.

**Request:** Multipart form data
```bash
curl -X POST '/upload' -F 'file=@document.pdf' \
  -F 'publication=Magazine' -F 'year=2024' -F 'title=Article Title'
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "fileId": "generated-uuid",
  "fileName": "document.pdf",
  "fileSize": 1024000,
  "s3Key": "smart-routed-files/uuid.pdf",
  "uploadTime": "2024-01-01T12:00:00Z",
  "routingDecision": {
    "route": "short-batch",
    "reason": "File size under 10MB, suitable for fast processing"
  }
}
```

---

## Get All Processed Files ✅ UNIFIED ENDPOINT
**Endpoint:** `GET /v1/batch/processed`

**Purpose:** Retrieve ALL processed files from both short-batch (Claude AI) and long-batch (AWS Textract) processing pipelines in a single unified response.

**Key Features:**
- ✅ **Combines both pipelines**: Returns files from short-batch AND long-batch processing
- ✅ **Automatic detection**: No need to specify which pipeline the file came from
- ✅ **Sorted by recency**: Most recently uploaded files first
- ✅ **Query parameter support**: Filter by specific fileId or limit results

---

## Edit Processed Files ✅ UNIFIED ENDPOINT
**Endpoint:** `PUT /v1/batch/processed/edit?fileId={fileId}`

**Purpose:** Edit OCR results for files from BOTH short-batch (Claude AI) and long-batch (AWS Textract) processing pipelines using a single unified endpoint.

**Key Features:**
- ✅ **Works with both pipelines**: Edit files regardless of processing method
- ✅ **Partial updates**: Update only the fields you want to change
- ✅ **Edit history**: Automatically tracks all changes with timestamps
- ✅ **Metadata support**: Update publication info, titles, authors, etc.

**Request Body:**
```json
{
  "refinedText": "Updated text content...",
  "formattedText": "Updated formatted text...",
  "metadata": {
    "title": "New Title",
    "author": "New Author",
    "description": "Updated description"
  }
}
```

**Example:**
```bash
# Edit refined text only
curl -X PUT "https://your-api.execute-api.region.amazonaws.com/v1/batch/processed/edit?fileId=your-file-id" \
  -H "Content-Type: application/json" \
  -d '{"refinedText": "Transport for Tomorrow - EDITED VERSION..."}'

# Edit multiple fields
curl -X PUT "https://your-api.execute-api.region.amazonaws.com/v1/batch/processed/edit?fileId=your-file-id" \
  -H "Content-Type: application/json" \
  -d '{
    "refinedText": "Updated text...",
    "metadata": {
      "title": "New Document Title",
      "author": "Updated Author"
    }
  }'
```

**Response:**
```json
{
  "fileId": "your-file-id",
  "refinedText": "Transport for Tomorrow - EDITED VERSION...",
  "formattedText": "Original formatted text...",
  "userEdited": true,
  "lastEdited": "2025-08-12T02:21:17.580819+00:00",
  "editHistory": [
    {
      "edited_at": "2025-08-12T02:21:17.580789+00:00",
      "edited_fields": ["refined_text"],
      "previous_refined_text": "Original text content..."
    }
  ],
  "message": "OCR results updated successfully"
}
```

**Query Parameters:**
- `fileId` - Get specific file (works for files from both pipelines)
- `limit` - Number of results (default: 50, applied after combining both pipelines)
- `status` - Filter by status (default: 'processed')

**Examples:**
```bash
# Get all processed files from both pipelines
curl 'https://your-api-gateway.execute-api.region.amazonaws.com/v1/batch/processed'

# Get specific file (works for both short-batch and long-batch files)
curl 'https://your-api-gateway.execute-api.region.amazonaws.com/v1/batch/processed?fileId=your-file-id'

# Get limited results (e.g., last 20 files from both pipelines)
curl 'https://your-api-gateway.execute-api.region.amazonaws.com/v1/batch/processed?limit=20'
```

**Response:**
```json
{
  "files": [
    {
      "fileId": "uuid",
      "fileName": "document.pdf",
      "uploadTimestamp": "2024-01-01T12:00:00Z",
      "processingStatus": "processed|completed",
      "fileSize": 1024000,
      "contentType": "application/pdf",
      "cloudFrontUrl": "https://cdn.example.com/files/uuid.pdf",
      "metadata": {
        "publication": "Magazine",
        "year": "2024",
        "title": "Article Title",
        "author": "John Doe",
        "description": "Article description",
        "tags": ["tech", "innovation"]
      },
      "ocrResults": {
        "formattedText": "Extracted text content...",
        "refinedText": "Grammar-corrected text...",
        "processingModel": "claude-sonnet-4-20250514|aws-textract",
        "processingType": "short-batch|long-batch",
        "processingDuration": "5.4s|2.1m",
        "processingCost": 0.025,
        "processedAt": "2024-01-01T12:01:30Z"
      },
      "textAnalysis": {
        "total_words": 1250,
        "total_paragraphs": 8,
        "total_sentences": 45,
        "processing_notes": "Dual-pass Claude processing: OCR + refinement"
      }
    }
  ],
  "count": 25,
  "hasMore": true
}
```

---

## Search All Documents
**Endpoint:** `GET /search`

**Purpose:** Search across ALL processed documents from both batch types.

**Query Parameters:**
- `q` - Search query (required)
- `limit` - Results limit (default: 50)
- `fuzzy` - Enable fuzzy search (true/false)
- `fuzzyThreshold` - Fuzzy match threshold (0-100)

**Example:**
```bash
curl '/v1/search?q=electric+cars&fuzzy=true&fuzzyThreshold=80'
```

---

## Other Unified Operations
- `POST /edit` - Edit OCR results
- `DELETE /delete/{fileId}` - Delete file (moves to recycle bin)
- `GET /recycle-bin` - List deleted files
- `POST /restore/{fileId}` - Restore from recycle bin

---

# Long-Batch Endpoints (AWS Batch Processing)

## Upload for Long-Batch
**Endpoint:** `POST /long-batch/upload`

**Purpose:** Force upload to long-batch processing (bypasses smart routing).

---

## Process Long-Batch
**Endpoint:** `POST /long-batch/process`

**Purpose:** Submit file for heavy processing using AWS Batch + Textract.

**Request:**
```json
{
  "fileId": "uuid-of-uploaded-file"
}
```

**Response:**
```json
{
  "message": "Job submitted successfully",
  "fileId": "uuid-of-uploaded-file",
  "jobId": "aws-batch-job-id",
  "jobName": "textract-job-uuid",
  "estimatedTime": "5-15 minutes",
  "status": "submitted"
}
```

---


---

## Long-Batch Operations
- `GET /long-batch/search` - Search only long-batch documents
- `PUT /long-batch/edit` - Edit long-batch OCR results  
- `DELETE /long-batch/delete/{fileId}` - Delete long-batch file
- `GET /long-batch/recycle-bin` - Long-batch recycle bin
- `POST /long-batch/restore/{fileId}` - Restore long-batch file

---

# Short-Batch Endpoints (Claude AI Processing)

## Upload for Short-Batch
**Endpoint:** `POST /short-batch/upload`

**Purpose:** Force upload to short-batch processing (bypasses smart routing).

---

## Process Short-Batch
**Endpoint:** `POST /short-batch/process`

**Purpose:** Submit file for fast processing using Claude AI OCR.

**Request:**
```json
{
  "fileId": "uuid-of-uploaded-file"
}
```

**Response:**
```json
{
  "message": "File queued for short batch processing",
  "fileId": "uuid-of-uploaded-file",
  "messageId": "sqs-message-id",
  "status": "queued",
  "estimatedProcessingTime": "10-30 seconds",
  "checkStatusUrl": "/short-batch/processed?fileId=uuid-of-uploaded-file"
}
```

---


---

## Short-Batch Operations
- `GET /short-batch/search` - Search only short-batch documents
- `PUT /short-batch/edit` - Edit short-batch OCR results
- `DELETE /short-batch/delete/{fileId}` - Delete short-batch file
- `GET /short-batch/recycle-bin` - Short-batch recycle bin  
- `POST /short-batch/restore/{fileId}` - Restore short-batch file

---

# Invoice Processing (Specialized Short-Batch)

## Invoice Upload
**Endpoint:** `POST /short-batch/invoices/upload`

**Purpose:** Specialized invoice processing with 60+ field extraction.

**Features:**
- Claude Sonnet 4 for maximum OCR accuracy
- 60+ structured fields extracted automatically
- Business info, client details, financial breakdown
- Line items with categories and pricing
- Payment terms and banking information

---

## Get Processed Invoices
**Endpoint:** `GET /short-batch/invoices/processed`

**Purpose:** Get processed invoices with specialized invoice analysis.

**Query Parameters:**
- `vendorName` - Filter by vendor
- `invoiceNumber` - Filter by invoice number  
- `dateRange` - Filter by date range
- `minAmount`/`maxAmount` - Filter by amount

---

# Processing Architecture Comparison

| Feature | Unified | Long-Batch | Short-Batch | Invoice |
|---------|---------|------------|-------------|---------|
| **Engine** | Both | AWS Batch + Textract | Lambda + Claude | Lambda + Claude |
| **File Size** | Any | No limit | 10MB max | 10MB max |
| **Time** | Varies | 5-15 min | 10-30 sec | 10-30 sec |
| **OCR Quality** | Both | Good | Excellent | Excellent |
| **Structured Data** | Both | Basic | Advanced | 60+ fields |
| **Use Case** | General | Complex docs | Fast processing | Invoice analysis |

---

# Response Status Codes

- **200** - Success
- **202** - Accepted (processing started)  
- **400** - Bad Request
- **404** - Not Found
- **500** - Internal Server Error

---

# Processing Status Values

- `uploaded` - File uploaded, awaiting processing
- `queued` - Submitted for processing
- `processing` - Currently being processed
- `downloading` - Downloading from S3 
- `processing_ocr` - OCR extraction in progress
- `assessing_quality` - Text quality assessment
- `refining_text` - Grammar refinement (Claude)
- `saving_results` - Saving to database
- `processed` - Long-batch completed successfully
- `completed` - Short-batch completed successfully  
- `failed` - Processing failed

---

# Example Usage Patterns

## 1. Smart Upload + Unified Retrieval
```javascript
// Upload with smart routing
const uploadResponse = await fetch('/v1/upload', {
  method: 'POST',
  body: formData
});
const { fileId, routingDecision } = await uploadResponse.json();

// Wait based on routing decision
const waitTime = routingDecision.route === 'short-batch' ? 30000 : 300000;

setTimeout(async () => {
  // Get from unified endpoint
  const results = await fetch(`/v1/batch/processed?fileId=${fileId}`);
  const data = await results.json();
  console.log('Results:', data.ocrResults);
}, waitTime);
```

## 2. Forced Short-Batch Processing
```javascript
// Force short-batch processing
const uploadResponse = await fetch('/v1/short-batch/upload', {
  method: 'POST',
  body: formData
});

const processResponse = await fetch('/v1/short-batch/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fileId })
});

// Check results using unified endpoint
setTimeout(async () => {
  const results = await fetch(`/v1/batch/processed?fileId=${fileId}`);
  const data = await results.json();
  console.log('Claude AI Results:', data.ocrResults);
}, 30000);
```

## 3. Invoice Processing Workflow
```javascript
// Upload invoice
const invoiceResponse = await fetch('/v1/short-batch/invoices/upload', {
  method: 'POST',
  body: invoiceFormData
});

// Get structured invoice data
setTimeout(async () => {
  const results = await fetch(`/short-batch/invoices/processed?fileId=${fileId}`);
  const data = await results.json();
  console.log('Invoice Data:', data.invoiceAnalysis);
  console.log('60+ Fields:', data.ocrResults);
}, 30000);
```

## 4. Search Across All Documents
```javascript
// Search all processed files
const searchAll = await fetch('/v1/search?q=transportation&fuzzy=true');

// Get all processed files
const allFiles = await fetch('/v1/batch/processed');

// Get specific processed file
const specificFile = await fetch('/v1/batch/processed?fileId=your-file-id');
```

---

# Key Benefits

## Unified Endpoints
✅ **Single source of truth** for all processed documents  
✅ **Consistent response format** regardless of processing method  
✅ **Simplified client integration** - one endpoint for all results  

## Smart Routing  
✅ **Automatic optimization** based on file characteristics  
✅ **Cost efficiency** - right processing method for each file  
✅ **Performance optimization** - fast processing when possible  

## Specialized Processing
✅ **Claude AI excellence** for high-quality OCR  
✅ **AWS Batch power** for complex document analysis  
✅ **Invoice specialization** with 60+ extracted fields  

## Operational Excellence
✅ **Comprehensive monitoring** with detailed processing metrics  
✅ **Soft delete** with 30-day recycle bin retention  
✅ **Advanced search** with fuzzy matching and filtering  
✅ **Cost tracking** with per-document processing costs