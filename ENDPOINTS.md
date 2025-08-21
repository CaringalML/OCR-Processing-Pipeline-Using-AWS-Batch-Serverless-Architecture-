# API Endpoints Documentation

This document provides comprehensive documentation for all available API endpoints in the OCR processing system with unified API architecture.

**Author:** Martin Lawrence Caringal  
**Contact:** [lawrencecaringal5@gmail.com](mailto:lawrencecaringal5@gmail.com)  
**Last Updated:** August 20, 2025

---

## 🧪 Postman Testing Guide

### **Quick Setup**
1. **Import Environment Variables**
```json
{
  "name": "OCR API Environment",
  "values": [
    {
      "key": "base_url",
      "value": "https://fqyxavdri0.execute-api.ap-southeast-2.amazonaws.com/v1",
      "enabled": true
    },
    {
      "key": "file_id",
      "value": "your-file-id-here",
      "enabled": true
    }
  ]
}
```

2. **Set Global Headers**
```json
{
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

### **📁 Postman Collection Structure**
```
📂 OCR Document Processing API
├── 📁 1. File Upload & Processing
│   ├── POST Smart Upload (Auto-routing)
│   ├── POST Force Short-batch Upload
│   └── POST Force Long-batch Upload
├── 📁 2. Document Retrieval
│   ├── GET All Processed Documents
│   └── GET Specific Document by ID
├── 📁 3. Intelligent Search
│   ├── GET Basic Search
│   ├── GET Academic Search with Filters
│   ├── GET Fuzzy Search
│   └── GET Multi-language Search
├── 📁 4. OCR Result Finalization
│   ├── POST Finalize OCR Results
│   ├── GET All Finalized Results  
│   ├── GET Specific Finalized Result
│   └── PUT Edit Finalized Document
├── 📁 5. File Management
│   ├── DELETE Soft Delete (Recycle Bin)
│   ├── GET View Recycle Bin
│   ├── POST Restore from Recycle Bin
│   └── DELETE Permanent Delete
└── 📁 6. Invoice Processing
    ├── POST Upload Invoice
    └── GET Processed Invoice Data
```

---

## Base URL Structure
```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/v1/
```

**Current Stage:** `v1` (production deployment)

## 🚀 **Key Features**
- 🤖 **Smart Document Processing**: Automatic routing based on file size and complexity
- 🌍 **Global Timezone Support**: ISO 8601 date format for worldwide compatibility  
- 📁 **Advanced File Management**: Complete lifecycle with recycle bin and restoration
- 🔍 **Unified Search**: Search across all documents regardless of processing method
- 📊 **Rich Metadata**: Publication details, OCR quality metrics, and processing insights
- 🎯 **OCR Result Finalization**: Choose between formattedText/refinedText with optional editing
- 📋 **Complete Audit Trail**: Track finalization decisions and changes

## ✅ CONFIRMED WORKING ENDPOINTS

### **Unified Batch Processing Endpoint**
**GET** `/v1/batch/processed` - ✅ **TESTED & WORKING**
- Combines files from both Claude AI (short-batch) and AWS Textract (long-batch)
- Supports `?fileId=` parameter for specific file retrieval
- Returns unified response format for all processing types

---

# API Architecture Overview

## Single Table Architecture with Smart Routing

### Database Design
- **Single DynamoDB Table:** All OCR results stored in `processing_results` table
- **Unified Data Access:** All functionality works across all processing types
- **Consistent Schema:** Same data structure regardless of processing pipeline

## Three-Tier Endpoint Structure

### 1. **Unified Endpoints** (Combines both batch types)
- **Purpose:** Access all processed files regardless of processing method
- **Base Path:** `/`
- **Database:** Single `processing_results` table
- **Use Case:** When you want to work with all processed documents together

### 2. **Long-Batch Endpoints** (AWS Batch + Textract)
- **Purpose:** Heavy processing for complex documents
- **Base Path:** `/long-batch/`
- **Processing:** AWS Batch → Textract → Comprehend
- **Storage:** Results saved to unified `processing_results` table
- **Use Case:** Large files, complex documents, detailed analysis

### 3. **Short-Batch Endpoints** (Lambda + Claude AI)  
- **Purpose:** Fast processing with Claude AI OCR
- **Base Path:** `/short-batch/`
- **Processing:** Lambda → Claude Sonnet 4 → Analysis
- **Storage:** Results saved to unified `processing_results` table
- **Use Case:** Quick processing, high-quality OCR, small to medium files

---

# Date Format Standard

## ISO 8601 Format (Global Best Practice)
All dates in API responses use **ISO 8601 format** for maximum compatibility with global users:
```
"2025-08-16T05:39:00.000000+00:00"
```

### Client-Side Date Conversion
Frontend applications can display dates in user's local timezone:
```javascript
// Convert to user's local timezone
const formatLocalDate = (isoDate) => {
    const date = new Date(isoDate);
    return date.toLocaleString('en-NZ', {
        day: 'numeric', month: 'long', year: 'numeric',
        hour: 'numeric', minute: '2-digit', hour12: true,
        timeZoneName: 'short'
    });
};

