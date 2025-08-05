# Invoice OCR Processing API

## Overview

The Invoice OCR Processing system provides specialized invoice document processing using Claude AI with enhanced prompts designed specifically for invoice data extraction and structured output.

## Endpoint

**POST** `/batch/short-batch/invoices/upload`

## Features

### 🧾 Invoice-Specific Processing
- **Specialized OCR Prompts**: Optimized for invoice field recognition
- **Structured Data Extraction**: JSON output with organized invoice fields
- **Enhanced Field Detection**: Vendor info, amounts, dates, line items, payment terms
- **Invoice Validation**: File type and size validation specific to invoices

### 📊 Structured Output
The system extracts and organizes:
- **Vendor Information**: Name, address, contact details, tax ID
- **Invoice Details**: Number, date, due date, purchase order
- **Financial Data**: Subtotal, tax amount, total, currency
- **Line Items**: Description, quantity, unit price, amounts
- **Payment Information**: Terms, methods, bank details
- **Addresses**: Bill-to and ship-to addresses

## Request Format

```json
{
  "file": "base64_encoded_file_content",
  "fileName": "invoice_001.pdf",
  "contentType": "application/pdf",
  
  // Optional Invoice Metadata
  "vendorName": "ABC Company Ltd",
  "invoiceNumber": "INV-2025-001",
  "invoiceDate": "2025-08-04",
  "dueDate": "2025-09-04",
  "totalAmount": "1250.00",
  "currency": "USD",
  "purchaseOrder": "PO-12345",
  "taxAmount": "125.00",
  "paymentTerms": "Net 30",
  
  // Classification
  "invoiceType": "standard", // standard, credit_note, receipt, estimate
  "businessCategory": "consulting",
  "priority": "normal", // urgent, normal, low
  
  // Standard metadata
  "description": "Monthly consulting invoice",
  "tags": ["consulting", "monthly", "professional-services"]
}
```

## Response Format

```json
{
  "fileId": "uuid-generated-id",
  "fileName": "invoice_001.pdf",
  "uploadTimestamp": "2025-08-04T12:00:00Z",
  "processingStatus": "uploaded",
  "processingRoute": "invoice-ocr",
  "fileSize": 245760,
  "fileSizeMB": 0.23,
  "contentType": "application/pdf",
  "s3Key": "invoice-files/uuid-generated-id.pdf",
  
  "note": "All invoice data will be extracted automatically by Claude AI OCR - no manual input required",
  
  "message": "Invoice uploaded successfully and queued for OCR processing"
}
```

## Processed Invoice Data Structure

Once processed, the invoice data is structured as:

```json
{
  "ocrResults": {
    "formattedText": "Raw extracted text...",
    "refinedText": "JSON structured data...",
    "structuredData": {
      "vendor_info": {
        "name": "ABC Company Ltd",
        "address": "123 Business St, City, State 12345",
        "phone": "+1-555-0123",
        "email": "billing@abccompany.com",
        "tax_id": "12-3456789"
      },
      "invoice_details": {
        "number": "INV-2025-001",
        "date": "2025-08-04",
        "due_date": "2025-09-04",
        "purchase_order": "PO-12345"
      },
      "amounts": {
        "subtotal": "1125.00",
        "tax_amount": "125.00",
        "tax_rate": "11.11%",
        "total": "1250.00",
        "currency": "USD"
      },
      "line_items": [
        {
          "description": "Consulting Services - July 2025",
          "quantity": "40",
          "unit_price": "28.125",
          "amount": "1125.00"
        }
      ],
      "payment_info": {
        "terms": "Net 30",
        "method": "Bank Transfer",
        "bank_details": "Account: 123-456-789"
      },
      "addresses": {
        "bill_to": "Client Company\n456 Client Ave\nClient City, State 67890",
        "ship_to": "Same as billing"
      },
      "extraction_confidence": "high",
      "language": "English",
      "invoice_type": "standard"
    }
  },
  "processingType": "invoice-ocr",
  "processingModel": "claude-sonnet-4-20250514",
  "extractionConfidence": "high",
  "invoiceFieldsExtracted": 15
}
```

## Supported File Types

- **PDF**: `application/pdf`
- **PNG**: `image/png`
- **JPEG**: `image/jpeg`, `image/jpg`

## File Size Limits

- **Maximum**: 10MB per invoice
- **Minimum**: 1KB per invoice

## Processing Flow

1. **Upload**: Invoice uploaded via POST endpoint
2. **Validation**: File type and size validation
3. **Storage**: File stored in S3 `invoice-files/` folder
4. **Metadata**: Invoice metadata stored in DynamoDB
5. **Queuing**: Message sent to invoice processing queue
6. **Processing**: Claude AI processes with invoice-specific prompts
7. **Extraction**: Structured data extracted and stored
8. **Completion**: Results available via standard `/processed` endpoint

## Error Handling

### Common Errors

- **400 Bad Request**: Invalid file format or missing required fields
- **413 Payload Too Large**: File exceeds 10MB limit
- **500 Internal Server Error**: Processing or storage failures

### Error Response Format

```json
{
  "error": "Invalid Invoice File",
  "message": "Unsupported file type: text/plain. Supported types: PDF, PNG, JPG, JPEG"
}
```

## Budget and Cost Management

- Uses the same Claude API budget as other OCR processing
- Invoice processing may use more tokens due to structured extraction
- Budget alerts configured for 90% threshold
- Cost tracking per invoice available in processing results

## Monitoring and Alerts

### CloudWatch Alarms
- **Invoice DLQ Messages**: Alerts when processing fails
- **High Message Count**: Alerts for systemic issues
- **Processing Duration**: Monitors for timeout issues

### Logs
- Invoice uploader logs: `/aws/lambda/{project}-{env}-invoice-uploader`
- Invoice processor logs: `/aws/lambda/{project}-{env}-invoice-processor`

## Usage Examples

### JavaScript/Node.js

```javascript
const invoiceData = {
  file: fileBase64,
  fileName: "invoice.pdf",
  contentType: "application/pdf",
  vendorName: "Tech Solutions Inc",
  invoiceNumber: "TS-2025-001",
  totalAmount: "2500.00",
  currency: "USD",
  invoiceType: "standard"
};

const response = await fetch('/batch/short-batch/invoices/upload', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(invoiceData)
});

const result = await response.json();
console.log('Invoice uploaded:', result.fileId);
```

### Python

```python
import requests
import base64

with open('invoice.pdf', 'rb') as file:
    file_base64 = base64.b64encode(file.read()).decode('utf-8')

payload = {
    "file": file_base64,
    "fileName": "invoice.pdf",
    "contentType": "application/pdf",
    "vendorName": "Tech Solutions Inc",
    "invoiceNumber": "TS-2025-001",
    "totalAmount": "2500.00",
    "currency": "USD"
}

response = requests.post(
    'https://api.yourhost.com/batch/short-batch/invoices/upload',
    json=payload
)

result = response.json()
print(f"Invoice uploaded: {result['fileId']}")
```

## Benefits Over Standard OCR

1. **Specialized Processing**: Invoice-specific prompts and field recognition
2. **Structured Output**: Organized JSON data instead of raw text
3. **Enhanced Accuracy**: Optimized for financial document formats
4. **Business Integration**: Ready-to-use structured data for accounting systems
5. **Field Validation**: Built-in validation for invoice-specific fields
6. **Cost Efficiency**: Targeted processing reduces unnecessary refinement

This invoice OCR system provides a professional-grade solution for automated invoice processing and data extraction.