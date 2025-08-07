# API Endpoints Documentation

This document provides comprehensive documentation for all available API endpoints in the OCR processing system with unified API architecture.

## Base URL Structure
```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/
```

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

## Get All Processed Files
**Endpoint:** `GET /processed`

**Purpose:** Retrieve ALL processed files from both short-batch (Claude) and long-batch (Textract) processing.

**Query Parameters:**
- `limit` - Number of results (default: 50)
- `fileId` - Get specific file
- `status` - Filter by status (default: 'processed')

**Examples:**
```bash
# Get all processed files
curl '/processed'

# Get specific file
curl '/processed?fileId=your-file-id'

# Get with limit
curl '/processed?limit=100'
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
curl '/search?q=electric+cars&fuzzy=true&fuzzyThreshold=80'
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

## Get Long-Batch Processed Files
**Endpoint:** `GET /long-batch/processed`

**Purpose:** Get ONLY long-batch processed files (Textract-based).

**Response:** Same structure as unified `/processed` but filtered to only show `processingType: "long-batch"`.

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

## Get Short-Batch Processed Files  
**Endpoint:** `GET /short-batch/processed`

**Purpose:** Get ONLY short-batch processed files (Claude AI-based).

**Response:** Same structure as unified `/processed` but filtered to only show `processingType: "short-batch"`.

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
const uploadResponse = await fetch('/upload', {
  method: 'POST',
  body: formData
});
const { fileId, routingDecision } = await uploadResponse.json();

// Wait based on routing decision
const waitTime = routingDecision.route === 'short-batch' ? 30000 : 300000;

setTimeout(async () => {
  // Get from unified endpoint
  const results = await fetch(`/processed?fileId=${fileId}`);
  const data = await results.json();
  console.log('Results:', data.ocrResults);
}, waitTime);
```

## 2. Forced Short-Batch Processing
```javascript
// Force short-batch processing
const uploadResponse = await fetch('/short-batch/upload', {
  method: 'POST',
  body: formData
});

const processResponse = await fetch('/short-batch/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fileId })
});

// Check short-batch results
setTimeout(async () => {
  const results = await fetch(`/short-batch/processed?fileId=${fileId}`);
  const data = await results.json();
  console.log('Claude AI Results:', data.ocrResults);
}, 30000);
```

## 3. Invoice Processing Workflow
```javascript
// Upload invoice
const invoiceResponse = await fetch('/short-batch/invoices/upload', {
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
const searchAll = await fetch('/search?q=transportation&fuzzy=true');

// Search only Claude AI processed files  
const searchShort = await fetch('/short-batch/search?q=transportation');

// Search only Textract processed files
const searchLong = await fetch('/long-batch/search?q=transportation');
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