// Example output:
// NZ Users: "16 August 2025, 5:39 PM NZST"
// US Users: "16 August 2025, 1:39 AM EDT"
// UK Users: "16 August 2025, 6:39 AM BST"
```

---

# Unified Endpoints (All Batch Types)

## Smart Upload 📤
**Endpoint:** `POST /v1/upload`

**Purpose:** Intelligent file upload with automatic routing based on file size and complexity.

**Note:** The `/v1/batch/upload` endpoint is planned but not yet implemented. Currently use `/v1/upload`.

### **🧪 Postman Setup**
```
Method: POST
URL: {{base_url}}/upload
Headers:
  Content-Type: multipart/form-data (auto-set by Postman)
```

### **📋 Form Data Parameters**
```
file: [Select File] (PDF, JPG, PNG, etc.)
publication: The Morning Chronicle
date: 2025
title: Your Document Title
author: Dr. Jane Smith
description: Document description
page: 1
tags: research,AI,technology
collection: Academic Papers
document_type: Research Paper
priority: normal
```

### **📝 Postman Pre-request Script**
```javascript
// Auto-generate metadata for testing
pm.globals.set("timestamp", new Date().toISOString());
pm.globals.set("test_title", "Test Document " + new Date().getTime());
```

### **✅ Postman Tests**
```javascript
pm.test("Upload successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains file ID", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.files[0]).to.have.property('file_id');
    pm.globals.set("file_id", jsonData.files[0].file_id);
});

pm.test("Smart routing decision made", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.files[0].routing).to.have.property('decision');
});
```

### **🔧 cURL Example**
```bash
curl -X POST '{{base_url}}/upload' \
  -F 'file=@document.pdf' \
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

## Get All Processed Files 📄 ✅ UNIFIED ENDPOINT
**Endpoint:** `GET /v1/batch/processed`

**Purpose:** Retrieve ALL processed files from both short-batch (Claude AI) and long-batch (AWS Textract) processing pipelines in a single unified response.

**Key Features:**
- ✅ **Combines both pipelines**: Returns files from short-batch AND long-batch processing
- ✅ **Automatic detection**: No need to specify which pipeline the file came from
- ✅ **Sorted by recency**: Most recently uploaded files first
- ✅ **Query parameter support**: Filter by specific fileId or limit results

### **🧪 Postman Setup**
```
Method: GET
URL: {{base_url}}/batch/processed
Headers:
  Accept: application/json
```

### **📋 Query Parameters**
```
fileId: [Optional] Specific file ID to retrieve
limit: [Optional] Number of results (default: 50, max: 100)
status: [Optional] Filter by processing status (default: 'processed')
```

### **📝 Postman Examples**

#### **1. Get All Processed Files**
```
URL: {{base_url}}/batch/processed
```

#### **2. Get Specific File**
```
URL: {{base_url}}/batch/processed?fileId={{file_id}}
```

#### **3. Get Limited Results**
```
URL: {{base_url}}/batch/processed?limit=10
```

### **✅ Postman Tests**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains files array", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('files');
    pm.expect(jsonData.files).to.be.an('array');
});

pm.test("Files have required properties", function () {
    const jsonData = pm.response.json();
    if (jsonData.files.length > 0) {
        const file = jsonData.files[0];
        pm.expect(file).to.have.property('fileId');
        pm.expect(file).to.have.property('fileName');
        pm.expect(file).to.have.property('cloudFrontUrl');
        pm.expect(file).to.have.property('ocrResults');
    }
});

