# Enhanced Invoice OCR Fields

## 🎯 Comprehensive Invoice Data Extraction

Based on the `invoice-example.png`, the enhanced OCR system now extracts **70+ detailed fields** organized into logical sections:

## 📊 **Business Information** (12 fields)
- `businessName`: "Your business name"
- `tradingName`: Trading/brand name if different
- `addressLine1`: "126 Industry Road" 
- `addressLine2`: Suite/unit if present
- `city`: "Auckland"
- `stateProvince`: State/province
- `postalCode`: "1061"
- `country`: "New Zealand"
- `fullAddress`: Complete formatted address
- `phone`: Phone number
- `email`: "email@yourbusinessname.co.nz"
- `website`: Website URL if present
- `taxId`: Tax ID/ABN/VAT number
- `businessNumber`: Business registration number
- `logoPresent`: Boolean - logo detection

## 👥 **Client Information** (11 fields)
- `clientName`: "Your client"
- `contactPerson`: Contact person if specified
- `addressLine1`: "75 Hamlin Road"
- `addressLine2`: Suite/unit if present
- `city`: "Auckland" 
- `stateProvince`: State/province
- `postalCode`: "1060"
- `country`: "New Zealand"
- `fullAddress`: Complete client address
- `phone`: Client phone
- `email`: Client email

## 📋 **Invoice Details** (8 fields)
- `invoiceNumber`: "2021011"
- `issueDate`: "11/30/2021"
- `dueDate`: "12/14/2021"
- `referenceNumber`: "2021011"
- `purchaseOrder`: PO number if present
- `customerId`: Customer ID if present
- `projectCode`: Project code if present
- `invoiceType`: standard/credit_note/receipt/etc

## 💰 **Financial Summary** (12 fields)
- `subtotal`: "$500.00"
- `discountAmount`: Discount amount if present
- `discountPercentage`: Discount % if present
- `taxAmount`: Tax amount
- `taxRate`: Tax rate %
- `taxType`: GST/VAT/Sales Tax type
- `shippingCost`: Shipping cost if present
- `otherCharges`: Other charges if present
- `totalBeforeTax`: Total before tax
- `totalAmount`: "$500.00"
- `totalDue`: "$500.00" (NZD)
- `currencyCode`: "NZD"
- `currencySymbol`: "$"

## 📦 **Line Items** (9 fields per item)
- `itemNumber`: Item/SKU number if present
- `description`: "Sample service"
- `category`: Item category if specified
- `quantity`: "1"
- `unitOfMeasure`: hours/pieces/kg/etc
- `unitPrice`: "$500.00"
- `lineTotal`: "$500.00"
- `taxIncluded`: Boolean
- `discountApplied`: Line discount if present

## 💳 **Payment Information** (8 fields)
- `paymentTerms`: Payment terms
- `paymentDueDays`: Days until due
- `paymentMethods`: Accepted payment methods
- `bankName`: Bank name if present
- `accountNumber`: Account number if present
- `routingNumber`: Routing/sort code if present
- `swiftCode`: SWIFT/BIC code if present
- `paymentReference`: Payment reference if specified

## 📄 **Additional Information** (7 fields)
- `notes`: Additional notes or terms
- `termsConditions`: Terms and conditions text
- `signaturePresent`: Boolean - signature detection
- `signatureText`: "Issued by, signature:"
- `authorizedBy`: Authorization information
- `documentFooter`: Footer text
- `watermarks`: Watermark text if present
- `pageNumbers`: Page numbering if multi-page

## 🔧 **Document Metadata** (7 fields)
- `extractionConfidence`: high/medium/low
- `detectedLanguage`: Primary language
- `documentQuality`: excellent/good/fair/poor
- `fieldsExtractedCount`: Number of fields extracted
- `missingFields`: List of fields not found
- `dataValidationNotes`: Validation concerns
- `processingModel`: "claude-sonnet-4-20250514"

## 💰 **Processing Cost Details** (10 fields)
- `totalCost`: Total processing cost in USD
- `inputTokens`: Number of input tokens used
- `outputTokens`: Number of output tokens generated
- `totalTokens`: Total tokens (input + output)
- `inputCost`: Cost for input tokens
- `outputCost`: Cost for output tokens
- `costPer1kInputTokens`: Rate per 1K input tokens ($0.003)
- `costPer1kOutputTokens`: Rate per 1K output tokens ($0.015)
- `ocrLlmProvider`: "Claude API"
- `currency`: "USD"

## 📤 **Upload Metadata** (7 fields)
- `processingPriority`: normal/urgent/low
- `businessCategory`: Category classification
- `uploadSource`: Source of upload
- `tags`: Associated tags
- `originalFileName`: Original file name
- `fileSize`: File size in bytes
- `contentType`: MIME type

---

## 🎯 **Expected Results for invoice-example.png**

### **Business Information:**
```json
{
  "businessName": "Your business name",
  "fullAddress": "126 Industry Road, Auckland 1061, New Zealand",
  "email": "email@yourbusinessname.co.nz",
  "logoPresent": true
}
```

### **Client Information:**
```json
{
  "clientName": "Your client", 
  "fullAddress": "75 Hamlin Road, Auckland 1060, New Zealand"
}
```

### **Invoice Details:**
```json
{
  "invoiceNumber": "2021011",
  "issueDate": "11/30/2021",
  "dueDate": "12/14/2021",
  "referenceNumber": "2021011"
}
```

### **Financial Summary:**
```json
{
  "subtotal": "NZ$500.00",
  "totalAmount": "NZ$500.00", 
  "totalDue": "NZ$500.00",
  "currencyCode": "NZD",
  "currencySymbol": "$"
}
```

### **Line Items:**
```json
[{
  "description": "Sample service",
  "quantity": "1", 
  "unitPrice": "NZ$500.00",
  "lineTotal": "NZ$500.00"
}]
```

### **Additional Information:**
```json
{
  "signaturePresent": true,
  "signatureText": "Issued by, signature:",
  "authorizedBy": "Your home security"
}
```

### **Processing Cost Details:**
```json
{
  "totalCost": 0.0148,
  "inputTokens": 1256,
  "outputTokens": 892,
  "totalTokens": 2148,
  "inputCost": 0.00377,
  "outputCost": 0.01338,
  "costPer1kInputTokens": 0.003,
  "costPer1kOutputTokens": 0.015,
  "ocrLlmProvider": "Claude API",
  "currency": "USD"
}
```

---

## 🚀 **Benefits of Enhanced Fields**

1. **Complete Data Capture**: Every visible element extracted
2. **Structured Organization**: Logical grouping of related fields  
3. **Currency Handling**: Proper formatting with symbols and codes
4. **Address Parsing**: Detailed address component extraction
5. **Quality Assessment**: Confidence and validation scoring
6. **Visual Element Detection**: Logo and signature recognition
7. **Multilingual Support**: Language detection and handling
8. **Flexible Line Items**: Support for complex item structures

This comprehensive extraction provides everything needed for automated invoice processing, accounting integration, and business intelligence! 🎉