pm.test("Save first file ID for subsequent tests", function () {
    const jsonData = pm.response.json();
    if (jsonData.files.length > 0) {
        pm.globals.set("test_file_id", jsonData.files[0].fileId);
    }
});
```

---
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

## Academic Document Search (Google Scholar Style) ✅ **FULLY FUNCTIONAL**
**Endpoint:** `GET /batch/search` ✅ **INTELLIGENT ACADEMIC SEARCH ENGINE**

**Purpose:** Advanced academic search across ALL processed documents with Google Scholar-like functionality, intelligent fuzzy matching, and auto-fallback capabilities.

**🧠 Intelligent Search Features:**
- **Smart Auto-Fuzzy**: Automatically enables fuzzy search when no exact matches found
- **Contextual Snippets**: Shows relevant text portions with highlighted matches
- **Academic Relevance Scoring**: Prioritizes title/author/publication matches
- **Multi-language Support**: Searches across English, Filipino, and other languages
- **Flexible Thresholds**: Optimized 70% default threshold for better user experience

**Query Parameters:**
- `q` - Search query in title, abstract, or full text (required)
- `author` - Author name filter (works with fuzzy search)
- `publication` - Publication/journal name filter  
- `as_ylo` - Year range start (e.g., "2020")
- `as_yhi` - Year range end (e.g., "2025")
- `collection` - Filter by document collection (e.g., "Academic Papers")
- `document_type` - Filter by document type (e.g., "Research Paper")
- `scisbd` - Sort by: "relevance" (default) or "date"
- `num` - Number of results (default: 20, max: 100)
- `fuzzy` - Enable fuzzy search explicitly (true/false, auto-enabled when needed)
- `fuzzyThreshold` - Fuzzy match threshold (0-100, default: 70)

### **🧪 Postman Setup**
```
Method: GET
URL: {{base_url}}/batch/search
Headers:
  Accept: application/json
```

### **📋 Query Parameters**
```
q: [Required] Search query
author: [Optional] Author name filter
publication: [Optional] Publication/journal filter
as_ylo: [Optional] Year range start (e.g., "2020")
as_yhi: [Optional] Year range end (e.g., "2025")
collection: [Optional] Document collection filter
document_type: [Optional] Document type filter
scisbd: [Optional] Sort by "relevance" or "date"
num: [Optional] Number of results (default: 20, max: 100)
fuzzy: [Optional] Enable fuzzy search (true/false)
fuzzyThreshold: [Optional] Fuzzy threshold (0-100, default: 70)
```

### **📝 Postman Examples Collection**

#### **1. Basic Auto-Fuzzy Search**
```
URL: {{base_url}}/batch/search?q=electric+vehicles
Expected: Finds "electric cars" with fuzzy score ~73%
```

#### **2. Academic Search with Filters**
```
URL: {{base_url}}/batch/search?q=transport&publication=Chronicle&as_ylo=1920&as_yhi=1930
Expected: 3 results with academic relevance scoring
```

#### **3. Poetry/Literature Search**
```
URL: {{base_url}}/batch/search?q=life+poem&author=Van+Dyke
Expected: Finds Henry Van Dyke poetry content
```

#### **4. Explicit Fuzzy Search**
```
URL: {{base_url}}/batch/search?q=transportation&fuzzy=true&fuzzyThreshold=75
Expected: Fuzzy matches for transport-related content
```

#### **5. Phrase Pattern Matching**
```
URL: {{base_url}}/batch/search?q=happy+heart+pays+toll+Youth+Age
Expected: Exact phrase patterns with contextual snippets
```

#### **6. Multi-language Content**
```
URL: {{base_url}}/batch/search?q=dianapichler
Expected: Finds Filipino poetry attribution
```

### **✅ Postman Tests**
```javascript
pm.test("Search successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has search structure", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('success', true);
    pm.expect(jsonData).to.have.property('results');
    pm.expect(jsonData).to.have.property('searchInfo');
});

pm.test("Search info contains intelligence data", function () {
    const jsonData = pm.response.json();
    const searchInfo = jsonData.searchInfo;
    pm.expect(searchInfo).to.have.property('fuzzySearchUsed');
    pm.expect(searchInfo).to.have.property('totalScanned');
    pm.expect(searchInfo).to.have.property('autoFuzzyTriggered');
});

pm.test("Results have academic structure", function () {
    const jsonData = pm.response.json();
    if (jsonData.results.length > 0) {
        const result = jsonData.results[0];
        pm.expect(result).to.have.property('title');
        pm.expect(result).to.have.property('authors');
        pm.expect(result).to.have.property('fileUrl');
        pm.expect(result).to.have.property('ocrResults');
        
        // Test fuzzy search results
        if (jsonData.searchInfo.fuzzySearchUsed) {
            pm.expect(result).to.have.property('fuzzyScore');
            pm.expect(result).to.have.property('matchField');
            pm.expect(result.fuzzyScore).to.be.above(0);
        }
    }
});

pm.test("Fuzzy score validation", function () {
    const jsonData = pm.response.json();
    if (jsonData.results.length > 0 && jsonData.searchInfo.fuzzySearchUsed) {
        jsonData.results.forEach(result => {
            if (result.fuzzyScore) {
                pm.expect(result.fuzzyScore).to.be.within(0, 100);
            }
        });
    }
});
```

### **🔧 cURL Examples**
```bash
# Basic search with auto-fuzzy fallback
curl '{{base_url}}/batch/search?q=electric+vehicles'

# Academic filtering with year range
curl '{{base_url}}/batch/search?q=climate&publication=Chronicle&as_ylo=1920&as_yhi=1930'

# Explicit fuzzy search with custom threshold
curl '{{base_url}}/batch/search?q=transportation&fuzzy=true&fuzzyThreshold=75'
```

**📊 Response Features:**
- **Fuzzy Score**: Shows similarity percentage for fuzzy matches
- **Match Field**: Indicates where match was found (text, title, author, etc.)
- **Smart Snippets**: Contextual text excerpts around matches
- **Academic Metadata**: Full publication details, authors, years
- **CloudFront URLs**: Direct document access links
- **Search Intelligence**: Shows if auto-fuzzy was triggered


---

# 🎯 OCR Result Finalization

The finalization system allows users to choose their preferred OCR version (formattedText or refinedText) and optionally edit it before locking it as the final result. All finalized results are stored in a separate table with complete audit trails.

## Finalize OCR Results 🎯
**Endpoint:** `POST /batch/processed/finalize/{fileId}`

**Purpose:** Choose between formattedText/refinedText with optional editing and save as finalized result.

### **🧪 Postman Setup**
```
Method: POST
URL: {{base_url}}/batch/processed/finalize/{{file_id}}
Headers:
  Content-Type: application/json
  Accept: application/json
```

### **Request Body Options**

#### 1. **Simple Finalization (Choose without editing)**
```json
{
    "textSource": "formatted"
}
```

#### 2. **Finalization with Editing**
```json
{
    "textSource": "refined",
    "editedText": "This is my edited version of the refined text with corrections and improvements.",
    "notes": "Fixed OCR errors and improved formatting"
}
```

### **✅ Postman Tests**
```javascript
pm.test("Finalization successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains finalization details", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('fileId');
    pm.expect(jsonData).to.have.property('finalizedTimestamp');
    pm.expect(jsonData).to.have.property('textSource');
    pm.expect(jsonData).to.have.property('wasEdited');
    pm.expect(jsonData).to.have.property('message');
});

pm.test("Text source matches request", function () {
    const jsonData = pm.response.json();
    const requestData = JSON.parse(pm.request.body.raw);
    pm.expect(jsonData.textSource).to.eql(requestData.textSource);
});
```

**Response (Simple Finalization):**
```json
{
    "fileId": "abc123-def456",
    "finalizedTimestamp": "2025-08-18T10:30:00Z",
    "textSource": "formatted",
    "wasEdited": false,
    "message": "OCR results finalized successfully using formatted text",
    "finalizedTextPreview": "First 500 characters of finalized text..."
}
```

**Response (With Editing):**
```json
{
    "fileId": "abc123-def456",
    "finalizedTimestamp": "2025-08-18T10:30:00Z", 
    "textSource": "refined",
    "wasEdited": true,
    "message": "OCR results finalized successfully using edited refined text",
    "finalizedTextPreview": "Your edited text first 500 characters..."
}
```

---

## Get All Finalized Results 📋
**Endpoint:** `GET /batch/processed?finalized=true`

**Purpose:** Retrieve all finalized OCR results with audit trail information.

### **🧪 Postman Setup**
```
Method: GET
URL: {{base_url}}/batch/processed?finalized=true
Headers:
  Accept: application/json
```

### **✅ Postman Tests**
```javascript
pm.test("Finalized results retrieved", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains finalized files", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('files');
    pm.expect(jsonData).to.have.property('count');
    
    if (jsonData.files.length > 0) {
        pm.expect(jsonData.files[0]).to.have.property('finalizedResults');
        pm.expect(jsonData.files[0].processingStatus).to.eql('finalized');
    }
});
```

**Response:**
```json
{
    "files": [
        {
            "fileId": "abc123",
            "fileName": "document.pdf",
            "uploadTimestamp": "2025-08-18T08:00:00Z",
            "finalizedTimestamp": "2025-08-18T10:30:00Z",
            "processingStatus": "finalized",
            "metadata": { "...": "..." },
            "finalizedResults": {
                "finalizedText": "The final locked version of the text",
                "textSource": "formatted",
                "wasEditedBeforeFinalization": true
            }
        }
    ],
    "count": 1,
    "hasMore": false
}
```

---

## Get Specific Finalized Result 📄
**Endpoint:** `GET /batch/processed?fileId={fileId}&finalized=true`

**Purpose:** Get finalized version of a specific document with complete audit trail.

### **🧪 Postman Setup**
```
Method: GET
URL: {{base_url}}/batch/processed?fileId={{file_id}}&finalized=true
Headers:
  Accept: application/json
```

### **Key Features of Finalization**
- ✅ **User Choice**: Select between formattedText or refinedText as the base
- ✅ **Optional Editing**: Edit the selected text before finalizing
- ✅ **Original Preservation**: Both original versions are always preserved
- ✅ **Audit Trail**: Complete tracking of what was chosen, when, and by whom
- ✅ **Post-Finalization Editing**: Edit finalized documents with complete audit trail
- ✅ **Edit Detection**: System tracks whether the final text was edited vs used as-is

---

# 📝 Finalized Document Editing

## Edit Finalized Document ✏️
**Endpoint:** `PUT /finalized/edit/{fileId}`

**Purpose:** Edit already finalized documents while maintaining complete audit trail and version history.

### **🧪 Postman Setup**
```
Method: PUT
URL: {{base_url}}/finalized/edit/{{file_id}}
Headers:
  Content-Type: application/json
  Accept: application/json
```

### **Request Body**
```json
{
    "finalizedText": "LIFE by Henry Van Dyke\n\nLet me but live my life from year to year,\nWith forward face and unreluctant soul;\nNot hurrying to, nor turning from the goal;\nNot mourning for the things that disappear\nIn the dim past, nor holding back in fear\nFrom what the future veils; but with a whole\nAnd happy heart, that pays its toll\nTo Youth and Age, and travels on with cheer.\n\n[Corrected formatting and added proper line breaks]",
    "editReason": "Fixed formatting and added proper line breaks for better readability"
}
```

### **Request Parameters**
- **`finalizedText`** *(required)*: The new finalized text content
- **`editReason`** *(required)*: Reason for making the edit
- **`preserveHistory`** *(optional)*: Keep edit history (defaults to true)

### **✅ Postman Tests**
```javascript
pm.test("Edit successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains edit details", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('fileId');
    pm.expect(jsonData).to.have.property('editTimestamp');
    pm.expect(jsonData).to.have.property('editCount');
    pm.expect(jsonData).to.have.property('message');
});

pm.test("Edit count incremented", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.editCount).to.be.above(0);
});
```

**Response:**
```json
{
    "message": "Document edited successfully",
    "fileId": "368bef8b-f777-4577-983e-f1858a4d4a25",
    "editTimestamp": "2025-08-19T12:30:45.123456+00:00",
    "editCount": 1,
    "textLengthChange": 85,
    "preservedHistory": true,
    "editedTextPreview": "LIFE by Henry Van Dyke\n\nLet me but live my life from year to year..."
}
```

### **Error Responses**

**400 - Missing Required Fields:**
```json
{
    "error": "Bad Request",
    "message": "finalizedText is required"
}
```

**404 - Document Not Found:**
```json
{
    "error": "Not Found", 
    "message": "No finalized document found for file ID: invalid-id"
}
```

### **Key Features of Finalized Document Editing**
- ✅ **Complete Audit Trail**: Every edit is logged with timestamp, user, and reason
- ✅ **Version History**: Previous versions are preserved in edit history
- ✅ **Required Justification**: Edit reason is mandatory for accountability
- ✅ **Real-time Updates**: Changes are immediately reflected in the system
- ✅ **Edit Tracking**: System maintains count of total edits made
- ✅ **Text Change Analysis**: Tracks length changes and content modifications

---

# File Management & Recycle Bin

## Delete File (Soft Delete) 🗑️
**Endpoint:** `DELETE /batch/delete/{fileId}`

**Purpose:** Moves file to recycle bin with 30-day retention period.

### **🧪 Postman Setup**
```
Method: DELETE
URL: {{base_url}}/batch/delete/{{test_file_id}}
Headers:
  Accept: application/json
```

### **✅ Postman Tests**
```javascript
pm.test("Delete successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains deletion info", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('message');
    pm.expect(jsonData).to.have.property('deletedAt');
    pm.expect(jsonData).to.have.property('willBeDeletedAt');
    pm.expect(jsonData).to.have.property('recycleBinRetentionDays', 30);
});
```

**Response:**
```json
{
    "message": "File xyz moved to recycle bin",
    "fileId": "xyz",
    "fileName": "document.pdf",
    "deletedAt": "2025-08-16T05:39:00.000000+00:00",
    "willBeDeletedAt": "2025-09-15T05:39:00.000000+00:00",
    "recycleBinRetentionDays": 30
}
```

---

## View Recycle Bin 📋
**Endpoint:** `GET /batch/recycle-bin`

**Purpose:** List all deleted files with expiry information and complete metadata.

### **🧪 Postman Setup**
```
Method: GET
URL: {{base_url}}/batch/recycle-bin
Headers:
  Accept: application/json
```

### **📋 Query Parameters**
```
limit: [Optional] Number of items (default: 50, max: 100)
fileId: [Optional] Get specific deleted file
lastKey: [Optional] Pagination token
```

### **📝 Postman Examples**

#### **1. View All Deleted Files**
```
URL: {{base_url}}/batch/recycle-bin
```

#### **2. View Specific Deleted File**
```
URL: {{base_url}}/batch/recycle-bin?fileId={{test_file_id}}
```

#### **3. Limited Results**
```
URL: {{base_url}}/batch/recycle-bin?limit=10
```

### **✅ Postman Tests**
```javascript
pm.test("Recycle bin retrieved", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has recycle bin structure", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('items');
    pm.expect(jsonData).to.have.property('count');
    pm.expect(jsonData.items).to.be.an('array');
});

pm.test("Deleted items have expiry info", function () {
    const jsonData = pm.response.json();
    if (jsonData.items.length > 0) {
        const item = jsonData.items[0];
        pm.expect(item).to.have.property('deletedAt');
        pm.expect(item).to.have.property('expiresAt');
        pm.expect(item).to.have.property('daysRemaining');
        pm.expect(item.daysRemaining).to.be.above(0);
    }
});
```

**Response:**
```json
{
    "items": [
        {
            "fileId": "xyz",
            "deletedAt": "2025-08-16T05:39:00.000000+00:00",
            "expiresAt": "2025-09-15T05:39:00.000000+00:00",
            "daysRemaining": 29,
            "deletedBy": "192.168.1.1",
            "metadata": {
                "filename": "document.pdf",
                "filesize": 194423,
                "mimeType": "application/pdf",
                "processingStatus": "completed",
                "uploadedAt": "2025-08-15T15:30:00.000000+00:00",
                "title": "Research Paper",
                "author": "Dr. Smith",
                "publication": "Nature Journal",
                "year": "2024",
                "description": "Climate research findings",
                "page": "15-23",
                "tags": ["climate", "research", "environment"]
            },
            "hasOcrResults": true,
            "ocrSummary": {
                "textLength": 1340,
                "hasFormattedText": true,
                "userEdited": false
            }
        }
    ],
    "count": 1,
    "hasMore": false
}
```

---

## Restore File ♻️
**Endpoint:** `POST /batch/restore/{fileId}`

**Purpose:** Restore file from recycle bin back to active state.

### **🧪 Postman Setup**
```
Method: POST
URL: {{base_url}}/batch/restore/{{test_file_id}}
Headers:
  Accept: application/json
```

### **✅ Postman Tests**
```javascript
pm.test("Restore successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains restore info", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('message');
    pm.expect(jsonData).to.have.property('restoredAt');
    pm.expect(jsonData).to.have.property('wasDeletedAt');
    pm.expect(jsonData).to.have.property('processingStatus');
});
```

**Response:**
```json
{
    "message": "File xyz restored successfully",
    "fileId": "xyz",
    "fileName": "document.pdf",
    "restoredAt": "2025-08-16T05:45:00.000000+00:00",
    "wasDeletedAt": "2025-08-16T05:39:00.000000+00:00",
    "processingStatus": "completed"
}
```

---

## Permanent Delete ⚠️
**Endpoint:** `DELETE /batch/delete/{fileId}?permanent=true`

**Purpose:** Permanently delete file (bypasses recycle bin - irreversible).

### **🧪 Postman Setup**
```
Method: DELETE
URL: {{base_url}}/batch/delete/{{test_file_id}}?permanent=true
Headers:
  Accept: application/json
```

### **⚠️ Warning Tests**
```javascript
pm.test("Permanent deletion successful", function () {
    pm.response.to.have.status(200);
});

pm.test("Response confirms permanent deletion", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('message');
    pm.expect(jsonData.message).to.include('permanently deleted');
    pm.expect(jsonData).to.have.property('fileId');
});

pm.test("⚠️ IRREVERSIBLE ACTION", function () {
    console.log("WARNING: This file has been permanently deleted and cannot be recovered!");
});
```

**Response:**
```json
{
    "message": "File xyz permanently deleted",
    "fileId": "xyz",
    "fileName": "document.pdf"
}
```

---

# Long-Batch Endpoints (AWS Batch Processing)

## Upload for Long-Batch
**Endpoint:** `POST /long-batch/upload`

**Purpose:** Force upload to long-batch processing (bypasses smart routing).

---

## Long-Batch Operations

**File Management:** All file operations (delete, restore, recycle bin) use the unified `/batch/` endpoints for consistent access across all processing types.

---

# Short-Batch Endpoints (Claude AI Processing)

## Upload for Short-Batch
**Endpoint:** `POST /short-batch/upload`

**Purpose:** Force upload to short-batch processing (bypasses smart routing).

---

## Short-Batch Operations

**Note:** File management (delete, restore, recycle bin) should use the unified endpoints:
- Use `/batch/delete/{fileId}` instead of `/short-batch/delete/{fileId}`
- Use `/batch/recycle-bin` instead of `/short-batch/recycle-bin`
- Use `/batch/restore/{fileId}` instead of `/short-batch/restore/{fileId}`
- All functionality uses the unified endpoints as all data is stored in a single table

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
| **Search** | ✅ **Intelligent Fuzzy Search** | ✅ **Included** | ✅ **Included** | ❌ Removed |
| **Auto-Fuzzy** | ✅ **Smart Fallback** | ✅ **Smart Fallback** | ✅ **Smart Fallback** | ❌ N/A |
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
const uploadResponse = await fetch('/v1/batch/upload', {
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
// Force short-batch processing (bypasses smart routing)
const uploadResponse = await fetch('/v1/short-batch/upload', {
  method: 'POST',
  body: formData
});

const { fileId } = await uploadResponse.json();

// Processing starts automatically after upload
// Check results using unified endpoint after processing time
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
// Search all processed files (unified batch endpoint)
const searchAll = await fetch('/v1/batch/search?q=transportation&fuzzy=true');

// Get all processed files
const allFiles = await fetch('/v1/batch/processed');

// Get specific processed file
const specificFile = await fetch('/v1/batch/processed?fileId=your-file-id');
```

## 5. File Management & Recycle Bin Workflow
```javascript
// Delete file (soft delete to recycle bin)
await fetch(`/v1/batch/delete/${fileId}`, { method: 'DELETE' });

// View recycle bin contents
const recycleBin = await fetch('/v1/batch/recycle-bin');
const deletedFiles = await recycleBin.json();

// Restore file from recycle bin
await fetch(`/v1/batch/restore/${fileId}`, { method: 'POST' });

// Permanent delete (bypasses recycle bin)
await fetch(`/v1/batch/delete/${fileId}?permanent=true`, { method: 'DELETE' });

// Display dates in user's timezone
deletedFiles.items.forEach(item => {
    const localDeletedAt = new Date(item.deletedAt).toLocaleString();
    const localExpiresAt = new Date(item.expiresAt).toLocaleString();
    console.log(`Deleted: ${localDeletedAt}, Expires: ${localExpiresAt}`);
});
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
✅ **Intelligent search** with auto-fuzzy fallback and contextual snippets  
✅ **Multi-language support** across English, Filipino, and other languages
✅ **Academic relevance scoring** with Google Scholar-style ranking
✅ **Cost tracking** with per-document processing costs

---

---

## 🔄 Complete Postman Workflow

### **📋 Recommended Testing Sequence**

1. **🔧 Setup Environment**
   - Import environment variables
   - Set base_url to your API Gateway endpoint

2. **📤 Upload Document**
   ```
   POST {{base_url}}/upload
   ↓ Saves file_id to environment
   ```

3. **⏳ Wait for Processing** (30s - 5min depending on file size)

4. **📄 Verify Processing**
   ```
   GET {{base_url}}/batch/processed?fileId={{file_id}}
   ↓ Confirms document is processed
   ```

5. **🔍 Test Search**
   ```
   GET {{base_url}}/batch/search?q=your+search+term
   ↓ Finds your uploaded document
   ```

6. **✏️ Test File Management**
   ```
   DELETE {{base_url}}/batch/delete/{{file_id}}
   ↓ Moves to recycle bin
   
   GET {{base_url}}/batch/recycle-bin
   ↓ Confirms file in recycle bin
   
   POST {{base_url}}/batch/restore/{{file_id}}
   ↓ Restores file to active state
   ```

### **🚀 Quick Import Collection**

Copy this JSON to import a complete Postman collection:

```json
{
  "info": {
    "name": "OCR Document Processing API",
    "description": "Complete API testing collection for intelligent OCR processing",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "https://fqyxavdri0.execute-api.ap-southeast-2.amazonaws.com/v1"
    }
  ],
  "item": [
    {
      "name": "1. Upload Document",
      "request": {
        "method": "POST",
        "header": [],
        "body": {
          "mode": "formdata",
          "formdata": [
            {"key": "file", "type": "file"},
            {"key": "publication", "value": "Test Publication"},
            {"key": "year", "value": "2025"},
            {"key": "title", "value": "Test Document"},
            {"key": "author", "value": "Test Author"}
          ]
        },
        "url": "{{base_url}}/upload"
      }
    },
    {
      "name": "2. Get Processed Files",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/batch/processed"
      }
    },
    {
      "name": "3. Search Documents",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/batch/search?q=test&fuzzy=true"
      }
    },
    {
      "name": "4. Delete File",
      "request": {
        "method": "DELETE",
        "url": "{{base_url}}/batch/delete/{{file_id}}"
      }
    },
    {
      "name": "5. View Recycle Bin",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/batch/recycle-bin"
      }
    },
    {
      "name": "6. Restore File",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/batch/restore/{{file_id}}"
      }
    }
  ]
}
```

### **💡 Pro Tips for Testing**

- **File ID Management**: Use Postman's `pm.globals.set()` to automatically capture file IDs
- **Environment Switching**: Create separate environments for dev/staging/prod
- **Batch Testing**: Use Postman Runner for automated testing sequences
- **Real Files**: Test with actual PDF/image files for realistic results
- **Fuzzy Search**: Test with intentional typos to verify fuzzy matching

---

## 📞 Contact & Support

For questions, enterprise inquiries, or technical support regarding this API:

**Author:** Martin Lawrence Caringal  
**Email:** [lawrencecaringal5@gmail.com](mailto:lawrencecaringal5@gmail.com)  
**Specialization:** Serverless Architecture, AI Integration, Enterprise Document Processing

*Last Updated: August 20, 2025*